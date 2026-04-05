# WebBot 简化技术方案 (基于用户明确偏好)

## 🎯 技术选择确认

基于用户2026-03-21 06:31 EDT的明确技术偏好：

### ✅ 确认的技术栈
1. **前端**: 纯粹的HTML文本 (原生HTML/CSS/JavaScript)
2. **后端**: FastAPI (文本编辑功能)
3. **数据库**: 与FileBot共享 (SQLite)
4. **部署**: 前端云服务器 + 后端内部网

### 🔄 方案调整说明

**原假设方案**:
- 前端: React + TypeScript + Vite (现代化SPA)
- 后端: FastAPI + 独立数据库  
- 部署: 一体化或微服务架构

**新确认方案**:
- 前端: 原生HTML/CSS/JS (轻量级，可能服务器端渲染)
- 后端: FastAPI (共享FileBot技术栈)
- 数据库: 直接共享FileBot的SQLite数据库
- 部署: 前后端分离，前端公开，后端内部

## 🏗️ 简化架构设计

### 整体架构
```
外部用户访问 (浏览器)
         ↓ HTTPS
[云服务器: WebBot前端]
├── 静态HTML/CSS/JS文件
├── 轻量级JavaScript交互
└── 通过内部API调用后端
         ↓ 内部网络/API
[内部网服务器: WebBot后端]
├── FastAPI应用
├── 业务逻辑处理
└── 数据库访问
         ↓ 直接文件访问
[共享SQLite数据库文件]
├── FileBot数据表
├── WebBot新增数据表
└── 共享用户/组织数据
```

### 前端架构选择

#### 方案对比:
| 方案 | 技术栈 | 优点 | 缺点 | 适合场景 |
|------|--------|------|------|----------|
| **纯静态HTML** | HTML + CSS + 原生JS | 最简单，性能最好 | 交互有限，代码组织差 | 简单展示型页面 |
| **HTML + htmx** | HTML + htmx库 | 增强交互，保持简单 | 需要学习新概念 | 增强型交互应用 |
| **HTML + Alpine.js** | HTML + Alpine.js | 响应式，组件化 | 轻量级框架 | 需要响应式交互 |
| **服务器端渲染** | FastAPI + Jinja2 | 服务端渲染，SEO友好 | 前后端耦合 | 内容型网站 |

#### 推荐方案: **HTML + htmx + 轻量级CSS框架**
- **HTML**: 语义化标记，良好的可访问性
- **CSS**: Tailwind CSS或简单自定义CSS
- **JavaScript**: 
  - htmx (增强HTML交互)
  - 原生ES6模块 (组织代码)
  - 可选Alpine.js (简单响应式)

#### 前端技术栈:
```html
<!-- 示例: 使用htmx增强的HTML -->
<div hx-get="/api/pages" hx-trigger="load">
  <!-- 内容由htmx动态加载 -->
</div>

<button hx-post="/api/pages" hx-target="#result">
  创建页面
</button>
```

### 后端架构设计

#### FastAPI应用结构:
```
webbot-backend/
├── app/
│   ├── main.py              # FastAPI应用入口
│   ├── api/                 # API路由
│   │   ├── v1/              # API版本1
│   │   │   ├── pages.py     # 页面管理API
│   │   │   ├── templates.py # 模板管理API  
│   │   │   └── auth.py      # 认证API (集成FileBot)
│   ├── models/              # 数据模型
│   │   ├── page.py          # 页面模型
│   │   ├── template.py      # 模板模型
│   │   └── __init__.py
│   ├── schemas/             # Pydantic模式
│   ├── services/            # 业务服务
│   │   ├── page_service.py  # 页面服务
│   │   └── auth_service.py  # 认证服务
│   ├── database.py          # 数据库配置
│   └── config.py            # 应用配置
├── tests/                   # 测试
├── requirements.txt         # Python依赖
└── Dockerfile              # Docker配置
```

#### 数据库共享策略:
1. **直接文件访问**:
   ```python
   # 使用FileBot的数据库文件
   DATABASE_URL = "sqlite:////home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
   
   # SQLAlchemy配置
   engine = create_engine(DATABASE_URL)
   SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
   ```

