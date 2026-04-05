# WebBot 技术方案文档

## 🏗️ 技术架构概述

### 设计原则
1. **与FileBot技术栈一致**: 最大化代码复用和开发效率
2. **微服务架构**: 独立部署，与FileBot松耦合集成
3. **现代化技术栈**: 采用行业最佳实践和工具
4. **可扩展设计**: 支持从小型个人网站到大型政府门户

## 🔧 技术栈选择

### 前端技术栈 (与FileBot一致)
- **框架**: React 19 + TypeScript
- **构建工具**: Vite (快速构建和热重载)
- **状态管理**: Zustand (轻量级) 或 Redux Toolkit
- **UI组件库**: 
  - 基础: Tailwind CSS + Headless UI
  - 组件: Radix UI 或 shadcn/ui
  - 图标: Lucide React
- **路由**: React Router v7
- **数据获取**: TanStack Query (React Query)
- **表单处理**: React Hook Form + Zod (验证)
- **代码质量**: ESLint + Prettier + TypeScript严格模式
- **测试**: Vitest + React Testing Library + Playwright (E2E)

### 后端技术栈 (与FileBot一致)
- **框架**: Python FastAPI (异步支持，高性能)
- **API文档**: 自动生成OpenAPI文档 (Swagger UI)
- **数据库**: 
  - 初期: SQLite (与FileBot共享，简化部署)
  - 扩展期: PostgreSQL (生产环境，支持并发)
- **ORM**: SQLAlchemy 2.0 + Alembic (数据库迁移)
- **认证**: JWT + OAuth2 (与FileBot用户系统集成)
- **文件存储**: 通过FileBot API管理 (复用FileBot文件服务)
- **缓存**: Redis (可选，性能优化)
- **任务队列**: Celery + Redis (异步任务处理)
- **测试**: pytest + FastAPI TestClient

### 基础设施
- **容器化**: Docker + Docker Compose
- **部署**: 
  - 开发环境: 本地Docker Compose
  - 生产环境: Kubernetes 或 云服务 (AWS/GCP/Azure)
- **监控**: Prometheus + Grafana
- **日志**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **CI/CD**: GitHub Actions 或 GitLab CI

## 🏛️ 系统架构设计

### 整体架构图
```
┌─────────────────────────────────────────────────────────────┐
│                   客户端 (浏览器/移动端)                     │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTPS/WebSocket
┌───────────────────────────▼─────────────────────────────────┐
│                  负载均衡器 / API网关                        │
└──────────────┬────────────────────────────┬─────────────────┘
               │                            │
┌──────────────▼────────────┐   ┌───────────▼──────────────┐
│        WebBot前端          │   │     WebBot后端API        │
│   (React + Vite + SPA)    │   │   (FastAPI + SQLite)     │
└──────────────┬────────────┘   └───────────┬──────────────┘
               │                            │
┌──────────────▼────────────────────────────▼──────────────┐
│                 FileBot微服务集群                         │
│  (用户服务、文件服务、认证服务、AI服务)                  │
└──────────────────────────────────────────────────────────┘
```

### 微服务划分
1. **WebBot前端服务**: SPA应用，提供用户界面
2. **WebBot后端服务**: 核心业务逻辑和API
3. **FileBot用户服务**: 复用FileBot的用户管理系统
4. **FileBot文件服务**: 复用FileBot的文件存储和管理
5. **FileBot AI服务**: 可选，用于内容分析和优化

### 数据库设计

#### 核心数据表
1. **pages表**: 网页内容
   - id, title, slug, content (JSON), status, author_id, created_at, updated_at
   
2. **templates表**: 页面模板
   - id, name, content (JSON), category, is_public, author_id
   
3. **versions表**: 页面版本历史
   - id, page_id, version_number, content_snapshot, author_id, created_at
   
4. **collaborations表**: 协作信息
   - id, page_id, user_id, role, permissions, joined_at
   
5. **publications表**: 发布记录
   - id, page_id, environment, version_id, published_by, published_at

#### 与FileBot共享的表
1. **users表**: 用户信息 (共享)
2. **organizations表**: 组织信息 (共享)
3. **files表**: 文件元数据 (通过FileBot API访问)

### API设计

