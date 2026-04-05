#!/usr/bin/env python3
"""
Smarti数据完整重新导入脚本（方案一）
"""

import os
import sys
import sqlite3
import json
import shutil
import subprocess
from pathlib import Path
import time

# 路径配置
BASE_DIR = Path("/home/hongb/.openclaw/workspace/filebot/backend")
DB_PATH = BASE_DIR / "filebot.db"
MAPPING_FILE = BASE_DIR / "smarti_import_mapping.json"
BACKUP_BASE = Path("/home/hongb/.openclaw/workspace/filebot/backups/production_migration_20260321_175924")
SMARTI_SCRIPT = BACKUP_BASE / "smarti.script.backup"

# 备份目录
BACKUP_DIR = Path(str(BASE_DIR) + "/reimport_backup_" + time.strftime("%Y%m%d_%H%M%S"))
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def log_step(message):
    """记录步骤"""
    print(f"\n{'='*60}")
    print(f"📋 {message}")
    print(f"{'='*60}")

def backup_current_data():
    """备份当前数据"""
    log_step("步骤1: 备份当前数据")
    
    # 1. 备份映射文件
    if MAPPING_FILE.exists():
        backup_file = BACKUP_DIR / "smarti_import_mapping.json"
        shutil.copy2(MAPPING_FILE, backup_file)
        print(f"✅ 映射文件备份到: {backup_file}")
    else:
        print("ℹ️  映射文件不存在，跳过备份")
    
    # 2. 备份数据库中的Smarti应用数据
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取Smarti应用
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
            apps_data.append({
                'id': app_id,
                'name': name,
                'slug': slug,
                'description': description,
                'settings': settings,
                'created_at': created_at
            })
        
        # 保存备份
        backup_file = BACKUP_DIR / "smarti_apps_backup.json"
        with open(backup_file, 'w') as f:
            json.dump(apps_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Smarti应用备份到: {backup_file}")
        print(f"   共备份 {len(apps_data)} 个应用")
    else:
        print("ℹ️  未找到Smarti应用，跳过应用备份")
    
    conn.close()
    
    print(f"\n📂 所有备份文件保存在: {BACKUP_DIR}")

def cleanup_database():
    """清理数据库"""
    log_step("步骤2: 清理数据库中的Smarti数据")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 获取Smarti应用ID
    cursor.execute("""
        SELECT id, name FROM apps 
        WHERE slug LIKE '%smarti%' OR name LIKE '%Smarti%'
    """)
    smarti_apps = cursor.fetchall()
    
    if not smarti_apps:
        print("ℹ️  数据库中未找到Smarti应用，跳过清理")
        return True
    
    app_ids = [app[0] for app in smarti_apps]
    app_names = [app[1] for app in smarti_apps]
    
    print(f"找到 {len(app_ids)} 个Smarti应用需要清理:")
    for name in app_names:
        print(f"  - {name}")
    
    # 2. 统计删除数据量
    print("\n📊 删除数据统计:")
    
    # 应用数量
    print(f"  Smarti应用: {len(app_ids)} 个")
    
    # 文件夹数量
    placeholders = ','.join(['?'] * len(app_ids))
    cursor.execute(f"""
        SELECT COUNT(*) FROM folders 
        WHERE app_id IN ({placeholders})
    """, app_ids)
    folder_count = cursor.fetchone()[0]
    print(f"  Smarti文件夹: {folder_count} 个")
    
    # 文档数量
    cursor.execute(f"""
        SELECT COUNT(*) FROM documents 
        WHERE folder_id IN (
            SELECT id FROM folders 
            WHERE app_id IN ({placeholders})
        )
    """, app_ids)
    doc_count = cursor.fetchone()[0]
    print(f"  Smarti文档: {doc_count} 个")
    
    # 3. 执行删除
    print("\n🔧 执行删除操作...")
    
    # 删除映射表
    cursor.execute("DROP TABLE IF EXISTS smarti_import_mapping")
    print("✅ 删除 smarti_import_mapping 表")
    
    # 删除应用（级联删除文件夹和文档）
    for app_id in app_ids:
        cursor.execute("DELETE FROM apps WHERE id = ?", (app_id,))
    
    conn.commit()
    print(f"✅ 删除 {len(app_ids)} 个Smarti应用")
    
    # 4. 验证清理
    cursor.execute("""
        SELECT COUNT(*) FROM apps 
        WHERE slug LIKE '%smarti%' OR name LIKE '%Smarti%'
    """)
    remaining_apps = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='smarti_import_mapping'")
    mapping_table_exists = cursor.fetchone()[0]
    
    conn.close()
    
    if remaining_apps == 0 and mapping_table_exists == 0:
        print("🎉 数据库清理完成！")
        return True
    else:
        print(f"⚠️  清理可能不完整:")
        print(f"  剩余Smarti应用: {remaining_apps} 个")
        print(f"  映射表存在: {'是' if mapping_table_exists else '否'}")
        return False

def run_import_script():
    """运行导入脚本"""
    log_step("步骤3: 运行Smarti导入脚本")
    
    if not SMARTI_SCRIPT.exists():
        print(f"❌ Smarti备份脚本不存在: {SMARTI_SCRIPT}")
        return False
    
    print(f"使用备份文件: {SMARTI_SCRIPT}")
    print(f"文件大小: {SMARTI_SCRIPT.stat().st_size:,} 字节")
    
    # 切换到工作目录
    original_cwd = os.getcwd()
    os.chdir(BASE_DIR)
    
    try:
        # 运行导入脚本
        print("\n🚀 开始导入...")
        result = subprocess.run(
            ["python3", "import_smarti.py"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        print("📋 导入脚本输出:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️  错误输出:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ 导入脚本执行成功")
            
            # 验证导入结果
            print("\n🔍 验证导入结果...")
            verify_result = subprocess.run(
                ["python3", "verify_smarti_import.py"],
                capture_output=True,
                text=True
            )
            
            print(verify_result.stdout)
            if verify_result.stderr:
                print(verify_result.stderr)
            
            return True
        else:
            print(f"❌ 导入脚本失败，返回码: {result.returncode}")
            return False
            
    finally:
        os.chdir(original_cwd)

def copy_physical_files():
    """复制物理文件"""
    log_step("步骤4: 复制物理文件")
    
    original_cwd = os.getcwd()
    os.chdir(BASE_DIR)
    
    try:
        print("🚀 运行文件复制脚本...")
        result = subprocess.run(
            ["python3", "copy_smarti_files.py"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        print("📋 复制脚本输出:")
        print(result.stdout[:1000])  # 只显示前1000字符
        
        if result.stderr:
            print("⚠️  错误输出:")
            print(result.stderr[:500])
        
        if result.returncode == 0:
            print("✅ 文件复制完成")
            return True
        else:
            print(f"❌ 文件复制失败，返回码: {result.returncode}")
            return False
            
    finally:
        os.chdir(original_cwd)

def mark_missing_files():
    """标记缺失文件"""
    log_step("步骤5: 标记缺失文件")
    
    original_cwd = os.getcwd()
    os.chdir(BASE_DIR)
    
    try:
        print("🚀 运行缺失文件标记脚本...")
        result = subprocess.run(
            ["python3", "mark_missing_files.py"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        print("📋 标记脚本输出:")
        print(result.stdout[:1000])  # 只显示前1000字符
        
        if result.stderr:
            print("⚠️  错误输出:")
            print(result.stderr[:500])
        
        if result.returncode == 0:
            print("✅ 缺失文件标记完成")
            
            # 检查报告文件
            report_file = BASE_DIR / "missing_files_report.txt"
            if report_file.exists():
                with open(report_file, 'r') as f:
                    content = f.read()
                    print(f"\n📄 缺失文件报告摘要:")
                    print(content[:500])
                    if len(content) > 500:
                        print("... (完整报告请查看文件)")
            
            return True
        else:
            print(f"❌ 标记脚本失败，返回码: {result.returncode}")
            return False
            
    finally:
        os.chdir(original_cwd)

def main():
    """主函数"""
    print("🚀 Smarti数据完整重新导入（方案一）")
    print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查数据库文件
    if not DB_PATH.exists():
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        return 1
    
    # 检查备份文件
    if not SMARTI_SCRIPT.exists():
        print(f"❌ Smarti备份脚本不存在: {SMARTI_SCRIPT}")
        return 1
    
    # 步骤1: 备份
    backup_current_data()
    
    # 步骤2: 清理数据库
    if not cleanup_database():
        print("❌ 数据库清理失败，停止执行")
        return 1
    
    # 步骤3: 导入数据
    if not run_import_script():
        print("❌ 数据导入失败，停止执行")
        return 1
    
    # 步骤4: 复制文件
    if not copy_physical_files():
        print("⚠️  文件复制失败，但继续执行")
    
    # 步骤5: 标记缺失文件
    if not mark_missing_files():
        print("⚠️  标记缺失文件失败")
    
    log_step("🎉 重新导入完成！")
    print(f"完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n📊 总结:")
    print(f"  - 备份保存在: {BACKUP_DIR}")
    print(f"  - 原始备份: {SMARTI_SCRIPT}")
    print(f"  - 数据库: {DB_PATH}")
    print(f"\n🔧 如需恢复备份，请参考备份目录中的文件")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())