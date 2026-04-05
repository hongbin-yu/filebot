#!/usr/bin/env python3
"""初始化数据库脚本"""
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import init_db, drop_db, engine
from app.models.app import App
from app.models.folder import Folder
from app.models.document import Document
from app.models.user import User

def main():
    print("初始化数据库...")
    
    # 可选：删除现有表
    # print("删除现有表...")
    # drop_db()
    
    print("创建表...")
    init_db()
    print("数据库表创建完成")
    
    # 检查创建的表
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\n创建的表 ({len(tables)} 个):")
    for table in tables:
        print(f"  - {table}")
        columns = inspector.get_columns(table)
        print(f"    列: {[col['name'] for col in columns]}")
    
    print("\n数据库初始化完成")

if __name__ == "__main__":
    main()