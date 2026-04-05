import sqlite3

db_path = '/home/hongb/.openclaw/workspace/filebot/backend/filebot.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查所有与组件相关的表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%component%';")
component_tables = cursor.fetchall()

print("所有组件相关表:")
for table in component_tables:
    table_name = table[0]
    print(f"\n=== {table_name} ===")
    
    # 获取表结构
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    print("列:", [col[1] for col in columns])
    
    # 获取记录数量
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    count = cursor.fetchone()[0]
    print(f"记录数: {count}")
    
    # 如果记录不多，显示所有数据
    if count > 0 and count <= 20:
        cursor.execute(f"SELECT * FROM {table_name};")
        rows = cursor.fetchall()
        print("数据:")
        for row in rows:
            # 只显示前几个字段，避免太长
            if table_name == 'component_templates':
                print(f"  ID: {row[0]}, 名称: {row[1]}, 分类: {row[3]}")
            elif table_name == 'component_instances':
                print(f"  ID: {row[0]}, 模板ID: {row[1]}, 页面ID: {row[2]}")
            else:
                print(f"  {row}")

# 检查webbot_page表
print("\n=== webbot_page ===")
cursor.execute("PRAGMA table_info(webbot_page);")
columns = cursor.fetchall()
print("列:", [col[1] for col in columns])

cursor.execute("SELECT COUNT(*) FROM webbot_page;")
count = cursor.fetchone()[0]
print(f"记录数: {count}")

if count > 0:
    cursor.execute("SELECT id, title, language, status FROM webbot_page;")
    rows = cursor.fetchall()
    print("页面:")
    for row in rows:
        print(f"  ID: {row[0]}, 标题: {row[1]}, 语言: {row[2]}, 状态: {row[3]}")

conn.close()