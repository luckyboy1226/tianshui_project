from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('environment', '0017_businesslayer_external_services'),
    ]

    operations = [
        migrations.AlterField(
            model_name='businesslayer',
            name='source_format',
            field=models.CharField(
                choices=[
                    ('shapefile', 'Shapefile ZIP'),
                    ('kml', 'KML'),
                    ('geotiff', 'GeoTIFF'),
                    ('wms', '外部WMS服务'),
                    ('wfs', '外部WFS服务'),
                    ('wcs', '外部WCS服务'),
                ],
                max_length=20,
                verbose_name='源数据格式',
            ),
        ),
        migrations.AddField(
            model_name='businesslayer',
            name='service_checked_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='服务检测时间'),
        ),
        migrations.AddField(
            model_name='businesslayer',
            name='service_health_message',
            field=models.CharField(blank=True, max_length=500, null=True, verbose_name='服务可用性说明'),
        ),
        migrations.AddField(
            model_name='businesslayer',
            name='service_health_status',
            field=models.CharField(default='unknown', max_length=20, verbose_name='服务可用性状态'),
        ),
        migrations.AddField(
            model_name='businesslayer',
            name='service_srs',
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name='服务坐标系'),
        ),
        migrations.AddField(
            model_name='businesslayer',
            name='style_name',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='样式名称'),
        ),
    ]
