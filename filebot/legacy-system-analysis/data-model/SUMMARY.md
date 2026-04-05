# 旧系统 (smarti) 数据模型分析

## 数据库架构概述

### 1. 支持的数据库
- **生产环境**：Oracle, MS SQL Server, Sybase
- **开发环境**：HSQLDB
- **配置文件**：多套配置文件支持不同数据库（hibernate-smarti.cfg.xml, hibernate-sybase.cfg.xml等）

### 2. 核心表结构

#### 2.1 用户表 (user)
- **id**：主键，整数类型
- **username**：用户名
- **password**：密码（明文或哈希）
- **email**：邮箱
- **fullName**：全名
- **isActive**：是否激活
- **role**：角色（admin, user等）
- **createdDate**：创建时间

#### 2.2 应用表 (app)
- **id**：主键，整数类型
- **name**：应用名称
- **description**：描述
- **createdDate**：创建时间
- **createdBy**：创建者

#### 2.3 抽屉表 (drawer)
- **id**：主键，整数类型
- **app_id**：外键，关联应用
- **name**：抽屉名称
- **order_index**：排序索引
- **createdDate**：创建时间

#### 2.4 文件夹表 (folder)
- **id**：主键，整数类型
- **drawer_id**：外键，关联抽屉
- **parent_folder_id**：外键，自关联（支持嵌套）
- **name**：文件夹名称
- **path**：虚拟路径
- **description**：描述
- **createdDate**：创建时间

#### 2.5 文档表 (document)
- **id**：主键，整数类型
- **folder_id**：外键，关联文件夹
- **documentNumber**：文档编号（唯一）
- **title**：文档标题
- **description**：文档描述
- **fileId**：关联文件表的ID
- **status**：文档状态（active, archived, deleted, processing）
- **type**：文档类型（general, invoice, contract, report, other）
- **comments**：备注
- **createdDate**：创建时间
- **createdBy**：创建者
- **updatedDate**：更新时间
- **updatedBy**：更新者

#### 2.6 文件表 (file)
- **id**：主键，整数类型
- **original_filename**：原始文件名
- **stored_filename**：存储文件名（UUID格式）
- **file_size**：文件大小（字节）
- **file_type**：文件类型（tiff, pdf, doc, docx等）
- **mime_type**：MIME类型
- **page_count**：页数
- **resolution**：分辨率
- **uploaded_by**：上传者ID
- **createdDate**：创建时间

#### 2.7 页面表 (page) - **关键表**
- **id**：复合主键（document_id + page_number）
- **document_id**：外键，关联文档
- **page_number**：页码
- **index1** - **index9**：9个索引字段
- **original_page_path**：原始页面文件路径（如TIFF单页）
- **converted_page_path**：转换后页面路径（PDF单页）
- **thumbnail_path**：缩略图路径
- **width**：页面宽度
- **height**：页面高度
- **ocr_text**：OCR识别文本
- **createdDate**：创建时间
- **createdBy**：创建者
- **updatedDate**：更新时间
- **updatedBy**：更新者

### 3. 关系映射

#### 3.1 一对多关系
```
App (1) → (*) Drawer
Drawer (1) → (*) Folder
Folder (1) → (*) Document
Document (1) → (*) Page
Document (1) → (1) File
```

#### 3.2 自引用关系
```
Folder (1) → (*) Folder (parent_folder_id)
```

### 4. 审计字段模式
所有主要表都包含以下审计字段：
- **createdDate**：记录创建时间
- **createdBy**：记录创建者
- **updatedDate**：记录最后更新时间
- **updatedBy**：记录最后更新者

### 5. 状态和类型枚举

#### 5.1 文档状态 (Document.status)
- **ACTIVE**：活跃状态
- **ARCHIVED**：已归档
- **DELETED**：已删除（软删除）
- **PROCESSING**：处理中

#### 5.2 文档类型 (Document.type)
- **GENERAL**：普通文档
- **INVOICE**：发票
- **CONTRACT**：合同
- **REPORT**：报告
- **OTHER**：其他

### 6. 索引字段设计

#### 6.1 字段数量
- 页面表支持**9个索引字段**（index1-index9）
- 实际使用数量根据应用配置决定（App.appConfigs）

