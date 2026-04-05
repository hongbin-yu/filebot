#!/usr/bin/env python3
"""
从FileBot的/boarding/canada-site导入完整的HTML页面到WebBot
"""

import sqlite3
import json
import os
import re
from datetime import datetime
from pathlib import Path

def get_db_connection():
    """获取数据库连接"""
    db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def extract_page_id_from_url(url):
    """从URL中提取页面ID"""
    if not url:
        return None
    
    # 从URL中提取路径部分
    # 例如: https://www.canada.ca/en/contact.html -> contact
    # 例如: https://www.canada.ca/en/services/benefits.html -> services-benefits
    
    # 移除协议和域名
    if '://' in url:
        url = url.split('://', 1)[1]
    
    # 移除域名部分
    if '/' in url:
        url = url.split('/', 1)[1]
    
    # 移除语言前缀 (en/ 或 fr/)
    if url.startswith('en/') or url.startswith('fr/'):
        url = url[3:]
    
    # 移除.html后缀
    if url.endswith('.html'):
        url = url[:-5]
    
    # 将斜杠替换为连字符
    url = url.replace('/', '-')
    
    # 清理特殊字符
    url = re.sub(r'[^a-zA-Z0-9\-]', '', url)
    
    return url.lower() if url else None

def extract_page_id_from_filename(filename):
    """从文件名中提取页面ID"""
    if not filename:
        return None
    
    # 移除.html后缀
    if filename.endswith('.html'):
        filename = filename[:-5]
    
    # 清理特殊字符
    filename = re.sub(r'[^a-zA-Z0-9\-]', '', filename)
    
    return filename.lower() if filename else None

def extract_title_from_html(html_content):
    """从HTML内容中提取标题"""
    if not html_content:
        return "Untitled"
    
    # 查找<title>标签
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()
        # 移除多余的空白字符
        title = re.sub(r'\s+', ' ', title)
        return title
    
    # 查找<h1>标签
    h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.IGNORECASE)
    if h1_match:
        title = h1_match.group(1).strip()
        title = re.sub(r'<[^>]+>', '', title)  # 移除HTML标签
        title = re.sub(r'\s+', ' ', title)
        return title
    
    return "Untitled"

def read_html_file(stored_filename, folder_id):
    """读取HTML文件内容"""
    if not stored_filename:
        return None
    
    # 尝试多个可能的路径
    possible_paths = [
        Path("/home/hongb/.openclaw/workspace/filebot/backend/data/documents") / stored_filename,
        Path("/home/hongb/.openclaw/workspace/filebot/backend/data/documents") / folder_id / stored_filename,
        Path("/home/hongb/.openclaw/workspace/filebot/backend/data/documents") / folder_id / os.path.basename(stored_filename),
    ]
    
    for file_path in possible_paths:
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        return f.read()
                except Exception as e:
                    print(f"  错误: 无法读取文件 {file_path}: {e}")
                    return None
            except Exception as e:
                print(f"  错误: 无法读取文件 {file_path}: {e}")
                return None
    
    print(f"  警告: 文件未找到: {stored_filename}")
    return None

