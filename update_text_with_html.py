#!/usr/bin/env python3
"""
将纯文本页面更新为HTML版本（如果可用）
"""

import sqlite3
import re
from datetime import datetime

def get_db_connection():
    """获取数据库连接"""
    db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def find_best_html_match(text_id, text_title, html_pages):
    """为纯文本页面找到最佳HTML匹配"""
    # 简化ID以便比较
    def simplify(s):
        return re.sub(r'[^a-z0-9]', '', s.lower())
    
    simple_text_id = simplify(text_id)
    simple_text_title = simplify(text_title.replace(' - Canada.ca', '').replace('Canada.ca', ''))
    
    best_match = None
    best_score = 0
    
    for html_id, (html_title, html_content) in html_pages.items():
        simple_html_id = simplify(html_id)
        simple_html_title = simplify(html_title.replace(' - Canada.ca', '').replace('Canada.ca', ''))
        
        score = 0
        
        # 检查ID匹配
        if simple_text_id == simple_html_id:
            score += 100
        elif simple_text_id in simple_html_id:
            score += 80
        elif simple_html_id in simple_text_id:
            score += 80
        
        # 检查标题匹配
        if simple_text_title == simple_html_title:
            score += 50
        elif simple_text_title in simple_html_title:
            score += 30
        elif simple_html_title in simple_text_title:
            score += 30
        
        # 检查常见关键词
        common_words = ['contact', 'benefits', 'health', 'indigenous', 'privacy', 'social', 'taxes']
        for word in common_words:
            if word in simple_text_id and word in simple_html_id:
                score += 20
        
        if score > best_score and score > 50:  # 至少需要一定的匹配度
            best_score = score
            best_match = (html_id, html_title, html_content)
    
    return best_match, best_score

def update_text_pages_with_html():
    """用HTML内容更新纯文本页面"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("🔍 分析页面数据...")
    
    # 获取所有页面
    cursor.execute('''
        SELECT id, title, content,
               CASE 
                   WHEN content LIKE '%<%' AND content LIKE '%>%' THEN 'HTML'
                   ELSE 'TEXT'
               END as content_type
        FROM webbot_page
    ''')
    
    pages = cursor.fetchall()
    
    # 分离HTML和纯文本页面
    html_pages = {}
    text_pages = {}
    
    for page_id, title, content, content_type in pages:
        if content_type == 'HTML':
            html_pages[page_id] = (title, content)
        else:
            text_pages[page_id] = (title, content)
    
    print(f'HTML页面: {len(html_pages)}')
    print(f'纯文本页面: {len(text_pages)}')
    
    # 查找匹配并更新
    updated_count = 0
    matches_found = 0
    
    current_time = datetime.now().isoformat()
    
    for text_id, (text_title, text_content) in text_pages.items():
        # 为纯文本页面找到最佳HTML匹配
        best_match, score = find_best_html_match(text_id, text_title, html_pages)
        
        if best_match:
            html_id, html_title, html_content = best_match
            matches_found += 1
            
            print(f'\n📄 匹配: {text_id} -> {html_id} (匹配度: {score})')
            print(f'  纯文本标题: {text_title[:60]}...')
            print(f'  HTML标题: {html_title[:60]}...')
            
            # 决定是否更新
            should_update = score >= 80  # 高匹配度才更新
            
            if should_update:
                print(f'  🔄 更新纯文本页面为HTML内容...')
                try:
                    # 更新页面内容，但保持原始ID（以便前端兼容）
                    cursor.execute('''
                        UPDATE webbot_page 
                        SET title = ?, content = ?, last_modified = ?
                        WHERE id = ?
                    ''', (html_title, html_content, current_time, text_id))
                    
                    updated_count += 1
                    print(f'    ✓ 更新成功')
                except Exception as e:
                    print(f'    ✗ 更新失败: {e}')
            else:
                print(f'  ⚠️ 跳过: 匹配度不足 ({score} < 80)')
        else:
            # 没有找到HTML匹配，但我们可以尝试从HTML页面中查找类似内容
            pass
    
    # 提交事务
    conn.commit()
    
    print(f'\n📊 更新完成:')
    print(f'  找到匹配: {matches_found} 个页面')
    print(f'  已更新: {updated_count} 个页面')
    
    # 验证结果
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN content LIKE '%<%' AND content LIKE '%>%' THEN 1 ELSE 0 END) as html_count,
            SUM(CASE WHEN content NOT LIKE '%<%' OR content NOT LIKE '%>%' THEN 1 ELSE 0 END) as text_count,
            COUNT(*) as total
        FROM webbot_page
    ''')
    result = cursor.fetchone()
    
    print(f'  更新后统计:')
    print(f'    HTML页面: {result["html_count"]}')
    print(f'    纯文本页面: {result["text_count"]}')
    print(f'    总计: {result["total"]}')
    
    conn.close()
    return updated_count

if __name__ == "__main__":
    print("🚀 开始用HTML内容更新纯文本页面")
    print("=" * 60)
    
    try:
        count = update_text_pages_with_html()
        print(f"\n✅ 成功更新 {count} 个页面")
    except Exception as e:
        print(f"\n❌ 更新过程中出错: {e}")
        import traceback
        traceback.print_exc()