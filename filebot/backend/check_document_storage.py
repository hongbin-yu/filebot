#!/usr/bin/env python3
import sqlite3
import json

conn = sqlite3.connect('filebot.db')
cursor = conn.cursor()

# 查看Smarti导入的文档存储信息
cursor.execute("""
    SELECT id, title, original_filename, stored_filename, full_storage_path, 
           file_type, file_size, folder_id
    FROM documents 
    WHERE original_filename LIKE '%.CLD' OR original_filename LIKE '%.cld' 
       OR original_filename LIKE '%.tif' OR original_filename LIKE '%.TIF'
    LIMIT 10
""")

docs = cursor.fetchall()
print("📄 文档存储信息（前10个）:")
for doc in docs:
    doc_id, title, original_filename, stored_filename, full_storage_path, file_type, file_size, folder_id = doc
    print(f"\n  {title} ({original_filename})")
    print(f"    存储文件: {stored_filename}")
    print(f"    完整路径: {full_storage_path}")
    print(f"    类型: {file_type}, 大小: {file_size}")
    print(f"    文件夹ID: {folder_id}")

# 统计存储字段的填充情况
cursor.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN stored_filename IS NOT NULL AND stored_filename != '' THEN 1 ELSE 0 END) as has_stored,
        SUM(CASE WHEN full_storage_path IS NOT NULL AND full_storage_path != '' THEN 1 ELSE 0 END) as has_full_path,
        SUM(CASE WHEN file_size IS NOT NULL AND file_size > 0 THEN 1 ELSE 0 END) as has_size
    FROM documents
    WHERE original_filename LIKE '%.CLD' OR original_filename LIKE '%.cld' 
       OR original_filename LIKE '%.tif' OR original_filename LIKE '%.TIF'
""")

stats = cursor.fetchone()
print(f"\n📊 存储字段统计:")
print(f"  总文档数: {stats[0]}")
print(f"  有stored_filename的: {stats[1]}")
print(f"  有full_storage_path的: {stats[2]}")
print(f"  有文件大小的: {stats[3]}")

# 检查实际文件是否存在
import os
print(f"\n🔍 检查文件系统中是否存在:")
cursor.execute("SELECT stored_filename, full_storage_path FROM documents WHERE stored_filename IS NOT NULL LIMIT 5")
files = cursor.fetchall()
for stored, full_path in files:
    if stored and os.path.exists(stored):
        print(f"  ✅ {stored} 存在")
    elif full_path and os.path.exists(full_path):
        print(f"  ✅ {full_path} 存在")
    else:
        print(f"  ❌ 文件不存在: {stored or full_path}")

conn.close()