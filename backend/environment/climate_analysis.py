"""
气候数据分析模块
提供CSV/Excel文件解析、数据统计分析和图表数据生成功能
"""

import pandas as pd
import numpy as np
import json
import logging
import os
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from django.core.files.base import ContentFile
from io import StringIO, BytesIO
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
from datetime import datetime
import rasterio
try:
    import seaborn as sns
except ImportError:
    sns = None

from .raster_processing import prepare_raster_upload, raster_band_statistics, preview_array, remove_tree

logger = logging.getLogger(__name__)

DEFAULT_CLIMATE_MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024
DEFAULT_CLIMATE_MAX_ROWS = 200000

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class ClimateDataAnalyzer:
    """气候数据分析器"""
    
    def __init__(self, file_path: str, file_type: str):
        """
        初始化分析器
        
        Args:
            file_path: 文件路径
            file_type: 文件类型 ('csv' 或 'xlsx')
        """
        self.file_path = file_path
        self.file_type = file_type
        self.df = None
        self.analysis_result = {}
        
    def validate_file_path(self) -> Tuple[bool, str]:
        """
        验证文件路径
        
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if not self.file_path:
            return False, "文件路径为空"
        
        if not os.path.exists(self.file_path):
            return False, f"文件不存在: {self.file_path}"
        
        if not os.path.isfile(self.file_path):
            return False, f"路径不是文件: {self.file_path}"
        
        # 检查文件大小
        file_size = os.path.getsize(self.file_path)
        if file_size == 0:
            return False, "文件为空"
        
        max_size = DEFAULT_CLIMATE_MAX_FILE_SIZE
        if file_size > max_size:
            return False, f"文件过大: {file_size / (1024*1024):.2f}MB > {max_size / (1024*1024*1024):.1f}GB"
        
        return True, ""
    
    def validate_dataframe(self) -> Tuple[bool, str]:
        """
        验证DataFrame数据
        
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if self.df is None:
            return False, "DataFrame未初始化"
        
        if self.df.empty:
            return False, "数据文件为空"
        
        # 检查行数
        if len(self.df) < 2:
            return False, "数据行数不足，至少需要2行数据"
        
        if len(self.df) > DEFAULT_CLIMATE_MAX_ROWS:
            return False, f"数据行数过多: {len(self.df)} > {DEFAULT_CLIMATE_MAX_ROWS}"
        
        # 检查必需的列（支持中英文列名）
        required_columns_en = ['Date', 'Temperature', 'Precipitation', 'Humidity', 'WindSpeed']
        required_columns_zh = ['日期', '温度(°C)', '降水量(mm)', '湿度(%)', '风速(m/s)']
        
        # 创建列名映射（映射到小写，与_preprocess_data保持一致）
        column_mapping = {
            'Date': 'date',
            'Temperature': 'temperature', 
            'Precipitation': 'precipitation',
            'Humidity': 'humidity',
            'WindSpeed': 'wind_speed',
            '日期': 'date',
            '温度(°C)': 'temperature',
            '降水量(mm)': 'precipitation', 
            '湿度(%)': 'humidity',
            '风速(m/s)': 'wind_speed'
        }
        
        missing_columns = []
        found_columns = []
        
        # 检查是否有任何可识别的列名
        for col_en in required_columns_en:
            if col_en in self.df.columns:
                found_columns.append(col_en)
            elif column_mapping.get(col_en) in self.df.columns:
                found_columns.append(col_en)
        
        # 检查中文列名
        for col_zh in required_columns_zh:
            if col_zh in self.df.columns:
                found_columns.append(col_zh)
        
        # 检查是否找到了所有必需的列
        if len(found_columns) < len(required_columns_en):
            missing_columns = []
            for col_en in required_columns_en:
                if col_en not in found_columns and column_mapping.get(col_en) not in [col for col in self.df.columns]:
                    missing_columns.append(f"{col_en} 或 {column_mapping.get(col_en, '')}")
            
            if missing_columns:
                return False, f"缺少必需的列: {missing_columns}"
        
        # 重命名列为标准小写列名
        self.df = self.df.rename(columns=column_mapping)
        
        # 检查数据类型
        numeric_columns = ['temperature', 'precipitation', 'humidity', 'wind_speed']
        for col in numeric_columns:
            if col in self.df.columns:
                # 尝试转换为数值类型
                try:
                    self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
                    # 检查是否有太多NaN值
                    nan_count = self.df[col].isna().sum()
                    if nan_count > len(self.df) * 0.5:  # 超过50%的NaN
                        return False, f"列 {col} 中缺失值过多: {nan_count}/{len(self.df)}"
                except Exception as e:
                    return False, f"列 {col} 数据类型转换失败: {str(e)}"
        
        return True, ""

    def load_data(self) -> bool:
        """
        加载数据文件
        
        Returns:
            bool: 加载是否成功
        """
        try:
            # 验证文件路径
            is_valid, error_msg = self.validate_file_path()
            if not is_valid:
                logger.error(f"文件路径验证失败: {error_msg}")
                return False
            
            # 加载数据
            if self.file_type.lower() == 'csv':
                # 尝试不同的编码格式
                encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
                for encoding in encodings:
                    try:
                        self.df = pd.read_csv(self.file_path, encoding=encoding)
                        logger.info(f"成功使用 {encoding} 编码加载CSV文件")
                        break
                    except UnicodeDecodeError:
                        continue
                    except Exception as e:
                        logger.warning(f"使用 {encoding} 编码加载失败: {str(e)}")
                        continue
                else:
                    raise ValueError("无法使用任何编码格式读取CSV文件")
            elif self.file_type.lower() == 'xlsx':
                try:
                    self.df = pd.read_excel(self.file_path)
                    logger.info("成功加载Excel文件")
                except Exception as e:
                    raise ValueError(f"Excel文件读取失败: {str(e)}")
            else:
                raise ValueError(f"不支持的文件类型: {self.file_type}")
            
            # 验证DataFrame
            is_valid, error_msg = self.validate_dataframe()
            if not is_valid:
                logger.error(f"DataFrame验证失败: {error_msg}")
                return False
            
            # 数据预处理
            self._preprocess_data()
            
            logger.info(f"数据加载完成，共 {len(self.df)} 行数据")
            return True
            
        except Exception as e:
            logger.error(f"加载数据文件失败: {str(e)}")
            return False
    
    def _preprocess_data(self):
        """数据预处理"""
        if self.df is None:
            return
        
        # 标准化列名
        column_mapping = {
            '日期': 'date',
            '温度': 'temperature',
            '温度(°C)': 'temperature',
            '降水量': 'precipitation',
            '降水量(mm)': 'precipitation',
            '湿度': 'humidity',
            '湿度(%)': 'humidity',
            '风速': 'wind_speed',
            '风速(m/s)': 'wind_speed'
        }
        
        # 重命名列
        self.df = self.df.rename(columns=column_mapping)
        
        # 确保日期列是datetime类型
        if 'date' in self.df.columns:
            self.df['date'] = pd.to_datetime(self.df['date'], errors='coerce')
        
        # 删除包含NaN的行
        self.df = self.df.dropna()
        
        logger.info(f"数据预处理完成，共 {len(self.df)} 行数据")
    
    def calculate_statistics(self) -> Dict:
        """
        计算统计数据
        
        Returns:
            Dict: 统计数据字典
        """
        if self.df is None:
            return {}
        
        stats = {}
        
        # 温度统计
        if 'temperature' in self.df.columns:
            temp_data = pd.to_numeric(self.df['temperature'], errors='coerce').dropna()
            stats['temperature'] = {
                'avg': round(temp_data.mean(), 2),
                'max': round(temp_data.max(), 2),
                'min': round(temp_data.min(), 2),
                'std': round(temp_data.std(), 2)
            }
        
        # 降水量统计
        if 'precipitation' in self.df.columns:
            prec_data = pd.to_numeric(self.df['precipitation'], errors='coerce').dropna()
            stats['precipitation'] = {
                'avg': round(prec_data.mean(), 2),
                'max': round(prec_data.max(), 2),
                'min': round(prec_data.min(), 2),
                'std': round(prec_data.std(), 2)
            }
        
        # 湿度统计
        if 'humidity' in self.df.columns:
            hum_data = pd.to_numeric(self.df['humidity'], errors='coerce').dropna()
            stats['humidity'] = {
                'avg': round(hum_data.mean(), 2),
                'max': round(hum_data.max(), 2),
                'min': round(hum_data.min(), 2),
                'std': round(hum_data.std(), 2)
            }
        
        # 风速统计
        if 'wind_speed' in self.df.columns:
            wind_data = pd.to_numeric(self.df['wind_speed'], errors='coerce').dropna()
            stats['wind_speed'] = {
                'avg': round(wind_data.mean(), 2),
                'max': round(wind_data.max(), 2),
                'min': round(wind_data.min(), 2),
                'std': round(wind_data.std(), 2)
            }
        
        return stats
    
    def generate_chart_data(self) -> Dict:
        """
        生成图表数据
        
        Returns:
            Dict: 图表数据字典
        """
        if self.df is None:
            return {}
        
        chart_data = {}
        
        # 温度数据
        if 'temperature' in self.df.columns:
            temp_data = pd.to_numeric(self.df['temperature'], errors='coerce').dropna()
            chart_data['temperature'] = temp_data.tolist()
        
        # 降水量数据
        if 'precipitation' in self.df.columns:
            prec_data = pd.to_numeric(self.df['precipitation'], errors='coerce').dropna()
            chart_data['precipitation'] = prec_data.tolist()
        
        # 湿度数据
        if 'humidity' in self.df.columns:
            hum_data = pd.to_numeric(self.df['humidity'], errors='coerce').dropna()
            chart_data['humidity'] = hum_data.tolist()
        
        # 风速数据
        if 'wind_speed' in self.df.columns:
            wind_data = pd.to_numeric(self.df['wind_speed'], errors='coerce').dropna()
            chart_data['wind_speed'] = wind_data.tolist()
        
        return chart_data
    
    def generate_visualizations(self) -> Dict[str, str]:
        """
        生成可视化图表
        
        Returns:
            Dict[str, str]: 图表文件路径字典
        """
        if self.df is None:
            return {}
        
        charts = {}
        
        try:
            # 设置图表样式
            plt.style.use('seaborn-v0_8')
            fig_size = (10, 6)
            
            # 温度趋势图
            if 'temperature' in self.df.columns:
                temp_data = pd.to_numeric(self.df['temperature'], errors='coerce').dropna()
                if len(temp_data) > 0:
                    plt.figure(figsize=fig_size)
                    plt.plot(range(len(temp_data)), temp_data, 'b-', linewidth=2, marker='o', markersize=4)
                    plt.title('温度趋势分析', fontsize=16, fontweight='bold')
                    plt.xlabel('时间序列', fontsize=12)
                    plt.ylabel('温度 (°C)', fontsize=12)
                    plt.grid(True, alpha=0.3)
                    plt.tight_layout()
                    
                    # 保存图表
                    temp_buffer = BytesIO()
                    plt.savefig(temp_buffer, format='png', dpi=300, bbox_inches='tight')
                    temp_buffer.seek(0)
                    charts['temperature'] = temp_buffer
                    plt.close()
            
            # 降水量柱状图
            if 'precipitation' in self.df.columns:
                prec_data = pd.to_numeric(self.df['precipitation'], errors='coerce').dropna()
                if len(prec_data) > 0:
                    plt.figure(figsize=fig_size)
                    plt.bar(range(len(prec_data)), prec_data, color='skyblue', alpha=0.7)
                    plt.title('降水量统计', fontsize=16, fontweight='bold')
                    plt.xlabel('时间序列', fontsize=12)
                    plt.ylabel('降水量 (mm)', fontsize=12)
                    plt.grid(True, alpha=0.3)
                    plt.tight_layout()
                    
                    prec_buffer = BytesIO()
                    plt.savefig(prec_buffer, format='png', dpi=300, bbox_inches='tight')
                    prec_buffer.seek(0)
                    charts['precipitation'] = prec_buffer
                    plt.close()
            
            # 湿度面积图
            if 'humidity' in self.df.columns:
                hum_data = pd.to_numeric(self.df['humidity'], errors='coerce').dropna()
                if len(hum_data) > 0:
                    plt.figure(figsize=fig_size)
                    plt.fill_between(range(len(hum_data)), hum_data, alpha=0.6, color='green')
                    plt.plot(range(len(hum_data)), hum_data, 'g-', linewidth=2)
                    plt.title('湿度变化', fontsize=16, fontweight='bold')
                    plt.xlabel('时间序列', fontsize=12)
                    plt.ylabel('湿度 (%)', fontsize=12)
                    plt.grid(True, alpha=0.3)
                    plt.tight_layout()
                    
                    hum_buffer = BytesIO()
                    plt.savefig(hum_buffer, format='png', dpi=300, bbox_inches='tight')
                    hum_buffer.seek(0)
                    charts['humidity'] = hum_buffer
                    plt.close()
            
            # 风速雷达图
            if 'wind_speed' in self.df.columns:
                wind_data = pd.to_numeric(self.df['wind_speed'], errors='coerce').dropna()
                if len(wind_data) > 0:
                    plt.figure(figsize=(8, 8))
                    angles = np.linspace(0, 2 * np.pi, len(wind_data), endpoint=False)
                    values = wind_data.tolist()
                    values += values[:1]  # 闭合图形
                    angles = np.concatenate((angles, [angles[0]]))
                    
                    ax = plt.subplot(111, projection='polar')
                    ax.plot(angles, values, 'o-', linewidth=2, color='red')
                    ax.fill(angles, values, alpha=0.25, color='red')
                    ax.set_title('风速分析', fontsize=16, fontweight='bold', pad=20)
                    ax.grid(True)
                    
                    wind_buffer = BytesIO()
                    plt.savefig(wind_buffer, format='png', dpi=300, bbox_inches='tight')
                    wind_buffer.seek(0)
                    charts['wind_speed'] = wind_buffer
                    plt.close()
            
        except Exception as e:
            logger.error(f"生成可视化图表失败: {str(e)}")
        
        return charts
    
    def analyze(self) -> Dict:
        """
        执行完整的数据分析
        
        Returns:
            Dict: 分析结果字典
        """
        if not self.load_data():
            return {'error': '数据加载失败'}
        
        # 计算统计数据
        statistics = self.calculate_statistics()
        
        # 生成图表数据
        chart_data = self.generate_chart_data()
        
        # 生成可视化图表
        charts = self.generate_visualizations()
        
        result = {
            'statistics': statistics,
            'chart_data': chart_data,
            'charts': charts,
            'data_count': len(self.df) if self.df is not None else 0
        }
        
        return result


