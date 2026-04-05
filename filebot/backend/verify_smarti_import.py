#!/usr/bin/env python3
"""
验证Smarti数据导入完整性的脚本
检查FileBot数据库中导入的Smarti数据是否正确
"""

import json
import sqlite3
from pathlib import Path
import sys

# 数据库路径
DB_PATH = "filebot.db"
MAPPING_FILE = "smarti_import_mapping.json"

def load_mapping():
    """加载映射文件"""
    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_db_connection():
    """获取数据库连接"""
    return sqlite3.connect(DB_PATH)

def verify_apps(conn, mapping):
    """验证应用导入"""
    print("🔍 验证应用导入...")
    
    # 从映射文件中获取导入的应用ID
    imported_app_ids = list(mapping['mappings']['app'].values())
    
    # 查询数据库中的应用
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, slug, description FROM apps WHERE id IN ({})".format(
        ','.join(['?'] * len(imported_app_ids))
    ), imported_app_ids)
    
    db_apps = cursor.fetchall()
    
    print(f"  映射文件中应用数量: {len(imported_app_ids)}")
    print(f"  数据库中查到的应用数量: {len(db_apps)}")
    
    if len(imported_app_ids) == len(db_apps):
        print("  ✅ 应用导入验证通过")
        
        # 显示应用详情
        print("\n  导入的应用详情:")
        for app_id, name, slug, description in db_apps:
            print(f"    - {name} (slug: {slug})")
            if description:
                print(f"      描述: {description[:100]}{'...' if len(description) > 100 else ''}")
    else:
        print("  ❌ 应用导入验证失败")
        missing_ids = set(imported_app_ids) - {row[0] for row in db_apps}
        if missing_ids:
            print(f"    缺失的应用ID: {missing_ids}")
    
    return len(db_apps)

def verify_folders(conn, mapping):
    """验证文件夹导入"""
    print("\n🔍 验证文件夹导入...")
    
    # 从映射文件中获取导入的文件夹ID
    imported_folder_ids = list(mapping['mappings']['fold'].values())
    
    # 查询数据库中的文件夹
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, path, parent_folder_id FROM folders WHERE id IN ({})".format(
        ','.join(['?'] * len(imported_folder_ids))
    ), imported_folder_ids)
    
    db_folders = cursor.fetchall()
    
    print(f"  映射文件中文件夹数量: {len(imported_folder_ids)}")
    print(f"  数据库中查到的文件夹数量: {len(db_folders)}")
    
    # 统计有父文件夹的文件夹数量
    folders_with_parent = sum(1 for _, _, _, parent_id in db_folders if parent_id)
    print(f"  其中有父文件夹的: {folders_with_parent}个")
    
    if len(imported_folder_ids) == len(db_folders):
        print("  ✅ 文件夹导入验证通过")
        
        # 显示文件夹示例
        print("\n  文件夹示例（前10个）:")
        for folder_id, name, path, parent_id in db_folders[:10]:
            parent_info = f" (父文件夹ID: {parent_id})" if parent_id else ""
            print(f"    - {name}: {path}{parent_info}")
    else:
        print("  ❌ 文件夹导入验证失败")
        missing_count = len(imported_folder_ids) - len(db_folders)
        print(f"    缺失的文件夹数量: {missing_count}")
    
    return len(db_folders)

def verify_documents(conn, mapping):
    """验证文档导入"""
    print("\n🔍 验证文档导入...")
    
    # 从映射文件中获取导入的文档ID
    imported_doc_ids = list(mapping['mappings']['doc'].values())
    
    # 查询数据库中的文档
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, original_filename, file_type, file_size, folder_id, document_metadata
        FROM documents WHERE id IN ({})
    """.format(','.join(['?'] * len(imported_doc_ids))), imported_doc_ids)
    
    db_docs = cursor.fetchall()
    
    print(f"  映射文件中文档数量: {len(imported_doc_ids)}")
    print(f"  数据库中查到的文档数量: {len(db_docs)}")
    
    # 统计文档类型
    type_count = {}
    for _, _, _, file_type, _, _, _ in db_docs:
        type_count[file_type] = type_count.get(file_type, 0) + 1
    
    print(f"  文档类型分布: {type_count}")
    
    # 检查是否有metadata
    docs_with_metadata = sum(1 for _, _, _, _, _, _, metadata in db_docs if metadata and metadata != '{}')
    print(f"  包含元数据的文档: {docs_with_metadata}个")
    
    if len(imported_doc_ids) == len(db_docs):
        print("  ✅ 文档导入验证通过")
        
        # 显示文档示例
        print("\n  文档示例（前5个）:")
        for doc_id, title, file_name, file_type, file_size, folder_id, _ in db_docs[:5]:
            size_str = f"{file_size/1024:.1f}KB" if file_size else "未知大小"
            print(f"    - {title} ({file_name}) - {file_type} - {size_str}")
    else:
        print("  ❌ 文档导入验证失败")
        missing_count = len(imported_doc_ids) - len(db_docs)
        print(f"    缺失的文档数量: {missing_count}")
    
    return len(db_docs)

def verify_folder_document_counts(conn, mapping):
    """验证文件夹-文档关系"""
    print("\n🔍 验证文件夹-文档关系...")
    
    # 查询所有导入的文件夹及其文档数量
    imported_folder_ids = list(mapping['mappings']['fold'].values())
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.id, f.name, f.path, COUNT(d.id) as doc_count
        FROM folders f
        LEFT JOIN documents d ON f.id = d.folder_id
        WHERE f.id IN ({})
        GROUP BY f.id
        ORDER BY doc_count DESC
    """.format(','.join(['?'] * len(imported_folder_ids))), imported_folder_ids)
    
    folder_stats = cursor.fetchall()
    
    # 统计
    folders_with_docs = sum(1 for _, _, _, count in folder_stats if count > 0)
    total_docs_in_folders = sum(count for _, _, _, count in folder_stats)
    
    print(f"  有文档的文件夹数量: {folders_with_docs}/{len(folder_stats)}")
    print(f"  文件夹中文档总数: {total_docs_in_folders}")
    
    # 显示文档最多的文件夹
    print("\n  文档最多的文件夹（前5个）:")
    for folder_id, name, path, count in folder_stats[:5]:
        print(f"    - {name}: {count}个文档")
    
    return folders_with_docs

