# Smart iAdmin 数据库数据导出指南

## 概述
为了将Smart iAdmin的报表配置迁移到FileBot系统，需要导出以下三个表的数据：

### 必需导出的表
1. **COLD_REPORT** - 报表主表（ID, NAME, APPID, FORMID等）
2. **COLD_FIELDINFO** - 字段信息表（REPORTID, TEXTFIELDSID, SEQ, PATTERN等）
3. **COLD_INDEXES** - 索引字段表（ID, COLN, LENGTH, PATTERN, REPLACES等）

## 数据导出方法

### 方法一：数据库客户端导出（推荐）

#### 对于HSQLDB数据库
```sql
-- 导出COLD_REPORT表
SELECT * FROM FMDBA.COLD_REPORT INTO TEXT 'cold_report.csv' WITH DELIMITER ',' HEADER;

-- 导出COLD_FIELDINFO表  
SELECT * FROM FMDBA.COLD_FIELDINFO INTO TEXT 'cold_fieldinfo.csv' WITH DELIMITER ',' HEADER;

-- 导出COLD_INDEXES表
SELECT * FROM FMDBA.COLD_INDEXES INTO TEXT 'cold_indexes.csv' WITH DELIMITER ',' HEADER;
```

#### 对于Oracle数据库
```sql
-- 使用SQL*Plus或SQL Developer
-- 在SQL Developer中：右键表 -> 导出 -> CSV格式
-- 或使用命令行：
SET PAGESIZE 0
SET FEEDBACK OFF
SET HEADING OFF
SPOOL cold_report.csv
SELECT '"'||ID||'","'||NAME||'","'||APPID||'","'||FORMID||'"' 
FROM FMDBA.COLD_REPORT;
SPOOL OFF
```

#### 对于MySQL/SQLite数据库
```sql
-- 使用命令行或GUI工具
-- MySQL命令行：
SELECT * FROM FMDBA.COLD_REPORT 
INTO OUTFILE '/tmp/cold_report.csv'
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\n';
```

### 方法二：使用数据库管理工具
1. **DBeaver/HeidiSQL等工具**：右键表 -> 导出数据 -> CSV格式
2. **phpMyAdmin**：选择表 -> 导出 -> CSV格式
3. **SQL Server Management Studio**：右键表 -> 导出数据 -> 平面文件目标

### 方法三：编写导出脚本

#### Python导出脚本（通用）
```python
import csv
import pyodbc  # 或 pymysql, cx_Oracle等

# 连接数据库
conn = pyodbc.connect('DSN=smartiadmin;UID=user;PWD=password')
cursor = conn.cursor()

# 导出COLD_REPORT
with open('cold_report.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    cursor.execute("SELECT * FROM FMDBA.COLD_REPORT")
    writer.writerow([column[0] for column in cursor.description])  # 写列名
    writer.writerows(cursor.fetchall())

# 同样导出其他表...
```

#### 简易命令行导出（如果支持）
```bash
# 如果数据库支持命令行导出
sqlplus user/password@smartiadmin @export_report.sql
```

## 必需字段检查

### 1. COLD_REPORT 表必需字段
```sql
-- 至少需要以下字段：
ID, NAME, APPID, FORMID, INDEXID, SOURCEID, 
LEVELID, TEXTFIELDSID, AUDITID, COMMENTS, 
SEPERATOR, ALLOWDUPS, REPTABLE, STORE_IN_DB, 
INDEX_PAGES, MODIFY_DATE, ENTER, DURATION, 
DURATIONUNIT, DEVICEID
```

### 2. COLD_FIELDINFO 表必需字段
```sql
-- 至少需要以下字段：
TEXTFIELDSID, SEQ, REPORTID, FORMID, 
ICOLUMN, LENGTH, START_ROW, END_ROW, 
TXTSRCH_FLD, EXPORT_FLD, INDEX_FLD, 
PATTERN, LEFTTRIM, LEFT_OFFSET
```

### 3. COLD_INDEXES 表必需字段
```sql
-- 至少需要以下字段：
ID, LEVELID, AUDITID, PAGE, IROW, COLN, LENGTH,
LITERAL, SAMPLE, LEFTTRIM, USEPATTERN, INVALID_ACTION,
PATTERN, REPLACES, TABLENAME, COLUMNNAME, KEYFIELDNAME,
KEYLEVELID, DATEFORMAT, LEFT_OFFSET
```

## 文件格式要求

### CSV文件要求
1. **编码**：UTF-8（首选）或系统默认编码
2. **分隔符**：逗号（`,`）
3. **文本限定符**：双引号（`"`）
4. **换行符**：`\n` 或 `\r\n`
5. **包含表头**：第一行必须是列名
6. **空值处理**：空字符串或NULL