def analyze_climate_data(file_path: str, file_type: str, preferred_metric: Optional[str] = None) -> Dict:
    """
    分析气候数据的便捷函数
    
    Args:
        file_path: 文件路径
        file_type: 文件类型
        
    Returns:
        Dict: 分析结果
    """
    if file_type.lower() in ['tif', 'tiff', 'zip']:
        if file_type.lower() == 'zip':
            zip_source_type = _inspect_zip_source_type(file_path)
            if zip_source_type == ZIP_SOURCE_SHAPEFILE:
                return analyze_climate_vector(file_path, preferred_metric=preferred_metric)
            if zip_source_type == ZIP_SOURCE_UNKNOWN:
                return {'error': 'ZIP 文件未识别为 ADF 栅格目录，也不是完整的 Shapefile 压缩包'}
        return analyze_climate_raster(file_path, file_type, preferred_metric=preferred_metric)

    analyzer = ClimateDataAnalyzer(file_path, file_type)
    return analyzer.analyze()


NON_CLIMATE_KEYWORDS = [
    'ndvi', 'ndwi', 'ndbi', 'ndsi', 'rsei',
    'dryness', 'wetness', 'greenness', 'heat',
    '干度', '湿度指数', '绿度', '热度', '生态指数',
    '归一化干度', '归一化湿度', '归一化植被', '归一化建筑', '归一化水体',
    '遥感', '生态', '植被指数', '建筑指数', '水体指数',
]

