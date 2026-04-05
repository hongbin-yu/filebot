#!/usr/bin/env python3
"""
修复错误的HTML匹配（将首页内容替换回原始纯文本内容）
"""

import sqlite3
import os
import json

def get_db_connection():
    """获取数据库连接"""
    db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def restore_original_content():
    """恢复原始纯文本内容"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("🔍 查找需要修复的页面...")
    
    # 获取所有页面
    cursor.execute('''
        SELECT id, title, content 
        FROM webbot_page 
        WHERE content LIKE '%<%' AND content LIKE '%>%'
        ORDER BY id
    ''')
    
    html_pages = cursor.fetchall()
    
    # 需要修复的页面ID列表（根据之前的错误匹配）
    bad_matches = [
        'canadian-dental-care-plan',
        'canadian-dental-care-plan---apply',
        'canadian-dental-care-plan---when-can-you-visit-an-oral-health-provider',
        'canadian-dental-care-plan---what-is-covered',
        'canadian-dental-care-plan---information-for-oral-health-professionals',
        'canadian-dental-care-plan---do-you-qualify',
        'canadian-dental-care-plan---member-eligibility-review',
        'canadian-dental-care-plan---privacy',
        'application-statistics---canadian-dental-care-plan',
        'canadian-dental-care-plan-providers-preauthorization-resources',
        'canadian-dental-care-plan-promotional-toolkit-overview',
        'rgime-canadien-de-soins-dentaires',
        'employment-insurance-benefits',
        'employment-insurance-reporting',
        'ei-fishing-benefits---overview',
        'benefits-for-self-employed-people',
        'ei-maternity-and-parental-benefits-what-these-benefits-offer',
        'benefits-for-canadians-living-abroad',
        'employment-insurance-and-training-programs',
        'employment-insurance-for-apprentices',
        'benefits-finder-find-benefits-and-financial-help',
        'ei-sickness-benefits-what-these-benefits-offer',
        'ei-regular-benefits',
        'federal-student-work-experience-program',
        'immigrate-through-express-entry',
        'pensions-publiques',
        'guaranteed-income-supplement---allowance',
        'what-to-do-when-someone-dies',
        'benefits-for-children-under-25',
        'canada-pension-plan-post-retirement-disability-benefit',
        'benefits-payment-dates',
        'old-age-security-payment-amounts',
        'canada-pension-plan-retirement-pension',
        'survivors-pension',
        'canada-pension-plan-monthly-payment-amounts',
        'canadian-retirement-income-calculator',
        'questions-and-comments-form',
        'environment-and-natural-resources',
        'national-security-and-defence',
        'manage-life-events',
        'about-government',
        'sign-in-to-a-government-of-canada-online-account',
        'departments-and-agencies',
        'transport-and-infrastructure',
        'policing-justice-and-emergencies',
        'immigration-and-citizenship',
        'mobile-centre',
        'science-and-innovation',
        'assault-style-firearms-compensation-program',
        'submit-a-firearm-compensation-claim-for-businesses',
        'assault-style-firearms-compensation-program-pilot-lessons-learned',
        'compensation-amounts-for-businesses',
        'public-pensions',
        'death-benefit',
        'canada-pension-plan-disability-benefits',
        'lived-or-living-outside-canada---pensions-and-benefits---overview',
        'learn-and-plan-for-your-retirement',
        'guaranteed-income-supplement---overview',
        'contact-old-age-security',
        'employment-insurance-contact-information-for-individuals',
    ]
    
    # 尝试从原始备份中恢复内容
    print(f'需要修复 {len(bad_matches)} 个页面')
    
    # 查找这些页面的当前内容
    fixed_count = 0
    
    for page_id in bad_matches:
        cursor.execute('SELECT id, title, content FROM webbot_page WHERE id = ?', (page_id,))
        page = cursor.fetchone()
        
        if page:
            current_content = page['content']
            current_title = page['title']
            
            # 检查是否是首页内容
            is_homepage = False
            if current_content:
                homepage_indicators = [
                    '<title>Home - Canada.ca</title>',
                    '<title>Accueil - Canada.ca</title>',
                    'Welcome to Canada.ca',
                    'Canada.ca The official website',
                    'Most requested'
                ]
                
                for indicator in homepage_indicators:
                    if indicator in current_content:
                        is_homepage = True
                        break
            
            if is_homepage:
                print(f'\n🔧 修复页面: {page_id}')
                print(f'  当前标题: {current_title}')
                print(f'  问题: 包含首页内容')
                
                # 尝试从pages.json备份中恢复原始内容
                backup_found = False
                
                # 方法1：检查是否有pages.json备份
                pages_json_path = '/home/hongb/.openclaw/workspace/webbot/static/pages.json'
                if os.path.exists(pages_json_path):
                    try:
                        with open(pages_json_path, 'r', encoding='utf-8') as f:
                            pages_data = json.load(f)
                            for page_data in pages_data:
                                if page_data.get('id') == page_id:
                                    original_content = page_data.get('content', '')
                                    original_title = page_data.get('title', current_title)
                                    
                                    if original_content and len(original_content) > 100:
                                        # 恢复原始内容
                                        cursor.execute('''
                                            UPDATE webbot_page 
                                            SET title = ?, content = ?, last_modified = datetime('now')
                                            WHERE id = ?
                                        ''', (original_title, original_content, page_id))
                                        print(f'  ✓ 从pages.json恢复原始内容 ({len(original_content)}字符)')
                                        backup_found = True
                                        fixed_count += 1
                                        break
                    except Exception as e:
                        print(f'  ⚠️ 读取pages.json失败: {e}')
                
                if not backup_found:
                    # 方法2：设置为空内容，稍后重新导入
                    print(f'  ⚠️ 未找到备份，清空内容')
                    cursor.execute('''
                        UPDATE webbot_page 
                        SET content = ?, last_modified = datetime('now')
                        WHERE id = ?
                    ''', (f'[需要重新导入] {current_title}', page_id))
                    fixed_count += 1
            else:
                print(f'\n✓ 页面正常: {page_id}')
                print(f'  标题: {current_title[:50]}...')
    
    # 提交事务
    conn.commit()
    
    print(f'\n📊 修复完成:')
    print(f'  修复了 {fixed_count} 个页面')
    
    # 验证结果
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN content LIKE '%<%' AND content LIKE '%>%' THEN 1 ELSE 0 END) as html_count,
            SUM(CASE WHEN content NOT LIKE '%<%' OR content NOT LIKE '%>%' THEN 1 ELSE 0 END) as text_count,
            COUNT(*) as total
        FROM webbot_page
    ''')
    result = cursor.fetchone()
    
    print(f'  修复后统计:')
    print(f'    HTML页面: {result["html_count"]}')
    print(f'    纯文本页面: {result["text_count"]}')
    print(f'    总计: {result["total"]}')
    
    conn.close()
    return fixed_count

if __name__ == "__main__":
    print("🚀 开始修复错误的HTML匹配")
    print("=" * 60)
    
    try:
        count = restore_original_content()
        print(f"\n✅ 成功修复 {count} 个页面")
    except Exception as e:
        print(f"\n❌ 修复过程中出错: {e}")
        import traceback
        traceback.print_exc()