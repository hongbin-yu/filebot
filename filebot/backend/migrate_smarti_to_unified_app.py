#!/usr/bin/env python3
"""
将5个Smarti源应用的数据迁移到统一的Smarti应用中
创建者: 码博士
创建时间: 2026-04-04
"""

import sqlite3
import json
import os
from datetime import datetime
import shutil

def backup_database(db_path, backup_dir='backups'):
    """备份数据库"""
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'filebot_pre_migration_{timestamp}.db')
    
    print(f"📦 创建数据库备份: {backup_path}")
    shutil.copy2(db_path, backup_path)
    return backup_path

def get_connection(db_path='filebot.db'):
    """获取数据库连接"""
    return sqlite3.connect(db_path)

def print_stats(cursor, title):
    """打印统计数据"""
    print(f"\n📊 {title}")
    print("-" * 50)
    
    # 应用数量
    cursor.execute("SELECT COUNT(*) FROM apps")
    total_apps = cursor.fetchone()[0]
    print(f"总应用数: {total_apps}")
    
    # Smarti相关应用
    cursor.execute("""
        SELECT COUNT(*) FROM apps 
        WHERE slug LIKE '%smarti%' OR name LIKE '%Smarti%'
    """)
    smarti_apps = cursor.fetchone()[0]
    print(f"Smarti相关应用: {smarti_apps}")
    
    # 文件夹总数
    cursor.execute("SELECT COUNT(*) FROM folders")
    total_folders = cursor.fetchone()[0]
    print(f"总文件夹数: {total_folders}")
    
    # 文档总数
    cursor.execute("SELECT COUNT(*) FROM documents")
    total_docs = cursor.fetchone()[0]
    print(f"总文档数: {total_docs}")

