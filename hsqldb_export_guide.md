# HSQLDB数据导出指南

## 📋 概述

本指南提供多种从Smart iAdmin HSQLDB数据库导出COLD_REPORT数据的方法。

## 🔍 第一步：确定您的HSQLDB配置

### 1. 检查Smart iAdmin配置文件
```bash
# 查看可能的数据库配置
grep -r "hsqldb" /mnt/c/workspace/smarti-admin/ 2>/dev/null
grep -r "jdbc:hsqldb" /mnt/c/workspace/smarti-admin/ 2>/dev/null
```

### 2. 常见的HSQLDB配置
- **文件模式**: `jdbc:hsqldb:file:/path/to/db`
- **内存模式**: `jdbc:hsqldb:mem:testdb`  
- **服务器模式**: `jdbc:hsqldb:hsql://localhost:9001/testdb`

### 3. 查找数据库文件
HSQLDB数据库通常由以下文件组成：
- `database.script` - SQL脚本文件
- `database.properties` - 属性文件
- `database.data` - 数据文件（如果使用CACHED表）
- `database.backup` - 备份文件

```bash
# 在Smart iAdmin目录中搜索
find /mnt/c/workspace/smarti-admin -name "*.script" -o -name "*.properties" -o -name "*.data" 2>/dev/null
```

## 🚀 第二步：选择导出方法

### 方法A：使用HSQLDB SqlTool（推荐，如果已安装）

#### 1. 下载HSQLDB
```bash
# 下载HSQLDB
wget https://repo1.maven.org/maven2/org/hsqldb/hsqldb/2.7.3/hsqldb-2.7.3.jar
```

#### 2. 创建SqlTool配置文件
创建 `sqltool.rc`：
```
urlid smarti
url jdbc:hsqldb:file:/path/to/your/database
username SA
password
```

#### 3. 使用export_hsqldb_simple.py脚本
```bash
# 运行简单导出脚本
python3 export_hsqldb_simple.py --db-file /path/to/database.script
```

### 方法B：使用Java直接连接（如果HSQLDB服务器正在运行）

#### 1. 检查HSQLDB是否在运行
```bash
# 检查端口9001
netstat -tlnp | grep :9001
# 或使用ps
ps aux | grep hsqldb
```

#### 2. 使用提供的Python脚本
```bash
# 下载HSQLDB JDBC驱动
wget https://repo1.maven.org/maven2/org/hsqldb/hsqldb/2.7.3/hsqldb-2.7.3.jar

# 运行导出脚本（服务器模式）
python3 export_hsqldb.py --mode server --host localhost --port 9001 --database testdb

# 或文件模式
python3 export_hsqldb.py --mode file --db-path /path/to/db
```

### 方法C：手动SQL查询（使用任何SQL客户端）

#### 1. 连接到HSQLDB
使用任何支持JDBC的SQL客户端（DBeaver、SQuirreL SQL等）连接到HSQLDB。

#### 2. 执行导出查询
```sql
-- 导出COLD_REPORT表
SELECT * FROM FMDBA.COLD_REPORT;

-- 导出COLD_FIELDINFO表  
SELECT * FROM FMDBA.COLD_FIELDINFO;

-- 导出COLD_INDEXES表
SELECT * FROM FMDBA.COLD_INDEXES;
```

#### 3. 导出为CSV
在SQL客户端中，右键查询结果 → 导出为CSV。

## 📁 第三步：导出脚本使用说明

### 脚本1：export_hsqldb.py（功能完整）
```bash
# 安装依赖
pip install JPype1==1.4.1 jaydebeapi

# 下载HSQLDB驱动
wget https://repo1.maven.org/maven2/org/hsqldb/hsqldb/2.7.3/hsqldb-2.7.3.jar

# 运行导出（根据您的配置选择一种）
# 方式1: 服务器模式
python3 export_hsqldb.py --mode server --host localhost --port 9001 --database smarti

# 方式2: 文件模式
python3 export_hsqldb.py --mode file --db-path /mnt/c/workspace/smarti-admin/data/smarti

# 方式3: 内存模式（通常用于测试）
python3 export_hsqldb.py --mode mem --database testdb
```

