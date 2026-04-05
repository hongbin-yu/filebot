import sqlite3
import sys

db_path = '/home/hongb/.openclaw/workspace/filebot/backend/filebot.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 获取所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("数据库中的表:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # 检查component_templates表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='component_templates';")
    component_table = cursor.fetchone()
    
    if component_table:
        print(f"\n✅ component_templates表存在")
        # 检查表结构
        cursor.execute("PRAGMA table_info(component_templates);")
        columns = cursor.fetchall()
        print("表结构:")
        for col in columns:
            print(f"  {col[0]}: {col[1]} ({col[2]})")
        
        # 检查记录数量
        cursor.execute("SELECT COUNT(*) FROM component_templates;")
        count = cursor.fetchone()[0]
        print(f"\n记录数量: {count}")
        
        # 显示前几行
        if count > 0:
            cursor.execute("SELECT id, name, category FROM component_templates LIMIT 5;")
            rows = cursor.fetchall()
            print("前几行数据:")
            for row in rows:
                print(f"  ID: {row[0]}, 名称: {row[1]}, 分类: {row[2]}")
    else:
        print(f"\n❌ component_templates表不存在")
        
        # 检查是否有其他组件相关表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%component%';")
        component_tables = cursor.fetchall()
        if component_tables:
            print("找到相关表:")
            for table in component_tables:
                print(f"  - {table[0]}")
    
    conn.close()
    
except Exception as e:
    print(f"错误: {e}")
    sys.exit(1)