def verify_app_folders(conn, mapping):
    """验证应用-文件夹关系"""
    print("\n🔍 验证应用-文件夹关系...")
    
    # 查询应用和其下的文件夹
    imported_app_ids = list(mapping['mappings']['app'].values())
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.name, COUNT(f.id) as folder_count
        FROM apps a
        LEFT JOIN folders f ON a.id = f.app_id
        WHERE a.id IN ({})
        GROUP BY a.id
        ORDER BY folder_count DESC
    """.format(','.join(['?'] * len(imported_app_ids))), imported_app_ids)
    
    app_stats = cursor.fetchall()
    
    print("  应用及其文件夹数量:")
    for app_id, app_name, folder_count in app_stats:
        print(f"    - {app_name}: {folder_count}个文件夹")
    
    total_folders = sum(count for _, _, count in app_stats)
    print(f"  应用下文件夹总数: {total_folders}")
    
    return app_stats

def main():
    print("=" * 60)
    print("Smarti数据导入完整性验证")
    print("=" * 60)
    
    # 检查文件是否存在
    if not Path(DB_PATH).exists():
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        sys.exit(1)
    
    if not Path(MAPPING_FILE).exists():
        print(f"❌ 映射文件不存在: {MAPPING_FILE}")
        sys.exit(1)
    
    # 加载映射数据
    try:
        mapping = load_mapping()
        print(f"📊 映射文件统计:")
        print(f"  应用: {len(mapping['mappings']['app'])}个")
        print(f"  文件夹: {len(mapping['mappings']['fold'])}个")
        print(f"  文档: {len(mapping['mappings']['doc'])}个")
        print(f"  导入时间: {mapping.get('import_time', '未知')}")
    except Exception as e:
        print(f"❌ 加载映射文件失败: {e}")
        sys.exit(1)
    
    # 连接数据库
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
    except Exception as e:
        print(f"❌ 连接数据库失败: {e}")
        sys.exit(1)
    
    try:
        # 执行各项验证
        app_count = verify_apps(conn, mapping)
        folder_count = verify_folders(conn, mapping)
        doc_count = verify_documents(conn, mapping)
        folders_with_docs = verify_folder_document_counts(conn, mapping)
        app_stats = verify_app_folders(conn, mapping)
        
        print("\n" + "=" * 60)
        print("验证结果摘要")
        print("=" * 60)
        
        # 比较映射文件和实际数据库
        mapping_apps = len(mapping['mappings']['app'])
        mapping_folders = len(mapping['mappings']['fold'])
        mapping_docs = len(mapping['mappings']['doc'])
        
        print(f"📊 数量对比:")
        print(f"  应用: {app_count}/{mapping_apps} {'✅' if app_count == mapping_apps else '❌'}")
        print(f"  文件夹: {folder_count}/{mapping_folders} {'✅' if folder_count == mapping_folders else '❌'}")
        print(f"  文档: {doc_count}/{mapping_docs} {'✅' if doc_count == mapping_docs else '❌'}")
        
        # 检查导入的文档是否在正确的文件夹中
        print(f"\n📁 文件夹-文档关系:")
        print(f"  有文档的文件夹: {folders_with_docs}/{folder_count}")
        
        # 应用-文件夹关系
        print(f"\n📱 应用-文件夹分布:")
        for app_id, app_name, folder_count in app_stats:
            print(f"  {app_name}: {folder_count}个文件夹")
        
        # 总体评估
        all_good = (app_count == mapping_apps and 
                   folder_count == mapping_folders and 
                   doc_count == mapping_docs)
        
        if all_good:
            print("\n🎉 所有数据导入验证通过！")
            print(f"   成功导入 {app_count}个应用、{folder_count}个文件夹、{doc_count}个文档")
        else:
            print("\n⚠️  数据导入存在差异，请检查导入日志")
            
    finally:
        conn.close()

if __name__ == "__main__":
    main()