CLIMATE_METRIC_FIELD_ALIASES = {
    'temperature': [
        'temperature', 'temp', 'tmean', 'tavg', 'avgtemp', 'meantemp',
        'airtemperature', 'surfaceairtemperature',
        '气温', '平均气温', '均温', '温度', '年均温', '月均温', '日均温', '最高气温', '最低气温'
    ],
    'precipitation': [
        'precipitation', 'precip', 'rain', 'rainfall', 'ppt', 'pre',
        '降水', '降水量', '降雨', '降雨量', '雨量', '累计降水'
    ],
    'humidity': [
        'humidity', 'relativehumidity', 'rh', 'humid',
        '湿度', '相对湿度', '空气湿度'
    ],
    'wind_speed': [
        'windspeed', 'windvelocity', 'wind', 'ws', 'avgwind',
        '风速', '平均风速', '风力'
    ],
}

CLIMATE_MISSING_VALUE_SENTINELS = [9999, 9999.0, 9999.9, 99999, 99999.0, -9999, -9999.0]

ZIP_SOURCE_SHAPEFILE = 'shapefile_zip'
ZIP_SOURCE_ADF = 'adf_zip'
ZIP_SOURCE_UNKNOWN = 'unknown_zip'


def _normalize_climate_field_name(name: str) -> str:
    text = str(name or '').strip().lower()
    text = re.sub(r'[\s_\-（）()\[\]{}【】.:：/\\]+', '', text)
    text = text.replace('℃', '').replace('°c', '').replace('%', '').replace('mm', '').replace('m/s', '')
    return text


