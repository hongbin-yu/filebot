#!/usr/bin/env python3
"""
智能样板文件分析器 - 识别数据段并生成精确的JSON配置文件
"""

import re
import json
import sys
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class SegmentType(Enum):
    """数据段类型枚举"""
    HEADER = "header"          # 标题段：公司信息等
    DATA_RECORD = "data_record"  # 数据记录段
    PRODUCT_INFO = "product_info"  # 产品信息段
    FOOTER = "footer"          # 页脚段
    UNKNOWN = "unknown"        # 未知段


class FieldType(Enum):
    """字段类型枚举"""
    STRING = "string"
    DATE = "date"
    NUMBER = "number"
    CURRENCY = "currency"
    CODE = "code"
    NAME = "name"
    PHONE = "phone"
    ADDRESS = "address"


@dataclass
class FieldDefinition:
    """字段定义"""
    name: str
    description: str
    segment_type: SegmentType
    keywords: List[str]
    start_pos: int
    length: int
    field_type: FieldType
    required: bool = False
    validation_pattern: Optional[str] = None
    sample_value: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "segment_type": self.segment_type.value,
            "keywords": self.keywords,
            "start_pos": self.start_pos,
            "length": self.length,
            "field_type": self.field_type.value,
            "required": self.required,
            "validation_pattern": self.validation_pattern,
            "sample_value": self.sample_value
        }


@dataclass
class SegmentDefinition:
    """数据段定义"""
    segment_type: SegmentType
    description: str
    line_patterns: List[str]  # 识别该段的行模式
    field_definitions: List[FieldDefinition] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "segment_type": self.segment_type.value,
            "description": self.description,
            "line_patterns": self.line_patterns,
            "field_definitions": [fd.to_dict() for fd in self.field_definitions]
        }


@dataclass
class DocumentSegment:
    """文档段实例"""
    segment_type: SegmentType
    start_line: int
    end_line: int
    lines: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "segment_type": self.segment_type.value,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "line_count": len(self.lines)
        }


