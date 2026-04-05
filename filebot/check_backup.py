#!/usr/bin/env python3
"""
检查备份数据库内容
"""

import sqlite3

BACKUP_DB = "/home/hongb/.openclaw/workspace/filebot/backups/production_migration_20260321_175924/filebot.db.backup"

def check_backup_tables():
    """检查备份数据库的表"""
    conn = sqlite3.connect(BACKUP_DB)
    cursor = conn.cursor()
    
    # 获取所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("备份数据库表:")
    for table in tables:
        table_name = table[0]
        print(f"  {table_name}")
    
    conn.close()

def check_backup_apps():
    """检查备份数据库中的应用"""
    conn = sqlite3.connect(BACKUP_DB)
    cursor = conn.cursor()
    
    print("\n备份数据库中的应用:")
    try:
        cursor.execute("SELECT id, name, slug FROM apps;")
        apps = cursor.fetchall()
        print(f"找到 {len(apps)} 个应用:")
        for app in apps:
            print(f"  ID: {app[0]}, 名称: {app[1]}, Slug: {app[2]}")
    except Exception as e:
        print(f"查询应用错误: {e}")
    
    conn.close()

def check_backup_documents():
    """检查备份数据库中的文档"""
    conn = sqlite3.connect(BACKUP_DB)
    cursor = conn.cursor()
    
    print("\n备份数据库中的文档:")
    try:
        cursor.execute("SELECT COUNT(*) FROM documents;")
        count = cursor.fetchone()[0]
        print(f"文档总数: {count}")
        
        # 获取一些示例
        cursor.execute("""
            SELECT d.id, d.original_filename, d.file_type, d.file_size,
                   f.name as folder_name
            FROM documents d
            LEFT JOIN folders f ON d.folder_id = f.id
            LIMIT 5;
        """)
        docs = cursor.fetchall()
        
        print("文档示例:")
        for doc in docs:
            print(f"  ID: {doc[0]}, 文件: {doc[1]}, 类型: {doc[2]}, 大小: {doc[3]}, 文件夹: {doc[4]}")
            
    except Exception as e:
        print(f"查询文档错误: {e}")
    
    conn.close()

def compare_databases():
    """比较当前数据库和备份数据库"""
    print("\n\n比较当前数据库和备份数据库:")
    
    # 连接两个数据库
    conn_current = sqlite3.connect("/home/hongb/.openclaw/workspace/filebot/backend/filebot.db")
    conn_backup = sqlite3.connect(BACKUP_DB)
    
    cursor_current = conn_current.cursor()
    cursor_backup = conn_backup.cursor()
    
    # 比较应用数量
    cursor_current.execute("SELECT COUNT(*) FROM apps;")
    current_apps = cursor_current.fetchone()[0]
    
    cursor_backup.execute("SELECT COUNT(*) FROM apps;")
    backup_apps = cursor_backup.fetchone()[0]
    
    print(f"应用数量 - 当前: {current_apps}, 备份: {backup_apps}")
    
    # 比较文档数量
    cursor_current.execute("SELECT COUNT(*) FROM documents;")
    current_docs = cursor_current.fetchone()[0]
    
    cursor_backup.execute("SELECT COUNT(*) FROM documents;")
    backup_docs = cursor_backup.fetchone()[0]
    
    print(f"文档数量 - 当前: {current_docs}, 备份: {backup_docs}")
    
    conn_current.close()
    conn_backup.close()

if __name__ == "__main__":
    print("检查备份数据库...")
    check_backup_tables()
    check_backup_apps()
    check_backup_documents()
    compare_databases()