#### 核心API端点
```
# 页面管理
GET    /api/v1/pages                  # 获取页面列表
POST   /api/v1/pages                  # 创建新页面
GET    /api/v1/pages/{id}             # 获取页面详情
PUT    /api/v1/pages/{id}             # 更新页面
DELETE /api/v1/pages/{id}             # 删除页面

# 版本控制
GET    /api/v1/pages/{id}/versions    # 获取版本历史
POST   /api/v1/pages/{id}/versions    # 创建新版本
GET    /api/v1/versions/{id}          # 获取版本详情
POST   /api/v1/versions/{id}/restore  # 恢复到指定版本

# 协作功能
GET    /api/v1/pages/{id}/collaborators  # 获取协作者
POST   /api/v1/pages/{id}/collaborators  # 添加协作者
PUT    /api/v1/collaborations/{id}       # 更新协作者权限
DELETE /api/v1/collaborations/{id}       # 移除协作者

# 发布管理
GET    /api/v1/environments              # 获取环境列表
POST   /api/v1/pages/{id}/publish       # 发布页面到环境
GET    /api/v1/publications              # 获取发布记录
DELETE /api/v1/publications/{id}         # 取消发布

# FileBot集成
GET    /api/v1/filebot/files            # 获取FileBot文件列表
POST   /api/v1/filebot/upload           # 上传文件到FileBot
GET    /api/v1/filebot/files/{id}       # 获取文件详情
```

#### 与FileBot集成API
WebBot后端将通过内部API调用FileBot服务：
- `GET /filebot-api/v1/users/current` - 获取当前用户信息
- `GET /filebot-api/v1/files` - 浏览文件
- `POST /filebot-api/v1/files/upload` - 上传文件
- `GET /filebot-api/v1/files/{id}/url` - 获取文件访问URL

## 🎨 前端架构详细设计

### 组件结构
```
src/
├── components/           # 可复用UI组件
│   ├── ui/              # 基础UI组件 (Button, Input, Card等)
│   ├── editor/          # 编辑器组件
│   ├── templates/       # 模板组件
│   └── layout/          # 布局组件
├── pages/               # 页面组件
│   ├── Dashboard/       # 仪表板
│   ├── Editor/          # 页面编辑器
│   ├── Templates/       # 模板管理
│   ├── Settings/        # 设置页面
│   └── Auth/            # 认证页面
├── services/            # API服务层
│   ├── api.ts           # API客户端配置
│   ├── page.service.ts  # 页面相关API
│   ├── template.service.ts # 模板相关API
│   └── filebot.service.ts  # FileBot集成API
├── stores/              # 状态管理
│   ├── auth.store.ts    # 认证状态
│   ├── editor.store.ts  # 编辑器状态
│   └── ui.store.ts      # UI状态
├── hooks/               # 自定义Hook
│   ├── useAuth.ts       # 认证相关Hook
│   ├── usePages.ts      # 页面相关Hook
│   └── useFilebot.ts    # FileBot集成Hook
├── utils/               # 工具函数
│   ├── validation.ts    # 验证工具
│   ├── formatting.ts    # 格式化工具
│   └── constants.ts     # 常量定义
└── types/               # TypeScript类型定义
    ├── api.types.ts     # API类型
    ├── page.types.ts    # 页面相关类型
    └── user.types.ts    # 用户相关类型
```

### 编辑器架构
WebBot的核心是页面编辑器，采用模块化设计：
1. **编辑器核心**: 基于ProseMirror或TipTap (富文本编辑器框架)
2. **组件系统**: 可拖拽的组件库
3. **属性面板**: 组件属性编辑
4. **画布区域**: 页面预览和编辑
5. **工具栏**: 编辑工具和操作

## 🚀 开发路线图

### 阶段1: 基础MVP (4-6周)
**目标**: 实现基本页面创建、编辑、发布功能

**前端任务**:
1. 项目脚手架搭建 (React + TypeScript + Vite)
2. 认证页面和用户仪表板
3. 基本页面列表和详情页
4. 简单文本编辑器 (基于textarea或简单富文本)

**后端任务**:
1. FastAPI项目初始化
2. 数据库设计和迁移脚本
3. 基本CRUD API (页面管理)
4. 与FileBot用户系统集成
5. 基础发布功能

### 阶段2: 核心功能增强 (4-6周)
**目标**: 添加版本控制、协作功能、模板系统

**前端任务**:
1. 增强型编辑器 (拖拽组件、属性面板)
2. 版本历史界面和对比功能
3. 协作者管理和权限控制
4. 模板库和模板选择器

**后端任务**:
1. 版本控制系统实现
2. 协作功能API
3. 模板管理系统
4. 审批工作流基础

### 阶段3: 高级功能 (4-6周)
**目标**: 完善发布流程、性能优化、管理功能

**前端任务**:
1. 多环境发布管理界面
2. 页面性能分析工具
3. SEO优化工具
4. 移动端响应式优化

**后端任务**:
1. 完整的发布管道
2. 性能监控和优化
3. 审计日志和安全增强
4. API速率限制和缓存

### 阶段4: 企业级功能 (4-8周)
**目标**: SSO集成、高级安全、定制功能

