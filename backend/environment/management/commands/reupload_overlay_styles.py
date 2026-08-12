"""
重新上传叠加分析图层样式的管理命令

修复SLD样式编码问题并重新上传
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from environment.geoserver_config import get_geoserver_manager
import os
import requests


class Command(BaseCommand):
    help = '重新上传叠加分析图层样式，修复编码问题'

    def handle(self, *args, **options):
        self.stdout.write('🔧 重新上传叠加分析图层样式...\n')
        
        geoserver = get_geoserver_manager()
        base_dir = settings.BASE_DIR
        
        # 样式配置
        styles_config = [
            {
                'style_name': 'ecology_raster',
                'sld_file': 'media/ecological_projects/ecology_raster_dem_style.sld',
                'layer_name': 'ecology_raster'
            },
            {
                'style_name': 'economy_vector',
                'sld_file': 'media/ecological_projects/economy_vector.sld',
                'layer_name': 'economy_vector'
            },
            {
                'style_name': 'engineering_vector',
                'sld_file': 'media/ecological_projects/engineering_vector.sld',
                'layer_name': 'engineering_vector'
            }
        ]
        
        for style_config in styles_config:
            style_name = style_config['style_name']
            sld_file_rel = style_config['sld_file']
            layer_name = style_config['layer_name']
            
            self.stdout.write(f'\n📋 处理样式: {style_name}')
            
            # 1. 读取SLD文件（确保UTF-8编码）
            sld_file_path = os.path.join(base_dir, sld_file_rel)
            if not os.path.exists(sld_file_path):
                self.stdout.write(self.style.ERROR(f'   ❌ SLD文件不存在: {sld_file_path}'))
                continue
            
            try:
                # 读取文件内容（UTF-8编码）
                with open(sld_file_path, 'rb') as f:
                    raw_data = f.read()
                
                # 移除BOM（如果存在）
                if raw_data.startswith(b'\xef\xbb\xbf'):
                    raw_data = raw_data[3:]
                
                # 解码为UTF-8
                sld_content = raw_data.decode('utf-8')
                
                # 验证内容
                if not sld_content.strip() or not sld_content.startswith('<?xml'):
                    self.stdout.write(self.style.ERROR(f'   ❌ SLD文件格式错误'))
                    continue
                
                self.stdout.write(self.style.SUCCESS(f'   ✅ SLD文件读取成功'))
                self.stdout.write(f'   📄 文件大小: {len(sld_content)} 字节')
                
                # 2. 删除旧样式
                try:
                    delete_url = f"{geoserver.base_url}/rest/styles/{style_name}?purge=true"
                    delete_response = requests.delete(delete_url, auth=geoserver.auth, timeout=10)
                    if delete_response.status_code in [200, 204]:
                        self.stdout.write(f'   🗑️  旧样式已删除')
                    elif delete_response.status_code == 404:
                        self.stdout.write(f'   ℹ️  样式不存在，将创建新样式')
                    else:
                        self.stdout.write(self.style.WARNING(f'   ⚠️  删除旧样式失败: {delete_response.status_code}'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'   ⚠️  删除旧样式异常: {str(e)}'))
                
                # 3. 创建样式元数据
                try:
                    style_data = {
                        "style": {
                            "name": style_name,
                            "filename": f"{style_name}.sld"
                        }
                    }
                    
                    create_url = f"{geoserver.base_url}/rest/styles"
                    create_response = requests.post(
                        create_url,
                        auth=geoserver.auth,
                        json=style_data,
                        headers={'Content-Type': 'application/json'},
                        timeout=10
                    )
                    
                    if create_response.status_code in [200, 201]:
                        self.stdout.write(self.style.SUCCESS(f'   ✅ 样式元数据创建成功'))
                    elif create_response.status_code == 409:
                        self.stdout.write(f'   ℹ️  样式已存在，将更新')
                    else:
                        self.stdout.write(self.style.WARNING(f'   ⚠️  创建样式元数据失败: {create_response.status_code}'))
                        if create_response.text:
                            self.stdout.write(f'   响应: {create_response.text[:200]}')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'   ⚠️  创建样式元数据异常: {str(e)}'))
                
                # 4. 上传SLD内容（确保UTF-8编码）
                try:
                    # 将内容编码为UTF-8字节
                    sld_bytes = sld_content.encode('utf-8')
                    
                    upload_url = f"{geoserver.base_url}/rest/styles/{style_name}"
                    upload_response = requests.put(
                        upload_url,
                        auth=geoserver.auth,
                        data=sld_bytes,
                        headers={
                            'Content-Type': 'application/vnd.ogc.sld+xml; charset=utf-8'
                        },
                        timeout=30
                    )
                    
                    if upload_response.status_code in [200, 201, 204]:
                        self.stdout.write(self.style.SUCCESS(f'   ✅ SLD内容上传成功'))
                    else:
                        self.stdout.write(self.style.ERROR(f'   ❌ SLD内容上传失败: {upload_response.status_code}'))
                        if upload_response.text:
                            self.stdout.write(f'   响应: {upload_response.text[:500]}')
                        continue
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'   ❌ 上传SLD内容异常: {str(e)}'))
                    continue
                
                # 5. 应用样式到图层
                try:
                    full_layer_name = f"{geoserver.workspace}:{layer_name}"
                    apply_url = f"{geoserver.base_url}/rest/layers/{full_layer_name}"
                    
                    # 获取图层信息
                    layer_info = geoserver.get_layer_info(full_layer_name)
                    if layer_info:
                        # 更新默认样式
                        layer_info['layer']['defaultStyle'] = {
                            'name': style_name,
                            'workspace': geoserver.workspace
                        }
                        
                        apply_response = requests.put(
                            apply_url,
                            auth=geoserver.auth,
                            json=layer_info,
                            headers={'Content-Type': 'application/json'},
                            timeout=30
                        )
                        
                        if apply_response.status_code in [200, 204]:
                            self.stdout.write(self.style.SUCCESS(f'   ✅ 样式已应用到图层 "{layer_name}"'))
                        else:
                            self.stdout.write(self.style.WARNING(f'   ⚠️  应用样式失败: {apply_response.status_code}'))
                            if apply_response.text:
                                self.stdout.write(f'   响应: {apply_response.text[:200]}')
                    else:
                        self.stdout.write(self.style.WARNING(f'   ⚠️  图层 "{layer_name}" 不存在，无法应用样式'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'   ⚠️  应用样式异常: {str(e)}'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ❌ 处理样式失败: {str(e)}'))
                import traceback
                self.stdout.write(f'   错误详情: {traceback.format_exc()}')
        
        self.stdout.write('')
        self.stdout.write('✅ 样式重新上传完成！')
        self.stdout.write('💡 建议运行检查命令验证配置: python manage.py check_geoserver_overlay_layers')




