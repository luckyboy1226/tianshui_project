"""
修复GeoServer WMS服务配置的管理命令

检查并修复WMS服务问题
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from environment.geoserver_config import get_geoserver_manager
import requests
import sys


class Command(BaseCommand):
    help = '修复GeoServer WMS服务配置'

    def handle(self, *args, **options):
        self.stdout.write('🔧 修复GeoServer WMS服务配置...\n')
        
        geoserver = get_geoserver_manager()
        
        # 测试三个图层
        layers_to_test = ['ecology_raster', 'economy_vector', 'engineering_vector']
        
        for layer_name in layers_to_test:
            self.stdout.write(f'\n📋 检查图层: {layer_name}')
            full_name = f"{geoserver.workspace}:{layer_name}"
            
            # 1. 检查图层信息
            try:
                layer_info = geoserver.get_layer_info(full_name)
                if not layer_info:
                    self.stdout.write(self.style.ERROR(f'   ❌ 图层 "{layer_name}" 不存在'))
                    continue
                
                # 检查图层是否启用
                layer_enabled = layer_info.get('layer', {}).get('enabled', False)
                if not layer_enabled:
                    self.stdout.write(self.style.WARNING(f'   ⚠️  图层 "{layer_name}" 未启用，正在启用...'))
                    layer_info['layer']['enabled'] = True
                    update_url = f"{geoserver.base_url}/rest/layers/{full_name}.json"
                    response = requests.put(
                        update_url,
                        auth=geoserver.auth,
                        json=layer_info,
                        headers={'Content-Type': 'application/json'},
                        timeout=30
                    )
                    if response.status_code in [200, 204]:
                        self.stdout.write(self.style.SUCCESS(f'   ✅ 图层已启用'))
                    else:
                        self.stdout.write(self.style.ERROR(f'   ❌ 启用失败: {response.status_code}'))
                
                # 2. 测试WMS GetMap（使用正确的BBOX格式）
                # WMS 1.3.0使用CRS轴顺序，EPSG:4326是纬度,经度顺序
                # 但EPSG:3857是X,Y顺序
                test_urls = [
                    # 使用EPSG:3857（Web Mercator）
                    f"{geoserver.base_url}/ows?service=WMS&version=1.3.0&request=GetMap&layers={full_name}&format=image/png&transparent=true&CRS=EPSG:3857&BBOX=11690000,4070000,11850000,4200000&WIDTH=256&HEIGHT=256",
                    # 使用EPSG:4326（WGS84）
                    f"{geoserver.base_url}/ows?service=WMS&version=1.3.0&request=GetMap&layers={full_name}&format=image/png&transparent=true&CRS=EPSG:4326&BBOX=105.0,34.0,106.5,35.0&WIDTH=256&HEIGHT=256"
                ]
                
                success = False
                for i, test_url in enumerate(test_urls):
                    crs_name = 'EPSG:3857' if i == 0 else 'EPSG:4326'
                    try:
                        response = requests.get(test_url, auth=geoserver.auth, timeout=10)
                        if response.status_code == 200:
                            content_type = response.headers.get('content-type', '')
                            if 'image' in content_type:
                                self.stdout.write(self.style.SUCCESS(f'   ✅ WMS服务正常 ({crs_name})'))
                                success = True
                                break
                            else:
                                # 读取错误信息
                                text = response.text[:1000]
                                if 'ServiceException' in text:
                                    # 提取错误信息
                                    import re
                                    error_match = re.search(r'<ServiceException[^>]*>([^<]+)</ServiceException>', text)
                                    if error_match:
                                        error_msg = error_match.group(1).strip()
                                        self.stdout.write(self.style.ERROR(f'   ❌ WMS错误 ({crs_name}): {error_msg}'))
                                    else:
                                        self.stdout.write(self.style.ERROR(f'   ❌ WMS返回非图像格式 ({crs_name})'))
                                        self.stdout.write(f'   响应内容: {text[:200]}')
                                else:
                                    self.stdout.write(self.style.WARNING(f'   ⚠️  WMS返回非图像格式 ({crs_name}): {content_type}'))
                        else:
                            self.stdout.write(self.style.ERROR(f'   ❌ WMS请求失败 ({crs_name}): HTTP {response.status_code}'))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'   ❌ WMS请求异常 ({crs_name}): {str(e)}'))
                
                if not success:
                    # 尝试获取详细错误信息
                    self.stdout.write('   💡 尝试获取详细错误信息...')
                    try:
                        # 使用GetCapabilities检查图层是否在列表中
                        caps_url = f"{geoserver.base_url}/ows?service=WMS&version=1.3.0&request=GetCapabilities"
                        caps_response = requests.get(caps_url, auth=geoserver.auth, timeout=10)
                        if caps_response.status_code == 200:
                            caps_text = caps_response.text
                            if full_name in caps_text:
                                self.stdout.write(self.style.SUCCESS(f'   ✅ 图层在WMS能力列表中'))
                            else:
                                self.stdout.write(self.style.WARNING(f'   ⚠️  图层不在WMS能力列表中'))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'   ❌ 获取能力信息失败: {str(e)}'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ❌ 检查图层失败: {str(e)}'))
        
        self.stdout.write('')
        self.stdout.write('✅ 检查完成！')

