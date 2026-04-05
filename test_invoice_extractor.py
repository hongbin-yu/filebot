#!/usr/bin/env python3
"""
测试发票提取器 - 使用从COLD_INDEXES转换的配置提取发票数据
"""

import json
import re
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path


class InvoiceExtractor:
    """基于COLD_INDEXES配置的发票提取器"""
    
    def __init__(self, config_path: str):
        """初始化提取器"""
        self.config = self._load_config(config_path)
        self.fields = self.config.get('fields', [])
        
        # 按层级和起始位置排序字段
        self.fields.sort(key=lambda f: (f.get('metadata', {}).get('levelid', 0), 
                                       f.get('start', 0)))
        
        print(f"加载配置: {self.config.get('name')}")
        print(f"描述: {self.config.get('description')}")
        print(f"字段数: {len(self.fields)}")
        
        # 按层级分组
        self.fields_by_level = {}
        for field in self.fields:
            levelid = field.get('metadata', {}).get('levelid', 0)
            if levelid not in self.fields_by_level:
                self.fields_by_level[levelid] = []
            self.fields_by_level[levelid].append(field)
        
        for levelid, fields in self.fields_by_level.items():
            print(f"  层级 {levelid}: {len(fields)} 个字段")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载JSON配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def extract_invoice(self, invoice_path: str) -> Dict[str, Any]:
        """提取发票数据"""
        print(f"\n提取发票文件: {invoice_path}")
        
        with open(invoice_path, 'r', encoding='utf-8') as f:
            lines = [line.rstrip('\n') for line in f]
        
        print(f"总行数: {len(lines)}")
        
        # 分析文件结构
        result = {
            "invoice_header": {},
            "invoice_lines": [],
            "totals": {},
            "metadata": {}
        }
        
        # 查找发票头（以7位数字开头的行）
        header_lines = []
        for i, line in enumerate(lines):
            if re.match(r'^\d{7}\s+\d{5}', line):
                header_lines.append((i, line))
        
        print(f"找到 {len(header_lines)} 个发票头")
        
        if header_lines:
            # 提取第一个发票头
            line_num, header_line = header_lines[0]
            header_data = self._extract_from_line(header_line, levelid=1)
            result["invoice_header"] = header_data
            
            # 查找订单行
            order_line = None
            for i in range(line_num, min(line_num + 20, len(lines))):
                if 'REF. ORDER/RELEASE #' in lines[i]:
                    order_line = (i, lines[i])
                    break
            
            if order_line:
                # 解析订单行
                order_match = re.search(r'REF\. ORDER/RELEASE #\s*(\d+)/(\d+)', order_line[1])
                if order_match:
                    result["invoice_header"]["order_number"] = order_match.group(1)
                    result["invoice_header"]["release_number"] = order_match.group(2)
            
            # 提取行项目
            result["invoice_lines"] = self._extract_invoice_lines(lines, line_num)
        
        return result
    
    def _extract_from_line(self, line: str, levelid: int) -> Dict[str, str]:
        """从单行提取指定层级的字段"""
        extracted = {}
        
        if levelid not in self.fields_by_level:
            return extracted
        
        for field in self.fields_by_level[levelid]:
            name = field['name']
            start = field['start'] - 1  # 转换为0-based
            length = field['length']
            
            # 检查偏移
            offset = field.get('offset', 0)
            
            # 提取字段值
            if start + offset + length <= len(line):
                value = line[start + offset:start + offset + length].strip()
                
                # 应用验证规则
                if 'validation' in field:
                    value = self._apply_validation(value, field['validation'])
                
                extracted[name] = value
        
        return extracted
    
    def _apply_validation(self, value: str, validation: Dict[str, Any]) -> str:
        """应用验证和转换规则"""
        if not value:
            return value
        
        # 应用替换规则
        if 'replaces' in validation and validation['replaces']:
            value = value.replace(validation['replaces'], '')
        
        # 应用左侧修剪
        if 'trim_left' in validation and validation['trim_left']:
            value = value.lstrip(validation['trim_left'])
        
        return value
    
    def _extract_invoice_lines(self, lines: List[str], header_line_num: int) -> List[Dict[str, Any]]:
        """提取发票行项目"""
        invoice_lines = []
        
        # 查找行项目（以3位数字开头的行，如"002 NH-..."）
        for i in range(header_line_num, len(lines)):
            line = lines[i]
            
            # 检查是否为行项目行
            if re.match(r'^\s*\d{3}\s+NH-', line):
                # 提取行项目数据
                line_data = self._extract_from_line(line, levelid=2)
                
                if line_data:
                    # 添加行号信息
                    line_data['line_number'] = i + 1
                    
                    # 尝试提取序号
                    seq_match = re.match(r'^\s*(\d{3})', line)
                    if seq_match:
                        line_data['sequence'] = seq_match.group(1).strip()
                    
                    invoice_lines.append(line_data)
        
        print(f"找到 {len(invoice_lines)} 个行项目")
        return invoice_lines
    
    def print_extraction_summary(self, extraction_result: Dict[str, Any]):
        """打印提取结果摘要"""
        print("\n" + "="*60)
        print("发票提取结果摘要")
        print("="*60)
        
        # 发票头信息
        header = extraction_result.get('invoice_header', {})
        if header:
            print("\n发票头信息:")
            for key, value in header.items():
                if value:  # 只显示非空值
                    print(f"  {key}: {value}")
        
        # 行项目
        lines = extraction_result.get('invoice_lines', [])
        if lines:
            print(f"\n行项目 ({len(lines)} 个):")
            for i, line in enumerate(lines[:5]):  # 显示前5个
                print(f"  行 {i+1}: {line.get('PART_NO', 'N/A')} - "
                      f"数量: {line.get('QTY', 'N/A')}, "
                      f"单价: {line.get('UNIT_PRICE', 'N/A')}, "
                      f"金额: {line.get('LINE_AMOUNT', 'N/A')}")
            
            if len(lines) > 5:
                print(f"  ... 和 {len(lines) - 5} 个更多行项目")
        
        # 总计
        totals = extraction_result.get('totals', {})
        if totals:
            print("\n总计信息:")
            for key, value in totals.items():
                print(f"  {key}: {value}")


def main():
    """主函数"""
    if len(sys.argv) < 3:
        print("用法: python test_invoice_extractor.py <config.json> <invoice.txt>")
        print("示例: python test_invoice_extractor.py invoice_config.json 'INVOICE - Test.txt'")
        sys.exit(1)
    
    config_path = sys.argv[1]
    invoice_path = sys.argv[2]
    
    # 检查文件是否存在
    if not Path(config_path).exists():
        print(f"错误: 配置文件不存在: {config_path}")
        sys.exit(1)
    
    if not Path(invoice_path).exists():
        print(f"错误: 发票文件不存在: {invoice_path}")
        sys.exit(1)
    
    # 创建提取器并提取数据
    extractor = InvoiceExtractor(config_path)
    result = extractor.extract_invoice(invoice_path)
    
    # 打印结果
    extractor.print_extraction_summary(result)
    
    # 保存结果到JSON文件
    output_path = Path(invoice_path).stem + '_extracted.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n完整结果已保存到: {output_path}")


if __name__ == "__main__":
    main()