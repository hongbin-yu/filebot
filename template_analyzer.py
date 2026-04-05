#!/usr/bin/env python3
"""
样板文件分析器 - 通过样板文件计算关键词位置，生成JSON提取配置文件
"""

import re
import json
import argparse
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import sys

class FieldType(Enum):
    """字段类型枚举"""
    STRING = "string"
    DATE = "date"          # MM/DD/YY 格式
    NUMBER = "number"
    CURRENCY = "currency"
    CODE = "code"          # 代码/缩写
    NAME = "name"          # 姓名
    PHONE = "phone"        # 电话号码
    ADDRESS = "address"    # 地址

@dataclass
class FieldDefinition:
    """字段定义"""
    name: str                     # 字段名称
    description: str              # 字段描述
    keywords: List[str]           # 用于定位的关键词
    start_pos: int                # 起始位置（0-based）
    length: int                   # 字段长度
    field_type: FieldType         # 字段类型
    required: bool = False        # 是否必填
    validation_pattern: Optional[str] = None  # 验证正则表达式
    sample_value: Optional[str] = None        # 样本值
    
    @property
    def end_pos(self) -> int:
        """结束位置（不包含）"""
        return self.start_pos + self.length
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "keywords": self.keywords,
            "start_pos": self.start_pos,
            "length": self.length,
            "field_type": self.field_type.value,
            "required": self.required,
            "validation_pattern": self.validation_pattern,
            "sample_value": self.sample_value
        }


@dataclass
class ApplicationConfig:
    """应用程序配置"""
    app_name: str                    # 应用程序名称
    app_code: str                    # 应用程序代码
    template_name: str               # JasperReports模板名称
    file_extension: str = ".cld"     # 文件扩展名
    encoding: str = "latin-1"        # 文件编码
    description: str = ""            # 应用描述
    field_definitions: List[FieldDefinition] = field(default_factory=list)
    
    def add_field(self, field_def: FieldDefinition):
        """添加字段定义"""
        self.field_definitions.append(field_def)
    
    def get_field(self, name: str) -> Optional[FieldDefinition]:
        """获取字段定义"""
        for field_def in self.field_definitions:
            if field_def.name == name:
                return field_def
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "app_name": self.app_name,
            "app_code": self.app_code,
            "template_name": self.template_name,
            "file_extension": self.file_extension,
            "encoding": self.encoding,
            "description": self.description,
            "field_definitions": [fd.to_dict() for fd in self.field_definitions]
        }
    
    def save_to_file(self, file_path: str):
        """保存到文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'ApplicationConfig':
        """从文件加载"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        config = cls(
            app_name=data["app_name"],
            app_code=data["app_code"],
            template_name=data["template_name"],
            file_extension=data.get("file_extension", ".cld"),
            encoding=data.get("encoding", "latin-1"),
            description=data.get("description", "")
        )
        
        for field_data in data["field_definitions"]:
            field_def = FieldDefinition(
                name=field_data["name"],
                description=field_data["description"],
                keywords=field_data["keywords"],
                start_pos=field_data["start_pos"],
                length=field_data["length"],
                field_type=FieldType(field_data["field_type"]),
                required=field_data.get("required", False),
                validation_pattern=field_data.get("validation_pattern"),
                sample_value=field_data.get("sample_value")
            )
            config.add_field(field_def)
        
        return config


