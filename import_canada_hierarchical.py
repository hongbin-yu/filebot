#!/usr/bin/env python3
"""
根据FileBot中的Canada.ca HTML文档路径，重新导入并构建层次化页面结构
页面ID使用basename（文件名不带扩展名），路径结构存储在parent_id中
"""

import sqlite3
import json
import urllib.parse
import os
from datetime import datetime
import re

def get_db_connection():
    """获取数据库连接"""
    db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def extract_page_id_from_filename(filename):
    """从文件名提取页面ID（basename不带扩展名）"""
    # 移除扩展名
    basename = os.path.splitext(filename)[0]
    
    # 清理特殊字符，只保留字母、数字、连字符
    clean_id = re.sub(r'[^a-z0-9\-]', '', basename.lower())
    
    # 如果清理后为空，使用原始basename
    if not clean_id:
        clean_id = basename.lower().replace(' ', '-')
    
    return clean_id

def extract_path_from_url(url):
    """从URL提取路径层次结构"""
    parsed = urllib.parse.urlparse(url)
    path = parsed.path
    
    # 移除前导和尾随斜杠
    path = path.strip('/')
    
    # 移除文件扩展名部分（最后一个斜杠后的部分）
    if '/' in path:
        # 分割路径和文件名
        path_parts = path.split('/')
        # 最后一个部分是文件名，我们不需要它
        dir_path = '/'.join(path_parts[:-1])
        return dir_path
    else:
        # 没有路径，只有文件名
        return ''

def get_parent_page_id(path, page_map):
    """根据路径获取父页面ID"""
    if not path:
        return None
    
    # 路径格式如: "en/government"
    # 父页面应该是路径的最后一部分，如 "government"
    path_parts = path.split('/')
    
    # 从最深层次开始查找父页面
    for i in range(len(path_parts) - 1, -1, -1):
        parent_path = '/'.join(path_parts[:i+1])
        parent_id = path_parts[i]  # 父页面ID是路径的最后一段
        
        # 检查父页面是否存在
        if parent_id in page_map:
            return parent_id
        
        # 如果不存在，需要创建这个父页面
        print(f'  ⚠️ 父页面不存在: {parent_id} (路径: {parent_path})')
        # 这里不自动创建，稍后处理
    
    return None

def read_html_content(stored_filename):
    """读取HTML文件内容"""
    # 构建完整的文件路径
    base_dir = "/home/hongb/.openclaw/workspace/filebot/backend/data/documents"
    file_path = os.path.join(base_dir, stored_filename)
    
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f'  读取文件失败: {file_path}, 错误: {e}')
            return None
    else:
        print(f'  文件不存在: {file_path}')
        return None

