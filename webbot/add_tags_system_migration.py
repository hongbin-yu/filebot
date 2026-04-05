#!/usr/bin/env python3
"""
WebBot标签系统迁移脚本
创建tags表和page-tag关联表
"""

import sqlite3
import sys
import os
from datetime import datetime
import re

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

def check_table_exists(conn, table_name):
    """检查表是否存在"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None

def slugify(text):
    """将文本转换为URL友好的slug"""
    if not text:
        return ""
    # 转换为小写，替换非字母数字字符为连字符
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[-\s]+', '-', slug).strip('-')
    return slug

def migrate_database():
    """执行数据库迁移"""
    print("🚀 开始WebBot标签系统迁移")
    print("=" * 60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查webbot_page表是否存在
        if not check_table_exists(conn, "webbot_page"):
            print("❌ webbot_page表不存在")
            conn.close()
            return
        
        # 1. 创建webbot_tag表
        if not check_table_exists(conn, "webbot_tag"):
            print("🏷️  创建webbot_tag表...")
            cursor.execute("""
                CREATE TABLE webbot_tag (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    slug TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            print("✅ webbot_tag表创建完成")
        else:
            print("✅ webbot_tag表已存在")
        
        # 2. 创建webbot_page_tag关联表
        if not check_table_exists(conn, "webbot_page_tag"):
            print("🔗 创建webbot_page_tag关联表...")
            cursor.execute("""
                CREATE TABLE webbot_page_tag (
                    page_id TEXT NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (page_id, tag_id),
                    FOREIGN KEY (page_id) REFERENCES webbot_page(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES webbot_tag(id) ON DELETE CASCADE
                )
            """)
            print("✅ webbot_page_tag表创建完成")
        else:
            print("✅ webbot_page_tag表已存在")
        
        # 3. 检查是否有tags信息存储在metadata中
        cursor.execute("SELECT id, metadata FROM webbot_page WHERE metadata LIKE '%tags%'")
        rows_with_metadata = cursor.fetchall()
        
        if rows_with_metadata:
            print(f"\n📊 发现 {len(rows_with_metadata)} 条记录在metadata中包含tags，开始迁移...")
            
            migrated_count = 0
            for row in rows_with_metadata:
                page_id = row[0]
                metadata_str = row[1]
                
                if metadata_str:
                    try:
                        import json
                        metadata = json.loads(metadata_str)
                        
                        # 迁移tags
                        if "tags" in metadata and isinstance(metadata["tags"], list):
                            tags = metadata["tags"]
                            if tags:
                                for tag_name in tags:
                                    if tag_name:
                                        # 检查标签是否已存在
                                        cursor.execute("SELECT id FROM webbot_tag WHERE name = ? OR slug = ?", 
                                                     (tag_name, slugify(tag_name)))
                                        existing_tag = cursor.fetchone()
                                        
                                        if existing_tag:
                                            tag_id = existing_tag[0]
                                        else:
                                            # 创建新标签
                                            slug = slugify(tag_name)
                                            created_at = datetime.now().isoformat()
                                            cursor.execute(
                                                "INSERT INTO webbot_tag (name, slug, created_at) VALUES (?, ?, ?)",
                                                (tag_name, slug, created_at)
                                            )
                                            tag_id = cursor.lastrowid
                                        
                                        # 创建关联
                                        try:
                                            cursor.execute(
                                                "INSERT INTO webbot_page_tag (page_id, tag_id) VALUES (?, ?)",
                                                (page_id, tag_id)
                                            )
                                        except sqlite3.IntegrityError:
                                            # 关联已存在，忽略
                                            pass
                                
                                # 从metadata中移除tags
                                del metadata["tags"]
                                migrated_count += 1
                            
                            # 更新清理后的metadata
                            cursor.execute("UPDATE webbot_page SET metadata = ? WHERE id = ?", 
                                         (json.dumps(metadata) if metadata else "{}", page_id))
                        
                    except json.JSONDecodeError:
                        print(f"⚠️  页面 {page_id} 的metadata JSON格式错误，跳过")
                    except Exception as e:
                        print(f"⚠️  迁移页面 {page_id} 时出错: {e}")
            
            print(f"✅ 成功迁移 {migrated_count} 条记录的tags数据")
        
        # 4. 创建索引以提高查询性能
        print("\n📊 创建索引...")
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_page_tag_page_id ON webbot_page_tag(page_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_page_tag_tag_id ON webbot_page_tag(tag_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tag_slug ON webbot_tag(slug)")
            print("✅ 索引创建完成")
        except sqlite3.Error as e:
            print(f"⚠️  创建索引时出错: {e}")
        
        # 提交更改
        conn.commit()
        print("\n🎉 标签系统迁移完成！")
        
        # 显示迁移后统计信息
        print("\n📋 迁移后统计信息:")
        cursor.execute("SELECT COUNT(*) as total_tags FROM webbot_tag")
        total_tags = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as total_relations FROM webbot_page_tag")
        total_relations = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT page_id) as tagged_pages FROM webbot_page_tag")
        tagged_pages = cursor.fetchone()[0]
        
        print(f"  - 总标签数: {total_tags}")
        print(f"  - 总标签关联数: {total_relations}")
        print(f"  - 有标签的页面数: {tagged_pages}")
        
        # 显示前10个最常用的标签
        cursor.execute("""
            SELECT t.name, COUNT(pt.tag_id) as usage_count
            FROM webbot_tag t
            LEFT JOIN webbot_page_tag pt ON t.id = pt.tag_id
            GROUP BY t.id
            ORDER BY usage_count DESC, t.name
            LIMIT 10
        """)
        top_tags = cursor.fetchall()
        
        if top_tags:
            print(f"\n🏆 最常用的标签 (前10):")
            for tag in top_tags:
                print(f"  - {tag['name']}: {tag['usage_count']} 个页面")
        
    except sqlite3.Error as e:
        print(f"❌ 数据库错误: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()
    
    print("\n📋 迁移总结:")
    print("  1. webbot_tag表: 已创建，存储标签信息")
    print("  2. webbot_page_tag表: 已创建，存储页面-标签关联")
    print("  3. 索引: 已创建，优化查询性能")
    print("  4. 现有数据: 已从metadata字段迁移tags数据")
    print("\n🚀 下一步: 更新API和前端以支持标签系统")

if __name__ == "__main__":
    migrate_database()