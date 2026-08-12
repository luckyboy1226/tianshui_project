"""
Django管理命令：重新发布栅格图层到GeoServer

用于修复之前分析任务中未成功发布的栅格图层

使用方法:
    python manage.py republish_raster_layers <task_id>
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from environment.models import OverlayAnalysisTask
from environment.geoserver_config import get_geoserver_manager
import os


class Command(BaseCommand):
    help = '重新发布叠加分析任务的栅格图层到GeoServer'

    def add_arguments(self, parser):
        parser.add_argument('task_id', type=str, help='任务ID')
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新发布，即使已存在WMS URL'
        )

    def handle(self, *args, **options):
        task_id = options['task_id']
        force = options.get('force', False)
        
        try:
            task = OverlayAnalysisTask.objects.get(id=task_id)
        except OverlayAnalysisTask.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'任务不存在: {task_id}'))
            return
        
        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write(self.style.WARNING(f'重新发布栅格图层 - 任务: {task.name}'))
        self.stdout.write(self.style.WARNING('=' * 60))
        
        geoserver = get_geoserver_manager()
        
        # 测试GeoServer连接
        self.stdout.write('\n[1/3] 测试GeoServer连接...')
        capabilities = geoserver.get_wms_capabilities()
        if not capabilities:
            self.stdout.write(self.style.ERROR('❌ GeoServer连接失败！请检查配置和运行状态'))
            return
        self.stdout.write(self.style.SUCCESS('✅ GeoServer连接成功'))
        
        # 确保工作空间存在
        self.stdout.write('\n[2/3] 创建工作空间...')
        geoserver.create_workspace()
        self.stdout.write(self.style.SUCCESS('✅ 工作空间就绪'))
        
        # 清理旧的CoverageStore（如果需要）
        coverage_store_name = f"overlay_{task.id}"
        self.stdout.write(f'\n[2.5/3] 清理旧的CoverageStore（如果需要）...')
        geoserver.delete_coveragestore(coverage_store_name, recurse=True)
        self.stdout.write(self.style.SUCCESS('✅ CoverageStore已清理'))
        
        # 获取栅格文件
        self.stdout.write('\n[3/3] 发布栅格图层...')
        
        published_count = 0
        raster_metadata = task.raster_layers_metadata.copy() if task.raster_layers_metadata else {}
        
        # 发布风险栅格
        if task.risk_raster_file:
            risk_file_path = task.risk_raster_file.path
            if os.path.exists(risk_file_path):
                layer_name = f"risk_layer_{task.id}"
                self.stdout.write(f'\n  发布风险栅格: {layer_name}')
                self.stdout.write(f'    文件: {risk_file_path}')
                
                if not force and raster_metadata.get('risk_layer', {}).get('wms_url'):
                    self.stdout.write(self.style.WARNING('    ⚠️  已存在WMS URL，跳过（使用--force强制重新发布）'))
                else:
                    # coverage_store_name已在前面定义
                    
                    if geoserver.publish_raster(coverage_store_name, layer_name, risk_file_path):
                        wms_url = f"{geoserver.base_url}/ows?service=WMS&version=1.3.0&request=GetMap&layers={geoserver.workspace}:{layer_name}&format=image/png&transparent=true"
                        
                        if 'risk_layer' not in raster_metadata:
                            raster_metadata['risk_layer'] = {}
                        
                        raster_metadata['risk_layer'].update({
                            'layer_name': layer_name,
                            'wms_url': wms_url,
                            'file_path': task.risk_raster_file.name,
                            'published': True
                        })
                        
                        self.stdout.write(self.style.SUCCESS(f'    ✅ 发布成功'))
                        self.stdout.write(f'    WMS URL: {wms_url}')
                        published_count += 1
                    else:
                        self.stdout.write(self.style.ERROR(f'    ❌ 发布失败'))
            else:
                self.stdout.write(self.style.ERROR(f'   ❌ 风险栅格文件不存在: {risk_file_path}'))
        
        # 发布影响栅格
        if task.impact_raster_file:
            impact_file_path = task.impact_raster_file.path
            if os.path.exists(impact_file_path):
                layer_name = f"impact_layer_{task.id}"
                self.stdout.write(f'\n  发布影响栅格: {layer_name}')
                self.stdout.write(f'    文件: {impact_file_path}')
                
                if not force and raster_metadata.get('impact_layer', {}).get('wms_url'):
                    self.stdout.write(self.style.WARNING('    ⚠️  已存在WMS URL，跳过（使用--force强制重新发布）'))
                else:
                    # coverage_store_name已在前面定义
                    
                    if geoserver.publish_raster(coverage_store_name, layer_name, impact_file_path):
                        wms_url = f"{geoserver.base_url}/ows?service=WMS&version=1.3.0&request=GetMap&layers={geoserver.workspace}:{layer_name}&format=image/png&transparent=true"
                        
                        if 'impact_layer' not in raster_metadata:
                            raster_metadata['impact_layer'] = {}
                        
                        raster_metadata['impact_layer'].update({
                            'layer_name': layer_name,
                            'wms_url': wms_url,
                            'file_path': task.impact_raster_file.name,
                            'published': True
                        })
                        
                        self.stdout.write(self.style.SUCCESS(f'    ✅ 发布成功'))
                        self.stdout.write(f'    WMS URL: {wms_url}')
                        published_count += 1
                    else:
                        self.stdout.write(self.style.ERROR(f'    ❌ 发布失败'))
            else:
                self.stdout.write(self.style.ERROR(f'   ❌ 影响栅格文件不存在: {impact_file_path}'))
        
        # 更新任务的栅格图层元数据
        if published_count > 0:
            task.raster_layers_metadata = raster_metadata
            
            # 更新分析结果中的栅格图层信息
            if task.analysis_results:
                task.analysis_results['raster_layers'] = raster_metadata
            else:
                task.analysis_results = {'raster_layers': raster_metadata}
            
            task.save()
            self.stdout.write(self.style.SUCCESS(f'\n✅ 已更新任务的栅格图层元数据'))
        
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS(f'完成！成功发布 {published_count} 个栅格图层'))
        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write('\n提示：刷新前端页面即可看到更新后的栅格图层\n')

