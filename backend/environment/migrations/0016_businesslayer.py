from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('environment', '0015_expand_climate_file_types'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BusinessLayer',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200, verbose_name='图层名称')),
                ('description', models.TextField(blank=True, null=True, verbose_name='描述')),
                ('layer_type', models.CharField(choices=[('vector', '矢量图层'), ('raster', '栅格图层')], max_length=20, verbose_name='图层类型')),
                ('source_format', models.CharField(choices=[('shapefile', 'Shapefile ZIP'), ('geotiff', 'GeoTIFF')], max_length=20, verbose_name='源数据格式')),
                ('file', models.FileField(upload_to='business_layers/source/', verbose_name='源数据文件')),
                ('status', models.CharField(choices=[('uploaded', '已上传'), ('publishing', '发布中'), ('published', '已发布'), ('failed', '发布失败')], default='uploaded', max_length=20, verbose_name='发布状态')),
                ('geoserver_workspace', models.CharField(blank=True, max_length=100, null=True, verbose_name='GeoServer工作空间')),
                ('geoserver_store_name', models.CharField(blank=True, max_length=200, null=True, verbose_name='GeoServer数据存储')),
                ('geoserver_layer_name', models.CharField(blank=True, max_length=200, null=True, verbose_name='GeoServer图层名')),
                ('wms_url', models.URLField(blank=True, max_length=1000, null=True, verbose_name='WMS地址')),
                ('wfs_url', models.URLField(blank=True, max_length=1000, null=True, verbose_name='WFS地址')),
                ('wcs_url', models.URLField(blank=True, max_length=1000, null=True, verbose_name='WCS地址')),
                ('metadata', models.JSONField(blank=True, default=dict, verbose_name='图层元数据')),
                ('error_message', models.TextField(blank=True, null=True, verbose_name='错误信息')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('published_at', models.DateTimeField(blank=True, null=True, verbose_name='发布时间')),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='上传用户')),
            ],
            options={
                'verbose_name': '业务图层',
                'verbose_name_plural': '业务图层',
                'db_table': 'business_layers',
                'ordering': ['-created_at'],
            },
        ),
    ]
