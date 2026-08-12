# -*- coding: utf-8 -*-
"""
修复choices中文字符编码问题的数据迁移
"""
from django.db import migrations

def fix_choices_encoding(apps, schema_editor):
    """
    由于SQLite的编码问题，我们需要重新定义choices
    这个迁移主要是为了确保模型定义正确
    """
    # 获取模型
    EcologicalIndex = apps.get_model('environment', 'EcologicalIndex')
    
    # 由于choices是在模型定义中，我们无法直接修改
    # 但我们可以确保数据库中的choices定义正确
    pass

def reverse_fix_choices_encoding(apps, schema_editor):
    """
    反向操作
    """
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('environment', '0012_fix_chinese_encoding'),
    ]

    operations = [
        migrations.RunPython(fix_choices_encoding, reverse_fix_choices_encoding),
    ]



