#!/usr/bin/env python3
"""
版本2：将COLD_INDEXES CSV转换为FileBot JSON配置
更健壮的类型转换和错误处理
"""

import csv
import json
import sys
import re
from pathlib import Path

def safe_int(value, default=0):
    """安全转换为整数"""
    if not value:
        return default
    value_str = str(value).strip()
    if value_str == '' or value_str.upper() == 'NULL':
        return default
    try:
        return int(value_str)
    except ValueError:
        # 尝试处理可能的小数或格式问题
        try:
            return int(float(value_str))
        except:
            return default

def map_dateformat_to_pattern(dateformat):
    """将DATEFORMAT值映射为验证模式"""
    if not dateformat or dateformat.upper() == 'NULL' or dateformat.strip() == '':
        return None
    
    dateformat = dateformat.strip().lower()
    
    # 常见模式映射
    pattern_mappings = {
        'mdy': r'\d{1,2}/\d{1,2}/\d{2,4}',  # 月/日/年
        'yyyymmdd': r'\d{4}\d{2}\d{2}',     # 年月日
        'a%': r'^[a-zA-Z].*',              # 字母开头
        'nnnnnnn': r'^\d{7}$',             # 7位数字
        'nnnnnnnn': r'^\d{8}$',            # 8位数字
        'xxxxxxxxx': r'^\w{9}$',           # 9位字母数字
        'nnnn': r'^\d{4}$',                # 4位数字
        'nnn': r'^\d{3}$',                 # 3位数字
        'nn': r'^\d{2}$',                  # 2位数字
        'n': r'^\d$',                      # 1位数字
    }
    
    # 检查精确匹配
    if dateformat in pattern_mappings:
        return pattern_mappings[dateformat]
    
    # 检查是否为日期格式模式
    if re.match(r'^[mdy]+$', dateformat):
        # 简单的日期格式，返回通用日期模式
        return r'\d{1,2}/\d{1,2}/\d{2,4}'
    
    # 检查是否为数字模式 (n重复)
    if re.match(r'^n+$', dateformat):
        length = len(dateformat)
        return f'^\\d{{{length}}}$'
    
    # 检查是否为字母模式 (a重复或包含%)
    if '%' in dateformat:
        # SQL LIKE模式转换为正则表达式
        pattern = dateformat.replace('%', '.*').replace('_', '.')
        return f'^{pattern}$'
    
    # 默认返回原始值作为模式
    return f'^{re.escape(dateformat)}$'

def csv_to_json_config(csv_file, output_file):
    """转换COLD_INDEXES CSV为JSON配置"""
    
    field_definitions = []
    report_index_map = {}  # 按ID分组字段
    error_count = 0
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        # 首先读取标题行
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        print(f"CSV字段: {fieldnames}")
        
        for i, row in enumerate(reader):
            try:
                # 调试：打印前几行
                if i < 5:
                    print(f"行 {i+1}: {row}")
                
                # 使用安全转换函数
                id_val = safe_int(row.get('ID', 0))
                levelid = safe_int(row.get('LEVELID', 0))
                coln = safe_int(row.get('COLN', 0))
                length = safe_int(row.get('LENGTH', 0))
                left_offset = safe_int(row.get('LEFT_OFFSET', 0))
                
                # 字符串字段
                literal = row.get('LITERAL', '').strip()
                sample = row.get('SAMPLE', '').strip()
                dateformat = row.get('DATEFORMAT', '').strip()
                lefttrim = row.get('LEFTTRIM', '').strip()
                
                # 跳过无效行
                if coln <= 0 or length <= 0:
                    continue
                
                # 生成字段名
                if literal and literal != 'NULL' and literal != ' ':
                    # 清理字面值作为字段名
                    clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', literal.lower())
                    field_name = f"{clean_name}_{coln}"
                else:
                    field_name = f"field_{id_val}_{levelid}_{coln}"
                
                # 创建字段定义
                field_def = {
                    "name": field_name,
                    "description": f"Index field for report {id_val}, level {levelid}, column {coln}",
                    "start_pos": coln - 1,  # FileBot使用0-based，COLD_INDEXES使用1-based
                    "length": length,
                    "field_type": "text",  # 默认类型
                    "required": True,
                    "validation": {}
                }
                
                # 添加偏移量（如果存在）
                if left_offset != 0:
                    field_def["offset"] = left_offset
                
                # 添加字面值（如果存在且有意义）
                if literal and literal != 'NULL' and literal.strip() and literal != ' ':
                    field_def["literal"] = literal
                
                # 添加样本值（如果存在）
                if sample and sample != 'NULL' and sample.strip():
                    field_def["sample_value"] = sample
                
                # 处理验证模式
                validation_rules = {}
                
                # 1. 从DATEFORMAT推导模式
                if dateformat and dateformat != 'NULL':
                    pattern = map_dateformat_to_pattern(dateformat)
                    if pattern:
                        validation_rules["pattern"] = pattern
                    
                    # 如果是日期格式，设置字段类型
                    date_like = dateformat.lower()
                    if date_like in ['mdy', 'yyyymmdd'] or 'm' in date_like or 'y' in date_like:
                        field_def["field_type"] = "date"
                        field_def["date_format"] = dateformat
                
                # 2. 从左修剪标志推导
                if lefttrim and lefttrim != 'NULL':
                    if lefttrim.lower() == 'y':
                        validation_rules["trim_left"] = True
                
                # 3. 从字面值推导简单模式
                if literal and len(literal) == 1:
                    if literal in ['n', 'N']:
                        validation_rules["pattern"] = r'^\d$'
                    elif literal in ['y', 'Y']:
                        validation_rules["pattern"] = r'^[YyNn]$'
                
                # 添加验证规则
                if validation_rules:
                    field_def["validation"] = validation_rules
                
                field_definitions.append(field_def)
                
                # 按报告ID分组
                if id_val not in report_index_map:
                    report_index_map[id_val] = []
                report_index_map[id_val].append(field_def)
                
            except Exception as e:
                error_count += 1
                print(f"警告: 跳过行 {i+1}: {e}")
                print(f"  行数据: {row}")
                continue
    
    if not field_definitions:
        print("错误: 未生成任何字段定义")
        return False
    
    # 创建完整配置
    config = {
        "app_name": "Smart iAdmin Migration",
        "app_code": "SMARTI",
        "template_name": "cold_indexes_template.jasper",
        "file_extension": ".cld",
        "encoding": "latin-1",
        "description": f"从Smart iAdmin COLD_INDEXES迁移的配置 ({len(field_definitions)} 个字段)",
        "version": "2.0",
        "created_from": Path(csv_file).name,
        "field_definitions": field_definitions,
        "report_indexes": {
            str(report_id): len(fields) for report_id, fields in report_index_map.items()
        },
        "error_count": error_count
    }
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 配置已生成: {output_file}")
    print(f"字段数: {len(field_definitions)}")
    print(f"错误行数: {error_count}")
    print(f"报表索引分布: {config['report_indexes']}")
    return True

def main():
    if len(sys.argv) != 3:
        print(f"用法: {sys.argv[0]} <COLD_INDEXES.csv> <输出JSON文件>")
        print(f"示例: {sys.argv[0]} cold_indexes.csv cold_indexes_config_v2.json")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not Path(csv_file).exists():
        print(f"错误: CSV文件不存在: {csv_file}")
        sys.exit(1)
    
    csv_to_json_config(csv_file, output_file)

if __name__ == '__main__':
    main()