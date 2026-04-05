import sqlite3

db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='component_templates'")
    result = cursor.fetchone()
    
    if result:
        print(f"✅ component_templates表存在: {result[0]}")
        
        # 检查记录数量
        cursor.execute("SELECT COUNT(*) FROM component_templates")
        count = cursor.fetchone()[0]
        print(f"✅ 记录数量: {count}")
        
        # 显示前几个组件
        cursor.execute("SELECT id, name, category FROM component_templates LIMIT 5")
        rows = cursor.fetchall()
        print("前5个组件:")
        for row in rows:
            print(f"  - {row[0]}: {row[1]} ({row[2]})")
    else:
        print("❌ component_templates表不存在")
        
        # 显示所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("数据库中的所有表:")
        for table in tables:
            print(f"  - {table[0]}")
    
    conn.close()
except Exception as e:
    print(f"❌ 错误: {e}")