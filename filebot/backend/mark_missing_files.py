#!/usr/bin/env python3
"""
标记缺失文件的状态
"""
import sqlite3
import json
from pathlib import Path

FILEBOT_DB = Path("filebot.db")

def mark_missing_documents():
    """标记缺失文档"""
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
    
    print("🔧 标记缺失文档...")
    
    updated_count = 0
    error_count = 0
    
    for original_filename in missing_files:
        try:
            # 检查文档是否存在
            cursor.execute("SELECT id, title FROM documents WHERE original_filename = ?", (original_filename,))
            doc = cursor.fetchone()
            
            if doc:
                doc_id, title = doc
                
                # 获取当前document_metadata
                cursor.execute("SELECT document_metadata FROM documents WHERE id = ?", (doc_id,))
                result = cursor.fetchone()
                current_metadata = json.loads(result[0]) if result and result[0] else {}
                
                # 更新document_metadata
                current_metadata['file_status'] = 'missing'
                current_metadata['missing_reason'] = 'not_found_in_backup'
                current_metadata['marked_missing_at'] = '2026-04-01T10:30:00Z'
                
                # 更新数据库
                cursor.execute(
                    "UPDATE documents SET document_metadata = ? WHERE id = ?",
                    (json.dumps(current_metadata), doc_id)
                )
                
                print(f"  ✅ 标记: {original_filename} ({title})")
                updated_count += 1
            else:
                print(f"  ⚠️  文档不在数据库中: {original_filename}")
                error_count += 1
                
        except Exception as e:
            print(f"  ❌ 错误处理 {original_filename}: {e}")
            error_count += 1
    
    conn.commit()
    
    # 验证更新
    print(f"\n📊 验证更新...")
    cursor.execute("""
        SELECT COUNT(*) 
        FROM documents 
        WHERE document_metadata LIKE '%"file_status": "missing"%'
    """)
    missing_count = cursor.fetchone()[0]
    print(f"  标记为缺失的文档总数: {missing_count}")
    
    # 显示标记的文档
    cursor.execute("""
        SELECT d.original_filename, d.title, f.name as folder_name
        FROM documents d
        LEFT JOIN folders f ON d.folder_id = f.id
        WHERE d.document_metadata LIKE '%"file_status": "missing"%'
        ORDER BY d.original_filename
        LIMIT 10
    """)
    
    marked_docs = cursor.fetchall()
    if marked_docs:
        print(f"\n📝 标记的文档示例 (前10个):")
        for original, title, folder in marked_docs:
            title_short = title[:20] + "..." if title and len(title) > 20 else title or ""
            print(f"  {original[:40]:40} {title_short:20} [{folder or '无文件夹'}]")
    
    conn.close()
    
    return updated_count, error_count

def add_file_status_field():
    """在metadata中添加file_status字段的索引"""
    print("\n🔧 优化metadata查询...")
    
    conn = sqlite3.connect(FILEBOT_DB)
    cursor = conn.cursor()
    
    # 检查是否有索引
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND name LIKE '%metadata%'
    """)
    indexes = cursor.fetchall()
    
    print(f"  现有metadata索引: {len(indexes)} 个")
    for idx in indexes:
        print(f"    - {idx[0]}")
    
    # 建议手动优化
    print(f"\n💡 建议:")
    print(f"  1. 对于生产环境，考虑添加metadata字段的索引")
    print(f"  2. 或者添加专门的file_status列")
    print(f"  3. 当前小规模使用JSON查询足够")
    
    conn.close()

def create_missing_report():
    """创建缺失文件报告"""
    print("\n📄 创建缺失文件报告...")
    
    conn = sqlite3.connect(FILEBOT_DB)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            d.original_filename,
            d.title,
            d.file_type,
            d.file_size,
            f.name as folder_name,
            a.name as app_name,
            d.document_metadata
        FROM documents d
        LEFT JOIN folders f ON d.folder_id = f.id
        LEFT JOIN apps a ON f.app_id = a.id
        WHERE d.document_metadata LIKE '%"file_status": "missing"%'
        ORDER BY d.original_filename
    """)
    
    missing_docs = cursor.fetchall()
    
    if missing_docs:
        report_path = Path("missing_files_report.txt")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("缺失文件报告\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"生成时间: 2026-04-01\n")
            f.write(f"缺失文件总数: {len(missing_docs)}\n\n")
            
            f.write("详细列表:\n")
            f.write("-" * 100 + "\n")
            f.write(f"{'文件名':40} {'类型':10} {'大小':10} {'应用':20}\n")
            f.write("-" * 100 + "\n")
            
            for doc in missing_docs:
                original, title, file_type, file_size, folder, app, metadata = doc
                size_str = f"{file_size/1024:.0f}KB" if file_size else "N/A"
                app_short = app[:18] + "..." if app and len(app) > 18 else app or ""
                
                f.write(f"{original[:38]:40} {file_type or '':10} {size_str:10} {app_short:20}\n")
            
            f.write("\n\n摘要:\n")
            f.write(f"  • 总缺失文件: {len(missing_docs)}\n")
            f.write(f"  • 涉及应用: {len(set(d[5] for d in missing_docs if d[5]))} 个\n")
            f.write(f"  • 涉及文件夹: {len(set(d[4] for d in missing_docs if d[4]))} 个\n")
        
        print(f"  ✅ 报告已保存到: {report_path.absolute()}")
    else:
        print(f"  ℹ️  没有找到标记为缺失的文档")
    
    conn.close()

def main():
    print("=" * 60)
    print("标记缺失文件")
    print("=" * 60)
    
    # 标记缺失文档
    updated, errors = mark_missing_documents()
    
    print(f"\n📊 标记结果:")
    print(f"  成功标记: {updated} 个文档")
    print(f"  错误/未找到: {errors} 个")
    
    # 优化metadata查询
    add_file_status_field()
    
    # 创建报告
    create_missing_report()
    
    print("\n" + "=" * 60)
    print("下一步")
    print("=" * 60)
    
    print(f"\n🎯 已完成:")
    print(f"  ✅ 标记了 {updated} 个缺失文档")
    print(f"  ✅ 创建了缺失文件报告")
    
    print(f"\n🚀 继续:")
    print(f"  1. 现在可以测试导出功能")
    print(f"  2. 缺失文档会在导出中显示file_status='missing'")
    print(f"  3. 用户可以清楚知道哪些文件不可用")

if __name__ == "__main__":
    main()