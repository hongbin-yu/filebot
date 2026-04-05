#!/usr/bin/env python3
"""
Smart iAdmin COLD_INDEXES to JSON配置转换器

将Smart iAdmin系统的COLD_INDEXES表结构转换为FileBot兼容的JSON配置格式。

映射关系:
- coln (列位置) -> start (1-based位置)
- length (长度) -> length
- pattern (模式) -> validation.pattern
- replaces (替换规则) -> validation.replaces  
- leftOffset (左偏移) -> offset
"""

import json
import re
import sys
import csv
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import xml.etree.ElementTree as ET
from pathlib import Path


@dataclass
class ColdIndexField:
    """COLD_INDEXES表字段定义"""
    id: int
    levelid: int
    auditid: int
    page: int
    irow: int
    coln: int  # 列位置 (1-based)
    length: int
    literal: Optional[str]
    sample: Optional[str]
    lefttrim: Optional[str]
    usepattern: Optional[str]
    invalid_action: Optional[int]
    pattern: Optional[str]  # 验证模式
    replaces: Optional[str]  # 替换规则
    table_name: Optional[str]
    column_name: Optional[str]
    key_field_name: Optional[str]
    key_levelid: Optional[int]
    date_format: Optional[str]
    left_offset: Optional[int]  # 左偏移


@dataclass
class JsonFieldConfig:
    """FileBot JSON字段配置"""
    name: str
    start: int
    length: int
    description: Optional[str] = None
    required: bool = False
    offset: Optional[int] = None
    validation: Optional[Dict[str, Any]] = None


