from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('environment', '0018_businesslayer_kml_health_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='businesslayer',
            name='sld_content',
            field=models.TextField(blank=True, null=True, verbose_name='SLD内容'),
        ),
        migrations.AddField(
            model_name='businesslayer',
            name='style_config',
            field=models.JSONField(blank=True, default=dict, verbose_name='样式配置'),
        ),
        migrations.CreateModel(
            name='BusinessLayerAuditLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('action', models.CharField(choices=[('upload', '上传'), ('publish', '发布'), ('unpublish', '撤销发布'), ('delete', '删除'), ('style_update', '样式更新'), ('health_check', '服务检测')], max_length=30, verbose_name='操作类型')),
                ('status', models.CharField(choices=[('success', '成功'), ('failed', '失败'), ('info', '信息')], default='info', max_length=20, verbose_name='操作结果')),
                ('operator_name', models.CharField(blank=True, max_length=150, null=True, verbose_name='操作人名称')),
                ('message', models.CharField(blank=True, max_length=500, null=True, verbose_name='说明')),
                ('details', models.JSONField(blank=True, default=dict, verbose_name='日志详情')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('business_layer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_logs', to='environment.businesslayer', verbose_name='业务图层')),
                ('operator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='操作人')),
            ],
            options={
                'verbose_name': '业务图层审计日志',
                'verbose_name_plural': '业务图层审计日志',
                'db_table': 'business_layer_audit_logs',
                'ordering': ['-created_at'],
            },
        ),
    ]
