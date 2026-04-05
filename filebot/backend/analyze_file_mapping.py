#!/usr/bin/env python3
"""
分析文件映射问题：数据库中的原始文件名 vs 实际文件系统
"""

import sqlite3
import os
import re
from collections import defaultdict
from pathlib import Path

# 路径配置
BACKUP_ROOT = Path("/home/hongb/.openclaw/workspace/filebot/backups/production_migration_20260321_175924")
FILEBOT_DB = Path("filebot.db")

def get_database_files():
    """从数据库获取所有Smarti相关文件的原始文件名"""
    conn = sqlite3.connect(FILEBOT_DB)
    cursor = conn.cursor()
    
    # 获取所有Smarti导入的文档
    cursor.execute("""
        SELECT id, original_filename, stored_filename, file_size
        FROM documents
        WHERE original_filename IS NOT NULL 
          AND original_filename != ''
          AND (original_filename LIKE '%smarti.%' OR original_filename LIKE '%.CLD' OR original_filename LIKE '%.cld')
        ORDER BY original_filename
    """)
    
    documents = cursor.fetchall()
    
    print(f"📊 数据库中的Smarti相关文档: {len(documents)} 个")
    
    # 分析文件名模式
    patterns = defaultdict(int)
    for doc_id, original, stored, size in documents[:20]:
        print(f"  {original} -> {stored} ({size if size else '无大小'})")
        # 提取目录部分
        if '\\' in original:
            dir_part = original.split('\\')[0]
            patterns[dir_part] += 1
    
    print(f"\n📁 文件名模式统计:")
    for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
        print(f"  {pattern}: {count} 个文件")
    
    conn.close()
    return documents

def scan_backup_files():
    """扫描备份目录中的所有文件"""
    print("\n🔍 扫描备份文件系统...")
    
    # 查找所有.CLD文件
    cld_files = []
    for root, dirs, files in os.walk(BACKUP_ROOT):
        for file in files:
            if file.lower().endswith('.cld'):
                rel_path = os.path.relpath(os.path.join(root, file), BACKUP_ROOT)
                cld_files.append(rel_path)
    
    print(f"  找到 {len(cld_files)} 个.CLD文件")
    
    # 按目录分组统计
    dir_counts = defaultdict(int)
    for file_path in cld_files:
        dir_name = os.path.dirname(file_path)
        dir_counts[dir_name] += 1
    
    print(f"\n📂 目录分布 (前10个):")
    for dir_name, count in sorted(dir_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {dir_name}: {count} 个文件")
    
    # 显示一些文件路径示例
    print(f"\n📋 文件路径示例 (前10个):")
    for file_path in sorted(cld_files)[:10]:
        print(f"  {file_path}")
    
    return cld_files

def find_missing_files(documents, cld_files):
    """查找数据库中但备份中找不到的文件"""
    print("\n🔎 查找缺失的文件...")
    
    # 将备份文件转换为查找字典（文件名 -> 完整路径）
    backup_dict = {}
    for file_path in cld_files:
        filename = os.path.basename(file_path)
        backup_dict[filename] = file_path
    
    missing = []
    found = []
    
    for doc_id, original, stored, size in documents:
        # 从原始文件名提取目标文件名
        # 格式如 "smarti.002\\00000002.CLD" 或 "smarti.002\\IDX00034.CLD"
        if '\\' in original:
            target_filename = original.split('\\')[1]
        else:
            target_filename = original
        
        if target_filename in backup_dict:
            found.append((original, backup_dict[target_filename]))
        else:
            missing.append(original)
    
    print(f"  数据库中的文件: {len(documents)} 个")
    print(f"  在备份中找到的: {len(found)} 个")
    print(f"  在备份中缺失的: {len(missing)} 个")
    
    if missing:
        print(f"\n❌ 缺失的文件示例 (前10个):")
        for filename in missing[:10]:
            print(f"  {filename}")
    
    if found:
        print(f"\n✅ 找到的文件示例 (前10个):")
        for original, backup_path in found[:10]:
            print(f"  {original} -> {backup_path}")
    
    return missing, found

def analyze_file_path_patterns():
    """分析文件路径模式"""
    print("\n🔍 分析文件路径模式...")
    
    # 查看原始SQL中的文件路径模式
    sql_file = BACKUP_ROOT / "smarti.script.backup"
    with open(sql_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 查找EXTERNAL_FILE表的INSERT语句
    external_file_pattern = r"INSERT INTO EXTERNAL_FILE VALUES\((\d+),(\d+),([^,]*),([^,]*),'([^']*)'"
    matches = re.findall(external_file_pattern, content)
    
    if matches:
        print(f"  在SQL中找到 {len(matches)} 个EXTERNAL_FILE记录")
        
        # 分析文件路径模式
        path_patterns = defaultdict(int)
        for match in matches[:20]:
            if len(match) >= 5:
                file_id, doc_id, x, y, file_path = match[:5]
                path_patterns[file_path] += 1
        
        print(f"\n📁 原始文件路径示例 (前10个):")
        for file_path, count in sorted(path_patterns.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {file_path}")
    else:
        print("  未找到EXTERNAL_FILE记录")

def check_file_sizes():
    """检查已成功复制文件的文件大小"""
    print("\n📏 检查文件大小...")
    
    conn = sqlite3.connect(FILEBOT_DB)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN file_size IS NOT NULL AND file_size > 0 THEN 1 ELSE 0 END) as has_size,
               AVG(file_size) as avg_size
        FROM documents
        WHERE original_filename LIKE '%.CLD' OR original_filename LIKE '%.cld'
    """)
    
    total, has_size, avg_size = cursor.fetchone()
    
    print(f"  .CLD文档总数: {total}")
    print(f"  有文件大小的: {has_size} ({has_size/total*100:.1f}%)")
    print(f"  平均文件大小: {avg_size/1024:.1f} KB" if avg_size else "  平均文件大小: N/A")
    
    conn.close()

def main():
    print("=" * 60)
    print("Smarti文件映射问题分析")
    print("=" * 60)
    
    # 1. 从数据库获取文件信息
    documents = get_database_files()
    
    # 2. 扫描备份文件系统
    cld_files = scan_backup_files()
    
    # 3. 查找缺失文件
    missing, found = find_missing_files(documents, cld_files)
    
    # 4. 分析原始文件路径模式
    analyze_file_path_patterns()
    
    # 5. 检查文件大小
    check_file_sizes()
    
    print("\n" + "=" * 60)
    print("结论与建议")
    print("=" * 60)
    
    if missing:
        print(f"❌ 问题: {len(missing)} 个文件在备份中找不到")
        print("可能原因:")
        print("  1. 备份不完整（部分文件未包含）")
        print("  2. 文件名不匹配（大小写、格式差异）")
        print("  3. 文件存储在其他位置（如files_backup）")
        print("  4. 数据库中的原始路径与实际路径不一致")
    
    print("\n🔧 建议解决方案:")
    print("  1. 使用文件名匹配而不是完整路径匹配")
    print("  2. 在所有备份子目录中搜索文件")
    print("  3. 检查files_backup目录")
    print("  4. 手动验证部分文件的存在性")

if __name__ == "__main__":
    main()