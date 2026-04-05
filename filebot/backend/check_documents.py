#!/usr/bin/env python3
import sqlite3
import sys

def main():
    db_path = "filebot.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查文档表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
        if not cursor.fetchone():
            print("文档表不存在")
            return
        
        # 查询文档总数
        cursor.execute("SELECT COUNT(*) FROM documents")
        total_docs = cursor.fetchone()[0]
        print(f"文档总数: {total_docs}")
        
        # 查询按folder_id分组的文档数量
        cursor.execute("""
            SELECT folder_id, COUNT(*) as count 
            FROM documents 
            GROUP BY folder_id 
            ORDER BY count DESC
            LIMIT 20
        """)
        
        print("\n按文件夹分组的文档数量 (前20个):")
        for folder_id, count in cursor.fetchall():
            print(f"  文件夹 {folder_id}: {count} 个文档")
        
        # 查询特定的文件夹ID 3dbee07d-31ad-49ba-b8fa-cd8c104ddab6
        target_folder = "3dbee07d-31ad-49ba-b8fa-cd8c104ddab6"
        cursor.execute("SELECT COUNT(*) FROM documents WHERE folder_id = ?", (target_folder,))
        count_in_target = cursor.fetchone()[0]
        print(f"\n在文件夹 {target_folder} 中的文档数量: {count_in_target}")
        
        # 如果有文档，显示前几个
        if count_in_target > 0:
            cursor.execute("""
                SELECT id, title, folder_id, created_at 
                FROM documents 
                WHERE folder_id = ? 
                LIMIT 5
            """, (target_folder,))
            print("\n该文件夹中的文档示例:")
            for doc_id, title, folder_id, created_at in cursor.fetchall():
                print(f"  ID: {doc_id[:8]}..., 标题: {title[:50]}, 文件夹: {folder_id[:8]}..., 创建时间: {created_at}")
        
        # 检查文件夹表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='folders'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM folders")
            total_folders = cursor.fetchone()[0]
            print(f"\n文件夹总数: {total_folders}")
            
            # 查询根文件夹的子文件夹
            cursor.execute("""
                SELECT id, name, parent_folder_id, path, created_by
                FROM folders 
                WHERE parent_folder_id = ? OR path LIKE ?
                ORDER BY path
                LIMIT 20
            """, (target_folder, f"%{target_folder}%"))
            
            print(f"\n与文件夹 {target_folder} 相关的文件夹:")
            for folder_id, name, parent_id, path, created_by in cursor.fetchall():
                print(f"  ID: {folder_id[:8]}..., 名称: {name}, 父文件夹: {parent_id[:8] if parent_id else 'None'}, 路径: {path}, 创建者: {created_by}")
        
        conn.close()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()