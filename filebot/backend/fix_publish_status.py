#!/usr/bin/env python3
"""
修复publish_status字段的大小写问题
"""
import sqlite3

def main():
    print("🔧 修复publish_status字段...")
    
    # 连接数据库
    conn = sqlite3.connect('filebot.db')
    cursor = conn.cursor()
    
    # 首先检查当前的publish_status值分布
    cursor.execute('''
        SELECT publish_status, COUNT(*) as count 
        FROM documents 
        WHERE publish_status IS NOT NULL 
        GROUP BY publish_status
        ORDER BY count DESC
    ''')
    results = cursor.fetchall()
    
    print("📊 当前publish_status分布:")
    for value, count in results:
        print(f"  '{value}': {count} 个文档")
    
    # 将小写'unpublished'更新为大写'UNPUBLISHED'
    cursor.execute('''
        UPDATE documents 
        SET publish_status = 'UNPUBLISHED'
        WHERE LOWER(publish_status) = 'unpublished'
    ''')
    updated_count = cursor.rowcount
    
    print(f"\n✅ 更新了 {updated_count} 个文档的publish_status字段 (小写 → 大写)")
    
    # 将NULL值设置为'UNPUBLISHED'（如果需要）
    cursor.execute('''
        SELECT COUNT(*) FROM documents WHERE publish_status IS NULL
    ''')
    null_count = cursor.fetchone()[0]
    
    if null_count > 0:
        cursor.execute('''
            UPDATE documents 
            SET publish_status = 'UNPUBLISHED'
            WHERE publish_status IS NULL
        ''')
        print(f"✅ 更新了 {cursor.rowcount} 个NULL值为'UNPUBLISHED'")
    
    # 提交更改
    conn.commit()
    
    # 验证修复结果
    cursor.execute('''
        SELECT publish_status, COUNT(*) as count 
        FROM documents 
        WHERE publish_status IS NOT NULL 
        GROUP BY publish_status
        ORDER BY count DESC
    ''')
    results = cursor.fetchall()
    
    print("\n📊 修复后的publish_status分布:")
    for value, count in results:
        print(f"  '{value}': {count} 个文档")
    
    # 检查是否有任何无效值
    cursor.execute('''
        SELECT DISTINCT publish_status 
        FROM documents 
        WHERE publish_status NOT IN ('PUBLISHED', 'UNPUBLISHED')
    ''')
    invalid = cursor.fetchall()
    
    if invalid:
        print("\n⚠️  发现无效值:")
        for value, in invalid:
            print(f"  '{value}'")
    else:
        print("\n✅ 所有publish_status值都是有效的 ('PUBLISHED' 或 'UNPUBLISHED')")
    
    conn.close()
    print("\n🎉 修复完成!")

if __name__ == "__main__":
    main()