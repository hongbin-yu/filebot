#!/usr/bin/env python3
import sqlite3
import sys

def main():
    db_path = "filebot.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 测试：查询en文件夹的文档数量
    en_folder_id = '2db73b44-660a-42ed-bc63-c97751dae48b'
    
    # 1. 直接文档数量
    cursor.execute("SELECT COUNT(*) FROM documents WHERE folder_id = ?", (en_folder_id,))
    direct_count = cursor.fetchone()[0]
    print(f"文件夹 en (ID: {en_folder_id[:8]}...) 的直接文档数量: {direct_count}")
    
    # 2. 获取文件夹信息
    cursor.execute("SELECT name, path, description FROM folders WHERE id = ?", (en_folder_id,))
    folder_info = cursor.fetchone()
    if folder_info:
        name, path, description = folder_info
        print(f"文件夹名称: {name}")
        print(f"文件夹路径: {path}")
        if description:
            print(f"文件夹描述: {description}")
    
    # 3. 获取该文件夹的子文件夹数量（根据用户截图显示有13个子文件夹）
    cursor.execute("SELECT COUNT(*) FROM folders WHERE parent_folder_id = ?", (en_folder_id,))
    subfolder_count = cursor.fetchone()[0]
    print(f"子文件夹数量: {subfolder_count}")
    
    # 4. 获取子文件夹的文档数量
    cursor.execute("SELECT id, name FROM folders WHERE parent_folder_id = ?", (en_folder_id,))
    subfolders = cursor.fetchall()
    
    total_docs_in_subfolders = 0
    print(f"\n子文件夹详细信息:")
    for sub_id, sub_name in subfolders:
        cursor.execute("SELECT COUNT(*) FROM documents WHERE folder_id = ?", (sub_id,))
        sub_doc_count = cursor.fetchone()[0]
        total_docs_in_subfolders += sub_doc_count
        print(f"  子文件夹: {sub_name} - 文档数量: {sub_doc_count}")
    
    print(f"\n汇总:")
    print(f"  直接文档数量: {direct_count}")
    print(f"  子文件夹文档总数: {total_docs_in_subfolders}")
    print(f"  总文档数量（直接+子文件夹）: {direct_count + total_docs_in_subfolders}")
    
    # 5. 检查数据库中所有文档的总数
    cursor.execute("SELECT COUNT(*) FROM documents")
    total_docs = cursor.fetchone()[0]
    print(f"\n数据库中的文档总数: {total_docs}")
    
    # 6. 测试我们修改的API逻辑：计算每个文件夹的文档数量
    print(f"\n测试文档计数逻辑（模拟API）:")
    
    # 获取所有文件夹及其文档数量
    cursor.execute("""
        SELECT 
            f.id, 
            f.name,
            COALESCE(doc_counts.count, 0) as document_count
        FROM folders f
        LEFT JOIN (
            SELECT folder_id, COUNT(*) as count
            FROM documents
            GROUP BY folder_id
        ) doc_counts ON f.id = doc_counts.folder_id
        WHERE f.app_id = (
            SELECT app_id FROM folders WHERE id = ?
        )
        ORDER BY f.name
        LIMIT 10
    """, (en_folder_id,))
    
    print("应用中的前10个文件夹及其文档数量:")
    for folder_id, folder_name, doc_count in cursor.fetchall():
        print(f"  {folder_name}: {doc_count} 文档")
    
    conn.close()

if __name__ == "__main__":
    main()