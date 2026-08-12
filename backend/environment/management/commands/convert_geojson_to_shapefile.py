"""
将GeoJSON转换为Shapefile的管理命令

使用方法:
    python manage.py convert_geojson_to_shapefile \
        --input media/ecological_projects/economy_vector.geojson \
        --output media/ecological_projects/economy_vector.shp
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import os
import geopandas as gpd
import sys


class Command(BaseCommand):
    help = '将GeoJSON文件转换为Shapefile格式'

    def add_arguments(self, parser):
        parser.add_argument(
            '--input',
            type=str,
            required=True,
            help='输入的GeoJSON文件路径（相对于项目根目录）'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='输出的Shapefile路径（相对于项目根目录），不指定则自动生成'
        )
        parser.add_argument(
            '--epsg',
            type=int,
            default=4326,
            help='输出坐标系EPSG代码（默认4326）'
        )

    def handle(self, *args, **options):
        input_path = options['input']
        output_path = options.get('output')
        epsg_code = options['epsg']

        # 转换为绝对路径
        if not os.path.isabs(input_path):
            input_path = os.path.join(settings.BASE_DIR, input_path)

        if not os.path.exists(input_path):
            self.stdout.write(
                self.style.ERROR(f'❌ 输入文件不存在: {input_path}')
            )
            sys.exit(1)

        # 生成输出路径
        if not output_path:
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            output_dir = os.path.dirname(input_path)
            output_path = os.path.join(output_dir, f'{base_name}.shp')
        else:
            if not os.path.isabs(output_path):
                output_path = os.path.join(settings.BASE_DIR, output_path)

        self.stdout.write(f'📖 读取GeoJSON文件: {input_path}')

        try:
            # 读取GeoJSON
            gdf = gpd.read_file(input_path)

            # 检查坐标系
            if gdf.crs is None:
                self.stdout.write(
                    self.style.WARNING('⚠️  GeoJSON没有坐标系信息，将设置为EPSG:4326')
                )
                gdf.set_crs(epsg=4326, inplace=True)

            # 如果指定了不同的坐标系，进行转换
            if gdf.crs.to_epsg() != epsg_code:
                self.stdout.write(
                    f'🔄 转换坐标系: {gdf.crs.to_epsg()} -> EPSG:{epsg_code}'
                )
                gdf = gdf.to_crs(epsg=epsg_code)

            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)

            # 导出为Shapefile
            self.stdout.write(f'💾 导出Shapefile: {output_path}')
            gdf.to_file(output_path, driver='ESRI Shapefile', encoding='utf-8')

            # 检查输出文件
            output_base = os.path.splitext(output_path)[0]
            required_files = [
                f'{output_base}.shp',
                f'{output_base}.shx',
                f'{output_base}.dbf',
                f'{output_base}.prj'
            ]

            all_exist = all(os.path.exists(f) for f in required_files)

            if all_exist:
                self.stdout.write(
                    self.style.SUCCESS('✅ Shapefile转换成功！')
                )
                self.stdout.write(f'\n生成的文件:')
                for f in required_files:
                    size = os.path.getsize(f)
                    self.stdout.write(f'  - {os.path.basename(f)} ({size} bytes)')

                # 显示数据统计
                self.stdout.write(f'\n数据统计:')
                self.stdout.write(f'  - 要素数量: {len(gdf)}')
                self.stdout.write(f'  - 坐标系: EPSG:{epsg_code}')
                self.stdout.write(f'  - 属性字段: {list(gdf.columns)}')

                # 显示字段信息
                if 'GDP' in gdf.columns:
                    gdp_stats = gdf['GDP'].describe()
                    self.stdout.write(f'\nGDP统计:')
                    self.stdout.write(f'  - 最小值: {gdp_stats["min"]:.2f}')
                    self.stdout.write(f'  - 最大值: {gdp_stats["max"]:.2f}')
                    self.stdout.write(f'  - 平均值: {gdp_stats["mean"]:.2f}')

            else:
                self.stdout.write(
                    self.style.WARNING('⚠️  部分Shapefile文件缺失')
                )

        except ImportError:
            self.stdout.write(
                self.style.ERROR('❌ 需要安装geopandas库')
            )
            self.stdout.write('   安装命令: pip install geopandas')
            sys.exit(1)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 转换失败: {str(e)}')
            )
            import traceback
            self.stdout.write(traceback.format_exc())
            sys.exit(1)

