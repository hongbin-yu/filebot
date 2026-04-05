#!/usr/bin/env python3
"""
将FileBot中的Canada.ca页面导入到WebBot页面表
"""

import sqlite3
import json
import os
from datetime import datetime
import re

def get_db_connection():
    """获取数据库连接"""
    db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"❌ 数据库连接失败: {e}")
        raise

def generate_page_id(title):
    """根据标题生成页面ID"""
    # 移除“ - Canada.ca”后缀
    clean_title = re.sub(r'\s*-\s*Canada\.ca\s*$', '', title, flags=re.IGNORECASE)
    # 转换为小写，替换空格为连字符，移除特殊字符
    page_id = re.sub(r'[^a-z0-9\s-]', '', clean_title.lower())
    page_id = re.sub(r'\s+', '-', page_id.strip())
    # 如果为空，使用UUID部分
    if not page_id:
        import uuid
        page_id = f"page-{uuid.uuid4().hex[:8]}"
    return page_id

def extract_language(metadata):
    """从元数据中提取语言代码"""
    if not metadata:
        return 'en'
    
    try:
        meta = json.loads(metadata) if isinstance(metadata, str) else metadata
        url = meta.get('url', '')
        if '/fr.' in url or '/fr/' in url or url.endswith('/fr'):
            return 'fr'
    except:
        pass
    
    return 'en'

def extract_content(metadata):
    """从元数据中提取HTML内容"""
    if not metadata:
        return ''
    
    try:
        meta = json.loads(metadata) if isinstance(metadata, str) else metadata
        html = meta.get('html_content', '')
        if html:
            return html
    except:
        pass
    
    return ''

def import_canada_pages(limit=100, max_created_at=None):
    """导入Canada.ca页面到WebBot"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 查询Canada.ca相关文档
    where_clause = "WHERE title LIKE '%Canada.ca%'"
    params = []
    
    if max_created_at:
        where_clause += " AND created_at <= ?"
        params.append(max_created_at)
    
    if limit:
        query = f"""
            SELECT id, title, document_metadata, created_by, created_at
            FROM documents 
            {where_clause}
            ORDER BY created_at ASC
            LIMIT ?
        """
        params.append(limit)
        cursor.execute(query, tuple(params))
    else:
        query = f"""
            SELECT id, title, document_metadata, created_by, created_at
            FROM documents 
            {where_clause}
            ORDER BY created_at ASC
        """
        cursor.execute(query, tuple(params))
    
    documents = cursor.fetchall()
    
    print(f"📄 找到 {len(documents)} 个Canada.ca文档")
    
    imported_count = 0
    skipped_count = 0
    
    for doc in documents:
        doc_id = doc['id']
        title = doc['title']
        metadata = doc['document_metadata']
        created_by = doc['created_by'] or '4dad6fa1-d521-417f-8877-efe95fcf1f04'  # admin用户
        created_at = doc['created_at'] or datetime.now().isoformat()
        
        # 检查是否已导入
        cursor.execute("SELECT id FROM webbot_page WHERE title = ?", (title,))
        if cursor.fetchone():
            print(f"⏭️  跳过已存在的页面: {title}")
            skipped_count += 1
            continue
        
        # 生成页面ID
        page_id = generate_page_id(title)
        
        # 提取语言和内容
        language = extract_language(metadata)
        content = extract_content(metadata)
        
        # 如果内容为空，使用占位符
        if not content:
            content = f"<h1>{title}</h1><p>Canada.ca页面内容</p>"
        
        # 插入到webbot_page表
        try:
            cursor.execute("""
                INSERT INTO webbot_page 
                (id, title, content, language, parent_id, other_lang_page_id, status, 
                 created_by, created_at, last_modified, last_published, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                page_id,
                title,
                content,
                language,
                None,  # parent_id
                None,  # other_lang_page_id
                'published',  # status
                created_by,
                created_at,
                created_at,  # last_modified初始化为created_at
                created_at,  # last_published初始化为created_at
                json.dumps({'source_document_id': doc_id, 'imported_at': datetime.now().isoformat()})
            ))
            
            imported_count += 1
            print(f"✅ 导入: {title} -> {page_id} ({language})")
            
        except sqlite3.Error as e:
            print(f"❌ 导入失败 {title}: {e}")
            conn.rollback()
            continue
    
    conn.commit()
    conn.close()
    
    print(f"\n📊 导入完成:")
    print(f"   ✅ 成功导入: {imported_count}")
    print(f"   ⏭️  跳过: {skipped_count}")
    
    # 验证总数
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM webbot_page")
    total = cursor.fetchone()[0]
    conn.close()
    
    print(f"   📄 WebBot页面总数: {total}")
    
    return imported_count

if __name__ == "__main__":
    print("🚀 开始导入Canada.ca页面到WebBot")
    print("=" * 50)
    
    try:
        # 导入前100个Canada.ca页面（按创建时间正序）
        imported = import_canada_pages(limit=100)
        
        if imported > 0:
            print(f"\n🎉 成功导入 {imported} 个页面！")
            print("🔧 接下来可以启动WebBot后端:")
            print("   cd /home/hongb/.openclaw/workspace/webbot")
            print("   ./start.sh")
        else:
            print("\n⚠️  没有导入任何页面，可能所有页面都已存在")
            
    except Exception as e:
        print(f"\n❌ 导入过程出错: {e}")
        import traceback
        traceback.print_exc()