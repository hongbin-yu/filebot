# WebBot 数据库架构设计

## 版本信息
- **文档版本**: 1.0.0
- **创建日期**: 2026-03-22
- **最后更新**: 2026-03-22
- **数据库类型**: SQLite (与FileBot共享)
- **设计原则**: 与FileBot完全一致的存储模式

## 架构概述

WebBot使用与FileBot相同的SQLite数据库，采用紧密集成架构。所有文件存储和版本控制通过FileBot处理，WebBot专注于页面管理和内容展示。

## 核心表设计

### 1. webbot_page (页面主表)

存储页面的核心信息和内容。

```sql
-- 页面主表
CREATE TABLE webbot_page (
    -- 主键标识 (基于标题生成，用于URL)
    id TEXT PRIMARY KEY,  -- 如"home-page-about-us"
    
    -- 用户提供的7个核心字段
    title TEXT NOT NULL,                     -- 页面标题
    parent_id TEXT REFERENCES webbot_page(id),  -- 父页面ID (支持层次结构)
    other_lang_page_id TEXT REFERENCES webbot_page(id),  -- 其他语言版本ID
    create_by INTEGER REFERENCES users(id),   -- 创建者 (共享FileBot用户表)
    last_modify TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 最后修改时间
    last_publish TIMESTAMP,                   -- 最后发布时间
    
    -- 内容存储 (方案A核心: 文本存当前版)
    current_content_text TEXT,                -- 当前版本文本内容 (快速访问)
    current_html_content TEXT,                -- 当前版本HTML内容
    
    -- FileBot文档引用 (紧密集成)
    source_document_id TEXT REFERENCES documents(id),  -- FileBot源文档ID
    current_document_id TEXT REFERENCES documents(id),  -- FileBot当前版本文档ID
    
    -- FileBot风格存储字段
    storage_subfolder TEXT,                   -- 存储子文件夹路径
    html_file_path TEXT,                      -- HTML文件完整路径
    
    -- 扩展字段
    language_code TEXT DEFAULT 'en',          -- 语言代码: 'en', 'fr'
    status TEXT DEFAULT 'draft',              -- draft/review/published/archived
    metadata_json TEXT,                       -- 扩展元数据 (JSON格式)
    ai_generated BOOLEAN DEFAULT FALSE,       -- 是否AI生成内容
    has_media BOOLEAN DEFAULT FALSE,          -- 是否包含媒体文件
    media_type TEXT,                          -- 主要媒体类型: 'document', 'image', 'video', 'audio'
    
    -- 系统字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,         -- 软删除标志
    
    -- 约束
    CHECK (language_code IN ('en', 'fr')),
    CHECK (status IN ('draft', 'review', 'published', 'archived'))
);

-- 索引优化
CREATE INDEX idx_webbot_page_parent ON webbot_page(parent_id);
CREATE INDEX idx_webbot_page_lang ON webbot_page(language_code);
CREATE INDEX idx_webbot_page_status ON webbot_page(status);
CREATE INDEX idx_webbot_page_created ON webbot_page(create_by, created_at);
CREATE INDEX idx_webbot_page_modified ON webbot_page(last_modify);
CREATE INDEX idx_webbot_page_published ON webbot_page(last_publish);
```

### 2. webbot_page_metadata (页面元数据表)

存储页面的扩展元数据，采用键值对结构。

```sql
-- 页面元数据表
CREATE TABLE webbot_page_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id TEXT NOT NULL REFERENCES webbot_page(id),
    meta_key TEXT NOT NULL,                    -- 元数据键
    meta_value TEXT NOT NULL,                  -- 元数据值
    meta_type TEXT DEFAULT 'text',             -- 数据类型: 'text', 'json', 'url', 'boolean', 'number'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束: 每个页面每个键唯一
    UNIQUE(page_id, meta_key)
);

-- 索引优化
CREATE INDEX idx_metadata_page ON webbot_page_metadata(page_id);
CREATE INDEX idx_metadata_key ON webbot_page_metadata(meta_key);
CREATE INDEX idx_metadata_type ON webbot_page_metadata(meta_type);
```

### 3. webbot_page_versions (页面版本关系表)

管理页面与FileBot文档版本的关联关系。

