#!/usr/bin/env python3
"""
更新5个Smarti应用的所有者，使其对当前用户可见
创建者: 码博士
创建时间: 2026-04-04
"""

import sqlite3
import os
from datetime import datetime
import shutil

def backup_database(db_path, backup_dir='backups'):
    """备份数据库"""
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'filebot_pre_ownership_update_{timestamp}.db')
    
    print(f"📦 创建数据库备份: {backup_path}")
    shutil.copy2(db_path, backup_path)
    return backup_path

def update_app_ownership():
    """更新应用所有者"""
    db_path = 'filebot.db'
    
    # 创建备份
    backup_path = backup_database(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🚀 更新Smarti应用所有权")
    print("=" * 60)
    
    # 定义用户ID
    user_id = '83208afb-917d-42aa-ab28-7a3fd04ae12f'  # 当前用户
    admin_id = '4dad6fa1-d521-417f-8877-efe95fcf1f04'  # 原所有者
    
    # 要更新的应用列表（5个有数据的Smarti应用）
    target_apps = [
        ('smarti-sample-financial', '[Smarti] Sample Financial'),
        ('smarti-sample-hospital', '[Smarti] Sample Hospital'),
        ('smarti-sample-invoicing', '[Smarti] Sample Invoicing'),
        ('smarti-sample-test', '[Smarti] Sample Test'),
        ('smarti-template', '[Smarti] Template')
    ]
    
    print(f"👤 当前用户ID: {user_id}")
    print(f"👑 原所有者ID: {admin_id}")
    print()
    
    # 显示当前状态
    print("📊 更新前应用状态:")
    for slug, name in target_apps:
        cursor.execute("""
            SELECT id, name, slug, owner_id, 
                   (SELECT COUNT(*) FROM folders WHERE app_id = apps.id) as folder_count,
                   (SELECT COUNT(*) FROM documents WHERE folder_id IN (SELECT id FROM folders WHERE app_id = apps.id)) as doc_count
            FROM apps WHERE slug = ?
        """, (slug,))
        
        app = cursor.fetchone()
        if app:
            app_id, app_name, app_slug, owner_id, folder_count, doc_count = app
            owner_desc = "👤 当前用户" if owner_id == user_id else "👑 管理员" if owner_id == admin_id else "❓ 其他"
            print(f"  {app_name} ({app_slug}):")
            print(f"    所有者: {owner_desc} ({owner_id})")
            print(f"    文件夹: {folder_count} 个, 文档: {doc_count} 个")
        else:
            print(f"  ⚠️  未找到应用: {name} ({slug})")
    
    # 确认执行
    print("\n⚠️  确认更新应用所有者吗？")
    print("  此操作将:")
    print("  1. 将5个Smarti应用的所有者从管理员改为当前用户")
    print("  2. 使你能够在前端直接看到这些应用")
    print("  3. 保持所有数据完整不变")
    print("  4. 不会合并或迁移任何数据")
    
    response = input("\n输入 'YES' 确认执行，其他任意键取消: ")
    
    if response.strip().upper() != 'YES':
        print("❌ 取消更新操作")
        conn.close()
        return
    
    # 开始事务
    conn.execute("BEGIN TRANSACTION")
    
    try:
        updated_count = 0
        
        for slug, name in target_apps:
            # 检查应用是否存在
            cursor.execute("SELECT id, owner_id FROM apps WHERE slug = ?", (slug,))
            app = cursor.fetchone()
            
            if app:
                app_id, current_owner = app
                
                if current_owner == user_id:
                    print(f"  ⚠️  {name} 已属于当前用户，跳过")
                    continue
                
                # 更新所有者
                cursor.execute("UPDATE apps SET owner_id = ? WHERE id = ?", (user_id, app_id))
                updated_count += 1
                
                print(f"  ✅ 更新 {name}: {current_owner[:8]}... → {user_id[:8]}...")
            else:
                print(f"  ❌ 未找到应用: {name} ({slug})")
        
        # 提交事务
        conn.commit()
        
        print(f"\n✅ 更新完成！成功更新 {updated_count} 个应用的所有者")
        
        # 显示更新后状态
        print("\n📊 更新后应用状态:")
        for slug, name in target_apps:
            cursor.execute("""
                SELECT name, slug, owner_id,
                       (SELECT COUNT(*) FROM folders WHERE app_id = apps.id) as folder_count
                FROM apps WHERE slug = ?
            """, (slug,))
            
            app = cursor.fetchone()
            if app:
                app_name, app_slug, owner_id, folder_count = app
                status = "👤 可见" if owner_id == user_id else "👑 管理员"
                print(f"  {app_name}: {status}, 文件夹: {folder_count} 个")
        
        print("\n" + "=" * 60)
        print("💡 使用说明:")
        print("=" * 60)
        print("1. 刷新前端页面或重新登录")
        print("2. 你现在应该能看到5个Smarti应用:")
        print("   - http://localhost:5174/smarti-sample-financial")
        print("   - http://localhost:5174/smarti-sample-hospital")
        print("   - http://localhost:5174/smarti-sample-invoicing")
        print("   - http://localhost:5174/smarti-sample-test")
        print("   - http://localhost:5174/smarti-template")
        print("3. 每个应用独立显示，包含原有文件夹和文档")
        print("4. 数据库备份: " + os.path.basename(backup_path))
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 更新失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

def main():
    """主函数"""
    print("🚀 Smarti应用所有权更新工具")
    print("=" * 60)
    print("将5个Smarti应用的所有者从管理员改为当前用户")
    print("使这些应用在前端直接可见，无需数据迁移")
    print()
    
    # 执行更新
    success = update_app_ownership()
    
    if success:
        print("\n✅ 所有权更新成功！")
    else:
        print("\n❌ 所有权更新失败")

if __name__ == "__main__":
    main()