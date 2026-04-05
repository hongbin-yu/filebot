#!/usr/bin/env python3
"""
.cld文件解析器
用于解析固定宽度文本格式的.cld文件（如PO.TXT）
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import json

@dataclass
class CldColumn:
    """列定义"""
    name: str
    start: int
    end: int
    dtype: str = "str"  # str, date, number, code
    
    def extract(self, line: str) -> str:
        """从行中提取列内容"""
        if self.start >= len(line):
            return ""
        end = min(self.end, len(line))
        return line[self.start:end].rstrip()
    
    def clean_value(self, value: str) -> str:
        """清理值：移除空字符和多余空格"""
        # 移除空字符
        value = value.replace('\x00', '')
        # 移除首尾空格
        value = value.strip()
        return value

@dataclass 
class CldRecord:
    """解析后的记录"""
    record_type: str  # 记录类型：-, 0, 1等
    line_number: int
    raw_line: str
    columns: Dict[str, str]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "record_type": self.record_type,
            "line_number": self.line_number,
            "columns": self.columns
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        cols = ", ".join(f"{k}={repr(v)}" for k, v in self.columns.items() if v)
        return f"CldRecord(type={self.record_type}, line={self.line_number}, {cols})"


class CldParser:
    """.cld文件解析器"""
    
    # 基于PO.TXT文件分析的列定义
    DEFAULT_COLUMNS = [
        CldColumn("record_marker", 0, 3, "code"),      # 记录标记：-, 0, 1
        CldColumn("date", 3, 15, "date"),             # 日期：MM/DD/YY
        CldColumn("status", 15, 21, "code"),          # 状态/代码：E, I等
        CldColumn("initials", 21, 26, "code"),        # 缩写：BD, DL等
        CldColumn("first_name", 26, 32, "str"),       # 名：BRIAN, DANNY
        CldColumn("last_name", 32, 39, "str"),        # 姓：DEARB, LEUNG
        CldColumn("field_1", 39, 48, "str"),          # 字段1（通常空字符填充）
        CldColumn("field_2", 48, 57, "str"),          # 字段2
        CldColumn("field_3", 57, 64, "str"),          # 字段3
        CldColumn("field_4", 64, 71, "str"),          # 字段4
        CldColumn("field_5", 71, 76, "str"),          # 字段5
        CldColumn("field_6", 76, 100, "str"),         # 字段6
    ]
    
    def __init__(self, column_defs: Optional[List[CldColumn]] = None):
        """初始化解析器"""
        self.columns = column_defs or self.DEFAULT_COLUMNS
        self.records: List[CldRecord] = []
        
    def parse_line(self, line: str, line_number: int) -> Optional[CldRecord]:
        """解析单行"""
        if not line.strip():
            return None  # 跳过空行
            
        # 确定记录类型（第一个非空格字符）
        record_type = ""
        for char in line:
            if char != ' ':
                record_type = char
                break
        
        # 提取各列数据
        columns_data = {}
        for col in self.columns:
            raw_value = col.extract(line)
            clean_value = col.clean_value(raw_value)
            if clean_value:  # 只保留非空值
                columns_data[col.name] = clean_value
        
        # 创建记录对象
        record = CldRecord(
            record_type=record_type,
            line_number=line_number,
            raw_line=line,
            columns=columns_data
        )
        
        return record
    
    def parse_file(self, file_path: str, encoding: str = "latin-1") -> List[CldRecord]:
        """解析整个文件"""
        self.records = []
        
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        
        # 解码文件
        content = raw_data.decode(encoding)
        lines = content.splitlines()
        
        # 解析每一行
        for i, line in enumerate(lines):
            record = self.parse_line(line, i+1)
            if record:
                self.records.append(record)
        
        return self.records
    
    def get_records_by_type(self, record_type: str) -> List[CldRecord]:
        """按记录类型筛选记录"""
        return [r for r in self.records if r.record_type == record_type]
    
    def get_dataframe(self) -> List[Dict[str, Any]]:
        """转换为类似数据框的结构（列表字典）"""
        return [r.to_dict() for r in self.records]
    
    def export_json(self, file_path: str):
        """导出为JSON文件"""
        data = self.get_dataframe()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def print_summary(self):
        """打印解析摘要"""
        print(f"解析完成，共 {len(self.records)} 条记录")
        
        # 按记录类型统计
        type_counts = {}
        for record in self.records:
            rt = record.record_type
            type_counts[rt] = type_counts.get(rt, 0) + 1
        
        print("记录类型统计:")
        for rt, count in sorted(type_counts.items()):
            print(f"  '{rt}': {count} 条")
        
        # 显示示例记录
        if self.records:
            print("\n示例记录（前5条）:")
            for i, record in enumerate(self.records[:5]):
                print(f"  {i+1}. {record}")
        
        # 显示列统计
        print("\n列数据统计（前10条记录）:")
        sample_records = self.records[:10]
        if sample_records:
            # 收集所有列名
            all_columns = set()
            for record in sample_records:
                all_columns.update(record.columns.keys())
            
            print(f"  发现列: {sorted(all_columns)}")


def analyze_file_structure(file_path: str):
    """分析文件结构并自动推断列定义"""
    print(f"分析文件结构: {file_path}")
    
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    
    content = raw_data.decode('latin-1')
    lines = content.splitlines()
    
    # 查找包含数据的行（非空行）
    data_lines = [line for line in lines if line.strip()]
    
    # 分析列边界
    column_boundaries = set()
    
    for line in data_lines[:20]:  # 分析前20行数据行
        prev_char = ' '
        for i, char in enumerate(line[:100]):  # 只分析前100个字符
            if prev_char == ' ' and char != ' ':
                column_boundaries.add(i)
            prev_char = char
    
    sorted_boundaries = sorted(column_boundaries)
    
    print(f"检测到 {len(sorted_boundaries)} 个列边界: {sorted_boundaries}")
    
    # 创建列定义
    columns = []
    for i in range(len(sorted_boundaries)):
        start = sorted_boundaries[i]
        end = sorted_boundaries[i+1] if i+1 < len(sorted_boundaries) else start + 10
        col_name = f"col_{i+1}"
        columns.append(CldColumn(col_name, start, end))
    
    return columns


def test_parser():
    """测试解析器"""
    print("测试.cld文件解析器")
    print("=" * 60)
    
    # 1. 分析文件结构
    print("1. 分析文件结构...")
    auto_columns = analyze_file_structure("PO.TXT")
    
    # 2. 使用默认列定义解析
    print("\n2. 使用默认列定义解析文件...")
    parser = CldParser()
    records = parser.parse_file("PO.TXT")
    
    # 3. 打印摘要
    parser.print_summary()
    
    # 4. 导出数据
    print("\n3. 导出解析结果...")
    parser.export_json("PO_parsed.json")
    print(f"  已导出到: PO_parsed.json")
    
    # 5. 显示特定类型的记录
    print("\n4. 显示'-'类型记录示例:")
    dash_records = parser.get_records_by_type('-')
    if dash_records:
        print(f"  找到 {len(dash_records)} 条'-'类型记录")
        for i, record in enumerate(dash_records[:3]):
            print(f"  示例{i+1}: {record}")
    
    # 6. 显示'0'类型记录
    print("\n5. 显示'0'类型记录示例:")
    zero_records = parser.get_records_by_type('0')
    if zero_records:
        print(f"  找到 {len(zero_records)} 条'0'类型记录")
        for i, record in enumerate(zero_records[:2]):
            print(f"  示例{i+1}: {record}")
            print(f"    原始行: {repr(record.raw_line[:80])}")
    
    return parser


if __name__ == "__main__":
    test_parser()