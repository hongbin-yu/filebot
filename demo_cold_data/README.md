# Smart iAdmin COLD_REPORT 测试数据

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
   python3 coldreport_to_json.py --mode convert-csv      --report-csv cold_report.csv      --fieldinfo-csv cold_fieldinfo.csv      --indexes-csv cold_indexes.csv      --output-dir report_configs
   ```

2. **测试单个报表**:
   ```bash
   python3 coldreport_to_json.py --mode convert-csv      --report-csv cold_report.csv      --fieldinfo-csv cold_fieldinfo.csv      --indexes-csv cold_indexes.csv      --report-id 101
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
