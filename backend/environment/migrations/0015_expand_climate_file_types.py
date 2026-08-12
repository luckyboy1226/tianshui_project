from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('environment', '0014_overlayanalysistask_impact_raster_file_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='climatedatafile',
            name='file_type',
            field=models.CharField(
                choices=[
                    ('csv', 'CSV'),
                    ('xlsx', 'Excel'),
                    ('tif', 'GeoTIFF'),
                    ('zip', 'ADF ZIP'),
                ],
                default='csv',
                max_length=10,
                verbose_name='文件类型',
            ),
        ),
    ]
