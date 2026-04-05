#!/usr/bin/env python3
"""
检查数据库表和内容
"""

import sys
sys.path.insert(0, '/home/hongb/.openclaw/workspace/filebot/backend')

from app.db.database import engine, Base, init_db
from sqlalchemy import inspect

def check_tables():
    """检查数据库表"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print(f"数据库中的表 ({len(tables)}):")
    for table in tables:
        print(f"  - {table}")
        
        # 显示列信息
        columns = inspector.get_columns(table)
        print(f"    列 ({len(columns)}):")
        for col in columns:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            default = f" DEFAULT {col['default']}" if col['default'] else ""
            print(f"      {col['name']} {col['type']} {nullable}{default}")
    
    # 检查是否需要初始化
    if not tables:
        print("\n数据库为空，正在初始化...")
        init_db()
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"初始化后的表 ({len(tables)}): {tables}")

if __name__ == "__main__":
    check_tables()