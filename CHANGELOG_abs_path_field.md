# 改动交接文档 — abs_path 字段（给码农 / dev 环境）

> 时间：2026-09-16 UTC
> 生产已改并验证通过。dev 环境需按本文同步。改动最小、纯增量，不影响既有功能。

---

## 一、改动原因（背景）

之前 `import-url` / 页面导入图片时，`Document.path` 被写成了**内部完整路径**
`/boarding/canadasite/content/dam/...`（含 app slug `boarding` + site `canadasite`）。

但 `path` 字段在系统里**到处都被引用**（主键、前端展示、HTML `<img src>`、
发布逻辑等），一旦带上前缀，发布时又得用 `p.find('/content')` 这种脆弱方式去剥前缀。

老板定案（最小改动方案）：
- **`path` 保持不变**，继续存**公开相对路径** `/content/dam/...`
- **新增 `abs_path` 字段**，专门记录**内部完整路径** `/boarding/canadasite/content/dam/...`
- `folder_path` 仍指向**内部树** `/boarding/canadasite/content/dam/...`（boarding 应用里可浏览）

这样新加字段完全不影响原有功能，发布逻辑也无需再剥前缀（`path` 本身就是公开路径）。

---

## 二、字段语义（务必记牢，别弄反）

| 字段 | 含义 | 示例值 |
|---|---|---|
| `path`（主键，公开，到处用） | 公开相对路径 | `/content/dam/fr/xxx/yyy.png` |
| `abs_path`（**新增**，内部完整路径） | 含 app+site 前缀 | `/boarding/canadasite/content/dam/fr/xxx/yyy.png` |
| `folder_path`（FK→folders，浏览树） | 内部树父目录 | `/boarding/canadasite/content/dam/fr/xxx` |
| `storage_path` | 物理相对路径（相对 DATA_ROOT） | `boarding/canadasite/content/dam/fr/xxx/yyy.png` |

### 代码内变量对应关系（`import_page.py`）
- `doc_path` = `/content/dam/...`（公开，赋给 `Document.path`）
- `db_path` = `"/boarding/canadasite" + doc_path`（内部，赋给 `abs_path` 和 `folder_path` 的父级）
- `storage_rel` = `db_path.lstrip('/')` = `boarding/canadasite/...`（物理相对路径）
- `folder_path` = `Path(db_path).parent`（内部树）

---

## 三、改动位置（共 3 个文件 + 1 条 DB 迁移）

### 1. 模型 `app/models/document.py`（第 80-81 行）
```python
# path 即主键（公开相对路径 /content/dam/...）
path = Column(String(500), primary_key=True)
# abs_path：内部完整路径（含 app+site 前缀 /boarding/canadasite/content/dam/...）
abs_path = Column(String(500), nullable=True, index=True)
folder_path = Column(String(500), ForeignKey("folders.path"), nullable=False, index=True)
```

### 2. 响应 Schema `app/schemas/document.py`（第 143 行）
在 `DocumentResponse` 里加：
```python
abs_path: Optional[str] = None  # 内部完整路径（/boarding/canadasite/content/dam/...）
```

### 3. 导入写入逻辑 `app/routers/import_page.py`
核心改动在 `download_and_store_dam_images()` 函数：

- **第 309 行**：`db_path = "/boarding/canadasite" + doc_path`（内部路径变量，保持不变）
- **第 478 行**：已存在查找改用公开主键
  `db.query(Document).filter(Document.path == doc_path)`（原来是 `== db_path`）
- **第 482 行**（更新已存在行）：`existing_doc.abs_path = db_path`
- **第 503-504 行**（新建行）：
  ```python
  doc = Document(
      path=doc_path,      # 公开路径
      abs_path=db_path,   # 内部完整路径（新增）
      folder_path=folder_path,   # 内部树
      ...
  )
  ```

> 注意：`folder_path`、`storage_rel`、物理文件写入路径、`_ensure_dam_folder_chain`
> 这些**保持不变**，仍用 `db_path`（内部树/内部物理路径），只有 `Document.path`
> 从 `db_path` 改回 `doc_path`，并额外写入 `abs_path = db_path`。

### 4. 数据库迁移（PostgreSQL，docker `wb-postgres`）
```sql
ALTER TABLE documents ADD COLUMN IF NOT EXISTS abs_path varchar(500);
CREATE INDEX IF NOT EXISTS idx_documents_abs_path ON documents(abs_path);
```

### 5. 存量数据回填（生产已执行，dev 环境也需执行）
```sql
-- /content/dam/...（公开路径，缺前缀）→ 加 /boarding/canadasite 前缀
-- 其余已是内部路径 → 原样
UPDATE documents
SET abs_path = CASE
    WHEN path LIKE '/content/dam/%' THEN '/boarding/canadasite' || path
    ELSE path
END
WHERE abs_path IS NULL;
```

---

## 四、发布逻辑（无需改动）

`app/core/path_utils.py` 的 `get_publish_relative_path()` 通过查找 `/content` 截取公开路径。
现在 `path` 本身就是 `/content/dam/...`，所以直接返回 `content/dam/...`，
**无需再剥 `/boarding/canadasite` 前缀**。

---

## 五、dev 环境同步清单

- [ ] 合并 `document.py`、`schemas/document.py`、`routers/import_page.py` 三个文件的改动
- [ ] 执行 `ALTER TABLE ... ADD COLUMN abs_path` + 建索引
- [ ] 执行回填 SQL（dev 有测试数据就回填）
- [ ] 重启后端，验证 `/api/health` 正常
- [ ] 导入一张测试图片，核对 `path`、`abs_path`、`folder_path` 三个字段值符合上表

---

## 六、仍未决（待老板拍板，勿擅自改）

1. **存量数据迁移（Step 2）**：现有 16,459 条 `/content/dam/` 旧行的 `folder_path`
   仍指向公开树 `/content/dam/...`，需迁到内部树 `/boarding/canadasite/...`；
   其中 15,122 条是重复（同图已有正确前缀行），需去重删除。**有删除动作，等确认。**
2. **数据根分裂**：`main.py` 的 DamProxy `_data_base` 硬编码
   `__file__/data/boarding/canadasite`，与 systemd 环境变量 `DATA_ROOT=/opt/webfilebot/data`
   不一致，导致图片写入位置与服务位置分裂（404 根因之一）。仍未决。