2. **数据表设计**:
   - **复用FileBot表**: users, organizations, files等
   - **新增WebBot表**: 
     ```sql
     -- 页面表
     CREATE TABLE pages (
         id INTEGER PRIMARY KEY,
         title TEXT NOT NULL,
         slug TEXT UNIQUE,
         content TEXT,  -- JSON格式的页面内容
         status TEXT DEFAULT 'draft',
         author_id INTEGER REFERENCES users(id),
         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
         updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
     );
     
     -- 模板表
     CREATE TABLE templates (
         id INTEGER PRIMARY KEY,
         name TEXT NOT NULL,
         content TEXT,  -- JSON格式的模板内容
         category TEXT,
         is_public BOOLEAN DEFAULT FALSE,
         author_id INTEGER REFERENCES users(id)
     );
     ```

3. **数据访问模式**:
   - 只读访问FileBot用户数据
   - 独立WebBot业务表
   - 通过外键关联共享数据

### 部署架构

#### 生产环境部署:
```
互联网用户
    ↓ HTTPS (443)
[云服务器: Nginx]
├── 静态文件服务 (HTML/CSS/JS)
└── API反向代理 (内部后端)
    ↓ 内部网络 (VPN/专线)
[内部网服务器: FastAPI]
├── Gunicorn + Uvicorn
└── 数据库访问 (共享SQLite)
```

#### 开发环境部署:
```yaml
# docker-compose.yml
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "5173:80"  # 静态文件服务
    
  backend:
    build: ./backend
    ports:
      - "8002:8000"  # FastAPI
    volumes:
      - ./filebot/backend/filebot.db:/app/filebot.db  # 共享数据库
    environment:
      - DATABASE_URL=sqlite:////app/filebot.db
```

## 🔧 核心功能实现方案

### 1. 页面编辑器实现

#### 前端编辑器选项:
1. **简单文本编辑器**:
   - `<textarea>` + 基本格式化
   - 适合简单内容编辑

2. **轻量级富文本编辑器**:
   - TipTap (轻量级，可定制)
   - Quill.js (中等重量)
   - 基于contenteditable的自定义编辑器

3. **代码编辑器**:
   - CodeMirror 或 Monaco Editor
   - 适合开发者编辑HTML/CSS/JS

#### 推荐: **TipTap富文本编辑器**
- 轻量级 (仅30KB gzipped)
- 无框架依赖，纯JavaScript
- 可扩展，支持自定义节点
- 输出为JSON，便于存储和处理

#### 编辑器集成:
```html
<!-- HTML结构 -->
<div id="editor"></div>

<!-- JavaScript -->
<script type="module">
  import { Editor } from 'tiptap';
  
  const editor = new Editor({
    element: document.querySelector('#editor'),
    content: '<p>初始内容</p>',
    onUpdate: ({ getJSON }) => {
      // 保存JSON格式内容
      const content = getJSON();
      // 通过htmx或fetch发送到后端
    }
  });
</script>
```

### 2. 用户认证集成

#### 与FileBot认证集成:
1. **方案A: 直接数据库验证**
   ```python
   # 直接查询FileBot用户表
   from sqlalchemy.orm import Session
   
   def authenticate_user(db: Session, username: str, password: str):
       user = db.query(FileBotUser).filter(FileBotUser.username == username).first()
       if not user:
           return False
       # 验证密码 (假设FileBot使用相同的哈希算法)
       return verify_password(password, user.hashed_password)
   ```

2. **方案B: 通过FileBot API验证**
   ```python
   # 调用FileBot认证API
   import requests
   
   def authenticate_via_filebot(username: str, password: str):
       response = requests.post(
           "http://filebot-backend:8001/api/v1/auth/login",
           json={"username": username, "password": password}
       )
       return response.status_code == 200
   ```

3. **方案C: 共享JWT令牌**
   - FileBot颁发JWT令牌
   - WebBot验证相同的JWT令牌
   - 需要共享JWT密钥

