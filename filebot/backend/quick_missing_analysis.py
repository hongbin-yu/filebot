#!/usr/bin/env python3
"""
快速分析缺失文件，识别最重要的文件
"""

import sqlite3
import json
from pathlib import Path

FILEBOT_DB = Path("filebot.db")

def analyze_missing_docs():
    """分析缺失文档"""
    conn = sqlite3.connect(FILEBOT_DB)
    cursor = conn.cursor()
    
    # 缺失文件列表
    missing_files = [
        "smarti.000\\....00000004.pdf",
        "smarti.000\\IDX00000085.CLD", 
        "smarti.000\\IDX00000101.pdf",
        "smarti.002\\IDX00000104.pdf",
        "smarti.003\\....00000005.pdf",
        "smarti.003\\sig00000004.png",
        "smarti.004\\IDX00000084.CLD",
        "smarti.004\\IDX00000103.pdf",
        "smarti.005\\IDX00000096.CLD",
        "smarti.005\\IDX00000098.CLD",
        "smarti.005\\IDX00000099.CLD",
        "smarti.005\\IDX00000102.pdf",
        "smarti.006\\IDX00000100.pdf",
        "smarti.007\\IDX00000087.CLD",
        "smarti.007\\IDX00000094.CLD"
    ]
    
    print("🔍 分析缺失文档重要性...")
    
    # 获取缺失文档的详细信息
    results = []
    for original_filename in missing_files:
        cursor.execute("""
            SELECT d.id, d.title, d.description, d.document_number, d.status,
                   d.type, d.file_type, d.mime_type, d.file_size,
                   f.name as folder_name, a.name as app_name
            FROM documents d
            LEFT JOIN folders f ON d.folder_id = f.id
            LEFT JOIN apps a ON f.app_id = a.id
            WHERE d.original_filename = ?
        """, (original_filename,))
        
        row = cursor.fetchone()
        if row:
            doc_id, title, description, doc_number, status, doc_type, file_type, mime_type, file_size, folder_name, app_name = row
            
            # 评估重要性
            importance_score = 0
            importance_reasons = []
            
            # 1. 文档类型重要性
            if doc_type and doc_type.lower() in ['invoice', 'contract', 'agreement']:
                importance_score += 3
                importance_reasons.append(f"重要文档类型: {doc_type}")
            
            # 2. 文件类型重要性
            if file_type and file_type.lower() in ['pdf', 'doc', 'docx']:
                importance_score += 2
                importance_reasons.append(f"重要文件格式: {file_type}")
            elif file_type and file_type.lower() == 'cld':
                importance_score += 1
            
            # 3. 文档状态重要性
            if status and status.lower() in ['final', 'approved', 'signed']:
                importance_score += 2
                importance_reasons.append(f"最终状态: {status}")
            
            # 4. 标题/描述重要性
            if title and any(keyword in title.lower() for keyword in ['final', 'contract', 'agreement', 'invoice', 'payment']):
                importance_score += 2
                importance_reasons.append(f"标题含关键词: {title[:30]}...")
            
            # 5. 文件大小（如果已知）
            if file_size and file_size > 1024 * 1024:  # >1MB
                importance_score += 1
                importance_reasons.append(f"大文件: {file_size/1024/1024:.1f}MB")
            
            results.append({
                'original_filename': original_filename,
                'title': title,
                'description': description,
                'document_number': doc_number,
                'status': status,
                'type': doc_type,
                'file_type': file_type,
                'mime_type': mime_type,
                'file_size': file_size,
                'folder_name': folder_name,
                'app_name': app_name,
                'importance_score': importance_score,
                'importance_reasons': importance_reasons
            })
        else:
            # 文档不在数据库中？这不应该发生
            print(f"  ⚠️ 文档不在数据库中: {original_filename}")
    
    # 按重要性排序
    results.sort(key=lambda x: x['importance_score'], reverse=True)
    
    print(f"\n📊 缺失文档重要性排序 (共 {len(results)} 个):")
    print("=" * 120)
    print(f"{'文件名':30} {'标题':25} {'类型':10} {'状态':10} {'大小':10} {'重要性':8} {'应用'}")
    print("-" * 120)
    
    for doc in results[:10]:  # 显示前10个
        title_short = (doc['title'][:22] + '...') if doc['title'] and len(doc['title']) > 22 else (doc['title'] or '')
        file_short = doc['original_filename'].split('\\')[-1][:20] if '\\' in doc['original_filename'] else doc['original_filename'][:20]
        app_short = (doc['app_name'][:15] + '...') if doc['app_name'] and len(doc['app_name']) > 15 else (doc['app_name'] or '')
        
        file_size_str = f"{doc['file_size']/1024:.0f}KB" if doc['file_size'] else "N/A"
        
        doc_type = doc.get('type') or ''
        doc_status = doc.get('status') or ''
        print(f"{file_short:30} {title_short:25} {doc_type[:8]:10} {doc_status[:8]:10} {file_size_str:10} {doc['importance_score']:8} {app_short}")
    
    # 显示重要性原因
    print(f"\n🔍 最重要的文档详细分析:")
    for doc in results[:5]:
        print(f"\n📄 {doc['original_filename']}")
        print(f"   标题: {doc['title']}")
        print(f"   描述: {doc['description'][:50] if doc['description'] else '无'}")
        print(f"   文件夹: {doc['folder_name']}")
        print(f"   应用: {doc['app_name']}")
        print(f"   重要性分数: {doc['importance_score']}")
        if doc['importance_reasons']:
            print(f"   重要性原因: {', '.join(doc['importance_reasons'])}")
    
    # 分类统计
    print(f"\n📈 分类统计:")
    
    # 按文件类型
    file_types = {}
    for doc in results:
        ft = doc['file_type'] or '未知'
        file_types[ft] = file_types.get(ft, 0) + 1
    
    print(f"  文件类型分布:")
    for ft, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
        print(f"    {ft}: {count} 个")
    
    # 按应用
    apps = {}
    for doc in results:
        app = doc['app_name'] or '未知'
        apps[app] = apps.get(app, 0) + 1
    
    print(f"  应用分布:")
    for app, count in sorted(apps.items(), key=lambda x: x[1], reverse=True):
        print(f"    {app}: {count} 个")
    
    conn.close()
    
    return results

