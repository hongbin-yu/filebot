#!/usr/bin/env python3
"""
分析Smarti备份脚本，了解数据库结构和数据量
"""

import re
import sqlite3
from pathlib import Path
from collections import defaultdict

# 备份文件路径
backup_file = Path("/home/hongb/.openclaw/workspace/filebot/backups/production_migration_20260321_175924/smarti.script.backup")

def analyze_sql_script(file_path):
    """分析SQL脚本，统计表和数据量"""
    print("🔍 分析Smarti备份脚本...")
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 提取CREATE TABLE语句
    create_table_pattern = r'CREATE (?:MEMORY )?TABLE (\w+)'
    tables = re.findall(create_table_pattern, content, re.IGNORECASE)
    
    # 提取INSERT INTO语句
    insert_pattern = r'INSERT INTO (\w+) VALUES'
    insert_matches = re.findall(insert_pattern, content, re.IGNORECASE)
    
    # 统计每个表的插入数量
    table_counts = defaultdict(int)
    for table in insert_matches:
        table_counts[table] += 1
    
    print(f"📊 数据库结构概览:")
    print(f"  总表数量: {len(tables)}")
    print(f"  总数据行数: {sum(table_counts.values())}")
    print()
    
    # 显示关键表的数据量
    key_tables = ['APP', 'DOC', 'FOLD', 'DRAW', 'EXTERNAL_FILE', 'PAGES', 'RECORD_CLASS', 'USERS']
    print("📋 关键表数据量:")
    for table in key_tables:
        count = table_counts.get(table, 0)
        print(f"  {table:20} {count:6} 行")
    
    # 统计文件引用
    print()
    print("📁 文件存储分析:")
    
    # 检查SMARTI备份目录中的文件
    backup_dir = Path("/home/hongb/.openclaw/workspace/filebot/backups/production_migration_20260321_175924")
    
    smarti_dirs = list(backup_dir.glob("SMARTI.*_backup"))
    if smarti_dirs:
        file_count = 0
        total_size = 0
        extensions = defaultdict(int)
        
        for dir_path in smarti_dirs:
            for file_path in dir_path.rglob("*"):
                if file_path.is_file():
                    file_count += 1
                    total_size += file_path.stat().st_size
                    ext = file_path.suffix.lower()
                    extensions[ext] += 1
        
        print(f"  SMARTI备份目录: {len(smarti_dirs)} 个")
        print(f"  文件总数: {file_count}")
        print(f"  总大小: {total_size / (1024*1024):.2f} MB")
        print("  文件类型分布:")
        for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"    {ext:8} {count:6} 个")
    
    # 检查files_backup目录
    files_backup = backup_dir / "files_backup"
    if files_backup.exists():
        cld_files = list(files_backup.rglob("*.CLD"))
        cld_files_lower = list(files_backup.rglob("*.cld"))
        print(f"  files_backup目录: {len(cld_files) + len(cld_files_lower)} 个.CLD文件")
    
    return tables, table_counts

def check_current_filebot():
    """检查当前FileBot数据库状态"""
    print("\n🔍 当前FileBot数据库状态:")
    
    db_path = Path("filebot.db")
    if not db_path.exists():
        print("  FileBot数据库不存在")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT COUNT(*) FROM apps')
        app_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM folders')
        folder_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM documents')
        doc_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        
        print(f"  应用数量: {app_count}")
        print(f"  文件夹数量: {folder_count}")
        print(f"  文档数量: {doc_count}")
        print(f"  用户数量: {user_count}")
        
        # 检查是否有冲突
        print(f"\n⚠️  导入前注意事项:")
        print(f"  - Smarti数据将添加到现有数据库")
        print(f"  - 可能会有ID冲突（如果使用相同ID范围）")
        print(f"  - 建议创建新应用或使用前缀避免冲突")
        
    except sqlite3.Error as e:
        print(f"  数据库查询错误: {e}")
    finally:
        conn.close()

def analyze_smarti_apps(content):
    """分析Smarti中的应用数据"""
    print("\n📱 Smarti应用分析:")
    
    # 提取APP表数据
    app_pattern = r"INSERT INTO APP VALUES\((\d+),([^,]*),'([^']*)','([^']*)',(\d+),'([^']*)',(\d+),(\d+),([^,]*),'([^']*)'\)"
    app_matches = re.findall(app_pattern, content)
    
    if app_matches:
        print(f"  找到 {len(app_matches)} 个应用:")
        for match in app_matches[:5]:  # 显示前5个
            app_id, disposition_id, name, create_date, admin_id, comments, deleted, querysec, view_basic_query, formtitle = match
            print(f"    ID: {app_id}, 名称: {name}, 创建日期: {create_date}, 注释: {comments}")
        if len(app_matches) > 5:
            print(f"    ... 还有 {len(app_matches)-5} 个应用")
    else:
        print("  未找到APP表数据或格式不匹配")

def main():
    print("=" * 60)
    print("Smarti数据库导入分析工具")
    print("=" * 60)
    
    if not backup_file.exists():
        print(f"❌ 备份文件不存在: {backup_file}")
        return
    
    # 分析SQL脚本
    tables, table_counts = analyze_sql_script(backup_file)
    
    # 读取文件内容进行详细分析
    with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 分析应用数据
    analyze_smarti_apps(content)
    
    # 检查当前FileBot状态
    check_current_filebot()
    
    print("\n" + "=" * 60)
    print("导入建议:")
    print("=" * 60)
    print("1. 数据库结构复杂，建议分阶段导入")
    print("2. 先导入核心数据（应用、文件夹、文档）")
    print("3. 文件处理可能需要特殊转换（.CLD, .PCL, .AFP等）")
    print("4. 考虑创建新的FileBot应用来容纳Smarti数据")
    print("5. 建议测试导入后再应用到生产数据库")
    
    print("\n📋 下一步行动:")
    print("  A) 只导入应用和文档元数据（不包含文件）")
    print("  B) 导入完整数据（包括文件复制）")
    print("  C) 创建映射分析报告")
    print("  D) 测试导入少量数据")

if __name__ == "__main__":
    main()