#### 6.2 使用模式
- 索引字段用于快速检索和分类
- 可以在查询时作为搜索条件
- 支持层级显示（根据displays变量）

#### 6.3 配置管理
- 通过App.appConfigs配置每个索引字段的名称和显示顺序
- 不同应用可以有不同数量的有效索引字段

### 7. 文件存储设计

#### 7.1 文件名策略
- **原始文件名**：用户上传时的文件名
- **存储文件名**：UUID格式，避免文件名冲突
- **页面文件**：基于文档ID和页码生成

#### 7.2 文件路径结构
```
{base_path}/{app_id}/{drawer_id}/{folder_id}/{document_id}/
├── original.{ext}          # 原始文件
├── converted.pdf           # 转换后PDF
└── pages/
    ├── page_1.{ext}       # 原始页面文件
    ├── page_1.pdf         # 转换后页面PDF
    └── page_1_thumb.jpg   # 页面缩略图
```

### 8. 数据完整性约束

#### 8.1 外键约束
- 所有外键关系都有数据库级约束
- 级联删除配置（删除文档时删除相关页面）

#### 8.2 唯一约束
- document.documentNumber：文档编号唯一
- user.username：用户名唯一
- user.email：邮箱唯一（如配置）

#### 8.3 数据验证
- 文件大小限制
- 文件类型验证
- 必填字段验证

### 9. 性能设计考虑

#### 9.1 索引策略
- 主键索引：所有表的主键
- 外键索引：所有外键字段
- 查询字段索引：username, documentNumber, status等
- 复合索引：频繁查询的组合字段

#### 9.2 分区策略
- 按时间分区：历史数据归档
- 按应用分区：大型部署的多租户支持

### 10. 新系统数据模型映射建议

#### 10.1 直接映射字段
| 旧系统字段 | 新系统字段 | 说明 |
|------------|------------|------|
| id | id | 整数→UUID转换 |
| createdDate | created_at | 时间格式标准化 |
| createdBy | created_by | 直接复制 |
| index1-index9 | index1-index9 | 保持9个索引字段 |

#### 10.2 类型转换
| 旧系统类型 | 新系统类型 | 转换规则 |
|------------|------------|----------|
| 整数ID | UUID | 基于旧ID生成确定性UUID |
| 数据库时间戳 | ISO8601字符串 | 时间格式标准化 |
| 枚举字符串 | Python Enum | 枚举值映射 |

#### 10.3 结构调整
| 调整项 | 理由 | 实现方式 |
|--------|------|----------|
| 合并Document和File表 | 简化模型 | 在新Document表中包含文件信息 |
| 统一审计字段命名 | 一致性 | created_at, created_by等 |
| 添加转换状态字段 | 新需求 | 支持文档转换状态跟踪 |

### 11. 迁移兼容性考虑

#### 11.1 必须保持的结构
1. **9个索引字段**：核心搜索功能依赖
2. **审计字段**：合规性和追溯性要求
3. **层级关系**：App→Drawer→Folder→Document→Page
4. **文档状态和类型**：业务逻辑依赖

#### 11.2 可以优化的结构
1. **文件存储策略**：可以优化但保持向后兼容
2. **数据库类型**：从多种数据库统一到SQLite
3. **ID生成方式**：从整数改为UUID，但保持映射关系

#### 11.3 数据验证规则
1. **保持现有验证**：确保迁移后数据有效性
2. **增强验证**：添加新的验证规则（如文件类型限制）
3. **错误处理**：兼容旧系统的错误代码和消息

### 12. 结论

旧系统的数据模型设计合理，具有以下特点：
1. **层级清晰**：明确的App→Drawer→Folder→Document→Page结构
2. **扩展性好**：支持9个索引字段，满足不同业务需求
3. **审计完整**：完整的创建和更新审计跟踪
4. **文件管理**：分离的文件存储和元数据管理

新系统应该在保持这些核心设计的基础上，进行以下改进：
1. **简化模型**：合并相关表，减少复杂度
2. **现代类型**：使用UUID、枚举等现代类型
3. **增强功能**：添加文档转换状态跟踪
4. **性能优化**：优化索引和查询策略

**迁移关键**：确保数据结构和业务逻辑的兼容性，实现平滑过渡。