**前端任务**:
1. SSO集成界面
2. 高级安全设置
3. 自定义工作流设计器
4. 多语言支持界面

**后端任务**:
1. SSO集成 (SAML, OIDC)
2. 高级安全功能 (IP限制、2FA)
3. 自定义插件系统
4. 多语言内容管理

## 🔄 与FileBot的集成方案

### 技术集成点
1. **用户认证集成**:
   - 共享JWT token验证
   - 统一用户会话管理
   - 跨产品单点登录

2. **文件服务集成**:
   - WebBot通过FileBot API上传/管理文件
   - FileBot提供文件存储、转换、优化服务
   - 统一文件权限控制

3. **数据库共享策略**:
   - 方案A: 共享SQLite数据库文件
   - 方案B: 通过API访问FileBot用户数据
   - 推荐: 方案B (松耦合，独立部署)

4. **部署架构**:
   ```
   方案1: 一体化部署
   [WebBot前端] → [WebBot后端] → [FileBot服务集群]
   
   方案2: 独立部署 + API网关
   [API网关] → [WebBot服务] → [FileBot服务]
               ↘ [FileBot前端] ↗
   ```

## 📈 性能与扩展性考虑

### 性能优化
1. **前端性能**:
   - 代码分割和懒加载
   - 图片懒加载和优化
   - 虚拟化长列表
   - Service Worker缓存

2. **后端性能**:
   - 数据库查询优化和索引
   - Redis缓存热点数据
   - 异步任务处理
   - CDN静态资源分发

### 扩展性设计
1. **水平扩展**:
   - 无状态服务设计
   - 数据库读写分离
   - 负载均衡配置

2. **垂直扩展**:
   - 微服务拆分粒度调整
   - 数据库分片策略
   - 缓存层级设计

## 🔒 安全设计

### 认证与授权
1. **认证机制**: JWT + 刷新令牌
2. **权限模型**: RBAC (基于角色的访问控制)
3. **API安全**: 速率限制、输入验证、SQL注入防护
4. **文件安全**: 文件类型验证、病毒扫描、访问控制

### 数据安全
1. **加密**: HTTPS传输加密、数据库字段加密
2. **备份**: 定期数据库备份、异地容灾
3. **审计**: 操作日志、访问日志、版本历史

### 合规性
1. **数据隐私**: GDPR、CCPA合规
2. **政府合规**: 政府安全标准满足
3. **可访问性**: WCAG 2.1 AA标准

## 🧪 测试策略

### 测试层级
1. **单元测试**: 函数和组件测试 (覆盖率>80%)
2. **集成测试**: API和数据库集成测试
3. **端到端测试**: 用户流程测试
4. **性能测试**: 负载测试和压力测试

### 测试工具
- **前端**: Vitest + React Testing Library + Playwright
- **后端**: pytest + FastAPI TestClient + Locust (性能测试)
- **API**: Postman + Newman (API测试)

## 📦 部署与运维

### 部署环境
1. **开发环境**: Docker Compose本地部署
2. **测试环境**: 独立的云服务器或容器集群
3. **生产环境**: Kubernetes集群或云托管服务

### 监控告警
1. **应用监控**: Prometheus + Grafana
2. **日志管理**: ELK Stack或云日志服务
3. **错误追踪**: Sentry或类似服务
4. **性能监控**: APM工具 (如New Relic)

### CI/CD流水线
1. **代码检查**: 代码质量、安全扫描
2. **自动化测试**: 单元测试、集成测试
3. **构建打包**: Docker镜像构建
4. **部署发布**: 蓝绿部署或金丝雀发布

## 💰 成本估算

### 开发成本
1. **人力成本**: 1名全栈开发者 (萝卜头) 主导，YuClaudeBot技术支持
2. **时间成本**: 4个阶段，总计16-26周
3. **工具成本**: 开发工具、测试工具、部署工具

### 基础设施成本
1. **服务器成本**: 云服务器或容器服务
2. **存储成本**: 文件存储、数据库存储
3. **网络成本**: CDN、API网关、负载均衡器
4. **监控成本**: 监控工具和服务

### 运营成本
1. **维护成本**: 持续开发、bug修复、功能增强
2. **支持成本**: 用户支持、技术文档
3. **营销成本**: 市场推广、用户获取

---

**文档版本**: 1.0  
**创建时间**: 2026-03-21 06:40 EDT  
**技术负责人**: 萝卜头 (Radish)  
**讨论用途**: 今晚8点三方讨论的技术方案文档  
**待确认事项**: 
- 技术栈最终确认 (特别是数据库选择)
- 开发时间表优先级
- 集成方案详细设计
- 成本预算和资源分配