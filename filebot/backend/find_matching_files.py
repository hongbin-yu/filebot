#!/usr/bin/env python3
"""
查找与数据库文件名匹配的备份文件
"""

import os
import sqlite3
from pathlib import Path

BACKUP_ROOT = Path("/home/hongb/.openclaw/workspace/filebot/backups/production_migration_20260321_175924")
FILEBOT_DB = Path("filebot.db")

def find_all_files():
    """查找所有备份文件"""
    print("🔍 查找所有备份文件...")
    
    all_files = []
    for root, dirs, files in os.walk(BACKUP_ROOT):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), BACKUP_ROOT)
            all_files.append(rel_path)
    
    print(f"  找到 {len(all_files)} 个文件")
    return all_files

def get_database_filenames():
    """获取数据库中的文件名"""
    conn = sqlite3.connect(FILEBOT_DB)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT original_filename 
        FROM documents
        WHERE original_filename IS NOT NULL 
          AND original_filename != ''
          AND (original_filename LIKE '%smarti.%' OR original_filename LIKE '%.CLD' OR original_filename LIKE '%.cld')
    """)
    
    filenames = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    print(f"  数据库中有 {len(filenames)} 个Smarti相关文件名")
    return filenames

def extract_base_filename(db_filename):
    """从数据库文件名提取基础文件名"""
    # 格式如 "smarti.002\00000002.CLD"
    if '\\' in db_filename:
        return db_filename.split('\\')[1]
    return db_filename

def find_matches(db_filenames, all_files):
    """查找匹配的文件"""
    print("\n🔍 查找匹配的文件...")
    
    # 创建查找字典（基础文件名 -> 完整路径）
    file_dict = {}
    for file_path in all_files:
        base_name = os.path.basename(file_path)
        file_dict[base_name] = file_path
    
    matches = []
    missing = []
    
    for db_filename in db_filenames:
        base_name = extract_base_filename(db_filename)
        
        if base_name in file_dict:
            matches.append((db_filename, file_dict[base_name]))
        else:
            missing.append(db_filename)
    
    print(f"  数据库文件: {len(db_filenames)} 个")
    print(f"  找到匹配的: {len(matches)} 个")
    print(f"  未找到的: {len(missing)} 个")
    
    if matches:
        print(f"\n✅ 匹配的文件 (前10个):")
        for db_filename, backup_path in matches[:10]:
            print(f"  {db_filename} -> {backup_path}")
    
    if missing:
        print(f"\n❌ 未找到的文件 (前10个):")
        for filename in missing[:10]:
            print(f"  {filename}")
    
    return matches, missing

def check_specific_files():
    """检查特定文件是否存在"""
    print("\n🔍 检查特定文件...")
    
    # 手动检查一些文件
    test_files = [
        "00000002.CLD",
        "IDX00034.CLD", 
        "IDX00053.CLD",
        "IDX00057.CLD",
        "IDX00067.CLD",
        "IDX00074.CLD",
        "IDX00093.CLD",
        "IDX00099.CLD",
        "fin00000.tif",
        "fin00001.tif"
    ]
    
    for filename in test_files:
        # 在所有位置查找
        found = []
        for root, dirs, files in os.walk(BACKUP_ROOT):
            if filename in files:
                rel_path = os.path.relpath(os.path.join(root, filename), BACKUP_ROOT)
                found.append(rel_path)
        
        if found:
            print(f"  ✅ {filename} 找到 {len(found)} 个位置:")
            for path in found[:2]:  # 只显示前2个
                print(f"    - {path}")
        else:
            print(f"  ❌ {filename} 未找到")

def check_file_counts():
    """检查文件数量"""
    print("\n📊 文件数量统计...")
    
    # 统计数据库中的文档总数
    conn = sqlite3.connect(FILEBOT_DB)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM documents")
    total_docs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM documents WHERE original_filename LIKE '%smarti.%'")
    smarti_docs = cursor.fetchone()[0]
    
    print(f"  数据库总文档数: {total_docs}")
    print(f"  Smarti相关文档: {smarti_docs} ({smarti_docs/total_docs*100:.1f}%)")
    
    # 统计备份中的.CLD文件
    cld_count = 0
    for root, dirs, files in os.walk(BACKUP_ROOT):
        for file in files:
            if file.lower().endswith('.cld'):
                cld_count += 1
    
    print(f"  备份中的.CLD文件: {cld_count}")
    
    conn.close()

def main():
    print("=" * 60)
    print("Smarti文件匹配分析")
    print("=" * 60)
    
    # 1. 获取所有备份文件
    all_files = find_all_files()
    
    # 2. 获取数据库文件名
    db_filenames = get_database_filenames()
    
    # 3. 查找匹配
    matches, missing = find_matches(db_filenames, all_files)
    
    # 4. 检查特定文件
    check_specific_files()
    
    # 5. 文件数量统计
    check_file_counts()
    
    print("\n" + "=" * 60)
    print("分析结论")
    print("=" * 60)
    
    if len(matches) > 0:
        print(f"✅ 好消息: 找到了 {len(matches)}/{len(db_filenames)} 个文件")
        print("   文件确实存在于备份中，只是路径不同")
    else:
        print("❌ 问题: 未找到任何匹配的文件")
    
    print("\n🔧 建议:")
    print("  1. 修改复制脚本，使用文件名匹配而非路径匹配")
    print("  2. 在所有备份子目录中递归搜索文件")
    print("  3. 如果文件确实不存在，可能需要从其他来源获取")

if __name__ == "__main__":
    main()