#!/usr/bin/env python3
"""精确分析数据行（"-"开头）的字段结构"""

import re

def analyze_data_lines(file_path: str):
    """分析所有数据行（"-"开头）的字段结构"""
    
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    
    content = raw_data.decode('latin-1')
    lines = content.splitlines()
    
    # 找到所有"-"开头的行
    data_lines = []
    for i, line in enumerate(lines):
        if line.strip() and line[0] == '-':
            data_lines.append((i+1, line))
    
    print(f"找到 {len(data_lines)} 条数据行（'-'开头）")
    
    if not data_lines:
        return
    
    # 分析第一条数据行
    print("\n=== 第一条数据行详细分析 ===")
    line_num, first_line = data_lines[0]
    print(f"行 {line_num}: {repr(first_line)}")
    print(f"长度: {len(first_line)}")
    
    # 显示字符位置
    print("位置: ", end='')
    for i in range(min(100, len(first_line))):
        print(f"{i%10}", end='')
    print()
    
    print("字符: ", end='')
    for i in range(min(100, len(first_line))):
        char = first_line[i]
        if char == ' ':
            print(' ', end='')
        elif char == '\x00':
            print('0', end='')
        else:
            print(char, end='')
    print()
    
    # 分析列边界（空格到非空格的转换）
    print("\n列边界分析:")
    prev_char = ' '
    boundaries = []
    field_segments = []
    
    for i, char in enumerate(first_line):
        if prev_char == ' ' and char != ' ':
            boundaries.append(i)
            # 记录字段开始
        elif prev_char != ' ' and char == ' ':
            # 字段结束
            if boundaries:
                start = boundaries[-1]
                field_segments.append((start, i, first_line[start:i]))
        
        prev_char = char
    
    # 添加最后一个字段（如果行不以空格结束）
    if boundaries and boundaries[-1] < len(first_line) and first_line[boundaries[-1]] != ' ':
        start = boundaries[-1]
        field_segments.append((start, len(first_line), first_line[start:]))
    
    print(f"检测到的字段段: {len(field_segments)}")
    for i, (start, end, content) in enumerate(field_segments):
        clean_content = content.replace('\x00', '0').strip()
        print(f"  字段{i+1}: 位置 {start}-{end-1}, 长度 {end-start}, 内容: {repr(clean_content)}")
    
    # 分析所有数据行的结构一致性
    print("\n=== 所有数据行结构一致性分析 ===")
    
    # 收集所有数据行的字段位置
    all_boundaries_sets = []
    for line_num, line in data_lines:
        boundaries_set = set()
        prev_char = ' '
        for i, char in enumerate(line[:150]):  # 只分析前150个字符
            if prev_char == ' ' and char != ' ':
                boundaries_set.add(i)
            prev_char = char
        all_boundaries_sets.append(boundaries_set)
    
    # 找出共同的列边界
    if all_boundaries_sets:
        common_boundaries = set(all_boundaries_sets[0])
        for boundaries_set in all_boundaries_sets[1:]:
            common_boundaries.intersection_update(boundaries_set)
        
        print(f"共同列边界（在所有 {len(data_lines)} 行中都存在）:")
        sorted_common = sorted(common_boundaries)
        print(f"  {sorted_common}")
        
        # 显示前5行的字段提取
        print(f"\n前5行数据行的字段提取（使用共同边界）:")
        for i in range(min(5, len(data_lines))):
            line_num, line = data_lines[i]
            print(f"\n  行 {line_num}:")
            
            # 使用共同边界提取字段
            boundaries_list = sorted_common
            if boundaries_list:
                boundaries_list.append(len(line))
                for j in range(len(boundaries_list)-1):
                    start = boundaries_list[j]
                    end = boundaries_list[j+1]
                    field = line[start:end].rstrip()
                    clean_field = field.replace('\x00', '0').strip()
                    if clean_field:
                        print(f"    位置 {start}-{end-1}: {repr(clean_field)}")
    
    # 分析字段内容模式
    print("\n=== 字段内容模式分析 ===")
    
    # 使用第一行的边界分析所有行
    if boundaries:
        boundaries_list = sorted(boundaries)
        boundaries_list.append(len(first_line))
        
        field_patterns = []
        for j in range(len(boundaries_list)-1):
            start = boundaries_list[j]
            end = boundaries_list[j+1]
            
            # 收集这个位置在所有行中的值
            values = []
            for line_num, line in data_lines:
                if start < len(line):
                    field_end = min(end, len(line))
                    value = line[start:field_end].strip()
                    clean_value = value.replace('\x00', '').strip()
                    if clean_value:
                        values.append(clean_value)
            
            if values:
                unique_values = set(values)
                print(f"  位置 {start}-{end-1}:")
                print(f"    总出现: {len(values)} 次")
                print(f"    唯一值: {len(unique_values)} 个")
                
                # 尝试识别字段类型
                field_type = "unknown"
                sample = values[0]
                
                # 检查日期模式
                if re.match(r'\d{2}/\d{2}/\d{2}', sample):
                    field_type = "date"
                # 检查短代码（1-3字符）
                elif len(sample) <= 3 and sample.isalpha():
                    field_type = "code"
                # 检查姓名（字母，可能包含空格）
                elif re.match(r'^[A-Z\s]+$', sample):
                    if ' ' in sample:
                        field_type = "full_name"
                    else:
                        field_type = "name"
                # 检查数字
                elif re.match(r'^\d+$', sample):
                    field_type = "number"
                
                print(f"    类型推断: {field_type}")
                print(f"    示例值: {repr(sample)}")
                
                if len(unique_values) <= 10:
                    print(f"    所有值: {sorted(unique_values)}")
                else:
                    print(f"    前10个值: {sorted(list(unique_values))[:10]}")
                
                field_patterns.append({
                    'start': start,
                    'end': end-1,
                    'type': field_type,
                    'sample': sample,
                    'unique_count': len(unique_values)
                })
    
    return data_lines

