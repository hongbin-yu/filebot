#!/usr/bin/env python3
"""
HSQLDB数据导出工具

从Smart iAdmin HSQLDB数据库导出COLD_REPORT相关数据为CSV文件。

使用前准备：
1. 确保Java已安装: java -version
2. 下载HSQLDB JDBC驱动: 
   - 从 https://hsqldb.org/ 下载 hsqldb-2.7.3.jar (或最新版本)
   - 或使用: wget https://repo1.maven.org/maven2/org/hsqldb/hsqldb/2.7.3/hsqldb-2.7.3.jar

使用方法：
1. 如果HSQLDB以服务器模式运行:
   python3 export_hsqldb.py --mode server --host localhost --port 9001 --database testdb

2. 如果使用数据库文件:
   python3 export_hsqldb.py --mode file --db-path /path/to/db

3. 如果是内存数据库:
   python3 export_hsqldb.py --mode mem --database memdb

参数说明：
  --mode: server/file/mem (默认: file)
  --db-path: 数据库文件路径 (对于file模式)
  --host: 服务器地址 (对于server模式，默认: localhost)
  --port: 服务器端口 (对于server模式，默认: 9001)
  --database: 数据库名称
  --username: 数据库用户名 (默认: SA)
  --password: 数据库密码 (默认: "")
  --jar-path: hsqldb.jar路径 (默认: ./hsqldb-2.7.3.jar)
  --output-dir: 输出目录 (默认: ./hsqldb_export)
  --limit: 每个表导出的最大记录数 (默认: 0表示全部)
"""

import argparse
import sys
import os
import csv
from pathlib import Path
import logging
import datetime
from typing import Dict, List, Any, Optional

# 尝试导入JDBC相关库
try:
    import jaydebeapi
    import jpype
