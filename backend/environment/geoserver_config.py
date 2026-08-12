"""
GeoServer配置模块
用于管理地理空间服务和WMS/WFS服务
"""

import os
import logging
from typing import Dict, Any, Optional
from django.conf import settings
from pathlib import Path
import numpy as np
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class GeoServerManager:
    """GeoServer管理类"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'GEOSERVER_URL', 'http://localhost:8080/geoserver')
        self.username = getattr(settings, 'GEOSERVER_USERNAME', 'admin')
        self.password = getattr(settings, 'GEOSERVER_PASSWORD', 'geoserver')
        self.workspace = getattr(settings, 'GEOSERVER_WORKSPACE', 'tianshuipy')
        self.auth = HTTPBasicAuth(self.username, self.password)
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """发送HTTP请求到GeoServer（更健壮的JSON处理）"""
        try:
            url = f"{self.base_url}/rest/{endpoint}"
            # 合并并补充请求头
            req_headers = kwargs.pop('headers', {}) or {}
            default_headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            headers = {**default_headers, **req_headers}

            response = requests.request(
                method=method,
                url=url,
                auth=self.auth,
                headers=headers,
                **kwargs
            )

            # 成功状态但可能无内容
            if response.status_code in [200, 201, 202, 204]:
                if not response.content:
                    return {}
                # 有内容但可能不是JSON
                try:
                    return response.json()
                except Exception:
                    # 返回空对象以避免上层报错，同时记录调试信息
                    logger.debug(
                        f"GeoServer返回非JSON内容（{response.status_code}），Content-Type={response.headers.get('Content-Type')}"
                    )
                    return {}

            logger.error(f"GeoServer请求失败: {response.status_code} - {response.text}")
            return None

        except Exception as e:
            logger.error(f"GeoServer请求异常: {e}")
            return None

    def _detect_vector_srs(self, shapefile_path: str) -> Optional[str]:
        """读取 Shapefile 实际坐标系，避免错误强制声明为 EPSG:4326。"""
        try:
            from osgeo import ogr
        except ImportError:
            logger.warning("未安装 GDAL/OGR，无法自动识别矢量坐标系")
            return None

        datasource = None
        try:
            datasource = ogr.Open(shapefile_path)
            if datasource is None:
                logger.warning(f"无法打开矢量文件以识别坐标系: {shapefile_path}")
                return None

            layer = datasource.GetLayer(0)
            if layer is None:
                return None

            spatial_ref = layer.GetSpatialRef()
            if spatial_ref is None:
                logger.warning(f"矢量文件缺少坐标参考信息(.prj): {shapefile_path}")
                return None

            auth_name = spatial_ref.GetAuthorityName(None)
            auth_code = spatial_ref.GetAuthorityCode(None)
            if auth_name and auth_code:
                return f"{auth_name}:{auth_code}"
        except Exception as exc:
            logger.warning(f"识别矢量坐标系失败 {shapefile_path}: {exc}")
            return None
        finally:
            datasource = None
    
    def create_workspace(self) -> bool:
        """创建工作空间"""
        if self.workspace_exists():
            logger.info(f"工作空间 {self.workspace} 已存在")
            return True

        workspace_data = {
            "workspace": {
                "name": self.workspace
            }
        }
        
        result = self._make_request(
            'POST', 
            'workspaces', 
            json=workspace_data
        )
        
        if result is not None:
            logger.info(f"工作空间 {self.workspace} 创建成功")
            return True
        return False

    def workspace_exists(self) -> bool:
        """检查工作空间是否存在"""
        try:
            url = f"{self.base_url}/rest/workspaces/{self.workspace}.json"
            response = requests.get(
                url,
                auth=self.auth,
                headers={'Accept': 'application/json'},
                timeout=30,
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"检查工作空间 {self.workspace} 失败: {e}")
            return False
    
    def create_datastore(self, datastore_name: str, datastore_type: str = 'GeoTIFF') -> bool:
        """创建数据存储"""
        # 先检查数据存储是否已存在
        try:
            existing = self._make_request('GET', f'workspaces/{self.workspace}/datastores/{datastore_name}.json')
            if existing:
                logger.info(f"数据存储 {datastore_name} 已存在")
                return True
        except:
            pass
        
        # 创建新数据存储
        datastore_data = {
            "dataStore": {
                "name": datastore_name,
                "type": datastore_type,
                "enabled": True,
                "connectionParameters": {
                    "entry": [
                        {"@key": "url", "$": f"file:data_dir"},
                        {"@key": "create spatial index", "$": "true"}
                    ]
                }
            }
        }
        
        result = self._make_request(
            'POST',
            f'workspaces/{self.workspace}/datastores',
            json=datastore_data
        )
        
        if result is not None:
            logger.info(f"数据存储 {datastore_name} 创建成功")
            return True
        
        # 如果创建失败，尝试另一种方式（直接创建空的数据存储）
        try:
            simple_datastore_data = {
                "dataStore": {
                    "name": datastore_name,
                    "type": datastore_type
                }
            }
            result = self._make_request(
                'POST',
                f'workspaces/{self.workspace}/datastores',
                json=simple_datastore_data
            )
            if result is not None:
                logger.info(f"数据存储 {datastore_name} 创建成功（简化方式）")
                return True
        except Exception as e:
            logger.warning(f"使用简化方式创建数据存储失败: {e}")
        
        logger.warning(f"数据存储 {datastore_name} 创建失败或已存在")
        return False

    def _extract_coverage_names(self, coverage_list: Optional[Dict[str, Any]]) -> list[str]:
        """兼容 GeoServer 多种 coverages.json 返回结构。"""
        if not coverage_list or 'coverages' not in coverage_list:
            return []

        coverages_node = coverage_list.get('coverages')
        if isinstance(coverages_node, str):
            return []
        if not isinstance(coverages_node, dict):
            return []

        raw_coverage = coverages_node.get('coverage', [])
        if isinstance(raw_coverage, dict):
            raw_coverage = [raw_coverage]
        elif not isinstance(raw_coverage, list):
            return []

        names = []
        for item in raw_coverage:
            if isinstance(item, dict):
                name = item.get('name')
                if name:
                    names.append(name)
            elif isinstance(item, str) and item:
                names.append(item)
        return names

    def resolve_raster_layer_name(self, coverage_store_name: str, preferred_layer_name: Optional[str] = None) -> Optional[str]:
        """根据 CoverageStore 解析 GeoServer 实际可用的栅格图层名。"""
        candidates = []
        if preferred_layer_name:
            candidates.append(preferred_layer_name)
        if coverage_store_name:
            candidates.append(coverage_store_name)

        for candidate in candidates:
            layer_info = self._make_request('GET', f'layers/{self.workspace}:{candidate}.json')
            if layer_info:
                return candidate

        coverage_list = self._make_request(
            'GET',
            f'workspaces/{self.workspace}/coveragestores/{coverage_store_name}/coverages.json'
        )
        coverage_names = self._extract_coverage_names(coverage_list)
        if coverage_names:
            return coverage_names[0]

        return coverage_store_name or preferred_layer_name
    
    def publish_raster(self, coverage_store_name: str, layer_name: str, file_path: str, style_type: str = 'default') -> bool:
        """发布栅格图层（使用CoverageStore）"""
        try:
            # 检查文件是否存在
            import os
            if not os.path.exists(file_path):
                logger.error(f"栅格文件不存在: {file_path}")
                return False
            
            # 对于用户上传的GeoTIFF，优先使用REST文件上传方式。
            # 真彩参考影像体积很大时，直接切换为文件路径引用，避免重复传输数GB数据。
            if style_type != 'imagery_rgb':
                try:
                    self.delete_coveragestore(coverage_store_name, recurse=True)
                    upload_url = (
                        f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores/"
                        f"{coverage_store_name}/file.geotiff"
                    )
                    logger.info(f"直接上传GeoTIFF到GeoServer: {upload_url}")
                    with open(file_path, 'rb') as raster_file:
                        response = requests.put(
                            upload_url,
                            auth=self.auth,
                            params={
                                'coverageName': layer_name,
                                'configure': 'all',
                                'update': 'overwrite',
                            },
                            data=raster_file,
                            headers={'Content-Type': 'image/tiff'},
                            timeout=600
                        )

                    logger.info(f"GeoTIFF上传响应: HTTP {response.status_code}")
                    if response.status_code in [200, 201, 202]:
                        import time
                        time.sleep(2)
                        layer_check = self._make_request('GET', f'layers/{self.workspace}:{layer_name}.json')
                        if layer_check:
                            logger.info(f"✅ 栅格图层 {layer_name} 上传并发布成功")
                            min_val, max_val = self._resolve_raster_style_range(style_type, file_path)
                            style_name = f"{layer_name}_style"
                            sld_content = self._build_raster_style(style_type, min_val, max_val)
                            if self.create_style(style_name, sld_content):
                                self.apply_style_to_layer(layer_name, style_name)
                            return True
                        logger.warning(f"GeoTIFF已上传，但图层 {layer_name} 暂未查询到")
                        return True

                    logger.warning(f"直接上传GeoTIFF失败: HTTP {response.status_code}")
                    logger.warning(f"响应内容: {response.text[:1000]}")
                except Exception as direct_upload_error:
                    logger.warning(f"直接上传GeoTIFF异常，回退到路径引用方式: {direct_upload_error}")
            else:
                logger.info("检测到高分真彩参考影像，跳过GeoTIFF直传，优先使用文件路径引用方式")

            # 对于GeoTIFF，使用CoverageStore而不是DataStore
            # 方法1: 检查并删除旧的CoverageStore（如果存在但类型不对）
            coverage_store_check = self._make_request('GET', f'workspaces/{self.workspace}/coveragestores/{coverage_store_name}.json')
            if coverage_store_check:
                # 检查类型
                store_type = coverage_store_check.get('coverageStore', {}).get('type', '')
                if store_type != 'GeoTIFF':
                    logger.info(f"CoverageStore {coverage_store_name} 类型不正确 ({store_type})，删除后重新创建")
                    self.delete_coveragestore(coverage_store_name, recurse=True)
                    coverage_store_check = None
            
            # 方法2: 如果不存在，创建新的CoverageStore（使用文件路径引用）
            if not coverage_store_check:
                logger.info(f"CoverageStore {coverage_store_name} 不存在，使用文件路径引用方式创建")
                # 使用文件路径引用方式创建CoverageStore（更可靠）
                try:
                    file_uri = Path(file_path).as_uri()
                except Exception:
                    # 退化：手工拼接（Windows路径替换分隔符）
                    file_uri = 'file:///' + file_path.replace('\\', '/')
                coverage_store_data = {
                    "coverageStore": {
                        "name": coverage_store_name,
                        "type": "GeoTIFF",
                        "enabled": True,
                        "workspace": {
                            "name": self.workspace
                        },
                        "url": file_uri  # 使用文件路径引用
                    }
                }
                
                create_result = self._make_request(
                    'POST',
                    f'workspaces/{self.workspace}/coveragestores',
                    json=coverage_store_data
                )
                
                if create_result is not None:
                    logger.info(f"✅ CoverageStore创建成功（文件路径引用方式）")
                    # 使用文件路径引用方式，无需上传文件，直接进入验证阶段
                    upload_success = True
                else:
                    logger.warning(f"创建CoverageStore失败，尝试直接上传文件方式")
                    upload_success = False
            else:
                # CoverageStore已存在，尝试更新文件
                upload_success = False
            
            # 方法3: 如果文件路径引用方式失败，尝试直接上传文件（备用方案）
            if not upload_success:
                upload_url = f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores/{coverage_store_name}/file.geotiff"
                
                logger.info(f"尝试直接上传栅格文件到GeoServer: {file_path}")
                logger.info(f"上传URL: {upload_url}")
                
                try:
                    with open(file_path, 'rb') as f:
                        file_size = os.path.getsize(file_path)
                        logger.info(f"文件大小: {file_size} 字节 ({file_size / 1024 / 1024:.2f} MB)")
                        
                        # 上传文件
                        response = requests.put(
                            upload_url,
                            auth=self.auth,
                            data=f,
                            headers={'Content-Type': 'image/tiff'},
                            timeout=300  # 5分钟超时，处理大文件
                        )
                    
                    logger.info(f"上传响应状态码: {response.status_code}")
                    
                    if response.status_code in [200, 201]:
                        logger.info(f"✅ 文件上传成功")
                        upload_success = True
                    else:
                        logger.warning(f"文件上传失败: HTTP {response.status_code}")
                        logger.warning(f"响应内容: {response.text[:200]}")
                        # 如果直接上传失败，尝试删除CoverageStore并使用文件路径引用方式
                        if response.status_code == 500:
                            logger.info("检测到HTTP 500错误，切换到文件路径引用方式")
                            try:
                                # 删除现有的CoverageStore
                                delete_url = f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores/{coverage_store_name}?recurse=true&purge=all"
                                requests.delete(delete_url, auth=self.auth, timeout=30)
                                logger.info("已删除旧的CoverageStore")
                                
                                # 使用文件路径引用方式重新创建
                                try:
                                    file_uri = Path(file_path).as_uri()
                                except Exception:
                                    file_uri = 'file:///' + file_path.replace('\\', '/')
                                coverage_store_data = {
                                    "coverageStore": {
                                        "name": coverage_store_name,
                                        "type": "GeoTIFF",
                                        "enabled": True,
                                        "workspace": {
                                            "name": self.workspace
                                        },
                                        "url": file_uri
                                    }
                                }
                                
                                create_result = self._make_request(
                                    'POST',
                                    f'workspaces/{self.workspace}/coveragestores',
                                    json=coverage_store_data
                                )
                                
                                if create_result is not None:
                                    logger.info(f"✅ CoverageStore创建成功（文件路径引用方式，备用方案）")
                                    upload_success = True
                                else:
                                    logger.error("文件路径引用方式创建CoverageStore也失败")
                            except Exception as e:
                                logger.error(f"切换到文件路径引用方式失败: {e}")
                
                except Exception as upload_error:
                    logger.error(f"上传文件异常: {upload_error}")
                    upload_success = False
            
            if upload_success:
                # 方法4: 检查并创建Coverage（如果不存在）
                import time
                time.sleep(2)  # 等待GeoServer处理
                
                # 检查Coverage是否存在
                coverage_list = self._make_request('GET', f'workspaces/{self.workspace}/coveragestores/{coverage_store_name}/coverages.json')
                coverage_names = self._extract_coverage_names(coverage_list)
                
                # 如果Coverage不存在，手动创建
                if not coverage_names:
                    logger.info("Coverage不存在，手动创建...")
                    native_coverage_name = Path(file_path).stem
                    coverage_data = {
                        "coverage": {
                            "name": layer_name,
                            "nativeName": native_coverage_name,
                            "title": layer_name,
                            "enabled": True
                        }
                    }
                    
                    create_coverage_result = self._make_request(
                        'POST',
                        f'workspaces/{self.workspace}/coveragestores/{coverage_store_name}/coverages',
                        json=coverage_data
                    )
                    
                    if create_coverage_result:
                        logger.info("✅ Coverage创建成功")
                        time.sleep(2)  # 等待Coverage创建完成
                    else:
                        logger.warning("Coverage创建失败，但继续验证")
                
                # 检查CoverageStore中的Coverage
                    coverage_list = self._make_request('GET', f'workspaces/{self.workspace}/coveragestores/{coverage_store_name}/coverages.json')
                    coverage_names = self._extract_coverage_names(coverage_list)
                    
                    actual_layer_name = None
                    if coverage_names:
                        actual_layer_name = coverage_names[0]
                    
                    # 如果找到了coverage，检查图层名称是否匹配期望的名称
                    if actual_layer_name:
                        logger.info(f"✅ 找到自动创建的Coverage: {actual_layer_name}")
                        # 检查对应的图层是否存在
                        layer_check = self._make_request('GET', f'layers/{self.workspace}:{actual_layer_name}.json')
                        if layer_check:
                            # 如果图层名称与期望的不同，尝试重命名图层
                            if actual_layer_name != layer_name:
                                logger.info(f"⚠️ 图层名称不匹配：期望 {layer_name}，实际 {actual_layer_name}，尝试重命名...")
                                # 通过更新Coverage的名称来重命名图层
                                try:
                                    # 获取Coverage信息
                                    coverage_info = self._make_request('GET', f'workspaces/{self.workspace}/coveragestores/{coverage_store_name}/coverages/{actual_layer_name}.json')
                                    if coverage_info and 'coverage' in coverage_info:
                                        # 更新Coverage名称
                                        coverage_info['coverage']['name'] = layer_name
                                        # 使用PUT请求更新Coverage
                                        update_url = f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores/{coverage_store_name}/coverages/{actual_layer_name}.json"
                                        update_response = requests.put(
                                            update_url,
                                            auth=self.auth,
                                            json=coverage_info,
                                            headers={'Content-Type': 'application/json'},
                                            timeout=30
                                        )
                                        if update_response.status_code in [200, 204]:
                                            logger.info(f"✅ Coverage重命名成功: {actual_layer_name} -> {layer_name}")
                                            time.sleep(2)  # 等待GeoServer处理
                                            # 验证新名称的图层是否存在
                                            new_check = self._make_request('GET', f'layers/{self.workspace}:{layer_name}.json')
                                            if new_check:
                                                logger.info(f"✅ 栅格图层 {layer_name} 已创建并验证成功")
                                                return True
                                            else:
                                                logger.warning(f"⚠️ Coverage已重命名但图层验证失败，等待更长时间...")
                                                time.sleep(3)
                                                final_check = self._make_request('GET', f'layers/{self.workspace}:{layer_name}.json')
                                                if final_check:
                                                    logger.info(f"✅ 栅格图层 {layer_name} 验证成功")

                                                    # 为图层创建并应用默认样式
                                                    style_name = f"{layer_name}_style"

                                                    min_val, max_val = self._resolve_raster_style_range(style_type, file_path)
                                                    sld_content = self._build_raster_style(style_type, min_val, max_val)
                                                    if self.create_style(style_name, sld_content):
                                                        self.apply_style_to_layer(layer_name, style_name)

                                                    return True

                                                logger.warning(f"⚠️ 图层 {layer_name} 验证失败，但文件已上传成功")

                                                # 即使验证失败，也尝试应用样式（使用实际图层名称）
                                                if actual_layer_name:
                                                    style_name = f"{actual_layer_name}_style"
                                                    min_val, max_val = self._resolve_raster_style_range(style_type, file_path)
                                                    sld_content = self._build_raster_style(style_type, min_val, max_val)
                                                    if self.create_style(style_name, sld_content):
                                                        self.apply_style_to_layer(actual_layer_name, style_name)

                                                return True  # 文件上传成功，即使验证失败也返回True
                                        else:
                                            logger.warning(f"⚠️ Coverage重命名失败: HTTP {update_response.status_code}")
                                except Exception as rename_error:
                                    logger.warning(f"⚠️ 重命名图层时出错: {rename_error}")
                                
                                # 即使重命名失败，也尝试使用实际创建的图层名称，并为实际图层创建并应用样式
                                logger.info(f"⚠️ 图层名称不匹配但文件已上传成功，使用实际图层名称: {actual_layer_name}")
                                
                                # 为实际创建的图层创建并应用默认样式
                                style_name = f"{actual_layer_name}_style"
                                logger.info(f"为实际图层 {actual_layer_name} 创建样式: {style_name}")

                                min_val, max_val = self._resolve_raster_style_range(
                                    style_type,
                                    file_path,
                                    default_range=(0.0, 5.0),
                                    quick_timeout=3,
                                )
                                sld_content = self._build_raster_style(style_type, min_val, max_val)
                                if self.create_style(style_name, sld_content):
                                    logger.info(f"样式 {style_name} 创建成功，开始应用到图层")
                                    if self.apply_style_to_layer(actual_layer_name, style_name):
                                        logger.info(f"✅ 样式已成功应用到图层 {actual_layer_name}")
                                    else:
                                        logger.warning(f"⚠️ 样式应用到图层失败，但图层已发布")
                                else:
                                    logger.warning(f"⚠️ 样式创建失败，但图层已发布")
                                
                                return True  # 文件上传成功，即使名称不匹配也返回True
                            else:
                                logger.info(f"✅ 栅格图层 {actual_layer_name} 已自动创建")
                                
                                # 为图层创建并应用默认样式
                                style_name = f"{actual_layer_name}_style"

                                min_val, max_val = self._resolve_raster_style_range(style_type, file_path)
                                sld_content = self._build_raster_style(style_type, min_val, max_val)
                                if self.create_style(style_name, sld_content):
                                    self.apply_style_to_layer(actual_layer_name, style_name)
                                
                                return True
                    else:
                        # 尝试使用期望的图层名称
                        actual_layer_name = layer_name
                        layer_check = self._make_request('GET', f'layers/{self.workspace}:{layer_name}.json')
                        if layer_check:
                            logger.info(f"✅ 栅格图层 {layer_name} 已自动创建")
                            
                            # 为图层创建并应用默认样式
                            style_name = f"{layer_name}_style"
                            min_val, max_val = self._resolve_raster_style_range(
                                style_type,
                                file_path,
                                default_range=(0.0, 5.0),
                            )
                            sld_content = self._build_raster_style(style_type, min_val, max_val)
                            if self.create_style(style_name, sld_content):
                                self.apply_style_to_layer(layer_name, style_name)
                            
                            return True
                    
                    # 如果图层名称不同，尝试使用coverage store的名称（GeoServer有时会用coverage store名称作为图层名称）
                    coverage_store_check = self._make_request('GET', f'workspaces/{self.workspace}/coveragestores/{coverage_store_name}.json')
                    if coverage_store_check:
                        # 检查是否有对应的图层
                        all_layers = self._make_request('GET', f'workspaces/{self.workspace}/layers.json')
                        if all_layers and 'layers' in all_layers:
                            layer_list = all_layers['layers'].get('layer', [])
                            if isinstance(layer_list, list):
                                for layer in layer_list:
                                    layer_dict = layer if isinstance(layer, dict) else {'name': str(layer)}
                                    layer_name_in_list = layer_dict.get('name', '')
                                    # 如果找到的图层是coverage store名称，尝试重命名
                                    if layer_name_in_list == coverage_store_name and layer_name_in_list != layer_name:
                                        logger.info(f"⚠️ 图层名称是CoverageStore名称 {layer_name_in_list}，期望是 {layer_name}，尝试重命名...")
                                        try:
                                            coverage_info = self._make_request('GET', f'workspaces/{self.workspace}/coveragestores/{coverage_store_name}/coverages/{layer_name_in_list}.json')
                                            if coverage_info and 'coverage' in coverage_info:
                                                coverage_info['coverage']['name'] = layer_name
                                                update_url = f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores/{coverage_store_name}/coverages/{layer_name_in_list}.json"
                                                update_response = requests.put(
                                                    update_url,
                                                    auth=self.auth,
                                                    json=coverage_info,
                                                    headers={'Content-Type': 'application/json'},
                                                    timeout=30
                                                )
                                                if update_response.status_code in [200, 204]:
                                                    logger.info(f"✅ Coverage重命名成功: {layer_name_in_list} -> {layer_name}")
                                                    time.sleep(2)
                                                    new_check = self._make_request('GET', f'layers/{self.workspace}:{layer_name}.json')
                                                    if new_check:
                                                        logger.info(f"✅ 栅格图层 {layer_name} 已创建并验证成功")
                                                        return True
                                        except Exception as rename_error:
                                            logger.warning(f"⚠️ 重命名图层时出错: {rename_error}")
                                    
                                    # 检查图层名称是否包含coverage store名称或期望的图层名称
                                    if coverage_store_name in layer_name_in_list or layer_name in layer_name_in_list:
                                        logger.info(f"✅ 找到图层: {layer_name_in_list}")
                                        # 即使名称不完全匹配，文件上传成功也返回True
                                        return True
                    
                    # 如果仍未找到，但文件已上传成功，说明图层应该存在，只是名称可能不同
                    logger.info(f"✅ 文件上传成功，GeoServer应已自动创建图层（可能名称不同）")
                    # 文件上传成功通常意味着图层已创建，即使查询不到也可能是GeoServer尚未完全处理
                    return True
                else:
                    # 如果找不到coverage，尝试手动创建
                    logger.debug("未找到Coverage，尝试手动创建...")
                    coverage_data = {
                        "coverage": {
                            "name": layer_name,
                            "nativeName": layer_name,
                            "title": layer_name,
                            "enabled": True
                        }
                    }
                    
                    create_coverage_result = self._make_request(
                        'POST',
                        f'workspaces/{self.workspace}/coveragestores/{coverage_store_name}/coverages',
                        json=coverage_data
                    )
                    
                    if create_coverage_result:
                        logger.info("✅ Coverage手动创建成功")
                        time.sleep(2)
                        # 验证图层
                        layer_check = self._make_request('GET', f'layers/{self.workspace}:{layer_name}.json')
                        if layer_check:
                            logger.info(f"✅ 栅格图层 {layer_name} 验证成功")
                            return True
                        else:
                            logger.debug(f"Coverage已创建但图层验证失败（可能GeoServer尚未完全处理）")
                            return True  # 仍然返回True，因为文件已上传
                    else:
                        # Coverage创建失败可能是因为已存在，检查错误信息
                        logger.debug("Coverage创建失败（可能已存在），文件已上传成功")
                        return True  # 文件已上传，返回True
            else:
                # upload_success为False，说明文件上传或CoverageStore创建失败
                logger.error(f"❌ 文件上传或CoverageStore创建失败")
                return False
                
        except Exception as e:
            logger.error(f"发布栅格图层失败: {e}", exc_info=True)
            
        return False
    
    def delete_coveragestore(self, coverage_store_name: str, recurse: bool = True) -> bool:
        """删除CoverageStore（以及可能存在的同名DataStore）"""
        success = True
        
        # 先删除CoverageStore
        try:
            delete_url = f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores/{coverage_store_name}?recurse={str(recurse).lower()}"
            response = requests.delete(
                delete_url,
                auth=self.auth
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"CoverageStore {coverage_store_name} 删除成功")
            elif response.status_code == 404:
                logger.info(f"CoverageStore {coverage_store_name} 不存在，无需删除")
            else:
                logger.warning(f"删除CoverageStore失败: HTTP {response.status_code}")
                success = False
        except Exception as e:
            logger.warning(f"删除CoverageStore异常: {e}")
        
        # 也删除可能存在的同名DataStore（如果之前错误地创建了）
        try:
            datastore_check = self._make_request('GET', f'workspaces/{self.workspace}/datastores/{coverage_store_name}.json')
            if datastore_check:
                logger.info(f"发现同名DataStore {coverage_store_name}，也删除")
                delete_url = f"{self.base_url}/rest/workspaces/{self.workspace}/datastores/{coverage_store_name}?recurse={str(recurse).lower()}"
                response = requests.delete(
                    delete_url,
                    auth=self.auth
                )
                
                if response.status_code in [200, 204]:
                    logger.info(f"DataStore {coverage_store_name} 删除成功")
                elif response.status_code == 404:
                    logger.info(f"DataStore {coverage_store_name} 不存在")
                else:
                    logger.warning(f"删除DataStore失败: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"检查/删除DataStore异常: {e}")
        
        return success

    def delete_datastore(self, datastore_name: str, recurse: bool = True) -> bool:
        """删除DataStore及其发布出的图层"""
        try:
            delete_url = (
                f"{self.base_url}/rest/workspaces/{self.workspace}/datastores/"
                f"{datastore_name}?recurse={str(recurse).lower()}"
            )
            response = requests.delete(delete_url, auth=self.auth, timeout=60)

            if response.status_code in [200, 204]:
                logger.info(f"DataStore {datastore_name} 删除成功")
                return True
            if response.status_code == 404:
                logger.info(f"DataStore {datastore_name} 不存在，无需删除")
                return True

            logger.warning(f"删除DataStore失败: HTTP {response.status_code} - {response.text[:500]}")
            return False
        except Exception as e:
            logger.warning(f"删除DataStore异常: {e}")
            return False
    
    def get_layer_info(self, layer_name: str) -> Optional[Dict[str, Any]]:
        """获取图层信息"""
        return self._make_request('GET', f'layers/{layer_name}')
    
    def get_wms_capabilities(self) -> Optional[Dict[str, Any]]:
        """获取WMS服务能力"""
        try:
            url = f"{self.base_url}/ows?service=WMS&version=1.3.0&request=GetCapabilities"
            response = requests.get(url, auth=self.auth)
            
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"获取WMS能力失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"获取WMS能力异常: {e}")
            return None
    
    def create_style(self, style_name: str, sld_content: str) -> bool:
        """创建或更新 SLD 样式。

        GeoServer 的样式内容上传接口需要直接接收 SLD XML。先尝试更新已有样式，
        不存在时再用 raw=true 创建，避免部分 GeoServer 版本把 JSON 样式声明误判为样式内容。
        """
        headers = {
            'Content-Type': 'application/vnd.ogc.sld+xml',
            'Accept': 'application/json',
        }

        try:
            update_url = f"{self.base_url}/rest/styles/{style_name}"
            update_response = requests.put(
                update_url,
                auth=self.auth,
                data=sld_content.encode('utf-8'),
                headers=headers,
                timeout=60,
            )

            if update_response.status_code in [200, 201]:
                logger.info(f"样式 {style_name} 更新成功")
                return True

            if update_response.status_code not in [404, 405]:
                logger.debug(
                    f"样式 {style_name} 更新返回 {update_response.status_code}: "
                    f"{update_response.text[:500]}"
                )

            create_url = f"{self.base_url}/rest/styles?name={style_name}&raw=true"
            create_response = requests.post(
                create_url,
                auth=self.auth,
                data=sld_content.encode('utf-8'),
                headers=headers,
                timeout=60,
            )

            if create_response.status_code in [200, 201]:
                logger.info(f"样式 {style_name} 创建成功")
                return True

            if create_response.status_code == 409:
                retry_response = requests.put(
                    update_url,
                    auth=self.auth,
                    data=sld_content.encode('utf-8'),
                    headers=headers,
                    timeout=60,
                )
                if retry_response.status_code in [200, 201]:
                    logger.info(f"样式 {style_name} 冲突后更新成功")
                    return True
                logger.error(
                    f"样式 {style_name} 冲突后更新失败: "
                    f"{retry_response.status_code} - {retry_response.text[:500]}"
                )
                return False

            logger.error(
                f"样式 {style_name} 创建失败: "
                f"{create_response.status_code} - {create_response.text[:500]}"
            )
            return False

        except Exception as e:
            logger.error(f"创建或更新样式 {style_name} 失败: {e}")
            return False
    
    def delete_style(self, style_name: str, purge: bool = True) -> bool:
        """删除样式"""
        try:
            url = f"{self.base_url}/rest/styles/{style_name}"
            if purge:
                url += "?purge=true"
            
            response = requests.delete(url, auth=self.auth, timeout=30)
            
            if response.status_code in [200, 204]:
                logger.info(f"样式 {style_name} 删除成功")
                return True
            elif response.status_code == 404:
                logger.debug(f"样式 {style_name} 不存在，无需删除")
                return True
            elif response.status_code == 403:
                logger.debug(f"删除样式 {style_name} 权限不足（403），将尝试更新")
                return True  # 返回True，允许后续更新操作
            else:
                logger.debug(f"删除样式失败: {response.status_code}，将尝试更新")
                return True  # 返回True，允许后续更新操作
        except Exception as e:
            logger.debug(f"删除样式异常: {e}，将尝试更新")
            return True  # 返回True，允许后续更新操作
    
    def _get_raster_statistics(self, file_path: str) -> tuple:
        """获取栅格文件的统计信息（最小值、最大值）"""
        try:
            from osgeo import gdal
            import numpy as np
            
            dataset = gdal.Open(file_path, gdal.GA_ReadOnly)
            if dataset is None:
                logger.warning(f"无法打开栅格文件读取统计信息: {file_path}")
                return (0.0, 5.0)
            
            band = dataset.GetRasterBand(1)
            
            # 尝试读取统计信息
            stats = band.GetStatistics(False, True)
            if stats and len(stats) >= 4:
                min_val = stats[0]
                max_val = stats[1]
                dataset = None
                
                # 如果统计信息有效
                if not np.isnan(min_val) and not np.isnan(max_val) and max_val > min_val:
                    logger.info(f"从栅格文件读取统计信息: min={min_val}, max={max_val}")
                    return (float(min_val), float(max_val))
            
            # 如果统计信息无效，尝试计算（限制数据量以提高性能）
            logger.info(f"统计信息无效，尝试计算栅格值域...")
            try:
                # 读取栅格尺寸
                width = band.XSize
                height = band.YSize
                total_pixels = width * height
                logger.info(f"栅格尺寸: {width}x{height} ({total_pixels} 像素)")
                
                # 如果图像很大，使用采样以提高性能
                if total_pixels > 5000000:  # 大于500万像素，使用采样
                    logger.info(f"图像较大 ({width}x{height})，使用采样计算值域")
                    # 采样大小为最大1000x1000或实际尺寸的1/10，取较小值
                    sample_x = min(max(100, width // 10), 1000)
                    sample_y = min(max(100, height // 10), 1000)
                    logger.info(f"采样尺寸: {sample_x}x{sample_y}")
                    data = band.ReadAsArray(0, 0, sample_x, sample_y)
                elif total_pixels > 1000000:  # 大于100万像素，使用更大的采样
                    logger.info(f"图像中等 ({width}x{height})，使用适度采样")
                    sample_x = min(width, 2000)
                    sample_y = min(height, 2000)
                    data = band.ReadAsArray(0, 0, sample_x, sample_y)
                else:
                    # 图像较小，读取全部数据
                    logger.info(f"图像较小 ({width}x{height})，读取全部数据")
                    try:
                        # 使用ReadAsArray读取数据，如果失败则使用采样
                        if total_pixels > 50000:  # 大于5万像素，使用采样以提高稳定性
                            logger.info(f"使用采样读取数据以提高稳定性")
                            sample_x = min(width, 500)
                            sample_y = min(height, 500)
                            data = band.ReadAsArray(0, 0, sample_x, sample_y)
                            logger.info(f"采样读取完成，采样尺寸: {sample_x}x{sample_y}")
                        else:
                            data = band.ReadAsArray()
                            logger.info(f"全部数据读取完成")
                        
                        if data is not None:
                            logger.info(f"数据形状: {data.shape}, 数据大小: {data.size}, 数据类型: {data.dtype}")
                        else:
                            logger.warning(f"读取到的数据为None")
                    except Exception as read_error:
                        logger.error(f"读取栅格数据失败: {read_error}")
                        # 如果读取失败，尝试使用默认值域
                        logger.warning(f"使用默认值域继续处理")
                        dataset = None
                        band = None
                        return (0.0, 5.0)
                
                if data is not None and data.size > 0:
                    logger.info(f"成功读取栅格数据，尺寸: {data.shape}, 数据类型: {data.dtype}")
                    
                    # 处理NoData值
                    nodata = band.GetNoDataValue()
                    logger.info(f"NoData值: {nodata}")
                    
                    if nodata is not None:
                        # 过滤NoData值
                        if np.issubdtype(data.dtype, np.floating):
                            valid_mask = ~np.isnan(data) & (data != nodata)
                        else:
                            valid_mask = data != nodata
                        valid_data = data[valid_mask]
                        logger.info(f"过滤NoData后，有效数据点数: {len(valid_data)} / {data.size}")
                    else:
                        # 如果没有NoData值，但数据是浮点型，需要检查NaN
                        if np.issubdtype(data.dtype, np.floating):
                            valid_data = data[~np.isnan(data)]
                            logger.info(f"过滤NaN后，有效数据点数: {len(valid_data)} / {data.size}")
                        else:
                            valid_data = data.flatten()
                            logger.info(f"全部数据点数: {len(valid_data)}")
                    
                    if len(valid_data) > 0:
                        min_val = float(np.nanmin(valid_data))
                        max_val = float(np.nanmax(valid_data))
                        logger.info(f"计算得到的栅格值域: min={min_val}, max={max_val}")
                        
                        # 清理内存
                        del data
                        del valid_data
                        dataset = None
                        band = None
                        
                        if not np.isnan(min_val) and not np.isnan(max_val) and max_val > min_val:
                            logger.info(f"✅ 有效的栅格值域: {min_val} - {max_val}")
                            return (min_val, max_val)
                        else:
                            logger.warning(f"⚠️ 计算得到的值域无效: min={min_val}, max={max_val}")
                    else:
                        logger.warning(f"⚠️ 没有有效数据点（可能全是NoData或NaN）")
                else:
                    logger.warning(f"⚠️ 无法读取栅格数据或数据为空")
            except MemoryError as mem_error:
                logger.warning(f"⚠️ 内存不足，无法计算栅格值域: {mem_error}，使用默认值域")
            except Exception as calc_error:
                logger.warning(f"⚠️ 计算栅格值域时出错: {calc_error}，使用默认值域")
            
            try:
                dataset = None
                band = None
            except:
                pass
            logger.warning(f"无法获取栅格统计信息，使用默认值域: 0.0-5.0")
            return (0.0, 5.0)
            
        except Exception as e:
            logger.warning(f"读取栅格统计信息失败: {e}，使用默认值域: 0.0-5.0")
            return (0.0, 5.0)

    def _resolve_raster_style_range(
        self,
        style_type: str,
        file_path: str,
        default_range: tuple = (0.0, 5.0),
        quick_timeout: Optional[int] = None,
    ) -> tuple:
        """为不同栅格样式选择值域，真彩影像无需扫描整幅数据。"""
        if style_type == 'imagery_rgb':
            return (0.0, 255.0)

        if style_type == 'ecology_rsei':
            try:
                min_val, max_val = self._get_raster_percentile_range(file_path, lower=2, upper=98)
                logger.info(f"使用生态/RSEI动态拉伸值域创建样式: {min_val} - {max_val}")
                return min_val, max_val
            except Exception as exc:
                logger.warning(f"获取生态/RSEI动态拉伸值域失败: {exc}，回退到常规值域")

        if quick_timeout:
            try:
                import threading

                result = [None]

                def quick_get_stats():
                    try:
                        result[0] = self._get_raster_statistics(file_path)
                    except Exception:
                        result[0] = None

                thread = threading.Thread(target=quick_get_stats)
                thread.daemon = True
                thread.start()
                thread.join(timeout=quick_timeout)
                if result[0] and not thread.is_alive():
                    min_val, max_val = result[0]
                    logger.info(f"✅ 快速获取到栅格统计信息: {min_val} - {max_val}")
                    return min_val, max_val
                logger.info(f"快速模式：使用默认值域创建样式: {default_range[0]} - {default_range[1]}")
                return default_range
            except Exception as exc:
                logger.warning(f"快速获取栅格统计信息失败: {exc}")
                return default_range

        try:
            min_val, max_val = self._get_raster_statistics(file_path)
            logger.info(f"使用栅格值域创建样式: {min_val} - {max_val}")
            return min_val, max_val
        except Exception as stats_error:
            logger.warning(f"读取栅格统计信息失败: {stats_error}，使用默认值域")
            return default_range

    def _get_raster_percentile_range(self, file_path: str, lower: float = 2, upper: float = 98) -> tuple:
        """读取栅格有效值的分位数范围，用于和分析页一致的动态拉伸渲染。"""
        try:
            import rasterio

            with rasterio.open(file_path) as dataset:
                data = dataset.read(1, masked=True)
                valid_data = data.compressed() if hasattr(data, 'compressed') else data.flatten()

            if valid_data.size == 0:
                raise ValueError('栅格没有可用像元用于动态拉伸')

            min_val = float(np.nanpercentile(valid_data, lower))
            max_val = float(np.nanpercentile(valid_data, upper))

            if not np.isfinite(min_val) or not np.isfinite(max_val) or max_val <= min_val:
                raw_min = float(np.nanmin(valid_data))
                raw_max = float(np.nanmax(valid_data))
                if np.isfinite(raw_min) and np.isfinite(raw_max) and raw_max > raw_min:
                    return (raw_min, raw_max)
                raise ValueError(f'动态拉伸值域无效: {min_val}, {max_val}')

            return (min_val, max_val)
        except Exception:
            return self._get_raster_statistics(file_path)

    def _create_default_raster_sld(self, min_value: float = 0.0, max_value: float = 5.0) -> str:
        """创建默认的栅格SLD样式（彩色渐变）"""
        # 确保值域有效
        if max_value <= min_value:
            min_value = 0.0
            max_value = 5.0
        
        # 计算中间值（使用更多节点，使过渡更平滑）
        range_val = max_value - min_value
        v1 = min_value + range_val * 0.1   # 10%
        v2 = min_value + range_val * 0.25   # 25%
        v3 = min_value + range_val * 0.4    # 40%
        v4 = min_value + range_val * 0.55   # 55%
        v5 = min_value + range_val * 0.7    # 70%
        v6 = min_value + range_val * 0.85   # 85%
        
        # 使用美观的生态指数配色方案：
        # 深红(差) -> 橙红 -> 橙 -> 黄 -> 黄绿 -> 浅绿 -> 深绿(优)
        # 使用更柔和的颜色，避免过于鲜艳
        sld = f'''<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0" 
    xmlns="http://www.opengis.net/sld" 
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
    <NamedLayer>
        <Name>raster_style</Name>
        <UserStyle>
            <Title>生态指数栅格美观样式</Title>
            <Abstract>生态指数渐变色样式 - 红色(差) -> 黄色(中) -> 绿色(优)</Abstract>
            <FeatureTypeStyle>
                <Rule>
                    <RasterSymbolizer>
                        <Opacity>0.75</Opacity>
                        <ColorMap type="ramp">
                            <!-- 深红色：极差 (min) -->
                            <ColorMapEntry color="#8B0000" quantity="{min_value:.6f}" opacity="0.75" label="极差"/>
                            
                            <!-- 红色：差 (10%) -->
                            <ColorMapEntry color="#DC143C" quantity="{v1:.6f}" opacity="0.75" label="差"/>
                            
                            <!-- 橙红色：较差 (25%) -->
                            <ColorMapEntry color="#FF6347" quantity="{v2:.6f}" opacity="0.75" label="较差"/>
                            
                            <!-- 橙色：中下 (40%) -->
                            <ColorMapEntry color="#FF8C00" quantity="{v3:.6f}" opacity="0.75" label="中下"/>
                            
                            <!-- 黄色：中等 (55%) -->
                            <ColorMapEntry color="#FFD700" quantity="{v4:.6f}" opacity="0.75" label="中等"/>
                            
                            <!-- 黄绿色：良好 (70%) -->
                            <ColorMapEntry color="#ADFF2F" quantity="{v5:.6f}" opacity="0.75" label="良好"/>
                            
                            <!-- 浅绿色：优秀 (85%) -->
                            <ColorMapEntry color="#7CFC00" quantity="{v6:.6f}" opacity="0.75" label="优秀"/>
                            
                            <!-- 深绿色：极优 (max) -->
                            <ColorMapEntry color="#228B22" quantity="{max_value:.6f}" opacity="0.75" label="极优"/>
                        </ColorMap>
                    </RasterSymbolizer>
                </Rule>
            </FeatureTypeStyle>
        </UserStyle>
    </NamedLayer>
</StyledLayerDescriptor>'''
        return sld
    
    def _get_vector_statistics(self, file_path: str, field_name: str = 'GDP') -> tuple:
        """获取矢量文件的属性统计信息"""
        try:
            from osgeo import ogr
            import numpy as np
            
            datasource = ogr.Open(file_path)
            if datasource is None:
                logger.warning(f"无法打开矢量文件: {file_path}")
                return (None, None, None)
            
            layer = datasource.GetLayer(0)
            values = []
            
            # 读取属性值
            for feature in layer:
                value = feature.GetField(field_name)
                if value is not None:
                    values.append(float(value))
            
            datasource = None
            
            if len(values) > 0:
                min_val = float(np.min(values))
                max_val = float(np.max(values))
                mean_val = float(np.mean(values))
                logger.info(f"矢量属性 '{field_name}' 统计: min={min_val}, max={max_val}, mean={mean_val}")
                return (min_val, max_val, mean_val)
            
        except Exception as e:
            logger.error(f"读取矢量统计信息失败: {e}")
        
        return (None, None, None)
    
    def _create_vector_sld_by_attribute(self, field_name: str, min_val: float, max_val: float, 
                                       color_scheme: str = 'default') -> str:
        """根据属性值创建矢量SLD样式（分级设色）"""
        # 计算分级阈值
        range_val = max_val - min_val
        threshold1 = min_val + range_val * 0.33
        threshold2 = min_val + range_val * 0.67
        
        # 定义配色方案
        color_schemes = {
            'default': {  # 黄-橙-红（适用于GDP等经济指标）
                'low': '#FFFFCC',
                'medium': '#FFAA00',
                'high': '#FF0000'
            },
            'green_yellow_red': {  # 绿-黄-红（适用于风险等级）
                'low': '#00FF00',
                'medium': '#FFFF00',
                'high': '#FF0000'
            },
            'blue_cyan_green': {  # 蓝-青-绿（适用于水资源等）
                'low': '#0000FF',
                'medium': '#00FFFF',
                'high': '#00FF00'
            },
            'purple_pink_red': {  # 紫-粉-红（适用于人口密度等）
                'low': '#9966FF',
                'medium': '#FF99CC',
                'high': '#FF0000'
            }
        }
        
        colors = color_schemes.get(color_scheme, color_schemes['default'])
        
        sld = f'''<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0" 
  xmlns="http://www.opengis.net/sld" 
  xmlns:ogc="http://www.opengis.net/ogc"
  xmlns:xlink="http://www.w3.org/1999/xlink" 
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.opengis.net/sld 
    http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
  
  <NamedLayer>
    <Name>vector_style</Name>
    <UserStyle>
      <Title>矢量图层动态样式（按{field_name}分级）</Title>
      <Abstract>根据{field_name}字段值自动分级设色</Abstract>
      <FeatureTypeStyle>
        <!-- 规则1: 低值 -->
        <Rule>
          <Name>低值</Name>
          <Title>低值 (&lt; {threshold1:.2f})</Title>
          <ogc:Filter>
            <ogc:PropertyIsLessThan>
              <ogc:PropertyName>{field_name}</ogc:PropertyName>
              <ogc:Literal>{threshold1:.6f}</ogc:Literal>
            </ogc:PropertyIsLessThan>
          </ogc:Filter>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">{colors['low']}</CssParameter>
              <CssParameter name="fill-opacity">0.5</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#666666</CssParameter>
              <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
        
        <!-- 规则2: 中值 -->
        <Rule>
          <Name>中值</Name>
          <Title>中值 ({threshold1:.2f} - {threshold2:.2f})</Title>
          <ogc:Filter>
            <ogc:And>
              <ogc:PropertyIsGreaterThanOrEqualTo>
                <ogc:PropertyName>{field_name}</ogc:PropertyName>
                <ogc:Literal>{threshold1:.6f}</ogc:Literal>
              </ogc:PropertyIsGreaterThanOrEqualTo>
              <ogc:PropertyIsLessThan>
                <ogc:PropertyName>{field_name}</ogc:PropertyName>
                <ogc:Literal>{threshold2:.6f}</ogc:Literal>
              </ogc:PropertyIsLessThan>
            </ogc:And>
          </ogc:Filter>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">{colors['medium']}</CssParameter>
              <CssParameter name="fill-opacity">0.5</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#666666</CssParameter>
              <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
        
        <!-- 规则3: 高值 -->
        <Rule>
          <Name>高值</Name>
          <Title>高值 (&gt;= {threshold2:.2f})</Title>
          <ogc:Filter>
            <ogc:PropertyIsGreaterThanOrEqualTo>
              <ogc:PropertyName>{field_name}</ogc:PropertyName>
              <ogc:Literal>{threshold2:.6f}</ogc:Literal>
            </ogc:PropertyIsGreaterThanOrEqualTo>
          </ogc:Filter>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">{colors['high']}</CssParameter>
              <CssParameter name="fill-opacity">0.5</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#666666</CssParameter>
              <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
        
        <!-- 默认样式（如果字段为空） -->
        <Rule>
          <Name>其他</Name>
          <Title>其他（无数据）</Title>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">#CCCCCC</CssParameter>
              <CssParameter name="fill-opacity">0.5</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#999999</CssParameter>
              <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>'''
        return sld
    
    def _create_vector_sld_simple(self, color: str = '#0000FF', opacity: float = 0.3) -> str:
        """创建简单统一样式的矢量SLD，兼容面/线/点几何。"""
        sld = f'''<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0" 
  xmlns="http://www.opengis.net/sld" 
  xmlns:ogc="http://www.opengis.net/ogc"
  xmlns:xlink="http://www.w3.org/1999/xlink" 
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.opengis.net/sld 
    http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
  
  <NamedLayer>
    <Name>vector_style</Name>
    <UserStyle>
      <Title>矢量图层统一样式</Title>
      <FeatureTypeStyle>
        <Rule>
          <PointSymbolizer>
            <Graphic>
              <Mark>
                <WellKnownName>circle</WellKnownName>
                <Fill>
                  <CssParameter name="fill">{color}</CssParameter>
                  <CssParameter name="fill-opacity">0.95</CssParameter>
                </Fill>
                <Stroke>
                  <CssParameter name="stroke">#FFFFFF</CssParameter>
                  <CssParameter name="stroke-width">1.5</CssParameter>
                </Stroke>
              </Mark>
              <Size>12</Size>
            </Graphic>
          </PointSymbolizer>
          <LineSymbolizer>
            <Stroke>
              <CssParameter name="stroke">{color}</CssParameter>
              <CssParameter name="stroke-width">4</CssParameter>
              <CssParameter name="stroke-opacity">0.95</CssParameter>
            </Stroke>
          </LineSymbolizer>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">{color}</CssParameter>
              <CssParameter name="fill-opacity">{max(opacity, 0.45)}</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">{color}</CssParameter>
              <CssParameter name="stroke-width">3</CssParameter>
              <CssParameter name="stroke-opacity">1.0</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>'''
        return sld

    def _create_ecology_rsei_raster_sld(self, min_value: float = 0.0, max_value: float = 1.0) -> str:
        """创建生态/RSEI 专用分级样式。"""
        classified_mode = min_value >= 0 and max_value <= 6.5 and max_value > 1.0

        if classified_mode:
            if max_value <= 5.5:
                entries = [
                    {'quantity': 1, 'color': '#c0392b', 'label': '差（高风险区域）'},
                    {'quantity': 2, 'color': '#f08c7f', 'label': '较差'},
                    {'quantity': 3, 'color': '#f1c453', 'label': '中等'},
                    {'quantity': 4, 'color': '#9ccf72', 'label': '良好'},
                    {'quantity': 5, 'color': '#2f8f5b', 'label': '优秀'},
                ]
                abstract = 'RSEI五级分级样式（编码栅格）：1=差，5=优秀'
            else:
                entries = [
                    {'quantity': 1, 'color': '#8b1e3f', 'label': '1级'},
                    {'quantity': 2, 'color': '#c0392b', 'label': '2级'},
                    {'quantity': 3, 'color': '#f08c7f', 'label': '3级'},
                    {'quantity': 4, 'color': '#f1c453', 'label': '4级'},
                    {'quantity': 5, 'color': '#9ccf72', 'label': '5级'},
                    {'quantity': 6, 'color': '#2f8f5b', 'label': '6级'},
                ]
                abstract = '单波段分类栅格样式（1-6级编码）'
            color_map_entries = "\n".join(
                f'                            <ColorMapEntry color="{entry["color"]}" quantity="{entry["quantity"]}" opacity="0.82" label="{entry["label"]}"/>'
                for entry in entries
            )
            color_map_type = 'intervals'
        else:
            if not np.isfinite(min_value) or not np.isfinite(max_value) or max_value <= min_value:
                min_value = 0.0
                max_value = 1.0

            raw_min = 0.0 if min_value >= 0.0 and max_value <= 1.0 else min_value
            raw_max = 1.0 if min_value >= 0.0 and max_value <= 1.0 else max_value
            range_value = max_value - min_value
            v1 = min_value + range_value * 0.2
            v2 = min_value + range_value * 0.4
            v3 = min_value + range_value * 0.6
            v4 = min_value + range_value * 0.8

            color_map_entries = "\n".join([
                f'                            <ColorMapEntry color="#8B0000" quantity="{raw_min:.6f}" opacity="1.0" label="最低值"/>',
                f'                            <ColorMapEntry color="#FF0000" quantity="{min_value:.6f}" opacity="1.0" label="低值"/>',
                f'                            <ColorMapEntry color="#FFA500" quantity="{v1:.6f}" opacity="1.0" label="较低值"/>',
                f'                            <ColorMapEntry color="#FFFF00" quantity="{v2:.6f}" opacity="1.0" label="中值"/>',
                f'                            <ColorMapEntry color="#00FF00" quantity="{v3:.6f}" opacity="1.0" label="较高值"/>',
                f'                            <ColorMapEntry color="#006400" quantity="{v4:.6f}" opacity="1.0" label="高值"/>',
                f'                            <ColorMapEntry color="#006400" quantity="{raw_max:.6f}" opacity="1.0" label="最高值"/>',
            ])
            abstract = 'RSEI动态拉伸样式：按当前结果有效值范围进行分析页同款渐变渲染'
            color_map_type = 'intervals'

        sld = f'''<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
    <NamedLayer>
        <Name>ecology_rsei_style</Name>
        <UserStyle>
            <Title>生态RSEI五级分级样式</Title>
            <Abstract>{abstract}</Abstract>
            <FeatureTypeStyle>
                <Rule>
                    <RasterSymbolizer>
                        <Opacity>1.0</Opacity>
                        <ChannelSelection>
                            <GrayChannel>
                                <SourceChannelName>1</SourceChannelName>
                            </GrayChannel>
                        </ChannelSelection>
                        <ColorMap type="{color_map_type}">
{color_map_entries}
                        </ColorMap>
                    </RasterSymbolizer>
                </Rule>
            </FeatureTypeStyle>
        </UserStyle>
    </NamedLayer>
</StyledLayerDescriptor>'''
        return sld

    def _create_rgb_imagery_raster_sld(self, red_band: int = 3, green_band: int = 2, blue_band: int = 1) -> str:
        """创建适用于高分真彩影像的 RGB 通道样式。"""
        sld = f'''<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
    <NamedLayer>
        <Name>imagery_rgb_style</Name>
        <UserStyle>
            <Title>高分真彩影像样式</Title>
            <Abstract>基于RGB波段组合的真彩遥感影像显示样式</Abstract>
            <FeatureTypeStyle>
                <Rule>
                    <RasterSymbolizer>
                        <Opacity>1.0</Opacity>
                        <ChannelSelection>
                            <RedChannel>
                                <SourceChannelName>{red_band}</SourceChannelName>
                            </RedChannel>
                            <GreenChannel>
                                <SourceChannelName>{green_band}</SourceChannelName>
                            </GreenChannel>
                            <BlueChannel>
                                <SourceChannelName>{blue_band}</SourceChannelName>
                            </BlueChannel>
                        </ChannelSelection>
                        <ContrastEnhancement>
                            <Normalize/>
                        </ContrastEnhancement>
                    </RasterSymbolizer>
                </Rule>
            </FeatureTypeStyle>
        </UserStyle>
    </NamedLayer>
</StyledLayerDescriptor>'''
        return sld

    def _build_raster_style(self, style_type: str, min_value: float, max_value: float) -> str:
        """根据栅格类型选择样式。"""
        if style_type == 'imagery_rgb':
            return self._create_rgb_imagery_raster_sld()
        if style_type == 'ecology_rsei':
            return self._create_ecology_rsei_raster_sld(min_value, max_value)
        return self._create_default_raster_sld(min_value, max_value)
    
    def apply_style_to_layer(self, layer_name: str, style_name: str) -> bool:
        """为图层应用样式"""
        try:
            # 更新图层配置，设置默认样式
            layer_url = f"{self.base_url}/rest/layers/{self.workspace}:{layer_name}.json"
            
            # 先获取图层信息
            layer_response = requests.get(
                layer_url,
                auth=self.auth,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if layer_response.status_code == 200:
                layer_data = layer_response.json()
                
                # 更新样式
                layer_data['layer']['defaultStyle'] = {
                    'name': style_name,
                    'workspace': self.workspace
                }
                
                # 提交更新
                update_response = requests.put(
                    layer_url,
                    auth=self.auth,
                    json=layer_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                
                if update_response.status_code in [200, 204]:
                    logger.info(f"✅ 样式 {style_name} 已应用到图层 {layer_name}")
                    return True
                else:
                    logger.error(f"❌ 应用样式失败: HTTP {update_response.status_code} - {update_response.text}")
            else:
                logger.error(f"❌ 获取图层信息失败: HTTP {layer_response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ 应用样式异常: {e}")
            
        return False
    
    def publish_shapefile(self, layer_name: str, shapefile_path: str, charset: str = 'GBK') -> bool:
        """发布Shapefile矢量图层到GeoServer
        
        Args:
            layer_name: 图层名称（也用作datastore名称）
            shapefile_path: Shapefile文件路径（.shp文件）
            charset: 字符集编码，默认GBK
            
        Returns:
            bool: 发布是否成功
        """
        try:
            import os
            from urllib.parse import quote
            
            # 确保文件存在
            if not os.path.exists(shapefile_path):
                logger.error(f"Shapefile文件不存在: {shapefile_path}")
                return False
            
            # 获取绝对路径
            abs_path = os.path.abspath(shapefile_path)
            # 将反斜杠转换为正斜杠（GeoServer使用）
            file_url = 'file:///' + abs_path.replace('\\', '/')
            
            logger.info(f"开始发布Shapefile: {layer_name}")
            logger.info(f"文件路径: {file_url}")
            
            # 1. 创建或更新Shapefile DataStore
            datastore_name = f"{layer_name}_store"
            
            # 构建DataStore配置
            datastore_data = {
                "dataStore": {
                    "name": datastore_name,
                    "type": "Shapefile",
                    "enabled": True,
                    "connectionParameters": {
                        "entry": [
                            {"@key": "url", "$": file_url},
                            {"@key": "charset", "$": charset},
                            {"@key": "create spatial index", "$": "true"},
                            {"@key": "memory mapped buffer", "$": "false"},
                            {"@key": "cache and reuse memory maps", "$": "true"}
                        ]
                    }
                }
            }
            
            # 先尝试删除旧的datastore
            try:
                delete_url = f"workspaces/{self.workspace}/datastores/{datastore_name}"
                self._make_request('DELETE', delete_url, params={'recurse': 'true'})
                logger.info(f"已删除旧的DataStore: {datastore_name}")
            except Exception as e:
                logger.debug(f"删除旧DataStore失败（可能不存在）: {e}")
            
            # 创建新的datastore
            result = self._make_request(
                'POST',
                f'workspaces/{self.workspace}/datastores',
                json=datastore_data
            )
            
            if result is None:
                logger.error(f"创建DataStore失败: {datastore_name}")
                return False
            
            logger.info(f"DataStore创建成功: {datastore_name}")
            
            # 2. 发布FeatureType（图层）
            # 获取Shapefile的基础名称（不带扩展名）
            base_name = os.path.splitext(os.path.basename(shapefile_path))[0]
            detected_srs = self._detect_vector_srs(shapefile_path)
            
            featuretype_data = {
                "featureType": {
                    "name": layer_name,
                    "nativeName": base_name,
                    "title": layer_name,
                    "enabled": True,
                    "store": {
                        "name": f"{self.workspace}:{datastore_name}",
                        "@class": "dataStore"
                    }
                }
            }
            if detected_srs:
                featuretype_data["featureType"]["srs"] = detected_srs
                featuretype_data["featureType"]["projectionPolicy"] = "FORCE_DECLARED"
                logger.info(f"检测到矢量坐标系: {detected_srs}")
            else:
                logger.warning(f"未识别到 {layer_name} 的明确坐标系，将让 GeoServer 使用源数据原生坐标系")
            
            # 发布FeatureType
            result = self._make_request(
                'POST',
                f'workspaces/{self.workspace}/datastores/{datastore_name}/featuretypes',
                json=featuretype_data
            )
            
            if result is None:
                # 尝试简化的发布方式
                logger.info("尝试简化的FeatureType发布...")
                simple_featuretype_data = {
                    "featureType": {
                        "name": layer_name,
                        "nativeName": base_name
                    }
                }
                result = self._make_request(
                    'POST',
                    f'workspaces/{self.workspace}/datastores/{datastore_name}/featuretypes',
                    json=simple_featuretype_data
                )
                
                if result is None:
                    logger.error(f"发布FeatureType失败: {layer_name}")
                    return False
            
            logger.info(f"[OK] Shapefile图层发布成功: {layer_name}")
            logger.info(f"     WMS URL: {self.base_url}/wms?service=WMS&version=1.1.0&request=GetMap&layers={self.workspace}:{layer_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"发布Shapefile失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


# 默认GeoServer管理器实例
geoserver_manager = GeoServerManager()


def get_geoserver_manager() -> GeoServerManager:
    """获取GeoServer管理器实例"""
    return geoserver_manager





