#!/usr/bin/env python3
"""
WebBot页面表keywords字段迁移脚本
添加keywords字段用于SEO关键词
"""

import sqlite3
import sys
import os
from datetime import datetime

def get_db_connection(db_path=None):
    """获取数据库连接"""
    if db_path is None:
        # 默认数据库路径（与FileBot共享）
        db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"❌ 数据库连接失败: {e}")
        sys.exit(1)

def check_column_exists(conn, table_name, column_name):
    """检查表中是否存在指定列"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    for col in columns:
        if col[1] == column_name:
            return True
    return False

def migrate_database():
    """执行数据库迁移"""
    print("🚀 开始WebBot页面表keywords字段迁移")
    print("=" * 60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查webbot_page表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='webbot_page'")
        if not cursor.fetchone():
            print("❌ webbot_page表不存在")
            conn.close()
            return
        
        # 检查并添加keywords字段
        if not check_column_exists(conn, "webbot_page", "keywords"):
            print("🔤 添加keywords字段到webbot_page表...")
            cursor.execute("ALTER TABLE webbot_page ADD COLUMN keywords TEXT DEFAULT ''")
            print("✅ keywords字段添加完成")
        else:
            print("✅ keywords字段已存在")
        
        # 验证字段添加结果
        print("\n🔍 验证表结构...")
        cursor.execute("PRAGMA table_info(webbot_page)")
        columns = cursor.fetchall()
        
        keyword_field = None
        for col in columns:
            if col[1] == "keywords":
                keyword_field = col
                break
        
        if keyword_field:
            cid, name, type_, notnull, dflt_value, pk = keyword_field
            print(f"📋 keywords字段详情:")
            print(f"  - 字段名: {name}")
            print(f"  - 类型: {type_}")
            print(f"  - 默认值: {dflt_value}")
        
        # 检查是否有keywords信息存储在metadata中
        cursor.execute("SELECT id, metadata FROM webbot_page WHERE metadata LIKE '%keywords%' OR metadata LIKE '%tags%'")
        rows_with_metadata = cursor.fetchall()
        
        if rows_with_metadata:
            print(f"\n📊 发现 {len(rows_with_metadata)} 条记录在metadata中包含keywords或tags，开始迁移...")
            
            migrated_count = 0
            for row in rows_with_metadata:
                page_id = row[0]
                metadata_str = row[1]
                
                if metadata_str:
                    try:
                        import json
                        metadata = json.loads(metadata_str)
                        
                        # 迁移keywords
                        if "keywords" in metadata:
                            cursor.execute("UPDATE webbot_page SET keywords = ? WHERE id = ?", 
                                         (metadata["keywords"], page_id))
                            del metadata["keywords"]
                            migrated_count += 1
                        
                        # 更新清理后的metadata
                        cursor.execute("UPDATE webbot_page SET metadata = ? WHERE id = ?", 
                                     (json.dumps(metadata) if metadata else "{}", page_id))
                        
                    except json.JSONDecodeError:
                        print(f"⚠️  页面 {page_id} 的metadata JSON格式错误，跳过")
                    except Exception as e:
                        print(f"⚠️  迁移页面 {page_id} 时出错: {e}")
            
            print(f"✅ 成功迁移 {migrated_count} 条记录的keywords数据")
        
        # 提交更改
        conn.commit()
        print("\n🎉 数据库迁移完成！")
        
        # 显示迁移后表结构摘要
        print("\n📋 迁移后表结构摘要:")
        cursor.execute("SELECT COUNT(*) as total FROM webbot_page")
        total_pages = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as with_keywords FROM webbot_page WHERE keywords IS NOT NULL AND keywords != ''")
        pages_with_keywords = cursor.fetchone()[0]
        
        print(f"  - 总页面数: {total_pages}")
        print(f"  - 有关键词的页面: {pages_with_keywords}")
        
    except sqlite3.Error as e:
        print(f"❌ 数据库错误: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()
    
    print("\n📋 迁移总结:")
    print("  1. keywords字段: 已添加，用于存储SEO关键词，逗号分隔")
    print("  2. 现有数据: 已从metadata字段迁移keywords数据")
    print("\n🚀 下一步: 重启WebBot服务以使更改生效")

if __name__ == "__main__":
    migrate_database()