def extract_business_data(file_path: str):
    """提取业务数据（人员记录）"""
    
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    
    content = raw_data.decode('latin-1')
    lines = content.splitlines()
    
    # 查找包含实际数据的数据行（不只是单独的"-"）
    data_records = []
    for i, line in enumerate(lines):
        if line.strip() and line[0] == '-' and len(line.strip()) > 1:
            # 这是一个包含数据的数据行
            data_records.append((i+1, line))
    
    print(f"\n=== 业务数据记录提取 ===")
    print(f"找到 {len(data_records)} 条包含数据的数据行")
    
    if not data_records:
        return
    
    # 分析第一条完整的数据记录
    line_num, record_line = data_records[0]
    print(f"\n第一条完整数据记录（行 {line_num}）:")
    print(f"原始: {repr(record_line)}")
    
    # 按空格分割（忽略空字符）
    parts = record_line.replace('\x00', ' ').split()
    print(f"按空格分割: {parts}")
    
    # 尝试提取字段
    if len(parts) >= 6:
        print("\n字段提取:")
        print(f"  记录标记: {parts[0]}")
        print(f"  日期: {parts[1]}")
        print(f"  状态: {parts[2]}")
        print(f"  缩写: {parts[3]}")
        print(f"  名: {parts[4]}")
        print(f"  姓: {parts[5]}")
    
    # 显示前5条记录
    print(f"\n前5条数据记录:")
    for i in range(min(5, len(data_records))):
        line_num, line = data_records[i]
        # 清理空字符并按空格分割
        clean_line = line.replace('\x00', ' ').strip()
        parts = clean_line.split()
        
        if len(parts) >= 6:
            print(f"  行{line_num}: {parts[1]} {parts[2]} {parts[3]} {parts[4]} {parts[5]}")
        else:
            print(f"  行{line_num}: {clean_line}")

if __name__ == "__main__":
    print("数据行（'-'开头）结构分析")
    print("=" * 60)
    
    data_lines = analyze_data_lines("PO.TXT")
    extract_business_data("PO.TXT")