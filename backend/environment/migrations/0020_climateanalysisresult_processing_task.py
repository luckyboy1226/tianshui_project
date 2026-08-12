from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('environment', '0019_businesslayer_style_and_audit'),
    ]

    operations = [
        migrations.AddField(
            model_name='climateanalysisresult',
            name='processing_task',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='climate_results', to='environment.processingtask', verbose_name='处理任务'),
        ),
    ]
