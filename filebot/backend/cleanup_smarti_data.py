#!/usr/bin/env python3
"""
清理现有的Smarti数据，为重新导入做准备
"""

import sqlite3
import json
from pathlib import Path
import shutil

# 路径配置
DB_PATH = Path("filebot.db")
MAPPING_FILE = Path("smarti_import_mapping.json")
BACKUP_DIR = Path("/home/hongb/.openclaw/workspace/filebot/backups/smarti_cleanup_backup")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def backup_data():
    """备份当前数据"""
    print("📂 备份当前数据...")
    
    # 1. 备份映射文件
    if MAPPING_FILE.exists():
        backup_file = BACKUP_DIR / f"smarti_import_mapping_{Path(DB_PATH).stat().st_mtime}.json"
        shutil.copy2(MAPPING_FILE, backup_file)
        print(f"  ✅ 映射文件备份到: {backup_file}")
    
    # 2. 备份数据库中的Smarti数据
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取所有Smarti应用
    cursor.execute("""
        SELECT id, name, slug, description, settings, created_at
        FROM apps 
        WHERE slug LIKE '%smarti%' OR name LIKE '%Smarti%'
    """)
    smarti_apps = cursor.fetchall()
    
    if smarti_apps:
        apps_data = []
        for app in smarti_apps:
            app_id, name, slug, description, settings, created_at = app
            app_info = {
                'id': app_id,
                'name': name,
                'slug': slug,
                'description': description,
                'settings': settings,
                'created_at': created_at
            }
            apps_data.append(app_info)
        
        # 保存到JSON文件
        backup_file = BACKUP_DIR / f"smarti_apps_backup_{Path(DB_PATH).stat().st_mtime}.json"
        with open(backup_file, 'w') as f:
            json.dump(apps_data, f, indent=2, ensure_ascii=False)
        print(f"  ✅ Smarti应用数据备份到: {backup_file}")
        print(f"     共备份 {len(apps_data)} 个应用")
    
    conn.close()

def cleanup_database():
    """清理数据库中的Smarti数据"""
    print("\n🗑️  清理数据库...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 获取所有Smarti应用ID
    cursor.execute("""
        SELECT id FROM apps 
        WHERE slug LIKE '%smarti%' OR name LIKE '%Smarti%'
    """)
    smarti_app_ids = [row[0] for row in cursor.fetchall()]
    
    if not smarti_app_ids:
        print("  ℹ️  未找到Smarti应用，无需清理")
        return
    
    print(f"  找到 {len(smarti_app_ids)} 个Smarti应用需要清理:")
    for app_id in smarti_app_ids:
        cursor.execute("SELECT name, slug FROM apps WHERE id = ?", (app_id,))
        app_name, app_slug = cursor.fetchone()
        print(f"    - {app_name} ({app_slug})")
    
    # 2. 统计删除前数据量
    print("\n📊 删除前统计:")
    
    # 应用数量
    print(f"  Smarti应用: {len(smarti_app_ids)} 个")
    
    # 文件夹数量
    cursor.execute(f"""
        SELECT COUNT(*) FROM folders 
        WHERE app_id IN ({','.join(['?']*len(smarti_app_ids))})
    """, smarti_app_ids)
    folder_count = cursor.fetchone()[0]
    print(f"  Smarti文件夹: {folder_count} 个")
    
    # 文档数量
    cursor.execute(f"""
        SELECT COUNT(*) FROM documents 
        WHERE folder_id IN (
            SELECT id FROM folders 
            WHERE app_id IN ({','.join(['?']*len(smarti_app_ids))})
        )
    """, smarti_app_ids)
    doc_count = cursor.fetchone()[0]
    print(f"  Smarti文档: {doc_count} 个")
    
    # 3. 询问确认
    print("\n⚠️  确认清理操作:")
    print(f"  将删除: {len(smarti_app_ids)}个应用, {folder_count}个文件夹, {doc_count}个文档")
    confirm = input("  输入 'YES' 确认执行清理操作: ")
    
    if confirm != 'YES':
        print("  ❌ 操作取消")
        conn.close()
        return False
    
    # 4. 执行删除（级联删除会自动处理文件夹和文档）
    print("\n🔧 执行删除操作...")
    
    # 先删除映射表
    cursor.execute("DROP TABLE IF EXISTS smarti_import_mapping")
    print("  ✅ 删除 smarti_import_mapping 表")
    
    # 删除应用（级联删除文件夹和文档）
    for app_id in smarti_app_ids:
        cursor.execute("DELETE FROM apps WHERE id = ?", (app_id,))
    
    conn.commit()
    print(f"  ✅ 删除 {len(smarti_app_ids)} 个Smarti应用")
    
    # 5. 验证删除
    cursor.execute("""
        SELECT COUNT(*) FROM apps 
        WHERE slug LIKE '%smarti%' OR name LIKE '%Smarti%'
    """)
    remaining_apps = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='smarti_import_mapping'")
    mapping_table_exists = cursor.fetchone()[0]
    
    conn.close()
    
    if remaining_apps == 0 and mapping_table_exists == 0:
        print("\n🎉 清理完成！")
        print(f"  ✅ 所有Smarti数据已清除")
        print(f"  ✅ 映射表已删除")
        return True
    else:
        print("\n⚠️  清理可能不完整:")
        print(f"  剩余Smarti应用: {remaining_apps} 个")
        print(f"  映射表存在: {'是' if mapping_table_exists else '否'}")
        return False

def cleanup_physical_files():
    """清理物理文件（可选）"""
    print("\n🗂️  清理物理文件（可选）...")
    
    # 文件存储路径
    storage_base = Path("/home/hongb/.openclaw/workspace/filebot/backend/storage")
    
    if not storage_base.exists():
        print("  ℹ️  存储目录不存在，跳过文件清理")
        return
    
    # 这里可以根据需要实现文件清理逻辑
    # 由于文件可能被其他应用共享，需要谨慎处理
    print("  ℹ️  文件清理需要根据具体存储结构实现")
    print("  ℹ️  当前跳过物理文件清理")
    
    # 可以添加逻辑来删除特定模式的文件
    # 例如: 删除 storage/ 目录下与Smarti相关的文件

def main():
    """主函数"""
    print("🧹 Smarti数据清理工具")
    print("=" * 50)
    
    # 检查数据库是否存在
    if not DB_PATH.exists():
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        return
    
    # 1. 备份
    backup_data()
    
    # 2. 清理数据库
    success = cleanup_database()
    
    if success:
        # 3. 可选：清理物理文件
        cleanup_physical_files()
        
        print("\n✅ 清理完成，可以重新运行导入脚本:")
        print("  cd /home/hongb/.openclaw/workspace/filebot/backend")
        print("  python3 import_smarti.py")
    else:
        print("\n❌ 清理失败，请检查问题")

if __name__ == "__main__":
    main()