#!/usr/bin/env python3
"""
修复file_type字段的大小写问题（统一为大写）
"""
import sqlite3

def main():
    print("🔧 修复file_type字段的大小写问题...")
    
    # 连接数据库
    conn = sqlite3.connect('filebot.db')
    cursor = conn.cursor()
    
    # 检查当前的file_type值分布
    cursor.execute('''
        SELECT file_type, COUNT(*) as count 
        FROM documents 
        WHERE file_type IS NOT NULL 
        GROUP BY file_type
        ORDER BY count DESC
    ''')
    results = cursor.fetchall()
    
    print("📊 当前file_type分布:")
    for value, count in results:
        print(f"  '{value}': {count} 个文档")
    
    # 将所有file_type值转换为大写
    cursor.execute('''
        UPDATE documents 
        SET file_type = UPPER(file_type)
        WHERE file_type IS NOT NULL
    ''')
    updated_count = cursor.rowcount
    
    print(f"\n✅ 更新了 {updated_count} 个文档的file_type字段 (统一为大写)")
    
    # 提交更改
    conn.commit()
    
    # 验证修复结果
    cursor.execute('''
        SELECT file_type, COUNT(*) as count 
        FROM documents 
        WHERE file_type IS NOT NULL 
        GROUP BY file_type
        ORDER BY count DESC
    ''')
    results = cursor.fetchall()
    
    print("\n📊 修复后的file_type分布:")
    for value, count in results:
        print(f"  '{value}': {count} 个文档")
    
    conn.close()
    print("\n🎉 file_type字段修复完成!")

if __name__ == "__main__":
    main()