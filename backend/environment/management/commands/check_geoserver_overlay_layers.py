"""
检查GeoServer叠加分析图层配置的管理命令

检查三个WMS图层是否已正确配置：
1. ecology_raster - 生态栅格
2. economy_vector - 经济矢量
3. engineering_vector - 工程矢量

使用方法:
    python manage.py check_geoserver_overlay_layers
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from environment.geoserver_config import get_geoserver_manager
import sys


class Command(BaseCommand):
    help = '检查GeoServer叠加分析图层配置状态'

    def handle(self, *args, **options):
        self.stdout.write('🔍 检查GeoServer叠加分析图层配置...\n')
        
        geoserver = get_geoserver_manager()
        
        # 检查项
        checks = {
            'connection': False,
            'workspace': False,
            'ecology_raster': False,
            'economy_vector': False,
            'engineering_vector': False,
            'ecology_style': False,
            'economy_style': False,
            'engineering_style': False
        }
        
        # 1. 检查GeoServer连接
        self.stdout.write('1️⃣ 检查GeoServer连接...')
        try:
            capabilities = geoserver.get_wms_capabilities()
            if capabilities:
                checks['connection'] = True
                self.stdout.write(self.style.SUCCESS('   ✅ GeoServer连接正常'))
                self.stdout.write(f'   📍 URL: {geoserver.base_url}')
                self.stdout.write(f'   👤 用户名: {geoserver.username}')
                self.stdout.write(f'   📁 工作空间: {geoserver.workspace}')
            else:
                self.stdout.write(self.style.ERROR('   ❌ GeoServer连接失败'))
                self.stdout.write('   💡 请检查:')
                self.stdout.write('      - GeoServer是否运行')
                self.stdout.write('      - URL是否正确')
                self.stdout.write('      - 用户名和密码是否正确')
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ GeoServer连接失败: {str(e)}'))
            self.stdout.write('   💡 请检查:')
            self.stdout.write('      - GeoServer是否运行 (http://localhost:8080/geoserver)')
            self.stdout.write('      - 网络连接是否正常')
            return
        
        self.stdout.write('')
        
        # 2. 检查工作空间
        self.stdout.write('2️⃣ 检查工作空间...')
        try:
            workspace_info = geoserver._make_request('GET', f'workspaces/{geoserver.workspace}.json')
            if workspace_info:
                checks['workspace'] = True
                self.stdout.write(self.style.SUCCESS(f'   ✅ 工作空间 "{geoserver.workspace}" 存在'))
            else:
                self.stdout.write(self.style.WARNING(f'   ⚠️  工作空间 "{geoserver.workspace}" 不存在'))
                self.stdout.write('   💡 尝试创建工作空间...')
                if geoserver.create_workspace():
                    checks['workspace'] = True
                    self.stdout.write(self.style.SUCCESS('   ✅ 工作空间创建成功'))
                else:
                    self.stdout.write(self.style.ERROR('   ❌ 工作空间创建失败'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ 检查工作空间失败: {str(e)}'))
        
        self.stdout.write('')
        
        # 3. 检查生态栅格图层
        self.stdout.write('3️⃣ 检查生态栅格图层 (ecology_raster)...')
        layer_name = 'ecology_raster'
        full_layer_name = f"{geoserver.workspace}:{layer_name}"
        
        try:
            layer_info = geoserver.get_layer_info(full_layer_name)
            if layer_info:
                checks['ecology_raster'] = True
                self.stdout.write(self.style.SUCCESS(f'   ✅ 图层 "{layer_name}" 已发布'))
                
                # 检查图层状态
                layer_state = layer_info.get('layer', {}).get('enabled', False)
                # 处理字符串形式的布尔值
                if isinstance(layer_state, str):
                    layer_state = layer_state.lower() in ('true', '1', 'yes')
                if layer_state:
                    self.stdout.write('   ✅ 图层已启用')
                else:
                    self.stdout.write(self.style.WARNING('   ⚠️  图层未启用'))
                    # 自动启用图层
                    try:
                        layer_info['layer']['enabled'] = True
                        import requests
                        update_url = f"{geoserver.base_url}/rest/layers/{full_layer_name}.json"
                        response = requests.put(
                            update_url,
                            auth=geoserver.auth,
                            json=layer_info,
                            headers={'Content-Type': 'application/json'},
                            timeout=30
                        )
                        if response.status_code in [200, 204]:
                            self.stdout.write(self.style.SUCCESS('   ✅ 已自动启用图层'))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'   ⚠️  自动启用失败: {str(e)}'))
                
                # 检查默认样式
                default_style = layer_info.get('layer', {}).get('defaultStyle', {}).get('name', '')
                if default_style:
                    self.stdout.write(f'   📝 默认样式: {default_style}')
                else:
                    self.stdout.write(self.style.WARNING('   ⚠️  未设置默认样式'))
            else:
                self.stdout.write(self.style.ERROR(f'   ❌ 图层 "{layer_name}" 未发布'))
                self.stdout.write('   💡 需要发布图层:')
                self.stdout.write('      - 文件: media/ecological_projects/ecology_raster.tif')
                self.stdout.write('      - 使用命令: python manage.py publish_raster_layer --file ecology_raster.tif')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ 检查图层失败: {str(e)}'))
        
        self.stdout.write('')
        
        # 4. 检查经济矢量图层
        self.stdout.write('4️⃣ 检查经济矢量图层 (economy_vector)...')
        layer_name = 'economy_vector'
        full_layer_name = f"{geoserver.workspace}:{layer_name}"
        
        try:
            layer_info = geoserver.get_layer_info(full_layer_name)
            if layer_info:
                checks['economy_vector'] = True
                self.stdout.write(self.style.SUCCESS(f'   ✅ 图层 "{layer_name}" 已发布'))
                
                # 检查图层状态
                layer_state = layer_info.get('layer', {}).get('enabled', False)
                # 处理字符串形式的布尔值
                if isinstance(layer_state, str):
                    layer_state = layer_state.lower() in ('true', '1', 'yes')
                if layer_state:
                    self.stdout.write('   ✅ 图层已启用')
                else:
                    self.stdout.write(self.style.WARNING('   ⚠️  图层未启用'))
                    # 自动启用图层
                    try:
                        layer_info['layer']['enabled'] = True
                        import requests
                        update_url = f"{geoserver.base_url}/rest/layers/{full_layer_name}.json"
                        response = requests.put(
                            update_url,
                            auth=geoserver.auth,
                            json=layer_info,
                            headers={'Content-Type': 'application/json'},
                            timeout=30
                        )
                        if response.status_code in [200, 204]:
                            self.stdout.write(self.style.SUCCESS('   ✅ 已自动启用图层'))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'   ⚠️  自动启用失败: {str(e)}'))
                
                # 检查默认样式
                default_style = layer_info.get('layer', {}).get('defaultStyle', {}).get('name', '')
                if default_style:
                    self.stdout.write(f'   📝 默认样式: {default_style}')
                    if default_style == 'economy_vector':
                        checks['economy_style'] = True
                else:
                    self.stdout.write(self.style.WARNING('   ⚠️  未设置默认样式'))
            else:
                self.stdout.write(self.style.ERROR(f'   ❌ 图层 "{layer_name}" 未发布'))
                self.stdout.write('   💡 需要发布图层:')
                self.stdout.write('      - 文件: media/ecological_projects/economy_vector.shp')
                self.stdout.write('      - 可以通过GeoServer Web界面发布')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ 检查图层失败: {str(e)}'))
        
        self.stdout.write('')
        
        # 5. 检查工程矢量图层
        self.stdout.write('5️⃣ 检查工程矢量图层 (engineering_vector)...')
        layer_name = 'engineering_vector'
        full_layer_name = f"{geoserver.workspace}:{layer_name}"
        
        try:
            layer_info = geoserver.get_layer_info(full_layer_name)
            if layer_info:
                checks['engineering_vector'] = True
                self.stdout.write(self.style.SUCCESS(f'   ✅ 图层 "{layer_name}" 已发布'))
                
                # 检查图层状态
                layer_state = layer_info.get('layer', {}).get('enabled', False)
                # 处理字符串形式的布尔值
                if isinstance(layer_state, str):
                    layer_state = layer_state.lower() in ('true', '1', 'yes')
                if layer_state:
                    self.stdout.write('   ✅ 图层已启用')
                else:
                    self.stdout.write(self.style.WARNING('   ⚠️  图层未启用'))
                    # 自动启用图层
                    try:
                        layer_info['layer']['enabled'] = True
                        import requests
                        update_url = f"{geoserver.base_url}/rest/layers/{full_layer_name}.json"
                        response = requests.put(
                            update_url,
                            auth=geoserver.auth,
                            json=layer_info,
                            headers={'Content-Type': 'application/json'},
                            timeout=30
                        )
                        if response.status_code in [200, 204]:
                            self.stdout.write(self.style.SUCCESS('   ✅ 已自动启用图层'))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'   ⚠️  自动启用失败: {str(e)}'))
                
                # 检查默认样式
                default_style = layer_info.get('layer', {}).get('defaultStyle', {}).get('name', '')
                if default_style:
                    self.stdout.write(f'   📝 默认样式: {default_style}')
                    if default_style == 'engineering_vector':
                        checks['engineering_style'] = True
                else:
                    self.stdout.write(self.style.WARNING('   ⚠️  未设置默认样式'))
            else:
                self.stdout.write(self.style.ERROR(f'   ❌ 图层 "{layer_name}" 未发布'))
                self.stdout.write('   💡 需要发布图层:')
                self.stdout.write('      - 文件: media/ecological_projects/engineering_vector.shp')
                self.stdout.write('      - 可以通过GeoServer Web界面发布')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ 检查图层失败: {str(e)}'))
        
        self.stdout.write('')
        
        # 6. 检查样式配置
        self.stdout.write('6️⃣ 检查SLD样式配置...')
        
        def check_style(style_name, check_key):
            """检查样式是否存在（在工作空间或全局）"""
            import requests
            
            # 先检查工作空间样式
            try:
                url = f"{geoserver.base_url}/rest/workspaces/{geoserver.workspace}/styles/{style_name}.json"
                response = requests.get(url, auth=geoserver.auth, timeout=5)
                if response.status_code == 200:
                    checks[check_key] = True
                    return True
            except:
                pass
            
            # 再检查全局样式
            try:
                url = f"{geoserver.base_url}/rest/styles/{style_name}.json"
                response = requests.get(url, auth=geoserver.auth, timeout=5)
                if response.status_code == 200:
                    checks[check_key] = True
                    return True
            except:
                pass
            
            return False
        
        # 检查生态栅格样式
        try:
            if check_style('ecology_raster', 'ecology_style'):
                self.stdout.write(self.style.SUCCESS('   ✅ 生态栅格样式 (ecology_raster) 已配置'))
            else:
                self.stdout.write(self.style.WARNING('   ⚠️  生态栅格样式未配置'))
                self.stdout.write('   💡 SLD文件: media/ecological_projects/ecology_raster.sld')
                # 尝试自动配置
                try:
                    import os
                    base_dir = settings.BASE_DIR
                    sld_file_path = os.path.join(base_dir, 'media', 'ecological_projects', 'ecology_raster_dem_style.sld')
                    if not os.path.exists(sld_file_path):
                        sld_file_path = os.path.join(base_dir, 'media', 'ecological_projects', 'ecology_raster.sld')
                    if os.path.exists(sld_file_path):
                        with open(sld_file_path, 'r', encoding='utf-8') as f:
                            sld_content = f.read()
                        if geoserver.create_style('ecology_raster', sld_content):
                            if geoserver.apply_style_to_layer('ecology_raster', 'ecology_raster'):
                                checks['ecology_style'] = True
                                self.stdout.write(self.style.SUCCESS('   ✅ 已自动配置生态栅格样式'))
                            else:
                                self.stdout.write(self.style.WARNING('   ⚠️  样式创建成功但应用失败'))
                        else:
                            # 样式可能已存在，尝试应用
                            if geoserver.apply_style_to_layer('ecology_raster', 'ecology_raster'):
                                checks['ecology_style'] = True
                                self.stdout.write(self.style.SUCCESS('   ✅ 样式已存在，已应用'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'   ⚠️  自动配置失败: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'   ⚠️  检查生态栅格样式失败: {str(e)}'))
        
        # 检查经济矢量样式
        try:
            if check_style('economy_vector', 'economy_style'):
                self.stdout.write(self.style.SUCCESS('   ✅ 经济矢量样式 (economy_vector) 已配置'))
            else:
                self.stdout.write(self.style.WARNING('   ⚠️  经济矢量样式未配置'))
                self.stdout.write('   💡 SLD文件: media/ecological_projects/economy_vector.sld')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'   ⚠️  检查经济矢量样式失败: {str(e)}'))
        
        # 检查工程矢量样式
        try:
            if check_style('engineering_vector', 'engineering_style'):
                self.stdout.write(self.style.SUCCESS('   ✅ 工程矢量样式 (engineering_vector) 已配置'))
            else:
                self.stdout.write(self.style.WARNING('   ⚠️  工程矢量样式未配置'))
                self.stdout.write('   💡 SLD文件: media/ecological_projects/engineering_vector.sld')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'   ⚠️  检查工程矢量样式失败: {str(e)}'))
        
        self.stdout.write('')
        
        # 7. 测试WMS服务
        self.stdout.write('7️⃣ 测试WMS服务...')
        try:
            # 测试GetCapabilities
            test_url = f"{geoserver.base_url}/ows?service=WMS&version=1.3.0&request=GetCapabilities"
            import requests
            response = requests.get(test_url, auth=geoserver.auth, timeout=5)
            
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS('   ✅ WMS服务正常'))
                
                # 测试三个图层的GetMap
                layers_to_test = ['ecology_raster', 'economy_vector', 'engineering_vector']
                for layer in layers_to_test:
                    full_name = f"{geoserver.workspace}:{layer}"
                    test_map_url = f"{geoserver.base_url}/ows?service=WMS&version=1.3.0&request=GetMap&layers={full_name}&format=image/png&transparent=true&CRS=EPSG:4326&BBOX=105.0,34.0,106.5,35.0&WIDTH=256&HEIGHT=256"
                    
                    map_response = requests.get(test_map_url, auth=geoserver.auth, timeout=5)
                    if map_response.status_code == 200:
                        content_type = map_response.headers.get('content-type', '')
                        if 'image' in content_type:
                            self.stdout.write(self.style.SUCCESS(f'   ✅ 图层 "{layer}" WMS服务正常'))
                        else:
                            self.stdout.write(self.style.WARNING(f'   ⚠️  图层 "{layer}" WMS返回非图像格式'))
                    else:
                        self.stdout.write(self.style.ERROR(f'   ❌ 图层 "{layer}" WMS服务失败: {map_response.status_code}'))
            else:
                self.stdout.write(self.style.ERROR(f'   ❌ WMS服务失败: {response.status_code}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ 测试WMS服务失败: {str(e)}'))
        
        self.stdout.write('')
        
        # 8. 总结
        self.stdout.write('📊 配置检查总结')
        self.stdout.write('=' * 50)
        
        total_checks = len(checks)
        passed_checks = sum(1 for v in checks.values() if v)
        
        self.stdout.write(f'总检查项: {total_checks}')
        self.stdout.write(f'通过: {passed_checks}')
        self.stdout.write(f'未通过: {total_checks - passed_checks}')
        self.stdout.write('')
        
        if passed_checks == total_checks:
            self.stdout.write(self.style.SUCCESS('✅ 所有检查项通过！GeoServer配置完整。'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  部分检查项未通过，请根据上述提示进行配置。'))
            self.stdout.write('')
            self.stdout.write('📋 待办事项:')
            
            if not checks['ecology_raster']:
                self.stdout.write('   - 发布生态栅格图层 (ecology_raster)')
            if not checks['economy_vector']:
                self.stdout.write('   - 发布经济矢量图层 (economy_vector)')
            if not checks['engineering_vector']:
                self.stdout.write('   - 发布工程矢量图层 (engineering_vector)')
            if not checks['ecology_style']:
                self.stdout.write('   - 配置生态栅格样式 (ecology_raster.sld)')
            if not checks['economy_style']:
                self.stdout.write('   - 配置经济矢量样式 (economy_vector.sld)')
            if not checks['engineering_style']:
                self.stdout.write('   - 配置工程矢量样式 (engineering_vector.sld)')
        
        self.stdout.write('')
        self.stdout.write('💡 配置说明文档:')
        self.stdout.write('   - backend/media/ecological_projects/SLD_USAGE.md')
        self.stdout.write('   - backend/media/ecological_projects/ECONOMY_SLD_USAGE.md')
        self.stdout.write('   - backend/media/ecological_projects/ENGINEERING_SLD_USAGE.md')