#### 推荐: **方案C (共享JWT令牌)**
- 松耦合，通过标准JWT集成
- 用户单点登录体验
- 无需直接访问用户密码

### 3. 文件管理集成

#### FileBot作为文件服务:
1. **文件上传流程**:
   ```javascript
   // 前端通过FormData上传
   const formData = new FormData();
   formData.append('file', fileInput.files[0]);
   
   // 调用WebBot后端，由后端转发到FileBot
   fetch('/api/v1/files/upload', {
     method: 'POST',
     body: formData
   });
   ```

2. **后端文件处理**:
   ```python
   # WebBot后端接收文件，转发到FileBot
   @app.post("/api/v1/files/upload")
   async def upload_file(file: UploadFile):
       # 读取文件内容
       contents = await file.read()
       
       # 调用FileBot API
       filebot_response = requests.post(
           "http://filebot-backend:8001/api/v1/files/upload",
           files={"file": (file.filename, contents)},
           headers={"Authorization": f"Bearer {current_user_token}"}
       )
       
       # 返回FileBot的文件信息
       return filebot_response.json()
   ```

3. **文件引用**:
   - 在页面内容中存储FileBot文件ID
   - 前端通过FileBot API获取文件URL
   - 实现文件预览和下载

### 4. 版本控制系统

