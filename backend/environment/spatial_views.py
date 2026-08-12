"""
地理空间服务视图
提供WMS、WFS、WCS等OGC标准服务接口
"""

import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Optional, Tuple

import rasterio
from django.conf import settings
from django.db import connection
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .band_mapping import infer_rgb_bands
from .geoserver_config import get_geoserver_manager
from .models import BusinessLayer, EcologicalIndex, RemoteSensingImage

logger = logging.getLogger(__name__)

PREFERRED_HIGHRES_IMAGERY_FILE = '2023.tif'


def _highres_imagery_root() -> Path:
    return Path(settings.MEDIA_ROOT) / 'fixed_highres_imagery'


def _highres_imagery_catalog_path() -> Path:
    return Path(settings.MEDIA_ROOT) / 'highres_imagery_catalog.json'


def _highres_publish_cache_dir() -> Path:
    return Path(settings.MEDIA_ROOT) / 'highres_publish_cache'


def _highres_preview_relative_path(relative_path: Path) -> Optional[str]:
    stem = relative_path.stem
    preview_relative = relative_path.with_name(f'{stem}_preview.png')
    preview_file = _highres_imagery_root() / preview_relative
    if preview_file.exists() and preview_file.is_file():
        return Path('fixed_highres_imagery', preview_relative.name).as_posix()
    return None


def _media_url(relative_path: Optional[str]) -> Optional[str]:
    if not relative_path:
        return None
    return settings.MEDIA_URL + str(relative_path).replace('\\', '/')


def _load_highres_imagery_catalog() -> dict:
    catalog_path = _highres_imagery_catalog_path()
    if not catalog_path.exists():
        return {}
    try:
        with catalog_path.open('r', encoding='utf-8') as catalog_file:
            data = json.load(catalog_file)
            return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.warning(f"读取高分影像目录失败: {exc}")
        return {}


def _save_highres_imagery_catalog(catalog: dict) -> None:
    catalog_path = _highres_imagery_catalog_path()
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    with catalog_path.open('w', encoding='utf-8') as catalog_file:
        json.dump(catalog, catalog_file, ensure_ascii=False, indent=2)


def _ensure_geoserver_publishable_raster(file_path: Path, imagery_key: str) -> Path:
    """
    GeoServer/Tomcat 在当前环境下无法稳定读取带中文目录的 GeoTIFF 路径。
    为发布过程准备一个 ASCII 路径的硬链接，避免复制超大影像文件。
    """
    try:
        file_path.as_posix().encode('ascii')
        return file_path
    except UnicodeEncodeError:
        pass

    cache_dir = _highres_publish_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha1(imagery_key.encode('utf-8')).hexdigest()[:16]
    staged_path = cache_dir / f'{digest}{file_path.suffix.lower()}'

    if staged_path.exists() and staged_path.is_file():
        return staged_path

    try:
        os.link(file_path, staged_path)
        return staged_path
    except OSError:
        # 如果硬链接失败，再退回复制，保证发布链路可用。
        import shutil
        shutil.copy2(file_path, staged_path)
        return staged_path


def _build_raster_service_urls(geoserver, layer_name: str) -> dict:
    qualified_layer = f'{geoserver.workspace}:{layer_name}'
    base_ows = f'{geoserver.base_url}/ows'
    return {
        'wms_url': (
            f'{base_ows}?service=WMS&version=1.3.0&request=GetMap'
            f'&layers={qualified_layer}&format=image/png&transparent=true'
        ),
        'wfs_url': None,
        'wcs_url': (
            f'{base_ows}?service=WCS&version=2.0.1&request=GetCoverage'
            f'&coverageId={qualified_layer}'
        ),
    }


def _resolve_catalog_layer_name(geoserver, entry: dict, fallback_layer_name: str) -> str:
    if not entry:
        return fallback_layer_name

    store_name = entry.get('geoserver_store_name')
    preferred_layer_name = entry.get('geoserver_layer_name') or fallback_layer_name
    if preferred_layer_name:
        return preferred_layer_name
    if not store_name:
        return preferred_layer_name

    try:
        return geoserver.resolve_raster_layer_name(store_name, preferred_layer_name) or preferred_layer_name
    except Exception as exc:
        logger.warning(f"解析高分影像实际图层名失败: {exc}")
        return preferred_layer_name


