#!/usr/bin/env python3
"""
Smart iAdmin COLD_REPORT to JSON配置转换器

将Smart iAdmin系统的COLD_REPORT表结构及相关数据转换为FileBot兼容的JSON配置格式。

包含:
- COLD_REPORT表: 报表级别配置
- COLD_INDEXES表: 索引字段配置 (通过REPORTID关联)
- COLD_FIELDINFO表: 字段信息配置 (通过REPORTID关联)

输出: 每个COLD_REPORT记录生成一个JSON配置文件，包含完整的数据提取配置。
"""

import json
import re
import sys
import csv
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
import xml.etree.ElementTree as ET
from pathlib import Path


@dataclass
class ColdReportRecord:
    """COLD_REPORT表记录"""
    id: int
    setid: Optional[int]
    sourceid: int
    dispositionid: Optional[int]
    appid: int
    sampleid: Optional[int]
    extern_id: Optional[int]
    formid: int
    recordclassid: Optional[int]
    indexid: int
    levelid: Optional[int]
    textfieldsid: Optional[int]
    auditid: Optional[int]
    name: str
    comments: Optional[str]
    seperator: Optional[str]
    allowdups: Optional[int]
    reptable: Optional[str]
    store_in_db: Optional[int]
    index_pages: Optional[str]
    modify_date: Optional[str]
    enter: Optional[int]
    duration: Optional[int]
    durationunit: Optional[int]
    deviceid: Optional[int]


@dataclass
class ColdFieldinfoRecord:
    """COLD_FIELDINFO表记录"""
    textfieldsid: int
    seq: int
    reportid: int
    formid: int
    icolumn: Optional[int]
    length: Optional[int]
    start_row: Optional[int]
    end_row: Optional[int]
    txtsrch_fld: Optional[int]
    export_fld: Optional[int]
    index_fld: Optional[int]
    pattern: Optional[str]
    lefttrim: Optional[str]
    left_offset: Optional[int]


@dataclass 
class ColdIndexRecord:
    """COLD_INDEXES表记录（简化版，用于关联）"""
    id: int
    levelid: int
    auditid: int
    page: int
    irow: int
    coln: int
    length: int
    literal: Optional[str]
    sample: Optional[str]
    lefttrim: Optional[str]
    usepattern: Optional[str]
    invalid_action: Optional[int]
    pattern: Optional[str]
    replaces: Optional[str]
    table_name: Optional[str]
    column_name: Optional[str]
    key_field_name: Optional[str]
    key_levelid: Optional[int]
    date_format: Optional[str]
    left_offset: Optional[int]


