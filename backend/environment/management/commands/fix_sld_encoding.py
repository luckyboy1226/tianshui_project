"""
修复SLD文件编码问题
确保所有SLD文件都是UTF-8编码（无BOM）
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = '修复SLD文件编码问题，确保都是UTF-8编码（无BOM）'

    def handle(self, *args, **options):
        self.stdout.write('🔧 修复SLD文件编码问题...\n')
        
        base_dir = settings.BASE_DIR
        sld_dir = os.path.join(base_dir, 'media', 'ecological_projects')
        
        # 需要修复的SLD文件
        sld_files = [
            'ecology_raster.sld',
            'ecology_raster_dem_style.sld',
            'economy_vector.sld',
            'engineering_vector.sld',
            'engineering_vector_colored.sld',
            'ecology_raster_simple.sld'
        ]
        
        for sld_file in sld_files:
            sld_path = os.path.join(sld_dir, sld_file)
            
            if not os.path.exists(sld_path):
                self.stdout.write(self.style.WARNING(f'   ⚠️  文件不存在: {sld_file}'))
                continue
            
            try:
                # 1. 读取原始文件（二进制模式）
                with open(sld_path, 'rb') as f:
                    raw_data = f.read()
                
                # 2. 移除BOM（如果存在）
                if raw_data.startswith(b'\xef\xbb\xbf'):
                    raw_data = raw_data[3:]
                    self.stdout.write(f'   📝 {sld_file}: 已移除BOM')
                
                # 3. 尝试解码为UTF-8
                try:
                    content = raw_data.decode('utf-8')
                except UnicodeDecodeError:
                    # 如果UTF-8解码失败，尝试其他编码
                    try:
                        content = raw_data.decode('gbk')
                        self.stdout.write(f'   📝 {sld_file}: 从GBK转换为UTF-8')
                    except UnicodeDecodeError:
                        self.stdout.write(self.style.ERROR(f'   ❌ {sld_file}: 无法解码'))
                        continue
                
                # 4. 验证XML格式
                if not content.strip().startswith('<?xml'):
                    self.stdout.write(self.style.ERROR(f'   ❌ {sld_file}: 不是有效的XML文件'))
                    continue
                
                # 5. 确保XML声明使用UTF-8编码
                if 'encoding="UTF-8"' not in content[:100]:
                    # 替换XML声明
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if '<?xml' in line and 'encoding' in line:
                            lines[i] = '<?xml version="1.0" encoding="UTF-8"?>'
                            break
                    content = '\n'.join(lines)
                    self.stdout.write(f'   📝 {sld_file}: 已更新XML声明')
                
                # 6. 重新编码为UTF-8（无BOM）
                utf8_bytes = content.encode('utf-8')
                
                # 7. 备份原文件
                backup_path = sld_path + '.backup'
                if not os.path.exists(backup_path):
                    with open(backup_path, 'wb') as f:
                        with open(sld_path, 'rb') as orig:
                            f.write(orig.read())
                    self.stdout.write(f'   💾 {sld_file}: 已创建备份')
                
                # 8. 写入修复后的文件
                with open(sld_path, 'wb') as f:
                    f.write(utf8_bytes)
                
                self.stdout.write(self.style.SUCCESS(f'   ✅ {sld_file}: 编码已修复'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ❌ {sld_file}: 处理失败 - {str(e)}'))
        
        self.stdout.write('')
        self.stdout.write('✅ SLD文件编码修复完成！')
        self.stdout.write('💡 建议运行重新上传命令: python manage.py reupload_overlay_styles')