class TemplateAnalyzer:
    """样板文件分析器"""
    
    def __init__(self, template_file: str, encoding: str = "latin-1"):
        self.template_file = template_file
        self.encoding = encoding
        self.lines: List[str] = []
        self.data_lines: List[str] = []  # 包含实际数据的行
        
        # 加载样板文件
        self._load_template()
    
    def _load_template(self):
        """加载样板文件"""
        with open(self.template_file, 'rb') as f:
            raw_data = f.read()
        
        content = raw_data.decode(self.encoding)
        self.lines = content.splitlines()
        
        # 识别包含实际数据的行（不只是格式行）
        for line in self.lines:
            if line.strip() and len(line.strip()) > 1:
                self.data_lines.append(line)
        
        print(f"样板文件: {self.template_file}")
        print(f"总行数: {len(self.lines)}")
        print(f"数据行数: {len(self.data_lines)}")
    
    def find_keyword_positions(self, keyword: str, 
                              max_lines: int = 10) -> List[Tuple[int, int, str]]:
        """查找关键词位置
        
        返回: [(行号, 位置, 上下文), ...]
        """
        positions = []
        
        for i, line in enumerate(self.data_lines[:max_lines]):
            # 查找关键词
            start_pos = line.find(keyword)
            if start_pos != -1:
                # 获取上下文（关键词前后各20个字符）
                context_start = max(0, start_pos - 20)
                context_end = min(len(line), start_pos + len(keyword) + 20)
                context = line[context_start:context_end]
                
                positions.append((i + 1, start_pos, context))
        
        return positions
    
    def analyze_field_position(self, field_name: str, keywords: List[str], 
                              expected_type: FieldType = FieldType.STRING) -> Optional[FieldDefinition]:
        """分析字段位置
        
        参数:
            field_name: 字段名称
            keywords: 用于定位的关键词列表
            expected_type: 期望的字段类型
        """
        print(f"\n分析字段: {field_name}")
        print(f"  关键词: {keywords}")
        
        # 在所有关键词中查找第一个匹配的位置
        first_position = None
        sample_value = None
        
        for keyword in keywords:
            positions = self.find_keyword_positions(keyword, max_lines=5)
            if positions:
                line_num, start_pos, context = positions[0]
                first_position = (line_num, start_pos, keyword)
                
                # 尝试提取样本值
                line = self.data_lines[line_num - 1]
                sample_value = self._extract_sample_value(line, start_pos, len(keyword))
                
                print(f"  在行 {line_num} 找到关键词 '{keyword}'")
                print(f"    位置: {start_pos}")
                print(f"    上下文: {repr(context)}")
                print(f"    样本值: {repr(sample_value)}")
                break
        
        if not first_position:
            print(f"  警告: 未找到任何关键词")
            return None
        
        line_num, start_pos, matched_keyword = first_position
        
        # 分析字段长度
        field_length = self._analyze_field_length(start_pos, matched_keyword, sample_value)
        
        # 确定字段类型
        field_type = self._determine_field_type(sample_value, expected_type)
        
        # 创建字段定义
        field_def = FieldDefinition(
            name=field_name,
            description=f"从样板文件分析的 {field_name} 字段",
            keywords=keywords,
            start_pos=start_pos,
            length=field_length,
            field_type=field_type,
            sample_value=sample_value
        )
        
        # 添加验证模式（如果适用）
        if field_type == FieldType.DATE:
            field_def.validation_pattern = r'\d{2}/\d{2}/\d{2}'
        elif field_type == FieldType.CODE and sample_value and len(sample_value) <= 3:
            field_def.validation_pattern = r'^[A-Z]{1,3}$'
        elif field_type == FieldType.PHONE:
            field_def.validation_pattern = r'\(\d{3}\) \d{3}-\d{4}'
        
        return field_def
    
    def _extract_sample_value(self, line: str, start_pos: int, keyword_length: int) -> str:
        """提取样本值"""
        # 从起始位置开始，提取直到遇到空格或行尾
        end_pos = start_pos
        while end_pos < len(line) and line[end_pos] != ' ':
            end_pos += 1
        
        value = line[start_pos:end_pos].strip()
        
        # 清理空字符
        value = value.replace('\x00', '')
        
        return value
    
    def _analyze_field_length(self, start_pos: int, keyword: str, sample_value: str) -> int:
        """分析字段长度"""
        # 基本策略：使用关键词长度或样本值长度
        if sample_value:
            # 使用样本值长度
            return len(sample_value)
        else:
            # 使用关键词长度，但最小为1
            return max(len(keyword), 1)
    
    def _determine_field_type(self, sample_value: str, expected_type: FieldType) -> FieldType:
        """确定字段类型"""
        if not sample_value:
            return expected_type
        
        # 基于样本值推断类型
        if re.match(r'\d{2}/\d{2}/\d{2}', sample_value):
            return FieldType.DATE
        elif re.match(r'^[A-Z]{1,3}$', sample_value):
            return FieldType.CODE
        elif re.match(r'^[A-Z]+$', sample_value) and 3 <= len(sample_value) <= 15:
            return FieldType.NAME
        elif re.match(r'\(\d{3}\) \d{3}-\d{4}', sample_value):
            return FieldType.PHONE
        elif re.match(r'^\d+$', sample_value):
            return FieldType.NUMBER
        elif re.match(r'^\d+\.\d+$', sample_value):
            return FieldType.NUMBER
        else:
            return expected_type
    
    def analyze_data_line_pattern(self, line_type: str = "data_record") -> Dict[str, Any]:
        """分析数据行模式"""
        print(f"\n分析数据行模式 (类型: {line_type})")
        
        # 找到数据行（以"-"开头且包含数据的行）
        data_lines = []
        for line in self.lines:
            if line.strip() and line[0] == '-' and len(line.strip()) > 1:
                data_lines.append(line)
        
        if not data_lines:
            print("  未找到数据行")
            return {}
        
        print(f"  找到 {len(data_lines)} 条数据行")
        
        # 分析第一行数据行
        sample_line = data_lines[0]
        print(f"  样本行: {repr(sample_line[:80])}")
        
        # 分析列结构
        column_boundaries = self._analyze_column_boundaries(sample_line)
        
        # 提取字段
        fields = self._extract_fields_from_line(sample_line, column_boundaries)
        
        return {
            "sample_line": sample_line,
            "column_boundaries": column_boundaries,
            "extracted_fields": fields
        }
    
    def _analyze_column_boundaries(self, line: str) -> List[int]:
        """分析列边界"""
        boundaries = []
        prev_char = ' '
        
        for i, char in enumerate(line[:150]):  # 只分析前150个字符
            if prev_char == ' ' and char != ' ':
                boundaries.append(i)
            prev_char = char
        
        return boundaries
    
    def _extract_fields_from_line(self, line: str, boundaries: List[int]) -> List[Dict[str, Any]]:
        """从行中提取字段"""
        if not boundaries:
            return []
        
        fields = []
        boundaries_with_end = boundaries + [len(line)]
        
        for i in range(len(boundaries_with_end) - 1):
            start = boundaries_with_end[i]
            end = boundaries_with_end[i + 1]
            field_content = line[start:end].strip()
            
            if field_content:
                # 清理空字符
                clean_content = field_content.replace('\x00', '')
                
                # 推断字段类型
                field_type = self._determine_field_type(clean_content, FieldType.STRING)
                
                fields.append({
                    "index": i + 1,
                    "start": start,
                    "end": end - 1,
                    "length": end - start,
                    "content": clean_content,
                    "field_type": field_type.value
                })
        
        return fields
    
    def generate_initial_config(self, app_name: str, app_code: str, 
                               template_name: str) -> ApplicationConfig:
        """生成初始配置（基于样板文件分析）"""
        print(f"\n{'='*60}")
        print(f"生成初始配置")
        print(f"  应用: {app_name} ({app_code})")
        print(f"  模板: {template_name}")
        print(f"{'='*60}")
        
        config = ApplicationConfig(
            app_name=app_name,
            app_code=app_code,
            template_name=template_name
        )
        
        # 基于PO.TXT分析的预定义字段（可以根据需要修改）
        predefined_fields = [
            {
                "name": "record_type",
                "description": "记录类型标记",
                "keywords": ["-"],
                "expected_type": FieldType.CODE
            },
            {
                "name": "date",
                "description": "日期 (MM/DD/YY)",
                "keywords": ["04/09/12", "05/02/12", "01/26/12"],
                "expected_type": FieldType.DATE
            },
            {
                "name": "status",
                "description": "状态代码",
                "keywords": ["E", "I", "O"],
                "expected_type": FieldType.CODE
            },
            {
                "name": "initials",
                "description": "人员缩写",
                "keywords": ["BD", "DL", "PH", "JM", "WO", "JD"],
                "expected_type": FieldType.CODE
            },
            {
                "name": "first_name",
                "description": "名",
                "keywords": ["BRIAN", "DANNY", "GARY", "PAUL", "WILLIE", "JOHN"],
                "expected_type": FieldType.NAME
            },
            {
                "name": "last_name",
                "description": "姓",
                "keywords": ["DEARB", "LEUNG", "MCKENN", "HOLLMA", "ORTI", "DEUGEN"],
                "expected_type": FieldType.NAME
            },
            {
                "name": "company_name",
                "description": "公司名称",
                "keywords": ["PARKER HANNIFIN CORPORATION", "PARKER HANNIFIN"],
                "expected_type": FieldType.STRING
            },
            {
                "name": "phone",
                "description": "电话号码",
                "keywords": ["(619) 661-7000", "(619) 671-3208"],
                "expected_type": FieldType.PHONE
            }
        ]
        
        # 分析每个字段
        for field_info in predefined_fields:
            field_def = self.analyze_field_position(
                field_name=field_info["name"],
                keywords=field_info["keywords"],
                expected_type=field_info["expected_type"]
            )
            
            if field_def:
                config.add_field(field_def)
        
        return config
    
    def validate_config(self, config: ApplicationConfig) -> Dict[str, Any]:
        """验证配置"""
        print(f"\n{'='*60}")
        print("验证配置")
        print(f"{'='*60}")
        
        validation_results = {
            "total_fields": len(config.field_definitions),
            "validated_fields": 0,
            "errors": [],
            "warnings": []
        }
        
        # 测试每个字段的定义
        for field_def in config.field_definitions:
            print(f"\n验证字段: {field_def.name}")
            
            # 查找样本值
            found_samples = []
            for keyword in field_def.keywords:
                positions = self.find_keyword_positions(keyword, max_lines=5)
                if positions:
                    for line_num, start_pos, context in positions:
                        line = self.data_lines[line_num - 1]
                        extracted = self._extract_with_config(line, field_def)
                        if extracted:
                            found_samples.append(extracted)
            
            if found_samples:
                print(f"  找到 {len(found_samples)} 个样本")
                print(f"  样本值: {found_samples[:3]}")  # 显示前3个
                validation_results["validated_fields"] += 1
            else:
                error_msg = f"字段 '{field_def.name}' 未找到样本"
                print(f"  错误: {error_msg}")
                validation_results["errors"].append(error_msg)
        
        print(f"\n验证完成:")
        print(f"  总字段数: {validation_results['total_fields']}")
        print(f"  已验证字段: {validation_results['validated_fields']}")
        print(f"  错误数: {len(validation_results['errors'])}")
        print(f"  警告数: {len(validation_results['warnings'])}")
        
        return validation_results
    
    def _extract_with_config(self, line: str, field_def: FieldDefinition) -> Optional[str]:
        """使用配置提取字段值"""
        if field_def.start_pos >= len(line):
            return None
        
        end_pos = min(field_def.end_pos, len(line))
        value = line[field_def.start_pos:end_pos].strip()
        
        # 清理空字符
        value = value.replace('\x00', '')
        
        return value if value else None


