#!/usr/bin/env python3
"""
解析Smart iAdmin HSQLDB .script文件
直接从.script文件提取INSERT语句，生成CSV文件

用法:
  python3 parse_smarti_script.py --input /path/to/smarti.script --output-dir ./data
  python3 parse_smarti_script.py --input /path/to/smarti.script --table COLD_REPORT
"""

import argparse
import re
import csv
import os
from pathlib import Path
import logging
from typing import Dict, List, Optional, Set

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SmartIScriptParser:
    def __init__(self, script_path: str):
        self.script_path = script_path
        self.content = ""
        self.tables: Dict[str, List[List[str]]] = {}
        
    def load(self):
        """加载.script文件"""
        logger.info(f"加载文件: {self.script_path}")
        with open(self.script_path, 'r', encoding='utf-8', errors='ignore') as f:
            self.content = f.read()
        logger.info(f"文件大小: {len(self.content)} 字节")
        
    def extract_table_names(self) -> Set[str]:
        """提取所有表名"""
        # 查找所有INSERT INTO语句
        pattern = r'INSERT INTO ([A-Z_][A-Z0-9_]*)'
        tables = set(re.findall(pattern, self.content, re.IGNORECASE))
        logger.info(f"找到 {len(tables)} 个表")
        return tables
    
    def parse_insert_statements(self, table_name: str) -> List[List[str]]:
        """解析特定表的所有INSERT语句"""
        # 查找该表的所有INSERT语句
        pattern = rf'INSERT INTO {table_name}\s*\((.*?)\)\s*VALUES\s*\((.*?)\);'
        matches = re.findall(pattern, self.content, re.IGNORECASE | re.DOTALL)
        
        if not matches:
            # 尝试简化匹配，可能没有列名
            pattern = rf'INSERT INTO {table_name}\s*VALUES\s*\((.*?)\);'
            matches = re.findall(pattern, self.content, re.IGNORECASE | re.DOTALL)
            if matches:
                # 对于没有列名的INSERT，返回空列名
                return [["数据", row] for row in matches]
            return []
        
        rows = []
        for columns_str, values_str in matches:
            # 解析列名
            columns = [col.strip().strip('"') for col in columns_str.split(',')]
            
            # 解析值 - 处理可能包含逗号的值（在引号内）
            values = self.parse_values(values_str)
            
            if len(values) == len(columns):
                rows.append(values)
            else:
                logger.warning(f"列数不匹配: {table_name} ({len(columns)}列, {len(values)}值)")
                # 仍然添加行，用None填充缺失值
                rows.append(values)
        
        return rows
    
    def parse_values(self, values_str: str) -> List[str]:
        """解析VALUES子句中的值"""
        values = []
        current_value = ""
        in_quotes = False
        escape_next = False
        
        for i, char in enumerate(values_str):
            if escape_next:
                current_value += char
                escape_next = False
            elif char == '\\' and i + 1 < len(values_str):
                escape_next = True
            elif char == "'" and not escape_next:
                in_quotes = not in_quotes
                current_value += char
            elif char == ',' and not in_quotes:
                values.append(current_value.strip())
                current_value = ""
            else:
                current_value += char
        
        # 添加最后一个值
        if current_value:
            values.append(current_value.strip())
        
        # 清理值：移除多余引号
        cleaned_values = []
        for val in values:
            if val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            cleaned_values.append(val)
        
        return cleaned_values
    
    def extract_table(self, table_name: str) -> Optional[List[List[str]]]:
        """提取特定表的数据"""
        logger.info(f"提取表: {table_name}")
        rows = self.parse_insert_statements(table_name)
        if rows:
            logger.info(f"找到 {len(rows)} 条记录")
            return rows
        else:
            logger.warning(f"表中没有数据: {table_name}")
            return None
    
    def export_to_csv(self, table_name: str, rows: List[List[str]], output_dir: str):
        """导出数据到CSV文件"""
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{table_name.lower()}.csv")
        
        # 尝试检测列名（从第一个INSERT语句）
        first_insert = self.find_first_insert(table_name)
        columns = self.extract_columns_from_insert(first_insert) if first_insert else []
        
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            
            if columns:
                writer.writerow(columns)
                logger.info(f"使用列名: {columns}")
            
            for row in rows:
                writer.writerow(row)
        
        logger.info(f"导出到: {output_path}")
        return output_path
    
    def find_first_insert(self, table_name: str) -> Optional[str]:
        """查找表的第一个INSERT语句"""
        pattern = rf'INSERT INTO {table_name}.*?;'
        match = re.search(pattern, self.content, re.IGNORECASE | re.DOTALL)
        return match.group(0) if match else None
    
    def extract_columns_from_insert(self, insert_stmt: str) -> List[str]:
        """从INSERT语句提取列名"""
        # 匹配 INSERT INTO table (col1, col2, ...) VALUES (...)
        pattern = r'INSERT INTO [A-Z_][A-Z0-9_]*\s*\((.*?)\)\s*VALUES'
        match = re.search(pattern, insert_stmt, re.IGNORECASE | re.DOTALL)
        if match:
            columns_str = match.group(1)
            columns = [col.strip().strip('"') for col in columns_str.split(',')]
            return columns
        return []

def main():
    parser = argparse.ArgumentParser(description='解析Smart iAdmin HSQLDB .script文件')
    parser.add_argument('--input', required=True, help='输入.script文件路径')
    parser.add_argument('--output-dir', default='./smarti_data', help='输出目录 (默认: ./smarti_data)')
    parser.add_argument('--table', help='只导出指定表 (默认: 导出所有表)')
    parser.add_argument('--list-tables', action='store_true', help='只列出表名，不导出')
    
    args = parser.parse_args()
    
    parser = SmartIScriptParser(args.input)
    parser.load()
    
    tables = parser.extract_table_names()
    
    if args.list_tables:
        print(f"\n找到 {len(tables)} 个表:")
        for table in sorted(tables):
            print(f"  - {table}")
        return
    
    if args.table:
        if args.table.upper() in tables:
            tables = {args.table.upper()}
        else:
            logger.error(f"表未找到: {args.table}")
            logger.info(f"可用表: {sorted(tables)}")
            return
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    results = {}
    for table in sorted(tables):
        rows = parser.extract_table(table)
        if rows:
            output_path = parser.export_to_csv(table, rows, args.output_dir)
            results[table] = len(rows)
    
    # 生成摘要
    print(f"\n✅ 导出完成!")
    print(f"输出目录: {args.output_dir}")
    print(f"导出表数: {len(results)}")
    print(f"总记录数: {sum(results.values())}")
    print("\n📋 导出摘要:")
    for table, count in results.items():
        print(f"  {table}: {count} 条记录 -> {table.lower()}.csv")

if __name__ == '__main__':
    main()