def _infer_metric_from_field_name(field_name: str) -> Optional[str]:
    normalized = _normalize_climate_field_name(field_name)
    if not normalized:
        return None

    for metric, aliases in CLIMATE_METRIC_FIELD_ALIASES.items():
        for alias in aliases:
            if _normalize_climate_field_name(alias) in normalized:
                return metric
    return None


def _extract_year_from_climate_field_name(field_name: str) -> Optional[int]:
    text = str(field_name or '').strip()
    if re.fullmatch(r'(?:19|20)\d{2}', text):
        year = int(text)
        if 1800 <= year <= 2100:
            return year
    return None


def _detect_year_value_fields(columns: List[str]) -> List[Tuple[int, str]]:
    year_fields = []
    for column in columns:
        year = _extract_year_from_climate_field_name(column)
        if year is not None:
            year_fields.append((year, column))
    return sorted(year_fields, key=lambda item: item[0])


def _infer_metric_from_context(*paths_or_names: str) -> Optional[str]:
    for value in paths_or_names:
        if not value:
            continue
        metric = _infer_climate_metric(str(value))
        if metric in {'temperature', 'precipitation', 'humidity', 'wind_speed'}:
            return metric
    return None


def _clean_climate_numeric_series(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors='coerce')
    numeric = numeric.replace(CLIMATE_MISSING_VALUE_SENTINELS, np.nan)
    # 气象站资料常用 9999.9 一类大值代表缺测；正常气候变量不会接近这个量级。
    numeric = numeric.mask(numeric.abs() >= 9990)
    return numeric.dropna()


