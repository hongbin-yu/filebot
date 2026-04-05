#!/usr/bin/env python3
"""
简单提取Smart iAdmin数据 - 使用字符串操作，非正则表达式
"""

import csv
import os
import sys

def parse_insert_line(line, table_name):
    """解析INSERT语句行"""
    if not line.strip().upper().startswith(f'INSERT INTO {table_name.upper()}'):
        return None
    
    # 找到 VALUES( 的位置
    values_keyword = 'VALUES('
    idx = line.upper().find(values_keyword)
    if idx == -1:
        # 尝试 VALUES ( 有空格的情况
        values_keyword = 'VALUES ('
        idx = line.upper().find(values_keyword)
        if idx == -1:
            return None
    
    # 提取括号内的内容
    start = idx + len(values_keyword) - 1  # 包含左括号
    # 找到匹配的右括号（从末尾开始找）
    paren_count = 0
    end_pos = -1
    for i in range(start, len(line)):
        if line[i] == '(':
            paren_count += 1
        elif line[i] == ')':
            paren_count -= 1
            if paren_count == 0:
                end_pos = i
                break
    
    if end_pos == -1:
        return None
    
    values_str = line[start+1:end_pos]  # 去掉左括号
    
    # 简单分割值（假设值中不包含逗号，除了字符串内的）
    values = []
    current = ''
    in_quotes = False
    escaped = False
    
    for char in values_str:
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
                # 尝试转换为数字
                try:
                    if '.' in val:
                        values.append(float(val))
                    else:
                        values.append(int(val))
                except ValueError:
                    values.append(val)
            current = ''
        else:
            current += char
    
    # 添加最后一个值
    if current:
        val = current.strip()
        if val == 'NULL':
            values.append('')
        elif val.startswith("'") and val.endswith("'"):
            values.append(val[1:-1])
        else:
            try:
                if '.' in val:
                    values.append(float(val))
                else:
                    values.append(int(val))
            except ValueError:
                values.append(val)
    
    return values

def main():
    if len(sys.argv) != 4:
        print(f"用法: {sys.argv[0]} <script文件> <表名> <输出目录>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    table_name = sys.argv[2]
    output_dir = sys.argv[3]
    
    rows = []
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            values = parse_insert_line(line, table_name)
            if values:
                rows.append(values)
    
    if not rows:
        print(f"表 {table_name} 无数据")
        sys.exit(0)
    
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

if __name__ == '__main__':
    main()