### 文件命名建议
```
cold_report.csv          # COLD_REPORT表
cold_fieldinfo.csv       # COLD_FIELDINFO表  
cold_indexes.csv         # COLD_INDEXES表
```

## 快速测试方法

### 测试数据量
1. **初始测试**：导出5-10个报表的配置即可
2. **完整迁移**：导出所有报表配置

### 选择测试报表的建议
```sql
-- 查询报表列表
SELECT ID, NAME, APPID, FORMID FROM FMDBA.COLD_REPORT 
WHERE NAME LIKE '%INVOICE%' OR NAME LIKE '%ORDER%' 
ORDER BY ID LIMIT 10;
```

### 最小测试数据集
如果系统中有大量报表，可以先导出：
1. 一个发票报表（INVOICE）
2. 一个采购单报表（PURCHASE ORDER）
3. 一个通用的业务报表

## 导出步骤检查清单

- [ ] 确认数据库连接信息
- [ ] 确认有FMDBA模式的访问权限
- [ ] 选择导出方法（工具/脚本）
- [ ] 导出COLD_REPORT表数据
- [ ] 导出COLD_FIELDINFO表数据
- [ ] 导出COLD_INDEXES表数据
- [ ] 验证CSV文件格式正确
- [ ] 检查文件编码为UTF-8
- [ ] 确认包含表头行
- [ ] 测试文件可正确读取

## 常见问题解决

### 问题1：权限不足
```sql
-- 检查权限
SELECT * FROM USER_TAB_PRIVS WHERE TABLE_NAME = 'COLD_REPORT';
-- 或请求数据库管理员授予SELECT权限
GRANT SELECT ON FMDBA.COLD_REPORT TO [用户名];
```

### 问题2：字段名大小写问题
```sql
-- 查询实际字段名
SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'COLD_REPORT' AND TABLE_SCHEMA = 'FMDBA';
```

### 问题3：导出文件过大
```sql
-- 分批导出
SELECT * FROM FMDBA.COLD_REPORT WHERE ID BETWEEN 1 AND 1000;
SELECT * FROM FMDBA.COLD_REPORT WHERE ID BETWEEN 1001 AND 2000;
-- 或使用LIMIT/OFFSET
```

## 数据验证

### 简单验证脚本
```python
import csv
import sys

def validate_csv(filename, expected_columns):
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        
        print(f"文件: {filename}")
        print(f"表头: {headers}")
        print(f"期望列数: {len(expected_columns)}")
        print(f"实际列数: {len(headers)}")
        
        # 检查必需字段
        missing = [col for col in expected_columns if col not in headers]
        if missing:
            print(f"错误: 缺少字段: {missing}")
            return False
        
        # 统计行数
        row_count = sum(1 for _ in reader) + 1  # +1 for header
        print(f"总行数: {row_count}")
        
        return True

# 验证各表
validate_csv('cold_report.csv', ['ID', 'NAME', 'APPID', 'FORMID', 'INDEXID'])
validate_csv('cold_fieldinfo.csv', ['REPORTID', 'TEXTFIELDSID', 'SEQ', 'FORMID'])
validate_csv('cold_indexes.csv', ['ID', 'COLN', 'LENGTH', 'PATTERN', 'REPLACES'])
```

## 转换准备

### 文件位置
将导出的CSV文件放在工作目录：
```
/home/hongb/.openclaw/workspace/
├── cold_report.csv
├── cold_fieldinfo.csv
└── cold_indexes.csv
```

### 运行转换器
```bash
cd /home/hongb/.openclaw/workspace

# 测试单个报表
python3 coldreport_to_json.py --mode convert-csv \
  --report-csv cold_report.csv \
  --fieldinfo-csv cold_fieldinfo.csv \
  --indexes-csv cold_indexes.csv \
  --report-id 101 \
  --output-dir report_configs

# 批量转换所有报表
python3 coldreport_to_json.py --mode convert-csv \
  --report-csv cold_report.csv \
  --fieldinfo-csv cold_fieldinfo.csv \
  --indexes-csv cold_indexes.csv \
  --output-dir report_configs
```

### 输出文件结构
转换完成后：
```
report_configs/
├── cold_report_101_Invoice_Report.json
├── cold_report_102_PurchaseOrder_Report.json
├── cold_report_103_General_Report.json
└── conversion_summary.txt
```

## 支持与帮助

如果在导出过程中遇到问题：

1. **数据库连接问题**：检查连接字符串、用户名密码、网络连接
2. **权限问题**：确认对FMDBA模式有SELECT权限
3. **文件格式问题**：确保CSV格式正确，使用UTF-8编码
4. **字段缺失问题**：检查必需的字段是否都存在

**注意**：如果数据库是生产环境，请先在测试环境或备份数据库上进行导出操作。

---

**下一步**：提供导出的CSV文件后，将运行转换器生成JSON配置，并在FileBot中进行测试验证。