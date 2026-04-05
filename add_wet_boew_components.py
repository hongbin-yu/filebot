#!/usr/bin/env python3
"""
批量添加WET-BOEW标准组件
用于演示系统的组件扩展
"""

import json
import uuid
from datetime import datetime
import sqlite3

def get_db_connection():
    """获取数据库连接"""
    db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def generate_component_id(name):
    """生成组件ID"""
    # 使用名称的简化版本作为ID
    return name.lower().replace(' ', '-').replace('(', '').replace(')', '')

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

def create_wet_boew_components():
    """创建WET-BOEW组件列表"""
    
    dependencies = get_wet_boew_dependencies()
    
    components = [
        # 1. 面包屑导航
        {
            "name": "wet-breadcrumb",
            "display_name": "面包屑导航 (WET-BOEW)",
            "category": "navigation",
            "description": "WET-BOEW标准面包屑导航，显示页面层级结构",
            "icon": "🍞",
            "html_template": """
<nav aria-label="面包屑导航">
  <ul id="wet-breadcrumb" class="breadcrumb">
    {{#each items}}
    <li{{#if @last}} class="active"{{/if}}>
      {{#if url}}<a href="{{url}}">{{text}}</a>{{else}}{{text}}{{/if}}
    </li>
    {{/each}}
  </ul>
</nav>""",
            "properties": {
                "items": {
                    "name": "items",
                    "type": "string",
                    "label": "面包屑项目 (JSON格式)",
                    "description": "JSON数组格式，例如: [{'text':'首页','url':'/'}, {'text':'当前页面'}]",
                    "default": '[{"text":"首页","url":"/"},{"text":"当前页面"}]',
                    "required": True,
                    "i18n": True
                }
            },
            "dependencies": dependencies,
            "tags": ["breadcrumb", "navigation", "wet-boew"]
        },
        
        # 2. 分页组件
        {
            "name": "wet-pagination",
            "display_name": "分页组件 (WET-BOEW)",
            "category": "navigation",
            "description": "WET-BOEW标准分页组件，支持多页导航",
            "icon": "🔢",
            "html_template": """
<nav aria-label="分页导航">
  <ul class="pagination">
    {{#if showPrevious}}
    <li><a href="{{previousUrl}}" aria-label="上一页">«</a></li>
    {{/if}}
    
    {{#each pages}}
    <li{{#if active}} class="active"{{/if}}>
      <a href="{{url}}">{{number}}</a>
    </li>
    {{/each}}
    
    {{#if showNext}}
    <li><a href="{{nextUrl}}" aria-label="下一页">»</a></li>
    {{/if}}
  </ul>
</nav>""",
            "properties": {
                "currentPage": {
                    "name": "currentPage",
                    "type": "number",
                    "label": "当前页码",
                    "default": 1,
                    "required": True
                },
                "totalPages": {
                    "name": "totalPages",
                    "type": "number",
                    "label": "总页数",
                    "default": 10,
                    "required": True
                },
                "baseUrl": {
                    "name": "baseUrl",
                    "type": "string",
                    "label": "基础URL",
                    "default": "/page/",
                    "required": True
                }
            },
            "dependencies": dependencies,
            "tags": ["pagination", "navigation", "wet-boew"]
        },
        
        # 3. 下拉选择框
        {
            "name": "wet-select",
            "display_name": "下拉选择框 (WET-BOEW)",
            "category": "form",
            "description": "可访问性友好的下拉选择框",
            "icon": "🔽",
            "html_template": """
<div class="form-group">
  <label for="{{id}}">{{label}}</label>
  <select id="{{id}}" class="form-control" {{#if required}}required{{/if}}>
    {{#each options}}
    <option value="{{value}}" {{#if selected}}selected{{/if}}>{{text}}</option>
    {{/each}}
  </select>
</div>""",
            "properties": {
                "label": {
                    "name": "label",
                    "type": "string",
                    "label": "标签文字",
                    "required": True,
                    "i18n": True
                },
                "options": {
                    "name": "options",
                    "type": "string",
                    "label": "选项列表 (JSON格式)",
                    "description": "JSON数组格式，例如: [{'value':'option1','text':'选项1'},{'value':'option2','text':'选项2'}]",
                    "default": '[{"value":"option1","text":"选项1"},{"value":"option2","text":"选项2"}]',
                    "required": True,
                    "i18n": True
                },
                "required": {
                    "name": "required",
                    "type": "boolean",
                    "label": "必填字段",
                    "default": False
                }
            },
            "dependencies": dependencies,
            "tags": ["select", "form", "dropdown", "wet-boew"]
        },
        
        # 4. 复选框
        {
            "name": "wet-checkbox",
            "display_name": "复选框 (WET-BOEW)",
            "category": "form",
            "description": "可访问性友好的复选框",
            "icon": "✅",
            "html_template": """
<div class="checkbox">
  <label>
    <input type="checkbox" {{#if checked}}checked{{/if}} {{#if disabled}}disabled{{/if}}>
    {{label}}
  </label>
</div>""",
            "properties": {
                "label": {
                    "name": "label",
                    "type": "string",
                    "label": "标签文字",
                    "required": True,
                    "i18n": True
                },
                "checked": {
                    "name": "checked",
                    "type": "boolean",
                    "label": "默认选中",
                    "default": False
                },
                "disabled": {
                    "name": "disabled",
                    "type": "boolean",
                    "label": "禁用状态",
                    "default": False
                }
            },
            "dependencies": dependencies,
            "tags": ["checkbox", "form", "wet-boew"]
        },
        
        # 5. 单选按钮
        {
            "name": "wet-radio",
            "display_name": "单选按钮 (WET-BOEW)",
            "category": "form",
            "description": "可访问性友好的单选按钮组",
            "icon": "🔘",
            "html_template": """
<div class="form-group">
  <label>{{groupLabel}}</label>
  {{#each options}}
  <div class="radio">
    <label>
      <input type="radio" name="{{../groupName}}" value="{{value}}" 
             {{#if checked}}checked{{/if}} {{#if ../disabled}}disabled{{/if}}>
      {{text}}
    </label>
  </div>
  {{/each}}
</div>""",
            "properties": {
                "groupLabel": {
                    "name": "groupLabel",
                    "type": "string",
                    "label": "组标签",
                    "required": True,
                    "i18n": True
                },
                "groupName": {
                    "name": "groupName",
                    "type": "string",
                    "label": "组名称",
                    "default": "radioGroup",
                    "required": True
                },
                "options": {
                    "name": "options",
                    "type": "string",
                    "label": "选项列表 (JSON格式)",
                    "description": "JSON数组格式，例如: [{'value':'option1','text':'选项1'},{'value':'option2','text':'选项2'}]",
                    "default": '[{"value":"option1","text":"选项1","checked":true},{"value":"option2","text":"选项2"}]',
                    "required": True,
                    "i18n": True
                },
                "disabled": {
                    "name": "disabled",
                    "type": "boolean",
                    "label": "禁用状态",
                    "default": False
                }
            },
            "dependencies": dependencies,
            "tags": ["radio", "form", "wet-boew"]
        },
        
        # 6. 文本域
        {
            "name": "wet-textarea",
            "display_name": "文本域 (WET-BOEW)",
            "category": "form",
            "description": "多行文本输入框",
            "icon": "📄",
            "html_template": """
<div class="form-group">
  <label for="{{id}}">{{label}}</label>
  <textarea id="{{id}}" class="form-control" rows="{{rows}}" 
            placeholder="{{placeholder}}" {{#if required}}required{{/if}}></textarea>
</div>""",
            "properties": {
                "label": {
                    "name": "label",
                    "type": "string",
                    "label": "标签文字",
                    "required": True,
                    "i18n": True
                },
                "placeholder": {
                    "name": "placeholder",
                    "type": "string",
                    "label": "占位符",
                    "i18n": True
                },
                "rows": {
                    "name": "rows",
                    "type": "number",
                    "label": "行数",
                    "default": 4
                },
                "required": {
                    "name": "required",
                    "type": "boolean",
                    "label": "必填字段",
                    "default": False
                }
            },
            "dependencies": dependencies,
            "tags": ["textarea", "form", "wet-boew"]
        },
        
        # 7. 警告框
        {
            "name": "wet-alert",
            "display_name": "警告框 (WET-BOEW)",
            "category": "content",
            "description": "WET-BOEW标准警告框，支持不同类型",
            "icon": "⚠️",
            "html_template": """
<div class="alert alert-{{type}}" role="alert">
  {{#if heading}}<h{{headingLevel}}>{{heading}}</h{{headingLevel}}>{{/if}}
  <p>{{message}}</p>
  {{#if dismissible}}
  <button type="button" class="close" data-dismiss="alert" aria-label="关闭">
    <span aria-hidden="true">×</span>
  </button>
  {{/if}}
</div>""",
            "properties": {
                "type": {
                    "name": "type",
                    "type": "select",
                    "label": "警告类型",
                    "options": ["success", "info", "warning", "danger"],
                    "default": "info"
                },
                "heading": {
                    "name": "heading",
                    "type": "string",
                    "label": "标题",
                    "i18n": True
                },
                "headingLevel": {
                    "name": "headingLevel",
                    "type": "number",
                    "label": "标题级别",
                    "default": 4,
                    "min_value": 1,
                    "max_value": 6
                },
                "message": {
                    "name": "message",
                    "type": "string",
                    "label": "消息内容",
                    "required": True,
                    "i18n": True
                },
                "dismissible": {
                    "name": "dismissible",
                    "type": "boolean",
                    "label": "可关闭",
                    "default": False
                }
            },
            "dependencies": dependencies,
            "tags": ["alert", "notification", "wet-boew"]
        },
        
        # 8. 卡片组件
        {
            "name": "wet-card",
            "display_name": "卡片组件 (WET-BOEW)",
            "category": "content",
            "description": "WET-BOEW标准卡片，用于内容展示",
            "icon": "🃏",
            "html_template": """
<div class="panel panel-default">
  {{#if heading}}
  <div class="panel-heading">
    <h{{headingLevel}} class="panel-title">{{heading}}</h{{headingLevel}}>
  </div>
  {{/if}}
  <div class="panel-body">
    {{content}}
  </div>
  {{#if footer}}
  <div class="panel-footer">{{footer}}</div>
  {{/if}}
</div>""",
            "properties": {
                "heading": {
                    "name": "heading",
                    "type": "string",
                    "label": "卡片标题",
                    "i18n": True
                },
                "headingLevel": {
                    "name": "headingLevel",
                    "type": "number",
                    "label": "标题级别",
                    "default": 3,
                    "min_value": 1,
                    "max_value": 6
                },
                "content": {
                    "name": "content",
                    "type": "string",
                    "label": "卡片内容",
                    "required": True,
                    "i18n": True
                },
                "footer": {
                    "name": "footer",
                    "type": "string",
                    "label": "卡片页脚",
                    "i18n": True
                }
            },
            "dependencies": dependencies,
            "tags": ["card", "panel", "content", "wet-boew"]
        },
        
        # 9. 表格组件
        {
            "name": "wet-table",
            "display_name": "表格组件 (WET-BOEW)",
            "category": "content",
            "description": "可访问性友好的数据表格",
            "icon": "📊",
            "html_template": """
<table class="table table-striped">
  {{#if caption}}<caption>{{caption}}</caption>{{/if}}
  <thead>
    <tr>
      {{#each headers}}
      <th scope="col">{{this}}</th>
      {{/each}}
    </tr>
  </thead>
  <tbody>
    {{#each rows}}
    <tr>
      {{#each this}}
      <td>{{this}}</td>
      {{/each}}
    </tr>
    {{/each}}
  </tbody>
</table>""",
            "properties": {
                "caption": {
                    "name": "caption",
                    "type": "string",
                    "label": "表格标题",
                    "i18n": True
                },
                "headers": {
                    "name": "headers",
                    "type": "string",
                    "label": "表头 (JSON数组)",
                    "description": "JSON数组格式，例如: [\"列1\", \"列2\", \"列3\"]",
                    "default": '["列1", "列2", "列3"]',
                    "required": True,
                    "i18n": True
                },
                "rows": {
                    "name": "rows",
                    "type": "string",
                    "label": "表格数据 (JSON二维数组)",
                    "description": "JSON二维数组格式，例如: [[\"数据1\", \"数据2\", \"数据3\"], [\"数据4\", \"数据5\", \"数据6\"]]",
                    "default": '[[ "数据1-1", "数据1-2", "数据1-3" ], [ "数据2-1", "数据2-2", "数据2-3" ]]',
                    "required": True,
                    "i18n": True
                }
            },
            "dependencies": dependencies,
            "tags": ["table", "data", "wet-boew"]
        },
        
        # 10. 折叠面板
        {
            "name": "wet-accordion",
            "display_name": "折叠面板 (WET-BOEW)",
            "category": "content",
            "description": "WET-BOEW标准折叠面板，用于内容分组",
            "icon": "📑",
            "html_template": """
<div class="panel-group" id="accordion-{{id}}" role="tablist" aria-multiselectable="true">
  {{#each items}}
  <div class="panel panel-default">
    <div class="panel-heading" role="tab" id="heading-{{@index}}">
      <h4 class="panel-title">
        <a role="button" data-toggle="collapse" data-parent="#accordion-{{../id}}" 
           href="#collapse-{{@index}}" aria-expanded="{{#if @first}}true{{else}}false{{/if}}" 
           aria-controls="collapse-{{@index}}">
          {{title}}
        </a>
      </h4>
    </div>
    <div id="collapse-{{@index}}" class="panel-collapse collapse{{#if @first}} in{{/if}}" 
         role="tabpanel" aria-labelledby="heading-{{@index}}">
      <div class="panel-body">
        {{content}}
      </div>
    </div>
  </div>
  {{/each}}
</div>""",
            "properties": {
                "items": {
                    "name": "items",
                    "type": "string",
                    "label": "面板项目 (JSON数组)",
                    "description": "JSON数组格式，例如: [{'title':'面板1','content':'内容1'},{'title':'面板2','content':'内容2'}]",
                    "default": '[{"title":"面板1","content":"面板1内容"},{"title":"面板2","content":"面板2内容"}]',
                    "required": True,
                    "i18n": True
                }
            },
            "dependencies": dependencies,
            "tags": ["accordion", "collapse", "content", "wet-boew"]
        },
        
        # 11. 提交按钮 (与主要按钮不同)
        {
            "name": "wet-submit-button",
            "display_name": "提交按钮 (WET-BOEW)",
            "category": "form",
            "description": "表单提交专用按钮",
            "icon": "📤",
            "html_template": '<button type="submit" class="btn btn-primary">{{text}}</button>',
            "properties": {
                "text": {
                    "name": "text",
                    "type": "string",
                    "label": "按钮文字",
                    "default": "提交",
                    "required": True,
                    "i18n": True
                }
            },
            "dependencies": dependencies,
            "tags": ["button", "submit", "form", "wet-boew"]
        },
        
        # 12. 链接按钮
        {
            "name": "wet-link-button",
            "display_name": "链接按钮 (WET-BOEW)",
            "category": "basic",
            "description": "看起来像按钮的链接",
            "icon": "🔗",
            "html_template": '<a href="{{url}}" class="btn btn-{{type}}">{{text}}</a>',
            "properties": {
                "text": {
                    "name": "text",
                    "type": "string",
                    "label": "按钮文字",
                    "default": "了解更多",
                    "required": True,
                    "i18n": True
                },
                "url": {
                    "name": "url",
                    "type": "url",
                    "label": "链接地址",
                    "default": "#",
                    "required": True
                },
                "type": {
                    "name": "type",
                    "type": "select",
                    "label": "按钮类型",
                    "options": ["primary", "secondary", "success", "danger", "warning", "info", "link"],
                    "default": "primary"
                }
            },
            "dependencies": dependencies,
            "tags": ["button", "link", "wet-boew"]
        }
    ]
    
    return components

def main():
    """主函数"""
    print("🚀 批量添加WET-BOEW组件")
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
        components = create_wet_boew_components()
        print(f"📝 准备添加 {len(components)} 个WET-BOEW组件")
        
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
        
    except Exception as e:
        print(f"❌ 添加组件时出错: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()