```sql
-- 页面版本关系表
CREATE TABLE webbot_page_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id TEXT NOT NULL REFERENCES webbot_page(id),
    document_id TEXT NOT NULL REFERENCES documents(id),  -- FileBot文档ID
    version_number INTEGER NOT NULL,                     -- 版本号
    version_type TEXT DEFAULT 'historical',              -- 'current', 'historical', 'draft'
    is_current BOOLEAN DEFAULT FALSE,                    -- 是否为当前版本
    change_description TEXT,                             -- 变更描述
    created_by INTEGER REFERENCES users(id),             -- 创建者
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    UNIQUE(page_id, version_number),
    CHECK (version_type IN ('current', 'historical', 'draft'))
);

-- 索引优化
CREATE INDEX idx_versions_page ON webbot_page_versions(page_id);
CREATE INDEX idx_versions_document ON webbot_page_versions(document_id);
CREATE INDEX idx_versions_current ON webbot_page_versions(page_id, is_current);
CREATE INDEX idx_versions_type ON webbot_page_versions(version_type);
CREATE INDEX idx_versions_created ON webbot_page_versions(created_at);
```

### 4. webbot_media_references (媒体引用表)

管理页面引用的媒体文件（图像、视频、音频）。

```sql
-- 媒体引用表
CREATE TABLE webbot_media_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id TEXT NOT NULL REFERENCES webbot_page(id),
    document_id TEXT NOT NULL REFERENCES documents(id),  -- FileBot中的媒体文档
    media_type TEXT NOT NULL,                            -- 'image', 'video', 'audio'
    position INTEGER,                                    -- 在页面中的位置顺序
    caption TEXT,                                        -- 媒体说明文字
    alt_text TEXT,                                       -- 替代文本 (可访问性)
    width INTEGER,                                       -- 宽度 (图像/视频)
    height INTEGER,                                      -- 高度 (图像/视频)
    duration INTEGER,                                    -- 时长 (视频/音频，秒)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    CHECK (media_type IN ('image', 'video', 'audio'))
);

-- 索引优化
CREATE INDEX idx_media_page ON webbot_media_references(page_id);
CREATE INDEX idx_media_type ON webbot_media_references(media_type);
CREATE INDEX idx_media_position ON webbot_media_references(page_id, position);
```

### 5. webbot_page_url_references (页面URL引用表)

存储页面间的URL引用关系，用于检测页面移动时的影响。

```sql
-- 页面URL引用表
CREATE TABLE webbot_page_url_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_page_id TEXT NOT NULL REFERENCES webbot_page(id),      -- 引用源页面
    target_url_path TEXT NOT NULL,                                -- 被引用的URL路径，如 "/en/about-us"
    target_page_id TEXT,                                          -- 对应的页面ID（如果URL能解析到有效页面）
    reference_context TEXT NOT NULL,                              -- 引用上下文：'content_link', 'nav_generated', 'lang_switch'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    CHECK (reference_context IN ('content_link', 'nav_generated', 'lang_switch')),
    
    -- 索引优化
    INDEX idx_refs_source (source_page_id),
    INDEX idx_refs_target_url (target_url_path),
    INDEX idx_refs_context (reference_context)
);
```

### 6. webbot_url_redirects (URL重定向表)

存储页面重命名或移动时创建的URL重定向。

```sql
-- URL重定向表
CREATE TABLE webbot_url_redirects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    old_url_path TEXT NOT NULL UNIQUE,                            -- 旧URL路径，如 "/en/old-page-id"
    new_url_path TEXT NOT NULL,                                   -- 新URL路径，如 "/en/new-page-id"
    redirect_type TEXT DEFAULT 'permanent',                       -- 重定向类型：'permanent'(301), 'temporary'(302)
    created_by INTEGER REFERENCES users(id),                      -- 创建者
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,                                         -- 重定向过期时间（可选）
    
    -- 约束
    CHECK (redirect_type IN ('permanent', 'temporary'))
);

-- 索引优化
CREATE INDEX idx_redirects_old ON webbot_url_redirects(old_url_path);
CREATE INDEX idx_redirects_new ON webbot_url_redirects(new_url_path);
CREATE INDEX idx_redirects_type ON webbot_url_redirects(redirect_type);
```

## 与FileBot的共享表

### 1. users (用户表 - 共享)
```sql
-- 使用FileBot现有的users表
-- WebBot通过外键引用用户ID
```

### 2. documents (文档表 - 共享)
```sql
-- 使用FileBot现有的documents表
-- WebBot通过source_document_id和current_document_id引用
```

## 视图设计

### 1. 页面详细视图
```sql
CREATE VIEW v_webbot_page_details AS
SELECT 
    wp.*,
    u.username as creator_username,
    COUNT(wpv.id) as version_count,
    MAX(wpv.created_at) as last_version_date
FROM webbot_page wp
LEFT JOIN users u ON wp.create_by = u.id
LEFT JOIN webbot_page_versions wpv ON wp.id = wpv.page_id
WHERE wp.is_deleted = FALSE
GROUP BY wp.id;
```