def _infer_imagery_rgb_bands(dataset) -> dict:
    rgb_mapping = infer_rgb_bands(dataset=dataset)
    if rgb_mapping:
        return rgb_mapping
    if getattr(dataset, 'count', 0) >= 3:
        return {'red_band': 3, 'green_band': 2, 'blue_band': 1}
    return {}


def _highres_imagery_metadata(file_path: Path) -> dict:
    metadata = {
        'file_size_bytes': file_path.stat().st_size,
    }
    try:
        with rasterio.open(file_path) as dataset:
            bounds = dataset.bounds
            metadata.update({
                'bounds': [bounds.left, bounds.bottom, bounds.right, bounds.top],
                'crs': dataset.crs.to_string() if dataset.crs else None,
                'width': dataset.width,
                'height': dataset.height,
                'band_count': dataset.count,
                'dtype': dataset.dtypes[0] if dataset.dtypes else None,
                'colorinterp': [str(item) for item in getattr(dataset, 'colorinterp', ())],
                'rgb_bands': _infer_imagery_rgb_bands(dataset),
            })
    except Exception as exc:
        logger.warning(f"读取高分影像元数据失败 {file_path}: {exc}")
    return metadata


def _parse_imagery_details(file_name: str) -> dict:
    stem = Path(file_name).stem
    date_match = re.search(r'(?<!\d)(20\d{6}|19\d{6})(?!\d)', stem)
    acquisition_date = None
    if date_match:
        raw_date = date_match.group(1)
        acquisition_date = f'{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}'

    sensor = None
    sensor_match = re.match(r'([A-Za-z0-9]+(?:_[A-Za-z0-9]+)?)', stem)
    if sensor_match:
        sensor = sensor_match.group(1)

    return {
        'sensor': sensor,
        'acquisition_date': acquisition_date,
    }


def _highres_imagery_id(relative_path: Path) -> str:
    return relative_path.as_posix()


def _highres_imagery_sort_key(file_path: Path):
    preferred_rank = 0 if file_path.name == PREFERRED_HIGHRES_IMAGERY_FILE else 1
    return (preferred_rank, file_path.name)


def _highres_imagery_layer_name(imagery_id: str) -> str:
    digest = hashlib.sha1(imagery_id.encode('utf-8')).hexdigest()[:12]
    return f'highres_imagery_{digest}'


def _resolve_highres_imagery_file(imagery_id: str) -> Tuple[Path, Path]:
    imagery_root = _highres_imagery_root()
    target_file = imagery_root / imagery_id
    if target_file.exists() and target_file.is_file():
        return target_file, Path(imagery_id)

    for file_path in imagery_root.rglob('*.tif'):
        relative_path = file_path.relative_to(imagery_root)
        if relative_path.as_posix() == imagery_id or file_path.name == imagery_id:
            return file_path, relative_path

    raise FileNotFoundError(f'未找到影像文件: {imagery_id}')


