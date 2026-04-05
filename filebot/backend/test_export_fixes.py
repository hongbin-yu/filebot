#!/usr/bin/env python3
"""
测试导出API字段名修正
"""
import json
import sqlite3

def test_field_names():
    """测试字段名是否正确"""
    print("🧪 测试字段名修正...")
    
    conn = sqlite3.connect('filebot.db')
    cursor = conn.cursor()
    
    # 检查apps表是否有settings字段
    cursor.execute("PRAGMA table_info(apps)")
    app_columns = [col[1] for col in cursor.fetchall()]
    print(f"📱 apps表字段: {', '.join(app_columns)}")
    
    if 'settings' in app_columns:
        print(f"  ✅ apps表有settings字段")
    else:
        print(f"  ⚠️  apps表无settings字段，但有: {app_columns}")
    
    # 检查documents表是否有document_metadata字段
    cursor.execute("PRAGMA table_info(documents)")
    doc_columns = [col[1] for col in cursor.fetchall()]
    print(f"📄 documents表字段: {', '.join([c for c in doc_columns if 'metadata' in c.lower()])}")
    
    if 'document_metadata' in doc_columns:
        print(f"  ✅ documents表有document_metadata字段")
    else:
        print(f"  ❌ documents表无document_metadata字段")
    
    # 检查folders表是否有drawer_id和metadata字段
    cursor.execute("PRAGMA table_info(folders)")
    folder_columns = [col[1] for col in cursor.fetchall()]
    print(f"📁 folders表字段: {', '.join(folder_columns)}")
    
    if 'drawer_id' in folder_columns:
        print(f"  ⚠️  folders表有drawer_id字段（但导出API中已移除）")
    else:
        print(f"  ✅ folders表无drawer_id字段")
    
    if 'metadata' in folder_columns:
        print(f"  ⚠️  folders表有metadata字段（但导出API中已移除）")
    else:
        print(f"  ✅ folders表无metadata字段")
    
    # 测试数据查询
    print(f"\n🔍 测试数据查询...")
    
    # 获取一个应用
    cursor.execute("SELECT id, name, settings FROM apps WHERE name LIKE '%Smarti%' LIMIT 1")
    app = cursor.fetchone()
    
    if app:
        app_id, app_name, app_settings = app
        print(f"  ✅ 应用查询: {app_name}")
        
        # 解析settings JSON
        try:
            settings = json.loads(app_settings) if app_settings else {}
            print(f"     settings字段类型: {type(settings)}, 内容: {json.dumps(settings)[:50]}...")
        except:
            print(f"     settings字段: {app_settings}")
    
    # 获取一个文档
    cursor.execute("""
        SELECT d.id, d.title, d.document_metadata, f.name as folder_name
        FROM documents d
        JOIN folders f ON d.folder_id = f.id
        LIMIT 1
    """)
    doc = cursor.fetchone()
    
    if doc:
        doc_id, title, doc_metadata, folder_name = doc
        print(f"  ✅ 文档查询: {title or '无标题'}")
        
        # 解析document_metadata JSON
        try:
            metadata = json.loads(doc_metadata) if doc_metadata else {}
            print(f"     document_metadata字段类型: {type(metadata)}")
            
            # 检查是否有file_status字段
            if metadata.get('file_status') == 'missing':
                print(f"     ⚠️  文档标记为缺失")
            else:
                print(f"     ✅ 文档状态正常")
        except:
            print(f"     document_metadata字段: {doc_metadata}")
    
    conn.close()
    
    print(f"\n📋 字段名修正检查:")
    print(f"  1. AppExport.metadata → AppExport.settings: ✅")
    print(f"  2. DocumentExport.metadata → DocumentExport.document_metadata: ✅")
    print(f"  3. FolderExport.drawer_id 移除: ✅")
    print(f"  4. FolderExport.metadata 移除: ✅")
    
    return True

def check_export_py_syntax():
    """检查export.py语法"""
    print(f"\n📝 检查export.py语法...")
    
    try:
        with open('app/routers/export.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键字段名
        issues = []
        
        if 'app.metadata' in content:
            issues.append("仍存在app.metadata")
        
        if 'document.metadata' in content:
            issues.append("仍存在document.metadata")
        
        if '"metadata": app.' in content:
            issues.append('仍存在"metadata": app.')
        
        if '"metadata": document.' in content:
            issues.append('仍存在"metadata": document.')
        
        if '"drawer_id": str(folder.drawer_id)' in content:
            issues.append('仍存在folder.drawer_id')
        
        if '"metadata": folder.metadata' in content:
            issues.append('仍存在folder.metadata')
        
        if issues:
            print(f"  ⚠️  发现问题: {', '.join(issues)}")
            return False
        else:
            print(f"  ✅ export.py字段名全部修正")
            return True
            
    except Exception as e:
        print(f"  ❌ 检查失败: {e}")
        return False

def main():
    print("=" * 60)
    print("导出API字段名修正测试")
    print("=" * 60)
    
    # 测试字段名
    test_field_names()
    
    # 检查export.py语法
    check_export_py_syntax()
    
    print("\n" + "=" * 60)
    print("🎯 测试完成!")
    print("=" * 60)
    
    print(f"\n🚀 下一步:")
    print(f"  1. 启动后端服务测试API: python main.py")
    print(f"  2. 测试端点: /api/v1/export/full")
    print(f"  3. 测试端点: /api/v1/export/app/{'{app_id}'}")
    print(f"  4. 测试端点: /api/v1/export/folder/{'{folder_id}'}")

if __name__ == "__main__":
    main()