### 2. 页面树视图
```sql
CREATE VIEW v_webbot_page_tree AS
WITH RECURSIVE page_tree AS (
    SELECT 
        id,
        title,
        parent_id,
        language_code,
        status,
        1 as depth,
        id as path
    FROM webbot_page
    WHERE parent_id IS NULL AND is_deleted = FALSE
    
    UNION ALL
    
    SELECT 
        wp.id,
        wp.title,
        wp.parent_id,
        wp.language_code,
        wp.status,
        pt.depth + 1,
        pt.path || '/' || wp.id
    FROM webbot_page wp
    JOIN page_tree pt ON wp.parent_id = pt.id
    WHERE wp.is_deleted = FALSE
)
SELECT * FROM page_tree
ORDER BY path;
```

### 3. 多语言页面对视图
```sql
CREATE VIEW v_webbot_language_pairs AS
SELECT 
    en_page.id as en_page_id,
    en_page.title as en_title,
    fr_page.id as fr_page_id,
    fr_page.title as fr_title,
    en_page.status as en_status,
    fr_page.status as fr_status
FROM webbot_page en_page
LEFT JOIN webbot_page fr_page ON en_page.other_lang_page_id = fr_page.id
WHERE en_page.language_code = 'en' AND en_page.is_deleted = FALSE
UNION ALL
SELECT 
    en_page.id as en_page_id,
    en_page.title as en_title,
    fr_page.id as fr_page_id,
    fr_page.title as fr_title,
    en_page.status as en_status,
    fr_page.status as fr_status
FROM webbot_page fr_page
LEFT JOIN webbot_page en_page ON fr_page.other_lang_page_id = en_page.id
WHERE fr_page.language_code = 'fr' AND fr_page.is_deleted = FALSE;
```

## 数据迁移方案

### 初始数据库创建
```sql
-- 1. 创建webbot_page表
-- 2. 创建webbot_page_metadata表
-- 3. 创建webbot_page_versions表
-- 4. 创建webbot_media_references表
-- 5. 创建视图
-- 6. 创建初始数据（如默认页面、系统配置等）
```

### 数据备份和恢复
- 与FileBot共享数据库备份策略
- 定期备份webbot_*表
- 备份包含文件存储路径信息

## 性能优化策略

### 1. 查询优化
- 使用适当的索引
- 避免N+1查询问题
- 使用视图预计算复杂查询

### 2. 缓存策略
- 热门页面的HTML内容缓存
- 页面树结构缓存
- 元数据缓存

### 3. 分页优化
- 使用LIMIT/OFFSET分页
- 大型结果集使用游标分页
- 预计算分页信息

## 完整性约束

### 1. 外键约束
- 所有外键都启用REFERENCES约束
- 级联删除策略谨慎使用
- 软删除优先于物理删除

### 2. 业务规则约束
- 页面ID唯一性
- 语言代码有效性
- 状态有效性
- 版本号连续性

## 扩展性考虑

### 1. 多语言扩展
- 当前支持英语和法语
- 设计支持其他语言扩展
- 语言代码使用ISO 639-1标准

### 2. 媒体类型扩展
- 当前支持文档、图像、视频、音频
- 设计支持新的媒体类型
- 媒体处理器插件架构

### 3. 存储扩展
- 与FileBot存储系统深度集成
- 支持云存储扩展
- CDN集成支持

## 维护脚本

### 1. 数据库健康检查
```sql
-- 检查数据完整性
SELECT 'webbot_page' as table_name, COUNT(*) as row_count FROM webbot_page WHERE is_deleted = FALSE
UNION ALL
SELECT 'webbot_page_metadata', COUNT(*) FROM webbot_page_metadata
UNION ALL
SELECT 'webbot_page_versions', COUNT(*) FROM webbot_page_versions
UNION ALL
SELECT 'webbot_media_references', COUNT(*) FROM webbot_media_references;
```

### 2. 清理脚本
```sql
-- 清理软删除的记录（保留期30天）
DELETE FROM webbot_page 
WHERE is_deleted = TRUE 
AND updated_at < datetime('now', '-30 days');

-- 清理过期的历史版本（保留最近100个版本）
DELETE FROM webbot_page_versions 
WHERE version_type = 'historical' 
AND version_number NOT IN (
    SELECT version_number 
    FROM webbot_page_versions 
    WHERE page_id = ? 
    ORDER BY version_number DESC 
    LIMIT 100
);
```

## 变更日志

### v1.0.0 (2026-03-22)
- 初始数据库架构设计
- 基于与FileBot紧密集成的方案A
- 支持页面管理、元数据、版本控制、媒体引用
- 完整的索引和视图设计
- 性能优化和维护策略