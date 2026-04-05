# WebBot 组件系统文档

## 概述

WebBot组件系统是一个可扩展的组件模板管理系统，专门为加拿大政府WET-BOEW框架设计。系统允许客户通过配置添加新组件，无需编写代码。

## 核心特性

### 1. 可扩展组件模板
- **动态注册**: 通过API注册新组件模板
- **配置驱动**: 组件属性通过JSON配置定义
- **模板系统**: 支持HTML/CSS/JS模板，支持变量替换

### 2. WET-BOEW原生支持
- **合规检查**: 自动验证WET-BOEW标准符合性
- **可访问性**: 内置可访问性检查和修复建议
- **依赖管理**: 自动加载WET-BOEW CSS/JS依赖

### 3. 简单版本控制
- **自动版本**: 每次修改自动创建版本记录
- **历史查看**: 时间线式版本历史界面
- **一键回滚**: 支持回滚到任意历史版本

### 4. AI助手集成
- **本地LLM模式**: 数据不出境，保证政府数据安全
- **OpenAI API模式**: 使用最新AI模型能力
- **混合模式**: 敏感数据本地处理，公开内容API处理

## 组件模板定义格式

### 基本结构

```json
{
  "name": "component-unique-name",
  "display_name": "组件显示名称",
  "category": "wet_boew",
  "description": "组件描述",
  "icon": "🔘",
  "html_template": "<button class='btn btn-primary'>{{text}}</button>",
  "css_template": null,
  "js_template": null,
  "properties": {
    "text": {
      "name": "text",
      "type": "string",
      "label": "按钮文字",
      "default": "提交",
      "required": true,
      "i18n": true
    }
  },
  "dependencies": [
    {
      "type": "css",
      "url": "https://wet-boew.github.io/wet-boew/css/wet-boew.min.css",
      "version": "4.0.0",
      "required": true
    }
  ],
  "wet_boew_compliant": true,
  "accessibility_checked": true,
  "tags": ["button", "form", "wet-boew"],
  "author": "作者名称",
  "version": "1.0.0"
}
```

### 属性类型

| 类型 | 描述 | 示例 |
|------|------|------|
| `string` | 文本字符串 | `"Hello World"` |
| `number` | 数字 | `42`, `3.14` |
| `boolean` | 布尔值 | `true`, `false` |
| `select` | 下拉选择 | `["small", "medium", "large"]` |
| `color` | 颜色选择 | `"#0070c0"` |
| `url` | URL链接 | `"https://example.com"` |
| `i18n` | 多语言文本 | `{"en": "Submit", "fr": "Soumettre"}` |

### 模板变量语法

模板中使用 `{{变量名}}` 语法插入属性值：

```html
<!-- 基础变量 -->
<div class="{{className}}">{{content}}</div>

<!-- 条件判断 -->
{{#if required}}required{{/if}}

<!-- 循环 -->
{{#each options}}
  <option value="{{this}}">{{this}}</option>
{{/each}}
```

## API参考

### 组件模板管理

#### 创建组件模板
```bash
POST /api/v1/components/templates
Content-Type: application/json

{
  "name": "wet-button-primary",
  "display_name": "主要按钮 (WET-BOEW)",
  "category": "wet_boew",
  "html_template": "<button class='btn btn-primary'>{{text}}</button>",
  "properties": {
    "text": {
      "type": "string",
      "label": "按钮文字",
      "default": "提交"
    }
  }
}
```

#### 获取组件模板列表
```bash
GET /api/v1/components/templates?category=wet_boew&status=published
```

#### 获取特定组件模板
```bash
GET /api/v1/components/templates/{component_id}
```

#### 更新组件模板
```bash
PUT /api/v1/components/templates/{component_id}
```

#### 删除组件模板
```bash
DELETE /api/v1/components/templates/{component_id}?permanent=false
```

### 版本控制

#### 创建新版本
```bash
POST /api/v1/components/templates/{component_id}/versions?change_description=修复按钮样式
```

#### 获取版本历史
```bash
GET /api/v1/components/templates/{component_id}/versions
```

#### 回滚到指定版本
```bash
POST /api/v1/components/templates/{component_id}/revert?version_id=5&reason=恢复稳定版本
```

### AI配置

#### 创建AI配置
```bash
POST /api/v1/components/ai/configurations
Content-Type: application/json

{
  "name": "本地LLM演示配置",
  "mode": "local_llm",
  "local_model_path": "/models/llama-3-8b",
  "local_gpu_enabled": true,
  "enabled_features": ["content_generation", "accessibility_check"]
}
```

#### 激活AI配置
```bash
POST /api/v1/components/ai/configurations/{config_id}/activate
```

## 使用示例

### 示例1：创建WET-BOEW按钮组件

