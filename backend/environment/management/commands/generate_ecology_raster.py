"""
生成生态栅格数据的管理命令

创建一个模拟的生态栅格TIF文件，用于测试和演示
使用DEM（数字高程模型）风格的连续值栅格

使用方法:
    python manage.py generate_ecology_raster \
        --output media/ecological_projects/ecology_raster.tif \
        --bounds 105.08 34.48 106.28 34.98 \
        --pixel-size 0.01 \
        --value-range 50 1000
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import os
import numpy as np
from osgeo import gdal, osr
import sys

gdal.UseExceptions()


class Command(BaseCommand):
    help = '生成生态栅格数据（模拟DEM格式）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='media/ecological_projects/ecology_raster.tif',
            help='输出的栅格文件路径（相对于项目根目录）'
        )
        parser.add_argument(
            '--bounds',
            type=float,
            nargs=4,
            metavar=('MIN_LON', 'MIN_LAT', 'MAX_LON', 'MAX_LAT'),
            default=[105.08, 34.48, 106.28, 34.98],
            help='栅格范围（经度最小值 纬度最小值 经度最大值 纬度最大值）'
        )
        parser.add_argument(
            '--pixel-size',
            type=float,
            default=0.01,
            help='像素大小（度），默认0.01度约1km'
        )
        parser.add_argument(
            '--value-range',
            type=float,
            nargs=2,
            metavar=('MIN_VAL', 'MAX_VAL'),
            default=[50, 1000],
            help='栅格值范围（最小值 最大值），默认50-1000（类似DEM高程值）'
        )
        parser.add_argument(
            '--seed',
            type=int,
            default=42,
            help='随机种子，用于生成一致的模拟数据'
        )

    def handle(self, *args, **options):
        output_path = options['output']
        min_lon, min_lat, max_lon, max_lat = options['bounds']
        pixel_size = options['pixel_size']
        min_val, max_val = options['value_range']
        seed = options['seed']

        # 转换为绝对路径
        if not os.path.isabs(output_path):
            output_path = os.path.join(settings.BASE_DIR, output_path)

        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        self.stdout.write(f'🎨 生成生态栅格数据...')
        self.stdout.write(f'   输出路径: {output_path}')
        self.stdout.write(f'   范围: [{min_lon}, {min_lat}] 到 [{max_lon}, {max_lat}]')
        self.stdout.write(f'   像素大小: {pixel_size}度')
        self.stdout.write(f'   值范围: {min_val} - {max_val}')

        try:
            # 计算栅格尺寸
            width = int((max_lon - min_lon) / pixel_size)
            height = int((max_lat - min_lat) / pixel_size)

            if width <= 0 or height <= 0:
                self.stdout.write(
                    self.style.ERROR('❌ 栅格尺寸无效')
                )
                sys.exit(1)

            self.stdout.write(f'   栅格尺寸: {width} x {height} 像素')

            # 创建模拟栅格数据
            # 使用多种方法生成更真实的连续值分布
            np.random.seed(seed)

            # 方法1: 基于距离中心的径向渐变（模拟地形或生态梯度）
            center_lon = (min_lon + max_lon) / 2
            center_lat = (min_lat + max_lat) / 2

            # 创建坐标网格
            lon_grid = np.linspace(min_lon, max_lon, width)
            lat_grid = np.linspace(max_lat, min_lat, height)  # 注意：纬度从上到下
            lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)

            # 计算到中心的距离
            dx = (lon_mesh - center_lon) * 111.32 * np.cos(np.radians(center_lat))
            dy = (lat_mesh - center_lat) * 111.32
            distance = np.sqrt(dx**2 + dy**2)

            # 基于距离生成渐变值（类似地形）
            max_distance = np.max(distance)
            normalized_distance = distance / max_distance if max_distance > 0 else distance

            # 生成基础值（类似DEM高程模式）
            base_values = min_val + (max_val - min_val) * (1 - normalized_distance * 0.6)

            # 添加随机噪声和局部变化（模拟真实的生态指数变化）
            noise = np.random.randn(height, width) * (max_val - min_val) * 0.1
            local_variation = np.sin(distance / 20) * (max_val - min_val) * 0.15

            # 组合所有值
            raster_array = base_values + noise + local_variation

            # 确保值在范围内
            raster_array = np.clip(raster_array, min_val, max_val)

            # 转换为float32
            raster_array = raster_array.astype(np.float32)

            # 创建GeoTIFF文件
            driver = gdal.GetDriverByName('GTiff')
            dst_ds = driver.Create(output_path, width, height, 1, gdal.GDT_Float32)

            if dst_ds is None:
                raise RuntimeError('无法创建输出栅格文件')

            # 设置地理变换参数（WGS84，经纬度）
            geotransform = (min_lon, pixel_size, 0, max_lat, 0, -pixel_size)
            dst_ds.SetGeoTransform(geotransform)

            # 设置投影（WGS84）
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(4326)
            dst_ds.SetProjection(srs.ExportToWkt())

            # 写入数据
            band = dst_ds.GetRasterBand(1)
            band.WriteArray(raster_array)
            band.SetNoDataValue(-9999)

            # 设置波段描述
            band.SetDescription('Ecology Index (Simulated DEM-style)')

            # 计算并设置统计信息
            valid_data = raster_array[~np.isnan(raster_array)]
            if len(valid_data) > 0:
                band.SetStatistics(
                    float(np.min(valid_data)),
                    float(np.max(valid_data)),
                    float(np.mean(valid_data)),
                    float(np.std(valid_data))
                )

            # 注意：Float32类型不支持颜色表
            # 颜色映射将在GeoServer SLD样式中配置

            band.FlushCache()
            dst_ds.FlushCache()
            dst_ds = None

            # 验证文件
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                self.stdout.write(
                    self.style.SUCCESS('✅ 生态栅格生成成功！')
                )
                self.stdout.write(f'\n文件信息:')
                self.stdout.write(f'  - 文件路径: {output_path}')
                self.stdout.write(f'  - 文件大小: {file_size:,} bytes ({file_size/1024:.2f} KB)')
                self.stdout.write(f'  - 栅格尺寸: {width} x {height} 像素')
                self.stdout.write(f'  - 空间范围: [{min_lon:.4f}, {min_lat:.4f}] 到 [{max_lon:.4f}, {max_lat:.4f}]')
                self.stdout.write(f'  - 像素分辨率: {pixel_size}度 (约 {pixel_size * 111:.2f}km)')
                self.stdout.write(f'  - 数据范围: {float(np.min(valid_data)):.2f} - {float(np.max(valid_data)):.2f}')
                self.stdout.write(f'  - 平均值: {float(np.mean(valid_data)):.2f}')
                self.stdout.write(f'  - 标准差: {float(np.std(valid_data)):.2f}')

                self.stdout.write(f'\n💡 使用建议:')
                self.stdout.write(f'  1. 在QGIS中打开查看')
                self.stdout.write(f'  2. 在GeoServer中配置SLD样式（按值范围 {min_val}-{max_val} 设置渐变色）')
                self.stdout.write(f'  3. 可以裁剪到economy_vector的范围作为研究区域')
                self.stdout.write(f'  4. 前端可以通过WMS服务加载显示')

            else:
                self.stdout.write(
                    self.style.ERROR('❌ 文件生成失败')
                )
                sys.exit(1)

        except ImportError as e:
            self.stdout.write(
                self.style.ERROR('❌ 需要安装GDAL库')
            )
            self.stdout.write('   安装命令: pip install gdal 或 conda install gdal')
            sys.exit(1)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 生成失败: {str(e)}')
            )
            import traceback
            self.stdout.write(traceback.format_exc())
            sys.exit(1)

