import os
import io

from celery import Celery

# 设置Django默认配置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tianshuipy.settings')

# 创建Celery实例
app = Celery('tianshuipy')

# 使用Django设置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现任务
app.autodiscover_tasks()

# 配置日志记录，避免Python版本兼容性问题
import logging
import sys

# 检查Python版本
if sys.version_info < (3, 8):
    # 对于较老的Python版本，使用兼容的日志格式
    class CompatibleFormatter(logging.Formatter):
        def formatException(self, ei):
            """兼容的异常格式化方法"""
            try:
                # 使用简单的异常格式化
                import traceback
                sio = io.StringIO()
                traceback.print_exception(ei[0], ei[1], ei[2], None, sio)
                return sio.getvalue()
            except:
                return "Exception occurred"
    
    # 应用兼容的格式化器
    for handler in logging.root.handlers:
        if hasattr(handler, 'formatter'):
            handler.setFormatter(CompatibleFormatter())

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 
