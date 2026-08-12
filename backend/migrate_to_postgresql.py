#!/usr/bin/env python
"""
数据迁移脚本：从 SQLite 迁移到 PostgreSQL

使用方法：
1. 确保 PostgreSQL 已安装并运行
2. 创建 .env 文件并配置数据库连接
3. 运行：python migrate_to_postgresql.py
"""

import os
import sys
import django
import json
import secrets
from pathlib import Path

# 添加项目路径
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

def main():
    print("=" * 60)
    print("天水市生态环境系统 - 数据库迁移工具")
    print("从 SQLite 迁移到 PostgreSQL")
    print("=" * 60)
    print()
    
    # 步骤 1: 导出 SQLite 数据
    print("步骤 1/5: 导出 SQLite 数据...")
    print("-" * 60)
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tianshuipy.settings_dev')
    django.setup()
    
    from django.core.management import call_command
    
    # 导出数据
    fixtures_dir = BASE_DIR / 'fixtures'
    fixtures_dir.mkdir(exist_ok=True)
    
    fixture_file = fixtures_dir / 'data_export.json'
    
    print(f"正在导出数据到: {fixture_file}")
    try:
        call_command('dumpdata', 
                    '--natural-foreign', 
                    '--natural-primary',
                    '--indent', '2',
                    '--output', str(fixture_file),
                    '--exclude', 'contenttypes',
                    '--exclude', 'auth.Permission',
                    '--exclude', 'sessions')
        print("✓ 数据导出成功！")
    except Exception as e:
        print(f"✗ 数据导出失败: {e}")
        return False
    
    print()
    
    # 步骤 2: 切换到 PostgreSQL 配置
    print("步骤 2/5: 切换到 PostgreSQL 配置...")
    print("-" * 60)
    
    # 检查 .env 文件
    env_file = BASE_DIR / '.env'
    if not env_file.exists():
        print("警告: 未找到 .env 文件")
        print("请创建 .env 文件并配置 PostgreSQL 连接信息")
        print("参考 .env.example 文件")
        
        response = input("是否现在创建 .env 文件? (y/n): ")
        if response.lower() == 'y':
            create_env_file()
        else:
            print("请手动创建 .env 文件后重新运行此脚本")
            return False
    
    # 重新加载 Django 配置（使用 PostgreSQL）
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tianshuipy.settings_postgresql'
    
    # 清除已加载的模块
    for key in list(sys.modules.keys()):
        if key.startswith('django'):
            del sys.modules[key]
    
    django.setup()
    print("✓ 已切换到 PostgreSQL 配置")
    print()
    
    # 步骤 3: 测试数据库连接
    print("步骤 3/5: 测试 PostgreSQL 连接...")
    print("-" * 60)
    
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"✓ PostgreSQL 连接成功！")
            print(f"  版本: {version}")
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        print("\n请检查:")
        print("1. PostgreSQL 服务是否正在运行")
        print("2. .env 文件中的数据库配置是否正确")
        print("3. 数据库是否已创建（CREATE DATABASE tianshuipy;）")
        return False
    
    print()
    
    # 步骤 4: 运行数据库迁移
    print("步骤 4/5: 创建数据库表结构...")
    print("-" * 60)
    
    try:
        call_command('migrate', '--noinput')
        print("✓ 数据库表结构创建成功！")
    except Exception as e:
        print(f"✗ 迁移失败: {e}")
        return False
    
    print()
    
    # 步骤 5: 导入数据
    print("步骤 5/5: 导入数据到 PostgreSQL...")
    print("-" * 60)
    
    try:
        call_command('loaddata', str(fixture_file))
        print("✓ 数据导入成功！")
    except Exception as e:
        print(f"✗ 数据导入失败: {e}")
        print("这可能是正常的（如果 SQLite 数据库是空的）")
    
    print()
    print("=" * 60)
    print("✓ 迁移完成！")
    print("=" * 60)
    print()
    print("后续步骤:")
    print("1. 验证数据: python manage.py dbshell")
    print("2. 启动服务: python manage.py runserver --settings=tianshuipy.settings_postgresql")
    print("3. 如果一切正常，可以备份 SQLite 数据库: db.sqlite3")
    print()
    
    return True

def create_env_file():
    """交互式创建 .env 文件"""
    print()
    print("创建 .env 配置文件")
    print("-" * 60)
    
    db_name = input("数据库名称 [tianshuipy]: ").strip() or "tianshuipy"
    db_user = input("数据库用户 [postgres]: ").strip() or "postgres"
    db_password = input("数据库密码: ").strip()
    db_host = input("数据库主机 [localhost]: ").strip() or "localhost"
    db_port = input("数据库端口 [5432]: ").strip() or "5432"
    secret_key = secrets.token_urlsafe(50)
    
    env_content = f"""# PostgreSQL 配置
DB_ENGINE=postgresql
DB_NAME={db_name}
DB_USER={db_user}
DB_PASSWORD={db_password}
DB_HOST={db_host}
DB_PORT={db_port}

# Django 配置
SECRET_KEY={secret_key}
DEBUG=False

# GeoServer 配置
GEOSERVER_URL=http://localhost:8080/geoserver
GEOSERVER_USERNAME=admin
GEOSERVER_PASSWORD=change_me
GEOSERVER_WORKSPACE=tianshuipy
"""
    
    env_file = BASE_DIR / '.env'
    env_file.write_text(env_content, encoding='utf-8')
    print(f"✓ .env 文件已创建: {env_file}")
    print()

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