def _build_highres_imagery_record(file_path: Path, relative_path: Path, catalog_entry: Optional[dict] = None) -> dict:
    imagery_id = _highres_imagery_id(relative_path)
    details = _parse_imagery_details(file_path.name)
    metadata = _highres_imagery_metadata(file_path)
    preview_relative_path = _highres_preview_relative_path(relative_path)
    entry = dict(catalog_entry or {})
    is_published = bool(entry.get('geoserver_layer_name') and entry.get('published_at'))
    status_code = entry.get('status') if entry.get('status') in {'ready', 'published', 'failed'} else None
    status_value = status_code or ('published' if is_published else 'ready')
    status_display = {
        'ready': '可加载',
        'published': '已发布',
        'failed': '发布失败',
    }.get(status_value, '可加载')

    return {
        'id': imagery_id,
        'name': file_path.stem,
        'file_name': file_path.name,
        'relative_path': relative_path.as_posix(),
        'layer_type': 'raster',
        'source_format': 'system_geotiff',
        'source_format_display': '系统高分影像',
        'status': status_value,
        'status_display': status_display,
        'sensor': details.get('sensor'),
        'acquisition_date': details.get('acquisition_date'),
        'geoserver_workspace': entry.get('geoserver_workspace'),
        'geoserver_store_name': entry.get('geoserver_store_name'),
        'geoserver_layer_name': entry.get('geoserver_layer_name'),
        'wms_url': entry.get('wms_url'),
        'wfs_url': entry.get('wfs_url'),
        'wcs_url': entry.get('wcs_url'),
        'preview_image_url': _media_url(preview_relative_path),
        'published_at': entry.get('published_at'),
        'error_message': entry.get('error_message', ''),
        'metadata': metadata,
    }


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def wms_capabilities(request):
    """获取WMS服务能力"""
    try:
        geoserver = get_geoserver_manager()
        capabilities = geoserver.get_wms_capabilities()

        if capabilities:
            return HttpResponse(capabilities, content_type='application/xml')
        return Response(
            {'error': '无法获取WMS服务能力'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        logger.error(f"获取WMS能力失败: {e}")
        return Response(
            {'error': f'获取WMS能力失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def wms_map(request):
    """WMS地图服务"""
    try:
        geoserver = get_geoserver_manager()
        import requests
        upstream = requests.get(
            f"{geoserver.base_url}/ows",
            params=request.GET,
            auth=geoserver.auth,
            timeout=120,
        )
        return HttpResponse(
            upstream.content,
            status=upstream.status_code,
            content_type=upstream.headers.get('Content-Type', 'application/octet-stream')
        )

    except Exception as e:
        logger.error(f"WMS地图服务失败: {e}")
        return Response(
            {'error': f'WMS地图服务失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def wfs_capabilities(request):
    """获取WFS服务能力"""
    try:
        geoserver = get_geoserver_manager()
        wfs_url = f"{geoserver.base_url}/ows?service=WFS&version=2.0.0&request=GetCapabilities"

        return Response({
            'message': 'WFS服务能力',
            'wfs_url': wfs_url,
            'supported_operations': [
                'GetCapabilities',
                'DescribeFeatureType',
                'GetFeature',
                'Transaction'
            ]
        })

    except Exception as e:
        logger.error(f"获取WFS能力失败: {e}")
        return Response(
            {'error': f'获取WFS能力失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def spatial_layers(request):
    """获取可用的空间图层列表"""
    try:
        remote_sensing_images = RemoteSensingImage.objects.all().values('id', 'name', 'image_type', 'center_lat', 'center_lon')
        ecological_indices = EcologicalIndex.objects.all().values(
            'id', 'index_type', 'remote_sensing_image__name',
            'remote_sensing_image__center_lat', 'remote_sensing_image__center_lon'
        )

        layers = {
            'remote_sensing': list(remote_sensing_images),
            'ecological_indices': list(ecological_indices)
        }

        return Response({
            'message': '获取空间图层成功',
            'layers': layers
        })

    except Exception as e:
        logger.error(f"获取空间图层失败: {e}")
        return Response(
            {'error': f'获取空间图层失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def highres_imagery_list(request):
    """扫描系统内置高分影像，供主地图页作为参考影像底图使用。"""
    try:
        imagery_root = _highres_imagery_root()
        if not imagery_root.exists():
            return Response({
                'message': '高分影像目录不存在',
                'imagery_root': str(imagery_root),
                'results': [],
            })

        catalog = _load_highres_imagery_catalog()
        geoserver = None
        catalog_changed = False
        results = []
        tif_files = sorted(imagery_root.rglob('*.tif'), key=_highres_imagery_sort_key)
        preferred_matches = [file_path for file_path in tif_files if file_path.name == PREFERRED_HIGHRES_IMAGERY_FILE]
        iterable_files = preferred_matches or tif_files

        for file_path in iterable_files:
            relative_path = file_path.relative_to(imagery_root)
            imagery_id = _highres_imagery_id(relative_path)
            entry = dict(catalog.get(imagery_id) or {})
            if entry.get('status') == 'published' and entry.get('geoserver_store_name'):
                geoserver = geoserver or get_geoserver_manager()
                actual_layer_name = _resolve_catalog_layer_name(
                    geoserver,
                    entry,
                    fallback_layer_name=_highres_imagery_layer_name(imagery_id),
                )
                if actual_layer_name and entry.get('geoserver_layer_name') != actual_layer_name:
                    entry['geoserver_layer_name'] = actual_layer_name
                    urls = _build_raster_service_urls(geoserver, actual_layer_name)
                    entry.update(urls)
                    catalog[imagery_id] = entry
                    catalog_changed = True
            results.append(_build_highres_imagery_record(
                file_path=file_path,
                relative_path=relative_path,
                catalog_entry=entry,
            ))

        if catalog_changed:
            _save_highres_imagery_catalog(catalog)

        return Response({
            'message': '获取高分影像列表成功',
            'imagery_root': str(imagery_root),
            'count': len(results),
            'results': results,
        })
    except Exception as exc:
        logger.error(f"获取高分影像列表失败: {exc}")
        return Response(
            {'error': f'获取高分影像列表失败: {str(exc)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def publish_highres_imagery(request):
    """将系统高分影像发布为GeoServer WMS/WCS图层。"""
    imagery_id = request.data.get('imagery_id') or request.data.get('id') or request.data.get('file_name')
    if not imagery_id:
        return Response(
            {'error': '缺少 imagery_id 参数'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        file_path, relative_path = _resolve_highres_imagery_file(str(imagery_id))
        imagery_key = _highres_imagery_id(relative_path)
        layer_name = _highres_imagery_layer_name(imagery_key)
        store_name = f'{layer_name}_store'
        publishable_file_path = _ensure_geoserver_publishable_raster(file_path, imagery_key)

        geoserver = get_geoserver_manager()
        geoserver.create_workspace()
        published = geoserver.publish_raster(
            coverage_store_name=store_name,
            layer_name=layer_name,
            file_path=str(publishable_file_path),
            style_type='imagery_rgb',
        )
        actual_layer_name = geoserver.resolve_raster_layer_name(store_name, layer_name) if published else layer_name

        catalog = _load_highres_imagery_catalog()
        entry = dict(catalog.get(imagery_key) or {})

        if published:
            urls = _build_raster_service_urls(geoserver, actual_layer_name)
            entry.update({
                'status': 'published',
                'file_name': file_path.name,
                'relative_path': relative_path.as_posix(),
                'geoserver_workspace': geoserver.workspace,
                'geoserver_store_name': store_name,
                'geoserver_layer_name': actual_layer_name,
                'published_at': timezone.now().isoformat(),
                'error_message': '',
                **urls,
            })
        else:
            entry.update({
                'status': 'failed',
                'file_name': file_path.name,
                'relative_path': relative_path.as_posix(),
                'geoserver_workspace': geoserver.workspace,
                'geoserver_store_name': store_name,
                'geoserver_layer_name': layer_name,
                'published_at': entry.get('published_at'),
                'error_message': 'GeoServer发布失败，请检查GeoServer服务和日志',
            })

        catalog[imagery_key] = entry
        _save_highres_imagery_catalog(catalog)

        record = _build_highres_imagery_record(
            file_path=file_path,
            relative_path=relative_path,
            catalog_entry=entry,
        )

        response_status = status.HTTP_200_OK if published else status.HTTP_500_INTERNAL_SERVER_ERROR
        return Response({
            'message': '高分影像发布成功' if published else '高分影像发布失败',
            'result': record,
        }, status=response_status)
    except FileNotFoundError as exc:
        return Response(
            {'error': str(exc)},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as exc:
        logger.error(f"发布高分影像失败: {exc}")
        return Response(
            {'error': f'发布高分影像失败: {str(exc)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def publish_to_geoserver(request):
    """发布图层到GeoServer"""
    try:
        layer_id = request.data.get('layer_id')
        layer_type = request.data.get('layer_type')
        datastore_name = request.data.get('datastore_name')

        if not all([layer_id, layer_type, datastore_name]):
            return Response(
                {'error': '缺少必要参数'},
                status=status.HTTP_400_BAD_REQUEST
            )

        geoserver = get_geoserver_manager()

        if layer_type == 'remote_sensing':
            layer_obj = RemoteSensingImage.objects.get(id=layer_id)
            file_path = layer_obj.file_path.path
            layer_name = f"rs_{layer_obj.name}"
        elif layer_type == 'ecological_indices':
            layer_obj = EcologicalIndex.objects.get(id=layer_id)
            file_path = layer_obj.result_file.path
            layer_name = f"ei_{layer_obj.remote_sensing_image.name}"
        else:
            return Response(
                {'error': '不支持的图层类型'},
                status=status.HTTP_400_BAD_REQUEST
            )

        geoserver.create_workspace()

        if not geoserver.create_datastore(datastore_name):
            return Response(
                {'error': '创建数据存储失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if geoserver.publish_raster(datastore_name, layer_name, file_path):
            return Response({
                'message': '图层发布成功',
                'layer_name': layer_name,
                'wms_url': f"{geoserver.base_url}/ows?service=WMS&version=1.3.0&request=GetMap&layers={geoserver.workspace}:{layer_name}"
            })
        return Response(
            {'error': '图层发布失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    except RemoteSensingImage.DoesNotExist:
        return Response(
            {'error': '遥感影像不存在'},
            status=status.HTTP_404_NOT_FOUND
        )
    except EcologicalIndex.DoesNotExist:
        return Response(
            {'error': '生态指数不存在'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"发布图层到GeoServer失败: {e}")
        return Response(
            {'error': f'发布图层失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def geoserver_status(request):
    """获取GeoServer状态"""
    try:
        geoserver = get_geoserver_manager()
        capabilities = geoserver.get_wms_capabilities()

        workspace_ok = False
        try:
            workspace_ok = geoserver.create_workspace()
        except Exception:
            pass

        status_info = {
            'connected': capabilities is not None,
            'base_url': geoserver.base_url,
            'workspace': geoserver.workspace,
            'workspace_ready': workspace_ok,
            'wms_enabled': capabilities is not None,
            'wfs_enabled': True,
            'wcs_enabled': True,
            'configured': True
        }

        return Response({
            'message': '获取GeoServer状态成功',
            'status': status_info,
            'tips': {
                'connected': 'GeoServer连接正常' if capabilities else 'GeoServer未连接，请检查配置和运行状态',
                'workspace': f'工作空间 "{geoserver.workspace}" {"已就绪" if workspace_ok else "需要创建"}',
                'next_steps': [] if capabilities else [
                    '1. 确认GeoServer已启动（访问 http://localhost:8080/geoserver）',
                    '2. 检查配置的URL、用户名、密码是否正确',
                    '3. 运行命令测试：python manage.py test_geoserver'
                ]
            }
        })

    except Exception as e:
        logger.error(f"获取GeoServer状态失败: {e}")
        status_info = {
            'connected': False,
            'base_url': getattr(get_geoserver_manager(), 'base_url', '未配置'),
            'workspace': getattr(get_geoserver_manager(), 'workspace', '未配置'),
            'error': str(e)
        }

        return Response({
            'message': '获取GeoServer状态失败',
            'status': status_info,
            'error': str(e),
            'tips': {
                'error': '无法连接到GeoServer',
                'checklist': [
                    '确认GeoServer是否已安装并启动',
                    '检查URL是否正确（默认：http://localhost:8080/geoserver）',
                    '验证用户名和密码是否正确',
                    '查看后端日志了解更多信息'
                ]
            }
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_health(request):
    """Return deployment health checks for database, media storage and GeoServer."""
    checks = {}

    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        checks['database'] = {'ok': True, 'message': '数据库连接正常'}
    except Exception as exc:
        checks['database'] = {'ok': False, 'message': f'数据库连接失败: {exc}'}

    media_root = str(settings.MEDIA_ROOT)
    checks['media_root'] = {
        'ok': os.path.isdir(media_root) and os.access(media_root, os.W_OK),
        'path': media_root,
        'message': '媒体目录可写' if os.path.isdir(media_root) and os.access(media_root, os.W_OK) else '媒体目录不存在或不可写',
    }

    try:
        geoserver = get_geoserver_manager()
        capabilities = geoserver.get_wms_capabilities()
        workspace_ready = False
        if capabilities:
            try:
                workspace_ready = bool(geoserver.workspace_exists() or geoserver.create_workspace())
            except Exception:
                workspace_ready = False
        checks['geoserver'] = {
            'ok': bool(capabilities) and workspace_ready,
            'connected': bool(capabilities),
            'workspace_ready': workspace_ready,
            'workspace': geoserver.workspace,
            'base_url': geoserver.base_url,
            'message': 'GeoServer连接和工作空间正常' if capabilities and workspace_ready else 'GeoServer未连接或工作空间未就绪',
        }
    except Exception as exc:
        checks['geoserver'] = {'ok': False, 'message': f'GeoServer检测失败: {exc}'}

    layer_counts = {
        'total': BusinessLayer.objects.count(),
        'published': BusinessLayer.objects.filter(status='published').count(),
        'failed': BusinessLayer.objects.filter(status='failed').count(),
        'uploaded': BusinessLayer.objects.filter(status='uploaded').count(),
    }
    checks['business_layers'] = {
        'ok': layer_counts['failed'] == 0,
        'counts': layer_counts,
        'message': '业务图层状态正常' if layer_counts['failed'] == 0 else f"存在 {layer_counts['failed']} 个发布失败图层",
    }

    overall_ok = all(item.get('ok') for item in checks.values())
    return Response({
        'ok': overall_ok,
        'checked_at': timezone.now(),
        'checks': checks,
    }, status=status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE)