class ColdReportConverter:
    """COLD_REPORT转换器"""
    
    def __init__(self):
        self.namespace = {
            'hibernate': 'http://hibernate.sourceforge.net/hibernate-mapping-3.0.dtd'
        }
        self.cold_reports: Dict[int, ColdReportRecord] = {}
        self.cold_fieldinfos: Dict[int, List[ColdFieldinfoRecord]] = {}  # reportid -> list
        self.cold_indexes: Dict[int, List[ColdIndexRecord]] = {}  # id -> list (注意：COLD_INDEXES.ID对应COLD_REPORT.ID)
    
    def parse_hbm_xml(self, xml_path: str) -> Dict[str, Any]:
        """解析Hibernate映射XML文件"""
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # 解析class元素
        class_elem = root.find('hibernate:class', self.namespace)
        if class_elem is None:
            class_elem = root.find('class')  # 尝试无命名空间
        
        table_info = {
            'table_name': class_elem.get('table') if class_elem is not None else '',
            'schema': class_elem.get('schema') if class_elem is not None else '',
            'fields': []
        }
        
        # 解析property元素
        properties = []
        if class_elem is not None:
            properties = class_elem.findall('hibernate:property', self.namespace)
            if not properties:
                properties = class_elem.findall('property')
        
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
    
    def load_cold_reports_csv(self, csv_path: str) -> bool:
        """从CSV文件加载COLD_REPORT表数据"""
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # 提取字段值
                    report_id = self._get_int(row, ['ID', 'id', 'Id'])
                    if report_id is None:
                        print(f"警告: 跳过行，缺少ID字段: {row}")
                        continue
                    
                    record = ColdReportRecord(
                        id=report_id,
                        setid=self._get_int(row, ['SETID', 'setid', 'SetId']),
                        sourceid=self._get_int(row, ['SOURCEID', 'sourceid', 'SourceId'], required=True),
                        dispositionid=self._get_int(row, ['DISPOSITIONID', 'dispositionid', 'DispositionId']),
                        appid=self._get_int(row, ['APPID', 'appid', 'AppId'], required=True),
                        sampleid=self._get_int(row, ['SAMPLEID', 'sampleid', 'SampleId']),
                        extern_id=self._get_int(row, ['EXTERN_ID', 'extern_id', 'ExternId']),
                        formid=self._get_int(row, ['FORMID', 'formid', 'FormId'], required=True),
                        recordclassid=self._get_int(row, ['RECORDCLASSID', 'recordclassid', 'RecordClassId']),
                        indexid=self._get_int(row, ['INDEXID', 'indexid', 'IndexId'], required=True),
                        levelid=self._get_int(row, ['LEVELID', 'levelid', 'LevelId']),
                        textfieldsid=self._get_int(row, ['TEXTFIELDSID', 'textfieldsid', 'TextFieldsId']),
                        auditid=self._get_int(row, ['AUDITID', 'auditid', 'AuditId']),
                        name=self._get_value(row, ['NAME', 'name', 'Name'], required=True),
                        comments=self._get_value(row, ['COMMENTS', 'comments', 'Comments']),
                        seperator=self._get_value(row, ['SEPERATOR', 'seperator', 'Seperator']),
                        allowdups=self._get_int(row, ['ALLOWDUPS', 'allowdups', 'AllowDups']),
                        reptable=self._get_value(row, ['REPTABLE', 'reptable', 'RepTable']),
                        store_in_db=self._get_int(row, ['STORE_IN_DB', 'store_in_db', 'StoreInDb']),
                        index_pages=self._get_value(row, ['INDEX_PAGES', 'index_pages', 'IndexPages']),
                        modify_date=self._get_value(row, ['MODIFY_DATE', 'modify_date', 'ModifyDate']),
                        enter=self._get_int(row, ['ENTER', 'enter', 'Enter']),
                        duration=self._get_int(row, ['DURATION', 'duration', 'Duration']),
                        durationunit=self._get_int(row, ['DURATIONUNIT', 'durationunit', 'DurationUnit']),
                        deviceid=self._get_int(row, ['DEVICEID', 'deviceid', 'DeviceId'])
                    )
                    
                    self.cold_reports[report_id] = record
            
            print(f"成功读取 {len(self.cold_reports)} 个COLD_REPORT记录")
            return True
            
        except Exception as e:
            print(f"读取COLD_REPORT CSV文件错误: {e}")
            return False
    
    def load_cold_fieldinfos_csv(self, csv_path: str) -> bool:
        """从CSV文件加载COLD_FIELDINFO表数据"""
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # 提取字段值
                    reportid = self._get_int(row, ['REPORTID', 'reportid', 'ReportId'])
                    if reportid is None:
                        print(f"警告: 跳过行，缺少REPORTID字段: {row}")
                        continue
                    
                    record = ColdFieldinfoRecord(
                        textfieldsid=self._get_int(row, ['TEXTFIELDSID', 'textfieldsid', 'TextFieldsId'], required=True),
                        seq=self._get_int(row, ['SEQ', 'seq', 'Seq'], required=True),
                        reportid=reportid,
                        formid=self._get_int(row, ['FORMID', 'formid', 'FormId'], required=True),
                        icolumn=self._get_int(row, ['ICOLUMN', 'icolumn', 'Icolumn']),
                        length=self._get_int(row, ['LENGTH', 'length', 'Length']),
                        start_row=self._get_int(row, ['START_ROW', 'start_row', 'StartRow']),
                        end_row=self._get_int(row, ['END_ROW', 'end_row', 'EndRow']),
                        txtsrch_fld=self._get_int(row, ['TXTSRCH_FLD', 'txtsrch_fld', 'TxtsrchFld']),
                        export_fld=self._get_int(row, ['EXPORT_FLD', 'export_fld', 'ExportFld']),
                        index_fld=self._get_int(row, ['INDEX_FLD', 'index_fld', 'IndexFld']),
                        pattern=self._get_value(row, ['PATTERN', 'pattern', 'Pattern']),
                        lefttrim=self._get_value(row, ['LEFTTRIM', 'lefttrim', 'LeftTrim']),
                        left_offset=self._get_int(row, ['LEFT_OFFSET', 'left_offset', 'LeftOffset'])
                    )
                    
                    if reportid not in self.cold_fieldinfos:
                        self.cold_fieldinfos[reportid] = []
                    
                    self.cold_fieldinfos[reportid].append(record)
            
            total_records = sum(len(records) for records in self.cold_fieldinfos.values())
            print(f"成功读取 {total_records} 个COLD_FIELDINFO记录")
            return True
            
        except Exception as e:
            print(f"读取COLD_FIELDINFO CSV文件错误: {e}")
            return False
    
    def load_cold_indexes_csv(self, csv_path: str) -> bool:
        """从CSV文件加载COLD_INDEXES表数据"""
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # 注意：COLD_INDEXES.ID字段对应COLD_REPORT.ID
                    index_id = self._get_int(row, ['ID', 'id', 'Id'])
                    if index_id is None:
                        print(f"警告: 跳过行，缺少ID字段: {row}")
                        continue
                    
                    record = ColdIndexRecord(
                        id=index_id,
                        levelid=self._get_int(row, ['LEVELID', 'levelid', 'LevelId'], 0),
                        auditid=self._get_int(row, ['AUDITID', 'auditid', 'AuditId'], 0),
                        page=self._get_int(row, ['PAGE', 'page', 'Page'], 0),
                        irow=self._get_int(row, ['IROW', 'irow', 'Irow'], 0),
                        coln=self._get_int(row, ['COLN', 'coln', 'Coln'], required=True),
                        length=self._get_int(row, ['LENGTH', 'length', 'Length'], required=True),
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
                    
                    if index_id not in self.cold_indexes:
                        self.cold_indexes[index_id] = []
                    
                    self.cold_indexes[index_id].append(record)
            
            total_records = sum(len(records) for records in self.cold_indexes.values())
            print(f"成功读取 {total_records} 个COLD_INDEXES记录")
            return True
            
        except Exception as e:
            print(f"读取COLD_INDEXES CSV文件错误: {e}")
            return False
    
    def _get_value(self, row: Dict, keys: List[str], default: Optional[str] = None, required: bool = False) -> Optional[str]:
        """从行数据中获取值，尝试多个可能的键名"""
        for key in keys:
            if key in row and row[key] is not None and str(row[key]).strip() != '':
                return str(row[key]).strip()
        
        if required:
            raise ValueError(f"缺少必需字段: {keys[0]}")
        
        return default
    
    def _get_int(self, row: Dict, keys: List[str], default: Optional[int] = None, required: bool = False) -> Optional[int]:
        """从行数据中获取整数值"""
        value = self._get_value(row, keys, None, required)
        
        if value is None:
            if required:
                raise ValueError(f"缺少必需字段: {keys[0]}")
            return default
        
        try:
            return int(value)
        except (ValueError, TypeError):
            if required:
                raise ValueError(f"字段 {keys[0]} 不是有效的整数: {value}")
            return default
    
    def convert_to_json_config(self, report_id: int) -> Optional[Dict[str, Any]]:
        """将指定COLD_REPORT记录转换为JSON配置"""
        
        if report_id not in self.cold_reports:
            print(f"错误: COLD_REPORT ID {report_id} 不存在")
            return None
        
        report = self.cold_reports[report_id]
        
        # 构建JSON配置
        json_config = {
            "name": report.name,
            "description": f"COLD_REPORT配置: {report.name}",
            "report_id": report_id,
            "version": "1.0",
            "source": "cold_report",
            "metadata": {
                "appid": report.appid,
                "formid": report.formid,
                "indexid": report.indexid,
                "levelid": report.levelid,
                "sourceid": report.sourceid,
                "comments": report.comments,
                "seperator": report.seperator,
                "allowdups": report.allowdups,
                "reptable": report.reptable,
                "store_in_db": report.store_in_db,
                "index_pages": report.index_pages,
                "enter": report.enter,
                "duration": report.duration,
                "durationunit": report.durationunit
            },
            "field_groups": [],
            "index_fields": []
        }
        
        # 添加COLD_FIELDINFO字段
        if report_id in self.cold_fieldinfos:
            fieldinfos = sorted(self.cold_fieldinfos[report_id], key=lambda x: x.seq)
            
            for fieldinfo in fieldinfos:
                field_config = {
                    "name": f"field_{fieldinfo.seq}",
                    "textfieldsid": fieldinfo.textfieldsid,
                    "seq": fieldinfo.seq,
                    "icolumn": fieldinfo.icolumn,
                    "length": fieldinfo.length,
                    "start_row": fieldinfo.start_row,
                    "end_row": fieldinfo.end_row,
                    "flags": {
                        "txtsrch_fld": fieldinfo.txtsrch_fld == 1,
                        "export_fld": fieldinfo.export_fld == 1,
                        "index_fld": fieldinfo.index_fld == 1
                    }
                }
                
                # 添加验证规则
                validation_rules = {}
                if fieldinfo.pattern:
                    validation_rules["pattern"] = fieldinfo.pattern
                if fieldinfo.lefttrim:
                    validation_rules["trim_left"] = fieldinfo.lefttrim
                if fieldinfo.left_offset:
                    validation_rules["offset"] = fieldinfo.left_offset
                
                if validation_rules:
                    field_config["validation"] = validation_rules
                
                json_config["field_groups"].append(field_config)
        
        # 添加COLD_INDEXES字段
        if report_id in self.cold_indexes:
            indexes = sorted(self.cold_indexes[report_id], key=lambda x: (x.levelid, x.coln))
            
            for index in indexes:
                index_config = {
                    "name": index.column_name or f"index_{index.id}_{index.coln}",
                    "start": index.coln,
                    "length": index.length,
                    "levelid": index.levelid,
                    "description": index.literal or f"Level {index.levelid}, Col {index.coln}",
                    "required": index.invalid_action is not None and index.invalid_action > 0,
                    "metadata": {
                        "cold_index_id": index.id,
                        "page": index.page,
                        "irow": index.irow,
                        "table_name": index.table_name,
                        "key_field_name": index.key_field_name,
                        "date_format": index.date_format
                    }
                }
                
                # 添加偏移
                if index.left_offset:
                    index_config["offset"] = index.left_offset
                
                # 添加验证规则
                validation_rules = {}
                if index.pattern:
                    validation_rules["pattern"] = index.pattern
                if index.replaces:
                    validation_rules["replaces"] = index.replaces
                if index.lefttrim:
                    validation_rules["trim_left"] = index.lefttrim
                if index.usepattern:
                    validation_rules["use_pattern"] = index.usepattern == 'Y'
                
                if validation_rules:
                    index_config["validation"] = validation_rules
                
                json_config["index_fields"].append(index_config)
        
        # 添加统计信息
        json_config["statistics"] = {
            "total_field_groups": len(json_config["field_groups"]),
            "total_index_fields": len(json_config["index_fields"]),
            "has_fieldinfo_data": report_id in self.cold_fieldinfos,
            "has_index_data": report_id in self.cold_indexes
        }
        
        return json_config
    
    def convert_all_reports(self, output_dir: str) -> Dict[int, str]:
        """转换所有COLD_REPORT记录为JSON文件"""
        
        if not self.cold_reports:
            print("错误: 未加载任何COLD_REPORT数据")
            return {}
        
        # 创建输出目录
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        converted_files = {}
        
        for report_id in sorted(self.cold_reports.keys()):
            report = self.cold_reports[report_id]
            
            # 生成JSON配置
            json_config = self.convert_to_json_config(report_id)
            if not json_config:
                continue
            
            # 生成文件名
            safe_name = re.sub(r'[^\w\-_\. ]', '_', report.name)
            filename = f"cold_report_{report_id}_{safe_name}.json"
            filepath = output_path / filename
            
            # 保存文件
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(json_config, f, indent=2, ensure_ascii=False)
                
                converted_files[report_id] = str(filepath)
                print(f"已生成: {filename}")
                
            except Exception as e:
                print(f"保存文件 {filename} 错误: {e}")
        
        return converted_files
    
    def generate_sample_csv(self, output_dir: str) -> bool:
        """生成示例CSV文件模板"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 生成COLD_REPORT示例
            report_headers = [
                "ID", "SETID", "SOURCEID", "DISPOSITIONID", "APPID", "SAMPLEID", 
                "EXTERN_ID", "FORMID", "RECORDCLASSID", "INDEXID", "LEVELID",
                "TEXTFIELDSID", "AUDITID", "NAME", "COMMENTS", "SEPERATOR",
                "ALLOWDUPS", "REPTABLE", "STORE_IN_DB", "INDEX_PAGES", "MODIFY_DATE",
                "ENTER", "DURATION", "DURATIONUNIT", "DEVICEID"
            ]
            
            report_sample = [
                {
                    "ID": "101",
                    "SETID": "1",
                    "SOURCEID": "1001",
                    "DISPOSITIONID": "",
                    "APPID": "1",
                    "SAMPLEID": "",
                    "EXTERN_ID": "",
                    "FORMID": "1",
                    "RECORDCLASSID": "",
                    "INDEXID": "101",
                    "LEVELID": "1",
                    "TEXTFIELDSID": "101",
                    "AUDITID": "0",
                    "NAME": "Invoice_Report",
                    "COMMENTS": "发票报表配置",
                    "SEPERATOR": ",",
                    "ALLOWDUPS": "0",
                    "REPTABLE": "INVOICE_DATA",
                    "STORE_IN_DB": "1",
                    "INDEX_PAGES": "Y",
                    "MODIFY_DATE": "2026-03-15",
                    "ENTER": "1",
                    "DURATION": "",
                    "DURATIONUNIT": "",
                    "DEVICEID": ""
                }
            ]
            
            report_path = output_path / "cold_report_sample.csv"
            with open(report_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=report_headers)
                writer.writeheader()
                writer.writerows(report_sample)
            
            # 生成COLD_FIELDINFO示例
            fieldinfo_headers = [
                "TEXTFIELDSID", "SEQ", "REPORTID", "FORMID", "ICOLUMN", "LENGTH",
                "START_ROW", "END_ROW", "TXTSRCH_FLD", "EXPORT_FLD", "INDEX_FLD",
                "PATTERN", "LEFTTRIM", "LEFT_OFFSET"
            ]
            
            fieldinfo_sample = [
                {
                    "TEXTFIELDSID": "101",
                    "SEQ": "1",
                    "REPORTID": "101",
                    "FORMID": "1",
                    "ICOLUMN": "1",
                    "LENGTH": "20",
                    "START_ROW": "1",
                    "END_ROW": "1",
                    "TXTSRCH_FLD": "1",
                    "EXPORT_FLD": "1",
                    "INDEX_FLD": "1",
                    "PATTERN": "^[A-Z0-9]+$",
                    "LEFTTRIM": "",
                    "LEFT_OFFSET": "0"
                }
            ]
            
            fieldinfo_path = output_path / "cold_fieldinfo_sample.csv"
            with open(fieldinfo_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldinfo_headers)
                writer.writeheader()
                writer.writerows(fieldinfo_sample)
            
            # 生成COLD_INDEXES示例（扩展）
            indexes_headers = [
                "ID", "LEVELID", "AUDITID", "PAGE", "IROW", "COLN", "LENGTH",
                "LITERAL", "SAMPLE", "LEFTTRIM", "USEPATTERN", "INVALID_ACTION",
                "PATTERN", "REPLACES", "TABLENAME", "COLUMNNAME", "KEYFIELDNAME",
                "KEYLEVELID", "DATEFORMAT", "LEFT_OFFSET"
            ]
            
            indexes_sample = [
                {
                    "ID": "101",
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
                }
            ]
            
            indexes_path = output_path / "cold_indexes_sample.csv"
            with open(indexes_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=indexes_headers)
                writer.writeheader()
                writer.writerows(indexes_sample)
            
            print(f"示例CSV文件已生成到目录: {output_dir}")
            print(f"  - COLD_REPORT示例: {report_path}")
            print(f"  - COLD_FIELDINFO示例: {fieldinfo_path}")
            print(f"  - COLD_INDEXES示例: {indexes_path}")
            print("\n说明: 请从Smart iAdmin数据库导出三个表的数据到对应CSV格式")
            
            return True
            
        except Exception as e:
            print(f"生成示例CSV错误: {e}")
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='COLD_REPORT to JSON配置转换器')
    parser.add_argument('--mode', choices=['parse-xml', 'convert-csv', 'generate-sample', 'test-conversion'], 
                       default='generate-sample', help='运行模式')
    parser.add_argument('--report-csv', type=str, help='COLD_REPORT CSV文件路径')
    parser.add_argument('--fieldinfo-csv', type=str, help='COLD_FIELDINFO CSV文件路径')
    parser.add_argument('--indexes-csv', type=str, help='COLD_INDEXES CSV文件路径')
    parser.add_argument('--output-dir', type=str, default='cold_report_configs', 
                       help='输出目录路径')
    parser.add_argument('--report-id', type=int, help='指定COLD_REPORT ID转换')
    
    args = parser.parse_args()
    
    converter = ColdReportConverter()
    
    if args.mode == 'parse-xml':
        # 可以解析XML文件，但需要指定文件路径
        print("请使用--input参数指定XML文件路径")
        print("示例: --mode parse-xml --input /path/to/ColdReport.hbm.xml")
        
    elif args.mode == 'convert-csv':
        if not args.report_csv:
            print("错误: convert-csv模式需要--report-csv参数")
            sys.exit(1)
        
        print(f"开始转换COLD_REPORT配置...")
        
        # 加载数据
        if not converter.load_cold_reports_csv(args.report_csv):
            print("错误: 无法加载COLD_REPORT数据")
            sys.exit(1)
        
        if args.fieldinfo_csv:
            converter.load_cold_fieldinfos_csv(args.fieldinfo_csv)
        
        if args.indexes_csv:
            converter.load_cold_indexes_csv(args.indexes_csv)
        
        # 转换报告
        if args.report_id:
            # 转换单个报告
            json_config = converter.convert_to_json_config(args.report_id)
            if json_config:
                output_path = Path(args.output_dir) / f"cold_report_{args.report_id}.json"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(json_config, f, indent=2, ensure_ascii=False)
                
                print(f"单个报告配置已保存到: {output_path}")
            else:
                print(f"错误: 无法转换COLD_REPORT ID {args.report_id}")
        else:
            # 转换所有报告
            converted_files = converter.convert_all_reports(args.output_dir)
            print(f"\n转换完成: 共生成 {len(converted_files)} 个配置文件")
            print(f"输出目录: {args.output_dir}")
        
    elif args.mode == 'generate-sample':
        converter.generate_sample_csv(args.output_dir)
        
    elif args.mode == 'test-conversion':
        print("测试转换功能...")
        
        # 创建测试数据并转换
        test_dir = Path("test_cold_report_data")
        test_dir.mkdir(exist_ok=True)
        
        # 生成示例数据
        converter.generate_sample_csv(str(test_dir))
        
        # 加载并转换
        report_csv = test_dir / "cold_report_sample.csv"
        fieldinfo_csv = test_dir / "cold_fieldinfo_sample.csv"
        indexes_csv = test_dir / "cold_indexes_sample.csv"
        
        converter.load_cold_reports_csv(str(report_csv))
        converter.load_cold_fieldinfos_csv(str(fieldinfo_csv))
        converter.load_cold_indexes_csv(str(indexes_csv))
        
        # 转换
        json_config = converter.convert_to_json_config(101)
        if json_config:
            print("\n测试转换结果:")
            print(json.dumps(json_config, indent=2, ensure_ascii=False))
            
            # 保存测试结果
            output_path = Path("test_output") / "cold_report_101_test.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_config, f, indent=2, ensure_ascii=False)
            
            print(f"\n测试结果已保存到: {output_path}")
        else:
            print("测试转换失败")


if __name__ == "__main__":
    main()