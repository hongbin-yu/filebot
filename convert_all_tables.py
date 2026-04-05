#!/usr/bin/env python3
"""
批量转换Smart iAdmin CSV文件为JSON配置
处理所有提取的表
"""

import csv
import json
import sys
import os
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
        try:
            return int(float(value_str))
        except:
            return default

def safe_str(value, default=''):
    """安全转换为字符串"""
    if value is None:
        return default
    value_str = str(value).strip()
    if value_str == '' or value_str.upper() == 'NULL':
        return default
    return value_str

def convert_table(csv_file, table_name):
    """根据表名转换CSV文件"""
    
    items = []
    csv_path = Path(csv_file)
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        print(f"  转换表 {table_name}: {len(fieldnames)} 列")
        
        for i, row in enumerate(reader):
            try:
                # 根据表名应用不同的转换逻辑
                if table_name.upper() == 'APP':
                    item = convert_app_row(row)
                elif table_name.upper() == 'DRAW':
                    item = convert_draw_row(row)
                elif table_name.upper() == 'FOLD':
                    item = convert_fold_row(row)
                elif table_name.upper() == 'DOC':
                    item = convert_doc_row(row)
                elif table_name.upper() == 'COLD_FIELDS':
                    item = convert_cold_fields_row(row)
                elif table_name.upper() == 'COLD_FORM_FIELDS':
                    item = convert_cold_form_fields_row(row)
                else:
                    # 通用转换
                    item = convert_generic_row(row, table_name)
                
                if item:
                    items.append(item)
                    
            except Exception as e:
                print(f"    警告: 跳过行 {i+1}: {e}")
                continue
    
    return items

def convert_app_row(row):
    """转换APP表行"""
    return {
        "id": safe_int(row.get('ID', 0)),
        "audit_id": safe_int(row.get('AUDITID', 0)),
        "name": safe_str(row.get('NAME', '')),
        "modify_date": safe_str(row.get('MODIFY_DATE', '')),
        "default_index_id": safe_int(row.get('DEFAULT_INDEXID', 0)),
        "comments": safe_str(row.get('COMMENTS', '')),
        "report_id": safe_int(row.get('REPORTID', 0)),
        "owner": safe_str(row.get('OWNER', '')),
        "template": safe_str(row.get('TEMPLATE', '')),
        "table": "app"
    }

def convert_draw_row(row):
    """转换DRAW表行"""
    return {
        "id": safe_int(row.get('ID', 0)),
        "app_id": safe_int(row.get('APPID', 0)),
        "name": safe_str(row.get('NAME', '')),
        "modify_date": safe_str(row.get('MODIFY_DATE', '')),
        "comments": safe_str(row.get('COMMENTS', '')),
        "audit_id": safe_int(row.get('AUDITID', 0)),
        "table": "draw"
    }

def convert_fold_row(row):
    """转换FOLD表行"""
    return {
        "id": safe_int(row.get('ID', 0)),
        "draw_id": safe_int(row.get('DRAWID', 0)),
        "name": safe_str(row.get('NAME', '')),
        "modify_date": safe_str(row.get('MODIFY_DATE', '')),
        "comments": safe_str(row.get('COMMENTS', '')),
        "audit_id": safe_int(row.get('AUDITID', 0)),
        "table": "fold"
    }

def convert_doc_row(row):
    """转换DOC表行"""
    return {
        "id": safe_int(row.get('ID', 0)),
        "fold_id": safe_int(row.get('FOLDID', 0)),
        "name": safe_str(row.get('NAME', '')),
        "modify_date": safe_str(row.get('MODIFY_DATE', '')),
        "comments": safe_str(row.get('COMMENTS', '')),
        "audit_id": safe_int(row.get('AUDITID', 0)),
        "page_count": safe_int(row.get('PAGECOUNT', 0)),
        "table": "doc"
    }

def convert_cold_fields_row(row):
    """转换COLD_FIELDS表行"""
    return {
        "id": safe_int(row.get('ID', 0)),
        "audit_id": safe_int(row.get('AUDITID', 0)),
        "field_type": safe_int(row.get('FIELDTYPE', 0)),
        "name": safe_str(row.get('NAME', '')),
        "comments": safe_str(row.get('COMMENTS', '')),
        "format": safe_str(row.get('FORMAT', '')),
        "table": "cold_fields"
    }

def convert_cold_form_fields_row(row):
    """转换COLD_FORM_FIELDS表行"""
    return {
        "id": safe_int(row.get('ID', 0)),
        "form_id": safe_int(row.get('FORMID', 0)),
        "field_id": safe_int(row.get('FIELDID', 0)),
        "table": "cold_form_fields"
    }

def convert_generic_row(row, table_name):
    """通用行转换"""
    item = {"table": table_name.lower()}
    
    for key, value in row.items():
        if value is None or str(value).strip() == '' or str(value).upper() == 'NULL':
            continue
        
        # 尝试推断类型
        value_str = str(value).strip()
        try:
            # 尝试整数
            if '.' not in value_str:
                item[key.lower()] = int(value_str)
            else:
                # 尝试浮点数
                item[key.lower()] = float(value_str)
        except ValueError:
            # 保留为字符串
            item[key.lower()] = value_str
    
    return item

def main():
    if len(sys.argv) != 3:
        print(f"用法: {sys.argv[0]} <CSV目录> <输出目录>")
        print(f"示例: {sys.argv[0]} hsqldb_export_with_headers converted_configs")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    if not os.path.exists(input_dir):
        print(f"错误: 输入目录不存在: {input_dir}")
        sys.exit(1)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 查找所有CSV文件
    csv_files = list(Path(input_dir).glob("*.csv"))
    if not csv_files:
        print(f"错误: 目录中无CSV文件: {input_dir}")
        sys.exit(1)
    
    print(f"找到 {len(csv_files)} 个CSV文件:")
    
    summary = {
        "total_files": len(csv_files),
        "converted_files": 0,
        "total_items": 0,
        "by_table": {}
    }
    
    all_configs = {}
    
    for csv_file in csv_files:
        table_name = csv_file.stem.upper()
        print(f"\n处理: {csv_file.name} -> {table_name}")
        
        items = convert_table(str(csv_file), table_name)
        
        if items:
            # 创建表配置
            config = {
                "table_name": table_name.lower(),
                "source_file": csv_file.name,
                "item_count": len(items),
                "items": items
            }
            
            # 保存为单独的文件
            output_file = Path(output_dir) / f"{table_name.lower()}_config.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # 添加到汇总
            all_configs[table_name.lower()] = config
            
            summary["converted_files"] += 1
            summary["total_items"] += len(items)
            summary["by_table"][table_name.lower()] = len(items)
            
            print(f"  成功: {len(items)} 个条目 -> {output_file}")
        else:
            print(f"  警告: 无有效条目")
    
    # 保存汇总文件
    summary_file = Path(output_dir) / "00_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # 保存完整配置
    all_configs_file = Path(output_dir) / "01_all_configs.json"
    with open(all_configs_file, 'w', encoding='utf-8') as f:
        json.dump(all_configs, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"✅ 批量转换完成!")
    print(f"输入目录: {input_dir}")
    print(f"输出目录: {output_dir}")
    print(f"处理文件: {summary['converted_files']}/{summary['total_files']}")
    print(f"总条目数: {summary['total_items']}")
    print(f"按表统计: {summary['by_table']}")
    print(f"汇总文件: {summary_file}")
    print(f"完整配置: {all_configs_file}")

if __name__ == '__main__':
    main()