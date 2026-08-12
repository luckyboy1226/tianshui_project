"""
Django管理命令：检查叠加分析任务的栅格图层状态

使用方法:
    python manage.py check_raster_layers <task_id>
    python manage.py check_raster_layers  # 检查所有任务
"""

from django.core.management.base import BaseCommand
from environment.models import OverlayAnalysisTask
from environment.geoserver_config import get_geoserver_manager
import os


class Command(BaseCommand):
    help = '检查叠加分析任务的栅格图层状态'

    def add_arguments(self, parser):
        parser.add_argument(
            'task_id',
            nargs='?',
            type=str,
            help='任务ID（可选，不提供则检查所有任务）'
        )

    def handle(self, *args, **options):
        task_id = options.get('task_id')
        
        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write(self.style.WARNING('栅格图层状态检查'))
        self.stdout.write(self.style.WARNING('=' * 60))
        
        if task_id:
            try:
                tasks = [OverlayAnalysisTask.objects.get(id=task_id)]
            except OverlayAnalysisTask.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'任务不存在: {task_id}'))
                return
        else:
            tasks = OverlayAnalysisTask.objects.filter(status='completed').order_by('-created_at')[:10]
            self.stdout.write(f'\n检查最近10个已完成的任务...')
        
        for task in tasks:
            self.stdout.write(self.style.SUCCESS(f'\n任务: {task.name} (ID: {task.id})'))
            self.stdout.write(f'创建时间: {task.created_at}')
            self.stdout.write(f'状态: {task.status}')
            
            # 检查分析结果
            if task.analysis_results:
                raster_layers = task.analysis_results.get('raster_layers', {})
                if raster_layers:
                    self.stdout.write(self.style.SUCCESS(f'  ✅ 栅格图层元数据存在'))
                    for key, layer in raster_layers.items():
                        self.stdout.write(f'\n  图层: {key}')
                        self.stdout.write(f'    名称: {layer.get("layer_name", "N/A")}')
                        self.stdout.write(f'    描述: {layer.get("description", "N/A")}')
                        wms_url = layer.get('wms_url')
                        if wms_url:
                            self.stdout.write(self.style.SUCCESS(f'    ✅ WMS URL: {wms_url}'))
                        else:
                            self.stdout.write(self.style.ERROR(f'    ❌ WMS URL: 未配置'))
                        
                        file_path = layer.get('file_path')
                        if file_path:
                            from django.conf import settings
                            full_path = os.path.join(settings.MEDIA_ROOT, file_path)
                            if os.path.exists(full_path):
                                file_size = os.path.getsize(full_path)
                                self.stdout.write(self.style.SUCCESS(f'    ✅ 栅格文件存在: {file_path} ({file_size / 1024:.2f} KB)'))
                            else:
                                self.stdout.write(self.style.ERROR(f'    ❌ 栅格文件不存在: {full_path}'))
                else:
                    self.stdout.write(self.style.WARNING(f'  ⚠️  分析结果中没有栅格图层数据'))
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠️  分析结果为空'))
            
            # 检查数据库字段
            if task.risk_raster_file:
                self.stdout.write(self.style.SUCCESS(f'  ✅ 风险栅格文件: {task.risk_raster_file.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠️  风险栅格文件: 未保存'))
                
            if task.impact_raster_file:
                self.stdout.write(self.style.SUCCESS(f'  ✅ 影响栅格文件: {task.impact_raster_file.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠️  影响栅格文件: 未保存'))
            
            # 检查栅格图层元数据
            if task.raster_layers_metadata:
                self.stdout.write(self.style.SUCCESS(f'  ✅ 栅格图层元数据: 已保存'))
                for key, layer in task.raster_layers_metadata.items():
                    wms_url = layer.get('wms_url')
                    if wms_url:
                        self.stdout.write(self.style.SUCCESS(f'    {key}: 已发布 (WMS URL存在)'))
                    else:
                        self.stdout.write(self.style.ERROR(f'    {key}: 未发布 (WMS URL缺失)'))
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠️  栅格图层元数据: 未保存'))
            
            # 检查GeoServer连接
            self.stdout.write(f'\n  GeoServer状态:')
            try:
                geoserver = get_geoserver_manager()
                capabilities = geoserver.get_wms_capabilities()
                if capabilities:
                    self.stdout.write(self.style.SUCCESS(f'    ✅ GeoServer连接正常'))
                    self.stdout.write(f'    URL: {geoserver.base_url}')
                    self.stdout.write(f'    工作空间: {geoserver.workspace}')
                else:
                    self.stdout.write(self.style.ERROR(f'    ❌ GeoServer连接失败'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'    ❌ GeoServer连接异常: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('检查完成！'))
        self.stdout.write(self.style.WARNING('=' * 60))

