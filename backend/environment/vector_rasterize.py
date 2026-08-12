import os
import zipfile
from typing import Optional, Tuple

from osgeo import ogr, osr, gdal


gdal.UseExceptions()


def _extract_zip_if_needed(input_path: str, work_dir: str) -> str:
    """
    如果传入的是zip，解压并返回shp主文件路径；否则直接返回原路径。
    """
    if input_path.lower().endswith('.zip'):
        # 添加调试信息
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"处理ZIP文件: {input_path}")
        logger.info(f"文件是否存在: {os.path.exists(input_path)}")
        logger.info(f"文件大小: {os.path.getsize(input_path) if os.path.exists(input_path) else 'N/A'} bytes")
        
        # 检查文件是否存在
        if not os.path.exists(input_path):
            raise ValueError(f'文件不存在: {input_path}')
        
        # 检查文件大小
        file_size = os.path.getsize(input_path)
        if file_size == 0:
            raise ValueError('ZIP文件为空')
        if file_size < 100:
            raise ValueError('ZIP文件过小，可能不是有效的压缩包')
        
        # 验证ZIP文件有效性
        if not zipfile.is_zipfile(input_path):
            # 尝试读取文件头来诊断问题
            try:
                with open(input_path, 'rb') as f:
                    header = f.read(10)
                    logger.error(f"文件头字节: {header}")
                    logger.error(f"文件头十六进制: {header.hex()}")
            except Exception as e:
                logger.error(f"无法读取文件头: {e}")
            raise ValueError(f'文件不是有效的ZIP格式。文件大小: {file_size} bytes，请确保上传正确的ZIP压缩包')
        
        os.makedirs(work_dir, exist_ok=True)
        try:
            with zipfile.ZipFile(input_path, 'r') as zf:
                # 列出ZIP内容
                file_list = zf.namelist()
                logger.info(f"ZIP文件内容: {file_list}")
                zf.extractall(work_dir)
        except zipfile.BadZipFile as e:
            raise ValueError(f'ZIP文件损坏或格式不正确: {str(e)}')
        except Exception as e:
            raise ValueError(f'解压ZIP文件失败: {str(e)}')
            
        # 寻找shp主文件
        shp_candidates = []
        for root, _dirs, files in os.walk(work_dir):
            for f in files:
                if f.lower().endswith('.shp'):
                    shp_candidates.append(os.path.join(root, f))
        if not shp_candidates:
            raise ValueError('ZIP包中未找到 .shp 文件，请确保包含完整的Shapefile组件')
        return shp_candidates[0]
    return input_path


def _validate_shapefile_sidecars(shp_path: str) -> None:
    """
    校验Shapefile的必要sidecar文件存在: .shp/.shx/.dbf/.prj
    """
    base, _ = os.path.splitext(shp_path)
    required_exts = ['.shx', '.dbf', '.prj']
    missing = [ext for ext in required_exts if not os.path.exists(base + ext)]
    if missing:
        raise ValueError(f'Shapefile组件缺失: {", ".join(missing)}')


def _get_layer_and_srs(shp_path: str) -> Tuple[ogr.Layer, osr.SpatialReference]:
    ds = ogr.Open(shp_path)
    if ds is None:
        raise ValueError(f'无法打开Shapefile: {shp_path}')
    layer = ds.GetLayer(0)
    if layer is None:
        raise ValueError('Shapefile无有效图层')
    # 仅支持面数据
    geom_type = layer.GetGeomType()
    if geom_type not in (ogr.wkbPolygon, ogr.wkbMultiPolygon):
        raise ValueError('仅支持面要素进行栅格化')
    srs = layer.GetSpatialRef()
    if srs is None:
        raise ValueError('未检测到投影（.prj），请提供坐标参考')
    return layer, srs


