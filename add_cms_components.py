#!/usr/bin/env python3
"""
添加CMS截图中显示的组件
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

def create_cms_components():
    """创建CMS截图中显示的组件"""
    
    dependencies = get_wet_boew_dependencies()
    
    components = [
        # 1. 图片组件 (Image)
        {
            "name": "wet-image",
            "display_name": "图片组件 (WET-BOEW)",
            "category": "content",
            "description": "WET-BOEW标准图片组件，支持响应式和可访问性",
            "icon": "🖼️",
            "html_template": """
<figure class="{{figureClass}}">
  <img src="{{src}}" alt="{{altText}}" class="{{imageClass}}" width="{{width}}" height="{{height}}">
  {{#if caption}}
  <figcaption>{{caption}}</figcaption>
  {{/if}}
</figure>""",
            "properties": {
                "src": {
                    "name": "src",
                    "type": "string",
                    "label": "图片URL",
                    "default": "https://via.placeholder.com/300x200",
                    "required": True,
                    "description": "图片的URL地址"
                },
                "altText": {
                    "name": "altText",
                    "type": "string",
                    "label": "替代文本",
                    "default": "描述图片内容",
                    "required": True,
                    "description": "图片的替代文本，用于可访问性"
                },
                "caption": {
                    "name": "caption",
                    "type": "string",
                    "label": "图片说明",
                    "default": "",
                    "description": "图片下方的说明文字"
                },
                "width": {
                    "name": "width",
                    "type": "string",
                    "label": "宽度",
                    "default": "300",
                    "description": "图片宽度（像素或百分比）"
                },
                "height": {
                    "name": "height",
                    "type": "string",
                    "label": "高度",
                    "default": "200",
                    "description": "图片高度（像素或百分比）"
                },
                "alignment": {
                    "name": "alignment",
                    "type": "select",
                    "label": "对齐方式",
                    "options": ["left", "center", "right"],
                    "default": "center",
                    "description": "图片对齐方式"
                }
            },
            "dependencies": dependencies,
            "tags": ["image", "media", "content", "wet-boew"]
        },
        
        # 2. 水平线组件 (Horizontal Line)
        {
            "name": "wet-horizontal-line",
            "display_name": "水平线组件 (WET-BOEW)",
            "category": "content",
            "description": "WET-BOEW标准水平分隔线",
            "icon": "➖",
            "html_template": """
<hr class="{{className}}">""",
            "properties": {
                "className": {
                    "name": "className",
                    "type": "string",
                    "label": "CSS类名",
                    "default": "",
                    "description": "额外的CSS类名"
                },
                "thickness": {
                    "name": "thickness",
                    "type": "select",
                    "label": "线粗",
                    "options": ["thin", "medium", "thick"],
                    "default": "medium",
                    "description": "水平线的粗细"
                }
            },
            "dependencies": dependencies,
            "tags": ["horizontal-line", "separator", "content", "wet-boew"]
        },
        
        # 3. HTML嵌入组件 (Embed HTML)
        {
            "name": "wet-embed-html",
            "display_name": "HTML嵌入组件 (WET-BOEW)",
            "category": "content",
            "description": "嵌入自定义HTML代码",
            "icon": "📄",
            "html_template": """
<div class="embed-html {{className}}">
  {{{html}}}
</div>""",
            "properties": {
                "html": {
                    "name": "html",
                    "type": "text",
                    "label": "HTML代码",
                    "default": "<p>自定义HTML内容</p>",
                    "required": True,
                    "description": "要嵌入的HTML代码"
                },
                "className": {
                    "name": "className",
                    "type": "string",
                    "label": "CSS类名",
                    "default": "",
                    "description": "容器CSS类名"
                }
            },
            "dependencies": dependencies,
            "tags": ["embed", "html", "custom", "content", "wet-boew"]
        },
        
        # 4. 特色链接组件 (Featured Link)
        {
            "name": "wet-featured-link",
            "display_name": "特色链接组件 (WET-BOEW)",
            "category": "navigation",
            "description": "带有图标的特色链接",
            "icon": "🔗",
            "html_template": """
<a href="{{url}}" class="featured-link {{className}}" {{#if target}}target="{{target}}"{{/if}}>
  {{#if icon}}
  <span class="featured-link-icon">{{icon}}</span>
  {{/if}}
  <span class="featured-link-text">{{text}}</span>
</a>""",
            "properties": {
                "text": {
                    "name": "text",
                    "type": "string",
                    "label": "链接文本",
                    "default": "了解更多",
                    "required": True,
                    "i18n": True
                },
                "url": {
                    "name": "url",
                    "type": "string",
                    "label": "链接URL",
                    "default": "#",
                    "required": True
                },
                "icon": {
                    "name": "icon",
                    "type": "string",
                    "label": "图标",
                    "default": "➔",
                    "description": "图标字符或emoji"
                },
                "target": {
                    "name": "target",
                    "type": "select",
                    "label": "打开方式",
                    "options": ["_self", "_blank", "_parent", "_top"],
                    "default": "_self",
                    "description": "链接打开的目标窗口"
                },
                "alignment": {
                    "name": "alignment",
                    "type": "select",
                    "label": "对齐方式",
                    "options": ["left", "center", "right"],
                    "default": "left",
                    "description": "链接对齐方式"
                }
            },
            "dependencies": dependencies,
            "tags": ["link", "navigation", "featured", "wet-boew"]
        },
        
        # 5. 脚注组件 (Footnotes)
        {
            "name": "wet-footnotes",
            "display_name": "脚注组件 (WET-BOEW)",
            "category": "content",
            "description": "WET-BOEW标准脚注组件",
            "icon": "📝",
            "html_template": """
<section class="footnotes {{className}}">
  <h2>{{title}}</h2>
  <ol>
    {{#each footnotes}}
    <li id="fn{{@index}}">
      <p>{{this}} <a href="#fnref{{@index}}" class="footnote-backref">↩</a></p>
    </li>
    {{/each}}
  </ol>
</section>""",
            "properties": {
                "title": {
                    "name": "title",
                    "type": "string",
                    "label": "脚注标题",
                    "default": "脚注",
                    "i18n": True
                },
                "footnotes": {
                    "name": "footnotes",
                    "type": "array",
                    "label": "脚注列表",
                    "default": ["这是第一个脚注", "这是第二个脚注"],
                    "description": "脚注内容列表"
                },
                "className": {
                    "name": "className",
                    "type": "string",
                    "label": "CSS类名",
                    "default": "",
                    "description": "容器CSS类名"
                }
            },
            "dependencies": dependencies,
            "tags": ["footnotes", "references", "content", "wet-boew"]
        },
        
        # 6. 分组容器组件 (Group)
        {
            "name": "wet-group",
            "display_name": "分组容器组件 (WET-BOEW)",
            "category": "layout",
            "description": "用于分组其他组件的容器",
            "icon": "📦",
            "html_template": """
<div class="group-container {{className}}">
  <div class="group-content">
    {{{children}}}
  </div>
</div>""",
            "properties": {
                "children": {
                    "name": "children",
                    "type": "text",
                    "label": "子内容",
                    "default": "<p>分组内容</p>",
                    "description": "分组内的HTML内容"
                },
                "className": {
                    "name": "className",
                    "type": "string",
                    "label": "CSS类名",
                    "default": "",
                    "description": "容器CSS类名"
                },
                "background": {
                    "name": "background",
                    "type": "color",
                    "label": "背景颜色",
                    "default": "#f5f5f5",
                    "description": "分组背景颜色"
                },
                "padding": {
                    "name": "padding",
                    "type": "string",
                    "label": "内边距",
                    "default": "20px",
                    "description": "分组内边距"
                }
            },
            "dependencies": dependencies,
            "tags": ["group", "container", "layout", "wet-boew"]
        }
    ]
    
    return components

def main():
    print("🚀 添加CMS截图中显示的组件")
    print("=" * 50)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='component_templates'")
    if not cursor.fetchone():
        print("❌ component_templates 表不存在，请先运行数据库迁移")
        conn.close()
        return
    
    # 获取当前组件数量
    cursor.execute("SELECT COUNT(*) as count FROM component_templates")
    current_count = cursor.fetchone()['count']
    print(f"📊 当前组件数量: {current_count}")
    
    # 创建组件
    components = create_cms_components()
    print(f"📝 准备添加 {len(components)} 个CMS组件")
    
    added_count = 0
    for component_data in components:
        if add_component_template(cursor, component_data):
            added_count += 1
    
    conn.commit()
    
    # 获取添加后的数量
    cursor.execute("SELECT COUNT(*) as count FROM component_templates")
    new_count = cursor.fetchone()['count']
    
    print("\n" + "=" * 50)
    print(f"✅ 组件添加完成!")
    print(f"📈 添加前: {current_count} 个组件")
    print(f"📈 添加后: {new_count} 个组件")
    print(f"📈 成功添加: {added_count} 个组件")
    
    # 显示新添加的组件
    cursor.execute("SELECT display_name, category FROM component_templates ORDER BY created_at DESC LIMIT ?", (added_count,))
    new_components = cursor.fetchall()
    
    print(f"\n🎯 新添加的组件:")
    for component in new_components:
        print(f"  • {component['display_name']} ({component['category']})")
    
    print(f"\n🔗 前端可访问组件API: GET /api/v1/components/templates")
    print(f"🔁 前端页面需刷新: 访问 http://localhost:5174 并按F5刷新")
    
    conn.close()

if __name__ == "__main__":
    main()