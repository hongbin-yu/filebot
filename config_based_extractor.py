#!/usr/bin/env python3
"""
配置驱动的索引提取器 - 使用JSON配置文件提取.cld文件数据
"""

import json
import re
import sys
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExtractedRecord:
    """提取的记录"""
    line_number: int
    record_type: str
    fields: Dict[str, str]
    raw_line: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "line_number": self.line_number,
            "record_type": self.record_type,
            "fields": self.fields,
            "raw_line_preview": repr(self.raw_line[:80]) if self.raw_line else ""
        }


class ConfigBasedExtractor:
    """配置驱动的提取器"""
    
    def __init__(self, config_path: str):
        """初始化提取器"""
        self.config = self._load_config(config_path)
        self.extracted_records: List[ExtractedRecord] = []
        self.statistics: Dict[str, Any] = {}
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"加载配置文件: {config_path}")
        print(f"应用程序: {config.get('app_name')} ({config.get('app_code')})")
        print(f"模板: {config.get('template_name')}")
        print(f"字段数: {len(config.get('field_definitions', []))}")
        
        return config
    
    def extract_from_file(self, file_path: str) -> Dict[str, Any]:
        """从文件提取数据"""
        print(f"\n提取文件: {file_path}")
        
        # 检查文件扩展名
        if self.config.get('file_extension') and not file_path.endswith(self.config['file_extension']):
            print(f"警告: 文件扩展名不是 {self.config['file_extension']}")
        
        # 读取文件
        encoding = self.config.get('encoding', 'latin-1')
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        
        content = raw_data.decode(encoding)
        lines = content.splitlines()
        
        print(f"总行数: {len(lines)}")
        
        # 重置状态
        self.extracted_records = []
        
        # 提取数据
        self._extract_records(lines)
        
        # 生成统计信息
        self._generate_statistics()
        
        return self.get_extraction_summary()
    
    def _extract_records(self, lines: List[str]):
        """提取记录"""
        field_defs = self.config.get('field_definitions', [])
        
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            
            # 根据配置提取字段
            extracted_fields = {}
            record_type = None
            
            for field_def in field_defs:
                field_name = field_def['name']
                start_pos = field_def['start_pos']
                length = field_def['length']
                
                # 检查是否在行范围内
                if start_pos < len(line):
                    end_pos = min(start_pos + length, len(line))
                    value = line[start_pos:end_pos].strip()
                    
                    # 清理空字符
                    value = value.replace('\x00', '')
                    
                    # 如果值不为空，添加到提取字段
                    if value:
                        extracted_fields[field_name] = value
                        
                        # 如果是记录类型字段，设置记录类型
                        if field_name == 'record_type':
                            record_type = value
            
            # 如果有提取到字段，创建记录
            if extracted_fields:
                record = ExtractedRecord(
                    line_number=i + 1,
                    record_type=record_type or 'unknown',
                    fields=extracted_fields,
                    raw_line=line
                )
                self.extracted_records.append(record)
    
    def _generate_statistics(self):
        """生成统计信息"""
        total_records = len(self.extracted_records)
        
        # 按记录类型统计
        record_type_counts = {}
        for record in self.extracted_records:
            rt = record.record_type
            record_type_counts[rt] = record_type_counts.get(rt, 0) + 1
        
        # 字段出现统计
        field_counts = {}
        field_value_counts = {}
        
        for record in self.extracted_records:
            for field_name, value in record.fields.items():
                # 字段出现次数
                field_counts[field_name] = field_counts.get(field_name, 0) + 1
                
                # 字段值统计
                if field_name not in field_value_counts:
                    field_value_counts[field_name] = {}
                field_value_counts[field_name][value] = field_value_counts[field_name].get(value, 0) + 1
        
        self.statistics = {
            "total_records": total_records,
            "record_type_counts": record_type_counts,
            "field_counts": field_counts,
            "field_value_counts": field_value_counts
        }
    
    def get_extraction_summary(self) -> Dict[str, Any]:
        """获取提取摘要"""
        summary = {
            "app_name": self.config.get('app_name'),
            "app_code": self.config.get('app_code'),
            "template_name": self.config.get('template_name'),
            "extraction_time": datetime.now().isoformat(),
            "statistics": self.statistics,
            "records": [record.to_dict() for record in self.extracted_records],
            "config_summary": {
                "field_count": len(self.config.get('field_definitions', [])),
                "field_names": [fd['name'] for fd in self.config.get('field_definitions', [])]
            }
        }
        
        return summary
    
    def print_summary(self):
        """打印提取摘要"""
        print(f"\n{'='*60}")
        print("提取摘要")
        print(f"{'='*60}")
        
        print(f"应用程序: {self.config.get('app_name')} ({self.config.get('app_code')})")
        print(f"提取记录: {self.statistics.get('total_records', 0)} 条")
        
        # 记录类型统计
        rt_counts = self.statistics.get('record_type_counts', {})
        if rt_counts:
            print(f"\n记录类型统计:")
            for rt, count in sorted(rt_counts.items()):
                print(f"  '{rt}': {count} 条")
        
        # 字段提取统计
        field_counts = self.statistics.get('field_counts', {})
        if field_counts:
            print(f"\n字段提取统计:")
            for field_name, count in sorted(field_counts.items()):
                unique_values = len(self.statistics.get('field_value_counts', {}).get(field_name, {}))
                print(f"  {field_name}: {count} 次 ({unique_values} 个唯一值)")
        
        # 显示示例记录
        if self.extracted_records:
            print(f"\n示例记录 (前5条):")
            for i, record in enumerate(self.extracted_records[:5]):
                print(f"  记录 {i+1} (行{record.line_number}, 类型: {record.record_type}):")
                for field_name, value in record.fields.items():
                    print(f"    {field_name}: {repr(value)}")
    
    def export_json(self, file_path: str):
        """导出提取结果为JSON文件"""
        summary = self.get_extraction_summary()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"\n提取结果已导出到: {file_path}")
    
    def export_csv(self, file_path: str):
        """导出提取结果为CSV文件"""
        if not self.extracted_records:
            print("没有提取记录可导出")
            return
        
        # 获取所有字段名
        all_field_names = set()
        for record in self.extracted_records:
            all_field_names.update(record.fields.keys())
        
        field_names = sorted(all_field_names)
        
        # 写入CSV
        import csv
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 写入标题行
            headers = ['line_number', 'record_type'] + field_names
            writer.writerow(headers)
            
            # 写入数据行
            for record in self.extracted_records:
                row = [record.line_number, record.record_type]
                row.extend([record.fields.get(field, '') for field in field_names])
                writer.writerow(row)
        
        print(f"CSV结果已导出到: {file_path}")


