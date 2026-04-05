# WebBot - AI增强的网站内容管理系统

基于FileBot基础设施，提供AI辅助创页、修正、删页、审查功能。

## 🚀 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 启动服务器
```bash
python main.py
```

或者直接运行：
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 访问API
- API地址: http://localhost:8000
- 交互式文档: http://localhost:8000/docs
- ReDoc文档: http://localhost:8000/redoc

## 📋 核心功能

### 1. 页面管理 (CRUD)
- `POST /api/v1/pages` - 创建新页面
- `GET /api/v1/pages` - 获取页面列表
- `GET /api/v1/pages/{page_id}` - 获取单个页面
- `PUT /api/v1/pages/{page_id}` - 更新页面
- `DELETE /api/v1/pages/{page_id}` - 删除页面

### 2. AI辅助功能

#### 🤖 AI任务系统
- `POST /api/v1/ai/create-task` - 创建AI任务
- `GET /api/v1/ai/tasks` - 获取AI任务列表
- `GET /api/v1/ai/tasks/{task_id}` - 获取AI任务详情

#### 🎯 直接AI处理
- `POST /api/v1/ai/create-page` - AI辅助创建页面
- `POST /api/v1/ai/optimize-page` - AI辅助优化页面内容
- `POST /api/v1/ai/review-page` - AI辅助审查页面合规性
- `POST /api/v1/ai/suggest-deletion` - AI辅助删除建议

## 🗄️ 数据库

WebBot使用FileBot的SQLite数据库 (`filebot/backend/filebot.db`)，自动创建以下表：

### `webbot_page` 表
- `id` - 页面ID (基于标题生成)
- `title` - 页面标题
- `content` - 页面内容 (HTML)
- `language` - 语言代码 (en/fr)
- `parent_id` - 父页面ID (支持嵌套结构)
- `other_lang_page_id` - 其他语言对应页面ID
- `status` - 状态 (draft/published/archived)
- `metadata` - JSON格式的元数据
- `created_at`, `last_modified`, `last_published` - 时间戳

### `webbot_tasks` 表
- `id` - 任务ID
- `task_type` - 任务类型 (create_page/optimize_page/review_page/delete_page)
- `page_id` - 关联页面ID
- `description` - 任务描述
- `status` - 状态 (pending/processing/completed/failed)
- `ai_model` - 使用的AI模型
- `prompt` - AI提示词
- `result` - AI处理结果
- `error_message` - 错误信息
- 时间戳字段

## 🔧 技术架构

- **后端框架**: FastAPI (Python 3.12+)
- **数据库**: SQLite (集成到FileBot数据库)
- **AI集成**: 模拟AI服务 + 可扩展的真实AI集成
- **API风格**: RESTful + 异步支持
- **部署**: 可独立运行或集成到FileBot系统

## 🎨 前端集成建议

WebBot设计为API优先，前端可通过以下方式集成：

1. **独立管理界面**: 基于React/Vue的独立管理后台
2. **集成到FileBot**: 作为FileBot的新模块
3. **命令行工具**: 基于API的命令行客户端

## 🤖 AI功能详情

### 创页功能
根据描述生成完整的HTML页面，包括：
- 语义化HTML结构
- Canada.ca合规的样式
- 基本的页面布局
- 可访问性优化

### 修正功能
优化现有页面内容：
- 语法和拼写修正
- 结构优化
- 可读性改进
- 合规性检查

### 审查功能
检查页面合规性：
- Canada.ca标准检查
- 可访问性审计
- 内容质量评估
- 安全建议

### 删除建议
分析页面并提供删除建议：
- 使用情况分析
- 相关性评估
- 替代方案建议
- 归档选项

## 📊 后续开发

### 短期计划
1. 真实AI集成 (OpenAI/Ollama)
2. 文件上传和处理集成
3. 版本控制和历史记录
4. 多用户权限管理

### 长期计划
1. 工作流自动化
2. 高级分析仪表板
3. 多站点管理
4. 智能内容推荐

## 📝 使用示例

### 创建页面
```bash
curl -X POST "http://localhost:8000/api/v1/pages" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "About Our Services",
    "content": "Initial content about our services.",
    "language": "en",
    "status": "draft"
  }'
```

### AI创建页面
```bash
curl -X POST "http://localhost:8000/api/v1/ai/create-page" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create_page",
    "content": "Create a page about environmental sustainability initiatives"
  }'
```

## 🛠️ 开发说明

项目结构：
```
webbot/app/
├── main.py              # 主应用入口
├── models.py           # 数据模型
├── routes/
│   ├── __init__.py
│   ├── pages.py       # 页面管理路由
│   └── ai.py          # AI功能路由
├── requirements.txt    # 依赖列表
└── README.md          # 本文档
```

## 📄 许可证

基于FileBot项目的许可证。