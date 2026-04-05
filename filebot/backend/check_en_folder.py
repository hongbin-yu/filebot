#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('filebot.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 获取canada-site应用
cursor.execute("SELECT id FROM apps WHERE slug = 'canada-site'")
app = cursor.fetchone()
if not app:
    print("找不到canada-site应用")
    exit(1)

app_id = app['id']
print(f"canada-site应用ID: {app_id}")

# 找到所有en文件夹
cursor.execute("SELECT id, name, path, parent_folder_id FROM folders WHERE app_id = ? AND name = 'en' ORDER BY created_at DESC", (app_id,))
en_folders = cursor.fetchall()

print(f"找到 {len(en_folders)} 个en文件夹:\n")

for i, folder in enumerate(en_folders):
    folder_id = folder['id']
    
    # 直接文档数量
    cursor.execute("SELECT COUNT(*) as count FROM documents WHERE folder_id = ?", (folder_id,))
    direct_count = cursor.fetchone()['count']
    
    # 子文件夹文档总数
    cursor.execute("""
        SELECT SUM(doc_count) as total
        FROM (
            SELECT COUNT(d.id) as doc_count
            FROM folders f
            LEFT JOIN documents d ON f.id = d.folder_id
            WHERE f.parent_folder_id = ?
            GROUP BY f.id
        )
    """, (folder_id,))
    
    sub_result = cursor.fetchone()
    sub_count = sub_result['total'] if sub_result['total'] else 0
    
    # 获取父文件夹信息
    parent_name = "根目录"
    if folder['parent_folder_id']:
        cursor.execute("SELECT name FROM folders WHERE id = ?", (folder['parent_folder_id'],))
        parent = cursor.fetchone()
        if parent:
            parent_name = parent['name']
    
    print(f"{i+1}. en文件夹: {folder_id[:8]}...")
    print(f"   路径: {folder['path']}")
    print(f"   父文件夹: {parent_name}")
    print(f"   直接文档: {direct_count}")
    print(f"   子文件夹文档: {sub_count}")
    print(f"   总计文档: {direct_count + sub_count}")
    print()

# 检查哪个en文件夹有最多文档
if en_folders:
    print("文档最多的en文件夹:")
    max_folder = None
    max_total = 0
    
    for folder in en_folders:
        folder_id = folder['id']
        
        # 直接文档数量
        cursor.execute("SELECT COUNT(*) as count FROM documents WHERE folder_id = ?", (folder_id,))
        direct_count = cursor.fetchone()['count']
        
        # 子文件夹文档总数
        cursor.execute("""
            SELECT SUM(doc_count) as total
            FROM (
                SELECT COUNT(d.id) as doc_count
                FROM folders f
                LEFT JOIN documents d ON f.id = d.folder_id
                WHERE f.parent_folder_id = ?
                GROUP BY f.id
            )
        """, (folder_id,))
        
        sub_result = cursor.fetchone()
        sub_count = sub_result['total'] if sub_result['total'] else 0
        
        total = direct_count + sub_count
        if total > max_total:
            max_total = total
            max_folder = (folder_id, direct_count, sub_count, folder['path'])
    
    if max_folder:
        folder_id, direct, sub, path = max_folder
        print(f"  文件夹ID: {folder_id[:8]}...")
        print(f"  路径: {path}")
        print(f"  直接文档: {direct}")
        print(f"  子文件夹文档: {sub}")
        print(f"  总计: {max_total}")

conn.close()