#!/usr/bin/env python3
"""
检查FileBot数据库内容
"""

import sqlite3
import os

# 数据库路径
DB_PATH = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"

def check_tables():
    """检查数据库中的表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("数据库表列表:")
    for table in tables:
        table_name = table[0]
        print(f"\n表: {table_name}")
        
        # 获取表结构
        try:
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            print("  列: ", end="")
            for col in columns:
                print(f"{col[1]}({col[2]}) ", end="")
            print()
            
            # 获取行数
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"  行数: {count}")
            
            # 如果是apps表，显示内容
            if table_name == "apps":
                cursor.execute(f"SELECT id, name, slug FROM {table_name} LIMIT 10;")
                apps = cursor.fetchall()
                print("  应用示例:")
                for app in apps:
                    print(f"    ID: {app[0]}, 名称: {app[1]}, Slug: {app[2]}")
                    
        except Exception as e:
            print(f"  错误: {e}")
    
    conn.close()

def check_documents():
    """检查文档表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n\n文档表内容:")
    try:
        # 检查documents表
        cursor.execute("""
            SELECT d.id, d.title, d.original_filename, d.file_type, d.file_size,
                   f.name as folder_name, a.name as app_name
            FROM documents d
            LEFT JOIN folders f ON d.folder_id = f.id
            LEFT JOIN apps a ON f.app_id = a.id
            LIMIT 10;
        """)
        docs = cursor.fetchall()
        
        print(f"找到 {len(docs)} 个文档:")
        for doc in docs:
            print(f"  ID: {doc[0]}, 标题: {doc[1]}, 文件: {doc[2]}, 类型: {doc[3]}, 大小: {doc[4]}")
            print(f"    文件夹: {doc[5]}, 应用: {doc[6]}")
            
    except Exception as e:
        print(f"查询文档表错误: {e}")
        # 尝试直接查询
        cursor.execute("SELECT COUNT(*) FROM documents;")
        count = cursor.fetchone()[0]
        print(f"文档总数: {count}")
    
    conn.close()

def check_backup_db():
    """检查备份数据库"""
    backup_path = "/home/hongb/.openclaw/workspace/filebot/backups/production_migration_20260321_175924/filebot.db.backup"
    if os.path.exists(backup_path):
        print(f"\n\n备份数据库存在: {backup_path}")
        try:
            conn = sqlite3.connect(backup_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            print(f"备份数据库包含 {len(tables)} 个表")
            conn.close()
        except Exception as e:
            print(f"无法打开备份数据库: {e}")
    else:
        print("\n\n备份数据库不存在")

if __name__ == "__main__":
    print("检查FileBot数据库...")
    check_tables()
    check_documents()
    check_backup_db()