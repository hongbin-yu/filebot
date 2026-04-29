#!/usr/bin/env python3
"""
WebBot页面表字段迁移脚本
添加description和hide_in_navigation字段
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
    print("🚀 开始WebBot页面表字段迁移")
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
        
        # 检查并添加description字段
        if not check_column_exists(conn, "webbot_page", "description"):
            print("📝 添加description字段到webbot_page表...")
            cursor.execute("ALTER TABLE webbot_page ADD COLUMN description TEXT")
            print("✅ description字段添加完成")
        else:
            print("✅ description字段已存在")
        
        # 检查并添加hide_in_navigation字段
        if not check_column_exists(conn, "webbot_page", "hide_in_navigation"):
            print("🔒 添加hide_in_navigation字段到webbot_page表...")
            cursor.execute("ALTER TABLE webbot_page ADD COLUMN hide_in_navigation BOOLEAN DEFAULT 0")
            print("✅ hide_in_navigation字段添加完成")
        else:
            print("✅ hide_in_navigation字段已存在")
        
        # 验证字段添加结果
        print("\n🔍 验证表结构...")
        cursor.execute("PRAGMA table_info(webbot_page)")
        columns = cursor.fetchall()
        
        new_fields = []
        for col in columns:
            if col[1] in ["description", "hide_in_navigation"]:
                new_fields.append(col)
        
        print(f"📋 新添加的字段 ({len(new_fields)}):")
        for col in new_fields:
            cid, name, type_, notnull, dflt_value, pk = col
            print(f"  - {name}: {type_} (默认值: {dflt_value})")
        
        # 更新现有记录的metadata（如果需要迁移现有数据）
        # 检查是否有description信息存储在metadata中
        cursor.execute("SELECT id, metadata FROM webbot_page WHERE metadata LIKE '%description%' OR metadata LIKE '%hide%'")
        rows_with_metadata = cursor.fetchall()
        
        if rows_with_metadata:
            print(f"\n📊 发现 {len(rows_with_metadata)} 条记录在metadata中包含相关字段，开始迁移...")
            
            migrated_count = 0
            for row in rows_with_metadata:
                page_id = row[0]
                metadata_str = row[1]
                
                if metadata_str:
                    try:
                        import json
                        metadata = json.loads(metadata_str)
                        
                        # 迁移description
                        if "description" in metadata:
                            cursor.execute("UPDATE webbot_page SET description = ? WHERE id = ?", 
                                         (metadata["description"], page_id))
                            del metadata["description"]
                            migrated_count += 1
                        
                        # 迁移hide_in_navigation
                        if "hide_in_navigation" in metadata or "hide_in_nav" in metadata:
                            hide_value = metadata.get("hide_in_navigation", metadata.get("hide_in_nav", False))
                            cursor.execute("UPDATE webbot_page SET hide_in_navigation = ? WHERE id = ?", 
                                         (1 if hide_value else 0, page_id))
                            if "hide_in_navigation" in metadata:
                                del metadata["hide_in_navigation"]
                            if "hide_in_nav" in metadata:
                                del metadata["hide_in_nav"]
                            migrated_count += 1
                        
                        # 更新清理后的metadata
                        cursor.execute("UPDATE webbot_page SET metadata = ? WHERE id = ?", 
                                     (json.dumps(metadata) if metadata else "{}", page_id))
                        
                    except json.JSONDecodeError:
                        print(f"⚠️  页面 {page_id} 的metadata JSON格式错误，跳过")
                    except Exception as e:
                        print(f"⚠️  迁移页面 {page_id} 时出错: {e}")
            
            print(f"✅ 成功迁移 {migrated_count} 条记录的字段数据")
        
        # 提交更改
        conn.commit()
        print("\n🎉 数据库迁移完成！")
        
        # 显示迁移后表结构摘要
        print("\n📋 迁移后表结构摘要:")
        cursor.execute("SELECT COUNT(*) as total FROM webbot_page")
        total_pages = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as with_desc FROM webbot_page WHERE description IS NOT NULL AND description != ''")
        pages_with_desc = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as hidden FROM webbot_page WHERE hide_in_navigation = 1")
        pages_hidden = cursor.fetchone()[0]
        
        print(f"  - 总页面数: {total_pages}")
        print(f"  - 有描述内容的页面: {pages_with_desc}")
        print(f"  - 在导航中隐藏的页面: {pages_hidden}")
        
    except sqlite3.Error as e:
        print(f"❌ 数据库错误: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()
    
    print("\n📋 迁移总结:")
    print("  1. description字段: 已添加，用于存储页面描述")
    print("  2. hide_in_navigation字段: 已添加，布尔类型，默认False")
    print("  3. 现有数据: 已从metadata字段迁移相关数据")
    print("\n🚀 下一步: 重启WebBot服务以使更改生效")

if __name__ == "__main__":
    migrate_database()