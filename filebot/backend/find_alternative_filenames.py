#!/usr/bin/env python3
"""
查找缺失文件的替代文件名
"""

import os
import re
from pathlib import Path

BACKUP_ROOT = Path("/home/hongb/.openclaw/workspace/filebot/backups/production_migration_20260321_175924")

# 缺失文件列表
missing_files = [
    "....00000004.pdf",
    "IDX00000085.CLD", 
    "IDX00000101.pdf",
    "IDX00000104.pdf",
    "....00000005.pdf",
    "sig00000004.png",
    "IDX00000084.CLD",
    "IDX00000103.pdf",
    "IDX00000096.CLD",
    "IDX00000098.CLD",
    "IDX00000099.CLD",
    "IDX00000102.pdf",
    "IDX00000100.pdf",
    "IDX00000087.CLD",
    "IDX00000094.CLD"
]

def find_similar_files(filename):
    """查找相似的文件名"""
    results = []
    
    # 移除特殊前缀
    clean_name = re.sub(r'^\.+', '', filename)  # 移除开头的"...."
    
    # 查找所有备份文件
    for root, dirs, files in os.walk(BACKUP_ROOT):
        for file in files:
            # 完全匹配
            if file == filename:
                results.append(("完全匹配", file, os.path.relpath(os.path.join(root, file), BACKUP_ROOT)))
            
            # 清理后匹配
            elif file == clean_name:
                results.append(("清理后匹配", file, os.path.relpath(os.path.join(root, file), BACKUP_ROOT)))
            
            # 相似匹配（相同的数字部分）
            elif re.search(r'\d+', filename) and re.search(r'\d+', file):
                # 提取数字部分
                nums1 = re.findall(r'\d+', filename)
                nums2 = re.findall(r'\d+', file)
                
                if nums1 and nums2 and nums1[-1] == nums2[-1]:  # 最后一个数字相同
                    results.append(("数字匹配", file, os.path.relpath(os.path.join(root, file), BACKUP_ROOT)))
    
    return results

def check_file_patterns():
    """检查文件命名模式"""
    print("🔍 检查文件命名模式...")
    
    # 获取所有备份文件名
    all_files = []
    for root, dirs, files in os.walk(BACKUP_ROOT):
        for file in files:
            all_files.append(file)
    
    # 分析.CLD文件的命名模式
    cld_files = [f for f in all_files if f.lower().endswith('.cld')]
    print(f"  备份中的.CLD文件: {len(cld_files)} 个")
    
    # 提取.CLD文件的数字部分
    cld_patterns = defaultdict(int)
    for file in cld_files:
        # 提取IDX后面的数字
        if file.startswith('IDX'):
            match = re.search(r'IDX(\d+)', file)
            if match:
                num = match.group(1)
                # 数字长度分组
                length = len(num)
                cld_patterns[f"IDX数字长度{length}"] += 1
        
        # 简单数字文件
        elif re.match(r'^\d+\.CLD$', file, re.IGNORECASE):
            match = re.search(r'(\d+)', file)
            if match:
                num = match.group(1)
                length = len(num)
                cld_patterns[f"纯数字长度{length}"] += 1
    
    print(f"\n  .CLD文件命名模式:")
    for pattern, count in sorted(cld_patterns.items(), key=lambda x: x[1], reverse=True):
        print(f"    {pattern}: {count} 个")
    
    # 检查缺失的CLD文件可能对应的模式
    print(f"\n🔍 缺失的.CLD文件分析:")
    for missing in missing_files:
        if missing.lower().endswith('.cld'):
            print(f"\n  {missing}:")
            # 查找相似文件
            similar = find_similar_files(missing)
            if similar:
                for match_type, found_file, path in similar[:3]:
                    print(f"    {match_type}: {found_file} ({path})")
            else:
                print(f"    没有找到相似文件")

def check_pdf_files():
    """检查PDF文件"""
    print(f"\n🔍 检查PDF文件...")
    
    # 查找所有PDF文件
    pdf_files = []
    for root, dirs, files in os.walk(BACKUP_ROOT):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(file)
    
    print(f"  备份中的PDF文件: {len(pdf_files)} 个")
    print(f"  前10个PDF文件:")
    for pdf in sorted(pdf_files)[:10]:
        print(f"    {pdf}")
    
    # 检查缺失的PDF文件
    print(f"\n🔍 缺失的PDF文件:")
    for missing in missing_files:
        if missing.lower().endswith('.pdf'):
            print(f"\n  {missing}:")
            # 尝试查找
            clean_name = re.sub(r'^\.+', '', missing)
            
            found = False
            for pdf in pdf_files:
                if pdf == clean_name:
                    print(f"    ✅ 找到清理后版本: {pdf}")
                    found = True
                    # 查找具体位置
                    for root, dirs, files in os.walk(BACKUP_ROOT):
                        if pdf in files:
                            print(f"      位置: {os.path.relpath(os.path.join(root, pdf), BACKUP_ROOT)}")
                            break
            
            if not found:
                print(f"    ❌ 未找到")

def main():
    print("=" * 60)
    print("缺失文件替代名查找")
    print("=" * 60)
    
    from collections import defaultdict
    
    print(f"🔍 检查 {len(missing_files)} 个缺失文件...")
    
    found_count = 0
    for missing in missing_files:
        print(f"\n{missing}:")
        results = find_similar_files(missing)
        
        if results:
            found_count += 1
            for match_type, found_file, path in results[:3]:  # 只显示前3个结果
                print(f"  {match_type}: {found_file} ({path})")
        else:
            print(f"  没有找到相似文件")
    
    print(f"\n📊 结果: 为 {found_count}/{len(missing_files)} 个文件找到相似文件")
    
    # 检查文件命名模式
    check_file_patterns()
    
    # 检查PDF文件
    check_pdf_files()

if __name__ == "__main__":
    main()