def test_with_po_config():
    """使用PO配置测试提取器"""
    print("配置驱动的索引提取器测试")
    print("=" * 60)
    
    # 创建提取器
    extractor = ConfigBasedExtractor("correct_po_config.json")
    
    # 提取PO.TXT文件
    summary = extractor.extract_from_file("PO.TXT")
    
    # 打印摘要
    extractor.print_summary()
    
    # 导出结果
    extractor.export_json("config_based_extraction.json")
    extractor.export_csv("config_based_extraction.csv")
    
    # 显示详细统计
    print(f"\n{'='*60}")
    print("详细字段值统计")
    print(f"{'='*60}")
    
    field_value_counts = extractor.statistics.get('field_value_counts', {})
    for field_name, value_counts in field_value_counts.items():
        print(f"\n{field_name} 值分布:")
        unique_count = len(value_counts)
        if unique_count <= 10:
            for value, count in sorted(value_counts.items()):
                print(f"  {repr(value)}: {count} 次")
        else:
            print(f"  共 {unique_count} 个唯一值")
            # 显示前10个最常见的值
            sorted_values = sorted(value_counts.items(), key=lambda x: x[1], reverse=True)
            for value, count in sorted_values[:10]:
                print(f"  {repr(value)}: {count} 次")
    
    return extractor


def validate_extraction(extractor: ConfigBasedExtractor) -> Dict[str, Any]:
    """验证提取结果"""
    print(f"\n{'='*60}")
    print("提取结果验证")
    print(f"{'='*60}")
    
    validation_results = {
        "total_records": len(extractor.extracted_records),
        "validated_records": 0,
        "errors": [],
        "warnings": []
    }
    
    # 检查必填字段
    field_defs = extractor.config.get('field_definitions', [])
    required_fields = [fd['name'] for fd in field_defs if fd.get('required', False)]
    
    if required_fields:
        print(f"必填字段: {required_fields}")
        
        missing_counts = {field: 0 for field in required_fields}
        
        for record in extractor.extracted_records:
            for field in required_fields:
                if field not in record.fields:
                    missing_counts[field] += 1
        
        for field, count in missing_counts.items():
            if count > 0:
                error_msg = f"字段 '{field}' 在 {count} 条记录中缺失"
                validation_results["errors"].append(error_msg)
                print(f"  错误: {error_msg}")
    
    # 检查字段验证模式
    for field_def in field_defs:
        field_name = field_def['name']
        pattern = field_def.get('validation_pattern')
        
        if pattern:
            print(f"\n验证字段 '{field_name}' 模式: {pattern}")
            
            invalid_count = 0
            for record in extractor.extracted_records:
                if field_name in record.fields:
                    value = record.fields[field_name]
                    if not re.match(pattern, value):
                        invalid_count += 1
            
            if invalid_count > 0:
                warning_msg = f"字段 '{field_name}' 有 {invalid_count} 个值不符合验证模式"
                validation_results["warnings"].append(warning_msg)
                print(f"  警告: {warning_msg}")
    
    validation_results["validated_records"] = validation_results["total_records"] - len(validation_results["errors"])
    
    print(f"\n验证完成:")
    print(f"  总记录数: {validation_results['total_records']}")
    print(f"  已验证记录: {validation_results['validated_records']}")
    print(f"  错误数: {len(validation_results['errors'])}")
    print(f"  警告数: {len(validation_results['warnings'])}")
    
    return validation_results


def main():
    """主函数"""
    if len(sys.argv) < 3:
        print("用法: python config_based_extractor.py <配置文件路径> <cld文件路径>")
        print("示例: python config_based_extractor.py correct_po_config.json PO.TXT")
        return
    
    config_path = sys.argv[1]
    cld_file_path = sys.argv[2]
    
    # 创建提取器
    extractor = ConfigBasedExtractor(config_path)
    
    # 提取文件
    extractor.extract_from_file(cld_file_path)
    
    # 打印摘要
    extractor.print_summary()
    
    # 验证结果
    validation_results = validate_extraction(extractor)
    
    # 导出结果
    base_name = os.path.splitext(os.path.basename(cld_file_path))[0]
    extractor.export_json(f"{base_name}_extracted.json")
    extractor.export_csv(f"{base_name}_extracted.csv")
    
    print(f"\n提取完成!")


if __name__ == "__main__":
    # 如果没有参数，运行测试
    if len(sys.argv) == 1:
        test_with_po_config()
    else:
        main()