```python
import requests
import json

# API端点
BASE_URL = "http://localhost:8000/api/v1/components"

# 按钮组件定义
button_component = {
    "name": "gc-primary-button",
    "display_name": "政府主要按钮",
    "category": "wet_boew",
    "description": "加拿大政府网站标准主要按钮",
    "icon": "🔘",
    "html_template": """
        <button class="btn btn-primary" {{#if disabled}}disabled{{/if}}>
            {{text}}
        </button>
    """,
    "properties": {
        "text": {
            "type": "string",
            "label": "按钮文字",
            "default": "提交",
            "required": true,
            "i18n": true
        },
        "disabled": {
            "type": "boolean",
            "label": "禁用状态",
            "default": False
        }
    },
    "dependencies": [
        {
            "type": "css",
            "url": "https://wet-boew.github.io/wet-boew/css/wet-boew.min.css",
            "required": True
        }
    ],
    "wet_boew_compliant": True,
    "accessibility_checked": True,
    "tags": ["button", "form", "government"],
    "author": "政府数字团队",
    "version": "1.0.0"
}

# 注册组件
response = requests.post(f"{BASE_URL}/templates", 
                        json=button_component,
                        params={"user_id": "gov-team"})
print(f"组件注册: {response.status_code}")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
```

### 示例2：使用组件创建版本

```python
# 创建第一个版本
response = requests.post(
    f"{BASE_URL}/templates/gc-primary-button/versions",
    params={
        "change_description": "初始版本创建",
        "user_id": "gov-team"
    }
)
print(f"版本创建: {response.status_code}")

# 查看版本历史
response = requests.get(f"{BASE_URL}/templates/gc-primary-button/versions")
versions = response.json()
print(f"共 {len(versions)} 个版本")
```

### 示例3：配置本地LLM AI助手

```python
ai_config = {
    "name": "政府安全AI配置",
    "mode": "local_llm",
    "local_model_name": "llama-3-8b-instruct",
    "local_gpu_enabled": True,
    "enabled_features": [
        "content_generation",
        "accessibility_check", 
        "wet_boew_compliance",
        "multilingual_support"
    ]
}

response = requests.post(f"{BASE_URL}/ai/configurations", json=ai_config)
print(f"AI配置创建: {response.status_code}")
```

## 集成指南

### 与TinyMCE集成

#### 1. 加载组件库
```javascript
// 从API获取组件列表
fetch('/api/v1/components/templates?status=published')
  .then(response => response.json())
  .then(components => {
    // 创建组件工具栏
    createComponentToolbar(components);
  });

// 创建TinyMCE组件插入器
tinymce.PluginManager.add('wetboew_components', function(editor) {
  editor.ui.registry.addMenuButton('wetboew', {
    icon: 'template',
    tooltip: '插入WET-BOEW组件',
    fetch: function(callback) {
      // 动态获取组件列表
      fetchComponentList().then(components => {
        const items = components.map(comp => ({
          type: 'menuitem',
          text: comp.display_name,
          icon: comp.icon,
          onAction: () => insertComponent(editor, comp)
        }));
        callback(items);
      });
    }
  });
});
```

#### 2. 组件插入和配置
```javascript
function insertComponent(editor, component) {
  // 弹出配置对话框
  openConfigDialog(component.properties, (configValues) => {
    // 渲染模板
    let html = component.html_template;
    Object.keys(configValues).forEach(key => {
      html = html.replace(`{{${key}}}`, configValues[key]);
    });
    
    // 插入到编辑器
    editor.insertContent(html);
    
    // 加载依赖
    loadComponentDependencies(component.dependencies);
  });
}
```

### 与现有页面系统集成

#### 1. 存储组件实例
当用户在页面中使用组件时，创建组件实例记录：

```python
# 创建组件实例
instance_data = {
    "page_id": "canadasite-en-home",
    "template_id": "gc-primary-button",
    "instance_name": "submit_button",
    "configuration": {
        "text": "提交申请",
        "disabled": False
    },
    "position": {
        "row": 1,
        "column": 2
    }
}

response = requests.post(f"{BASE_URL}/instances", json=instance_data)
```

#### 2. 渲染页面时加载组件
```python
# 获取页面所有组件实例
def get_page_components(page_id):
    response = requests.get(f"{BASE_URL}/instances?page_id={page_id}")
    instances = response.json()
    
    # 获取每个组件的模板和配置
    components = []
    for instance in instances:
        template = get_component_template(instance['template_id'])
        rendered = render_component(template, instance['configuration'])
        components.append({
            'instance': instance,
            'rendered': rendered
        })
    
    return components
```

## 开发指南

### 创建新组件模板

#### 步骤1：设计组件
1. **确定用途**: 组件的功能和目标用户
2. **设计HTML结构**: 符合WET-BOEW标准的HTML
3. **定义属性**: 用户可配置的参数
4. **测试可访问性**: 确保符合WCAG标准

#### 步骤2：创建模板定义
```json
{
  "name": "gc-alert-warning",
  "display_name": "警告提示框",
  "category": "wet_boew",
  "html_template": """
    <div class="alert alert-warning" role="alert">
      <h4 class="alert-heading">{{title}}</h4>
      <p>{{message}}</p>
    </div>
  """,
  "properties": {
    "title": {
      "type": "string",
      "label": "标题",
      "default": "警告",
      "i18n": true
    },
    "message": {
      "type": "string", 
      "label": "消息内容",
      "required": true,
      "i18n": true
    }
  }
}
```

