# -*- coding: utf-8 -*-
"""
修复中文字符编码问题的迁移
"""
from django.db import migrations

def fix_chinese_encoding(apps, schema_editor):
    """
    修复数据库中的中文字符编码问题
    由于SQLite的编码限制，我们需要重新创建choices
    """
    # 这个迁移主要是为了确保choices定义正确
    # 实际的修复需要在Django设置中处理
    pass

def reverse_fix_chinese_encoding(apps, schema_editor):
    """
    反向操作
    """
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('environment', '0011_ecologicalindexfile_ecologicalprojectfile_and_more'),
    ]

    operations = [
        migrations.RunPython(fix_chinese_encoding, reverse_fix_chinese_encoding),
    ]