def _inspect_zip_source_type(file_path: str) -> str:
    try:
        if not zipfile.is_zipfile(file_path):
            return ZIP_SOURCE_UNKNOWN

        with zipfile.ZipFile(file_path, 'r') as zf:
            names = [member.filename.lower() for member in zf.infolist() if not member.is_dir()]

        has_shp = any(name.endswith('.shp') for name in names)
        has_dbf = any(name.endswith('.dbf') for name in names)
        has_shx = any(name.endswith('.shx') for name in names)
        if has_shp and has_dbf and has_shx:
            return ZIP_SOURCE_SHAPEFILE

        if any(name.endswith('.adf') for name in names):
            return ZIP_SOURCE_ADF
    except Exception as exc:
        logger.warning(f"识别ZIP来源类型失败: {exc}")

    return ZIP_SOURCE_UNKNOWN


def _extract_shapefile_zip_for_analysis(zip_path: str) -> Tuple[str, str]:
    extract_dir = tempfile.mkdtemp(prefix='climate_shp_', dir=os.path.dirname(zip_path))
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for member in zf.infolist():
                member_name = member.filename
                if os.path.isabs(member_name) or '..' in Path(member_name).parts:
                    continue
                zf.extract(member, extract_dir)

        shp_candidates = []
        for root, _, files in os.walk(extract_dir):
            for file_name in files:
                if file_name.lower().endswith('.shp'):
                    shp_candidates.append(os.path.join(root, file_name))

        if not shp_candidates:
            raise ValueError('ZIP 中未找到可用的 .shp 文件')

        shp_path = sorted(shp_candidates, key=lambda item: len(Path(item).parts))[0]
        return shp_path, extract_dir
    except Exception:
        remove_tree(extract_dir)
        raise


def _load_shapefile_dataframe(shp_path: str) -> pd.DataFrame:
    try:
        from osgeo import ogr
    except ImportError as exc:
        raise RuntimeError('当前环境缺少 GDAL/OGR，无法读取 Shapefile 属性表') from exc

    datasource = ogr.Open(shp_path)
    if datasource is None:
        raise ValueError(f'无法打开 Shapefile: {shp_path}')

    layer = datasource.GetLayer(0)
    if layer is None:
        raise ValueError(f'Shapefile 图层为空: {shp_path}')

    layer_defn = layer.GetLayerDefn()
    field_names = [layer_defn.GetFieldDefn(i).GetNameRef() for i in range(layer_defn.GetFieldCount())]
    records = []
    feature = layer.GetNextFeature()
    while feature is not None:
        record = {field_name: feature.GetField(field_name) for field_name in field_names}
        records.append(record)
        feature = layer.GetNextFeature()

    datasource = None
    return pd.DataFrame(records)


def _detect_climate_metric_fields(columns: List[str]) -> Dict[str, List[str]]:
    mapping = {metric: [] for metric in CLIMATE_METRIC_FIELD_ALIASES.keys()}
    for column in columns:
        metric = _infer_metric_from_field_name(column)
        if metric:
            mapping[metric].append(column)
    return {metric: fields for metric, fields in mapping.items() if fields}


def _sample_series_values(series: pd.Series, max_points: int = 240) -> List[float]:
    cleaned = _clean_climate_numeric_series(series)
    if cleaned.empty:
        return []
    values = cleaned.to_numpy(dtype=float)
    if values.size > max_points:
        indices = np.linspace(0, values.size - 1, max_points).astype(int)
        values = values[indices]
    return [round(float(value), 4) for value in values.tolist()]


