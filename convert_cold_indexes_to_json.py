#!/usr/bin/env python3
"""
将COLD_INDEXES CSV转换为FileBot JSON配置
"""

import csv
import json
import sys
from pathlib import Path

def csv_to_json_config(csv_file, output_file):
    """转换COLD_INDEXES CSV为JSON配置"""
    
    field_definitions = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for i, row in enumerate(reader):
            try:
                # 解析字段值
                id_val = int(row.get('ID', 0))
                levelid = int(row.get('LEVELID', 0))
                coln = int(row.get('COLN', 0))
                length = int(row.get('LENGTH', 0))
                left_offset = int(row.get('LEFT_OFFSET', 0)) if row.get('LEFT_OFFSET') else 0
                literal = row.get('LITERAL', '').strip()
                sample = row.get('SAMPLE', '').strip()
                dateformat = row.get('DATEFORMAT', '').strip()
                
                # 跳过无效行
                if coln <= 0 or length <= 0:
                    continue
                
                # 创建字段定义
                field_def = {
                    "name": f"field_{id_val}_{levelid}_{coln}",
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
                
                # 添加字面值（如果存在）
                if literal and literal.strip() and literal.strip() != 'NULL':
                    field_def["literal"] = literal
                
                # 添加样本值（如果存在）
                if sample and sample.strip() and sample.strip() != 'NULL':
                    field_def["sample_value"] = sample
                
                # 添加日期格式（如果存在）
                if dateformat and dateformat.strip() and dateformat.strip() != 'NULL':
                    field_def["date_format"] = dateformat
                    field_def["field_type"] = "date"
                
                # 添加验证模式（基于字面值或样本）
                if literal and len(literal) > 0 and literal != ' ':
                    # 如果字面值是单个字符，可能是验证模式
                    if len(literal) == 1 and literal in ['n', 'y', 'Y', 'N']:
                        field_def["validation"]["pattern"] = f"^[{literal}]$"
                    elif '%' in literal:
                        field_def["validation"]["pattern"] = literal.replace('%', '.*')
                
                field_definitions.append(field_def)
                
            except (ValueError, KeyError) as e:
                print(f"警告: 跳过行 {i+1}: {e}")
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
        "version": "1.0",
        "created_from": Path(csv_file).name,
        "field_definitions": field_definitions
    }
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 配置已生成: {output_file}")
    print(f"字段数: {len(field_definitions)}")
    return True

def main():
    if len(sys.argv) != 3:
        print(f"用法: {sys.argv[0]} <COLD_INDEXES.csv> <输出JSON文件>")
        print(f"示例: {sys.argv[0]} cold_indexes.csv cold_indexes_config.json")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not Path(csv_file).exists():
        print(f"错误: CSV文件不存在: {csv_file}")
        sys.exit(1)
    
    csv_to_json_config(csv_file, output_file)

if __name__ == '__main__':
    main()