except ImportError:
    print("缺少必要的Python库。请安装:")
    print("  pip install JPype1==1.4.1 jaydebeapi")
    print("或使用系统包管理器:")
    print("  sudo apt-get install python3-jpype python3-jaydebeapi")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HsqldbExporter:
    """HSQLDB数据导出器"""
    
    def __init__(self, args):
        self.args = args
        self.connection = None
        self.cursor = None
        
        # 验证jar文件存在
        if not os.path.exists(args.jar_path):
            logger.error(f"HSQLDB JDBC驱动未找到: {args.jar_path}")
            logger.info(f"请从以下地址下载:")
            logger.info(f"  https://repo1.maven.org/maven2/org/hsqldb/hsqldb/2.7.3/hsqldb-2.7.3.jar")
            logger.info(f"或运行: wget https://repo1.maven.org/maven2/org/hsqldb/hsqldb/2.7.3/hsqldb-2.7.3.jar")
            sys.exit(1)
    
    def build_jdbc_url(self) -> str:
        """构建JDBC连接URL"""
        mode = self.args.mode
        
        if mode == 'server':
            # 服务器模式: jdbc:hsqldb:hsql://host:port/database
            host = self.args.host or 'localhost'
            port = self.args.port or 9001
            database = self.args.database or 'testdb'
            return f"jdbc:hsqldb:hsql://{host}:{port}/{database}"
        
        elif mode == 'file':
            # 文件模式: jdbc:hsqldb:file:/path/to/db
            db_path = self.args.db_path
            if not db_path:
                logger.error("文件模式需要指定 --db-path 参数")
                sys.exit(1)
            return f"jdbc:hsqldb:file:{db_path}"
        
        elif mode == 'mem':
            # 内存模式: jdbc:hsqldb:mem:database
            database = self.args.database or 'memdb'
            return f"jdbc:hsqldb:mem:{database}"
        
        else:
            logger.error(f"不支持的模式: {mode}")
            sys.exit(1)
    
    def connect(self):
        """连接到HSQLDB数据库"""
        jdbc_url = self.build_jdbc_url()
        username = self.args.username or 'SA'
        password = self.args.password or ''
        
        logger.info(f"连接HSQLDB: {jdbc_url}")
        logger.info(f"用户名: {username}")
        
        try:
            # JDBC驱动类名
            driver_class = 'org.hsqldb.jdbc.JDBCDriver'
            
            # 连接参数
            connection_properties = {
                'user': username,
                'password': password
            }
            
            # 建立连接
            self.connection = jaydebeapi.connect(
                driver_class,
                jdbc_url,
                connection_properties,
                self.args.jar_path
            )
            
            self.cursor = self.connection.cursor()
            logger.info("✅ 数据库连接成功")
            
            # 测试连接
            self.cursor.execute("SELECT 1 FROM INFORMATION_SCHEMA.SYSTEM_USERS")
            logger.info("✅ 连接测试通过")
            
        except Exception as e:
            logger.error(f"❌ 连接失败: {e}")
            logger.info("\n常见问题解决:")
            logger.info("1. 确保HSQLDB服务器正在运行")
            logger.info("2. 检查JDBC URL是否正确")
            logger.info("3. 验证用户名/密码")
            logger.info("4. 检查网络连接（对于server模式）")
            sys.exit(1)
    
    def disconnect(self):
        """断开数据库连接"""
        if self.cursor:
            try:
                self.cursor.close()
            except:
                pass
        
        if self.connection:
            try:
                self.connection.close()
            except:
                pass
        
        logger.info("数据库连接已关闭")
    
    def get_table_names(self) -> List[str]:
        """获取所有表名"""
        try:
            # 查询所有表（排除系统表）
            query = """
            SELECT TABLE_SCHEMA, TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'PUBLIC' 
            ORDER BY TABLE_NAME
            """
            
            self.cursor.execute(query)
            tables = self.cursor.fetchall()
            
            table_names = []
            for table in tables:
                schema, name = table
                full_name = f"{schema}.{name}" if schema else name
                table_names.append(full_name)
            
            logger.info(f"发现 {len(table_names)} 个表")
            return table_names
            
        except Exception as e:
            logger.error(f"获取表名失败: {e}")
            # 如果查询失败，尝试使用已知的表名
            known_tables = [
                "FMDBA.COLD_REPORT",
                "FMDBA.COLD_FIELDINFO", 
                "FMDBA.COLD_INDEXES",
                "COLD_REPORT",
                "COLD_FIELDINFO",
                "COLD_INDEXES"
            ]
            return known_tables
    
    def get_smart_iadmin_tables(self) -> Dict[str, str]:
        """获取Smart iAdmin相关表名（处理可能的模式前缀）"""
        
        # 尝试不同的表名模式
        table_patterns = [
            # 模式.表名
            ("FMDBA.COLD_REPORT", "cold_report"),
            ("FMDBA.COLD_FIELDINFO", "cold_fieldinfo"),
            ("FMDBA.COLD_INDEXES", "cold_indexes"),
            # 只有表名
            ("COLD_REPORT", "cold_report"),
            ("COLD_FIELDINFO", "cold_fieldinfo"),
            ("COLD_INDEXES", "cold_indexes"),
            # 小写表名
            ("cold_report", "cold_report"),
            ("cold_fieldinfo", "cold_fieldinfo"),
            ("cold_indexes", "cold_indexes"),
        ]
        
        found_tables = {}
        
        for table_query, output_name in table_patterns:
            try:
                # 检查表是否存在
                check_query = f"""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = UPPER('{table_query.split('.')[-1]}')
                """
                self.cursor.execute(check_query)
                count = self.cursor.fetchone()[0]
                
                if count > 0:
                    found_tables[output_name] = table_query
                    logger.info(f"✅ 找到表: {table_query} → {output_name}")
                    
            except Exception as e:
                logger.debug(f"检查表 {table_query} 失败: {e}")
                continue
        
        return found_tables
    
    def export_table_to_csv(self, table_name: str, output_file: str):
        """导出表数据到CSV文件"""
        
        # 构建查询（可添加限制）
        limit_clause = ""
        if self.args.limit > 0:
            limit_clause = f" LIMIT {self.args.limit}"
        
        query = f"SELECT * FROM {table_name}{limit_clause}"
        
        try:
            logger.info(f"导出表: {table_name}")
            self.cursor.execute(query)
            
            # 获取列名
            column_names = [desc[0] for desc in self.cursor.description]
            
            # 获取数据
            rows = self.cursor.fetchall()
            
            # 写入CSV
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(column_names)
                writer.writerows(rows)
            
            logger.info(f"  ✅ 导出 {len(rows)} 行到 {output_file}")
            return len(rows)
            
        except Exception as e:
            logger.error(f"  ❌ 导出表 {table_name} 失败: {e}")
            return 0
    
    def export_smart_iadmin_data(self, output_dir: str):
        """导出Smart iAdmin相关数据"""
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 查找相关表
        tables = self.get_smart_iadmin_tables()
        
        if not tables:
            logger.warning("未找到Smart iAdmin表，尝试导出所有表")
            all_tables = self.get_table_names()
            for table in all_tables:
                if 'COLD' in table.upper():
                    tables[table] = table
        
        if not tables:
            logger.error("未找到任何表")
            return
        
        logger.info(f"开始导出 {len(tables)} 个表")
        
        results = {}
        for output_name, table_query in tables.items():
            output_file = os.path.join(output_dir, f"{output_name}.csv")
            row_count = self.export_table_to_csv(table_query, output_file)
            results[output_name] = row_count
        
        # 生成README文件
        self.generate_readme(output_dir, results)
        
        return results
    
    def generate_readme(self, output_dir: str, results: Dict[str, int]):
        """生成导出说明文件"""
        
        readme_content = f"""# HSQLDB数据导出报告

## 导出信息
- 导出时间: {datetime.datetime.now().isoformat()}
- 导出模式: {self.args.mode}
- 数据库URL: {self.build_jdbc_url()}
- 输出目录: {output_dir}

## 导出结果
| 表名 | 记录数 | 文件 |
|------|--------|------|
"""
        
        for table_name, row_count in results.items():
            filename = f"{table_name}.csv"
            readme_content += f"| {table_name} | {row_count} | {filename} |\n"
        
        readme_content += f"""
## 文件说明

### 1. cold_report.csv
COLD_REPORT表，包含报表配置信息。
关键字段: ID, NAME, APPID, FORMID, INDEXID, COMMENTS, SEPERATOR, REPTABLE等。

### 2. cold_fieldinfo.csv  
COLD_FIELDINFO表，包含报表字段定义。
关键字段: TEXTFIELDSID, SEQ, REPORTID, FORMID, ICOLUMN, LENGTH, PATTERN等。

### 3. cold_indexes.csv
COLD_INDEXES表，包含索引字段定义。
关键字段: ID, COLN, LENGTH, PATTERN, REPLACES, LEFT_OFFSET, TABLENAME等。

## 使用说明

这些CSV文件可以直接用于FileBot COLD_REPORT转换器:

```bash
python3 coldreport_to_json.py --mode convert-csv \
  --report-csv cold_report.csv \
  --fieldinfo-csv cold_fieldinfo.csv \
  --indexes-csv cold_indexes.csv \
  --output-dir report_configs
```

## 故障排除

### 1. 表不存在
如果某些表不存在，可能是:
- 数据库中没有Smart iAdmin数据
- 表名可能有不同的模式前缀
- 数据库未初始化

### 2. 导出记录数为0
- 检查表中是否有数据
- 检查用户是否有SELECT权限
- 尝试使用不同的表名模式

### 3. 连接问题
- 确保HSQLDB服务器正在运行
- 检查JDBC URL、用户名和密码
- 验证网络连接

## 下一步
1. 使用FileBot转换器生成JSON配置
2. 测试数据提取功能
3. 集成到FileBot系统
"""

        readme_path = os.path.join(output_dir, "README.md")
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        logger.info(f"📄 说明文件已生成: {readme_path}")
    
    def run(self):
        """运行导出流程"""
        try:
            self.connect()
            results = self.export_smart_iadmin_data(self.args.output_dir)
            
            if results:
                total_rows = sum(results.values())
                logger.info(f"\n✅ 导出完成!")
                logger.info(f"总导出记录数: {total_rows}")
                logger.info(f"输出目录: {self.args.output_dir}")
                
                print("\n📋 导出摘要:")
                for table, count in results.items():
                    print(f"  {table}: {count} 行")
            else:
                logger.warning("未导出任何数据")
            
        finally:
            self.disconnect()

