#!/usr/bin/env python3
"""
快速修正导出API中的字段名
"""
import os
import re

EXPORT_PY = "/home/hongb/.openclaw/workspace/filebot/backend/app/routers/export.py"
EXPORT_SCHEMA = "/home/hongb/.openclaw/workspace/filebot/backend/app/schemas/export.py"

def fix_export_py():
    """修正export.py中的字段名"""
    print(f"🔧 修正 {EXPORT_PY}...")
    
    with open(EXPORT_PY, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换app.metadata为app.settings
    content = re.sub(r'app\.metadata\b', 'app.settings', content)
    content = re.sub(r'"metadata"\s*:\s*app\.metadata', '"settings": app.settings', content)
    
    # 替换document.metadata为document.document_metadata
    content = re.sub(r'document\.metadata\b', 'document.document_metadata', content)
    content = re.sub(r'"metadata"\s*:\s*document\.metadata', '"document_metadata": document.document_metadata', content)
    
    # 移除folder.metadata引用
    content = re.sub(r'"metadata"\s*:\s*folder\.metadata,\s*\n', '', content)
    content = re.sub(r'"metadata"\s*:\s*folder\.metadata', '', content)
    
    # 检查是否还有metadata字段（对于文件夹）
    content = re.sub(r'"metadata"\s*:\s*\{\}', '', content)
    
    # 修正schema导入
    if 'metadata: Optional[Dict[str, Any]]' in content:
        # 替换document部分的metadata为document_metadata
        content = re.sub(
            r'"metadata": document\.metadata',
            '"document_metadata": document.document_metadata',
            content
        )
    
    # 写入文件
    with open(EXPORT_PY, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  ✅ 完成修正")

def fix_export_schema():
    """修正export schema中的字段名"""
    print(f"🔧 修正 {EXPORT_SCHEMA}...")
    
    with open(EXPORT_SCHEMA, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 在DocumentExport中将metadata改为document_metadata
    content = re.sub(
        r'class DocumentExport\(BaseModel\):',
        'class DocumentExport(BaseModel):\n    """文档导出模型"""',
        content
    )
    
    # 查找metadata字段并改为document_metadata
    lines = content.split('\n')
    fixed_lines = []
    in_document_export = False
    
    for i, line in enumerate(lines):
        if 'class DocumentExport' in line:
            in_document_export = True
        elif 'class ' in line and 'DocumentExport' not in line:
            in_document_export = False
        
        if in_document_export and 'metadata: Optional[Dict[str, Any]]' in line:
            # 改为document_metadata
            line = '    document_metadata: Optional[Dict[str, Any]]'
            print(f"  ✅ 将DocumentExport.metadata改为document_metadata")
        
        fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    # 确保FolderExport中没有metadata字段
    if '"metadata": folder.metadata' in content:
        content = content.replace('"metadata": folder.metadata', '')
    
    # 确保AppExport中使用settings而不是metadata
    if 'metadata: Optional[Dict[str, Any]]' in content and 'class AppExport' in content:
        # 在AppExport中
        lines = content.split('\n')
        fixed_lines = []
        in_app_export = False
        
        for line in lines:
            if 'class AppExport' in line:
                in_app_export = True
            elif 'class ' in line and 'AppExport' not in line:
                in_app_export = False
            
            if in_app_export and 'metadata: Optional[Dict[str, Any]]' in line:
                line = '    settings: Optional[Dict[str, Any]]'
                print(f"  ✅ 将AppExport.metadata改为settings")
            
            fixed_lines.append(line)
        
        content = '\n'.join(fixed_lines)
    
    # 写入文件
    with open(EXPORT_SCHEMA, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  ✅ 完成schema修正")

def check_fixes():
    """检查修正结果"""
    print(f"\n🔍 检查修正结果...")
    
    with open(EXPORT_PY, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查关键字段
    issues = []
    
    if 'app.metadata' in content:
        issues.append("仍存在app.metadata")
    
    if 'document.metadata' in content:
        issues.append("仍存在document.metadata")
    
    if '"metadata": app.' in content:
        issues.append('仍存在"metadata": app.')
    
    if '"metadata": document.' in content:
        issues.append('仍存在"metadata": document.')
    
    if issues:
        print(f"  ⚠️  发现问题: {', '.join(issues)}")
        # 显示相关行
        for issue in issues:
            lines = [line for line in content.split('\n') if issue.split(':')[0] in line]
            for line in lines[:2]:
                print(f"    {line.strip()[:80]}")
    else:
        print(f"  ✅ 所有字段名已修正")
    
    # 检查schema
    with open(EXPORT_SCHEMA, 'r', encoding='utf-8') as f:
        schema_content = f.read()
    
    if 'metadata: Optional[Dict[str, Any]]' in schema_content and 'DocumentExport' in schema_content:
        print(f"  ⚠️  DocumentExport中仍有metadata字段")
    else:
        print(f"  ✅ schema字段名正确")

def create_test_script():
    """创建测试脚本"""
    print(f"\n📝 创建测试脚本...")
    
    test_script = """#!/usr/bin/env python3
"""
测试导出功能
"""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path("filebot.db")

def test_export_logic():
    \"\"\"测试导出逻辑\"\"\"
    print("🧪 测试导出逻辑...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 测试1: 获取一个应用
    cursor.execute("SELECT id, name, slug FROM apps LIMIT 1")
    app = cursor.fetchone()
    
    if app:
        app_id, app_name, app_slug = app
        print(f"✅ 找到应用: {app_name} ({app_slug})")
        
        # 测试2: 获取应用的文件夹
        cursor.execute("""
            SELECT id, name, path, document_count 
            FROM folders 
            WHERE app_id = ?
            LIMIT 3
        """, (app_id,))
        
        folders = cursor.fetchall()
        print(f"✅ 找到 {len(folders)} 个文件夹")
        
        for folder in folders:
            folder_id, folder_name, folder_path, doc_count = folder
            print(f"   📁 {folder_name}: {doc_count} 个文档")
            
            # 测试3: 获取文件夹的文档
            cursor.execute("""
                SELECT id, title, original_filename, file_size, file_type
                FROM documents
                WHERE folder_id = ?
                LIMIT 2
            """, (folder_id,))
            
            documents = cursor.fetchall()
            print(f"     📄 文档示例 ({len(documents)} 个):")
            for doc in documents:
                doc_id, title, filename, size, file_type = doc
                size_str = f"{size/1024:.1f}KB" if size else "N/A"
                print(f"       • {title or '无标题'} ({file_type}, {size_str})")
    
    # 测试4: 检查缺失文件标记
    cursor.execute("""
        SELECT COUNT(*) 
        FROM documents 
        WHERE document_metadata LIKE '%\"file_status\": \"missing\"%'
    """)
    missing_count = cursor.fetchone()[0]
    print(f"✅ 标记为缺失的文档: {missing_count} 个")
    
    # 测试5: 生成简单JSON导出
    print(f"\\n📊 生成简单JSON导出示例...")
    
    cursor.execute("""
        SELECT a.name as app_name, 
               COUNT(DISTINCT f.id) as folder_count,
               COUNT(DISTINCT d.id) as document_count
        FROM apps a
        LEFT JOIN folders f ON a.id = f.app_id
        LEFT JOIN documents d ON f.id = d.folder_id
        GROUP BY a.id
        LIMIT 3
    """)
    
    stats = cursor.fetchall()
    
    export_data = {
        "export_time": "2026-04-01T10:45:00Z",
        "summary": {
            "total_apps": len(stats),
            "total_folders": sum(s[1] for s in stats),
            "total_documents": sum(s[2] for s in stats)
        },
        "apps": []
    }
    
    for app_name, folder_count, doc_count in stats:
        app_data = {
            "name": app_name,
            "folder_count": folder_count,
            "document_count": doc_count
        }
        export_data["apps"].append(app_data)
    
    # 保存示例
    with open("export_sample.json", "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 导出示例已保存到 export_sample.json")
    print(f"📋 示例内容:")
    print(json.dumps(export_data, ensure_ascii=False, indent=2)[:500] + "...")
    
    conn.close()
    return True

if __name__ == "__main__":
    test_export_logic()
"""
    
    test_path = Path("/home/hongb/.openclaw/workspace/filebot/backend/test_export_simple.py")
    with open(test_path, 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    print(f"  ✅ 测试脚本已创建: {test_path}")

def main():
    print("=" * 60)
    print("导出API字段名修正")
    print("=" * 60)
    
    # 备份原文件
    import shutil
    if os.path.exists(EXPORT_PY + ".backup"):
        shutil.copy2(EXPORT_PY, EXPORT_PY + ".backup2")
    else:
        shutil.copy2(EXPORT_PY, EXPORT_PY + ".backup")
    
    if os.path.exists(EXPORT_SCHEMA + ".backup"):
        shutil.copy2(EXPORT_SCHEMA, EXPORT_SCHEMA + ".backup2")
    else:
        shutil.copy2(EXPORT_SCHEMA, EXPORT_SCHEMA + ".backup")
    
    print(f"📁 已创建备份文件")
    
    # 修正文件
    fix_export_py()
    fix_export_schema()
    
    # 检查修正
    check_fixes()
    
    # 创建测试脚本
    create_test_script()
    
    print("\n" + "=" * 60)
    print("完成")
    print("=" * 60)
    
    print(f"\n🎯 下一步:")
    print(f"  1. 运行测试脚本: python3 test_export_simple.py")
    print(f"  2. 如果需要，手动检查修正后的文件")
    print(f"  3. 启动后端服务测试完整API")
    print(f"  4. 原文件已备份为 .backup 文件")

if __name__ == "__main__":
    main()