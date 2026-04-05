#!/usr/bin/env python3
"""
简单的HSQLDB导出脚本

使用HSQLDB SqlTool通过命令行导出数据。
无需Python JDBC库，只需要Java和hsqldb.jar。

使用方法：
1. 下载hsqldb.jar: wget https://repo1.maven.org/maven2/org/hsqldb/hsqldb/2.7.3/hsqldb-2.7.3.jar
2. 运行: python3 export_hsqldb_simple.py --db-file /path/to/database.script

或者直接使用Java命令：
java -jar hsqldb-2.7.3.jar --sql "SELECT * FROM COLD_REPORT;" --rcFile sqltool.rc
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
import tempfile
import datetime

def create_sqltool_rc(db_file, rc_file):
    """创建SqlTool配置文件"""
    
    # 从db_file路径提取数据库目录和名称
    db_path = Path(db_file)
    db_dir = str(db_path.parent)
    db_name = db_path.stem  # 去掉扩展名
    
    # 构建JDBC URL（文件模式）
    # HSQLDB文件模式：jdbc:hsqldb:file:/path/to/db
    # 注意：SqlTool期望文件路径不带.script扩展名
    jdbc_url = f"jdbc:hsqldb:file:{db_dir}/{db_name}"
    
    rc_content = f"""# SqlTool配置文件
# 用于连接HSQLDB数据库

urlid smarti
url {jdbc_url}
username SA
password
transiso TRANSACTION_READ_COMMITTED
driver org.hsqldb.jdbc.JDBCDriver
"""
    
    with open(rc_file, 'w') as f:
        f.write(rc_content)
    
    print(f"✅ 创建SqlTool配置文件: {rc_file}")
    print(f"   JDBC URL: {jdbc_url}")
    
    return rc_file

def run_sqltool_command(jar_path, rc_file, sql_command, output_file=None):
    """运行SqlTool命令"""
    
    cmd = ['java', '-jar', jar_path, '--rcFile', rc_file, 'smarti']
    
    # 如果指定了输出文件，使用SCRIPT命令
    if output_file:
        sql_command = f"SCRIPT TO '{output_file}' FROM {sql_command};"
    
    print(f"📋 执行SQL: {sql_command[:100]}...")
    
    try:
        # 通过管道传递SQL命令
        result = subprocess.run(
            cmd,
            input=sql_command.encode('utf-8'),
            capture_output=True,
            text=False,  # 使用二进制模式避免编码问题
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"❌ SqlTool执行失败 (返回码: {result.returncode})")
            if result.stderr:
                print("错误输出:")
                print(result.stderr.decode('utf-8', errors='ignore'))
            return False
        
        print("✅ SQL执行成功")
        
        if output_file and os.path.exists(output_file):
            # 统计输出文件行数
            with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                print(f"📄 导出 {len(lines)} 行到 {output_file}")
        
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ SQL执行超时")
        return False
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return False

def export_table(jar_path, rc_file, table_name, output_dir, limit=None):
    """导出单个表"""
    
    output_file = os.path.join(output_dir, f"{table_name.lower()}.csv")
    
    # 构建查询
    query = f"SELECT * FROM {table_name}"
    if limit:
        query += f" LIMIT {limit}"
    
    # 尝试不同的表名模式
    table_patterns = [
        f"FMDBA.{table_name}",
        table_name,
        table_name.upper(),
        table_name.lower()
    ]
    
    for table_pattern in table_patterns:
        print(f"🔄 尝试表名: {table_pattern}")
        
        # 修改查询中的表名
        pattern_query = query.replace(table_name, table_pattern)
        
        if run_sqltool_command(jar_path, rc_file, pattern_query, output_file):
            return output_file
    
    return None

def check_java_available():
    """检查Java是否可用"""
    try:
        result = subprocess.run(
            ['java', '-version'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✅ Java可用")
            return True
    except FileNotFoundError:
        print("❌ Java未安装")
        print("   请安装Java: sudo apt install openjdk-11-jdk")
        return False

def check_jar_file(jar_path):
    """检查jar文件是否存在"""
    if os.path.exists(jar_path):
        print(f"✅ HSQLDB JAR文件: {jar_path}")
        return True
    else:
        print(f"❌ HSQLDB JAR文件未找到: {jar_path}")
        print(f"   请下载: wget https://repo1.maven.org/maven2/org/hsqldb/hsqldb/2.7.3/hsqldb-2.7.3.jar")
        return False

def download_hsqldb_jar(jar_path):
    """下载HSQLDB JAR文件"""
    import urllib.request
    
    url = "https://repo1.maven.org/maven2/org/hsqldb/hsqldb/2.7.3/hsqldb-2.7.3.jar"
    
    print(f"⬇️  下载HSQLDB JAR文件: {url}")
    
    try:
        urllib.request.urlretrieve(url, jar_path)
        print(f"✅ 下载完成: {jar_path}")
        return True
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='简单的HSQLDB数据导出工具')
    
    parser.add_argument('--db-file', required=True,
                       help='HSQLDB数据库文件路径 (例如: /path/to/database.script)')
    parser.add_argument('--jar-path', default='./hsqldb-2.7.3.jar',
                       help='hsqldb.jar路径 (默认: ./hsqldb-2.7.3.jar)')
    parser.add_argument('--output-dir', default='./hsqldb_export',
                       help='输出目录 (默认: ./hsqldb_export)')
    parser.add_argument('--limit', type=int, default=0,
                       help='每个表导出的最大记录数 (0表示全部)')
    parser.add_argument('--download-jar', action='store_true',
                       help='自动下载hsqldb.jar')
    
    args = parser.parse_args()
    
    # 检查前置条件
    if not check_java_available():
        sys.exit(1)
    
    # 检查或下载jar文件
    if not check_jar_file(args.jar_path):
        if args.download_jar:
            if not download_hsqldb_jar(args.jar_path):
                sys.exit(1)
        else:
            print("\n💡 使用 --download-jar 参数自动下载hsqldb.jar")
            sys.exit(1)
    
    # 检查数据库文件
    if not os.path.exists(args.db_file):
        print(f"❌ 数据库文件不存在: {args.db_file}")
        print("\n💡 尝试查找数据库文件:")
        print("   find /mnt/c/workspace/smarti-admin -name '*.script' 2>/dev/null")
        sys.exit(1)
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.rc', delete=False) as f:
        rc_file = f.name
    
    try:
        # 创建SqlTool配置文件
        create_sqltool_rc(args.db_file, rc_file)
        
        # 要导出的表
        tables_to_export = [
            'COLD_REPORT',
            'COLD_FIELDINFO',
            'COLD_INDEXES'
        ]
        
        print("\n🚀 开始导出数据...")
        
        exported_files = {}
        
        for table in tables_to_export:
            print(f"\n📊 导出表: {table}")
            
            output_file = export_table(
                args.jar_path,
                rc_file,
                table,
                args.output_dir,
                args.limit if args.limit > 0 else None
            )
            
            if output_file:
                exported_files[table] = output_file
            else:
                print(f"⚠️  表 {table} 导出失败，可能不存在")
        
        # 生成摘要报告
        if exported_files:
            print("\n" + "="*60)
            print("✅ 导出完成!")
            print("="*60)
            
            summary_file = os.path.join(args.output_dir, 'export_summary.txt')
            with open(summary_file, 'w') as f:
                f.write("HSQLDB数据导出报告\n")
                f.write("="*40 + "\n\n")
                f.write(f"数据库文件: {args.db_file}\n")
                f.write(f"导出时间: {datetime.datetime.now().isoformat()}\n")
                f.write(f"输出目录: {args.output_dir}\n\n")
                
                f.write("导出的文件:\n")
                for table, filepath in exported_files.items():
                    if os.path.exists(filepath):
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as csv_file:
                            lines = csv_file.readlines()
                            row_count = len(lines) - 1 if len(lines) > 0 else 0  # 减去标题行
                        
                        f.write(f"  - {table}: {row_count} 行 -> {os.path.basename(filepath)}\n")
            
            print(f"\n📄 导出摘要: {summary_file}")
            print("\n📋 导出的文件:")
            for table, filepath in exported_files.items():
                if os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as csv_file:
                        lines = csv_file.readlines()
                        row_count = len(lines) - 1 if len(lines) > 0 else 0
                    
                    print(f"  ✅ {table}: {row_count} 行 -> {os.path.basename(filepath)}")
            
            print(f"\n📁 所有文件保存在: {args.output_dir}")
            
            # 创建使用说明
            readme_content = f"""# HSQLDB导出数据使用说明

