#!/usr/bin/env python3
"""
索引提取器 - 从文本文件中按固定位置提取索引字段
支持不同应用程序的字段定义配置
"""

import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

class DataType(Enum):
    """数据类型枚举"""
    STRING = "string"
    DATE = "date"      # MM/DD/YY 格式
    NUMBER = "number"
    CURRENCY = "currency"
    CODE = "code"      # 代码/缩写

@dataclass
class FieldDefinition:
    """字段定义"""
    name: str           # 字段名称
    description: str    # 字段描述
    start_pos: int      # 起始位置（0-based）
    length: int         # 字段长度
    data_type: DataType = DataType.STRING
    required: bool = False
    validation_pattern: Optional[str] = None
    sample_value: Optional[str] = None
    
    @property
    def end_pos(self) -> int:
        """结束位置（不包含）"""
        return self.start_pos + self.length
    
    def extract(self, line: str) -> str:
        """从行中提取字段值"""
        if self.start_pos >= len(line):
            return ""
        end = min(self.end_pos, len(line))
        value = line[self.start_pos:end].strip()
        return self.clean_value(value)
    
    def clean_value(self, value: str) -> str:
        """清理字段值"""
        # 移除空字符
        value = value.replace('\x00', '')
        # 移除首尾空格
        value = value.strip()
        
        # 根据数据类型进一步处理
        if self.data_type == DataType.DATE:
            # 确保日期格式一致
            if re.match(r'\d{2}/\d{2}/\d{2}', value):
                return value
        elif self.data_type == DataType.NUMBER:
            # 移除非数字字符（保留小数点和逗号）
            value = re.sub(r'[^\d.,]', '', value)
        
        return value
    
    def validate(self, value: str) -> Tuple[bool, str]:
        """验证字段值"""
        if self.required and not value:
            return False, f"字段 '{self.name}' 是必填字段，但值为空"
        
        if self.validation_pattern and value:
            if not re.match(self.validation_pattern, value):
                return False, f"字段 '{self.name}' 的值 '{value}' 不符合验证模式"
        
        return True, ""

@dataclass
class ApplicationDefinition:
    """应用程序定义"""
    app_name: str                    # 应用程序名称
    app_code: str                    # 应用程序代码
    template_name: str               # 对应的JasperReports模板
    field_definitions: List[FieldDefinition] = field(default_factory=list)
    line_patterns: Dict[str, str] = field(default_factory=dict)  # 行类型模式
    
    def get_field(self, name: str) -> Optional[FieldDefinition]:
        """获取字段定义"""
        for field_def in self.field_definitions:
            if field_def.name == name:
                return field_def
        return None
    
    def add_field(self, field_def: FieldDefinition):
        """添加字段定义"""
        self.field_definitions.append(field_def)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "app_name": self.app_name,
            "app_code": self.app_code,
            "template_name": self.template_name,
            "field_definitions": [
                {
                    "name": fd.name,
                    "description": fd.description,
                    "start_pos": fd.start_pos,
                    "length": fd.length,
                    "data_type": fd.data_type.value,
                    "required": fd.required,
                    "validation_pattern": fd.validation_pattern,
                    "sample_value": fd.sample_value
                }
                for fd in self.field_definitions
            ]
        }