def _build_year_wide_vector_analysis(
    df: pd.DataFrame,
    year_fields: List[Tuple[int, str]],
    metric: str,
    capability: Dict,
    file_path: str,
) -> Dict:
    yearly_values = []
    yearly_labels = []
    merged_values = []

    for year, field_name in year_fields:
        cleaned = _clean_climate_numeric_series(df[field_name])
        if cleaned.empty:
            continue

        yearly_labels.append(year)
        yearly_values.append(round(float(cleaned.mean()), 4))
        merged_values.append(cleaned)

    if not merged_values:
        return {
            'error': 'Shapefile 年份属性字段中未解析出有效气候值，可能全部为缺测值 9999.9。',
            'capabilities': capability,
        }

    merged_series = pd.concat(merged_values, ignore_index=True)
    statistics = {
        metric: {
            'avg': round(float(merged_series.mean()), 4),
            'max': round(float(merged_series.max()), 4),
            'min': round(float(merged_series.min()), 4),
            'std': round(float(merged_series.std(ddof=1)) if len(merged_series) > 1 else 0.0, 4),
        }
    }
    chart_data = {
        metric: yearly_values,
        'vector_metadata': {
            'filename': os.path.basename(file_path),
            'feature_count': int(len(df)),
            'source_type': 'vector_attribute_table',
            'table_layout': 'year_wide',
            'available_metrics': [metric],
            'field_mapping': {metric: [field_name for _, field_name in year_fields]},
            'detected_category': capability.get('detected_category'),
            'year_labels': yearly_labels,
            'year_range': [min(yearly_labels), max(yearly_labels)] if yearly_labels else None,
            'valid_year_count': len(yearly_labels),
            'missing_value_rule': '9999/9999.9/-9999 已按缺测剔除',
        }
    }

    return {
        'statistics': statistics,
        'chart_data': chart_data,
        'charts': {},
        'data_count': int(len(merged_series)),
    }


def detect_climate_vector_capabilities(file_path: str) -> Dict:
    cleanup_dir = None
    try:
        shp_path, cleanup_dir = _extract_shapefile_zip_for_analysis(file_path)
        df = _load_shapefile_dataframe(shp_path)
        field_mapping = _detect_climate_metric_fields(df.columns.tolist())
        year_fields = _detect_year_value_fields(df.columns.tolist())
        year_table_metric = _infer_metric_from_context(file_path, shp_path)
        if year_fields and year_table_metric:
            field_mapping = {year_table_metric: [field_name for _, field_name in year_fields]}

        supported_metrics = list(field_mapping.keys())
        inferred_metric = supported_metrics[0] if len(supported_metrics) == 1 else None

        if not supported_metrics:
            has_year_table = bool(year_fields)
            return {
                'detected_mode': 'vector_attribute_table',
                'inferred_metric': None,
                'supported_metrics': ['temperature', 'precipitation', 'humidity', 'wind_speed'] if has_year_table else [],
                'unsupported_for_climate': not has_year_table,
                'manual_selection_required': has_year_table,
                'detected_category': 'shapefile_year_wide_table' if has_year_table else 'shapefile_attribute_table',
                'reason': (
                    '已识别出年份字段，但无法从文件名判断是温度、降水、湿度还是风速，请手动选择指标后再分析。'
                    if has_year_table
                    else '已识别为 Shapefile 属性表，但未检测到温度、降水、湿度或风速字段，请检查字段命名。'
                ),
                'filename_hint': os.path.basename(file_path).lower(),
                'source_type': ZIP_SOURCE_SHAPEFILE,
                'field_mapping': {},
                'year_fields': [year for year, _ in year_fields],
            }

        return {
            'detected_mode': 'vector_attribute_table',
            'inferred_metric': inferred_metric,
            'supported_metrics': supported_metrics,
            'unsupported_for_climate': False,
            'manual_selection_required': False,
            'detected_category': 'shapefile_year_wide_table' if year_fields else 'shapefile_attribute_table',
            'reason': None,
            'filename_hint': os.path.basename(file_path).lower(),
            'source_type': ZIP_SOURCE_SHAPEFILE,
            'field_mapping': field_mapping,
            'year_fields': [year for year, _ in year_fields],
        }
    finally:
        if cleanup_dir:
            remove_tree(cleanup_dir)


def detect_climate_file_capabilities(file_path: str, file_type: Optional[str] = None) -> Dict:
    normalized_type = str(file_type or Path(file_path).suffix.lstrip('.')).lower()
    if normalized_type == 'zip':
        source_type = _inspect_zip_source_type(file_path)
        if source_type == ZIP_SOURCE_SHAPEFILE:
            return detect_climate_vector_capabilities(file_path)
        if source_type == ZIP_SOURCE_ADF:
            capability = detect_climate_raster_capabilities(file_path)
            capability['source_type'] = ZIP_SOURCE_ADF
            return capability
        return {
            'detected_mode': 'unknown',
            'inferred_metric': None,
            'supported_metrics': [],
            'unsupported_for_climate': True,
            'manual_selection_required': False,
            'detected_category': 'unknown_zip',
            'reason': 'ZIP 文件未识别为 ADF 栅格目录，也不是完整的 Shapefile 压缩包。',
            'filename_hint': os.path.basename(file_path).lower(),
            'source_type': ZIP_SOURCE_UNKNOWN,
        }

    capability = detect_climate_raster_capabilities(file_path)
    capability['source_type'] = 'single_metric_raster'
    return capability


