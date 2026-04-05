#!/usr/bin/env python3
import sqlite3
import json

def main():
    conn = sqlite3.connect('filebot.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("当前应用列表:")
    cursor.execute("SELECT id, slug, name FROM apps")
    apps = cursor.fetchall()
    for app in apps:
        print(f"  {app['slug']} ({app['name']}): {app['id']}")
    
    print(f"\n爬虫创建的文件夹 (来自canada-site应用):")
    
    # 找到canada-site应用
    cursor.execute("SELECT id FROM apps WHERE slug = 'canada-site' OR name LIKE '%canada%' LIMIT 1")
    app_row = cursor.fetchone()
    if app_row:
        app_id = app_row['id']
        print(f"应用ID: {app_id}")
        
        # 找到en文件夹
        cursor.execute("SELECT id, name, path FROM folders WHERE app_id = ? AND name = 'en'", (app_id,))
        en_folders = cursor.fetchall()
        print(f"找到 {len(en_folders)} 个en文件夹:")
        
        for folder in en_folders:
            folder_id = folder['id']
            # 统计文档数量
            cursor.execute("SELECT COUNT(*) as count FROM documents WHERE folder_id = ?", (folder_id,))
            doc_count = cursor.fetchone()['count']
            
            # 统计子文件夹文档
            cursor.execute("""
                SELECT SUM(sub_docs) as total
                FROM (
                    SELECT COUNT(d.id) as sub_docs
                    FROM folders f
                    LEFT JOIN documents d ON f.id = d.folder_id
                    WHERE f.parent_folder_id = ?
                    GROUP BY f.id
                )
            """, (folder_id,))
            
            sub_docs_result = cursor.fetchone()
            sub_docs = sub_docs_result['total'] if sub_docs_result['total'] else 0
            
            print(f"  - {folder['name']} ({folder_id[:8]}...):")
            print(f"    路径: {folder['path']}")
            print(f"    直接文档: {doc_count}")
            print(f"    子文件夹文档: {sub_docs}")
            print(f"    总计: {doc_count + sub_docs}")
    
    conn.close()

if __name__ == "__main__":
    main()