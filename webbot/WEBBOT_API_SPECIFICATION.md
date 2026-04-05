# WebBot API 规范

## 版本信息
- **文档版本**: 1.0.0
- **创建日期**: 2026-03-22
- **最后更新**: 2026-03-22
- **状态**: 草案

## 概述

WebBot是一个基于FileBot的文件到网页转换系统，支持PDF、Word、图像、视频和音频文件上传，自动转换为符合Canada.ca标准的网页。本文档描述WebBot的REST API接口规范。

## 基础信息

### 技术栈
- **后端框架**: FastAPI (与FileBot保持一致)
- **数据库**: SQLite (与FileBot共享数据库文件)
- **文件存储**: 与FileBot完全一致的混合存储架构
- **前端框架**: 原生HTML + htmx + WET-BOEW组件
- **API版本**: v1

### 基础URL
```
http://localhost:8002/api/v1
```

### 认证和授权
- 使用与FileBot相同的JWT认证系统
- 共享FileBot的`users`表进行用户管理
- 基础权限：创建、编辑、发布、管理

## 核心数据模型

### 页面 (Page)
```json
{
  "id": "home-page-about-us",
  "title": "Home Page About Us",
  "parent_id": null,
  "other_lang_page_id": "page-accueil-a-propos",
  "language_code": "en",
  "status": "published",
  "current_content_text": "完整文本内容...",
  "current_html_content": "<div>HTML内容...</div>",
  "source_document_id": "filebot-doc-uuid-123",
  "current_document_id": "filebot-doc-uuid-456",
  "storage_subfolder": "pages/en/home-page-about-us",
  "html_file_path": "/webbot-storage/pages/en/abc123-uuid/index.html",
  "create_by": 1,
  "last_modify": "2026-03-22T12:00:00Z",
  "last_publish": "2026-03-22T12:00:00Z",
  "metadata": {
    "seo_title": "About Us - Company Name",
    "seo_description": "Learn about our company...",
    "og_image": "/media/about-us-image.jpg"
  }
}
```

## API端点

### 1. 页面管理

#### 1.1 获取页面列表
```
GET /pages
```

**查询参数**:
- `language` (可选): 语言代码，如'en', 'fr'
- `status` (可选): 状态过滤，如'draft', 'published', 'archived'
- `parent_id` (可选): 父页面ID过滤
- `limit` (可选): 每页数量，默认20
- `offset` (可选): 偏移量，默认0