#### 步骤3：注册组件
```bash
curl -X POST http://localhost:8000/api/v1/components/templates \
  -H "Content-Type: application/json" \
  -d @gc-alert-warning.json
```

#### 步骤4：测试组件
1. 通过API获取组件验证
2. 在编辑器中测试插入和配置
3. 验证可访问性和WET-BOEW合规性

### 扩展组件系统

#### 添加新属性类型
1. 在 `models_components.py` 中扩展 `PropertyType` 枚举
2. 更新属性验证逻辑
3. 添加对应的前端表单控件

#### 添加新AI功能
1. 在AI配置中添加新功能标识
2. 实现对应的AI服务端点
3. 更新前端AI助手界面

## 最佳实践

### 组件设计
1. **保持简单**: 每个组件专注于单一功能
2. **符合标准**: 严格遵守WET-BOEW和WCAG标准
3. **文档完整**: 提供清晰的属性说明和使用示例
4. **测试充分**: 跨浏览器和设备测试

### 版本管理
1. **描述清晰**: 版本变更描述具体明确
2. **定期备份**: 重要版本创建备份点
3. **审计跟踪**: 记录所有修改操作

### 性能优化
1. **依赖合并**: 合并相同依赖减少HTTP请求
2. **模板缓存**: 缓存渲染结果提高性能
3. **懒加载**: 非关键组件延迟加载

## 故障排除

### 常见问题

#### 1. 组件注册失败
- **检查**: 组件名称是否唯一
- **检查**: 属性定义格式是否正确
- **检查**: 模板语法是否正确

#### 2. 模板渲染错误
- **检查**: 变量名是否与属性匹配
- **检查**: 条件判断语法是否正确
- **检查**: 特殊字符是否转义

#### 3. AI功能不可用
- **检查**: AI配置是否激活
- **检查**: 本地模型路径是否正确
- **检查**: API密钥是否有效

### 调试方法

#### API调试
```bash
# 启用详细日志
curl -v http://localhost:8000/api/v1/components/templates

# 查看错误日志
tail -f /tmp/webbot_restart.log
```

#### 数据库调试
```python
# 直接查询数据库
import sqlite3
conn = sqlite3.connect("/path/to/filebot.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM component_templates")
print(cursor.fetchall())
```

## 部署指南

### 生产环境部署

#### 1. 数据库准备
```bash
# 备份现有数据库
cp filebot.db filebot.db.backup.$(date +%s)

# 运行迁移脚本
python3 app/db_migration_components.py
```

#### 2. 服务配置
```bash
# 创建服务配置文件
cat > /etc/systemd/system/webbot.service << EOF
[Unit]
Description=WebBot Component System
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/webbot/app
Environment="PATH=/opt/webbot/app/venv/bin"
ExecStart=/opt/webbot/app/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 启用服务
systemctl daemon-reload
systemctl enable webbot
systemctl start webbot
```

#### 3. 反向代理配置 (Nginx)
```nginx
server {
    listen 80;
    server_name webbot.example.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # 静态文件缓存
    location /static {
        alias /opt/webbot/frontend;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 监控和日志

#### 健康检查
```bash
# 定期健康检查
curl -s http://webbot.example.com/health | grep -q "healthy" || echo "服务异常"
```

#### 日志监控
```bash
# 查看错误日志
tail -f /var/log/webbot/error.log

# 监控API访问
tail -f /var/log/nginx/access.log | grep "/api/v1/components"
```

## 附录

### A. WET-BOEW资源
- [官方网站](https://wet-boew.github.io/wet-boew/)
- [设计规范](https://design.canada.ca/)
- [可访问性指南](https://www.canada.ca/en/treasury-board-secretariat/services/government-communications/canada-content-style-guide.html)

### B. 组件示例库
示例组件存储在 `components/examples/` 目录中，包括：
- `gc-button-primary.json` - 主要按钮
- `gc-input-text.json` - 文本输入框
- `gc-alert-warning.json` - 警告提示框
- `gc-navigation-bar.json` - 导航栏
- `gc-footer-standard.json` - 标准页脚

### C. API速查表

| 端点 | 方法 | 描述 |
|------|------|------|
| `/components/templates` | GET | 获取组件列表 |
| `/components/templates` | POST | 创建新组件 |
| `/components/templates/{id}` | GET | 获取组件详情 |
| `/components/templates/{id}` | PUT | 更新组件 |
| `/components/templates/{id}/versions` | POST | 创建新版本 |
| `/components/templates/{id}/revert` | POST | 回滚版本 |
| `/components/ai/configurations` | POST | 创建AI配置 |
| `/components/health` | GET | 系统健康检查 |

---

**文档版本**: 1.0.0  
**最后更新**: 2026-03-25  
**适用版本**: WebBot 1.0.0+