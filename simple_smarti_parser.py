#!/usr/bin/env python3
"""
简单Smart iAdmin .script文件解析器
逐行解析INSERT语句，生成CSV文件
"""

import argparse
import csv
import os
import re
import sys

def parse_insert_statement(line, table_name):
    """解析单行INSERT语句"""
    # 匹配 INSERT INTO table VALUES(...);
    pattern = rf'INSERT INTO {table_name}\s+VALUES\s*\((.*)\);'
    match = re.match(pattern, line, re.IGNORECASE)
    if not match:
        return None
    
    values_str = match.group(1)
    values = []
    current = ''
    in_quotes = False
    escaped = False
    
    for i, char in enumerate(values_str):
        if escaped:
            current += char
            escaped = False
        elif char == '\\':
            escaped = True
        elif char == "'" and not escaped:
            in_quotes = not in_quotes
            current += char
        elif char == ',' and not in_quotes:
            values.append(current.strip())
            current = ''
        else:
            current += char
    
    if current:
        values.append(current.strip())
    
    # 清理值：移除字符串值的引号
    cleaned = []
    for v in values:
        if v == 'NULL':
            cleaned.append('')
        elif v.startswith("'") and v.endswith("'"):
            cleaned.append(v[1:-1])
        else:
            cleaned.append(v)
    
    return cleaned

def main():
    parser = argparse.ArgumentParser(description='简单Smart iAdmin解析器')
    parser.add_argument('--input', required=True, help='输入.script文件')
    parser.add_argument('--output-dir', default='./output', help='输出目录')
    parser.add_argument('--table', help='要提取的表（默认：所有表）')
    
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 读取文件
    with open(args.input, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    # 收集所有表
    tables = {}
    for line in lines:
        if 'INSERT INTO' not in line:
            continue
        
        # 提取表名
        match = re.match(r'INSERT INTO ([A-Z_][A-Z0-9_]*)\s+VALUES', line, re.IGNORECASE)
        if not match:
            continue
        
        table = match.group(1).upper()
        if table not in tables:
            tables[table] = []
        
        # 解析值
        values = parse_insert_statement(line, table)
        if values:
            tables[table].append(values)
    
    print(f"找到 {len(tables)} 个表")
    
    # 如果指定了表，只处理该表
    if args.table:
        table_name = args.table.upper()
        if table_name in tables:
            tables = {table_name: tables[table_name]}
        else:
            print(f"错误：表 {args.table} 未找到")
            print(f"可用表：{sorted(tables.keys())}")
            return
    
    # 导出CSV
    for table, rows in sorted(tables.items()):
        if not rows:
            continue
        
        output_file = os.path.join(args.output_dir, f"{table.lower()}.csv")
        
        # 生成列名（使用通用列名）
        num_cols = len(rows[0])
        columns = [f"col{i+1}" for i in range(num_cols)]
        
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)
        
        print(f"导出 {table}: {len(rows)} 行 -> {output_file}")
    
    print(f"\n导出完成到: {args.output_dir}")

if __name__ == '__main__':
    main()