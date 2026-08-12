from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('environment', '0016_businesslayer'),
    ]

    operations = [
        migrations.AlterField(
            model_name='businesslayer',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to='business_layers/source/', verbose_name='源数据文件'),
        ),
        migrations.AlterField(
            model_name='businesslayer',
            name='source_format',
            field=models.CharField(
                choices=[
                    ('shapefile', 'Shapefile ZIP'),
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
            name='service_type_name',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='服务图层名称'),
        ),
        migrations.AddField(
            model_name='businesslayer',
            name='service_url',
            field=models.URLField(blank=True, max_length=1000, null=True, verbose_name='标准服务地址'),
        ),
    ]
