"""
配置GeoServer叠加分析图层的管理命令

自动配置三个WMS图层：
1. 启用图层
2. 配置样式
3. 验证WMS服务

使用方法:
    python manage.py setup_geoserver_overlay_layers
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from environment.geoserver_config import get_geoserver_manager
import os
import sys


class Command(BaseCommand):
    help = '配置GeoServer叠加分析图层'

    def handle(self, *args, **options):
        self.stdout.write('🔧 配置GeoServer叠加分析图层...\n')
        
        geoserver = get_geoserver_manager()
        
        # 1. 检查连接
        self.stdout.write('1️⃣ 检查GeoServer连接...')
        try:
            capabilities = geoserver.get_wms_capabilities()
            if not capabilities:
                self.stdout.write(self.style.ERROR('   ❌ GeoServer连接失败'))
                return
            self.stdout.write(self.style.SUCCESS('   ✅ GeoServer连接正常'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ GeoServer连接失败: {str(e)}'))
            return
        
        self.stdout.write('')
        
        # 2. 启用图层
        self.stdout.write('2️⃣ 启用图层...')
        layers_to_enable = ['ecology_raster', 'economy_vector', 'engineering_vector']
        
        for layer_name in layers_to_enable:
            full_layer_name = f"{geoserver.workspace}:{layer_name}"
            try:
                layer_info = geoserver.get_layer_info(full_layer_name)
                if layer_info:
                    layer_state = layer_info.get('layer', {}).get('enabled', False)
                    if not layer_state:
                        # 启用图层
                        layer_info['layer']['enabled'] = True
                        update_url = f"{geoserver.base_url}/rest/layers/{full_layer_name}.json"
                        import requests
                        response = requests.put(
                            update_url,
                            auth=geoserver.auth,
                            json=layer_info,
                            headers={'Content-Type': 'application/json'},
                            timeout=30
                        )
                        if response.status_code in [200, 204]:
                            self.stdout.write(self.style.SUCCESS(f'   ✅ 图层 "{layer_name}" 已启用'))
                        else:
                            self.stdout.write(self.style.WARNING(f'   ⚠️  启用图层 "{layer_name}" 失败: {response.status_code}'))
                    else:
                        self.stdout.write(self.style.SUCCESS(f'   ✅ 图层 "{layer_name}" 已启用'))
                else:
                    self.stdout.write(self.style.ERROR(f'   ❌ 图层 "{layer_name}" 不存在'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ❌ 处理图层 "{layer_name}" 失败: {str(e)}'))
        
        self.stdout.write('')
        
        # 3. 配置生态栅格样式
        self.stdout.write('3️⃣ 配置生态栅格样式...')
        try:
            # 读取SLD文件
            sld_file_path = os.path.join(settings.BASE_DIR, 'media', 'ecological_projects', 'ecology_raster_dem_style.sld')
            if not os.path.exists(sld_file_path):
                # 尝试另一个文件
                sld_file_path = os.path.join(settings.BASE_DIR, 'media', 'ecological_projects', 'ecology_raster.sld')
            
            if os.path.exists(sld_file_path):
                with open(sld_file_path, 'r', encoding='utf-8') as f:
                    sld_content = f.read()
                
                # 创建样式
                style_name = 'ecology_raster'
                if geoserver.create_style(style_name, sld_content):
                    self.stdout.write(self.style.SUCCESS(f'   ✅ 样式 "{style_name}" 已创建'))
                    
                    # 应用样式到图层
                    if geoserver.apply_style_to_layer('ecology_raster', style_name):
                        self.stdout.write(self.style.SUCCESS(f'   ✅ 样式已应用到图层'))
                    else:
                        self.stdout.write(self.style.WARNING(f'   ⚠️  应用样式失败'))
                else:
                    self.stdout.write(self.style.WARNING(f'   ⚠️  创建样式失败（可能已存在）'))
                    # 尝试应用样式
                    if geoserver.apply_style_to_layer('ecology_raster', style_name):
                        self.stdout.write(self.style.SUCCESS(f'   ✅ 样式已应用到图层'))
            else:
                self.stdout.write(self.style.WARNING(f'   ⚠️  SLD文件不存在: {sld_file_path}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ 配置样式失败: {str(e)}'))
        
        self.stdout.write('')
        
        # 4. 验证配置
        self.stdout.write('4️⃣ 验证配置...')
        try:
            import requests
            
            # 测试三个图层的GetMap
            layers_to_test = ['ecology_raster', 'economy_vector', 'engineering_vector']
            for layer in layers_to_test:
                full_name = f"{geoserver.workspace}:{layer}"
                test_map_url = f"{geoserver.base_url}/ows?service=WMS&version=1.3.0&request=GetMap&layers={full_name}&format=image/png&transparent=true&CRS=EPSG:4326&BBOX=105.0,34.0,106.5,35.0&WIDTH=256&HEIGHT=256"
                
                map_response = requests.get(test_map_url, auth=geoserver.auth, timeout=10)
                if map_response.status_code == 200:
                    content_type = map_response.headers.get('content-type', '')
                    if 'image' in content_type:
                        self.stdout.write(self.style.SUCCESS(f'   ✅ 图层 "{layer}" WMS服务正常'))
                    else:
                        self.stdout.write(self.style.WARNING(f'   ⚠️  图层 "{layer}" WMS返回非图像格式: {content_type}'))
                        # 尝试读取响应内容
                        try:
                            text = map_response.text[:500]
                            if 'ServiceException' in text:
                                self.stdout.write(f'   🔍 GeoServer错误: {text[:200]}')
                        except:
                            pass
                else:
                    self.stdout.write(self.style.ERROR(f'   ❌ 图层 "{layer}" WMS服务失败: {map_response.status_code}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ 验证配置失败: {str(e)}'))
        
        self.stdout.write('')
        self.stdout.write('✅ 配置完成！')
        self.stdout.write('💡 建议运行检查命令验证配置: python manage.py check_geoserver_overlay_layers')