## 导出的文件
{chr(10).join(f'- `{os.path.basename(f)}` - {t}表' for t, f in exported_files.items())}

## 使用FileBot转换器
```bash
cd /home/hongb/.openclaw/workspace
python3 coldreport_to_json.py --mode convert-csv \\
  --report-csv {os.path.basename(next((f for t, f in exported_files.items() if 'COLD_REPORT' in t), ''))} \\
  --fieldinfo-csv {os.path.basename(next((f for t, f in exported_files.items() if 'COLD_FIELDINFO' in t), ''))} \\
  --indexes-csv {os.path.basename(next((f for t, f in exported_files.items() if 'COLD_INDEXES' in t), ''))} \\
  --output-dir report_configs
```

## 验证数据
```bash
# 查看CSV文件
head -5 *.csv

# 统计行数
wc -l *.csv
```

## 下一步
1. 运行FileBot转换器生成JSON配置
2. 测试数据提取功能
3. 集成到FileBot系统
"""
            
            readme_file = os.path.join(args.output_dir, 'README.md')
            with open(readme_file, 'w') as f:
                f.write(readme_content)
            
            print(f"\n📖 使用说明: {readme_file}")
            
        else:
            print("\n⚠️  未成功导出任何表")
            print("\n💡 可能的解决方案:")
            print("1. 检查表名是否正确（尝试不同的大小写）")
            print("2. 检查数据库文件是否包含Smart iAdmin数据")
            print("3. 尝试手动连接数据库查看表结构")
            print("4. 使用HSQLDB数据库管理器查看: java -cp hsqldb-2.7.3.jar org.hsqldb.util.DatabaseManagerSwing")
    
    finally:
        # 清理临时文件
        if os.path.exists(rc_file):
            os.unlink(rc_file)

if __name__ == "__main__":
    main()