def import_html_pages():
    """导入HTML页面"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("🔍 查找/boarding/canada-site中的HTML文档...")
    
    # 查找boarding应用中所有canada-site相关的HTML文档
    cursor.execute('''
        SELECT d.id as doc_id, d.original_filename, d.title, d.file_type, 
               d.file_size, d.document_metadata, d.stored_filename,
               f.id as folder_id, f.path as folder_path
        FROM documents d
        JOIN folders f ON d.folder_id = f.id
        JOIN apps a ON f.app_id = a.id
        WHERE a.slug = 'boarding' 
        AND f.path LIKE '%canada-site%'
        AND d.file_type IN ('HTML', 'HTM')
        ORDER BY f.path, d.original_filename
    ''')
    
    docs = cursor.fetchall()
    print(f"找到 {len(docs)} 个HTML文档")
    
    imported_count = 0
    updated_count = 0
    skipped_count = 0
    
    for doc in docs:
        doc_id = doc['doc_id']
        filename = doc['original_filename']
        title = doc['title']
        file_size = doc['file_size']
        metadata_json = doc['document_metadata']
        stored_filename = doc['stored_filename']
        folder_id = doc['folder_id']
        folder_path = doc['folder_path']
        
        print(f"\n📄 处理: {filename} (路径: {folder_path})")
        
        # 解析元数据
        url = None
        if metadata_json:
            try:
                metadata = json.loads(metadata_json)
                url = metadata.get('url')
            except:
                pass
        
        # 读取HTML内容
        html_content = read_html_file(stored_filename, folder_id)
        if not html_content:
            print(f"  ⚠️ 跳过: 无法读取HTML内容")
            skipped_count += 1
            continue
        
        # 确定页面ID
        page_id = None
        
        # 首先尝试从URL提取
        if url:
            page_id = extract_page_id_from_url(url)
            print(f"  从URL提取页面ID: {url} -> {page_id}")
        
        # 如果失败，从文件名提取
        if not page_id and filename:
            page_id = extract_page_id_from_filename(filename)
            print(f"  从文件名提取页面ID: {filename} -> {page_id}")
        
        if not page_id:
            print(f"  ⚠️ 跳过: 无法确定页面ID")
            skipped_count += 1
            continue
        
        # 从HTML中提取标题（如果数据库中的标题不完整）
        if not title or title == filename:
            extracted_title = extract_title_from_html(html_content)
            if extracted_title and extracted_title != "Untitled":
                title = extracted_title
                print(f"  从HTML提取标题: {title[:50]}...")
        
        # 确定语言
        language = "en"  # 默认英语
        if "/fr/" in (url or "") or "/fr/" in folder_path:
            language = "fr"
        elif folder_path.endswith("/fr") or "/fr/" in folder_path:
            language = "fr"
        
        # 检查页面是否已存在
        cursor.execute('SELECT id FROM webbot_page WHERE id = ?', (page_id,))
        existing_page = cursor.fetchone()
        
        current_time = datetime.now().isoformat()
        
        if existing_page:
            # 更新现有页面
            print(f"  🔄 更新页面: {page_id}")
            try:
                cursor.execute('''
                    UPDATE webbot_page 
                    SET title = ?, content = ?, language = ?, last_modified = ?
                    WHERE id = ?
                ''', (title, html_content, language, current_time, page_id))
                updated_count += 1
                print(f"    ✓ 更新成功")
            except Exception as e:
                print(f"    ✗ 更新失败: {e}")
        else:
            # 插入新页面
            print(f"  ➕ 创建页面: {page_id}")
            try:
                cursor.execute('''
                    INSERT INTO webbot_page 
                    (id, title, content, language, status, created_at, last_modified)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (page_id, title, html_content, language, 'published', current_time, current_time))
                imported_count += 1
                print(f"    ✓ 导入成功")
            except Exception as e:
                print(f"    ✗ 导入失败: {e}")
    
    # 提交事务
    conn.commit()
    
    print(f"\n📊 导入完成:")
    print(f"  导入: {imported_count} 个新页面")
    print(f"  更新: {updated_count} 个现有页面")
    print(f"  跳过: {skipped_count} 个文档")
    
    # 验证总数
    cursor.execute('SELECT COUNT(*) FROM webbot_page')
    total_pages = cursor.fetchone()[0]
    print(f"  webbot_page表总计: {total_pages} 个页面")
    
    conn.close()
    return imported_count + updated_count

if __name__ == "__main__":
    print("🚀 开始从FileBot /boarding/canada-site导入HTML页面")
    print("=" * 60)
    
    try:
        count = import_html_pages()
        print(f"\n✅ 成功处理 {count} 个页面")
    except Exception as e:
        print(f"\n❌ 导入过程中出错: {e}")
        import traceback
        traceback.print_exc()