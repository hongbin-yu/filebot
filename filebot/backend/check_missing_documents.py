#!/usr/bin/env python3
"""
检查数据库中但备份中找不到的文档
"""

import sqlite3
import os
from pathlib import Path

BACKUP_ROOT = Path("/home/hongb/.openclaw/workspace/filebot/backups/production_migration_20260321_175924")
FILEBOT_DB = Path("filebot.db")

def find_all_backup_files():
    """获取所有备份文件的清单"""
    backup_files = {}
    for root, dirs, files in os.walk(BACKUP_ROOT):
        for file in files:
            backup_files[file] = os.path.relpath(os.path.join(root, file), BACKUP_ROOT)
    return backup_files

def check_missing_documents():
    """检查缺失的文档"""
    conn = sqlite3.connect(FILEBOT_DB)
    cursor = conn.cursor()
    
    # 获取所有Smarti相关文档
    cursor.execute("""
        SELECT d.id, d.title, d.original_filename, d.stored_filename, d.file_size, d.file_type,
               f.name as folder_name, a.name as app_name
        FROM documents d
        LEFT JOIN folders f ON d.folder_id = f.id
        LEFT JOIN apps a ON f.app_id = a.id
        WHERE d.original_filename IS NOT NULL 
          AND d.original_filename != ''
          AND (d.original_filename LIKE '%smarti.%' OR d.original_filename LIKE '%.CLD' OR d.original_filename LIKE '%.cld')
        ORDER BY d.original_filename
    """)
    
    documents = cursor.fetchall()
    
    # 获取备份文件清单
    backup_files = find_all_backup_files()
    
    print(f"📊 检查 {len(documents)} 个Smarti相关文档")
    
    missing = []
    found = []
    other_issues = []
    
    for doc in documents:
        doc_id, title, original_filename, stored_filename, file_size, file_type, folder_name, app_name = doc
        
        # 提取目标文件名
        if '\\' in original_filename:
            target_filename = original_filename.split('\\')[1]
        else:
            target_filename = original_filename
        
        # 检查是否在备份中
        if target_filename in backup_files:
            found.append((original_filename, backup_files[target_filename]))
        else:
            # 检查文件大小是否为0或NULL
            if file_size is None or file_size == 0:
                missing.append((original_filename, target_filename, folder_name, app_name, "无文件大小"))
            else:
                other_issues.append((original_filename, target_filename, folder_name, app_name, f"已有大小: {file_size}"))
    
    print(f"\n📈 统计结果:")
    print(f"  总文档数: {len(documents)}")
    print(f"  在备份中找到的: {len(found)}")
    print(f"  在备份中缺失且无文件大小的: {len(missing)}")
    print(f"  其他情况: {len(other_issues)}")
    
    if missing:
        print(f"\n❌ 缺失的文档（无文件大小）:")
        print(f"{'原始文件名':40} {'目标文件名':20} {'文件夹':20} {'应用':20} {'状态'}")
        print("-" * 120)
        for original, target, folder, app, status in missing[:20]:
            folder_short = folder[:18] + "..." if folder and len(folder) > 18 else folder or ""
            app_short = app[:18] + "..." if app and len(app) > 18 else app or ""
            print(f"{original:40} {target:20} {folder_short:20} {app_short:20} {status}")
        
        # 按文件类型统计缺失的文件
        print(f"\n📊 缺失文件类型分布:")
        type_counts = {}
        for original, target, folder, app, status in missing:
            ext = target.split('.')[-1].lower() if '.' in target else '未知'
            type_counts[ext] = type_counts.get(ext, 0) + 1
        
        for ext, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  .{ext}: {count} 个")
    
    if found:
        print(f"\n✅ 找到的文件示例（前10个）:")
        for original, backup_path in found[:10]:
            print(f"  {original} -> {backup_path}")
    
    # 检查特定的可疑文件模式
    print(f"\n🔍 检查特定文件模式:")
    suspicious_patterns = ['....', 'sig00000004', 'IDX000000']
    for pattern in suspicious_patterns:
        matches = [(original, target, folder, app, status) 
                   for original, target, folder, app, status in missing 
                   if pattern in original or pattern in target]
        if matches:
            print(f"  包含 '{pattern}' 的文件:")
            for original, target, folder, app, status in matches[:5]:
                print(f"    {original}")
    
    conn.close()
    
    return missing, found, other_issues

def check_backup_integrity():
    """检查备份完整性"""
    print("\n🔍 检查备份完整性...")
    
    # 统计备份中的文件类型
    type_counts = {}
    total_files = 0
    
    for root, dirs, files in os.walk(BACKUP_ROOT):
        for file in files:
            total_files += 1
            ext = file.split('.')[-1].lower() if '.' in file else '无扩展名'
            type_counts[ext] = type_counts.get(ext, 0) + 1
    
    print(f"  备份文件总数: {total_files}")
    print(f"  文件类型分布:")
    for ext, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"    .{ext}: {count} 个 ({count/total_files*100:.1f}%)")
    
    # 检查备份目录结构
    print(f"\n📁 备份目录结构:")
    for item in sorted(os.listdir(BACKUP_ROOT)):
        item_path = BACKUP_ROOT / item
        if item_path.is_dir():
            file_count = sum(len(files) for _, _, files in os.walk(item_path))
            print(f"  {item}/: {file_count} 个文件")

def main():
    print("=" * 60)
    print("Smarti文档完整性检查")
    print("=" * 60)
    
    # 检查缺失文档
    missing, found, other_issues = check_missing_documents()
    
    # 检查备份完整性
    check_backup_integrity()
    
    print("\n" + "=" * 60)
    print("结论")
    print("=" * 60)
    
    if missing:
        print(f"❌ 发现 {len(missing)} 个文档在备份中找不到且无文件大小")
        print("\n可能原因:")
        print("  1. 备份不完整（某些文件在迁移过程中丢失）")
        print("  2. 文件名不匹配（数据库中的文件名与实际文件不一致）")
        print("  3. 文件存储在其他位置（不在当前备份目录中）")
        print("  4. 导入过程有问题（只导入了部分文件）")
        
        print("\n🔧 建议:")
        print("  1. 手动检查缺失文件是否确实不存在")
        print("  2. 考虑从其他备份源获取这些文件")
        print("  3. 如果文件不重要，可以标记为'文件缺失'状态")
        print("  4. 继续处理其他任务，如导出功能开发")
    else:
        print("✅ 所有文档都在备份中找到或有文件大小")

if __name__ == "__main__":
    main()