#!/usr/bin/env python3
"""
检查当前FileBot数据库中的Smarti数据
"""

import sqlite3
import json
from pathlib import Path

# 数据库路径
DB_PATH = Path("filebot.db")

def check_smarti_data():
    """检查Smarti相关数据"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("📊 检查当前FileBot数据库中的Smarti数据")
    print("=" * 50)
    
    # 1. 检查应用
    print("\n🔍 1. 检查Smarti应用:")
    cursor.execute("""
        SELECT id, name, slug, description, created_at 
        FROM apps 
        WHERE slug LIKE '%smarti%' OR name LIKE '%Smarti%'
        ORDER BY created_at
    """)
    smarti_apps = cursor.fetchall()
    
    print(f"   找到 {len(smarti_apps)} 个Smarti相关应用:")
    for app in smarti_apps:
        app_id, name, slug, description, created_at = app
        print(f"   - {name} ({slug})")
        print(f"     ID: {app_id}, 创建时间: {created_at}")
        
        # 统计该应用的文件夹
        cursor.execute("""
            SELECT COUNT(*) FROM folders WHERE app_id = ?
        """, (app_id,))
        folder_count = cursor.fetchone()[0]
        print(f"     文件夹数: {folder_count}")
        
        # 统计该应用的文档
        cursor.execute("""
            SELECT COUNT(*) FROM documents 
            WHERE folder_id IN (SELECT id FROM folders WHERE app_id = ?)
        """, (app_id,))
        doc_count = cursor.fetchone()[0]
        print(f"     文档数: {doc_count}")
    
    # 2. 检查映射表
    print("\n🔍 2. 检查Smarti导入映射表:")
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name LIKE '%smarti%'
    """)
    smarti_tables = cursor.fetchall()
    
    if smarti_tables:
        print(f"   找到 {len(smarti_tables)} 个Smarti相关表:")
        for table in smarti_tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   - {table_name}: {count} 行")
    else:
        print("   未找到Smarti映射表")
    
    # 3. 检查数据库结构
    print("\n🔍 3. 检查数据库表结构:")
    cursor.execute("PRAGMA table_info(apps)")
    app_columns = cursor.fetchall()
    print("   apps表字段:")
    for col in app_columns:
        print(f"     - {col[1]} ({col[2]})")
    
    # 4. 检查文档总数
    print("\n🔍 4. 检查文档统计:")
    cursor.execute("SELECT COUNT(*) FROM documents")
    total_docs = cursor.fetchone()[0]
    print(f"   总文档数: {total_docs}")
    
    # 检查是否有file_status字段
    cursor.execute("PRAGMA table_info(documents)")
    doc_columns = [col[1] for col in cursor.fetchall()]
    
    if 'file_status' in doc_columns:
        cursor.execute("""
            SELECT file_status, COUNT(*) as count
            FROM documents
            WHERE file_status IS NOT NULL
            GROUP BY file_status
            ORDER BY count DESC
        """)
        file_status_stats = cursor.fetchall()
        
        print("   文档文件状态统计:")
        for status, count in file_status_stats:
            print(f"   - {status}: {count} 个文档")
    else:
        print("   documents表没有file_status字段")
    
    conn.close()
    
    # 5. 生成清理建议
    print("\n💡 清理建议:")
    if smarti_apps:
        app_ids = [app[0] for app in smarti_apps]
        print(f"   找到 {len(smarti_apps)} 个Smarti应用，ID: {app_ids}")
        print("   清理步骤:")
        print("   1. 备份当前映射文件: cp smarti_import_mapping.json smarti_import_mapping.json.backup")
        print("   2. 删除映射表数据（如果存在）")
        print("   3. 删除Smarti相关应用（会级联删除文件夹和文档）")
        print("   4. 重新运行导入脚本: python3 import_smarti.py")
    else:
        print("   未找到Smarti相关数据，可以直接运行导入脚本")

if __name__ == "__main__":
    check_smarti_data()