def detect_climate_raster_capabilities(file_path):
    name = os.path.basename(file_path).lower()
    metric = _infer_climate_metric(file_path)
    climate_metrics = ['temperature', 'precipitation', 'humidity', 'wind_speed']
    reason = None
    unsupported_for_climate = False
    manual_selection_required = False
    detected_category = 'climate_metric'
    supported_metrics = []
    inferred_metric = None

    if metric == 'remote_sensing_index':
        unsupported_for_climate = True
        detected_category = 'remote_sensing_index'
        reason = '检测到该文件更像遥感生态指数栅格，不属于气候监测统计的温度/降水/湿度/风速变量。'
    elif metric == 'unknown':
        manual_selection_required = True
        detected_category = 'unknown_climate_raster'
        supported_metrics = climate_metrics
        reason = '当前文件未包含明确变量名，无法自动判断是温度、降水、湿度还是风速，请先手动选择后再分析。'
    else:
        inferred_metric = metric
        supported_metrics = [metric]

    return {
        'detected_mode': 'single_metric_raster',
        'inferred_metric': inferred_metric,
        'supported_metrics': supported_metrics,
        'unsupported_for_climate': unsupported_for_climate,
        'manual_selection_required': manual_selection_required,
        'detected_category': detected_category,
        'reason': reason,
        'filename_hint': name,
    }


def _infer_climate_metric(file_path):
    name = os.path.basename(file_path).lower()
    if any(key in name for key in NON_CLIMATE_KEYWORDS):
        return 'remote_sensing_index'
    if any(key in name for key in ['降水', '降雨', '雨量', 'precip', 'rain']):
        return 'precipitation'
    if any(key in name for key in ['湿度', 'humidity', 'wet']):
        return 'humidity'
    if any(key in name for key in ['风速', 'wind']):
        return 'wind_speed'
    if any(key in name for key in ['气温', '平均气温', '均温', '温度', '地温', 'lst', 'temp']):
        return 'temperature'
    return 'unknown'


def _sample_raster_values(path, max_points=240):
    data = preview_array(path, max_size=700)
    valid = data[np.isfinite(data)]
    if valid.size == 0:
        return []
    if valid.size > max_points:
        indices = np.linspace(0, valid.size - 1, max_points).astype(int)
        valid = valid[indices]
    return [round(float(value), 4) for value in valid]


