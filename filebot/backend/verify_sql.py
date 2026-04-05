#!/usr/bin/env python3
import sqlite3
import json

def main():
    conn = sqlite3.connect('filebot.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("验证数据库中的文档分布...")
    
    # 1. 总文档数
    cursor.execute("SELECT COUNT(*) as total FROM documents")
    total_docs = cursor.fetchone()['total']
    print(f"数据库中的总文档数: {total_docs}")
    
    # 2. 按文件夹分组的文档数
    cursor.execute("""
        SELECT 
            f.id as folder_id,
            f.name as folder_name,
            f.path as folder_path,
            COUNT(d.id) as doc_count
        FROM folders f
        LEFT JOIN documents d ON f.id = d.folder_id
        GROUP BY f.id
        HAVING doc_count > 0
        ORDER BY doc_count DESC
        LIMIT 20
    """)
    
    folders_with_docs = cursor.fetchall()
    print(f"\n包含文档的文件夹 (前20个):")
    print(f"{'文件夹名称':<30} {'文档数':<8} {'文件夹ID':<40}")
    print("-" * 80)
    
    for row in folders_with_docs:
        folder_name = row['folder_name']
        if len(folder_name) > 28:
            folder_name = folder_name[:25] + "..."
        
        folder_id_short = row['folder_id'][:8] + "..."
        print(f"{folder_name:<30} {row['doc_count']:<8} {folder_id_short:<40}")
    
    # 3. 检查特定的en文件夹
    en_folder_id = '2db73b44-660a-42ed-bc63-c97751dae48b'
    print(f"\n检查特定的en文件夹 (ID: {en_folder_id[:8]}...):")
    
    # 直接文档
    cursor.execute("SELECT COUNT(*) as count FROM documents WHERE folder_id = ?", (en_folder_id,))
    direct_count = cursor.fetchone()['count']
    print(f"  直接文档数量: {direct_count}")
    
    # 文件夹信息
    cursor.execute("SELECT name, path FROM folders WHERE id = ?", (en_folder_id,))
    folder_info = cursor.fetchone()
    if folder_info:
        print(f"  文件夹名称: {folder_info['name']}")
        print(f"  文件夹路径: {folder_info['path']}")
    
    # 子文件夹文档总数
    cursor.execute("""
        SELECT SUM(doc_count) as total_sub_docs
        FROM (
            SELECT COUNT(d.id) as doc_count
            FROM folders f
            LEFT JOIN documents d ON f.id = d.folder_id
            WHERE f.parent_folder_id = ?
            GROUP BY f.id
        )
    """, (en_folder_id,))
    
    sub_docs_result = cursor.fetchone()
    sub_docs_total = sub_docs_result['total_sub_docs'] if sub_docs_result['total_sub_docs'] else 0
    print(f"  子文件夹文档总数: {sub_docs_total}")
    print(f"  总文档数 (直接+子文件夹): {direct_count + sub_docs_total}")
    
    # 4. 验证SQL查询与后端API查询的一致性
    print(f"\n验证API查询逻辑:")
    
    # 模拟后端API的查询
    cursor.execute("""
        SELECT 
            f.id,
            f.name,
            f.path,
            f.description,
            f.app_id,
            f.parent_folder_id,
            f.created_by,
            f.created_at,
            f.updated_at,
            f.updated_by,
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
        AND f.name = 'en'
    """, (en_folder_id,))
    
    api_simulated_result = cursor.fetchone()
    if api_simulated_result:
        print(f"  API模拟查询结果:")
        print(f"    文件夹: {api_simulated_result['name']}")
        print(f"    document_count: {api_simulated_result['document_count']}")
        print(f"    与实际直接文档数匹配: {'是' if api_simulated_result['document_count'] == direct_count else '否'}")
    
    # 5. 检查前端显示为0文档的问题
    print(f"\n前端显示为0文档的可能原因分析:")
    print(f"  1. 前端API响应中不包含document_count字段")
    print(f"  2. 后端没有正确计算document_count")
    print(f"  3. 前端没有正确解析document_count字段")
    print(f"  4. 缓存问题（前端使用模拟数据）")
    
    # 检查前端开发模式
    print(f"\n建议检查点:")
    print(f"  1. 确保前端DEV_MODE = false（使用真实API）")
    print(f"  2. 检查浏览器开发者工具中的API响应")
    print(f"  3. 验证后端API是否返回document_count字段")
    
    conn.close()

if __name__ == "__main__":
    main()