class IndexExtractor:
    """索引提取器"""
    
    def __init__(self, app_def: Optional[ApplicationDefinition] = None):
        self.app_def = app_def
        self.extracted_data: Dict[str, Any] = {}
        self.validation_errors: List[str] = []
        
    def set_application(self, app_def: ApplicationDefinition):
        """设置应用程序定义"""
        self.app_def = app_def
        
    def extract_from_line(self, line: str, line_type: str = "default") -> Dict[str, str]:
        """从单行提取字段"""
        if not self.app_def:
            raise ValueError("未设置应用程序定义")
        
        extracted = {}
        for field_def in self.app_def.field_definitions:
            value = field_def.extract(line)
            if value:
                extracted[field_def.name] = value
        
        return extracted
    
    def extract_from_file(self, file_path: str, encoding: str = "latin-1") -> Dict[str, Any]:
        """从文件提取索引字段"""
        if not self.app_def:
            raise ValueError("未设置应用程序定义")
        
        # 读取文件
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        
        content = raw_data.decode(encoding)
        lines = content.splitlines()
        
        # 初始化提取结果
        self.extracted_data = {
            "app_name": self.app_def.app_name,
            "app_code": self.app_def.app_code,
            "template_name": self.app_def.template_name,
            "fields": {},
            "records": [],  # 多条记录（如人员记录）
            "summary": {
                "total_lines": len(lines),
                "data_lines": 0,
                "extracted_fields": 0
            }
        }
        
        self.validation_errors = []
        
        # 提取数据
        records = []
        for i, line in enumerate(lines):
            if not line.strip():
                continue
                
            # 根据行首字符判断行类型
            line_type = self._detect_line_type(line)
            
            # 提取字段
            extracted_fields = self.extract_from_line(line, line_type)
            
            if extracted_fields:
                record = {
                    "line_number": i + 1,
                    "line_type": line_type,
                    "raw_line": repr(line[:100]),
                    "fields": extracted_fields
                }
                records.append(record)
                
                # 更新字段汇总
                for field_name, value in extracted_fields.items():
                    if field_name not in self.extracted_data["fields"]:
                        self.extracted_data["fields"][field_name] = {
                            "values": [],
                            "count": 0
                        }
                    self.extracted_data["fields"][field_name]["values"].append(value)
                    self.extracted_data["fields"][field_name]["count"] += 1
        
        self.extracted_data["records"] = records
        self.extracted_data["summary"]["data_lines"] = len(records)
        self.extracted_data["summary"]["extracted_fields"] = sum(
            len(r["fields"]) for r in records
        )
        
        return self.extracted_data
    
    def _detect_line_type(self, line: str) -> str:
        """检测行类型"""
        if not line.strip():
            return "empty"
        
        first_char = line[0] if line else ''
        
        # 常见行类型映射
        type_mapping = {
            '-': "data_record",      # 数据记录行
            '0': "header",           # 标题行
            '1': "page_marker",      # 页面标记
            ' ': "indented",         # 缩进行
        }
        
        return type_mapping.get(first_char, f"type_{first_char}")
    
    def validate_extraction(self) -> Tuple[bool, List[str]]:
        """验证提取结果"""
        if not self.app_def:
            return False, ["未设置应用程序定义"]
        
        errors = []
        
        # 检查必填字段
        for field_def in self.app_def.field_definitions:
            if field_def.required:
                field_name = field_def.name
                if field_name not in self.extracted_data.get("fields", {}):
                    errors.append(f"必填字段 '{field_name}' 未找到")
                else:
                    values = self.extracted_data["fields"][field_name]["values"]
                    if not any(values):  # 所有值都为空
                        errors.append(f"必填字段 '{field_name}' 的所有值都为空")
        
        self.validation_errors = errors
        return len(errors) == 0, errors
    
    def export_json(self, file_path: str):
        """导出提取结果到JSON文件"""
        if not self.extracted_data:
            raise ValueError("没有提取数据可导出")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.extracted_data, f, indent=2, ensure_ascii=False)
    
    def print_summary(self):
        """打印提取摘要"""
        if not self.extracted_data:
            print("没有提取数据")
            return
        
        data = self.extracted_data
        print(f"应用程序: {data['app_name']} ({data['app_code']})")
        print(f"模板: {data['template_name']}")
        print(f"总行数: {data['summary']['total_lines']}")
        print(f"数据行数: {data['summary']['data_lines']}")
        print(f"提取字段数: {data['summary']['extracted_fields']}")
        
        # 字段统计
        print("\n字段提取统计:")
        fields = data.get("fields", {})
        for field_name, field_data in sorted(fields.items()):
            unique_values = len(set(field_data["values"]))
            sample = field_data["values"][0] if field_data["values"] else ""
            print(f"  {field_name}: {field_data['count']} 次, {unique_values} 个唯一值")
            if sample:
                print(f"    示例: {repr(sample[:50])}")
        
        # 记录类型统计
        print("\n记录类型统计:")
        type_counts = {}
        for record in data.get("records", []):
            line_type = record.get("line_type", "unknown")
            type_counts[line_type] = type_counts.get(line_type, 0) + 1
        
        for line_type, count in sorted(type_counts.items()):
            print(f"  {line_type}: {count} 条")
        
        # 验证结果
        is_valid, errors = self.validate_extraction()
        if errors:
            print(f"\n验证错误 ({len(errors)} 个):")
            for error in errors:
                print(f"  - {error}")
        else:
            print("\n验证通过")


# ============================================================================
# 基于PO.TXT分析的应用程序定义（推断）
# ============================================================================

