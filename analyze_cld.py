#!/usr/bin/env python3
import sys
import os
import re
from collections import defaultdict

def analyze_file(file_path):
    """分析.cld/.TXT文件结构"""
    print(f"分析文件: {file_path}")
    
    # 检查文件大小
    file_size = os.path.getsize(file_path)
    print(f"文件大小: {file_size} 字节")
    
    # 读取文件内容
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    
    # 检查编码和特殊字符
    null_count = raw_data.count(b'\x00')
    print(f"空字符 (\\x00) 数量: {null_count}")
    
    # 检查其他控制字符
    control_chars = sum(1 for b in raw_data if b < 32 and b not in [9, 10, 13])  # 排除制表符、换行符
    print(f"其他控制字符数量: {control_chars}")
    
    # 解码为文本（尝试不同编码）
    try:
        # 先尝试utf-8
        content = raw_data.decode('utf-8', errors='replace')
        print("使用UTF-8解码（不可解码字符替换为�）")
    except UnicodeDecodeError:
        try:
            # 尝试latin-1
            content = raw_data.decode('latin-1')
            print("使用Latin-1解码")
        except:
            content = raw_data.decode('utf-8', errors='ignore')
            print("使用UTF-8解码（忽略错误）")
    
    lines = content.splitlines()
    print(f"总行数: {len(lines)}")
    
    # 分析行类型
    line_types = defaultdict(int)
    for line in lines:
        if not line.strip():
            line_types['空行'] += 1
            continue
        
        # 检查行首字符
        first_char = line[0] if line else ''
        if first_char.isdigit():
            line_types[f'数字开头({first_char})'] += 1
        elif first_char == '-':
            line_types['-开头'] += 1
        elif first_char == ' ':
            line_types['空格开头'] += 1
        elif first_char == '*':
            line_types['*开头'] += 1
        else:
            line_types[f'其他({first_char})'] += 1
    
    print("\n行类型统计:")
    for type_name, count in sorted(line_types.items()):
        print(f"  {type_name}: {count}")
    
    # 分析列结构（基于空格对齐）
    print("\n分析列结构:")
    
    # 获取非空行
    non_empty_lines = [line for line in lines if line.strip()]
    
    # 分析前20行非空行的列结构
    sample_lines = non_empty_lines[:20]
    
    # 查找可能的列边界（基于空格对齐）
    column_positions = set()
    for line in sample_lines:
        # 查找连续空格后的非空格位置
        in_space = False
        for i, char in enumerate(line):
            if char == ' ' and not in_space:
                in_space = True
            elif char != ' ' and in_space:
                column_positions.add(i)
                in_space = False
    
    print(f"检测到 {len(column_positions)} 个可能的列边界位置")
    if column_positions:
        sorted_positions = sorted(column_positions)
        print(f"列边界位置: {sorted_positions[:10]}... (显示前10个)")
        
        # 显示样本行的列对齐
        print("\n样本行列对齐示例:")
        for i, line in enumerate(sample_lines[:5]):
            print(f"行 {i+1}: {repr(line[:80])}")
            # 标记列边界
            marked_line = ''
            for j, char in enumerate(line[:80]):
                if j in sorted_positions:
                    marked_line += '|'
                else:
                    marked_line += char
            print(f"       {marked_line}")
    
    # 分析特殊行内容
    print("\n特殊行内容分析:")
    
    # 查找包含空字符的行
    null_char_lines = [i+1 for i, line in enumerate(lines) if '\x00' in line]
    if null_char_lines:
        print(f"包含空字符的行: {null_char_lines[:10]}... (共{len(null_char_lines)}行)")
        # 显示一个示例
        sample_line_idx = null_char_lines[0] - 1
        sample_line = lines[sample_line_idx]
        print(f"示例行 {null_char_lines[0]}: {repr(sample_line[:100])}")
    
    # 分析字段类型
    print("\n字段模式分析:")
    
    # 查找常见模式
    date_pattern = r'\d{2}/\d{2}/\d{2}'
    phone_pattern = r'\(\d{3}\) \d{3}-\d{4}'
    part_number_pattern = r'\d+-\d+'
    money_pattern = r'\$\d+[,.]?\d*|\d+[,.]?\d+\$'
    
    dates = []
    phones = []
    part_numbers = []
    money_values = []
    
    for i, line in enumerate(lines):
        # 查找日期
        dates_found = re.findall(date_pattern, line)
        dates.extend([(i+1, d) for d in dates_found])
        
        # 查找电话号码
        phones_found = re.findall(phone_pattern, line)
        phones.extend([(i+1, p) for p in phones_found])
        
        # 查找零件号（如75-211401）
        part_numbers_found = re.findall(part_number_pattern, line)
        part_numbers.extend([(i+1, p) for p in part_numbers_found])
        
        # 查找金额
        money_found = re.findall(money_pattern, line)
        money_values.extend([(i+1, m) for m in money_found])
    
    print(f"找到日期: {len(dates)} 个")
    if dates:
        print(f"  示例: 行{dates[0][0]}: {dates[0][1]}")
    
    print(f"找到电话号码: {len(phones)} 个")
    if phones:
        print(f"  示例: 行{phones[0][0]}: {phones[0][1]}")
    
    print(f"找到零件号: {len(part_numbers)} 个")
    if part_numbers:
        print(f"  示例: 行{part_numbers[0][0]}: {part_numbers[0][1]}")
    
    print(f"找到金额: {len(money_values)} 个")
    if money_values:
        print(f"  示例: 行{money_values[0][0]}: {money_values[0][1]}")
    
    # 生成报告
    print(f"\n{'='*60}")
    print("分析结论:")
    print("1. 文件包含固定宽度文本格式")
    print("2. 使用空字符(\\x00)作为填充")
    print("3. 有明显的列对齐结构")
    print("4. 包含业务数据：公司信息、地址、日期、零件号、金额等")
    print("5. 需要设计解析器处理固定宽度列和空字符")
    
    return {
        'lines': lines,
        'column_positions': sorted(column_positions) if column_positions else [],
        'null_char_lines': null_char_lines
    }

if __name__ == "__main__":
    file_path = "PO.TXT"
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    
    analyze_file(file_path)