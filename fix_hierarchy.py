#!/usr/bin/env python3
"""
修复页面层次结构，确保路径中的每个中间节点都有对应的页面
例如：路径 "en/government/system" 应该创建：
- 页面 "en" (根)
- 页面 "government" (父: en)
- 页面 "system" (父: government)
"""

import sqlite3
import json
import urllib.parse
import os
from datetime import datetime

def get_db_connection():
    """获取数据库连接"""
    db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def extract_page_id_from_filename(filename):
    """从文件名提取页面ID（basename不带扩展名）"""
    import re
    basename = os.path.splitext(filename)[0]
    clean_id = re.sub(r'[^a-z0-9\-]', '', basename.lower())
    if not clean_id:
        clean_id = basename.lower().replace(' ', '-')
    return clean_id

def rebuild_hierarchy():
    """重新构建正确的页面层次结构"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("🔧 重新构建页面层次结构")
    print("=" * 60)
    
    # 第一步：获取所有文档及其URL
    cursor.execute('''
        SELECT d.id as doc_id, d.original_filename, d.title, d.document_metadata, d.stored_filename
        FROM documents d
        JOIN folders f ON d.folder_id = f.id
        WHERE d.file_type IN ('HTML', 'HTM')
        AND f.path LIKE '%canada-site%'
        AND d.document_metadata IS NOT NULL
    ''')
    
    documents = cursor.fetchall()
    print(f"找到 {len(documents)} 个文档")
    
    # 清空现有的parent_id关系（但保留页面）
    print("🔄 重置现有父关系...")
    cursor.execute("UPDATE webbot_page SET parent_id = NULL")
    conn.commit()
    
    # 创建页面映射和需要创建的中间节点
    current_time = datetime.now().isoformat()
    created_pages = 0
    
    for doc in documents:
        doc_id, filename, title, metadata_json, stored_filename = doc
        
        # 解析元数据获取URL
        try:
            metadata = json.loads(metadata_json)
            url = metadata.get('url')
        except:
            url = None
        
        if not url:
            continue
        
        # 提取页面ID
        page_id = extract_page_id_from_filename(filename)
        
        # 解析URL路径
        parsed = urllib.parse.urlparse(url)
        url_path = parsed.path
        
        # 移除前导/尾随斜杠和扩展名
        url_path = url_path.strip('/')
        
        if not url_path:
            # 根页面，如 https://www.canada.ca
            print(f'🌐 根页面: {page_id} (URL: {url})')
            continue
        
        # 分割路径部分
        # 例如: "en/government/about-canada-ca.html" → ["en", "government", "about-canada-ca.html"]
        path_parts = url_path.split('/')
        
        # 最后一个部分是文件名
        filename_part = path_parts[-1]
        
        # 目录部分（如果没有目录，则为空列表）
        dir_parts = path_parts[:-1]
        
        print(f'\n📄 处理: {page_id}')
        print(f'  URL路径: {url_path}')
        print(f'  目录: {dir_parts}')
        
        # 构建目录层次
        parent_id = None
        for i, dir_part in enumerate(dir_parts):
            # 目录部分的ID（例如 "en", "government"）
            dir_id = extract_page_id_from_filename(dir_part)
            
            if not dir_id:
                # 如果目录部分没有有效的ID（如数字或其他），跳过
                continue
            
            # 检查这个目录页面是否存在
            cursor.execute("SELECT id FROM webbot_page WHERE id = ?", (dir_id,))
            existing_dir = cursor.fetchone()
            
            if not existing_dir:
                # 创建目录页面
                dir_title = dir_part.replace('-', ' ').title()
                if 'en' in dir_id:
                    dir_title = 'English'
                elif 'fr' in dir_id:
                    dir_title = 'Français'
                
                print(f'  ➕ 创建目录页面: {dir_id} -> "{dir_title}" (父: {parent_id})')
                
                cursor.execute('''
                    INSERT OR REPLACE INTO webbot_page 
                    (id, title, content, parent_id, created_at, last_modified, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (dir_id, dir_title, f'[目录] {dir_title}', parent_id, current_time, current_time,
                     json.dumps({'is_directory': True, 'source_url': f'/{"/".join(dir_parts[:i+1])}'})))
                
                created_pages += 1
            
            # 更新父ID为当前目录
            parent_id = dir_id
        
        # 现在设置实际页面的父ID
        if parent_id:
            print(f'  🔗 设置父关系: {page_id} → {parent_id}')
            
            # 更新页面的父ID
            cursor.execute('''
                UPDATE webbot_page 
                SET parent_id = ?, last_modified = ?
                WHERE id = ?
            ''', (parent_id, current_time, page_id))
    
    # 提交事务
    conn.commit()
    
    # 验证结果
    print(f"\n📊 层次结构重建完成:")
    print(f"  创建了 {created_pages} 个目录页面")
    
    # 显示层次结构示例
    print(f"\n🌳 新的层次结构示例:")
    
    # 查找根页面（没有父页面的页面）
    cursor.execute('''
        SELECT id, title, COUNT(child.id) as child_count
        FROM webbot_page p
        LEFT JOIN webbot_page child ON child.parent_id = p.id
        WHERE p.parent_id IS NULL
        GROUP BY p.id, p.title
        HAVING COUNT(child.id) > 0
        ORDER BY child_count DESC
        LIMIT 10
    ''')
    
    roots = cursor.fetchall()
    print("根页面:")
    for root_id, title, child_count in roots:
        print(f'  {root_id:20} → {child_count:2} 个子页面 ({title[:30]})')
        
        # 显示一级子页面
        cursor.execute('''
            SELECT id, title, COUNT(grandchild.id) as grandchild_count
            FROM webbot_page child
            LEFT JOIN webbot_page grandchild ON grandchild.parent_id = child.id
            WHERE child.parent_id = ?
            GROUP BY child.id, child.title
            ORDER BY grandchild_count DESC, child.id
            LIMIT 5
        ''', (root_id,))
        
        children = cursor.fetchall()
        for child_id, child_title, grandchild_count in children:
            indent = '    '
            print(f'  {indent}{child_id:20} → {grandchild_count:2} 个子页面 ({child_title[:30]})')
            
            # 显示二级子页面（如果有）
            if grandchild_count > 0:
                cursor.execute('''
                    SELECT id, title 
                    FROM webbot_page 
                    WHERE parent_id = ?
                    ORDER BY id
                    LIMIT 3
                ''', (child_id,))
                
                grandchildren = cursor.fetchall()
                for grandchild_id, grandchild_title in grandchildren:
                    print(f'  {indent*2}{grandchild_id:20} ({grandchild_title[:30]})')
    
    conn.close()
    return created_pages

if __name__ == "__main__":
    try:
        created = rebuild_hierarchy()
        print(f"\n✅ 成功重建层次结构，创建了 {created} 个目录页面")
        
        # 重启WebBot服务以使更改生效
        print("\n🔄 重启WebBot服务...")
        import subprocess
        subprocess.run(["pkill", "-f", "uvicorn.*webbot"], capture_output=True)
        import time
        time.sleep(2)
        
        print("服务重启完成，请手动启动: cd /home/hongb/.openclaw/workspace/webbot && nohup ./start.sh > webbot.log 2>&1 &")
        
    except Exception as e:
        print(f"\n❌ 重建过程中出错: {e}")
        import traceback
        traceback.print_exc()