def analyze_climate_vector(file_path: str, preferred_metric: Optional[str] = None) -> Dict:
    cleanup_dir = None
    try:
        shp_path, cleanup_dir = _extract_shapefile_zip_for_analysis(file_path)
        df = _load_shapefile_dataframe(shp_path)
        if df.empty:
            return {'error': 'Shapefile 属性表为空，无法进行气候统计分析'}

        field_mapping = _detect_climate_metric_fields(df.columns.tolist())
        year_fields = _detect_year_value_fields(df.columns.tolist())
        year_table_metric = _infer_metric_from_context(file_path, shp_path)
        if year_fields and year_table_metric:
            field_mapping = {year_table_metric: [field_name for _, field_name in year_fields]}

        capability = {
            'detected_mode': 'vector_attribute_table',
            'inferred_metric': list(field_mapping.keys())[0] if len(field_mapping) == 1 else None,
            'supported_metrics': list(field_mapping.keys()) or (['temperature', 'precipitation', 'humidity', 'wind_speed'] if year_fields else []),
            'unsupported_for_climate': not bool(field_mapping) and not bool(year_fields),
            'manual_selection_required': False,
            'detected_category': 'shapefile_year_wide_table' if year_fields else 'shapefile_attribute_table',
            'reason': None if (field_mapping or year_fields) else '已识别为 Shapefile 属性表，但未检测到温度、降水、湿度或风速字段，请检查字段命名。',
            'filename_hint': os.path.basename(file_path).lower(),
            'source_type': ZIP_SOURCE_SHAPEFILE,
            'field_mapping': field_mapping,
            'year_fields': [year for year, _ in year_fields],
        }
        if capability.get('unsupported_for_climate'):
            return {
                'error': capability.get('reason') or '当前 Shapefile 未识别出可用的气候统计字段',
                'capabilities': capability,
            }

        target_metric = preferred_metric
        if target_metric == 'wind':
            target_metric = 'wind_speed'

        if year_fields:
            metric = year_table_metric or target_metric
            if not metric or metric not in {'temperature', 'precipitation', 'humidity', 'wind_speed'}:
                return {
                    'error': '当前 Shapefile 是年份宽表，但无法判断指标类型，请选择温度、降水、湿度或风速后再分析。',
                    'capabilities': {
                        **capability,
                        'manual_selection_required': True,
                        'supported_metrics': ['temperature', 'precipitation', 'humidity', 'wind_speed'],
                    },
                }

            capability['inferred_metric'] = metric
            capability['supported_metrics'] = [metric]
            capability['field_mapping'] = {metric: [field_name for _, field_name in year_fields]}
            return _build_year_wide_vector_analysis(
                df=df,
                year_fields=year_fields,
                metric=metric,
                capability=capability,
                file_path=file_path,
            )

        metric_fields = field_mapping
        if target_metric and target_metric in {'temperature', 'precipitation', 'humidity', 'wind_speed'}:
            if target_metric not in metric_fields:
                return {
                    'error': f'当前 Shapefile 属性表中未识别出“{target_metric}”对应字段',
                    'capabilities': capability,
                }
            metric_fields = {target_metric: metric_fields[target_metric]}

        statistics = {}
        chart_data = {}
        for metric, fields in metric_fields.items():
            series_list = []
            for field_name in fields:
                numeric_series = _clean_climate_numeric_series(df[field_name])
                if not numeric_series.empty:
                    series_list.append(numeric_series)

            if not series_list:
                continue

            merged_series = pd.concat(series_list, ignore_index=True)
            statistics[metric] = {
                'avg': round(float(merged_series.mean()), 4),
                'max': round(float(merged_series.max()), 4),
                'min': round(float(merged_series.min()), 4),
                'std': round(float(merged_series.std(ddof=1)) if len(merged_series) > 1 else 0.0, 4),
            }
            chart_data[metric] = _sample_series_values(merged_series)

        if not statistics:
            return {
                'error': 'Shapefile 属性表中未解析出有效的气候数值字段',
                'capabilities': capability,
            }

        chart_data['vector_metadata'] = {
            'filename': os.path.basename(file_path),
            'feature_count': int(len(df)),
            'source_type': 'vector_attribute_table',
            'available_metrics': list(statistics.keys()),
            'field_mapping': metric_fields,
            'detected_category': capability.get('detected_category'),
        }
        return {
            'statistics': statistics,
            'chart_data': chart_data,
            'charts': {},
            'data_count': int(len(df)),
        }
    finally:
        if cleanup_dir:
            remove_tree(cleanup_dir)


def analyze_climate_raster(file_path: str, file_type: str, preferred_metric: Optional[str] = None) -> Dict:
    cleanup_dirs = []
    raster_path = file_path
    try:
        if file_type.lower() == 'zip':
            result_dir = os.path.join(os.path.dirname(file_path), f'{Path(file_path).stem}_converted')
            os.makedirs(result_dir, exist_ok=True)
            raster_path, cleanup_dirs = prepare_raster_upload(file_path, result_dir)

        with rasterio.open(raster_path) as dataset:
            band_count = dataset.count
            width = dataset.width
            height = dataset.height
            crs = str(dataset.crs) if dataset.crs else None

        capability = detect_climate_file_capabilities(file_path, file_type)
        metric = preferred_metric or capability['inferred_metric']
        if preferred_metric == 'wind':
            metric = 'wind_speed'

        if capability['unsupported_for_climate']:
            return {
                'error': capability['reason'] or '当前栅格无法识别为气候监测变量',
                'capabilities': capability,
            }

        if metric not in {'temperature', 'precipitation', 'humidity', 'wind_speed'}:
            return {
                'error': capability['reason'] or '当前栅格无法识别为气候监测变量',
                'capabilities': capability,
            }

        stats = raster_band_statistics(raster_path, include_classes=False)
        metric_stats = {
            'avg': round(stats['mean_value'], 4),
            'max': round(stats['max_value'], 4),
            'min': round(stats['min_value'], 4),
            'std': round(stats['std_value'], 4),
        }
        statistics = {metric: metric_stats}
        chart_data = {metric: _sample_raster_values(raster_path)}
        chart_data['raster_metadata'] = {
            'filename': os.path.basename(file_path),
            'bands_count': band_count,
            'width': width,
            'height': height,
            'crs': crs,
            'source_type': 'single_metric_raster',
            'inferred_metric': metric,
            'available_metrics': [metric],
            'detected_category': capability['detected_category'],
        }
        return {
            'statistics': statistics,
            'chart_data': chart_data,
            'charts': {},
            'data_count': width * height,
        }
    finally:
        for cleanup_dir in cleanup_dirs:
            remove_tree(cleanup_dir)
