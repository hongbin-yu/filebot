#!/usr/bin/env python3
"""
提取Smart iAdmin .script文件中的数据为CSV
使用纯Python标准库，无外部依赖
"""

import csv
import os
import re
import sys

def parse_values(values_str):
    """解析VALUES括号内的值列表"""
    values = []
    current = ''
    in_quotes = False
    escaped = False
    i = 0
    
    while i < len(values_str):
        char = values_str[i]
        
        if escaped:
            current += char
            escaped = False
        elif char == '\\':
            escaped = True
        elif char == "'" and not escaped:
            in_quotes = not in_quotes
            current += char
        elif char == ',' and not in_quotes:
            # 结束当前值
            val = current.strip()
            if val == 'NULL':
                values.append('')
            elif val.startswith("'") and val.endswith("'"):
                values.append(val[1:-1])
            else:
                values.append(val)
            current = ''
        else:
            current += char
        i += 1
    
    # 处理最后一个值
    if current:
        val = current.strip()
        if val == 'NULL':
            values.append('')
        elif val.startswith("'") and val.endswith("'"):
            values.append(val[1:-1])
        else:
            values.append(val)
    
    return values

def extract_table(input_file, table_name, output_dir):
    """提取特定表的所有数据"""
    rows = []
    
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line.startswith(f'INSERT INTO {table_name}'):
                continue
            
            # 匹配 VALUES(...);
            match = re.match(rf'INSERT INTO {table_name}\s+VALUES\s*\((.*)\);', line, re.IGNORECASE)
            if not match:
                continue
            
            values_str = match.group(1)
            values = parse_values(values_str)
            if values:
                rows.append(values)
    
    if not rows:
        print(f"警告: 表 {table_name} 无数据")
        return 0
    
    # 写入CSV
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{table_name.lower()}.csv")
    
    # 生成列名
    num_cols = len(rows[0])
    columns = [f"col{i+1}" for i in range(num_cols)]
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)
    
    print(f"导出 {table_name}: {len(rows)} 行 -> {output_file}")
    return len(rows)

def main():
    if len(sys.argv) != 4:
        print(f"用法: {sys.argv[0]} <script文件> <表名> <输出目录>")
        print(f"示例: {sys.argv[0]} smarti.script COLD_REPORT ./output")
        sys.exit(1)
    
    input_file = sys.argv[1]
    table_name = sys.argv[2].upper()
    output_dir = sys.argv[3]
    
    if not os.path.exists(input_file):
        print(f"错误: 文件不存在: {input_file}")
        sys.exit(1)
    
    extract_table(input_file, table_name, output_dir)

if __name__ == '__main__':
    main()