def rasterize_shapefile_to_tiff(
    input_path: str,
    output_tif: str,
    attribute_field: str,
    pixel_size: float = 30.0,
    nodata_value: int = -9999,
    temp_dir: Optional[str] = None,
) -> str:
    """
    将Shapefile(或zip)按属性字段栅格化为GeoTIFF整型分类栅格。

    Returns: 生成的GeoTIFF路径（output_tif）。
    """
    # 1) 处理zip与校验sidecars
    work_dir = temp_dir or os.path.join(os.path.dirname(output_tif), 'tmp')
    shp_path = _extract_zip_if_needed(input_path, work_dir)
    _validate_shapefile_sidecars(shp_path)

    # 2) 读取图层与SRS
    layer, srs = _get_layer_and_srs(shp_path)

    # 3) 检查属性字段
    layer_defn = layer.GetLayerDefn()
    field_names = [layer_defn.GetFieldDefn(i).GetName() for i in range(layer_defn.GetFieldCount())]
    
    # 如果指定的属性字段不存在或不是数字字段，尝试自动选择数字字段
    is_numeric_field = False
    if attribute_field in field_names:
        # 检查字段类型
        for i in range(layer_defn.GetFieldCount()):
            field_defn = layer_defn.GetFieldDefn(i)
            if field_defn.GetName() == attribute_field:
                field_type = field_defn.GetTypeName()
                if field_type in ['Integer', 'Real', 'Float', 'Double']:
                    is_numeric_field = True
                break
    
    if attribute_field not in field_names or not is_numeric_field:
        # 优先选择的数字字段
        preferred_fields = ['ID', 'id', 'FID', 'fid', 'OBJECTID', 'objectid', 'CLASS_ID', 'class_id']
        
        # 查找数字字段
        numeric_fields = []
        for i in range(layer_defn.GetFieldCount()):
            field_defn = layer_defn.GetFieldDefn(i)
            field_type = field_defn.GetTypeName()
            if field_type in ['Integer', 'Real', 'Float', 'Double']:
                numeric_fields.append(field_defn.GetName())
        
        # 按优先级选择字段
        selected_field = None
        for preferred in preferred_fields:
            if preferred in numeric_fields:
                selected_field = preferred
                break
        
        if not selected_field and numeric_fields:
            selected_field = numeric_fields[0]  # 使用第一个数字字段
        
        if selected_field:
            print(f"⚠️ 属性字段 '{attribute_field}' 不存在，自动选择数字字段: '{selected_field}'")
            attribute_field = selected_field
        else:
            raise ValueError(f'属性字段不存在: {attribute_field}，且未找到可用的数字字段。可用字段: {", ".join(field_names)}')

    # 4) 计算范围与栅格尺寸
    min_x, max_x, min_y, max_y = layer.GetExtent()
    x_res = int((max_x - min_x) / pixel_size + 0.5)
    y_res = int((max_y - min_y) / pixel_size + 0.5)
    if x_res <= 0 or y_res <= 0:
        raise ValueError('栅格尺寸计算异常，请检查像元大小或数据范围')

    # 5) 创建目标栅格
    os.makedirs(os.path.dirname(output_tif), exist_ok=True)
    driver = gdal.GetDriverByName('GTiff')
    dst_ds = driver.Create(output_tif, x_res, y_res, 1, gdal.GDT_Int32, options=['COMPRESS=LZW'])
    if dst_ds is None:
        raise RuntimeError('无法创建输出栅格')

    geotransform = (min_x, pixel_size, 0, max_y, 0, -pixel_size)
    dst_ds.SetGeoTransform(geotransform)
    dst_ds.SetProjection(srs.ExportToWkt())

    band = dst_ds.GetRasterBand(1)
    band.Fill(nodata_value)
    band.SetNoDataValue(nodata_value)

    # 6) 栅格化（按属性）
    err = gdal.RasterizeLayer(
        dst_ds,
        [1],
        layer,
        options=[f'ATTRIBUTE={attribute_field}']
    )
    if err != 0:
        raise RuntimeError(f'Rasterize失败，错误码: {err}')

    band.FlushCache()
    dst_ds.FlushCache()
    dst_ds = None
    return output_tif