# ============================================================================
# 命令行界面和主函数
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='样板文件分析器 - 生成JSON提取配置文件')
    parser.add_argument('template', help='样板文件路径')
    parser.add_argument('--app-name', default='Purchase Order', help='应用程序名称')
    parser.add_argument('--app-code', default='PO', help='应用程序代码')
    parser.add_argument('--template-name', default='pcl_form.jasper', help='JasperReports模板名称')
    parser.add_argument('--output', default='app_config.json', help='输出配置文件路径')
    parser.add_argument('--analyze-only', action='store_true', help='只分析不生成配置')
    
    args = parser.parse_args()
    
    print("样板文件分析器")
    print("=" * 60)
    
    # 创建分析器
    analyzer = TemplateAnalyzer(args.template)
    
    # 分析数据行模式
    pattern_result = analyzer.analyze_data_line_pattern()
    
    if args.analyze_only:
        print("\n分析完成，未生成配置文件")
        return
    
    # 生成初始配置
    config = analyzer.generate_initial_config(
        app_name=args.app_name,
        app_code=args.app_code,
        template_name=args.template_name
    )
    
    # 验证配置
    validation_results = analyzer.validate_config(config)
    
    if validation_results["errors"]:
        print(f"\n警告: 配置有 {len(validation_results['errors'])} 个错误")
        for error in validation_results["errors"]:
            print(f"  - {error}")
    
    # 保存配置
    config.save_to_file(args.output)
    print(f"\n配置已保存到: {args.output}")
    
    # 显示配置摘要
    print(f"\n配置摘要:")
    print(f"  应用: {config.app_name} ({config.app_code})")
    print(f"  模板: {config.template_name}")
    print(f"  字段数: {len(config.field_definitions)}")
    
    print(f"\n字段列表:")
    for field_def in config.field_definitions:
        print(f"  {field_def.name}: 位置 {field_def.start_pos}-{field_def.end_pos-1}, 类型 {field_def.field_type.value}")
        if field_def.sample_value:
            print(f"    样本: {field_def.sample_value}")


