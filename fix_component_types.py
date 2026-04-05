#!/usr/bin/env python3
"""
修复组件属性类型以匹配FastAPI模型
"""

import json
import sqlite3

def get_db_connection():
    """获取数据库连接"""
    db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def fix_property_type(prop_type):
    """修复属性类型以匹配模型枚举"""
    type_mapping = {
        'text': 'string',
        'array': 'string',  # 暂时改为string，可能需要特殊处理
        'textarea': 'string',
        'html': 'string',
        'richtext': 'string'
    }
    return type_mapping.get(prop_type, prop_type)

def fix_component_properties():
    """修复所有组件的属性类型"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取所有组件
    cursor.execute("SELECT id, name, properties_json FROM component_templates")
    components = cursor.fetchall()
    
    print(f"🔧 检查 {len(components)} 个组件的属性类型")
    
    updated_count = 0
    for component in components:
        component_id = component['id']
        component_name = component['name']
        properties_json = component['properties_json']
        
        try:
            properties = json.loads(properties_json)
            needs_update = False
            
            # 检查并修复每个属性
            for prop_name, prop_data in properties.items():
                if isinstance(prop_data, dict):
                    current_type = prop_data.get('type')
                    if current_type:
                        new_type = fix_property_type(current_type)
                        if new_type != current_type:
                            print(f"  🔄 {component_name}.{prop_name}: {current_type} → {new_type}")
                            prop_data['type'] = new_type
                            needs_update = True
            
            if needs_update:
                # 更新数据库
                new_properties_json = json.dumps(properties, ensure_ascii=False)
                cursor.execute(
                    "UPDATE component_templates SET properties_json = ? WHERE id = ?",
                    (new_properties_json, component_id)
                )
                updated_count += 1
                print(f"✅ 更新 {component_name} 的属性类型")
                
        except json.JSONDecodeError as e:
            print(f"❌ {component_name} 的JSON解析错误: {e}")
            continue
    
    conn.commit()
    
    print(f"\n📊 修复完成:")
    print(f"  总组件数: {len(components)}")
    print(f"  更新组件数: {updated_count}")
    
    # 显示修复后的组件属性
    cursor.execute("SELECT name, properties_json FROM component_templates WHERE name IN ('wet-group', 'wet-footnotes', 'wet-embed-html')")
    fixed_components = cursor.fetchall()
    
    print(f"\n🔍 修复后的组件属性:")
    for component in fixed_components:
        print(f"\n{component['name']}:")
        properties = json.loads(component['properties_json'])
        for prop_name, prop_data in properties.items():
            if isinstance(prop_data, dict):
                print(f"  - {prop_name}: type={prop_data.get('type')}")
    
    conn.close()

if __name__ == "__main__":
    fix_component_properties()