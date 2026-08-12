import os
import shutil
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from .band_mapping import get_band_scale_offset, infer_standard_band_mapping


SHAPEFILE_REQUIRED_EXTENSIONS = {'.shp', '.shx', '.dbf'}


def validate_shapefile_zip(zip_path):
    """Return (ok, message) for a Shapefile zip archive."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as archive:
            names = [Path(item.filename).name for item in archive.infolist() if not item.is_dir()]
    except zipfile.BadZipFile:
        return False, 'ZIP文件损坏或不是标准ZIP格式'

    stems = {}
    for name in names:
        path = Path(name)
        ext = path.suffix.lower()
        if ext in SHAPEFILE_REQUIRED_EXTENSIONS or ext in {'.prj', '.cpg'}:
            stems.setdefault(path.stem, set()).add(ext)

    for stem, extensions in stems.items():
        missing = SHAPEFILE_REQUIRED_EXTENSIONS - extensions
        if not missing:
            return True, f'检测到完整Shapefile: {stem}'

    return False, 'ZIP中未找到完整Shapefile组件，至少需要同名 .shp/.shx/.dbf'


def extract_zip(zip_path, output_dir):
    with zipfile.ZipFile(zip_path, 'r') as archive:
        archive.extractall(output_dir)


def find_adf_dataset(root_dir):
    """Find an Arc/Info Binary Grid directory inside an extracted ZIP."""
    root = Path(root_dir)
    candidates = []
    for hdr_path in root.rglob('hdr.adf'):
        folder = hdr_path.parent
        if (folder / 'w001001.adf').exists():
            candidates.append(folder)
    if candidates:
        return str(candidates[0])
    return None


def convert_adf_to_geotiff(adf_dir, output_tif):
    """Convert Arc/Info Binary Grid to GeoTIFF via GDAL if available."""
    try:
        from osgeo import gdal
    except ImportError as exc:
        raise RuntimeError('当前环境未安装GDAL/osgeo，无法自动转换ADF。请先转为GeoTIFF后上传。') from exc

    dataset = gdal.Open(str(adf_dir))
    if dataset is None:
        raise RuntimeError('无法打开ADF栅格目录，请确认ZIP中包含完整ArcGIS栅格文件夹')

    os.makedirs(os.path.dirname(output_tif), exist_ok=True)
    options = gdal.TranslateOptions(
        format='GTiff',
        creationOptions=['TILED=YES', 'COMPRESS=LZW', 'BIGTIFF=IF_SAFER']
    )
    result = gdal.Translate(str(output_tif), dataset, options=options)
    dataset = None
    if result is None:
        raise RuntimeError('ADF转GeoTIFF失败')
    result = None
    return output_tif


def prepare_raster_upload(upload_abs, result_dir_abs):
    """
    Return a raster path usable by rasterio. A .zip containing ADF is converted
    to GeoTIFF; normal TIFFs are returned unchanged.
    """
    lower = upload_abs.lower()
    if not lower.endswith('.zip'):
        return upload_abs, []

    extracted_dir = os.path.join(result_dir_abs, 'extracted')
    os.makedirs(extracted_dir, exist_ok=True)
    extract_zip(upload_abs, extracted_dir)
    adf_dir = find_adf_dataset(extracted_dir)
    if not adf_dir:
        raise RuntimeError('ZIP中没有找到完整ADF栅格目录。Shapefile请到矢量上传入口使用。')

    output_tif = os.path.join(result_dir_abs, 'converted_from_adf.tif')
    convert_adf_to_geotiff(adf_dir, output_tif)
    return output_tif, [extracted_dir]


def _valid_values(data, nodata=None):
    arr = data.astype('float32', copy=False)
    if nodata is not None:
        arr = np.where(arr == nodata, np.nan, arr)
    return arr[np.isfinite(arr)]


def _stats_from_accumulators(count, total, square_total, min_value, max_value):
    if count == 0:
        raise ValueError('栅格中没有有效像元')
    mean_value = total / count
    variance = max(0.0, square_total / count - mean_value ** 2)
    return {
        'min_value': float(min_value),
        'max_value': float(max_value),
        'mean_value': float(mean_value),
        'std_value': float(np.sqrt(variance)),
    }


def _pixel_area_km2(dataset):
    area = abs(dataset.transform.a * dataset.transform.e) / 1000000
    if not np.isfinite(area) or area == 0:
        return 30 * 30 / 1000000
    return float(area)


def classify_area_by_std(path, band_index, stats):
    with rasterio.open(path) as dataset:
        nodata = dataset.nodata
        mean_value = stats['mean_value']
        std_value = stats['std_value']
        thresholds = {
            'excellent': mean_value + 1.5 * std_value,
            'good': mean_value + 0.5 * std_value,
            'moderate': mean_value - 0.5 * std_value,
            'poor': mean_value - 1.5 * std_value,
        }
        counts = {'excellent': 0, 'good': 0, 'moderate': 0, 'poor': 0, 'bad': 0}
        for _, window in dataset.block_windows(band_index):
            data = dataset.read(band_index, window=window).astype('float32')
            if nodata is not None:
                data[data == nodata] = np.nan
            valid = data[np.isfinite(data)]
            if valid.size == 0:
                continue
            counts['excellent'] += int(np.sum(valid >= thresholds['excellent']))
            counts['good'] += int(np.sum((valid >= thresholds['good']) & (valid < thresholds['excellent'])))
            counts['moderate'] += int(np.sum((valid >= thresholds['moderate']) & (valid < thresholds['good'])))
            counts['poor'] += int(np.sum((valid >= thresholds['poor']) & (valid < thresholds['moderate'])))
            counts['bad'] += int(np.sum(valid < thresholds['poor']))

        pixel_area = _pixel_area_km2(dataset)
        return {
            'excellent_area': float(counts['excellent'] * pixel_area),
            'good_area': float(counts['good'] * pixel_area),
            'moderate_area': float(counts['moderate'] * pixel_area),
            'poor_area': float(counts['poor'] * pixel_area),
            'bad_area': float(counts['bad'] * pixel_area),
        }


def raster_band_statistics(path, band_index=1, include_classes=True):
    with rasterio.open(path) as dataset:
        nodata = dataset.nodata
        count = 0
        total = 0.0
        square_total = 0.0
        min_value = None
        max_value = None

        for _, window in dataset.block_windows(band_index):
            valid = _valid_values(dataset.read(band_index, window=window), nodata)
            if valid.size == 0:
                continue
            count += int(valid.size)
            total += float(np.sum(valid, dtype=np.float64))
            square_total += float(np.sum(np.square(valid, dtype=np.float64)))
            chunk_min = float(np.min(valid))
            chunk_max = float(np.max(valid))
            min_value = chunk_min if min_value is None else min(min_value, chunk_min)
            max_value = chunk_max if max_value is None else max(max_value, chunk_max)

        stats = _stats_from_accumulators(count, total, square_total, min_value, max_value)
        if include_classes:
            stats.update(classify_area_by_std(path, band_index, stats))
        return stats


def preview_array(path, band_index=1, max_size=2000):
    with rasterio.open(path) as dataset:
        scale = max(1, int(np.ceil(max(dataset.width, dataset.height) / max_size)))
        return _read_scaled_band(
            dataset,
            band_index,
            out_shape=(max(1, dataset.height // scale), max(1, dataset.width // scale)),
            resampling=Resampling.bilinear,
        )


def _read_scaled_band(dataset, band_index, window=None, out_shape=None, resampling=Resampling.bilinear):
    raw_data = dataset.read(
        band_index,
        window=window,
        out_shape=out_shape,
        resampling=resampling,
    )
    data = raw_data.astype('float32')
    nodata = dataset.nodata
    if nodata is not None:
        data[raw_data == nodata] = np.nan
    scale, offset = get_band_scale_offset(dataset, band_index - 1, band_count=int(dataset.count))
    return data * np.float32(scale) + np.float32(offset)


def _remote_band_pair(dataset, index_type):
    band_count = int(dataset.count)
    mapping = infer_standard_band_mapping(dataset=dataset, band_count=band_count)
    if index_type == 'ndvi':
        if mapping.get('nir') is not None and mapping.get('red') is not None:
            return mapping['nir'] + 1, mapping['red'] + 1
        if band_count == 3:
            return 2, 1
    if index_type == 'ndwi':
        if mapping.get('green') is not None and mapping.get('nir') is not None:
            return mapping['green'] + 1, mapping['nir'] + 1
        if band_count == 3:
            return 2, 1
    raise ValueError(f'当前波段配置不支持 {index_type.upper()} 分块计算')


def calculate_normalized_index_windowed(input_path, output_path, index_type):
    """Calculate NDVI/NDWI by windows and return statistics."""
    index_type = index_type.lower()
    with rasterio.open(input_path) as src:
        numerator_band, denominator_band = _remote_band_pair(src, index_type)
        meta = src.meta.copy()
        meta.update({
            'driver': 'GTiff',
            'count': 1,
            'dtype': 'float32',
            'nodata': np.nan,
            'tiled': True,
            'compress': 'lzw',
            'BIGTIFF': 'IF_SAFER',
        })
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        count = 0
        total = 0.0
        square_total = 0.0
        min_value = None
        max_value = None

        with rasterio.open(output_path, 'w', **meta) as dst:
            for _, window in src.block_windows(1):
                a = _read_scaled_band(src, numerator_band, window=window)
                b = _read_scaled_band(src, denominator_band, window=window)
                denominator = a + b
                result = np.full(a.shape, np.nan, dtype='float32')
                mask = denominator != 0
                result[mask] = (a[mask] - b[mask]) / denominator[mask]
                result = np.clip(result, -1.0, 1.0)
                dst.write(result, 1, window=window)

                valid = result[np.isfinite(result)]
                if valid.size == 0:
                    continue
                count += int(valid.size)
                total += float(np.sum(valid, dtype=np.float64))
                square_total += float(np.sum(np.square(valid, dtype=np.float64)))
                chunk_min = float(np.min(valid))
                chunk_max = float(np.max(valid))
                min_value = chunk_min if min_value is None else min(min_value, chunk_min)
                max_value = chunk_max if max_value is None else max(max_value, chunk_max)

    stats = _stats_from_accumulators(count, total, square_total, min_value, max_value)
    stats.update(classify_area_by_std(output_path, 1, stats))
    return output_path, stats


def calculate_normalized_index_preview_stats(input_path, index_type, max_preview_size=2000):
    """Calculate NDVI/NDWI statistics by windows and return a downsampled preview."""
    index_type = index_type.lower()
    with rasterio.open(input_path) as src:
        numerator_band, denominator_band = _remote_band_pair(src, index_type)
        base_pixel_area = _pixel_area_km2(src)
        count = 0
        total = 0.0
        square_total = 0.0
        min_value = None
        max_value = None

        for _, window in src.block_windows(1):
            a = _read_scaled_band(src, numerator_band, window=window)
            b = _read_scaled_band(src, denominator_band, window=window)
            denominator = a + b
            result = np.full(a.shape, np.nan, dtype='float32')
            mask = denominator != 0
            result[mask] = (a[mask] - b[mask]) / denominator[mask]
            result = np.clip(result, -1.0, 1.0)

            valid = result[np.isfinite(result)]
            if valid.size == 0:
                continue
            count += int(valid.size)
            total += float(np.sum(valid, dtype=np.float64))
            square_total += float(np.sum(np.square(valid, dtype=np.float64)))
            chunk_min = float(np.min(valid))
            chunk_max = float(np.max(valid))
            min_value = chunk_min if min_value is None else min(min_value, chunk_min)
            max_value = chunk_max if max_value is None else max(max_value, chunk_max)

        stats = _stats_from_accumulators(count, total, square_total, min_value, max_value)

        scale = max(1, int(np.ceil(max(src.width, src.height) / max_preview_size)))
        out_shape = (max(1, src.height // scale), max(1, src.width // scale))
        a_preview = _read_scaled_band(src, numerator_band, out_shape=out_shape, resampling=Resampling.bilinear)
        b_preview = _read_scaled_band(src, denominator_band, out_shape=out_shape, resampling=Resampling.bilinear)
        denominator = a_preview + b_preview
        preview = np.full(a_preview.shape, np.nan, dtype='float32')
        mask = denominator != 0
        preview[mask] = (a_preview[mask] - b_preview[mask]) / denominator[mask]
        preview = np.clip(preview, -1.0, 1.0)

    mean_value = stats['mean_value']
    std_value = stats['std_value']
    thresholds = {
        'excellent': mean_value + 1.5 * std_value,
        'good': mean_value + 0.5 * std_value,
        'moderate': mean_value - 0.5 * std_value,
        'poor': mean_value - 1.5 * std_value,
    }
    valid_preview = preview[np.isfinite(preview)]
    pixel_area = base_pixel_area * scale * scale
    stats.update({
        'excellent_area': float(np.sum(valid_preview >= thresholds['excellent']) * pixel_area),
        'good_area': float(np.sum((valid_preview >= thresholds['good']) & (valid_preview < thresholds['excellent'])) * pixel_area),
        'moderate_area': float(np.sum((valid_preview >= thresholds['moderate']) & (valid_preview < thresholds['good'])) * pixel_area),
        'poor_area': float(np.sum((valid_preview >= thresholds['poor']) & (valid_preview < thresholds['moderate'])) * pixel_area),
        'bad_area': float(np.sum(valid_preview < thresholds['poor']) * pixel_area),
    })
    return preview, stats


def remove_tree(path):
    if path and os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)


class RasterioLandUseAnalyzer:
    """Land-use analyzer fallback for classified GeoTIFF files without GDAL/osgeo."""

    def __init__(self, landuse_path):
        self.landuse_path = landuse_path
        self.dataset = None
        self.width = None
        self.height = None
        self.transform = None
        self.crs = None
        self.no_data_value = None
        self.class_counts = {}
        self.valid_pixels = 0
        self.preview_data = None
        self.landuse_classes = {
            1: {'name': '耕地', 'color': '#FFFF00', 'fragility': 0.3},
            2: {'name': '林地', 'color': '#228B22', 'fragility': 0.1},
            3: {'name': '草地', 'color': '#90EE90', 'fragility': 0.2},
            4: {'name': '水域', 'color': '#0000FF', 'fragility': 0.4},
            5: {'name': '建设用地', 'color': '#FF0000', 'fragility': 0.8},
            6: {'name': '未利用地', 'color': '#808080', 'fragility': 0.9},
            7: {'name': '湿地', 'color': '#00FFFF', 'fragility': 0.5},
            8: {'name': '园地', 'color': '#32CD32', 'fragility': 0.2},
        }

    def load_landuse_data(self):
        self.dataset = rasterio.open(self.landuse_path)
        self.width = self.dataset.width
        self.height = self.dataset.height
        self.transform = self.dataset.transform
        self.crs = self.dataset.crs
        self.no_data_value = self.dataset.nodata
        self.class_counts = {}
        self.valid_pixels = 0

        for _, window in self.dataset.block_windows(1):
            data = self.dataset.read(1, window=window)
            if self.no_data_value is not None:
                data = data[data != self.no_data_value]
            data = data[np.isfinite(data)]
            if data.size == 0:
                continue
            values, counts = np.unique(data.astype(np.int64), return_counts=True)
            for value, count in zip(values, counts):
                self.class_counts[int(value)] = self.class_counts.get(int(value), 0) + int(count)
            self.valid_pixels += int(data.size)

        self.preview_data = self._read_preview(max_size=2500)
        return self.valid_pixels > 0

    def _read_preview(self, max_size=2500):
        scale = max(1, int(np.ceil(max(self.width, self.height) / max_size)))
        data = self.dataset.read(
            1,
            out_shape=(max(1, self.height // scale), max(1, self.width // scale)),
            resampling=Resampling.nearest,
        )
        if self.no_data_value is not None:
            data = np.where(data == self.no_data_value, -9999, data)
        return data.astype(np.int32)

    def close(self):
        if self.dataset is not None:
            self.dataset.close()
            self.dataset = None

    def _pixel_area_km2(self):
        area = abs(self.transform.a * self.transform.e) / 1000000
        if not np.isfinite(area) or area == 0:
            return 30 * 30 / 1000000
        return float(area)

    def get_landuse_statistics(self):
        pixel_area = self._pixel_area_km2()
        classes = {}
        for class_id, info in self.landuse_classes.items():
            pixels = self.class_counts.get(class_id, 0)
            ratio = pixels / self.valid_pixels * 100 if self.valid_pixels else 0
            classes[class_id] = {
                'name': info['name'],
                'pixels': int(pixels),
                'area_km2': float(pixels * pixel_area),
                'ratio_percent': float(ratio),
                'fragility': info['fragility'],
            }
        return {
            'total_pixels': int(self.width * self.height),
            'valid_pixels': int(self.valid_pixels),
            'pixel_area_m2': float(pixel_area * 1000000),
            'total_area_km2': float(self.valid_pixels * pixel_area),
            'classes': classes,
        }

    def _preview_valid(self):
        if self.preview_data is None:
            return np.array([], dtype=np.int32)
        return self.preview_data[self.preview_data != -9999]

    def _patch_count_on_preview(self, mask):
        try:
            from scipy import ndimage
            _, count = ndimage.label(mask)
            return int(count)
        except Exception:
            return int(np.any(mask))

    def calculate_fragmentation_index(self):
        valid_mask = self.preview_data != -9999
        total_area = int(np.sum(valid_mask))
        total_patches = self._patch_count_on_preview(valid_mask)
        fragmentation = (total_patches - 1) / total_patches if total_patches > 1 else 0.0
        class_fragmentation = {}
        for class_id, info in self.landuse_classes.items():
            class_mask = self.preview_data == class_id
            pixels = int(np.sum(class_mask))
            if pixels <= 0:
                continue
            patches = self._patch_count_on_preview(class_mask)
            class_fragmentation[class_id] = {
                'name': info['name'],
                'patches': patches,
                'area': pixels,
                'fragmentation_index': float((patches - 1) / patches if patches > 1 else 0.0),
            }
        return {
            'overall_fragmentation': float(fragmentation),
            'total_patches': int(total_patches),
            'total_area': int(total_area),
            'class_fragmentation': class_fragmentation,
            'note': '未安装GDAL时基于降采样预览估算破碎度',
        }

    def calculate_cohesion_index(self):
        valid = self._preview_valid()
        if valid.size == 0:
            return {'cohesion_index': 0.0}
        dominant_ratio = 0.0
        if self.class_counts and self.valid_pixels:
            dominant_ratio = max(self.class_counts.values()) / self.valid_pixels
        return {
            'cohesion_index': float(max(0.0, min(100.0, dominant_ratio * 100))),
            'total_patches': int(len([v for v in self.class_counts.values() if v > 0])),
            'total_area': int(self.valid_pixels),
            'note': '未安装GDAL时基于类型优势度估算内聚力',
        }

    def calculate_diversity_index(self):
        counts = np.array([count for cid, count in self.class_counts.items() if cid in self.landuse_classes and count > 0], dtype=np.float64)
        if counts.size == 0:
            return {'shannon_diversity': 0.0, 'simpson_diversity': 0.0}
        proportions = counts / counts.sum()
        shannon = -np.sum(proportions * np.log(proportions))
        simpson = 1 - np.sum(proportions * proportions)
        pielou = shannon / np.log(counts.size) if counts.size > 1 else 0.0
        return {
            'shannon_diversity': float(shannon),
            'simpson_diversity': float(simpson),
            'pielou_evenness': float(pielou),
            'class_count': int(counts.size),
        }

    def calculate_fragility_index(self):
        if not self.valid_pixels:
            return {'fragility_index': 0.0}
        total = 0.0
        class_fragility = {}
        for class_id, info in self.landuse_classes.items():
            pixels = self.class_counts.get(class_id, 0)
            ratio = pixels / self.valid_pixels if self.valid_pixels else 0
            contribution = ratio * info['fragility']
            total += contribution
            class_fragility[class_id] = {
                'name': info['name'],
                'fragility': info['fragility'],
                'area_ratio': float(ratio),
                'contribution': float(contribution),
            }
        return {'fragility_index': float(total), 'class_fragility': class_fragility}

    def calculate_soil_erosion_index(self):
        weights = {1: 0.45, 2: 0.12, 3: 0.25, 4: 0.05, 5: 0.55, 6: 0.85, 7: 0.18, 8: 0.2}
        value = self._weighted_index(weights)
        return {'soil_erosion_index': float(value), 'risk_level': self._risk_label(value)}

    def calculate_unused_land_ratio(self):
        ratio = self.class_counts.get(6, 0) / self.valid_pixels * 100 if self.valid_pixels else 0
        return {'unused_land_ratio': float(ratio), 'unused_land_pixels': int(self.class_counts.get(6, 0))}

    def calculate_development_ratio(self):
        pixels = self.class_counts.get(1, 0) + self.class_counts.get(5, 0)
        ratio = pixels / self.valid_pixels * 100 if self.valid_pixels else 0
        return {'development_ratio': float(ratio), 'cultivated_construction_pixels': int(pixels)}

    def calculate_land_degradation_index(self):
        weights = {1: 0.35, 2: 0.08, 3: 0.22, 4: 0.05, 5: 0.65, 6: 0.9, 7: 0.15, 8: 0.18}
        value = self._weighted_index(weights)
        return {'land_degradation_index': float(value), 'risk_level': self._risk_label(value)}

    def _weighted_index(self, weights):
        if not self.valid_pixels:
            return 0.0
        return sum(self.class_counts.get(class_id, 0) / self.valid_pixels * weight for class_id, weight in weights.items())

    def _risk_label(self, value):
        if value < 0.2:
            return '低风险'
        if value < 0.4:
            return '中风险'
        if value < 0.6:
            return '高风险'
        return '极高风险'

    def create_landuse_visualization(self, output_path):
        if self.preview_data is None:
            raise ValueError('土地利用数据未加载')
        colors = ['#FFFFFF']
        labels = []
        for class_id, info in self.landuse_classes.items():
            colors.append(info['color'])
            labels.append(f"{class_id} {info['name']}")
        cmap = ListedColormap(colors)
        cmap = cmap.copy()
        cmap.set_bad((1, 1, 1, 0))
        data = np.ma.masked_where(self.preview_data == -9999, self.preview_data)
        fig, ax = plt.subplots(figsize=(12, 7))
        ax.imshow(data, cmap=cmap, interpolation='nearest', vmin=0, vmax=max(self.landuse_classes.keys()))
        ax.set_title('土地利用分类分布图', fontsize=16)
        ax.set_xticks([])
        ax.set_yticks([])
        handles = [
            plt.Line2D([0], [0], marker='s', color='w', markerfacecolor=self.landuse_classes[class_id]['color'], markersize=10, label=label)
            for class_id, label in zip(self.landuse_classes.keys(), labels)
            if self.class_counts.get(class_id, 0) > 0
        ]
        if handles:
            ax.legend(handles=handles, loc='lower center', bbox_to_anchor=(0.5, -0.12), ncol=4, fontsize=9)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.tight_layout()
        plt.savefig(output_path, dpi=180, bbox_inches='tight')
        plt.close(fig)
        return True