def import_hierarchical_pages():
    """导入层次化页面结构"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("🚀 开始导入层次化Canada.ca页面结构")
    print("=" * 60)
    
    # 首先，备份现有的webbot_page表
    print("📋 备份现有数据...")
    cursor.execute("CREATE TABLE IF NOT EXISTS webbot_page_backup AS SELECT * FROM webbot_page")
    conn.commit()
    print("  ✓ 备份完成")
    
    # 清空现有的webbot_page表（但保留表结构）
    print("🧹 清理现有数据...")
    cursor.execute("DELETE FROM webbot_page")
    conn.commit()
    print(f"  ✓ 删除了 {cursor.rowcount} 条记录")
    
    # 获取所有Canada.ca HTML文档
    print("🔍 查找Canada.ca HTML文档...")
    cursor.execute('''
        SELECT d.id, d.original_filename, d.title, d.document_metadata, d.stored_filename, f.path as folder_path
        FROM documents d
        JOIN folders f ON d.folder_id = f.id
        WHERE d.file_type IN ('HTML', 'HTM')
        AND f.path LIKE '%canada-site%'
        AND d.document_metadata IS NOT NULL
        ORDER BY f.path, d.original_filename
    ''')
    
    documents = cursor.fetchall()
    print(f"  找到 {len(documents)} 个HTML文档")
    
    # 构建页面映射和路径映射
    page_map = {}  # page_id -> 页面信息
    path_map = {}  # 完整路径 -> page_id
    pages_to_create = []  # 要创建的页面列表
    
    # 第一遍：收集所有页面信息
    print("📝 分析文档结构...")
    for doc in documents:
        doc_id, filename, title, metadata_json, stored_filename, folder_path = doc
        
        # 解析元数据获取URL
        try:
            metadata = json.loads(metadata_json)
            url = metadata.get('url')
        except:
            url = None
        
        # 提取页面ID（basename不带扩展名）
        page_id = extract_page_id_from_filename(filename)
        
        # 提取路径
        path = ''
        parent_id = None
        
        if url:
            # 从URL提取路径
            parsed = urllib.parse.urlparse(url)
            url_path = parsed.path.strip('/')
            
            if url_path:
                # 分割路径和文件名
                path_parts = url_path.split('/')
                
                if len(path_parts) > 1:
                    # 有路径层次
                    filename_part = path_parts[-1]
                    dir_path = '/'.join(path_parts[:-1])
                    path = dir_path
                    
                    # 构建路径映射
                    full_path = url_path
                    path_map[full_path] = page_id
                    
                    # 记录路径信息用于后续处理
                    print(f'  📄 {page_id:30} 路径: {path:40} URL: {url[:50]}...')
                else:
                    # 只有文件名，没有路径
                    print(f'  📄 {page_id:30} (根目录) URL: {url[:50]}...')
            else:
                print(f'  📄 {page_id:30} (无路径) URL: {url[:50]}...')
        else:
            print(f'  ⚠️ {page_id:30} 无URL信息')
        
        # 读取HTML内容
        html_content = read_html_content(stored_filename)
        
        if html_content:
            # 添加到页面列表
            pages_to_create.append({
                'id': page_id,
                'title': title,
                'content': html_content,
                'url': url,
                'path': path,
                'filename': filename,
                'full_path': url_path if url else '',
                'folder_path': folder_path
            })
            
            # 添加到页面映射
            page_map[page_id] = {
                'title': title,
                'path': path,
                'url': url
            }
        else:
            print(f'  ❌ 无法读取 {page_id} 的内容')
    
    print(f"\n📊 分析完成:")
    print(f"  有效页面: {len(pages_to_create)}")
    print(f"  唯一路径数: {len(set(p['path'] for p in pages_to_create))}")
    
    # 第二遍：创建页面并建立父子关系
    print("\n🏗️ 创建页面层次结构...")
    
    # 先按路径深度排序（浅路径先创建）
    pages_to_create.sort(key=lambda p: p['path'].count('/') if p['path'] else 0)
    
    created_pages = 0
    created_parents = 0
    
    current_time = datetime.now().isoformat()
    
    for page in pages_to_create:
        page_id = page['id']
        title = page['title']
        content = page['content']
        path = page['path']
        
        print(f'\n📄 处理: {page_id:30} 路径: {path if path else "(根)"}')
        
        # 确定父页面ID
        parent_id = None
        if path:
            # 路径格式如: "en/government"
            path_parts = path.split('/')
            
            # 查找父页面（路径的上一级）
            for i in range(len(path_parts) - 1, -1, -1):
                potential_parent_id = path_parts[i]
                
                # 检查这个父页面是否存在
                cursor.execute("SELECT id FROM webbot_page WHERE id = ?", (potential_parent_id,))
                existing_parent = cursor.fetchone()
                
                if existing_parent:
                    parent_id = potential_parent_id
                    print(f'  👨‍👦 父页面: {parent_id}')
                    break
                else:
                    # 父页面不存在，可能需要创建
                    # 但对于中间路径节点，我们可能需要创建占位页面
                    pass
        
        # 检查页面是否已存在
        cursor.execute("SELECT id FROM webbot_page WHERE id = ?", (page_id,))
        existing_page = cursor.fetchone()
        
        if existing_page:
            # 更新现有页面
            print(f'  🔄 更新现有页面')
            cursor.execute('''
                UPDATE webbot_page 
                SET title = ?, content = ?, parent_id = ?, last_modified = ?
                WHERE id = ?
            ''', (title, content, parent_id, current_time, page_id))
        else:
            # 创建新页面
            print(f'  ✅ 创建新页面')
            cursor.execute('''
                INSERT INTO webbot_page 
                (id, title, content, parent_id, created_at, last_modified, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (page_id, title, content, parent_id, current_time, current_time, 
                 json.dumps({'source_url': page['url'], 'original_filename': page['filename']})))
            created_pages += 1
    
    # 提交事务
    conn.commit()
    
    # 验证结果
    cursor.execute("SELECT COUNT(*) as total FROM webbot_page")
    total_pages = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(DISTINCT parent_id) as parent_count FROM webbot_page WHERE parent_id IS NOT NULL")
    parent_count = cursor.fetchone()['parent_count']
    
    cursor.execute("SELECT COUNT(*) as leaf_count FROM webbot_page WHERE id IN (SELECT DISTINCT parent_id FROM webbot_page WHERE parent_id IS NOT NULL)")
    branch_count = cursor.fetchone()['leaf_count']
    
    print(f"\n📊 导入完成:")
    print(f"  总页面数: {total_pages}")
    print(f"  有父页面的页面数: {parent_count}")
    print(f"  分支页面数: {branch_count}")
    
    # 显示一些示例
    print(f"\n🌳 层次结构示例:")
    cursor.execute('''
        SELECT id, title, parent_id, LENGTH(content) as content_len
        FROM webbot_page
        WHERE parent_id IS NOT NULL
        ORDER BY parent_id, id
        LIMIT 10
    ''')
    
    examples = cursor.fetchall()
    for ex in examples:
        content_type = "HTML" if "<" in str(ex['content_len']) else "文本"
        print(f'  {ex["id"]:40} → 父: {ex["parent_id"]:20} ({content_type}, {ex["content_len"]} 字符)')
    
    conn.close()
    return total_pages

def create_missing_parent_pages():
    """创建缺失的父页面（路径中的中间节点）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("\n🔧 检查并创建缺失的父页面...")
    
    # 查找所有有父页面的页面
    cursor.execute('''
        SELECT DISTINCT parent_id 
        FROM webbot_page 
        WHERE parent_id IS NOT NULL 
        AND parent_id NOT IN (SELECT id FROM webbot_page)
    ''')
    
    missing_parents = cursor.fetchall()
    
    if missing_parents:
        print(f"  找到 {len(missing_parents)} 个缺失的父页面:")
        
        current_time = datetime.now().isoformat()
        
        for parent_row in missing_parents:
            parent_id = parent_row['parent_id']
            
            # 为父页面生成合适的标题
            title = parent_id.replace('-', ' ').title()
            
            print(f'  ➕ 创建父页面: {parent_id} -> "{title}"')
            
            # 创建父页面（内容为空或占位符）
            cursor.execute('''
                INSERT INTO webbot_page 
                (id, title, content, created_at, last_modified, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (parent_id, title, f'[目录页面] {title}', current_time, current_time, 
                 json.dumps({'is_directory': True})))
        
        conn.commit()
        print(f"  ✅ 创建了 {len(missing_parents)} 个父页面")
    else:
        print("  ✓ 所有父页面都存在")
    
    conn.close()

if __name__ == "__main__":
    try:
        # 第一步：导入层次化页面
        total = import_hierarchical_pages()
        
        # 第二步：创建缺失的父页面
        create_missing_parent_pages()
        
        print(f"\n🎉 层次化页面导入完成！")
        print(f"   访问 http://localhost:8000/gcweb/canada-viewer.html 查看结果")
        
    except Exception as e:
        print(f"\n❌ 导入过程中出错: {e}")
        import traceback
        traceback.print_exc()