**响应**:
```json
{
  "pages": [
    {
      "id": "home-page-about-us",
      "title": "Home Page About Us",
      "language_code": "en",
      "status": "published",
      "last_modify": "2026-03-22T12:00:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

#### 1.2 获取单个页面
```
GET /pages/{page_id}
```

**路径参数**:
- `page_id`: 页面ID (基于标题生成的URL标识符)

**响应**: 完整的页面对象

#### 1.3 创建页面 (通过文件上传)
```
POST /pages
```

**请求头**:
```
Content-Type: multipart/form-data
```

**表单数据**:
- `file`: 上传的文件 (PDF, Word, 图像等)
- `title`: 页面标题 (必需)
- `parent_id`: 父页面ID (可选)
- `language_code`: 语言代码，默认'en' (可选)
- `status`: 初始状态，默认'draft' (可选)

**处理流程**:
1. 接收上传文件
2. 调用FileBot API进行文件处理
3. 根据标题生成页面ID (空格→"-" + 小写，法语字符转换)
4. 创建页面记录，存储文本内容和FileBot文档引用
5. 创建初始版本记录

**响应**: 创建的页面对象

#### 1.4 更新页面
```
PUT /pages/{page_id}
```

**请求体**:
```json
{
  "title": "Updated Title",
  "current_content_text": "更新后的文本内容",
  "status": "review",
  "metadata": {
    "seo_title": "Updated SEO Title"
  }
}
```

**注意事项**:
- 更新`title`时可能需要重新生成`id` (如果id规则允许修改)
- 更新内容时会创建新的版本记录
- 可以部分更新，只包含需要修改的字段

#### 1.5 删除页面
```
DELETE /pages/{page_id}
```

**注意**: 标记为已删除或归档，而不是物理删除，保留历史版本

### 2. 引用管理

#### 2.1 获取页面引用关系
```
GET /pages/{page_id}/references
```

**查询参数**:
- `direction` (可选): 引用方向，'incoming'(被引用), 'outgoing'(引用其他), 'both'(双向)，默认'both'
- `context` (可选): 引用上下文过滤，如'content_link', 'nav_generated', 'lang_switch'

**响应**:
```json
{
  "page_id": "about-us",
  "incoming_references": [
    {
      "source_page_id": "home",
      "source_title": "Home Page",
      "target_url_path": "/en/about-us",
      "reference_context": "nav_generated",
      "created_at": "2026-03-22T10:00:00Z"
    }
  ],
  "outgoing_references": [
    {
      "target_url_path": "/en/contact",
      "target_page_id": "contact",
      "target_title": "Contact Us",
      "reference_context": "content_link",
      "created_at": "2026-03-22T11:00:00Z"
    }
  ]
}
```

#### 2.2 检查页面移动影响
```
POST /pages/{page_id}/check-move-impact
```

**查询参数**:
- `detailed` (可选): 是否返回详细影响列表，默认`false`（仅返回数量）

**请求体**:
```json
{
  "new_id": "new-page-id"
}
```

**响应 (detailed=false)**:
```json
{
  "old_url": "/en/old-page-id",
  "new_url": "/en/new-page-id",
  "total_affected": 3,
  "message": "移动此页面将影响3个引用页面，所有引用将自动更新"
}
```

**响应 (detailed=true)**:
```json
{
  "old_url": "/en/old-page-id",
  "new_url": "/en/new-page-id",
  "affected_pages": [
    {
      "page_id": "home",
      "title": "Home Page",
      "reference_context": "nav_generated"
    }
  ],
  "total_affected": 3
}
```

#### 2.3 执行页面移动
```
POST /pages/{page_id}/move
```

**请求体**:
```json
{
  "new_id": "new-page-id",
  "create_redirect": true,           // 可选，默认true
  "redirect_type": "permanent"       // 可选，默认'permanent'
}
```

**处理流程**:
1. 验证新ID是否可用
2. 检查引用影响（调用check-move-impact获取受影响页面数量）
3. **全自动更新所有引用链接**（无需用户确认）
4. 创建URL重定向记录（如果create_redirect为true）
5. 更新页面ID和相关URL
6. 返回移动结果和更新统计

**响应**:
```json
{
  "success": true,
  "old_id": "old-page-id",
  "new_id": "new-page-id",
  "old_url": "/en/old-page-id",
  "new_url": "/en/new-page-id",
  "references_updated": 3,
  "redirect_created": true,
  "message": "页面移动完成，自动更新了3个引用页面"
}
```

#### 2.4 创建URL重定向
```
POST /redirects
```

**请求体**:
```json
{
  "old_url_path": "/en/old-page-id",
  "new_url_path": "/en/new-page-id",
  "redirect_type": "permanent",
  "expires_at": "2027-03-22T12:00:00Z"  // 可选
}
```

#### 2.5 获取重定向列表
```
GET /redirects
```

**查询参数**:
- `old_url` (可选): 旧URL过滤
- `new_url` (可选): 新URL过滤
- `type` (可选): 重定向类型过滤
- `active_only` (可选): 仅返回未过期的重定向，默认true

### 3. 文件处理和FileBot集成

#### 2.1 上传并处理文件
```
POST /files/process
```

**请求头**:
```
Content-Type: multipart/form-data
```

**表单数据**:
- `file`: 上传的文件
- `process_type`: 处理类型，如'extract_text', 'convert_html' (可选)

**处理流程**:
1. 将文件上传到FileBot
2. 根据文件类型调用适当的FileBot处理功能
3. 返回处理结果 (文本内容、HTML、元数据等)

**响应**:
```json
{
  "success": true,
  "document_id": "filebot-doc-uuid-123",
  "content_text": "提取的文本内容...",
  "content_html": "<div>生成的HTML...</div>",
  "metadata": {
    "page_count": 5,
    "file_type": "pdf",
    "file_size": 102400
  }
}
```

#### 2.2 获取文件处理状态
```
GET /files/process/{task_id}/status
```

用于异步文件处理的状态查询。

### 4. 版本控制

#### 4.1 获取页面版本列表
```
GET /pages/{page_id}/versions
```

**响应**:
```json
{
  "versions": [
    {
      "id": 1,
      "version_number": 1,
      "version_type": "current",
      "change_description": "初始版本",
      "created_by": 1,
      "created_at": "2026-03-22T10:00:00Z",
      "document_id": "filebot-doc-uuid-456"
    }
  ]
}
```

#### 4.2 获取特定版本内容
```
GET /pages/{page_id}/versions/{version_number}
```

**响应**: 特定版本的内容和元数据

#### 4.3 恢复到特定版本
```
POST /pages/{page_id}/versions/{version_number}/restore
```

将页面内容恢复到指定版本，创建新的当前版本。

### 5. 元数据管理

#### 5.1 获取页面元数据
```
GET /pages/{page_id}/metadata
```

**响应**: 页面的所有元数据键值对

#### 5.2 设置页面元数据
```
PUT /pages/{page_id}/metadata/{key}
```

**请求体**:
```json
{
  "value": "metadata value",
  "meta_type": "text"
}
```

#### 5.3 批量更新元数据
```
PUT /pages/{page_id}/metadata
```

**请求体**:
```json
{
  "seo_title": "SEO Title",
  "seo_description": "SEO Description",
  "og_image": "/path/to/image.jpg"
}
```

### 6. 导航和结构

#### 6.1 获取页面树
```
GET /pages/tree
```

**查询参数**:
- `language`: 语言代码 (可选)
- `depth`: 树深度，默认3 (可选)

**响应**: 嵌套的页面结构树

#### 6.2 更新页面顺序
```
PUT /pages/{page_id}/order
```

**请求体**:
```json
{
  "position": 2,
  "parent_id": "parent-page-id"
}
```

### 6. 发布管理

#### 6.1 发布页面
```
POST /pages/{page_id}/publish
```

将页面状态从'draft'或'review'改为'published'，创建发布版本。

#### 6.2 取消发布
```
POST /pages/{page_id}/unpublish
```

将页面状态改回'draft'。

#### 6.3 批量发布
```
POST /pages/batch-publish
```

**请求体**:
```json
{
  "page_ids": ["page-1", "page-2"],
  "publish_note": "批量发布更新"
}
```

## FileBot API集成

### 文件上传到FileBot
```
POST http://localhost:8001/api/v1/documents/upload
```

**WebBot调用参数**:
```json
{
  "file": "文件二进制数据",
  "original_filename": "document.pdf",
  "process_options": {
    "extract_text": true,
    "generate_html": true,
    "store_original": true
  }
}
```

### 获取FileBot文档信息
```
GET http://localhost:8001/api/v1/documents/{document_id}
```

### FileBot处理状态查询
```
GET http://localhost:8001/api/v1/tasks/{task_id}
```

## 错误处理

### 错误响应格式
```json
{
  "error": {
    "code": "PAGE_NOT_FOUND",
    "message": "页面不存在",
    "details": "页面ID 'example-page' 不存在",
    "timestamp": "2026-03-22T12:00:00Z"
  }
}
```

### 常见错误代码
- `VALIDATION_ERROR`: 请求数据验证失败
- `PAGE_NOT_FOUND`: 页面不存在
- `FILE_PROCESSING_ERROR`: 文件处理失败
- `VERSION_CONFLICT`: 版本冲突
- `PERMISSION_DENIED`: 权限不足
- `FILEBOT_UNAVAILABLE`: FileBot服务不可用

## 速率限制

- 认证用户: 100请求/分钟
- 文件上传: 10文件/分钟
- API密钥: 1000请求/天

## 变更日志

### v1.0.0 (2026-03-22)
- 初始API规范
- 基于与FileBot紧密集成的架构设计
- 支持文件上传、页面管理、版本控制、元数据管理
- 完整的错误处理和速率限制规范