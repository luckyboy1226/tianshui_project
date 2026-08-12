"""
修复 GeoServer 矢量图层字符编码问题
确保 Shapefile 数据源使用 UTF-8 编码
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import requests
from requests.auth import HTTPBasicAuth
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '修复 GeoServer 矢量图层字符编码问题'

    def handle(self, *args, **options):
        self.stdout.write('[*] 修复 GeoServer 矢量图层字符编码...\n')
        
        # GeoServer 配置
        geoserver_url = getattr(settings, 'GEOSERVER_URL', 'http://localhost:8080/geoserver')
        username = getattr(settings, 'GEOSERVER_USERNAME', 'admin')
        password = getattr(settings, 'GEOSERVER_PASSWORD', 'geoserver')
        workspace = getattr(settings, 'GEOSERVER_WORKSPACE', 'tianshuipy')
        auth = HTTPBasicAuth(username, password)
        
        # 需要修复的矢量图层数据源
        datastores = [
            'economy_vector',
            'engineering_vector'
        ]
        
        for datastore_name in datastores:
            self.stdout.write(f'\n[+] 处理数据源: {datastore_name}')
            
            try:
                # 1. 获取数据源配置
                datastore_url = f'{geoserver_url}/rest/workspaces/{workspace}/datastores/{datastore_name}.json'
                response = requests.get(datastore_url, auth=auth)
                
                if response.status_code != 200:
                    self.stdout.write(self.style.WARNING(f'   [!] 数据源不存在或无法访问'))
                    continue
                
                datastore_data = response.json()
                
                # 2. 检查并更新字符集配置
                connection_params = datastore_data.get('dataStore', {}).get('connectionParameters', {})
                entries = connection_params.get('entry', [])
                
                # 查找是否已有 charset 配置
                charset_exists = False
                for entry in entries:
                    if isinstance(entry, dict) and entry.get('@key') == 'charset':
                        if entry.get('$') != 'UTF-8':
                            entry['$'] = 'UTF-8'
                            self.stdout.write('   [+] 更新 charset 为 UTF-8')
                        else:
                            self.stdout.write('   [OK] charset 已经是 UTF-8')
                        charset_exists = True
                        break
                
                # 如果没有 charset 配置，添加它
                if not charset_exists:
                    entries.append({
                        '@key': 'charset',
                        '$': 'UTF-8'
                    })
                    self.stdout.write('   [+] 添加 charset=UTF-8 配置')
                
                # 3. 更新数据源配置
                update_response = requests.put(
                    datastore_url,
                    auth=auth,
                    json=datastore_data,
                    headers={'Content-Type': 'application/json'}
                )
                
                if update_response.status_code in [200, 204]:
                    self.stdout.write(self.style.SUCCESS(f'   [OK] {datastore_name} 编码配置已更新'))
                else:
                    self.stdout.write(self.style.ERROR(
                        f'   [ERROR] 更新失败: HTTP {update_response.status_code}'
                    ))
                    self.stdout.write(f'      响应: {update_response.text[:200]}')
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   [ERROR] 处理失败: {e}'))
        
        self.stdout.write('\n' + self.style.SUCCESS('[OK] 编码修复完成!'))
        self.stdout.write('[INFO] 建议: 重启 GeoServer 或重新加载工作空间以确保更改生效')

