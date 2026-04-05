#!/usr/bin/env python3
"""
将COLD_REPORT CSV转换为FileBot报表配置
"""

import csv
import json
import sys
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

def csv_to_json_config(csv_file, output_file):
    """转换COLD_REPORT CSV为JSON配置"""
    
    reports = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        print(f"CSV字段 ({len(fieldnames)}): {fieldnames}")
        
        for i, row in enumerate(reader):
            try:
                # 调试：打印前几行
                if i < 3:
                    print(f"行 {i+1}: {row}")
                
                # 解析字段值
                report_id = safe_int(row.get('ID', 0))
                app_id = safe_int(row.get('APPID', 0))
                source_id = safe_int(row.get('SOURCEID', 0))
                form_id = safe_int(row.get('FORMID', 0))
                index_id = safe_int(row.get('INDEXID', 0))
                level_id = safe_int(row.get('LEVELID', 0))
                
                # 字符串字段
                name = safe_str(row.get('NAME', ''))
                comments = safe_str(row.get('COMMENTS', ''))
                index_pages = safe_str(row.get('INDEX_PAGES', ''))
                modify_date = safe_str(row.get('MODIFY_DATE', ''))
                
                # 跳过无效行
                if report_id == 0 or not name:
                    continue
                
                # 创建报表配置
                report_config = {
                    "id": report_id,
                    "name": name,
                    "description": comments if comments else f"Report {report_id}",
                    "app_id": app_id,
                    "form_id": form_id,
                    "index_id": index_id,
                    "level_id": level_id,
                    "source_id": source_id,
                    "index_pages": index_pages.lower() == 'y',
                    "modify_date": modify_date,
                    "field_references": f"cold_indexes_{report_id}"  # 引用对应的字段定义
                }
                
                # 添加可选字段（如果存在且非空）
                set_id = safe_int(row.get('SETID', 0))
                if set_id != 0:
                    report_config["set_id"] = set_id
                
                disposition_id = safe_int(row.get('DISPOSITIONID', 0))
                if disposition_id != 0:
                    report_config["disposition_id"] = disposition_id
                
                sample_id = safe_int(row.get('SAMPLEID', 0))
                if sample_id != 0:
                    report_config["sample_id"] = sample_id
                
                extern_id = safe_int(row.get('EXTERN_ID', 0))
                if extern_id != 0:
                    report_config["extern_id"] = extern_id
                
                recordclass_id = safe_int(row.get('RECORDCLASSID', 0))
                if recordclass_id != 0:
                    report_config["recordclass_id"] = recordclass_id
                
                textfields_id = safe_int(row.get('TEXTFIELDSID', 0))
                if textfields_id != 0:
                    report_config["textfields_id"] = textfields_id
                
                audit_id = safe_int(row.get('AUDITID', 0))
                if audit_id != 0:
                    report_config["audit_id"] = audit_id
                
                reports.append(report_config)
                
            except Exception as e:
                print(f"警告: 跳过行 {i+1}: {e}")
                continue
    
    if not reports:
        print("错误: 未生成任何报表配置")
        return False
    
    # 创建完整配置
    config = {
        "config_type": "smart_iadmin_reports",
        "version": "1.0",
        "created_from": Path(csv_file).name,
        "total_reports": len(reports),
        "reports": reports,
        "summary": {
            "by_app": {},
            "by_level": {}
        }
    }
    
    # 生成摘要统计
    for report in reports:
        app_id = report.get("app_id", 0)
        level_id = report.get("level_id", 0)
        
        if app_id not in config["summary"]["by_app"]:
            config["summary"]["by_app"][app_id] = 0
        config["summary"]["by_app"][app_id] += 1
        
        if level_id not in config["summary"]["by_level"]:
            config["summary"]["by_level"][level_id] = 0
        config["summary"]["by_level"][level_id] += 1
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 报表配置已生成: {output_file}")
    print(f"报表数: {len(reports)}")
    print(f"应用分布: {config['summary']['by_app']}")
    print(f"层级分布: {config['summary']['by_level']}")
    return True

def main():
    if len(sys.argv) != 3:
        print(f"用法: {sys.argv[0]} <COLD_REPORT.csv> <输出JSON文件>")
        print(f"示例: {sys.argv[0]} cold_report.csv cold_report_config.json")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not Path(csv_file).exists():
        print(f"错误: CSV文件不存在: {csv_file}")
        sys.exit(1)
    
    csv_to_json_config(csv_file, output_file)

if __name__ == '__main__':
    main()