def check_alternative_locations():
    """检查替代位置"""
    print("\n🔍 检查可能的替代位置...")
    
    # 检查备份目录中的所有PDF文件
    backup_root = Path("/home/hongb/.openclaw/workspace/filebot/backups/production_migration_20260321_175924")
    
    # 查找所有PDF文件
    pdf_files = []
    for pdf_path in backup_root.rglob("*.pdf"):
        pdf_files.append(pdf_path.relative_to(backup_root))
    
    print(f"  备份中的PDF文件: {len(pdf_files)} 个")
    
    # 查找可能匹配的文件
    print(f"\n  可能匹配的文件:")
    
    # 查找类似00000004.pdf的文件
    patterns_to_check = [
        "00000004.pdf", "00000005.pdf", 
        "IDX00000101.pdf", "IDX00000104.pdf"
    ]
    
    for pattern in patterns_to_check:
        matches = []
        for pdf_path in pdf_files:
            if pattern.lower() in str(pdf_path).lower():
                matches.append(pdf_path)
        
        if matches:
            print(f"    {pattern}: 找到 {len(matches)} 个匹配")
            for match in matches[:2]:  # 显示前2个
                print(f"      - {match}")
        else:
            print(f"    {pattern}: 未找到")

def main():
    print("=" * 60)
    print("缺失文档快速分析")
    print("=" * 60)
    
    # 分析缺失文档
    results = analyze_missing_docs()
    
    # 检查替代位置
    check_alternative_locations()
    
    print("\n" + "=" * 60)
    print("建议调查策略")
    print("=" * 60)
    
    # 基于分析结果提供建议
    top_important = [r for r in results if r['importance_score'] >= 3]
    medium_important = [r for r in results if 1 <= r['importance_score'] < 3]
    low_important = [r for r in results if r['importance_score'] == 0]
    
    print(f"💎 高重要性文档 ({len(top_important)} 个):")
    for doc in top_important[:3]:
        print(f"  • {doc['original_filename']} (分数: {doc['importance_score']})")
    
    print(f"\n🔄 中重要性文档 ({len(medium_important)} 个):")
    
    print(f"\n📋 低重要性文档 ({len(low_important)} 个)")
    
    print(f"\n🎯 建议调查顺序:")
    print(f"  1. 先调查 {len(top_important)} 个高重要性文档")
    print(f"  2. 选择性调查 {min(5, len(medium_important))} 个中重要性文档")  
    print(f"  3. 低重要性文档标记为'缺失'，继续其他任务")

if __name__ == "__main__":
    main()