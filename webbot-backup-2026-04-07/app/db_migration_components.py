#!/usr/bin/env python3
"""
WebBot组件系统数据库迁移脚本
添加组件模板、版本控制、AI配置相关表
"""

import sqlite3
import sys
import os
from datetime import datetime

def get_db_connection(db_path=None):
    """获取数据库连接"""
    if db_path is None:
        # 默认数据库路径（与FileBot共享）
        db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"❌ 数据库连接失败: {e}")
        sys.exit(1)

def check_table_exists(conn, table_name):
    """检查表是否存在"""
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None

def create_component_tables(conn):
    """创建组件系统相关表"""
    
    print("🔧 开始创建组件系统表...")
    
    cursor = conn.cursor()
    
    # 1. 组件模板表
    if not check_table_exists(conn, "component_templates"):
        print("📋 创建 component_templates 表...")
        cursor.execute("""
            CREATE TABLE component_templates (
                id TEXT PRIMARY KEY,  -- 组件唯一ID
                name TEXT NOT NULL UNIQUE,  -- 组件唯一名称
                display_name TEXT NOT NULL,  -- 显示名称
                category TEXT NOT NULL,  -- 组件分类
                description TEXT,  -- 组件描述
                icon TEXT,  -- 图标标识
                
                -- 模板内容
                html_template TEXT NOT NULL,  -- HTML模板
                css_template TEXT,  -- CSS模板
                js_template TEXT,  -- JavaScript模板
                
                -- 属性定义 (JSON格式)
                properties_json TEXT NOT NULL DEFAULT '{}',
                
                -- 依赖 (JSON格式)
                dependencies_json TEXT NOT NULL DEFAULT '[]',
                
                -- WET-BOEW特定
                wet_boew_version TEXT,
                wet_boew_compliant BOOLEAN DEFAULT 0,
                accessibility_checked BOOLEAN DEFAULT 0,
                
                -- 元数据
                tags_json TEXT NOT NULL DEFAULT '[]',
                author TEXT,
                version TEXT DEFAULT '1.0.0',
                
                -- 状态和管理
                status TEXT DEFAULT 'draft',
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usage_count INTEGER DEFAULT 0,
                
                -- 约束
                CHECK (category IN ('basic', 'form', 'navigation', 'content', 'layout', 'wet_boew', 'custom')),
                CHECK (status IN ('draft', 'published', 'deprecated'))
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX idx_component_category ON component_templates(category)")
        cursor.execute("CREATE INDEX idx_component_status ON component_templates(status)")
        cursor.execute("CREATE INDEX idx_component_created ON component_templates(created_at)")
        cursor.execute("CREATE INDEX idx_component_wet_boew ON component_templates(wet_boew_compliant)")
        print("✅ component_templates 表创建完成")
    
    # 2. 组件版本表 (简单历史记录)
    if not check_table_exists(conn, "component_versions"):
        print("📋 创建 component_versions 表...")
        cursor.execute("""
            CREATE TABLE component_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                component_id TEXT NOT NULL REFERENCES component_templates(id),
                version_number INTEGER NOT NULL,  -- 版本号
                content_json TEXT NOT NULL,  -- 版本内容 (完整配置JSON)
                change_description TEXT,  -- 变更描述
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- 每个组件每个版本号唯一
                UNIQUE(component_id, version_number)
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX idx_version_component ON component_versions(component_id)")
        cursor.execute("CREATE INDEX idx_version_number ON component_versions(version_number)")
        cursor.execute("CREATE INDEX idx_version_created ON component_versions(created_at)")
        print("✅ component_versions 表创建完成")
    
    # 3. 组件实例表 (页面中使用的组件)
    if not check_table_exists(conn, "component_instances"):
        print("📋 创建 component_instances 表...")
        cursor.execute("""
            CREATE TABLE component_instances (
                id TEXT PRIMARY KEY,  -- 实例唯一ID
                page_id TEXT NOT NULL,  -- 所属页面ID
                template_id TEXT NOT NULL REFERENCES component_templates(id),
                instance_name TEXT NOT NULL,  -- 实例名称
                configuration_json TEXT NOT NULL DEFAULT '{}',  -- 配置值 (JSON)
                position_json TEXT,  -- 位置信息 (JSON)
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- 同一页面内实例名称唯一
                UNIQUE(page_id, instance_name)
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX idx_instance_page ON component_instances(page_id)")
        cursor.execute("CREATE INDEX idx_instance_template ON component_instances(template_id)")
        cursor.execute("CREATE INDEX idx_instance_created ON component_instances(created_at)")
        print("✅ component_instances 表创建完成")
    
    # 4. AI配置表
    if not check_table_exists(conn, "ai_configurations"):
        print("📋 创建 ai_configurations 表...")
        cursor.execute("""
            CREATE TABLE ai_configurations (
                id TEXT PRIMARY KEY,  -- 配置ID
                name TEXT NOT NULL,  -- 配置名称
                mode TEXT NOT NULL,  -- AI模式
                
                -- 本地LLM配置
                local_model_path TEXT,
                local_model_name TEXT,
                local_gpu_enabled BOOLEAN DEFAULT 0,
                
                -- OpenAI配置
                openai_api_key TEXT,
                openai_model TEXT DEFAULT 'gpt-4',
                
                -- 混合模式配置
                hybrid_rules_json TEXT DEFAULT '{}',
                
                -- 功能配置
                enabled_features_json TEXT DEFAULT '[]',
                
                -- 状态
                is_active BOOLEAN DEFAULT 0,  -- 是否激活
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- 约束
                CHECK (mode IN ('local_llm', 'openai_api', 'hybrid'))
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX idx_ai_mode ON ai_configurations(mode)")
        cursor.execute("CREATE INDEX idx_ai_active ON ai_configurations(is_active)")
        cursor.execute("CREATE INDEX idx_ai_created ON ai_configurations(created_at)")
        print("✅ ai_configurations 表创建完成")
    
    # 5. 当前版本指针表 (简化版本控制)
    if not check_table_exists(conn, "component_current_versions"):
        print("📋 创建 component_current_versions 表...")
        cursor.execute("""
            CREATE TABLE component_current_versions (
                component_id TEXT PRIMARY KEY REFERENCES component_templates(id),
                current_version_id INTEGER NOT NULL REFERENCES component_versions(id),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ component_current_versions 表创建完成")
    
    # 6. 创建示例数据 (可选)
    create_sample_data(cursor)
    
    conn.commit()
    print("🎉 组件系统表创建完成！")

def create_sample_data(cursor):
    """创建示例组件数据"""
    print("📝 创建示例组件数据...")
    
    from datetime import datetime
    import json
    import uuid
    
    # 示例1: WET-BOEW主要按钮
    button_id = "wet-button-primary"
    button_properties = {
        "text": {
            "name": "text",
            "type": "string",
            "label": "按钮文字",
            "default": "提交",
            "required": True,
            "i18n": True
        },
        "size": {
            "name": "size",
            "type": "select",
            "label": "尺寸",
            "options": ["small", "medium", "large"],
            "default": "medium"
        },
        "disabled": {
            "name": "disabled",
            "type": "boolean",
            "label": "禁用状态",
            "default": False
        }
    }
    
    button_dependencies = [
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
    
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO component_templates 
            (id, name, display_name, category, description, icon, html_template, 
             properties_json, dependencies_json, wet_boew_compliant, accessibility_checked,
             tags_json, author, version, status, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            button_id,
            button_id,
            "主要按钮 (WET-BOEW)",
            "wet_boew",
            "加拿大政府标准主要按钮，符合WET-BOEW可访问性要求",
            "🔘",
            '<button class="btn btn-primary" data-wet-boew="button" {{#if disabled}}disabled{{/if}}>{{text}}</button>',
            json.dumps(button_properties, ensure_ascii=False),
            json.dumps(button_dependencies, ensure_ascii=False),
            1,  # wet_boew_compliant
            1,  # accessibility_checked
            json.dumps(["button", "form", "wet-boew"], ensure_ascii=False),
            "系统",
            "1.0.0",
            "published",
            "system"
        ))
        
        # 示例2: 文本输入框
        input_id = "wet-input-text"
        input_properties = {
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
            "required": {
                "name": "required",
                "type": "boolean",
                "label": "必填字段",
                "default": False
            }
        }
        
        cursor.execute("""
            INSERT OR IGNORE INTO component_templates 
            (id, name, display_name, category, description, icon, html_template, 
             properties_json, dependencies_json, wet_boew_compliant, accessibility_checked,
             tags_json, author, version, status, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            input_id,
            input_id,
            "文本输入框 (WET-BOEW)",
            "form",
            "可访问性友好的文本输入框，符合WCAG标准",
            "📝",
            '''
            <div class="form-group">
                <label for="{{id}}">{{label}}</label>
                <input type="text" id="{{id}}" class="form-control" 
                       placeholder="{{placeholder}}" 
                       {{#if required}}required{{/if}}>
            </div>
            ''',
            json.dumps(input_properties, ensure_ascii=False),
            json.dumps(button_dependencies, ensure_ascii=False),  # 相同依赖
            1,  # wet_boew_compliant
            1,  # accessibility_checked
            json.dumps(["input", "form", "wet-boew"], ensure_ascii=False),
            "系统",
            "1.0.0",
            "published",
            "system"
        ))
        
        print("✅ 示例组件数据创建完成")
        
    except Exception as e:
        print(f"⚠️ 创建示例数据时出错: {e}")

def main():
    """主函数"""
    print("🚀 WebBot组件系统数据库迁移工具")
    print("=" * 50)
    
    # 数据库路径
    db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        print("请确保FileBot数据库已创建")
        sys.exit(1)
    
    print(f"📁 数据库文件: {db_path}")
    print(f"📏 文件大小: {os.path.getsize(db_path) / 1024 / 1024:.2f} MB")
    
    # 备份数据库
    backup_path = f"{db_path}.backup.{int(datetime.now().timestamp())}"
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"📦 数据库已备份到: {backup_path}")
    except Exception as e:
        print(f"⚠️ 备份失败: {e}")
        user_input = input("继续执行？(y/N): ")
        if user_input.lower() != 'y':
            print("退出迁移")
            sys.exit(0)
    
    # 连接到数据库
    conn = get_db_connection(db_path)
    
    try:
        # 创建组件系统表
        create_component_tables(conn)
        
        # 验证表创建
        tables = ["component_templates", "component_versions", "component_instances", 
                  "ai_configurations", "component_current_versions"]
        
        print("\n🔍 表创建验证:")
        for table in tables:
            if check_table_exists(conn, table):
                print(f"✅ {table} 表存在")
            else:
                print(f"❌ {table} 表不存在")
        
        print("\n🎯 迁移完成！")
        print("下一步:")
        print("1. 重启WebBot服务以加载新模型")
        print("2. 访问 /api/v1/components/templates 验证API")
        print("3. 开始开发组件管理界面")
        
    except Exception as e:
        print(f"❌ 迁移过程中出错: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()