def migrate_smarti_data():
    """执行Smarti数据迁移"""
    db_path = 'filebot.db'
    
    # 创建备份
    backup_path = backup_database(db_path)
    
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    print("🚀 开始Smarti数据迁移")
    print("=" * 60)
    
    # 1. 获取目标应用（用户新创建的Smarti应用）
    cursor.execute("""
        SELECT id, name, slug FROM apps 
        WHERE slug = 'smarti' AND owner_id = '83208afb-917d-42aa-ab28-7a3fd04ae12f'
    """)
    target_app = cursor.fetchone()
    
    if not target_app:
        print("❌ 未找到目标Smarti应用（slug='smarti'）")
        return False
    
    target_app_id, target_app_name, target_app_slug = target_app
    print(f"✅ 目标应用: {target_app_name} (ID: {target_app_id})")
    
    # 2. 获取源应用列表（需要迁移的5个Smarti应用）
    source_apps = [
        ('smarti-sample-financial', '[Smarti] Sample Financial'),
        ('smarti-sample-hospital', '[Smarti] Sample Hospital'),
        ('smarti-sample-invoicing', '[Smarti] Sample Invoicing'),
        ('smarti-sample-test', '[Smarti] Sample Test'),
        ('smarti-template', '[Smarti] Template')
    ]
    
    # 查询源应用的详细信息
    source_app_details = []
    for slug, name in source_apps:
        cursor.execute("SELECT id, name, slug FROM apps WHERE slug = ?", (slug,))
        app = cursor.fetchone()
        if app:
            source_app_details.append(app)
            print(f"📁 源应用: {app[1]} (ID: {app[0]})")
        else:
            print(f"⚠️  警告: 未找到应用 {slug}")
    
    if not source_app_details:
        print("❌ 未找到任何源应用")
        return False
    
    # 3. 开始事务
    conn.execute("BEGIN TRANSACTION")
    
    try:
        # 4. 为每个源应用创建顶层文件夹（在目标应用中）
        print("\n🏗️  创建顶层文件夹结构...")
        top_folder_map = {}  # 映射：源应用ID -> 顶层文件夹ID
        
        for app_id, app_name, app_slug in source_app_details:
            # 跳过空应用（如Template）
            cursor.execute("SELECT COUNT(*) FROM folders WHERE app_id = ?", (app_id,))
            folder_count = cursor.fetchone()[0]
            
            if folder_count == 0:
                print(f"  跳过 {app_name} (无文件夹)")
                top_folder_map[app_id] = None
                continue
            
            # 创建顶层文件夹
            top_folder_name = app_name.replace('[Smarti] ', '').strip()
            top_folder_slug = f"{app_slug}-root"
            
            cursor.execute("""
                INSERT INTO folders (
                    id, name, slug, app_id, parent_folder_id, 
                    drawer_id, settings, metadata, created_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?, NULL,
                    NULL, '{}', '{}', datetime('now'), datetime('now')
                )
            """, (
                f"{app_id}-root",  # 使用源应用ID加后缀作为新文件夹ID
                top_folder_name,
                top_folder_slug,
                target_app_id
            ))
            
            top_folder_id = f"{app_id}-root"
            top_folder_map[app_id] = top_folder_id
            
            print(f"  创建顶层文件夹: {top_folder_name} (ID: {top_folder_id})")
        
        # 5. 迁移文件夹（更新app_id和parent_folder_id）
        print("\n🔄 迁移文件夹...")
        migrated_folders = 0
        
        for app_id, app_name, app_slug in source_app_details:
            if app_id not in top_folder_map or top_folder_map[app_id] is None:
                continue
            
            top_folder_id = top_folder_map[app_id]
            
            # 获取该应用的所有文件夹
            cursor.execute("""
                SELECT id, name, slug, parent_folder_id 
                FROM folders 
                WHERE app_id = ?
                ORDER BY created_at
            """, (app_id,))
            
            folders = cursor.fetchall()
            
            for folder_id, folder_name, folder_slug, old_parent_id in folders:
                # 确定新的parent_folder_id
                new_parent_id = top_folder_id if old_parent_id is None else old_parent_id
                
                # 更新文件夹的app_id和parent_folder_id
                cursor.execute("""
                    UPDATE folders 
                    SET app_id = ?, parent_folder_id = ?
                    WHERE id = ?
                """, (target_app_id, new_parent_id, folder_id))
                
                migrated_folders += 1
            
            print(f"  迁移 {app_name}: {len(folders)} 个文件夹")
        
        # 6. 验证文档自动跟随（通过外键关系，文档会自动关联到新文件夹）
        print("\n📄 检查文档迁移...")
        for app_id, app_name, app_slug in source_app_details:
            if app_id not in top_folder_map or top_folder_map[app_id] is None:
                continue
            
            # 统计迁移到目标应用中的文档数量
            cursor.execute("""
                SELECT COUNT(*) FROM documents 
                WHERE folder_id IN (
                    SELECT id FROM folders WHERE app_id = ?
                )
            """, (target_app_id,))
            
            doc_count_in_target = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM documents 
                WHERE folder_id IN (
                    SELECT id FROM folders WHERE app_id = ?
                )
            """, (app_id,))
            
            doc_count_in_source = cursor.fetchone()[0]
            
            print(f"  {app_name}: {doc_count_in_source} 个文档已自动迁移")
        
        # 7. 提交事务
        conn.commit()
        print("\n✅ 数据迁移完成！")
        
        # 8. 打印迁移后统计
        print("\n" + "=" * 60)
        print("🎉 迁移完成统计")
        print("=" * 60)
        
        cursor.execute("SELECT COUNT(*) FROM folders WHERE app_id = ?", (target_app_id,))
        final_folder_count = cursor.fetchone()[0]
        print(f"目标应用文件夹总数: {final_folder_count} 个")
        
        cursor.execute("""
            SELECT COUNT(*) FROM documents 
            WHERE folder_id IN (
                SELECT id FROM folders WHERE app_id = ?
            )
        """, (target_app_id,))
        final_doc_count = cursor.fetchone()[0]
        print(f"目标应用文档总数: {final_doc_count} 个")
        
        # 显示新的文件夹结构
        print("\n📂 新的文件夹结构:")
        cursor.execute("""
            SELECT f1.name as top_folder, COUNT(f2.id) as subfolders, COUNT(d.id) as documents
            FROM folders f1
            LEFT JOIN folders f2 ON f2.parent_folder_id = f1.id
            LEFT JOIN documents d ON d.folder_id IN (f1.id, f2.id)
            WHERE f1.app_id = ? AND f1.parent_folder_id IS NULL
            GROUP BY f1.id, f1.name
            ORDER BY f1.name
        """, (target_app_id,))
        
        for top_folder, subfolders, documents in cursor.fetchall():
            print(f"  📁 {top_folder}: {subfolders} 个子文件夹, {documents} 个文档")
        
        # 9. 可选：修改源应用的所有者，使其不在前端显示
        print("\n🔄 可选：修改源应用所有者以隐藏它们...")
        for app_id, app_name, app_slug in source_app_details:
            cursor.execute("""
                UPDATE apps SET owner_id = '4dad6fa1-d521-417f-8877-efe95fcf1f04'
                WHERE id = ?
            """, (app_id,))
            print(f"  隐藏 {app_name}")
        
        conn.commit()
        
        print("\n" + "=" * 60)
        print("💡 使用说明:")
        print("=" * 60)
        print("1. 访问地址: http://localhost:5174/smarti")
        print("2. 所有Smarti数据现在统一在一个应用中")
        print("3. 源应用已被隐藏（如需恢复，可修改所有者ID）")
        print("4. 数据库备份: " + os.path.basename(backup_path))
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

def main():
    """主函数"""
    print("🚀 Smarti数据统一迁移工具")
    print("=" * 60)
    print("将5个分散的Smarti应用数据迁移到统一的Smarti应用中")
    print()
    
    # 迁移前统计
    conn = get_connection()
    cursor = conn.cursor()
    print_stats(cursor, "迁移前统计")
    conn.close()
    
    # 确认执行
    print("\n⚠️  确认执行迁移操作吗？")
    print("  此操作将:")
    print("  1. 创建数据库备份")
    print("  2. 迁移97个文件夹和115个文档到统一应用")
    print("  3. 修改源应用所有者以隐藏它们")
    print("  4. 无法自动回滚（需手动恢复备份）")
    
    response = input("\n输入 'YES' 确认执行，其他任意键取消: ")
    
    if response.strip().upper() != 'YES':
        print("❌ 取消迁移操作")
        return
    
    # 执行迁移
    success = migrate_smarti_data()
    
    if success:
        print("\n✅ 迁移成功完成！")
    else:
        print("\n❌ 迁移失败，请检查错误信息")

if __name__ == "__main__":
    main()