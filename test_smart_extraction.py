#!/usr/bin/env python3
"""
测试智能配置的提取准确性
"""

import json
import re

def test_smart_config():
    """测试智能配置"""
    print("测试智能配置提取准确性")
    print("=" * 60)
    
    # 加载配置
    with open("smart_po_config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    print(f"应用: {config['app_name']} ({config['app_code']})")
    print(f"字段数: {len(config['field_definitions'])}")
    print(f"段数: {len(config['segments'])}")
    
    # 加载PO.TXT文件
    with open("PO.TXT", "rb") as f:
        raw_data = f.read()
    
    content = raw_data.decode("latin-1")
    lines = content.splitlines()
    
    print(f"\n文件行数: {len(lines)}")
    
    # 获取字段定义
    field_defs = config['field_definitions']
    
    # 按段类型分组字段
    fields_by_segment = {}
    for field in field_defs:
        seg_type = field['segment_type']
        if seg_type not in fields_by_segment:
            fields_by_segment[seg_type] = []
        fields_by_segment[seg_type].append(field)
    
    print(f"\n按段类型分组的字段:")
    for seg_type, fields in fields_by_segment.items():
        print(f"  {seg_type}: {len(fields)} 个字段")
        for field in fields:
            print(f"    {field['name']}: 位置 {field['start_pos']}-{field['start_pos']+field['length']-1}")
    
    # 测试数据记录字段提取
    print(f"\n{'='*60}")
    print("测试数据记录字段提取")
    print(f"{'='*60}")
    
    data_record_fields = fields_by_segment.get('data_record', [])
    
    if data_record_fields:
        print(f"数据记录字段: {[f['name'] for f in data_record_fields]}")
        
        # 找到数据记录行
        data_lines = []
        for i, line in enumerate(lines):
            if line.strip() and line[0] == '-' and len(line.strip()) > 1:
                data_lines.append((i+1, line))
        
        print(f"找到 {len(data_lines)} 条数据记录行")
        
        if data_lines:
            # 测试前5条记录
            for i in range(min(5, len(data_lines))):
                line_num, line = data_lines[i]
                print(f"\n记录 {i+1} (行{line_num}):")
                print(f"  原始: {repr(line[:80])}")
                
                # 提取每个字段
                for field in data_record_fields:
                    start = field['start_pos']
                    length = field['length']
                    
                    if start < len(line):
                        end = min(start + length, len(line))
                        value = line[start:end].strip()
                        value = value.replace('\x00', '')
                        
                        if value:
                            print(f"  {field['name']}: {repr(value)} (位置 {start}-{end-1})")
                        else:
                            print(f"  {field['name']}: 空值 (位置 {start}-{end-1})")
            
            # 验证字段位置准确性
            print(f"\n{'='*60}")
            print("字段位置准确性验证")
            print(f"{'='*60}")
            
            # 分析第一行数据记录的精确结构
            line_num, sample_line = data_lines[0]
            print(f"分析第一行数据记录 (行{line_num}):")
            print(f"原始行: {repr(sample_line)}")
            
            # 显示字符位置
            print("位置: ", end='')
            for i in range(min(100, len(sample_line))):
                print(f"{i%10}", end='')
            print()
            
            print("字符: ", end='')
            for i in range(min(100, len(sample_line))):
                char = sample_line[i]
                if char == ' ':
                    print(' ', end='')
                elif char == '\x00':
                    print('0', end='')
                else:
                    print(char, end='')
            print()
            
            # 分析实际的字段边界
            print(f"\n实际字段边界分析:")
            prev_char = ' '
            boundaries = []
            
            for i, char in enumerate(sample_line[:100]):
                if prev_char == ' ' and char != ' ':
                    boundaries.append(i)
                prev_char = char
            
            print(f"检测到的字段边界: {boundaries}")
            
            # 提取基于边界的字段
            if boundaries:
                boundaries.append(len(sample_line))
                for j in range(len(boundaries)-1):
                    start = boundaries[j]
                    end = boundaries[j+1]
                    field_content = sample_line[start:end].rstrip()
                    clean_content = field_content.replace('\x00', '')
                    
                    if clean_content:
                        print(f"  字段{j+1}: 位置 {start}-{end-1}, 内容: {repr(clean_content)}")
            
            # 验证配置中的字段位置
            print(f"\n配置字段位置验证:")
            for field in data_record_fields:
                name = field['name']
                config_start = field['start_pos']
                config_length = field['length']
                config_end = config_start + config_length
                
                # 提取配置位置的值
                if config_start < len(sample_line):
                    end = min(config_end, len(sample_line))
                    config_value = sample_line[config_start:end].strip()
                    config_value = config_value.replace('\x00', '')
                    
                    # 查找实际值
                    actual_value = ""
                    for j in range(len(boundaries)-1):
                        start = boundaries[j]
                        end = boundaries[j+1]
                        if start <= config_start < end:
                            actual_value = sample_line[start:end].rstrip()
                            actual_value = actual_value.replace('\x00', '')
                            break
                    
                    print(f"  {name}:")
                    print(f"    配置位置: {config_start}-{config_end-1} (长度 {config_length})")
                    print(f"    配置值: {repr(config_value)}")
                    print(f"    实际值: {repr(actual_value)}")
                    print(f"    匹配: {'是' if config_value == actual_value else '否'}")
    
    # 测试标题字段提取
    print(f"\n{'='*60}")
    print("测试标题字段提取")
    print(f"{'='*60}")
    
    header_fields = fields_by_segment.get('header', [])
    
    if header_fields:
        print(f"标题字段: {[f['name'] for f in header_fields]}")
        
        # 找到标题行
        header_lines = []
        for i, line in enumerate(lines[:50]):  # 只检查前50行
            if line.strip() and (line[0] in '01' or 'PARKER HANNIFIN' in line):
                header_lines.append((i+1, line))
        
        print(f"找到 {len(header_lines)} 条标题行")
        
        if header_lines:
            for field in header_fields:
                name = field['name']
                keywords = field['keywords']
                
                print(f"\n字段: {name}")
                print(f"  关键词: {keywords}")
                
                # 查找包含关键词的行
                for line_num, line in header_lines:
                    for keyword in keywords:
                        if keyword in line:
                            start = line.find(keyword)
                            if start != -1:
                                end = start + len(keyword)
                                value = line[start:end].strip()
                                print(f"  行{line_num}: 找到关键词 '{keyword}', 位置 {start}-{end-1}")
                                print(f"    值: {repr(value)}")
                                break


def create_optimized_config():
    """创建优化后的配置（基于精确分析）"""
    print(f"\n{'='*60}")
    print("创建优化后的配置")
    print(f"{'='*60}")
    
    # 精确的字段定义（基于PO.TXT分析）
    optimized_config = {
        "app_name": "Purchase Order",
        "app_code": "PO",
        "template_name": "pcl_form.jasper",
        "file_extension": ".cld",
        "encoding": "latin-1",
        "description": "优化后的采购订单配置 - 基于精确字段位置分析",
        "field_definitions": [
            {
                "name": "record_type",
                "description": "记录类型标记",
                "segment_type": "data_record",
                "keywords": ["-"],
                "start_pos": 0,
                "length": 3,  # 包括空格填充
                "field_type": "code",
                "required": True,
                "validation_pattern": "^-$",
                "sample_value": "-"
            },
            {
                "name": "date",
                "description": "日期 (MM/DD/YY)",
                "segment_type": "data_record",
                "keywords": ["04/09/12", "05/02/12", "01/26/12"],
                "start_pos": 3,
                "length": 12,  # MM/DD/YY + 空格填充
                "field_type": "date",
                "required": True,
                "validation_pattern": r"\d{2}/\d{2}/\d{2}",
                "sample_value": "04/09/12"
            },
            {
                "name": "status",
                "description": "状态代码",
                "segment_type": "data_record",
                "keywords": ["E", "I", "O"],
                "start_pos": 15,
                "length": 6,  # 代码 + 空格填充
                "field_type": "code",
                "required": True,
                "validation_pattern": "^[EIO]$",
                "sample_value": "E"
            },
            {
                "name": "initials",
                "description": "人员缩写",
                "segment_type": "data_record",
                "keywords": ["BD", "DL", "PH", "JM", "WO", "JD"],
                "start_pos": 21,
                "length": 5,  # 缩写 + 空格填充
                "field_type": "code",
                "required": True,
                "validation_pattern": "^[A-Z]{2}$",
                "sample_value": "BD"
            },
            {
                "name": "first_name",
                "description": "名",
                "segment_type": "data_record",
                "keywords": ["BRIAN", "DANNY", "GARY", "PAUL", "WILLIE", "JOHN"],
                "start_pos": 26,
                "length": 6,  # 名 + 空格填充
                "field_type": "name",
                "required": True,
                "validation_pattern": "^[A-Z]+$",
                "sample_value": "BRIAN"
            },
            {
                "name": "last_name",
                "description": "姓",
                "segment_type": "data_record",
                "keywords": ["DEARB", "LEUNG", "MCKENN", "HOLLMA", "ORTI", "DEUGEN"],
                "start_pos": 32,
                "length": 7,  # 姓 + 空格填充
                "field_type": "name",
                "required": True,
                "validation_pattern": "^[A-Z]+$",
                "sample_value": "DEARB"
            }
        ]
    }
    
    # 保存优化配置
    with open("optimized_po_config.json", "w", encoding="utf-8") as f:
        json.dump(optimized_config, f, indent=2, ensure_ascii=False)
    
    print(f"优化配置已保存到: optimized_po_config.json")
    
    # 显示配置摘要
    print(f"\n优化配置摘要:")
    print(f"  字段数: {len(optimized_config['field_definitions'])}")
    for field in optimized_config['field_definitions']:
        print(f"  {field['name']}: 位置 {field['start_pos']}-{field['start_pos']+field['length']-1}, 类型 {field['field_type']}")


if __name__ == "__main__":
    test_smart_config()
    create_optimized_config()