#### 简单版本控制设计:
1. **版本存储**:
   ```sql
   CREATE TABLE page_versions (
       id INTEGER PRIMARY KEY,
       page_id INTEGER REFERENCES pages(id),
       version_number INTEGER,
       content_snapshot TEXT,  -- 页面内容JSON
       created_by INTEGER REFERENCES users(id),
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

2. **版本操作**:
   - 自动保存: 每次编辑自动创建版本
   - 手动保存: 用户明确保存版本
   - 版本标签: 给重要版本添加标签

3. **版本恢复**:
   ```python
   @app.post("/api/v1/pages/{page_id}/restore/{version_id}")
   def restore_version(page_id: int, version_id: int):
       version = db.query(PageVersion).filter(PageVersion.id == version_id).first()
       page = db.query(Page).filter(Page.id == page_id).first()
       
       # 恢复内容
       page.content = version.content_snapshot
       db.commit()
       
       # 创建新版本记录恢复操作
       new_version = PageVersion(
           page_id=page_id,
           version_number=get_next_version(page_id),
           content_snapshot=page.content,
           created_by=current_user.id
       )
       db.add(new_version)
       db.commit()
   ```

## 🚀 开发路线图 (简化版)

### 阶段1: 基础MVP (3-4周)
**目标**: 实现基本页面创建、编辑、发布

**第1周**: 项目初始化
- [ ] 前端: 基础HTML结构，简单CSS
- [ ] 后端: FastAPI项目搭建，数据库配置
- [ ] 集成: 与FileBot用户认证集成

**第2周**: 核心编辑器
- [ ] 前端: 集成TipTap富文本编辑器
- [ ] 后端: 页面CRUD API实现
- [ ] 功能: 基本页面保存和加载

**第3周**: 发布功能
- [ ] 前端: 发布管理界面
- [ ] 后端: 页面状态管理API
- [ ] 集成: 文件上传到FileBot

**第4周**: 测试优化
- [ ] 测试: 端到端测试
- [ ] 部署: 开发环境部署
- [ ] 文档: 用户手册和API文档

### 阶段2: 协作功能 (3-4周)
**目标**: 版本控制、协作编辑、模板系统

**第5周**: 版本控制
- [ ] 前端: 版本历史界面
- [ ] 后端: 版本控制系统
- [ ] 功能: 版本对比和恢复

**第6周**: 协作功能
- [ ] 前端: 协作者管理界面
- [ ] 后端: 权限控制系统
- [ ] 功能: 简单的实时协作提示

**第7周**: 模板系统
- [ ] 前端: 模板选择和编辑
- [ ] 后端: 模板管理API
- [ ] 功能: 模板应用和自定义

**第8周**: 优化完善
- [ ] 性能: 前端性能优化
- [ ] 安全: 安全增强
- [ ] 部署: 生产环境准备

### 阶段3: 高级功能 (4-6周)
**目标**: 完整发布流程、SEO工具、第三方集成

**第9-10周**: 发布管道
- [ ] 多环境发布管理
- [ ] 发布审批流程
- [ ] CDN和缓存集成

**第11-12周**: SEO与优化
- [ ] SEO分析工具
- [ ] 页面性能优化
- [ ] 移动端适配

**第13-14周**: 第三方集成
- [ ] 社交媒体集成
- [ ] 分析工具集成
- [ ] 插件系统基础

## 📊 技术风险评估

### 优势分析
1. **技术简单**: 轻量级技术栈，学习成本低
2. **快速开发**: 简化架构，开发速度快
3. **部署简单**: 静态前端+API后端，部署简单
4. **成本控制**: 无复杂框架许可费用
5. **安全性**: 后端内部网，安全风险低

### 挑战与风险
1. **前端交互复杂度限制**
   - 风险: 复杂交互难以实现
   - 缓解: 渐进增强，必要部分使用轻量级JS

2. **数据库共享冲突**
   - 风险: 并发访问导致数据损坏
   - 缓解: 合理的锁机制，读写分离考虑

3. **性能扩展性**
   - 风险: SQLite在大数据量时性能下降
   - 缓解: 数据库优化，未来迁移到PostgreSQL计划

4. **部署网络复杂性**
   - 风险: 内外网通信配置复杂
   - 缓解: 清晰的网络架构，VPN/专线配置

### 技术决策点
1. **前端交互库选择**: htmx vs Alpine.js vs 纯原生
2. **编辑器选择**: TipTap vs 自定义编辑器
3. **认证集成方式**: 共享JWT vs 直接数据库验证
4. **数据库访问模式**: 直接文件访问 vs API包装

## 📝 实施建议

### 建议采用的技术栈:
1. **前端**: HTML5 + Tailwind CSS + htmx + 原生ES6模块
2. **编辑器**: TipTap (轻量级富文本编辑器)
3. **后端**: FastAPI + SQLAlchemy + Pydantic
4. **数据库**: 共享FileBot SQLite数据库
5. **部署**: Nginx静态服务 + FastAPI后端 + 内部网络

### 开发流程建议:
1. **小步快跑**: 快速迭代，每2周可演示版本
2. **用户反馈**: 早期用户测试，快速调整
3. **技术债务**: 定期重构，保持代码质量
4. **文档驱动**: API文档先行，前后端协同开发

### 质量保证:
1. **测试策略**: 
   - 单元测试 (pytest)
   - API测试 (FastAPI TestClient)
   - 端到端测试 (Playwright)
2. **代码质量**: 
   - 代码审查
   - 静态分析 (flake8, mypy)
   - 自动化格式化 (black, isort)
3. **安全考虑**:
   - 输入验证和清理
   - SQL注入防护
   - XSS和CSRF防护
   - 文件上传安全

## 💰 成本与资源估算

### 开发资源:
- **主要开发者**: 萝卜头 (100%时间)
- **技术支持**: YuClaudeBot (20-30%时间，按需)
- **时间估算**: 10-14周完成核心功能
- **总工作量**: 约400-600人时

### 基础设施成本:
1. **云服务器** (前端): $10-50/月 (根据流量)
2. **内部服务器**: 已有基础设施，边际成本低
3. **存储成本**: 共享FileBot存储，边际成本低
4. **网络成本**: VPN/专线费用 (如有)
5. **工具成本**: 开发工具，约$0-100/月

### 总成本预测:
- **开发成本**: 以人力为主 (萝卜头时间)
- **运营成本**: $50-200/月 (初期)
- **营销成本**: 单独预算

---

**文档版本**: 1.0  
**创建时间**: 2026-03-21 07:00 EDT  
**技术基础**: 基于用户明确技术偏好 (纯粹的HTML文本, FastAPI, 共享数据库, 前后端分离部署)  
**讨论重点**: 
- 前端具体技术选择确认 (htmx/TipTap等)
- 数据库共享实施方案细节
- 部署网络架构具体设计
- 开发时间表和优先级确认
- 与FileBot集成技术细节