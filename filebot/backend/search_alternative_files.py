#!/usr/bin/env python3
"""
快速搜索缺失文件的替代文件
"""
import os
import re
from pathlib import Path

BACKUP_ROOT = Path("/home/hongb/.openclaw/workspace/filebot/backups/production_migration_20260321_175924")

# 缺失文件的基础名称（去掉smarti.xxx\前缀）
missing_base_files = [
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

def search_files():
    """搜索文件"""
    print("🔍 搜索缺失文件的替代版本...")
    
    all_files = []
    for root, dirs, files in os.walk(BACKUP_ROOT):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), BACKUP_ROOT)
            all_files.append((file, rel_path))
    
    print(f"  扫描到 {len(all_files)} 个文件")
    
    # 为每个缺失文件搜索
    for missing in missing_base_files:
        print(f"\n{missing}:")
        
        # 清理文件名：去掉开头的"...."
        clean_name = re.sub(r'^\.+', '', missing)
        
        # 提取可能的数字部分
        numbers = re.findall(r'\d+', missing)
        
        found = []
        
        for file_name, file_path in all_files:
            # 1. 完全匹配
            if file_name == missing:
                found.append(("完全匹配", file_path))
            # 2. 清理后匹配  
            elif file_name == clean_name:
                found.append(("清理后匹配", file_path))
            # 3. 包含相同数字序列
            elif numbers:
                file_numbers = re.findall(r'\d+', file_name)
                if numbers and file_numbers and numbers[-1] == file_numbers[-1]:
                    found.append(("数字匹配", file_path))
        
        if found:
            print(f"  找到 {len(found)} 个可能的匹配:")
            for match_type, path in found[:3]:  # 只显示前3个
                print(f"    {match_type}: {path}")
        else:
            print(f"  未找到任何匹配")
    
    # 特别检查PDF文件
    print(f"\n📄 特别检查: PDF文件")
    pdf_files = [(name, path) for name, path in all_files if name.lower().endswith('.pdf')]
    print(f"  备份中有 {len(pdf_files)} 个PDF文件")
    
    for name, path in sorted(pdf_files)[:10]:
        print(f"    {name} -> {path}")
    
    # 检查数字模式
    print(f"\n🔢 检查数字命名模式...")
    
    # 查找所有包含00000004或00000005的文件
    patterns = ["00000004", "00000005", "00000101", "00000104"]
    for pattern in patterns:
        matches = [(name, path) for name, path in all_files if pattern in name]
        if matches:
            print(f"  包含 '{pattern}' 的文件 ({len(matches)} 个):")
            for name, path in matches[:3]:
                print(f"    {name} -> {path}")

def check_pdf_availability():
    """检查PDF文件的可用性"""
    print(f"\n📊 PDF文件可用性分析...")
    
    # 备份中的PDF文件
    backup_pdfs = []
    for pdf_path in BACKUP_ROOT.rglob("*.pdf"):
        backup_pdfs.append(pdf_path.relative_to(BACKUP_ROOT))
    
    print(f"  备份中的PDF文件总数: {len(backup_pdfs)}")
    
    # 缺失的PDF文件
    missing_pdfs = [f for f in missing_base_files if f.lower().endswith('.pdf')]
    print(f"  缺失的PDF文件: {len(missing_pdfs)} 个")
    
    # 检查是否有类似的PDF文件
    print(f"\n🔍 寻找替代PDF文件...")
    
    for missing in missing_pdfs:
        # 提取数字部分
        numbers = re.findall(r'\d+', missing)
        if numbers:
            target_num = numbers[-1]  # 最后一个数字序列
            # 在备份中查找包含相同数字的PDF
            alternatives = []
            for pdf_path in backup_pdfs:
                if target_num in str(pdf_path):
                    alternatives.append(pdf_path)
            
            if alternatives:
                print(f"  {missing}: 找到 {len(alternatives)} 个包含数字'{target_num}'的PDF")
                for alt in alternatives[:2]:
                    print(f"    - {alt}")
            else:
                print(f"  {missing}: 未找到包含数字'{target_num}'的PDF")

def main():
    print("=" * 60)
    print("缺失文件替代搜索")
    print("=" * 60)
    
    search_files()
    check_pdf_availability()
    
    print("\n" + "=" * 60)
    print("结论")
    print("=" * 60)
    
    print("\n🔧 建议:")
    print("  1. 检查备份中是否有其他命名变体")
    print("  2. 考虑文件可能在其他位置（不同的备份目录）")
    print("  3. 如果确实找不到，标记为'文件缺失'")
    print("  4. 继续导出功能开发（不依赖实际文件）")

if __name__ == "__main__":
    main()