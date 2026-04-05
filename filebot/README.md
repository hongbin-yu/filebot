# FileBot - 文档转换与文件管理系统

## 项目概述
FileBot 是一个现代化的 Web 应用程序，用于文件管理和多格式文档统一转换为 PDF。系统替代旧的 smarti 系统，提供更好的用户体验和性能。

## 核心功能
1. **文件管理**
   - 层级结构：App → Drawer → Folder → Document → Page
   - 文件操作：上传、下载、删除、重命名、移动、复制
   - 树状目录导航、批量操作、拖拽上传

2. **文档转换**
   - **输入格式**：TIFF, PDF, Word (.doc/.docx), JPEG, 文本打印流, PCL
   - **输出格式**：统一 PDF
   - 批量转换支持、转换队列管理、进度跟踪

3. **用户管理**
   - 数据库管理的用户系统
   - 角色和权限控制
   - 多用户支持、数据隔离

4. **搜索功能（简化版）**
   - 基于文件名、元数据的搜索
   - 页面级索引搜索（每个页面最多4个索引字段）
   - 不包含复杂的全文内容检索

## 技术栈
- **前端**：React + TypeScript + Vite（现代、组件化、响应式）
- **后端**：Python FastAPI（快速开发、异步支持、文档处理生态丰富）
- **数据库**：SQLite（轻量级、易于部署）
- **文件存储**：本地文件系统 + 配置路径
- **转换引擎**：Python库 + Ghostscript + LibreOffice

## 快速开始

### 1. 系统要求
- Python 3.10+
- Node.js 18+ (前端开发)
- 系统工具：Ghostscript, LibreOffice, Tesseract OCR, ImageMagick

### 2. 一键安装
```bash
# 克隆项目后
cd filebot
chmod +x setup.sh
./setup.sh
```

### 3. 数据迁移准备（从旧系统迁移）
```bash
# 进入迁移目录
cd migration

# 复制配置文件模板
cp config.example.ini config.ini

# 编辑配置文件，设置旧数据库连接
# 支持 Oracle, MS SQL Server, Sybase, HSQLDB, MySQL

# 测试数据库连接
python migrate.py --config config.ini --test

# 查看数据统计
python migrate.py --config config.ini --counts

# 执行全量迁移
python migrate.py --config config.ini --full

# 启动增量迁移（并行运行期间）
python migrate.py --config config.ini --incremental
```

### 3. 手动安装
```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装Python依赖
pip install -r requirements.txt

# 安装系统依赖 (Ubuntu/Debian)
sudo apt-get install ghostscript libreoffice-core tesseract-ocr imagemagick poppler-utils

# 初始化数据库
python -c "from backend.app.db.database import init_db; init_db()"

# 安装前端
cd frontend && npm install && cd ..
```

### 4. 启动服务
```bash
# 启动后端API
uvicorn backend.main:app --reload

# 启动前端 (另一个终端)
cd frontend && npm start
```

### 5. 访问应用
- 前端界面：http://localhost:3000
- 后端API：http://localhost:8000
- API文档：http://localhost:8000/api/docs

### 6. 默认账户
- 用户名：admin
- 密码：admin123
- 邮箱：admin@filebot.com

## 项目结构
```
filebot/
├── backend/           # 后端代码
│   ├── app/          # 应用模块
│   │   ├── models/   # 数据库模型
│   │   ├── routers/  # API路由
│   │   ├── schemas/  # Pydantic模型
│   │   ├── services/ # 业务逻辑
│   │   └── core/     # 核心配置
│   ├── main.py       # 应用入口
│   └── requirements.txt
├── frontend/         # 前端代码 (React)
├── data/             # 数据存储
│   ├── files/        # 上传文件
│   ├── temp/         # 临时文件
│   └── logs/         # 日志文件
├── docs/             # 项目文档
├── docker-compose.yml # Docker部署
└── setup.sh          # 安装脚本
```

## 数据迁移与并行运行

### 迁移策略
FileBot 设计支持从旧系统 (smarti) 平滑迁移：
1. **数据结构兼容**：保持相同层级 (App→Drawer→Folder→Document→Page)
2. **多数据库支持**：Oracle, MS SQL Server, Sybase, HSQLDB, MySQL
3. **增量迁移**：新旧系统可并行运行，定期同步数据
4. **渐进切换**：三个阶段逐步完成迁移

### 并行运行三个阶段
1. **阶段一**：新系统只读 + 旧系统正常（验证期）
2. **阶段二**：逐步切换用户到新系统（过渡期）
3. **阶段三**：完全切换到新系统（完成期）

详细方案见 [PARALLEL_RUNNING.md](PARALLEL_RUNNING.md)

## 开发计划
1. **Phase 1**：基础框架、迁移工具、用户认证
2. **Phase 2**：文件管理核心功能、并行测试
3. **Phase 3**：文档转换引擎、增量迁移验证
4. **Phase 4**：前端界面开发、用户切换
5. **Phase 5**：测试优化、完全切换、部署

## 文档
- [项目要求](requirements.md) - 详细需求规格
- [架构设计](ARCHITECTURE.md) - 系统架构说明
- [项目总结](PROJECT_SUMMARY.md) - 整体设计总结
- [技术调研](tech-research.md) - 技术选型分析
- [并行运行方案](PARALLEL_RUNNING.md) - 新旧系统迁移策略
- [迁移工具](migration/README.md) - 数据迁移详细指南

## 许可证
项目内部使用，待定。