def create_sample_config():
    """创建示例配置（基于PO.TXT分析）"""
    print("创建示例配置（基于PO.TXT分析）")
    
    # 创建配置
    config = ApplicationConfig(
        app_name="Purchase Order",
        app_code="PO",
        template_name="pcl_form.jasper",
        description="采购订单应用程序配置"
    )
    
    # 添加字段定义（基于之前分析的结果）
    config.add_field(FieldDefinition(
        name="record_type",
        description="记录类型标记",
        keywords=["-"],
        start_pos=0,
        length=3,
        field_type=FieldType.CODE,
        required=True,
        sample_value="-"
    ))
    
    config.add_field(FieldDefinition(
        name="date",
        description="日期 (MM/DD/YY)",
        keywords=["04/09/12", "05/02/12", "01/26/12"],
        start_pos=3,
        length=12,
        field_type=FieldType.DATE,
        required=True,
        validation_pattern=r'\d{2}/\d{2}/\d{2}',
        sample_value="04/09/12"
    ))
    
    config.add_field(FieldDefinition(
        name="status",
        description="状态代码",
        keywords=["E", "I", "O"],
        start_pos=15,
        length=6,
        field_type=FieldType.CODE,
        sample_value="E"
    ))
    
    config.add_field(FieldDefinition(
        name="initials",
        description="人员缩写",
        keywords=["BD", "DL", "PH", "JM", "WO", "JD"],
        start_pos=21,
        length=5,
        field_type=FieldType.CODE,
        sample_value="BD"
    ))
    
    config.add_field(FieldDefinition(
        name="first_name",
        description="名",
        keywords=["BRIAN", "DANNY", "GARY", "PAUL", "WILLIE", "JOHN"],
        start_pos=26,
        length=6,
        field_type=FieldType.NAME,
        sample_value="BRIAN"
    ))
    
    config.add_field(FieldDefinition(
        name="last_name",
        description="姓",
        keywords=["DEARB", "LEUNG", "MCKENN", "HOLLMA", "ORTI", "DEUGEN"],
        start_pos=32,
        length=7,
        field_type=FieldType.NAME,
        sample_value="DEARB"
    ))
    
    config.add_field(FieldDefinition(
        name="company_name",
        description="公司名称",
        keywords=["PARKER HANNIFIN CORPORATION", "PARKER HANNIFIN"],
        start_pos=40,  # 估计位置
        length=40,
        field_type=FieldType.STRING,
        sample_value="PARKER HANNIFIN CORPORATION"
    ))
    
    config.add_field(FieldDefinition(
        name="phone",
        description="电话号码",
        keywords=["(619) 661-7000", "(619) 671-3208"],
        start_pos=20,  # 估计位置
        length=20,
        field_type=FieldType.PHONE,
        sample_value="(619) 661-7000"
    ))
    
    # 保存配置
    config.save_to_file("sample_app_config.json")
    print(f"示例配置已保存到: sample_app_config.json")
    
    return config


if __name__ == "__main__":
    # 如果没有参数，运行示例
    if len(sys.argv) == 1:
        print("运行示例配置生成...")
        create_sample_config()
    else:
        main()