### 脚本2：export_hsqldb_simple.py（更简单，使用SqlTool）
```bash
# 无需Python依赖，只需要Java
java -jar hsqldb-2.7.3.jar --rcFile sqltool.rc smarti <<EOF
SCRIPT TO 'cold_report.csv' FROM SELECT * FROM FMDBA.COLD_REPORT;
SCRIPT TO 'cold_fieldinfo.csv' FROM SELECT * FROM FMDBA.COLD_FIELDINFO;
SCRIPT TO 'cold_indexes.csv' FROM SELECT * FROM FMDBA.COLD_INDEXES;
EOF
```

## 🔧 故障排除

### 问题1：找不到表FMDBA.COLD_REPORT
```sql
-- 尝试不同的表名
SELECT * FROM COLD_REPORT;
SELECT * FROM cold_report;
SELECT * FROM PUBLIC.COLD_REPORT;

-- 查看所有表
SELECT TABLE_SCHEMA, TABLE_NAME 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_NAME LIKE '%COLD%';
```

### 问题2：连接被拒绝
1. **确保HSQLDB正在运行**
   ```bash
   # 启动HSQLDB服务器（如果使用文件数据库）
   java -cp hsqldb-2.7.3.jar org.hsqldb.server.Server --database.0 file:mydb --dbname.0 testdb
   ```

2. **检查防火墙设置**
   ```bash
   # 允许端口9001
   sudo ufw allow 9001
   ```

### 问题3：权限不足
```sql
-- 以SA用户连接（默认无密码）
jdbc:hsqldb:hsql://localhost:9001/testdb
用户名: SA
密码: (空)
```

### 问题4：Java版本不兼容
```bash
# 检查Java版本
java -version

# 需要Java 8或更高版本
# 如果版本太低，更新Java:
sudo apt update
sudo apt install openjdk-11-jdk
```

## 📊 验证导出结果

### 检查导出的CSV文件
```bash
# 查看文件大小
ls -lh *.csv

# 查看前几行
head -5 cold_report.csv

# 检查列数
head -1 cold_report.csv | tr ',' '\n' | wc -l
```

### 预期的CSV结构

#### cold_report.csv应包含：
- ID, NAME, APPID, FORMID, INDEXID, COMMENTS, SEPERATOR, REPTABLE等

#### cold_fieldinfo.csv应包含：
- TEXTFIELDSID, SEQ, REPORTID, FORMID, ICOLUMN, LENGTH, PATTERN等

#### cold_indexes.csv应包含：
- ID, COLN, LENGTH, PATTERN, REPLACES, LEFT_OFFSET, TABLENAME等

## 🎯 快速开始（最简单路径）

### 如果您是开发者，已有Smart iAdmin运行环境：

1. **查找数据库文件**：
   ```bash
   find /mnt/c/workspace/smarti-admin -name "*.script" 2>/dev/null
   ```

2. **使用最简单脚本**：
   ```bash
   # 假设数据库文件在 /mnt/c/workspace/smarti-admin/data/smarti.script
   python3 export_hsqldb_simple.py --db-file /mnt/c/workspace/smarti-admin/data/smarti.script
   ```

3. **如果失败，尝试直接SQL**：
   ```bash
   # 启动HSQLDB数据库管理器
   java -cp hsqldb-2.7.3.jar org.hsqldb.util.DatabaseManagerSwing
   # 然后手动执行查询并导出CSV
   ```

## 📞 获取帮助

如果以上方法都失败，请提供以下信息：

1. **HSQLDB配置**：`jdbc:hsqldb:` URL是什么？
2. **数据库文件**：是否有.script或.properties文件？
3. **错误信息**：具体的错误消息是什么？
4. **环境信息**：操作系统、Java版本、Smart iAdmin版本

## 🚀 下一步

成功导出CSV文件后，使用FileBot转换器：

```bash
python3 coldreport_to_json.py --mode convert-csv \
  --report-csv cold_report.csv \
  --fieldinfo-csv cold_fieldinfo.csv \
  --indexes-csv cold_indexes.csv \
  --output-dir report_configs
```

然后测试数据提取：
```bash
python3 filebot_coldreport_integration_demo.py
```

---

**提示**：如果无法确定HSQLDB配置，可以考虑从Smart iAdmin的SQL初始化脚本(`smartiinit.sql`)重新创建数据库进行测试。