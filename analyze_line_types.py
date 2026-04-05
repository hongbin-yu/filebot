#!/usr/bin/env python3
"""分析.cld文件中的行类型和结构"""

import re
from collections import defaultdict

def analyze_line_types(file_path: str):
    """分析文件中的行类型"""
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    
    content = raw_data.decode('latin-1')
    lines = content.splitlines()
    
    print(f"文件: {file_path}")
    print(f"总行数: {len(lines)}")
    print(f"非空行: {len([l for l in lines if l.strip()])}")
    
    # 按行首字符分类
    line_types = defaultdict(list)
    for i, line in enumerate(lines):
        if not line.strip():
            continue
            
        first_char = line[0] if line else ''
        line_types[first_char].append((i+1, line))
    
    print(f"\n行类型统计（按首字符）:")
    for char, type_lines in sorted(line_types.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  '{char}': {len(type_lines):3} 行")
    
    # 分析主要行类型
    print(f"\n{'='*60}")
    print("主要行类型分析:")
    
    # 1. 类型'-'行（数据行）
    print("\n1. 类型'-'行（数据行）:")
    dash_lines = line_types.get('-', [])
    if dash_lines:
        print(f"  共 {len(dash_lines)} 行")
        # 显示前3行
        for i in range(min(3, len(dash_lines))):
            line_num, line = dash_lines[i]
            print(f"  行{line_num}: {repr(line[:80])}")
        
        # 分析列结构
        if dash_lines:
            sample_line = dash_lines[0][1]
            print(f"  样本行列边界分析:")
            prev_char = ' '
            boundaries = []
            for j, char in enumerate(sample_line[:100]):
                if prev_char == ' ' and char != ' ':
                    boundaries.append(j)
                prev_char = char
            
            print(f"    列边界: {boundaries}")
            
            # 提取字段
            if boundaries:
                boundaries.append(len(sample_line))
                print(f"    字段提取:")
                for k in range(min(6, len(boundaries)-1)):
                    start = boundaries[k]
                    end = boundaries[k+1]
                    field = sample_line[start:end].rstrip()
                    print(f"      字段{k+1}({start}-{end-1}): {repr(field)}")
    
    # 2. 类型'0'行
    print("\n2. 类型'0'行:")
    zero_lines = line_types.get('0', [])
    if zero_lines:
        print(f"  共 {len(zero_lines)} 行")
        # 显示不同类型的'0'行
        zero_subtypes = defaultdict(list)
        for line_num, line in zero_lines:
            # 根据内容分类
            if len(line.strip()) == 1:  # 只有'0'
                zero_subtypes['only_0'].append((line_num, line))
            elif 'PARKER' in line:
                zero_subtypes['parker'].append((line_num, line))
            elif 'DESENCO' in line:
                zero_subtypes['desenco'].append((line_num, line))
            else:
                zero_subtypes['other'].append((line_num, line))
        
        for subtype, sublines in zero_subtypes.items():
            print(f"    {subtype}: {len(sublines)} 行")
            if sublines and subtype != 'other':
                line_num, line = sublines[0]
                print(f"      示例行{line_num}: {repr(line[:80])}")
    
    # 3. 类型'1'行
    print("\n3. 类型'1'行:")
    one_lines = line_types.get('1', [])
    if one_lines:
        print(f"  共 {len(one_lines)} 行")
        # 显示前2行
        for i in range(min(2, len(one_lines))):
            line_num, line = one_lines[i]
            print(f"  行{line_num}: {repr(line[:80])}")
    
    # 4. 其他常见类型
    print("\n4. 其他常见行类型:")
    common_types = ['P', 'F', 'S', 'T', 'A', 'R', 'M']
    for char in common_types:
        if char in line_types:
            lines_list = line_types[char]
            print(f"  '{char}': {len(lines_list):3} 行")
            if lines_list:
                line_num, line = lines_list[0]
                print(f"    示例行{line_num}: {repr(line[:80])}")
    
    # 分析整个文件的结构模式
    print(f"\n{'='*60}")
    print("文件结构模式分析:")
    
    # 查找重复模式
    patterns = []
    current_pattern = []
    prev_type = None
    
    for i, line in enumerate(lines[:100]):  # 只分析前100行
        if not line.strip():
            line_type = '空行'
        else:
            line_type = line[0] if line[0] != ' ' else '空格开头'
        
        if line_type == prev_type:
            current_pattern.append(line_type)
        else:
            if current_pattern:
                pattern_str = f"{prev_type}×{len(current_pattern)}"
                patterns.append(pattern_str)
            current_pattern = [line_type]
            prev_type = line_type
    
    if current_pattern:
        pattern_str = f"{prev_type}×{len(current_pattern)}"
        patterns.append(pattern_str)
    
    print(f"前100行模式序列:")
    print("  " + " → ".join(patterns[:20]))
    
    # 查找数据块
    print(f"\n数据块识别:")
    data_blocks = []
    in_data_block = False
    block_start = 0
    
    for i, line in enumerate(lines):
        if not line.strip():
            continue
            
        first_char = line[0] if line else ''
        
        if first_char == '-' and not in_data_block:
            # 开始数据块
            in_data_block = True
            block_start = i
        elif first_char != '-' and in_data_block:
            # 结束数据块
            in_data_block = False
            block_end = i
            data_blocks.append((block_start+1, block_end+1))
    
    if in_data_block:
        data_blocks.append((block_start+1, len(lines)+1))
    
    print(f"  找到 {len(data_blocks)} 个数据块（以'-'开头的连续行）")
    if data_blocks:
        for i, (start, end) in enumerate(data_blocks[:3]):
            print(f"    块{i+1}: 行{start}-{end-1} ({end-start}行)")
    
    return line_types

if __name__ == "__main__":
    analyze_line_types("PO.TXT")