#!/usr/bin/env python3
import sqlite3
import json

def check_folders():
    conn = sqlite3.connect('filebot.db')
    cursor = conn.cursor()
    
    # 加载映射
    with open('smarti_import_mapping.json', 'r') as f:
        mapping = json.load(f)
    
    # 获取所有从Smarti导入的文件夹ID
    imported_folder_ids = list(mapping['mappings']['fold'].values())
    
    print(f"📊 导入的文件夹数量: {len(imported_folder_ids)}")
    
    # 查询这些文件夹的详细信息
    cursor.execute(f"""
        SELECT id, name, path, parent_folder_id, app_id
        FROM folders 
        WHERE id IN ({','.join(['?']*len(imported_folder_ids))})
    """, imported_folder_ids)
    
    folders = cursor.fetchall()
    
    print("\n📁 文件夹详情 (前20个):")
    for fid, name, path, parent_id, app_id in folders[:20]:
        parent_info = f"parent: {parent_id}" if parent_id else "root (no parent)"
        print(f"  {name} ({fid})")
        print(f"    路径: {path}, {parent_info}")
    
    # 统计parent_folder_id情况
    with_parent = sum(1 for _, _, _, parent_id, _ in folders if parent_id)
    print(f"\n📈 统计:")
    print(f"  有父文件夹的: {with_parent}/{len(folders)}")
    
    # 检查应用分布
    app_counts = {}
    for _, _, _, _, app_id in folders:
        app_counts[app_id] = app_counts.get(app_id, 0) + 1
    
    print(f"\n📱 应用分布:")
    for app_id, count in app_counts.items():
        # 获取应用名称
        cursor.execute("SELECT name FROM apps WHERE id = ?", (app_id,))
        app_name = cursor.fetchone()
        app_name = app_name[0] if app_name else app_id
        print(f"  {app_name}: {count}个文件夹")
    
    conn.close()

def compare_with_original():
    """比较数据库文件夹与原始FOLD数据"""
    print("\n🔍 与原始FOLD数据对比...")
    
    # 需要解析原始数据，但先简单检查
    # 从映射文件中获取原始ID到新ID的映射
    with open('smarti_import_mapping.json', 'r') as f:
        mapping = json.load(f)
    
    fold_mapping = mapping['mappings']['fold']  # Smarti FOLD_ID -> FileBot folder_id
    
    print(f"  映射记录数: {len(fold_mapping)}")
    
    # 检查是否有重复的文件夹名称
    conn = sqlite3.connect('filebot.db')
    cursor = conn.cursor()
    
    name_counts = {}
    for smarti_id, filebot_id in fold_mapping.items():
        cursor.execute("SELECT name FROM folders WHERE id = ?", (filebot_id,))
        row = cursor.fetchone()
        if row:
            name = row[0]
            name_counts[name] = name_counts.get(name, 0) + 1
    
    # 显示重复的名称
    duplicates = {name: count for name, count in name_counts.items() if count > 1}
    if duplicates:
        print(f"⚠️  发现重复文件夹名称 ({len(duplicates)} 个):")
        for name, count in list(duplicates.items())[:10]:
            print(f"    '{name}': {count}次")
    else:
        print("✅ 没有重复的文件夹名称")
    
    conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("当前文件夹状态检查")
    print("=" * 60)
    check_folders()
    compare_with_original()