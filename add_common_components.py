#!/usr/bin/env python3
"""
添加用户指定的常用组件：title, list, columns.feature image
"""

import json
import sqlite3
from datetime import datetime

def get_db_connection():
    """获取数据库连接"""
    db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def generate_component_id(name):
    """生成组件ID"""
    return name.lower().replace(' ', '-').replace('(', '').replace(')', '').replace('.', '-')

def add_component_template(cursor, component_data):
    """添加组件模板到数据库"""
    
    component_id = generate_component_id(component_data['name'])
    
    # 检查是否已存在
    cursor.execute("SELECT id FROM component_templates WHERE name = ?", (component_data['name'],))
    if cursor.fetchone():
        print(f"⚠️ 组件 '{component_data['name']}' 已存在，跳过")
        return False
    
    # 准备数据
    now = datetime.now().isoformat()
    
    # 插入数据
    cursor.execute("""
        INSERT INTO component_templates 
        (id, name, display_name, category, description, icon, html_template, 
         css_template, js_template, properties_json, dependencies_json,
         wet_boew_compliant, accessibility_checked, tags_json, author, version,
         status, created_by, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        component_id,
        component_data['name'],
        component_data['display_name'],
        component_data['category'],
        component_data['description'],
        component_data['icon'],
        component_data['html_template'],
        component_data.get('css_template'),
        component_data.get('js_template'),
        json.dumps(component_data['properties'], ensure_ascii=False),
        json.dumps(component_data['dependencies'], ensure_ascii=False),
        1 if component_data.get('wet_boew_compliant', True) else 0,
        1 if component_data.get('accessibility_checked', True) else 0,
        json.dumps(component_data['tags'], ensure_ascii=False),
        component_data.get('author', '系统'),
        component_data.get('version', '1.0.0'),
        component_data.get('status', 'published'),
        component_data.get('created_by', 'system'),
        now,
        now
    ))
    
    print(f"✅ 添加组件: {component_data['display_name']} ({component_id})")
    return True

def get_wet_boew_dependencies():
    """获取WET-BOEW依赖"""
    return [
        {
            "type": "css",
            "url": "https://wet-boew.github.io/wet-boew/css/wet-boew.min.css",
            "version": "4.0.0",
            "required": True
        },
        {
            "type": "js",
            "url": "https://wet-boew.github.io/wet-boew/js/wet-boew.min.js",
            "version": "4.0.0",
            "required": True
        }
    ]

def create_common_components():
    """创建用户指定的常用组件"""
    
    dependencies = get_wet_boew_dependencies()
    
    components = [
        # 1. 标题组件 (title)
        {
            "name": "wet-title",
            "display_name": "标题组件 (WET-BOEW)",
            "category": "content",
            "description": "WET-BOEW标准标题，支持h1-h6级别",
            "icon": "🏷️",
            "html_template": """
<{{level}} class="{{className}}" id="{{id}}">
  {{text}}
</{{level}}>""",
            "properties": {
                "text": {
                    "name": "text",
                    "type": "string",
                    "label": "标题文本",
                    "default": "页面标题",
                    "required": True,
                    "i18n": True
                },
                "level": {
                    "name": "level",
                    "type": "select",
                    "label": "标题级别",
                    "options": ["h1", "h2", "h3", "h4", "h5", "h6"],
                    "default": "h2",
                    "description": "h1为最高级别，h6为最低级别"
                },
                "className": {
                    "name": "className",
                    "type": "string",
                    "label": "CSS类名",
                    "default": "",
                    "description": "额外的CSS类名，多个用空格分隔"
                },
                "alignment": {
                    "name": "alignment",
                    "type": "select",
                    "label": "对齐方式",
                    "options": ["left", "center", "right"],
                    "default": "left",
                    "description": "标题文本对齐方式"
                }
            },
            "dependencies": dependencies,
            "tags": ["title", "heading", "content", "wet-boew"]
        },
        
        # 2. 列表组件 (list)
        {
            "name": "wet-list",
            "display_name": "列表组件 (WET-BOEW)",
            "category": "content",
            "description": "WET-BOEW标准列表，支持有序和无序列表",
            "icon": "📋",
            "html_template": """
<{{listType}} class="{{className}}">
  {{#each items}}
  <li>{{this}}</li>
  {{/each}}
</{{listType}}>""",
            "properties": {
                "listType": {
                    "name": "listType",
                    "type": "select",
                    "label": "列表类型",
                    "options": ["ul", "ol"],
                    "default": "ul",
                    "description": "ul为无序列表，ol为有序列表"
                },
                "items": {
                    "name": "items",
                    "type": "string",
                    "label": "列表项目 (JSON数组)",
                    "description": "JSON数组格式，例如: [\"项目1\", \"项目2\", \"项目3\"]",
                    "default": '["列表项目1", "列表项目2", "列表项目3"]',
                    "required": True,
                    "i18n": True
                },
                "className": {
                    "name": "className",
                    "type": "string",
                    "label": "CSS类名",
                    "default": "",
                    "description": "额外的CSS类名，如list-unstyled等"
                }
            },
            "dependencies": dependencies,
            "tags": ["list", "ul", "ol", "content", "wet-boew"]
        },
        
        # 3. 列特征图片组件 (columns.feature image)
        {
            "name": "wet-feature-columns",
            "display_name": "特征图片列 (WET-BOEW)",
            "category": "content",
            "description": "WET-BOEW标准特征图片列，用于展示特色内容",
            "icon": "🖼️",
            "html_template": """
<div class="row">
  {{#each columns}}
  <div class="col-md-{{../columnSize}}">
    <div class="feature-item">
      {{#if imageUrl}}
      <div class="feature-image">
        <img src="{{imageUrl}}" alt="{{imageAlt}}" class="img-responsive">
      </div>
      {{/if}}
      <div class="feature-content">
        {{#if title}}<h3>{{title}}</h3>{{/if}}
        {{#if description}}<p>{{description}}</p>{{/if}}
      </div>
    </div>
  </div>
  {{/each}}
</div>""",
            "properties": {
                "columns": {
                    "name": "columns",
                    "type": "string",
                    "label": "列数据 (JSON数组)",
                    "description": "JSON数组格式，每列包含imageUrl, imageAlt, title, description",
                    "default": '[{"imageUrl":"https://via.placeholder.com/300x200","imageAlt":"特征图片1","title":"特征1","description":"特征1描述"},{"imageUrl":"https://via.placeholder.com/300x200","imageAlt":"特征图片2","title":"特征2","description":"特征2描述"},{"imageUrl":"https://via.placeholder.com/300x200","imageAlt":"特征图片3","title":"特征3","description":"特征3描述"}]',
                    "required": True,
                    "i18n": True
                },
                "columnSize": {
                    "name": "columnSize",
                    "type": "select",
                    "label": "每列宽度",
                    "options": ["12", "6", "4", "3"],
                    "default": "4",
                    "description": "12为全宽(1列)，6为半宽(2列)，4为三分之一(3列)，3为四分之一(4列)"
                },
                "className": {
                    "name": "className",
                    "type": "string",
                    "label": "CSS类名",
                    "default": "",
                    "description": "额外的CSS类名"
                }
            },
            "dependencies": dependencies,
            "tags": ["columns", "feature", "image", "grid", "content", "wet-boew"]
        }
    ]
    
    return components

def main():
    """主函数"""
    print("🚀 添加用户指定的常用组件")
    print("=" * 50)
    print("用户提到的常用组件:")
    print("  1. title - 标题组件")
    print("  2. list - 列表组件") 
    print("  3. columns.feature image - 特征图片列组件")
    print("=" * 50)
    
    # 连接到数据库
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='component_templates'")
        if not cursor.fetchone():
            print("❌ component_templates 表不存在，请先运行数据库迁移")
            return
        
        # 获取现有组件数量
        cursor.execute("SELECT COUNT(*) as count FROM component_templates")
        current_count = cursor.fetchone()['count']
        print(f"📊 当前组件数量: {current_count}")
        
        # 创建组件数据
        components = create_common_components()
        print(f"📝 准备添加 {len(components)} 个用户指定的常用组件")
        
        # 添加组件
        added_count = 0
        for component in components:
            if add_component_template(cursor, component):
                added_count += 1
        
        # 提交事务
        conn.commit()
        
        # 验证结果
        cursor.execute("SELECT COUNT(*) as count FROM component_templates")
        new_count = cursor.fetchone()['count']
        
        print("\n" + "=" * 50)
        print(f"✅ 组件添加完成!")
        print(f"📈 添加前: {current_count} 个组件")
        print(f"📈 添加后: {new_count} 个组件")
        print(f"📈 成功添加: {added_count} 个组件")
        
        if added_count > 0:
            print("\n🎯 新添加的组件:")
            cursor.execute("SELECT display_name, category FROM component_templates ORDER BY created_at DESC LIMIT ?", (added_count,))
            for row in cursor.fetchall():
                print(f"  • {row['display_name']} ({row['category']})")
        
        print("\n🔗 前端可访问组件API: GET /api/v1/components/templates")
        print("🔁 前端页面需刷新: 访问 http://localhost:5174 并按F5刷新")
        
    except Exception as e:
        print(f"❌ 添加组件时出错: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()