class ColdIndexesConverter:
    """COLD_INDEXES转换器"""
    
    def __init__(self):
        self.namespace = {
            'hibernate': 'http://hibernate.sourceforge.net/hibernate-mapping-3.0.dtd'
        }
    
    def parse_hbm_xml(self, xml_path: str) -> Dict[str, Any]:
        """解析Hibernate映射XML文件"""
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # 解析class元素
        class_elem = root.find('hibernate:class', self.namespace)
        if class_elem is None:
            class_elem = root.find('class')  # 尝试无命名空间
        
        table_info = {
            'table_name': class_elem.get('table') if class_elem is not None else 'COLD_INDEXES',
            'schema': class_elem.get('schema') if class_elem is not None else 'FMDBA',
            'fields': []
        }
        
        # 解析所有property元素
        properties = class_elem.findall('hibernate:property', self.namespace) if class_elem else []
        if not properties:
            properties = class_elem.findall('property') if class_elem else []
        
        for prop in properties:
            field_info = {
                'name': prop.get('name'),
                'type': prop.get('type'),
                'column': None
            }
            
            # 获取column元素
            column = prop.find('hibernate:column', self.namespace)
            if column is None:
                column = prop.find('column')
            
            if column is not None:
                field_info['column'] = column.get('name')
                field_info['length'] = column.get('length')
                field_info['sql_type'] = column.get('sql-type')
                field_info['not_null'] = column.get('not-null') == 'true'
            
            table_info['fields'].append(field_info)
        
        return table_info
    
    def csv_to_cold_indexes(self, csv_path: str) -> List[ColdIndexField]:
        """从CSV文件读取COLD_INDEXES表数据"""
        fields = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # 尝试不同的列名格式
                    coln = self._get_value(row, ['COLN', 'coln', 'Coln'])
                    length = self._get_value(row, ['LENGTH', 'length', 'Length'])
                    
                    if not coln or not length:
                        print(f"警告: 跳过行，缺少必要字段: {row}")
                        continue
                    
                    field = ColdIndexField(
                        id=int(self._get_value(row, ['ID', 'id', 'Id'], 0)),
                        levelid=int(self._get_value(row, ['LEVELID', 'levelid', 'LevelId'], 0)),
                        auditid=int(self._get_value(row, ['AUDITID', 'auditid', 'AuditId'], 0)),
                        page=int(self._get_value(row, ['PAGE', 'page', 'Page'], 0)),
                        irow=int(self._get_value(row, ['IROW', 'irow', 'Irow'], 0)),
                        coln=int(coln),
                        length=int(length),
                        literal=self._get_value(row, ['LITERAL', 'literal', 'Literal']),
                        sample=self._get_value(row, ['SAMPLE', 'sample', 'Sample']),
                        lefttrim=self._get_value(row, ['LEFTTRIM', 'lefttrim', 'LeftTrim']),
                        usepattern=self._get_value(row, ['USEPATTERN', 'usepattern', 'UsePattern']),
                        invalid_action=self._get_int(row, ['INVALID_ACTION', 'invalid_action', 'InvalidAction']),
                        pattern=self._get_value(row, ['PATTERN', 'pattern', 'Pattern']),
                        replaces=self._get_value(row, ['REPLACES', 'replaces', 'Replaces']),
                        table_name=self._get_value(row, ['TABLENAME', 'tablename', 'TableName']),
                        column_name=self._get_value(row, ['COLUMNNAME', 'columnname', 'ColumnName']),
                        key_field_name=self._get_value(row, ['KEYFIELDNAME', 'keyfieldname', 'KeyFieldName']),
                        key_levelid=self._get_int(row, ['KEYLEVELID', 'keylevelid', 'KeyLevelId']),
                        date_format=self._get_value(row, ['DATEFORMAT', 'dateformat', 'DateFormat']),
                        left_offset=self._get_int(row, ['LEFT_OFFSET', 'left_offset', 'LeftOffset'])
                    )
                    
                    fields.append(field)
            
            print(f"成功读取 {len(fields)} 个字段定义")
            return fields
            
        except Exception as e:
            print(f"读取CSV文件错误: {e}")
            return []
    
    def _get_value(self, row: Dict, keys: List[str], default: Optional[str] = None) -> Optional[str]:
        """从行数据中获取值，尝试多个可能的键名"""
        for key in keys:
            if key in row and row[key]:
                return row[key].strip()
        return default
    
    def _get_int(self, row: Dict, keys: List[str], default: int = 0) -> Optional[int]:
        """从行数据中获取整数值"""
        value = self._get_value(row, keys)
        if value and value.strip():
            try:
                return int(value)
            except ValueError:
                return default
        return default
    
    def convert_to_json_config(self, cold_fields: List[ColdIndexField], 
                              config_name: str = "converted_config") -> Dict[str, Any]:
        """将ColdIndexField列表转换为JSON配置"""
        
        # 按levelid分组
        fields_by_level = {}
        for field in cold_fields:
            if field.levelid not in fields_by_level:
                fields_by_level[field.levelid] = []
            fields_by_level[field.levelid].append(field)
        
        # 构建JSON配置
        json_config = {
            "name": config_name,
            "description": f"从Smart iAdmin COLD_INDEXES转换的配置",
            "version": "1.0",
            "source": "cold_indexes",
            "fields": []
        }
        
        for levelid, fields in sorted(fields_by_level.items()):
            # 为每个levelid创建字段组
            for field in fields:
                json_field = self._create_json_field(field, levelid)
                if json_field:
                    json_config["fields"].append(json_field)
        
        return json_config
    
    def _create_json_field(self, field: ColdIndexField, levelid: int) -> Optional[Dict[str, Any]]:
        """创建单个JSON字段配置"""
        
        # 生成字段名
        if field.column_name:
            field_name = field.column_name
        elif field.table_name and field.column_name:
            field_name = f"{field.table_name}_{field.column_name}"
        else:
            field_name = f"field_{field.id}_{levelid}_{field.coln}"
        
        # 生成描述
        description_parts = []
        if field.literal:
            description_parts.append(f"Literal: {field.literal}")
        if field.sample:
            description_parts.append(f"Sample: {field.sample[:50]}...")
        
        description = " | ".join(description_parts) if description_parts else f"Level {levelid}, Col {field.coln}"
        
        # 构建字段配置
        json_field = {
            "name": field_name,
            "start": field.coln,
            "length": field.length,
            "description": description,
            "required": field.invalid_action is not None and field.invalid_action > 0
        }
        
        # 添加偏移
        if field.left_offset and field.left_offset != 0:
            json_field["offset"] = field.left_offset
        
        # 添加验证规则
        validation_rules = {}
        
        if field.pattern and field.pattern.strip():
            validation_rules["pattern"] = field.pattern.strip()
        
        if field.replaces and field.replaces.strip():
            validation_rules["replaces"] = field.replaces.strip()
        
        if field.lefttrim and field.lefttrim.strip():
            validation_rules["trim_left"] = field.lefttrim.strip()
        
        if field.usepattern and field.usepattern.strip():
            validation_rules["use_pattern"] = field.usepattern.strip() == 'Y'
        
        if validation_rules:
            json_field["validation"] = validation_rules
        
        # 添加元数据
        json_field["metadata"] = {
            "cold_index_id": field.id,
            "levelid": levelid,
            "page": field.page,
            "irow": field.irow,
            "table_name": field.table_name,
            "column_name": field.column_name,
            "key_field_name": field.key_field_name,
            "date_format": field.date_format
        }
        
        return json_field
    
    def save_json_config(self, config: Dict[str, Any], output_path: str) -> bool:
        """保存JSON配置到文件"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"JSON配置已保存到: {output_path}")
            return True
        except Exception as e:
            print(f"保存JSON配置错误: {e}")
            return False
    
    def generate_sample_csv(self, output_path: str) -> bool:
        """生成示例CSV文件模板"""
        headers = [
            "ID", "LEVELID", "AUDITID", "PAGE", "IROW", "COLN", "LENGTH",
            "LITERAL", "SAMPLE", "LEFTTRIM", "USEPATTERN", "INVALID_ACTION",
            "PATTERN", "REPLACES", "TABLENAME", "COLUMNNAME", "KEYFIELDNAME",
            "KEYLEVELID", "DATEFORMAT", "LEFT_OFFSET"
        ]
        
        # 示例数据
        sample_data = [
            {
                "ID": "1",
                "LEVELID": "1",
                "AUDITID": "0",
                "PAGE": "1",
                "IROW": "1",
                "COLN": "1",
                "LENGTH": "7",
                "LITERAL": "Invoice No",
                "SAMPLE": "1333333",
                "LEFTTRIM": "",
                "USEPATTERN": "Y",
                "INVALID_ACTION": "1",
                "PATTERN": "^\\d{7}$",
                "REPLACES": "",
                "TABLENAME": "INVOICE_HEADER",
                "COLUMNNAME": "INVOICE_NO",
                "KEYFIELDNAME": "",
                "KEYLEVELID": "",
                "DATEFORMAT": "",
                "LEFT_OFFSET": "0"
            },
            {
                "ID": "1",
                "LEVELID": "1",
                "AUDITID": "0",
                "PAGE": "1",
                "IROW": "1",
                "COLN": "9",
                "LENGTH": "5",
                "LITERAL": "Customer No",
                "SAMPLE": "33333",
                "LEFTTRIM": "",
                "USEPATTERN": "Y",
                "INVALID_ACTION": "1",
                "PATTERN": "^\\d{5}$",
                "REPLACES": "",
                "TABLENAME": "INVOICE_HEADER",
                "COLUMNNAME": "CUSTOMER_NO",
                "KEYFIELDNAME": "",
                "KEYLEVELID": "",
                "DATEFORMAT": "",
                "LEFT_OFFSET": "0"
            }
        ]
        
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(sample_data)
            
            print(f"示例CSV模板已生成: {output_path}")
            print("说明: 请从Smart iAdmin数据库导出COLD_INDEXES表数据到此格式")
            return True
            
        except Exception as e:
            print(f"生成示例CSV错误: {e}")
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='COLD_INDEXES to JSON配置转换器')
    parser.add_argument('--mode', choices=['parse-xml', 'convert-csv', 'generate-sample'], 
                       default='convert-csv', help='运行模式')
    parser.add_argument('--input', type=str, help='输入文件路径')
    parser.add_argument('--output', type=str, default='cold_indexes_config.json', 
                       help='输出JSON文件路径')
    parser.add_argument('--config-name', type=str, default='converted_config',
                       help='配置名称')
    
    args = parser.parse_args()
    
    converter = ColdIndexesConverter()
    
    if args.mode == 'parse-xml':
        if not args.input:
            print("错误: parse-xml模式需要--input参数指定XML文件")
            sys.exit(1)
        
        table_info = converter.parse_hbm_xml(args.input)
        print("Hibernate映射文件解析结果:")
        print(json.dumps(table_info, indent=2, ensure_ascii=False))
        
    elif args.mode == 'convert-csv':
        if not args.input:
            print("错误: convert-csv模式需要--input参数指定CSV文件")
            sys.exit(1)
        
        print(f"正在转换CSV文件: {args.input}")
        cold_fields = converter.csv_to_cold_indexes(args.input)
        
        if not cold_fields:
            print("错误: 未读取到有效的字段定义")
            sys.exit(1)
        
        json_config = converter.convert_to_json_config(cold_fields, args.config_name)
        converter.save_json_config(json_config, args.output)
        
        # 显示统计信息
        print(f"\n转换统计:")
        print(f"  - 总字段数: {len(json_config['fields'])}")
        print(f"  - 包含验证规则的字段: {sum(1 for f in json_config['fields'] if 'validation' in f)}")
        print(f"  - 包含偏移的字段: {sum(1 for f in json_config['fields'] if 'offset' in f)}")
        
    elif args.mode == 'generate-sample':
        sample_path = args.output.replace('.json', '_sample.csv')
        converter.generate_sample_csv(sample_path)


if __name__ == "__main__":
    main()