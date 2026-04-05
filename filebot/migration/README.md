# 数据迁移工具

## 概述
此工具用于将旧版 smarti 系统的数据迁移到新版 FileBot 系统。支持多种源数据库：Oracle, MS SQL Server, Sybase, HSQLDB（开发环境），目标为SQLite数据库。

## 支持的数据源
1. **Oracle** - 生产环境常见
2. **MS SQL Server** - 生产环境常见  
3. **Sybase** - 生产环境常见
4. **HSQLDB** - 开发/测试环境
5. **MySQL** - 部分环境

## 重要注意事项：转换模式差异

### 旧系统 vs 新系统转换模式
| 特性 | 旧系统 (smarti) | 新系统 (FileBot) |
|------|------------------|------------------|
| **转换时机** | 按需转换（用户访问时） | 预处理转换（上传后立即） |
| **存储要求** | 只存原始文件 | 存储原始文件 + PDF |
| **用户延迟** | 首次访问有转换延迟 | 无延迟（PDF已预转换） |
| **设计背景** | 10年前存储成本高 | 现代存储成本低廉 |

### 迁移影响
1. **数据迁移**：可以迁移文档元数据，但需要重新转换PDF
2. **文件处理**：原始文件可以迁移，但需要在新系统重新转换
3. **过渡策略**：建议分批迁移，避免大量文件同时转换
4. **存储规划**：需要规划双倍存储空间（原始文件 + PDF）

## 迁移策略

### 1. 并行运行（推荐）
- 新旧系统并行运行一段时间
- 新数据写入新系统，旧数据逐步迁移
- 最终切换流量到新系统

### 2. 一次性迁移
- 选择业务低峰期
- 停止旧系统写入
- 导出全部数据，导入新系统
- 验证数据完整性
- 切换至新系统

## 数据映射关系

### 旧系统表 → 新系统表
1. `user` → `users`
2. `app` → `apps`
3. `drawer` → `drawers`
4. `folder` → `folders`
5. `document` → `documents`
6. `file` → `documents` (合并)
7. `page` → `pages`

### 字段映射
#### User表
| 旧字段 | 新字段 | 备注 |
|--------|--------|------|
| id | id | UUID转换 |
| username | username | 直接复制 |
| password | password_hash | 密码重新哈希 |
| email | email | 直接复制 |
| fullName | full_name | 直接复制 |
| isActive | is_active | 直接复制 |
| role | role | 直接复制 |
| createdDate | created_at | 时间格式转换 |

#### App表
| 旧字段 | 新字段 | 备注 |
|--------|--------|------|
| id | id | UUID转换 |
| name | name | 直接复制 |
| description | description | 直接复制 |
| createdDate | created_at | 时间格式转换 |
| createdBy | created_by | 直接复制 |

#### Document表
| 旧字段 | 新字段 | 备注 |
|--------|--------|------|
| id | id | UUID转换 |
| documentNumber | document_number | 直接复制 |
| title | title | 直接复制 |
| description | description | 直接复制 |
| createdDate | created_at | 时间格式转换 |
| createdBy | created_by | 直接复制 |
| fileId | stored_filename | 文件关联处理 |
| status | status | 状态映射 |
| type | type | 类型映射 |
| comments | comments | 直接复制 |

#### Page表
| 旧字段 | 新字段 | 备注 |
|--------|--------|------|
| id | id | UUID转换 |
| documentId | document_id | 关联转换 |
| pageNumber | page_number | 直接复制 |
| index1-index9 | index1-index9 | 直接复制 |
| originalPagePath | original_page_path | 直接复制 |
| convertedPagePath | converted_page_path | 直接复制 |
| thumbnailPath | thumbnail_path | 直接复制 |
| width | width | 直接复制 |
| height | height | 直接复制 |
| ocrText | ocr_text | 直接复制 |
| createdDate | created_at | 时间格式转换 |

## 迁移步骤

### 步骤1：环境准备
1. 确保旧系统MySQL数据库可访问
2. 安装迁移工具依赖：
   ```bash
   pip install mysql-connector-python sqlalchemy pymysql
   ```

### 步骤2：配置连接
创建 `config.ini`：
```ini
[mysql]
host = localhost
port = 3306
database = smarti
username = root
password = root

[sqlite]
database = ../filebot.db

[paths]
file_storage = ../data/files
```

### 步骤3：运行迁移
```bash
# 查看帮助
python migrate.py --help

# 测试连接
python migrate.py --test

# 预览迁移数据（不实际写入）
python migrate.py --dry-run

# 执行完整迁移
python migrate.py --all

# 按表迁移
python migrate.py --table users
python migrate.py --table apps
python migrate.py --table documents
```

### 步骤4：验证数据
1. 记录总数对比
2. 关键字段抽样检查
3. 关联关系验证
4. 文件完整性检查

## 错误处理

### 常见问题
1. **UUID格式不一致**：旧系统使用整数ID，新系统使用UUID
   - 解决方案：使用UUID v5基于旧ID生成确定性的UUID

2. **文件路径不一致**：旧系统文件存储路径不同
   - 解决方案：文件复制或路径映射

3. **数据格式差异**：时间格式、枚举值不同
   - 解决方案：转换函数处理

4. **外键关联断裂**：关联记录不存在
   - 解决方案：创建占位记录或跳过并记录

### 重试机制
- 支持断点续传
- 错误记录到日志文件
- 可重试失败的记录

## 回滚方案

### 情况1：迁移过程中出错
- 删除已迁移的部分数据
- 修复问题后重新迁移

### 情况2：迁移后发现问题
- 保留旧系统数据不变
- 新系统数据可清空重来
- 或编写数据修复脚本

## 性能优化

### 批量处理
- 使用批量插入（每1000条提交一次）
- 关闭SQLite的同步设置（迁移期间）
- 使用事务保证数据一致性

### 内存管理
- 分页读取大表数据
- 及时释放不再使用的对象
- 使用生成器减少内存占用

## 监控和日志

### 日志级别
- INFO：迁移进度、统计信息
- WARNING：数据转换警告
- ERROR：迁移失败错误
- DEBUG：详细数据转换过程

### 进度报告
- 当前迁移表
- 已处理记录数
- 预计剩余时间
- 错误统计

## 后续维护

### 增量迁移
如果新旧系统并行运行，需要增量迁移工具：
- 定时同步新增数据
- 更新修改的数据
- 标记删除的数据

### 数据一致性检查
定期运行数据一致性检查脚本：
- 对比关键表记录数
- 验证关联关系
- 检查文件完整性