def main():
    parser = argparse.ArgumentParser(description='HSQLDB数据导出工具')
    
    # 连接模式
    parser.add_argument('--mode', choices=['server', 'file', 'mem'], 
                       default='file', help='HSQLDB模式 (默认: file)')
    
    # 文件模式参数
    parser.add_argument('--db-path', help='数据库文件路径 (对于file模式)')
    
    # 服务器模式参数
    parser.add_argument('--host', default='localhost', help='服务器地址 (默认: localhost)')
    parser.add_argument('--port', type=int, default=9001, help='服务器端口 (默认: 9001)')
    parser.add_argument('--database', default='testdb', help='数据库名称 (默认: testdb)')
    
    # 通用参数
    parser.add_argument('--username', default='SA', help='数据库用户名 (默认: SA)')
    parser.add_argument('--password', default='', help='数据库密码 (默认: 空)')
    
    # 文件参数
    parser.add_argument('--jar-path', default='./hsqldb-2.7.3.jar',
                       help='hsqldb.jar路径 (默认: ./hsqldb-2.7.3.jar)')
    parser.add_argument('--output-dir', default='./hsqldb_export',
                       help='输出目录 (默认: ./hsqldb_export)')
    parser.add_argument('--limit', type=int, default=0,
                       help='每个表导出的最大记录数 (0表示全部，默认: 0)')
    
    args = parser.parse_args()
    
    # 验证参数
    if args.mode == 'file' and not args.db_path:
        logger.error("文件模式需要指定 --db-path 参数")
        parser.print_help()
        sys.exit(1)
    
    # 运行导出
    exporter = HsqldbExporter(args)
    exporter.run()

if __name__ == "__main__":
    main()