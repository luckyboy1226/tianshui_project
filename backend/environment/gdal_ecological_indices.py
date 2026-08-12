"""
使用GDAL进行遥感生态指数计算
GDAL (Geospatial Data Abstraction Library) 是处理地理空间数据的强大库
"""

import numpy as np
from osgeo import gdal, osr
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.colors import LinearSegmentedColormap

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
import os
import tempfile
from PIL import Image
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import logging
import json
try:
    from .band_mapping import (
        get_band_descriptions,
        get_band_scale_offset,
        get_tasseled_cap_coefficients,
        infer_standard_band_mapping,
        thermal_band_is_calibrated,
        thermal_conversion_parameters,
        uses_approximate_tasseled_cap,
    )
except ImportError:  # 兼容直接运行脚本
    from band_mapping import (
        get_band_descriptions,
        get_band_scale_offset,
        get_tasseled_cap_coefficients,
        infer_standard_band_mapping,
        thermal_band_is_calibrated,
        thermal_conversion_parameters,
        uses_approximate_tasseled_cap,
    )

# 设置GDAL错误处理
gdal.UseExceptions()

logger = logging.getLogger(__name__)


class GDALEcologicalIndexCalculator:
    """基于GDAL的生态指数计算器"""
    
    def __init__(self, image_path):
        """
        初始化GDAL生态指数计算器
        
        Args:
            image_path: 遥感影像文件路径
        """
        self.image_path = image_path
        self.dataset = None
        self.bands = {}
        self.metadata = {}
        self.geotransform = None
        self.projection = None
        self._sensor_band_mapping = None
        self._scaled_band_cache = {}
        
    def load_image(self):
        """使用GDAL加载遥感影像"""
        try:
            # 打开数据集
            self.dataset = gdal.Open(self.image_path, gdal.GA_ReadOnly)
            if self.dataset is None:
                raise ValueError(f"无法打开影像文件: {self.image_path}")
            
            # 获取基本信息
            self.geotransform = self.dataset.GetGeoTransform()
            self.projection = self.dataset.GetProjection()
            
            # 获取影像尺寸
            self.width = self.dataset.RasterXSize
            self.height = self.dataset.RasterYSize
            self.band_count = self.dataset.RasterCount
            
            # 读取所有波段
            for i in range(1, self.band_count + 1):
                band = self.dataset.GetRasterBand(i)
                self.bands[i] = band.ReadAsArray().astype(np.float32)
                
                # 获取波段元数据
                self.metadata[f'band_{i}'] = {
                    'description': band.GetDescription(),
                    'no_data_value': band.GetNoDataValue(),
                    'scale': band.GetScale(),
                    'offset': band.GetOffset(),
                    'unit_type': band.GetUnitType()
                }
            self._sensor_band_mapping = None
            self._scaled_band_cache = {}
            
            logger.info(f"成功加载影像: {self.image_path}")
            logger.info(f"影像尺寸: {self.width} x {self.height}, 波段数: {self.band_count}")
            return True
            
        except Exception as e:
            logger.error(f"加载影像失败: {e}")
            return False
    
    def get_band_info(self):
        """获取波段信息"""
        info = {
            'width': self.width,
            'height': self.height,
            'band_count': self.band_count,
            'geotransform': self.geotransform,
            'projection': self.projection,
            'bands': {}
        }
        
        for band_num, band_data in self.bands.items():
            info['bands'][band_num] = {
                'shape': band_data.shape,
                'dtype': str(band_data.dtype),
                'min': float(np.nanmin(band_data)),
                'max': float(np.nanmax(band_data)),
                'mean': float(np.nanmean(band_data)),
                'std': float(np.nanstd(band_data)),
                'metadata': self.metadata.get(f'band_{band_num}', {})
            }
        
        return info

    def _get_sensor_band_mapping(self):
        if self._sensor_band_mapping is None and self.band_count:
            self._sensor_band_mapping = infer_standard_band_mapping(
                dataset=self.dataset,
                band_count=self.band_count,
                descriptions=get_band_descriptions(self.dataset, band_count=self.band_count),
            )
            if self._sensor_band_mapping:
                logger.info(f"识别到GDAL波段映射: {self._sensor_band_mapping}")
        return self._sensor_band_mapping

    def _get_scaled_band_by_index(self, band_index):
        """按scale/offset还原指定0基波段数据。"""
        if band_index in self._scaled_band_cache:
            return self._scaled_band_cache[band_index]

        band_number = band_index + 1
        band_data = self.bands.get(band_number)
        if band_data is None:
            return None

        scale, offset = get_band_scale_offset(self.dataset, band_index, band_count=self.band_count)
        scaled_band = band_data.astype(np.float32, copy=False) * np.float32(scale) + np.float32(offset)
        self._scaled_band_cache[band_index] = scaled_band
        return scaled_band

    def _get_band_array(self, band_name):
        mapping = self._get_sensor_band_mapping()
        if not mapping:
            return None

        band_index = mapping.get(band_name)
        if band_index is None:
            return None
        return self._get_scaled_band_by_index(band_index)

    def _safe_normalized_difference(self, band_a, band_b):
        if band_a is None or band_b is None:
            return None

        numerator = band_a - band_b
        denominator = band_a + band_b
        result = np.full_like(band_a, np.nan, dtype=np.float32)
        valid_mask = np.isfinite(band_a) & np.isfinite(band_b) & (denominator != 0)
        result[valid_mask] = numerator[valid_mask] / denominator[valid_mask]
        return np.clip(result, -1.0, 1.0)

    def _safe_divide(self, numerator, denominator):
        result = np.full_like(numerator, np.nan, dtype=np.float32)
        valid_mask = np.isfinite(numerator) & np.isfinite(denominator) & (denominator != 0)
        result[valid_mask] = numerator[valid_mask] / denominator[valid_mask]
        return result

    def _normalize_to_unit_interval(self, index_data):
        normalized = np.full_like(index_data, np.nan, dtype=np.float32)
        valid_mask = np.isfinite(index_data)
        if not np.any(valid_mask):
            return normalized

        valid_values = index_data[valid_mask]
        min_val = np.min(valid_values)
        max_val = np.max(valid_values)
        if max_val > min_val:
            normalized[valid_mask] = (valid_values - min_val) / (max_val - min_val)
        else:
            normalized[valid_mask] = 0.0
        return normalized
    
    def calculate_ndvi(self, red_band=3, nir_band=4):
        """计算NDVI（归一化植被指数）"""
        try:
            nir = self._get_band_array('nir')
            red = self._get_band_array('red')

            if nir is None or red is None:
                if self.band_count == 3:
                    nir = self._get_scaled_band_by_index(1)
                    red = self._get_scaled_band_by_index(0)
                    logger.info("GDAL计算器使用RGB波段近似计算NDVI")
                else:
                    raise ValueError(f"当前波段配置不支持NDVI计算: {self.band_count}波段")

            ndvi = self._safe_normalized_difference(nir, red)
            if ndvi is None:
                raise ValueError("NDVI计算失败，近红外或红波段无效")

            logger.info("NDVI计算完成")
            return ndvi
            
        except Exception as e:
            logger.error(f"计算NDVI失败: {e}")
            return None
    
    def calculate_ndwi(self, green_band=2, nir_band=4):
        """计算NDWI（归一化水体指数）"""
        try:
            green = self._get_band_array('green')
            nir = self._get_band_array('nir')

            if green is None or nir is None:
                if self.band_count == 3:
                    green = self._get_scaled_band_by_index(1)
                    nir = self._get_scaled_band_by_index(0)
                    logger.info("GDAL计算器使用RGB波段近似计算NDWI")
                else:
                    raise ValueError(f"当前波段配置不支持NDWI计算: {self.band_count}波段")

            ndwi = self._safe_normalized_difference(green, nir)
            if ndwi is None:
                raise ValueError("NDWI计算失败，绿波段或近红外波段无效")

            logger.info("NDWI计算完成")
            return ndwi
            
        except Exception as e:
            logger.error(f"计算NDWI失败: {e}")
            return None
    
    def calculate_ndbi(self, nir_band=4, swir_band=5):
        """计算NDBI（归一化建筑指数）"""
        try:
            nir = self._get_band_array('nir')
            swir = self._get_band_array('swir1')

            if swir is None or nir is None:
                if self.band_count == 3:
                    swir = self._get_scaled_band_by_index(2)
                    nir = self._get_scaled_band_by_index(0)
                    logger.info("GDAL计算器使用RGB波段近似计算NDBI")
                else:
                    raise ValueError(f"当前波段配置不支持NDBI计算: {self.band_count}波段")

            ndbi = self._safe_normalized_difference(swir, nir)
            if ndbi is None:
                raise ValueError("NDBI计算失败，短波红外或近红外波段无效")

            logger.info("NDBI计算完成")
            return ndbi
            
        except Exception as e:
            logger.error(f"计算NDBI失败: {e}")
            return None
    
    def calculate_ndsi(self, green_band=2, swir_band=5):
        """计算NDSI（归一化积雪指数）"""
        try:
            green = self._get_band_array('green')
            swir = self._get_band_array('swir1')
            blue = self._get_band_array('blue')
            red = self._get_band_array('red')

            if green is not None and swir is not None:
                ndsi = self._safe_normalized_difference(green, swir)
                logger.info("GDAL计算器使用 Green/SWIR1 计算标准NDSI")
            elif self.band_count == 4 and green is not None and red is not None:
                ndsi = self._safe_normalized_difference(green, red)
                logger.info("GDAL计算器缺少SWIR1，使用 Green/Red 近似计算NDSI")
            elif self.band_count == 3 and green is not None and blue is not None:
                ndsi = self._safe_normalized_difference(green, blue)
                logger.info("GDAL计算器为RGB影像，使用 Green/Blue 近似计算NDSI")
            else:
                raise ValueError(f"当前波段配置不支持NDSI计算: {self.band_count}波段")

            logger.info("NDSI计算完成")
            return np.clip(ndsi, -1, 1) if ndsi is not None else None
            
        except Exception as e:
            logger.error(f"计算NDSI失败: {e}")
            return None

    def calculate_wetness(self):
        """计算湿度指数（WET，基于标准Tasseled Cap 湿度分量）"""
        try:
            mapping = self._get_sensor_band_mapping()
            if not mapping:
                raise ValueError("无法识别影像波段布局")

            blue = self._get_band_array('blue')
            green = self._get_band_array('green')
            red = self._get_band_array('red')
            nir = self._get_band_array('nir')
            swir1 = self._get_band_array('swir1')
            swir2 = self._get_band_array('swir2')

            if any(item is None for item in [blue, green, red, nir, swir1, swir2]):
                raise ValueError("当前影像缺少计算WET所需的Blue/Green/Red/NIR/SWIR1/SWIR2波段")

            tc_coefficients = get_tasseled_cap_coefficients(mapping.get('profile'))
            if not tc_coefficients or 'wetness' not in tc_coefficients:
                raise ValueError("当前影像缺少可用的Tasseled Cap 系数，无法计算标准WET")

            coefficients = tc_coefficients['wetness']
            if uses_approximate_tasseled_cap(mapping.get('profile')):
                logger.warning("GDAL计算器正在使用通用6波段近似系数计算WET")

            wetness = (
                coefficients[0] * blue +
                coefficients[1] * green +
                coefficients[2] * red +
                coefficients[3] * nir +
                coefficients[4] * swir1 +
                coefficients[5] * swir2
            ).astype(np.float32)

            logger.info("WET计算完成")
            return wetness
        except Exception as e:
            logger.error(f"计算WET失败: {e}")
            return None

    def calculate_dryness(self):
        """计算干度指数（NDBSI = (SI + IBI) / 2）"""
        try:
            blue = self._get_band_array('blue')
            green = self._get_band_array('green')
            red = self._get_band_array('red')
            nir = self._get_band_array('nir')
            swir1 = self._get_band_array('swir1')

            if any(item is None for item in [blue, green, red, nir, swir1]):
                raise ValueError("当前影像缺少计算NDBSI所需的Blue/Green/Red/NIR/SWIR1波段")

            si_numerator = (swir1 + red) - (nir + blue)
            si_denominator = (swir1 + red) + (nir + blue)
            si = self._safe_divide(si_numerator, si_denominator)

            ndbi_component = self._safe_divide(2.0 * swir1, swir1 + nir)
            vegetation_component = self._safe_divide(nir, nir + red)
            water_component = self._safe_divide(green, green + swir1)
            ibi_numerator = ndbi_component - (vegetation_component + water_component)
            ibi_denominator = ndbi_component + vegetation_component + water_component
            ibi = self._safe_divide(ibi_numerator, ibi_denominator)

            dryness = ((si + ibi) / 2.0).astype(np.float32)
            logger.info("干度指数计算完成")
            return dryness
        except Exception as e:
            logger.error(f"计算干度指数失败: {e}")
            return None

    def calculate_heat(self):
        """计算热度指数（LST/热红外亮温分量）。"""
        try:
            mapping = self._get_sensor_band_mapping() or {}
            thermal = self._get_band_array('thermal')
            if thermal is None:
                raise ValueError("当前影像缺少热红外/LST波段")

            if not thermal_band_is_calibrated(mapping=mapping, dataset=self.dataset):
                raise ValueError("当前影像热红外波段缺少可靠的温度量纲信息")

            heat = np.where(np.isfinite(thermal), thermal, np.nan).astype(np.float32)
            scale, offset = thermal_conversion_parameters(mapping.get('profile'))
            if scale is not None and offset is not None:
                raw_scale, raw_offset = get_band_scale_offset(
                    self.dataset,
                    mapping['thermal'],
                    band_count=self.band_count,
                )
                if abs(raw_scale - 1.0) <= 1e-12 and abs(raw_offset) <= 1e-12:
                    heat = heat * np.float32(scale) + np.float32(offset)
                    logger.info("GDAL计算器按已知传感器参数补充还原热红外温度")

            logger.info("热度指数计算完成")
            return heat
        except Exception as e:
            logger.error(f"计算热度指数失败: {e}")
            return None

    def calculate_greenness(self):
        """计算绿度指数（标准RSEI中使用NDVI作为绿度分量）"""
        return self.calculate_ndvi()

    def calculate_tasseled_cap(self):
        """
        计算缨帽变换（Tasseled Cap Transformation）
        用于提取绿度、亮度、湿度等特征
        """
        try:
            band_mapping = self._get_sensor_band_mapping()
            required_roles = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']
            if any(band_mapping.get(role) is None for role in required_roles):
                raise ValueError(
                    f"当前影像缺少缨帽变换所需波段，识别结果: {band_mapping}"
                )

            tc_coefficients = get_tasseled_cap_coefficients(band_mapping.get('profile'))
            if not tc_coefficients:
                raise ValueError("当前影像缺少可用的Tasseled Cap 系数")
            if uses_approximate_tasseled_cap(band_mapping.get('profile')):
                logger.warning("GDAL计算器正在使用通用6波段近似系数执行缨帽变换")

            # 按语义波段顺序抽取，而不是简单截取前6个波段
            band_data = [
                self._get_scaled_band_by_index(band_mapping[role]).flatten()
                for role in required_roles
            ]
            
            band_matrix = np.column_stack(band_data)
            
            # 计算缨帽变换
            tc_results = {}
            for component, coefficients in tc_coefficients.items():
                coef_array = np.array(coefficients[:len(band_data)])
                tc_value = np.dot(band_matrix, coef_array)
                tc_results[component] = tc_value.reshape(self.height, self.width)

            logger.info("缨帽变换计算完成")
            return tc_results
            
        except Exception as e:
            logger.error(f"计算缨帽变换失败: {e}")
            return None
    
    def calculate_rsei(self):
        """
        计算RSEI（遥感生态指数）
        基于标准四分量归一化和主成分分析的综合生态指数
        """
        try:
            greenness = self.calculate_greenness()
            wetness = self.calculate_wetness()
            dryness = self.calculate_dryness()
            heat = self.calculate_heat()

            if any(item is None for item in [greenness, wetness, dryness, heat]):
                raise ValueError("无法获取计算RSEI所需的全部分量")

            greenness_n = self._normalize_to_unit_interval(greenness)
            wetness_n = self._normalize_to_unit_interval(wetness)
            dryness_n = self._normalize_to_unit_interval(dryness)
            heat_n = self._normalize_to_unit_interval(heat)

            valid_mask = (
                np.isfinite(greenness_n) &
                np.isfinite(wetness_n) &
                np.isfinite(dryness_n) &
                np.isfinite(heat_n)
            )
            if not np.any(valid_mask):
                raise ValueError("没有有效像元用于计算RSEI")

            data_matrix = np.column_stack([
                greenness_n[valid_mask],
                wetness_n[valid_mask],
                dryness_n[valid_mask],
                heat_n[valid_mask],
            ])

            pca = PCA(n_components=4)
            pca_result = pca.fit_transform(data_matrix)
            pc1 = pca_result[:, 0]

            ecological_score = (
                greenness_n[valid_mask] +
                wetness_n[valid_mask] -
                dryness_n[valid_mask] -
                heat_n[valid_mask]
            )
            corr_matrix = np.corrcoef(pc1, ecological_score)
            pc1_corr = corr_matrix[0, 1] if corr_matrix.shape == (2, 2) else np.nan
            corrected_components = pca.components_.copy()
            if np.isfinite(pc1_corr) and pc1_corr < 0:
                pc1 = -pc1
                corrected_components[0] = -corrected_components[0]

            rsei_values = np.full(valid_mask.sum(), 0.0, dtype=np.float32)
            pc1_min = np.nanmin(pc1)
            pc1_max = np.nanmax(pc1)
            if pc1_max > pc1_min:
                rsei_values = ((pc1 - pc1_min) / (pc1_max - pc1_min)).astype(np.float32)

            rsei = np.full(greenness.shape, np.nan, dtype=np.float32)
            rsei[valid_mask] = rsei_values

            logger.info("RSEI计算完成")
            return {
                'rsei': rsei,
                'greenness': greenness_n,
                'wetness': wetness_n,
                'dryness': dryness_n,
                'heat': heat_n,
                'weights': corrected_components[0],
                'pca_components': corrected_components,
                'explained_variance': pca.explained_variance_ratio_,
            }
            
        except Exception as e:
            logger.error(f"计算RSEI失败: {e}")
            return None
    
    def calculate_statistics(self, index_data):
        """
        计算指数统计信息
        
        Args:
            index_data: 指数数据数组
        """
        try:
            if index_data is None:
                return None
            
            # 移除无效值
            valid_data = index_data[np.isfinite(index_data)]
            
            if len(valid_data) == 0:
                return None
            
            stats = {
                'min': float(np.min(valid_data)),
                'max': float(np.max(valid_data)),
                'mean': float(np.mean(valid_data)),
                'std': float(np.std(valid_data)),
                'median': float(np.median(valid_data)),
                'percentile_25': float(np.percentile(valid_data, 25)),
                'percentile_75': float(np.percentile(valid_data, 75)),
                'valid_pixels': int(len(valid_data)),
                'total_pixels': int(index_data.size),
                'valid_ratio': float(len(valid_data) / index_data.size)
            }
            
            # 分类统计（适用于NDVI等指数）
            if stats['min'] >= -1 and stats['max'] <= 1:
                # 五级分类
                thresholds = [-1, -0.2, 0, 0.2, 0.4, 1]
                labels = ['很差', '差', '中等', '良好', '优秀']
                
                for i, (threshold, label) in enumerate(zip(thresholds[:-1], labels)):
                    mask = (valid_data >= threshold) & (valid_data < thresholds[i+1])
                    stats[f'{label}_pixels'] = int(np.sum(mask))
                    stats[f'{label}_ratio'] = float(np.sum(mask) / len(valid_data))
            
            return stats
            
        except Exception as e:
            logger.error(f"计算统计信息失败: {e}")
            return None
    
    def save_result(self, index_data, output_path, index_name="index"):
        """
        保存计算结果为GeoTIFF文件
        
        Args:
            index_data: 指数数据数组
            output_path: 输出文件路径
            index_name: 指数名称
        """
        try:
            if index_data is None:
                raise ValueError("指数数据为空")
            
            # 创建输出目录
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 创建GeoTIFF文件
            driver = gdal.GetDriverByName('GTiff')
            out_dataset = driver.Create(
                output_path,
                self.width,
                self.height,
                1,  # 单波段
                gdal.GDT_Float32
            )
            
            if out_dataset is None:
                raise ValueError("无法创建输出文件")
            
            # 设置地理变换参数
            out_dataset.SetGeoTransform(self.geotransform)
            out_dataset.SetProjection(self.projection)
            
            # 写入数据
            out_band = out_dataset.GetRasterBand(1)
            out_band.WriteArray(index_data)
            
            # 设置元数据
            out_band.SetDescription(f"{index_name} Index")
            out_band.SetNoDataValue(np.nan)
            
            # 计算统计信息
            valid_data = index_data[np.isfinite(index_data)]
            if len(valid_data) > 0:
                out_band.SetStatistics(
                    float(np.min(valid_data)),
                    float(np.max(valid_data)),
                    float(np.mean(valid_data)),
                    float(np.std(valid_data))
                )
            
            # 刷新缓存
            out_band.FlushCache()
            out_dataset.FlushCache()
            
            # 关闭文件
            out_dataset = None
            
            logger.info(f"结果已保存到: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存结果失败: {e}")
            return False
    
    def create_visualization(self, index_data, index_name, output_path, colormap='RdYlGn'):
        """
        创建可视化图片
        
        Args:
            index_data: 指数数据数组
            index_name: 指数名称
            output_path: 输出图片路径
            colormap: 颜色映射
        """
        try:
            if index_data is None:
                raise ValueError("指数数据为空")
            
            # 创建输出目录
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 准备数据
            valid_data = index_data[np.isfinite(index_data)]
            if len(valid_data) == 0:
                raise ValueError("没有有效数据")

            height, width = index_data.shape
            raster_ratio = width / height if height else 1.0
            map_panel_weight = min(max(raster_ratio, 1.0), 2.8)
            
            # 创建图形
            fig, (ax1, ax2) = plt.subplots(
                1,
                2,
                figsize=(15, 6),
                gridspec_kw={'width_ratios': [map_panel_weight, 1.0]},
            )
            
            # 主图：指数分布
            im1 = ax1.imshow(
                index_data,
                cmap=colormap,
                vmin=np.min(valid_data),
                vmax=np.max(valid_data),
                aspect='equal',
                interpolation='nearest',
            )
            ax1.set_box_aspect(height / width)
            ax1.set_title(f'{index_name} 分布图')
            ax1.axis('off')
            
            # 添加颜色条
            cbar1 = plt.colorbar(im1, ax=ax1, shrink=0.8)
            cbar1.set_label(f'{index_name} 值')
            
            # 子图：直方图
            ax2.hist(valid_data, bins=50, alpha=0.7, color='skyblue', edgecolor='black')
            ax2.set_title(f'{index_name} 值分布直方图')
            ax2.set_xlabel(f'{index_name} 值')
            ax2.set_ylabel('像素数量')
            ax2.grid(True, alpha=0.3)
            
            # 添加统计信息
            stats_text = f"""
            统计信息:
            最小值: {np.min(valid_data):.4f}
            最大值: {np.max(valid_data):.4f}
            平均值: {np.mean(valid_data):.4f}
            标准差: {np.std(valid_data):.4f}
            有效像素: {len(valid_data):,}
            """
            ax2.text(0.02, 0.98, stats_text, transform=ax2.transAxes, 
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"可视化图片已保存到: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"创建可视化失败: {e}")
            return False
    
    def close(self):
        """关闭数据集"""
        if self.dataset is not None:
            self.dataset = None
            self._sensor_band_mapping = None
            self._scaled_band_cache = {}
            logger.info("数据集已关闭")


def calculate_all_indices(image_path, output_dir):
    """
    计算所有生态指数的便捷函数
    
    Args:
        image_path: 输入影像路径
        output_dir: 输出目录
    """
    try:
        # 创建计算器
        calculator = GDALEcologicalIndexCalculator(image_path)
        
        # 加载影像
        if not calculator.load_image():
            raise ValueError("无法加载影像")
        
        # 获取波段信息
        band_info = calculator.get_band_info()
        logger.info(f"波段信息: {json.dumps(band_info, indent=2, default=str)}")
        
        # 计算各种指数
        indices = {}
        results = {}
        
        # NDVI
        ndvi = calculator.calculate_ndvi()
        if ndvi is not None:
            indices['NDVI'] = ndvi
            results['NDVI'] = calculator.calculate_statistics(ndvi)
            
            # 保存结果
            ndvi_path = os.path.join(output_dir, 'ndvi.tif')
            calculator.save_result(ndvi, ndvi_path, 'NDVI')
            
            # 创建可视化
            vis_path = os.path.join(output_dir, 'ndvi_visualization.png')
            calculator.create_visualization(ndvi, 'NDVI', vis_path, 'RdYlGn')
        
        # NDWI
        ndwi = calculator.calculate_ndwi()
        if ndwi is not None:
            indices['NDWI'] = ndwi
            results['NDWI'] = calculator.calculate_statistics(ndwi)
            
            ndwi_path = os.path.join(output_dir, 'ndwi.tif')
            calculator.save_result(ndwi, ndwi_path, 'NDWI')
            
            vis_path = os.path.join(output_dir, 'ndwi_visualization.png')
            calculator.create_visualization(ndwi, 'NDWI', vis_path, 'Blues')
        
        # NDBI
        ndbi = calculator.calculate_ndbi()
        if ndbi is not None:
            indices['NDBI'] = ndbi
            results['NDBI'] = calculator.calculate_statistics(ndbi)
            
            ndbi_path = os.path.join(output_dir, 'ndbi.tif')
            calculator.save_result(ndbi, ndbi_path, 'NDBI')
            
            vis_path = os.path.join(output_dir, 'ndbi_visualization.png')
            calculator.create_visualization(ndbi, 'NDBI', vis_path, 'Reds')
        
        # NDSI
        ndsi = calculator.calculate_ndsi()
        if ndsi is not None:
            indices['NDSI'] = ndsi
            results['NDSI'] = calculator.calculate_statistics(ndsi)
            
            ndsi_path = os.path.join(output_dir, 'ndsi.tif')
            calculator.save_result(ndsi, ndsi_path, 'NDSI')
            
            vis_path = os.path.join(output_dir, 'ndsi_visualization.png')
            calculator.create_visualization(ndsi, 'NDSI', vis_path, 'Blues')
        
        # RSEI
        rsei_result = calculator.calculate_rsei()
        if rsei_result is not None:
            indices['RSEI'] = rsei_result['rsei']
            results['RSEI'] = calculator.calculate_statistics(rsei_result['rsei'])
            
            # 保存RSEI结果
            rsei_path = os.path.join(output_dir, 'rsei.tif')
            calculator.save_result(rsei_result['rsei'], rsei_path, 'RSEI')
            
            vis_path = os.path.join(output_dir, 'rsei_visualization.png')
            calculator.create_visualization(rsei_result['rsei'], 'RSEI', vis_path, 'RdYlGn')
            
            # 保存分量
            for component in ['greenness', 'wetness', 'dryness', 'heat']:
                if component in rsei_result:
                    comp_data = rsei_result[component]
                    comp_path = os.path.join(output_dir, f'rsei_{component}.tif')
                    calculator.save_result(comp_data, comp_path, f'RSEI_{component.upper()}')
        
        # 保存统计结果
        stats_path = os.path.join(output_dir, 'statistics.json')
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        # 关闭计算器
        calculator.close()
        
        logger.info(f"所有指数计算完成，结果保存在: {output_dir}")
        return results
        
    except Exception as e:
        logger.error(f"计算所有指数失败: {e}")
        return None


if __name__ == "__main__":
    # 测试代码
    import sys
    
    if len(sys.argv) != 3:
        print("用法: python gdal_ecological_indices.py <input_image> <output_dir>")
        sys.exit(1)
    
    input_image = sys.argv[1]
    output_dir = sys.argv[2]
    
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    # 计算所有指数
    results = calculate_all_indices(input_image, output_dir)
    
    if results:
        print("计算完成！")
        for index_name, stats in results.items():
            print(f"\n{index_name}:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
    else:
        print("计算失败！") 
