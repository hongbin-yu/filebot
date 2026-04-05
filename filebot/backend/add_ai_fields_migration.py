#!/usr/bin/env python3
"""
添加AI字段到数据库的迁移脚本
运行此脚本将添加新的AI相关字段到现有表中
"""

import sqlite3
import os
import sys

def get_db_path():
    """获取数据库路径"""
    # 数据库文件在当前目录下
    db_path = os.path.join(os.path.dirname(__file__), "filebot.db")
    if not os.path.exists(db_path):
        print(f"错误: 数据库文件不存在: {db_path}")
        sys.exit(1)
    return db_path

def check_table_exists(cursor, table_name):
    """检查表是否存在"""
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    return cursor.fetchone() is not None

def check_column_exists(cursor, table_name, column_name):
    """检查列是否存在"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    return column_name in columns

def migrate_documents_table(conn):
    """迁移documents表，添加AI字段"""
    cursor = conn.cursor()
    
    if not check_table_exists(cursor, "documents"):
        print("documents表不存在，跳过迁移")
        return
    
    print("检查documents表的AI字段...")
    
    # 需要添加的AI字段
    ai_columns = [
        ("ai_category", "VARCHAR(100)"),
        ("ai_confidence", "FLOAT"),
        ("ai_tags", "TEXT"),  # 存储为JSON文本
        ("ai_summary", "TEXT"),
        ("vector_embedding", "TEXT"),  # 存储为JSON文本
        ("is_indexed", "BOOLEAN DEFAULT 0"),
        ("classification_status", "VARCHAR(50)")
    ]
    
    added_count = 0
    for column_name, column_type in ai_columns:
        if not check_column_exists(cursor, "documents", column_name):
            print(f"  添加字段: {column_name} ({column_type})")
            try:
                cursor.execute(f"ALTER TABLE documents ADD COLUMN {column_name} {column_type}")
                added_count += 1
            except Exception as e:
                print(f"  错误添加字段 {column_name}: {e}")
        else:
            print(f"  字段已存在: {column_name}")
    
    conn.commit()
    print(f"documents表迁移完成，添加了 {added_count} 个字段")

def migrate_folders_table(conn):
    """迁移folders表，添加系统文件夹标志"""
    cursor = conn.cursor()
    
    if not check_table_exists(cursor, "folders"):
        print("folders表不存在，跳过迁移")
        return
    
    print("检查folders表的系统字段...")
    
    # 需要添加的字段
    system_columns = [
        ("is_system_folder", "BOOLEAN DEFAULT 0"),
        ("order_index", "INTEGER DEFAULT 0")
    ]
    
    added_count = 0
    for column_name, column_type in system_columns:
        if not check_column_exists(cursor, "folders", column_name):
            print(f"  添加字段: {column_name} ({column_type})")
            try:
                cursor.execute(f"ALTER TABLE folders ADD COLUMN {column_name} {column_type}")
                added_count += 1
            except Exception as e:
                print(f"  错误添加字段 {column_name}: {e}")
        else:
            print(f"  字段已存在: {column_name}")
    
    conn.commit()
    print(f"folders表迁移完成，添加了 {added_count} 个字段")

def backup_database(db_path):
    """创建数据库备份"""
    backup_path = db_path + ".backup"
    import shutil
    shutil.copy2(db_path, backup_path)
    print(f"数据库已备份到: {backup_path}")
    return backup_path

def main():
    """主迁移函数"""
    print("=" * 60)
    print("FileBot AI字段迁移脚本")
    print("=" * 60)
    
    # 获取数据库路径
    db_path = get_db_path()
    print(f"数据库文件: {db_path}")
    
    # 创建备份
    backup_path = backup_database(db_path)
    
    # 连接到数据库
    conn = sqlite3.connect(db_path)
    
    try:
        # 启用外键约束
        conn.execute("PRAGMA foreign_keys = ON")
        
        # 迁移documents表
        migrate_documents_table(conn)
        
        # 迁移folders表
        migrate_folders_table(conn)
        
        # 验证迁移
        print("\n验证迁移结果...")
        cursor = conn.cursor()
        
        # 检查documents表结构
        cursor.execute("PRAGMA table_info(documents)")
        columns = cursor.fetchall()
        ai_column_names = ["ai_category", "ai_confidence", "ai_tags", "ai_summary", 
                          "vector_embedding", "is_indexed", "classification_status"]
        
        existing_ai_columns = []
        for col in columns:
            if col[1] in ai_column_names:
                existing_ai_columns.append(col[1])
        
        print(f"documents表现有AI字段: {len(existing_ai_columns)}/{len(ai_column_names)}")
        if existing_ai_columns:
            print(f"  字段列表: {', '.join(existing_ai_columns)}")
        
        # 检查folders表结构
        cursor.execute("PRAGMA table_info(folders)")
        columns = cursor.fetchall()
        system_column_names = ["is_system_folder", "order_index"]
        
        existing_system_columns = []
        for col in columns:
            if col[1] in system_column_names:
                existing_system_columns.append(col[1])
        
        print(f"folders表现有系统字段: {len(existing_system_columns)}/{len(system_column_names)}")
        if existing_system_columns:
            print(f"  字段列表: {', '.join(existing_system_columns)}")
        
        print("\n" + "=" * 60)
        print("迁移完成!")
        print("=" * 60)
        print(f"备份文件: {backup_path}")
        print("\n注意:")
        print("1. 如果迁移过程中出现错误，可以使用备份文件恢复")
        print("2. 重启FileBot后端服务以应用更改")
        print("3. 测试AI分类功能前，请确保Ollama服务正在运行")
        
    except Exception as e:
        print(f"迁移失败: {e}")
        print(f"可以从备份恢复: {backup_path}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()