#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/hongb/.openclaw/workspace/filebot/backend')

from app.db.database import init_db, engine
from sqlalchemy import inspect

print("初始化数据库...")
init_db()

print("检查表结构...")
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"表: {tables}")

# 检查file_naming_rules表的列
if 'file_naming_rules' in tables:
    columns = inspector.get_columns('file_naming_rules')
    print("\nfile_naming_rules表列:")
    for col in columns:
        print(f"  - {col['name']}: {col['type']}")
        
# 检查documents表的列
if 'documents' in tables:
    columns = inspector.get_columns('documents')
    print("\ndocuments表列:")
    for col in columns:
        print(f"  - {col['name']}: {col['type']}")
        
# 检查devices表的列
if 'devices' in tables:
    columns = inspector.get_columns('devices')
    print("\ndevices表列:")
    for col in columns:
        print(f"  - {col['name']}: {col['type']}")