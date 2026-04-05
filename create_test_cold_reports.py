#!/usr/bin/env python3
"""
创建测试用的COLD_REPORT数据
生成多个报表的测试数据，模拟真实场景
"""

import csv
import os
from pathlib import Path

def create_test_data(output_dir: str = "test_cold_data"):
    """创建测试数据"""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 1. 创建COLD_REPORT测试数据
    report_data = [
        # ID, SETID, SOURCEID, DISPOSITIONID, APPID, SAMPLEID, EXTERN_ID, FORMID, RECORDCLASSID, INDEXID, LEVELID,
        # TEXTFIELDSID, AUDITID, NAME, COMMENTS, SEPERATOR, ALLOWDUPS, REPTABLE, STORE_IN_DB, INDEX_PAGES, MODIFY_DATE,
        # ENTER, DURATION, DURATIONUNIT, DEVICEID
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
        },
        {
            "ID": "102",
            "SETID": "1",
            "SOURCEID": "1002",
            "DISPOSITIONID": "",
            "APPID": "1",
            "SAMPLEID": "",
            "EXTERN_ID": "",
            "FORMID": "2",
            "RECORDCLASSID": "",
            "INDEXID": "102",
            "LEVELID": "1",
            "TEXTFIELDSID": "102",
            "AUDITID": "0",
            "NAME": "PurchaseOrder_Report",
            "COMMENTS": "采购单报表配置",
            "SEPERATOR": "|",
            "ALLOWDUPS": "0",
            "REPTABLE": "PO_DATA",
            "STORE_IN_DB": "1",
            "INDEX_PAGES": "Y",
            "MODIFY_DATE": "2026-03-15",
            "ENTER": "1",
            "DURATION": "365",
            "DURATIONUNIT": "1",  # 天
            "DEVICEID": "1"
        },
        {
            "ID": "103",
            "SETID": "2",
            "SOURCEID": "1003",
            "DISPOSITIONID": "",
            "APPID": "2",
            "SAMPLEID": "",
            "EXTERN_ID": "",
            "FORMID": "3",
            "RECORDCLASSID": "",
            "INDEXID": "103",
            "LEVELID": "2",
            "TEXTFIELDSID": "103",
            "AUDITID": "1",
            "NAME": "CustomerStatement_Report",
            "COMMENTS": "客户对账单报表配置",
            "SEPERATOR": ",",
            "ALLOWDUPS": "1",
            "REPTABLE": "CUSTOMER_STATEMENT",
            "STORE_IN_DB": "1",
            "INDEX_PAGES": "N",
            "MODIFY_DATE": "2026-03-14",
            "ENTER": "0",
            "DURATION": "30",
            "DURATIONUNIT": "2",  # 月
            "DEVICEID": ""
        },
        {
            "ID": "104",
            "SETID": "3",
            "SOURCEID": "1004",
            "DISPOSITIONID": "1",
            "APPID": "3",
            "SAMPLEID": "1",
            "EXTERN_ID": "1001",
            "FORMID": "4",
            "RECORDCLASSID": "1",
            "INDEXID": "104",
            "LEVELID": "3",
            "TEXTFIELDSID": "104",
            "AUDITID": "0",
            "NAME": "Payment_Report",
            "COMMENTS": "付款报表配置",
            "SEPERATOR": ",",
            "ALLOWDUPS": "0",
            "REPTABLE": "PAYMENT_DATA",
            "STORE_IN_DB": "0",
            "INDEX_PAGES": "Y",
            "MODIFY_DATE": "2026-03-13",
            "ENTER": "1",
            "DURATION": "",
            "DURATIONUNIT": "",
            "DEVICEID": "2"
        }
    ]
    
    report_headers = [
        "ID", "SETID", "SOURCEID", "DISPOSITIONID", "APPID", "SAMPLEID", 
        "EXTERN_ID", "FORMID", "RECORDCLASSID", "INDEXID", "LEVELID",
        "TEXTFIELDSID", "AUDITID", "NAME", "COMMENTS", "SEPERATOR",
        "ALLOWDUPS", "REPTABLE", "STORE_IN_DB", "INDEX_PAGES", "MODIFY_DATE",
        "ENTER", "DURATION", "DURATIONUNIT", "DEVICEID"
    ]
    
    report_path = output_path / "cold_report.csv"
    with open(report_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=report_headers)
        writer.writeheader()
        writer.writerows(report_data)
    
    print(f"创建COLD_REPORT数据: {len(report_data)} 条记录")
    
    # 2. 创建COLD_FIELDINFO测试数据
    fieldinfo_data = [
        # 报表101的字段
        {
            "TEXTFIELDSID": "101",
            "SEQ": "1",
            "REPORTID": "101",
            "FORMID": "1",
            "ICOLUMN": "1",
            "LENGTH": "15",
            "START_ROW": "1",
            "END_ROW": "1",
            "TXTSRCH_FLD": "1",
            "EXPORT_FLD": "1",
            "INDEX_FLD": "1",
            "PATTERN": "^INV-\d{8}$",
            "LEFTTRIM": "",
            "LEFT_OFFSET": "0"
        },
        {
            "TEXTFIELDSID": "101",
            "SEQ": "2",
            "REPORTID": "101",
            "FORMID": "1",
            "ICOLUMN": "2",
            "LENGTH": "10",
            "START_ROW": "1",
            "END_ROW": "1",
            "TXTSRCH_FLD": "1",
            "EXPORT_FLD": "1",
            "INDEX_FLD": "0",
            "PATTERN": "^[0-9]{2}/[0-9]{2}/[0-9]{4}$",
            "LEFTTRIM": "",
            "LEFT_OFFSET": "0"
        },
        {
            "TEXTFIELDSID": "101",
            "SEQ": "3",
            "REPORTID": "101",
            "FORMID": "1",
            "ICOLUMN": "3",
            "LENGTH": "12",
            "START_ROW": "1",
            "END_ROW": "1",
            "TXTSRCH_FLD": "1",
            "EXPORT_FLD": "1",
            "INDEX_FLD": "1",
            "PATTERN": "^[A-Z]{3}-[0-9]{5}$",
            "LEFTTRIM": "",
            "LEFT_OFFSET": "0"
        },
        # 报表102的字段
        {
            "TEXTFIELDSID": "102",
            "SEQ": "1",
            "REPORTID": "102",
            "FORMID": "2",
            "ICOLUMN": "1",
            "LENGTH": "12",
            "START_ROW": "1",
            "END_ROW": "1",
            "TXTSRCH_FLD": "1",
            "EXPORT_FLD": "1",
            "INDEX_FLD": "1",
            "PATTERN": "^PO-\d{9}$",
            "LEFTTRIM": "",
            "LEFT_OFFSET": "0"
        },
        {
            "TEXTFIELDSID": "102",
            "SEQ": "2",
            "REPORTID": "102",
            "FORMID": "2",
            "ICOLUMN": "2",
            "LENGTH": "50",
            "START_ROW": "1",
            "END_ROW": "1",
            "TXTSRCH_FLD": "1",
            "EXPORT_FLD": "1",
            "INDEX_FLD": "0",
            "PATTERN": "",
            "LEFTTRIM": "",
            "LEFT_OFFSET": "0"
        },
        {
            "TEXTFIELDSID": "102",
            "SEQ": "3",
            "REPORTID": "102",
            "FORMID": "2",
            "ICOLUMN": "3",
            "LENGTH": "10",
            "START_ROW": "1",
            "END_ROW": "1",
            "TXTSRCH_FLD": "1",
            "EXPORT_FLD": "1",
            "INDEX_FLD": "0",
            "PATTERN": "^USD \d+\.\d{2}$",
            "LEFTTRIM": "",
            "LEFT_OFFSET": "0"
        },
        # 报表103的字段
        {
            "TEXTFIELDSID": "103",
            "SEQ": "1",
            "REPORTID": "103",
            "FORMID": "3",
            "ICOLUMN": "1",
            "LENGTH": "8",
            "START_ROW": "1",
            "END_ROW": "1",
            "TXTSRCH_FLD": "1",
            "EXPORT_FLD": "1",
            "INDEX_FLD": "1",
            "PATTERN": "^CUST\d{4}$",
            "LEFTTRIM": "",
            "LEFT_OFFSET": "0"
        },
        {
            "TEXTFIELDSID": "103",
            "SEQ": "2",
            "REPORTID": "103",
            "FORMID": "3",
            "ICOLUMN": "2",
            "LENGTH": "40",
            "START_ROW": "1",
            "END_ROW": "1",
            "TXTSRCH_FLD": "1",
            "EXPORT_FLD": "1",
            "INDEX_FLD": "0",
            "PATTERN": "",
            "LEFTTRIM": "",
            "LEFT_OFFSET": "0"
        }
    ]
    
    fieldinfo_headers = [
        "TEXTFIELDSID", "SEQ", "REPORTID", "FORMID", "ICOLUMN", "LENGTH",
        "START_ROW", "END_ROW", "TXTSRCH_FLD", "EXPORT_FLD", "INDEX_FLD",
        "PATTERN", "LEFTTRIM", "LEFT_OFFSET"
    ]
    
    fieldinfo_path = output_path / "cold_fieldinfo.csv"
    with open(fieldinfo_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldinfo_headers)
        writer.writeheader()
        writer.writerows(fieldinfo_data)
    
    print(f"创建COLD_FIELDINFO数据: {len(fieldinfo_data)} 条记录")
    
    # 3. 创建COLD_INDEXES测试数据
    indexes_data = [
        # 报表101的索引
        {
            "ID": "101",
            "LEVELID": "1",
            "AUDITID": "0",
            "PAGE": "1",
            "IROW": "1",
            "COLN": "1",
            "LENGTH": "15",
            "LITERAL": "Invoice Number",
            "SAMPLE": "INV-20260315",
            "LEFTTRIM": "",
            "USEPATTERN": "Y",
            "INVALID_ACTION": "1",
            "PATTERN": "^INV-\d{8}$",
            "REPLACES": "",
            "TABLENAME": "INVOICE_HEADER",
            "COLUMNNAME": "INVOICE_NO",
            "KEYFIELDNAME": "",
            "KEYLEVELID": "",
            "DATEFORMAT": "",
            "LEFT_OFFSET": "0"
        },
        {
            "ID": "101",
            "LEVELID": "1",
            "AUDITID": "0",
            "PAGE": "1",
            "IROW": "1",
            "COLN": "17",  # 从第17列开始（前一个字段结束位置+分隔符）
            "LENGTH": "10",
            "LITERAL": "Invoice Date",
            "SAMPLE": "03/15/2026",
            "LEFTTRIM": "",
            "USEPATTERN": "Y",
            "INVALID_ACTION": "1",
            "PATTERN": "^[0-9]{2}/[0-9]{2}/[0-9]{4}$",
            "REPLACES": "",
            "TABLENAME": "INVOICE_HEADER",
            "COLUMNNAME": "INVOICE_DATE",
            "KEYFIELDNAME": "",
            "KEYLEVELID": "",
            "DATEFORMAT": "MM/DD/YYYY",
            "LEFT_OFFSET": "0"
        },
        {
            "ID": "101",
            "LEVELID": "1",
            "AUDITID": "0",
            "PAGE": "1",
            "IROW": "1",
            "COLN": "28",  # 从第28列开始
            "LENGTH": "12",
            "LITERAL": "Customer Code",
            "SAMPLE": "ABC-12345",
            "LEFTTRIM": "",
            "USEPATTERN": "Y",
            "INVALID_ACTION": "1",
            "PATTERN": "^[A-Z]{3}-[0-9]{5}$",
            "REPLACES": "",
            "TABLENAME": "INVOICE_HEADER",
            "COLUMNNAME": "CUSTOMER_CODE",
            "KEYFIELDNAME": "",
            "KEYLEVELID": "",
            "DATEFORMAT": "",
            "LEFT_OFFSET": "0"
        },
        # 报表102的索引
        {
            "ID": "102",
            "LEVELID": "1",
            "AUDITID": "0",
            "PAGE": "1",
            "IROW": "1",
            "COLN": "1",
            "LENGTH": "12",
            "LITERAL": "PO Number",
            "SAMPLE": "PO-2026031501",
            "LEFTTRIM": "",
            "USEPATTERN": "Y",
            "INVALID_ACTION": "1",
            "PATTERN": "^PO-\d{9}$",
            "REPLACES": "",
            "TABLENAME": "PO_HEADER",
            "COLUMNNAME": "PO_NO",
            "KEYFIELDNAME": "",
            "KEYLEVELID": "",
            "DATEFORMAT": "",
            "LEFT_OFFSET": "0"
        },
        {
            "ID": "102",
            "LEVELID": "1",
            "AUDITID": "0",
            "PAGE": "1",
            "IROW": "1",
            "COLN": "14",  # 使用|分隔符，所以位置跳变
            "LENGTH": "50",
            "LITERAL": "Supplier Name",
            "SAMPLE": "ABC Supplier Inc.",
            "LEFTTRIM": "",
            "USEPATTERN": "N",
            "INVALID_ACTION": "0",
            "PATTERN": "",
            "REPLACES": "",
            "TABLENAME": "PO_HEADER",
            "COLUMNNAME": "SUPPLIER_NAME",
            "KEYFIELDNAME": "",
            "KEYLEVELID": "",
            "DATEFORMAT": "",
            "LEFT_OFFSET": "0"
        },
        # 报表103的索引
        {
            "ID": "103",
            "LEVELID": "2",
            "AUDITID": "1",
            "PAGE": "1",
            "IROW": "1",
            "COLN": "1",
            "LENGTH": "8",
            "LITERAL": "Customer ID",
            "SAMPLE": "CUST1001",
            "LEFTTRIM": "",
            "USEPATTERN": "Y",
            "INVALID_ACTION": "1",
            "PATTERN": "^CUST\d{4}$",
            "REPLACES": "",
            "TABLENAME": "CUSTOMER_MASTER",
            "COLUMNNAME": "CUST_ID",
            "KEYFIELDNAME": "",
            "KEYLEVELID": "",
            "DATEFORMAT": "",
            "LEFT_OFFSET": "0"
        }
    ]
    
    indexes_headers = [
        "ID", "LEVELID", "AUDITID", "PAGE", "IROW", "COLN", "LENGTH",
        "LITERAL", "SAMPLE", "LEFTTRIM", "USEPATTERN", "INVALID_ACTION",
        "PATTERN", "REPLACES", "TABLENAME", "COLUMNNAME", "KEYFIELDNAME",
        "KEYLEVELID", "DATEFORMAT", "LEFT_OFFSET"
    ]
    
    indexes_path = output_path / "cold_indexes.csv"
    with open(indexes_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=indexes_headers)
        writer.writeheader()
        writer.writerows(indexes_data)
    
    print(f"创建COLD_INDEXES数据: {len(indexes_data)} 条记录")
    
    # 4. 创建对应的.cld测试文件
    cld_test_dir = output_path / "test_cld_files"
    cld_test_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建发票测试数据
    invoice_cld = """INV-2026031501,03/15/2026,ABC-12345,ACME Corporation,$1,250.75
INV-2026031502,03/15/2026,DEF-67890,Global Suppliers,$3,450.20
INV-2026031503,03/14/2026,GHI-11223,Tech Solutions,$890.50"""
    
    invoice_path = cld_test_dir / "invoice_data.cld"
    with open(invoice_path, 'w', encoding='utf-8') as f:
        f.write(invoice_cld)
    
    # 创建采购单测试数据
    po_cld = """PO-2026031501|ABC Supplier Inc.|USD 1250.75
PO-2026031502|Global Suppliers|USD 3450.20
PO-2026031503|Tech Solutions|USD 890.50"""
    
    po_path = cld_test_dir / "po_data.cld"
    with open(po_path, 'w', encoding='utf-8') as f:
        f.write(po_cld)
    
    # 创建客户对账单测试数据
    statement_cld = """CUST1001,John Smith Corporation,Statement for March 2026
CUST1002,Jane Doe Enterprises,Statement for March 2026
CUST1003,Robert Johnson LLC,Statement for March 2026"""
    
    statement_path = cld_test_dir / "statement_data.cld"
    with open(statement_path, 'w', encoding='utf-8') as f:
        f.write(statement_cld)
    
    print(f"创建测试.cld文件: {cld_test_dir}/")
    
    # 5. 创建README说明文件
    readme_content = """# Smart iAdmin COLD_REPORT 测试数据

## 数据文件说明

### 1. CSV数据文件
- `cold_report.csv` - 4个报表配置
- `cold_fieldinfo.csv` - 8个字段定义
- `cold_indexes.csv` - 5个索引字段定义

### 2. 测试报表详情

#### 报表101: Invoice_Report
- 类型: 发票报表
- 分隔符: 逗号 (,)
- 字段: 发票号(15), 发票日期(10), 客户代码(12)
- 验证规则: 严格的格式验证

#### 报表102: PurchaseOrder_Report  
- 类型: 采购单报表
- 分隔符: 竖线 (|)
- 字段: PO号(12), 供应商名(50), 金额(10)
- 验证规则: PO号格式验证

#### 报表103: CustomerStatement_Report
- 类型: 客户对账单报表
- 分隔符: 逗号 (,)
- 字段: 客户ID(8), 客户名称(40)
- 验证规则: 客户ID格式验证

#### 报表104: Payment_Report
- 类型: 付款报表
- 备注: 用于演示，无详细字段定义

### 3. 测试.cld文件
- `invoice_data.cld` - 发票测试数据 (3条记录)
- `po_data.cld` - 采购单测试数据 (3条记录)  
- `statement_data.cld` - 对账单测试数据 (3条记录)

## 使用说明

1. **运行转换器生成JSON配置**:
   ```bash
   python3 coldreport_to_json.py --mode convert-csv \
     --report-csv cold_report.csv \
     --fieldinfo-csv cold_fieldinfo.csv \
     --indexes-csv cold_indexes.csv \
     --output-dir report_configs
   ```

2. **测试单个报表**:
   ```bash
   python3 coldreport_to_json.py --mode convert-csv \
     --report-csv cold_report.csv \
     --fieldinfo-csv cold_fieldinfo.csv \
     --indexes-csv cold_indexes.csv \
     --report-id 101
   ```

3. **使用配置提取数据**:
   ```python
   from config_based_extractor import ConfigBasedExtractor
   
   # 加载JSON配置
   with open('report_configs/cold_report_101_Invoice_Report.json', 'r') as f:
       config = json.load(f)
   
   # 创建提取器
   extractor = ConfigBasedExtractor(config)
   
   # 提取数据
   data = extractor.extract('test_cld_files/invoice_data.cld')
   ```

## 数据映射验证

每个报表的配置都包含:
- 字段位置和长度
- 验证模式 (正则表达式)
- 数据库表映射
- 提取标志设置

这些配置可以无缝迁移到FileBot系统中使用。
"""
    
    readme_path = output_path / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"创建说明文档: {readme_path}")
    
    return {
        "report_csv": str(report_path),
        "fieldinfo_csv": str(fieldinfo_path),
        "indexes_csv": str(indexes_path),
        "cld_dir": str(cld_test_dir),
        "readme": str(readme_path)
    }

if __name__ == "__main__":
    print("开始创建Smart iAdmin测试数据...")
    result = create_test_data("demo_cold_data")
    print(f"\n✅ 测试数据创建完成!")
    print(f"输出目录: {os.path.abspath('demo_cold_data')}")
    print(f"\n包含:")
    print(f"  - 4个COLD_REPORT记录")
    print(f"  - 8个COLD_FIELDINFO记录")
    print(f"  - 5个COLD_INDEXES记录")
    print(f"  - 3个测试.cld文件")
    print(f"  - 完整说明文档")