class SmartTemplateAnalyzer:
    """智能样板文件分析器"""
    
    def __init__(self, template_file: str, encoding: str = "latin-1"):
        self.template_file = template_file
        self.encoding = encoding
        self.lines: List[str] = []
        self.segments: List[DocumentSegment] = []
        self.segment_definitions: Dict[SegmentType, SegmentDefinition] = {}
        
        # 加载样板文件
        self._load_template()
        
        # 初始化段定义
        self._initialize_segment_definitions()
    
    def _load_template(self):
        """加载样板文件"""
        with open(self.template_file, 'rb') as f:
            raw_data = f.read()
        
        content = raw_data.decode(self.encoding)
        self.lines = content.splitlines()
        
        print(f"样板文件: {self.template_file}")
        print(f"总行数: {len(self.lines)}")
    
    def _initialize_segment_definitions(self):
        """初始化段定义（基于PO.TXT分析）"""
        
        # 标题段定义
        header_def = SegmentDefinition(
            segment_type=SegmentType.HEADER,
            description="标题段：公司信息、地址、电话等",
            line_patterns=[
                r"^\s*[01]\s",  # 以0或1开头
                r"PARKER HANNIFIN",
                r"PH#.*\(\d{3}\)",
                r"FAX.*\(\d{3}\)"
            ]
        )
        
        # 数据记录段定义
        data_record_def = SegmentDefinition(
            segment_type=SegmentType.DATA_RECORD,
            description="数据记录段：人员记录",
            line_patterns=[
                r"^-\s+\d{2}/\d{2}/\d{2}",  # 以"-"开头，后跟日期
                r"^-\s+[A-Z]\s+[A-Z]{2}\s+[A-Z]+\s+[A-Z]+"  # 以"-"开头，后跟状态、缩写、名、姓
            ]
        )
        
        # 产品信息段定义
        product_info_def = SegmentDefinition(
            segment_type=SegmentType.PRODUCT_INFO,
            description="产品信息段：零件号、描述等",
            line_patterns=[
                r"\d+-\d+",  # 包含零件号
                r"PLATE.*MOLD",
                r"EA\s+\d+"
            ]
        )
        
        self.segment_definitions = {
            SegmentType.HEADER: header_def,
            SegmentType.DATA_RECORD: data_record_def,
            SegmentType.PRODUCT_INFO: product_info_def
        }
    
    def identify_segments(self) -> List[DocumentSegment]:
        """识别文档中的数据段"""
        print("\n识别文档数据段...")
        
        self.segments = []
        current_segment: Optional[DocumentSegment] = None
        
        for i, line in enumerate(self.lines):
            if not line.strip():
                continue  # 跳过空行
            
            # 确定当前行的段类型
            line_segment_type = self._identify_line_segment_type(line)
            
            # 如果当前没有段，或者段类型改变，开始新段
            if not current_segment or current_segment.segment_type != line_segment_type:
                # 保存当前段（如果有）
                if current_segment:
                    current_segment.end_line = i
                    self.segments.append(current_segment)
                
                # 开始新段
                current_segment = DocumentSegment(
                    segment_type=line_segment_type,
                    start_line=i + 1,
                    end_line=i + 1,
                    lines=[line]
                )
            else:
                # 继续当前段
                current_segment.lines.append(line)
                current_segment.end_line = i + 1
        
        # 添加最后一个段
        if current_segment:
            self.segments.append(current_segment)
        
        # 打印段统计
        print(f"识别到 {len(self.segments)} 个数据段")
        
        segment_counts = {}
        for segment in self.segments:
            seg_type = segment.segment_type
            segment_counts[seg_type] = segment_counts.get(seg_type, 0) + 1
        
        for seg_type, count in segment_counts.items():
            print(f"  {seg_type.value}: {count} 段")
        
        # 显示段详情
        print("\n段详情:")
        for segment in self.segments[:10]:  # 只显示前10段
            print(f"  行{segment.start_line}-{segment.end_line}: {segment.segment_type.value} ({len(segment.lines)}行)")
            if len(segment.lines) > 0:
                sample_line = segment.lines[0]
                print(f"    示例: {repr(sample_line[:60])}")
        
        return self.segments
    
    def _identify_line_segment_type(self, line: str) -> SegmentType:
        """识别单行的段类型"""
        # 检查数据记录段模式
        if line.strip().startswith('-') and len(line.strip()) > 1:
            # 检查是否包含日期模式
            if re.search(r'\d{2}/\d{2}/\d{2}', line):
                return SegmentType.DATA_RECORD
        
        # 检查标题段模式
        if line.strip().startswith(('0', '1')) or 'PARKER HANNIFIN' in line:
            return SegmentType.HEADER
        
        # 检查产品信息段模式
        if re.search(r'\d+-\d+', line) or 'PLATE' in line or 'MOLD' in line:
            return SegmentType.PRODUCT_INFO
        
        return SegmentType.UNKNOWN
    
    def analyze_data_record_segment(self) -> List[FieldDefinition]:
        """分析数据记录段"""
        print("\n分析数据记录段...")
        
        # 找到所有数据记录段
        data_segments = [s for s in self.segments if s.segment_type == SegmentType.DATA_RECORD]
        
        if not data_segments:
            print("未找到数据记录段")
            return []
        
        print(f"找到 {len(data_segments)} 个数据记录段")
        
        # 使用第一个数据记录段进行分析
        sample_segment = data_segments[0]
        sample_lines = sample_segment.lines
        
        print(f"使用第一个数据记录段进行分析 (行{sample_segment.start_line}-{sample_segment.end_line})")
        print(f"包含 {len(sample_lines)} 条数据记录")
        
        # 分析第一行数据记录
        if sample_lines:
            first_record = sample_lines[0]
            print(f"第一条记录: {repr(first_record[:80])}")
            
            # 分析记录结构
            field_defs = self._analyze_data_record_structure(first_record)
            
            # 验证字段定义在其他记录中的有效性
            self._validate_field_definitions(field_defs, sample_lines[:5])  # 验证前5条记录
            
            return field_defs
        
        return []
    
    def _analyze_data_record_structure(self, record_line: str) -> List[FieldDefinition]:
        """分析数据记录结构"""
        print("\n分析数据记录结构...")
        
        # 清理空字符
        clean_line = record_line.replace('\x00', ' ').strip()
        
        # 按空格分割
        parts = clean_line.split()
        
        print(f"按空格分割: {parts}")
        
        field_definitions = []
        
        # 定义字段映射（基于PO.TXT分析）
        field_mappings = [
            {
                "name": "record_type",
                "description": "记录类型标记",
                "keywords": ["-"],
                "field_type": FieldType.CODE,
                "required": True
            },
            {
                "name": "date",
                "description": "日期 (MM/DD/YY)",
                "keywords": ["04/09/12", "05/02/12", "01/26/12"],
                "field_type": FieldType.DATE,
                "required": True
            },
            {
                "name": "status",
                "description": "状态代码",
                "keywords": ["E", "I", "O"],
                "field_type": FieldType.CODE,
                "required": True
            },
            {
                "name": "initials",
                "description": "人员缩写",
                "keywords": ["BD", "DL", "PH", "JM", "WO", "JD"],
                "field_type": FieldType.CODE,
                "required": True
            },
            {
                "name": "first_name",
                "description": "名",
                "keywords": ["BRIAN", "DANNY", "GARY", "PAUL", "WILLIE", "JOHN"],
                "field_type": FieldType.NAME,
                "required": True
            },
            {
                "name": "last_name",
                "description": "姓",
                "keywords": ["DEARB", "LEUNG", "MCKENN", "HOLLMA", "ORTI", "DEUGEN"],
                "field_type": FieldType.NAME,
                "required": True
            }
        ]
        
        # 基于分割部分确定字段位置
        for i, part in enumerate(parts):
            if i < len(field_mappings):
                field_info = field_mappings[i]
                
                # 在原始行中查找该部分的位置
                start_pos = record_line.find(part)
                if start_pos != -1:
                    field_def = FieldDefinition(
                        name=field_info["name"],
                        description=field_info["description"],
                        segment_type=SegmentType.DATA_RECORD,
                        keywords=field_info["keywords"],
                        start_pos=start_pos,
                        length=len(part),
                        field_type=field_info["field_type"],
                        required=field_info["required"],
                        sample_value=part
                    )
                    
                    # 添加验证模式
                    if field_def.field_type == FieldType.DATE:
                        field_def.validation_pattern = r'\d{2}/\d{2}/\d{2}'
                    elif field_def.field_type == FieldType.CODE:
                        field_def.validation_pattern = r'^[A-Z]{1,3}$'
                    
                    field_definitions.append(field_def)
                    
                    print(f"  字段 {field_def.name}: 位置 {start_pos}-{start_pos+len(part)-1}, 值: {repr(part)}")
        
        return field_definitions
    
    def _validate_field_definitions(self, field_defs: List[FieldDefinition], sample_lines: List[str]):
        """验证字段定义"""
        print("\n验证字段定义...")
        
        for field_def in field_defs:
            print(f"\n验证字段: {field_def.name}")
            
            extracted_values = []
            for line in sample_lines:
                if field_def.start_pos < len(line):
                    end_pos = min(field_def.start_pos + field_def.length, len(line))
                    value = line[field_def.start_pos:end_pos].strip()
                    value = value.replace('\x00', '')
                    if value:
                        extracted_values.append(value)
            
            if extracted_values:
                unique_values = set(extracted_values)
                print(f"  提取到 {len(extracted_values)} 个值")
                print(f"  唯一值: {len(unique_values)} 个")
                print(f"  样本值: {list(unique_values)[:5]}")
            else:
                print(f"  警告: 未提取到值")
    
    def analyze_header_segment(self) -> List[FieldDefinition]:
        """分析标题段"""
        print("\n分析标题段...")
        
        # 找到标题段
        header_segments = [s for s in self.segments if s.segment_type == SegmentType.HEADER]
        
        if not header_segments:
            print("未找到标题段")
            return []
        
        print(f"找到 {len(header_segments)} 个标题段")
        
        # 使用第一个标题段进行分析
        sample_segment = header_segments[0]
        sample_lines = sample_segment.lines
        
        print(f"使用第一个标题段进行分析 (行{sample_segment.start_line}-{sample_segment.end_line})")
        
        field_definitions = []
        
        # 分析标题行
        for line in sample_lines:
            # 查找公司名称
            if 'PARKER HANNIFIN' in line:
                start_pos = line.find('PARKER')
                if start_pos != -1:
                    # 提取公司名称（直到行尾或特定字符）
                    company_part = line[start_pos:].strip()
                    
                    field_def = FieldDefinition(
                        name="company_name",
                        description="公司名称",
                        segment_type=SegmentType.HEADER,
                        keywords=["PARKER HANNIFIN CORPORATION", "PARKER HANNIFIN"],
                        start_pos=start_pos,
                        length=len(company_part),
                        field_type=FieldType.STRING,
                        required=False,
                        sample_value=company_part
                    )
                    field_definitions.append(field_def)
                    print(f"  公司名称: 位置 {start_pos}-{start_pos+len(company_part)-1}, 值: {repr(company_part)}")
            
            # 查找电话号码
            phone_match = re.search(r'\(\d{3}\) \d{3}-\d{4}', line)
            if phone_match:
                start_pos = phone_match.start()
                phone_number = phone_match.group(0)
                
                field_def = FieldDefinition(
                    name="phone",
                    description="电话号码",
                    segment_type=SegmentType.HEADER,
                    keywords=[phone_number],
                    start_pos=start_pos,
                    length=len(phone_number),
                    field_type=FieldType.PHONE,
                    required=False,
                    validation_pattern=r'\(\d{3}\) \d{3}-\d{4}',
                    sample_value=phone_number
                )
                field_definitions.append(field_def)
                print(f"  电话: 位置 {start_pos}-{start_pos+len(phone_number)-1}, 值: {repr(phone_number)}")
            
            # 查找地址
            if 'WAY' in line or 'CA' in line:
                # 尝试提取地址
                clean_line = line.replace('\x00', ' ').strip()
                if clean_line and not clean_line.startswith(('PH#', 'FAX')):
                    # 这可能是地址行
                    field_def = FieldDefinition(
                        name="address",
                        description="地址",
                        segment_type=SegmentType.HEADER,
                        keywords=["WAY", "CA", "SAN DIEGO"],
                        start_pos=0,
                        length=len(clean_line),
                        field_type=FieldType.ADDRESS,
                        required=False,
                        sample_value=clean_line
                    )
                    field_definitions.append(field_def)
                    print(f"  地址: 位置 0-{len(clean_line)-1}, 值: {repr(clean_line)}")
        
        return field_definitions
    
    def generate_configuration(self, app_name: str, app_code: str, 
                             template_name: str) -> Dict[str, Any]:
        """生成完整配置"""
        print(f"\n{'='*60}")
        print(f"生成完整配置")
        print(f"  应用: {app_name} ({app_code})")
        print(f"  模板: {template_name}")
        print(f"{'='*60}")
        
        # 识别段
        self.identify_segments()
        
        # 分析各段
        data_record_fields = self.analyze_data_record_segment()
        header_fields = self.analyze_header_segment()
        
        # 合并所有字段
        all_fields = data_record_fields + header_fields
        
        # 创建配置
        config = {
            "app_name": app_name,
            "app_code": app_code,
            "template_name": template_name,
            "file_extension": ".cld",
            "encoding": self.encoding,
            "description": f"基于样板文件 {self.template_file} 生成的配置",
            "segments": [segment.to_dict() for segment in self.segments[:10]],  # 只保存前10个段
            "field_definitions": [field.to_dict() for field in all_fields]
        }
        
        return config
    
    def save_configuration(self, config: Dict[str, Any], output_path: str):
        """保存配置到文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"\n配置已保存到: {output_path}")
        
        # 显示配置摘要
        print(f"\n配置摘要:")
        print(f"  应用: {config['app_name']} ({config['app_code']})")
        print(f"  模板: {config['template_name']}")
        print(f"  字段数: {len(config['field_definitions'])}")
        print(f"  段数: {len(config['segments'])}")
        
        # 显示字段列表
        print(f"\n字段列表:")
        for field in config['field_definitions']:
            print(f"  {field['name']}: {field['description']}")
            print(f"    段: {field['segment_type']}, 位置: {field['start_pos']}-{field['start_pos']+field['length']-1}")
            if field.get('sample_value'):
                print(f"    样本: {repr(field['sample_value'])}")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python smart_template_analyzer.py <样板文件路径> [--app-name APP_NAME] [--app-code APP_CODE] [--template-name TEMPLATE] [--output OUTPUT]")
        print("示例: python smart_template_analyzer.py PO.TXT --app-name 'Purchase Order' --app-code PO --template-name pcl_form.jasper --output smart_config.json")
        return
    
    template_file = sys.argv[1]
    
    # 解析参数
    app_name = "Purchase Order"
    app_code = "PO"
    template_name = "pcl_form.jasper"
    output_path = "smart_app_config.json"
    
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--app-name" and i + 1 < len(sys.argv):
            app_name = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--app-code" and i + 1 < len(sys.argv):
            app_code = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--template-name" and i + 1 < len(sys.argv):
            template_name = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--output" and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    print("智能样板文件分析器")
    print("=" * 60)
    
    # 创建分析器
    analyzer = SmartTemplateAnalyzer(template_file)
    
    # 生成配置
    config = analyzer.generate_configuration(
        app_name=app_name,
        app_code=app_code,
        template_name=template_name
    )
    
    # 保存配置
    analyzer.save_configuration(config, output_path)


if __name__ == "__main__":
    main()