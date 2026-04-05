# FileBot 架构设计

## 整体架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端 (React)   │    │   后端 (FastAPI) │    │   转换服务      │
│                 │    │                 │    │   (Python库 +   │
│ - 文件管理界面   │◄──►│ - REST API      │◄──►│   外部工具)      │
│ - 搜索功能      │    │ - 用户管理       │    │                 │
│ - 预览功能      │    │ - 数据模型       │    │ - TIFF→PDF     │
│                 │    │ - 权限控制       │    │ - Word→PDF     │
│                 │    │                 │    │ - PCL→PDF       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   数据库         │
                       │   (PostgreSQL)  │
                       │   - 用户数据     │
                       │   - 文件元数据   │
                       │   - 权限信息     │
                       └─────────────────┘
```

## 数据结构模型

### 1. 核心层次结构
```
App (应用)
  ├── Drawer (抽屉)
  │     ├── Folder (文件夹)
  │     │     ├── Document (文档)
  │     │     │     ├── Page (页面) - 1
  │     │     │     ├── Page (页面) - 2
  │     │     │     └── ...
  │     │     └── ...
  │     └── ...
  └── ...
```

### 2. 数据库表设计

#### 用户表 (users)
- id: UUID (主键)
- username: 用户名
- email: 邮箱
- password_hash: 密码哈希
- created_at: 创建时间
- updated_at: 更新时间
- is_active: 是否激活
- role: 角色 (admin, user, viewer)

#### 应用表 (apps)
- id: UUID (主键)
- name: 应用名称
- description: 描述
- owner_id: 所属用户ID (外键)
- created_at: 创建时间
- settings: JSON配置

#### 抽屉表 (drawers)
- id: UUID (主键)
- app_id: 所属应用ID (外键)
- name: 抽屉名称
- order_index: 排序索引
- created_at: 创建时间

#### 文件夹表 (folders)
- id: UUID (主键)
- drawer_id: 所属抽屉ID (外键)
- parent_folder_id: 父文件夹ID (自引用，支持嵌套)
- name: 文件夹名称
- path: 虚拟路径
- created_at: 创建时间

#### 文档表 (documents)
- id: UUID (主键)
- folder_id: 所属文件夹ID (外键)
- original_filename: 原始文件名
- stored_filename: 存储文件名 (UUID)
- file_size: 文件大小
- file_type: 文件类型 (tiff, pdf, docx, jpeg, pcl, etc.)
- mime_type: MIME类型
- conversion_status: 转换状态 (pending, processing, completed, failed)
- converted_pdf_path: 转换后PDF路径
- metadata: JSON元数据 (分辨率、页数等)
- created_at: 创建时间
- updated_at: 更新时间
- uploaded_by: 上传用户ID (外键)

**重要设计决策**：与旧系统不同，FileBot采用**预处理转换模式**：
- **旧系统**：按需转换（用户访问时才转换，节省存储但延迟高）
- **新系统**：上传后立即转换（存储原始+PDF，用户体验更好）
- **理由**：存储成本大幅降低，用户体验优先级提高

#### 页面表 (pages)
- id: UUID (主键)
- document_id: 所属文档ID (外键)
- page_number: 页码
- original_page_path: 原始页面路径 (如TIFF单页)
- converted_page_path: 转换后页面路径 (PDF单页)
- thumbnail_path: 缩略图路径
- created_at: 创建时间

#### 转换任务表 (conversion_tasks)
- id: UUID (主键)
- document_id: 关联文档ID (外键)
- status: 状态 (queued, processing, completed, failed)
- source_format: 源格式
- target_format: 目标格式
- started_at: 开始时间
- completed_at: 完成时间
- error_message: 错误信息
- created_at: 创建时间

#### 权限表 (permissions)
- id: UUID (主键)
- user_id: 用户ID (外键)
- resource_type: 资源类型 (app, drawer, folder, document)
- resource_id: 资源ID
- permission_level: 权限级别 (read, write, admin)
- created_at: 创建时间

## 搜索功能设计（简化版）

### 搜索维度
1. **文件名搜索** (原始文件名)
2. **元数据搜索** (文件类型、大小、创建时间、上传者等)
3. **索引搜索** (页面级别的索引字段 - index1到index9)
4. **层级搜索** (按App/Drawer/Folder路径)

### 搜索实现方案
- 数据库标准索引 (SQLite索引优化)
- 基于页面索引字段的快速检索
- 简单的关键词匹配，不包含复杂全文检索
- 标签系统 (可选，为文档添加标签增强搜索)

## API 设计原则
1. RESTful 风格
2. JWT 认证
3. 分页支持
4. 过滤和排序
5. 版本控制 (v1, v2)

## 部署架构
- 前端: Nginx 静态文件服务
- 后端: Gunicorn/Uvicorn + FastAPI
- 数据库: PostgreSQL (主从复制，可选)
- 文件存储: 本地文件系统 + 定期备份
- 缓存: Redis (可选，性能优化)
- 消息队列: Celery + Redis (异步任务处理)