def create_po_application_definition() -> ApplicationDefinition:
    """创建采购订单应用程序定义（基于PO.TXT分析推断）"""
    
    app_def = ApplicationDefinition(
        app_name="Purchase Order",
        app_code="PO",
        template_name="pcl_form.jasper"  # 假设的模板
    )
    
    # 基于PO.TXT分析推断的字段定义
    # 注意：这些是基于内容分析的推断，需要用户确认
    
    # 数据记录行（"-"开头）的字段
    app_def.add_field(FieldDefinition(
        name="record_type",
        description="记录类型标记",
        start_pos=0,
        length=3,
        data_type=DataType.CODE,
        required=True,
        sample_value="-"
    ))
    
    app_def.add_field(FieldDefinition(
        name="date",
        description="日期 (MM/DD/YY)",
        start_pos=3,
        length=12,
        data_type=DataType.DATE,
        required=True,
        validation_pattern=r'\d{2}/\d{2}/\d{2}',
        sample_value="04/09/12"
    ))
    
    app_def.add_field(FieldDefinition(
        name="status",
        description="状态代码",
        start_pos=15,
        length=6,
        data_type=DataType.CODE,
        sample_value="E"
    ))
    
    app_def.add_field(FieldDefinition(
        name="initials",
        description="人员缩写",
        start_pos=21,
        length=5,
        data_type=DataType.CODE,
        sample_value="BD"
    ))
    
    app_def.add_field(FieldDefinition(
        name="first_name",
        description="名",
        start_pos=26,
        length=6,
        data_type=DataType.STRING,
        sample_value="BRIAN"
    ))
    
    app_def.add_field(FieldDefinition(
        name="last_name",
        description="姓",
        start_pos=32,
        length=7,
        data_type=DataType.STRING,
        sample_value="DEARB"
    ))
    
    # 标题行（"0"开头）的字段
    app_def.add_field(FieldDefinition(
        name="company_name",
        description="公司名称",
        start_pos=40,  # 粗略估计
        length=40,
        data_type=DataType.STRING,
        sample_value="PARKER HANNIFIN CORPORATION"
    ))
    
    app_def.add_field(FieldDefinition(
        name="phone",
        description="电话号码",
        start_pos=20,  # 粗略估计
        length=20,
        data_type=DataType.STRING,
        sample_value="(619) 661-7000"
    ))
    
    return app_def


# ============================================================================
# 测试函数
# ============================================================================

def test_po_extraction():
    """测试PO.TXT文件提取"""
    print("测试采购订单索引提取器")
    print("=" * 60)
    
    # 创建应用程序定义
    app_def = create_po_application_definition()
    
    # 创建提取器
    extractor = IndexExtractor(app_def)
    
    # 提取文件
    print("1. 从PO.TXT提取索引字段...")
    extracted_data = extractor.extract_from_file("PO.TXT")
    
    # 打印摘要
    print("\n2. 提取摘要:")
    extractor.print_summary()
    
    # 导出结果
    print("\n3. 导出提取结果...")
    extractor.export_json("po_extracted.json")
    print(f"   已导出到: po_extracted.json")
    
    # 显示示例记录
    records = extracted_data.get("records", [])
    if records:
        print(f"\n4. 示例记录（前3条）:")
        for i, record in enumerate(records[:3]):
            print(f"   记录 {i+1} (行{record['line_number']}, 类型: {record['line_type']}):")
            for field_name, value in record['fields'].items():
                print(f"     {field_name}: {repr(value)}")
    
    # 显示字段统计详情
    print(f"\n5. 字段详情统计:")
    fields = extracted_data.get("fields", {})
    for field_name in sorted(fields.keys()):
        field_data = fields[field_name]
        unique_values = len(set(field_data["values"]))
        if unique_values <= 5:  # 显示少量唯一值的字段
            print(f"   {field_name}: {field_data['count']} 次")
            print(f"     唯一值: {sorted(set(field_data['values']))}")
    
    return extractor


def analyze_field_positions(file_path: str):
    """分析文件中字段的实际位置（用于推断字段定义）"""
    print(f"分析文件字段位置: {file_path}")
    
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    
    content = raw_data.decode('latin-1')
    lines = content.splitlines()
    
    # 按行类型分组
    line_groups = {}
    for i, line in enumerate(lines[:100]):  # 只分析前100行
        if not line.strip():
            continue
            
        first_char = line[0] if line else ''
        if first_char not in line_groups:
            line_groups[first_char] = []
        line_groups[first_char].append((i+1, line))
    
    # 分析每种行类型的列结构
    print("\n行类型列结构分析:")
    for char, group_lines in sorted(line_groups.items()):
        print(f"\n类型 '{char}' ({len(group_lines)} 行):")
        
        if group_lines:
            # 分析第一行的列边界
            line_num, sample_line = group_lines[0]
            print(f"  示例行 {line_num}: {repr(sample_line[:80])}")
            
            # 查找列边界
            prev_char = ' '
            boundaries = []
            for j, char in enumerate(sample_line[:100]):
                if prev_char == ' ' and char != ' ':
                    boundaries.append(j)
                prev_char = char
            
            print(f"  检测到的列边界: {boundaries}")
            
            # 显示字段提取
            if boundaries:
                boundaries.append(len(sample_line))
                print(f"  字段提取:")
                for k in range(min(8, len(boundaries)-1)):
                    start = boundaries[k]
                    end = boundaries[k+1]
                    field = sample_line[start:end].strip()
                    if field:
                        print(f"    位置 {start}-{end-1}: {repr(field)}")


if __name__ == "__main__":
    # 测试提取器
    extractor = test_po_extraction()
    
    print(f"\n{'='*60}")
    print("字段位置分析:")
    analyze_field_positions("PO.TXT")