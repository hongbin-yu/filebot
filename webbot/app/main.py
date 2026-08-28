"""
WebBot - AI增强的网站内容管理系统
基于FileBot基础设施，提供AI辅助创页、修正、删页、审查功能
"""

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from contextlib import asynccontextmanager
import sqlite3
import os
import mimetypes
import asyncio
import aiohttp
from datetime import datetime

# 导入认证模块（用于中间件保护）
try:
    from .routes.auth_security import decode_access_token, get_user_by_id, get_user_by_username
except ImportError:
    def decode_access_token(token): return None
    def get_user_by_id(uid): return None
    def get_user_by_username(uid): return None

# 导入路由
try:
    from .routes import pages_router, pages_v1_router, ai_router, files_router, components_router, mustache_router, auth_router, search_router, tags_router, analytics_router, versions_router, schedule_router, mail_router, feedback_router, track_router, references_router, translate_router, experiments_router, io_router, COMPONENTS_ENABLED, FILES_ENABLED, MUSTACHE_ENABLED, AUTH_ENABLED, SEARCH_ENABLED, TAGS_ENABLED, ANALYTICS_ENABLED, VERSIONS_ENABLED, SCHEDULE_ENABLED, MAIL_ENABLED, FEEDBACK_ENABLED, TRACK_ENABLED, REFERENCES_ENABLED, TRANSLATE_ENABLED, IO_ENABLED
except ImportError:
    # 备用导入方式
    from routes import pages_router, pages_v1_router, ai_router, files_router, components_router, mustache_router, auth_router, search_router, tags_router, analytics_router, versions_router, schedule_router, mail_router, feedback_router, track_router, references_router, translate_router, experiments_router, io_router, COMPONENTS_ENABLED, FILES_ENABLED, MUSTACHE_ENABLED, AUTH_ENABLED, SEARCH_ENABLED, TAGS_ENABLED, ANALYTICS_ENABLED, VERSIONS_ENABLED, SCHEDULE_ENABLED, MAIL_ENABLED, FEEDBACK_ENABLED, TRACK_ENABLED, REFERENCES_ENABLED, TRANSLATE_ENABLED, IO_ENABLED

# 数据库路径
WEBBOT_DB_PATH = os.environ.get(
    "WEBBOT_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "webbot.db")
)
FILEBOT_DB_PATH = os.environ.get(
    "FILEBOT_DB_PATH",
    "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
)

async def scheduled_publish_loop():
    """定时发布后台任务 — 每分钟检查一次，通过 HTTP 调用自身实现发布"""
    import asyncio

    while True:
        try:
            conn = sqlite3.connect(WEBBOT_DB_PATH)
            conn.row_factory = sqlite3.Row
            now = datetime.utcnow().isoformat()
            cursor = conn.execute(
                "SELECT path FROM webbot_page WHERE scheduled_publish IS NOT NULL "
                "AND scheduled_publish <= ? AND status != 'published'",
                (now,)
            )
            due = [dict(r) for r in cursor.fetchall()]
            conn.close()

            for page in due:
                path = page["path"]
                try:
                    print(f"⏰ Scheduled publish: {path}")
                    # 通过 HTTP 调用内部 publish API
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"http://localhost:8000/api/v1/pages/publish?path={path}",
                            headers={"X-WebBot-Internal": "scheduler"}
                        ) as resp:
                            if resp.status == 200:
                                # 清除定时标记
                                conn2 = sqlite3.connect(WEBBOT_DB_PATH)
                                conn2.execute(
                                    "UPDATE webbot_page SET scheduled_publish = NULL WHERE path = ?",
                                    (path,)
                                )
                                conn2.commit()
                                conn2.close()
                                print(f"✅ Scheduled publish done: {path}")
                            else:
                                err = await resp.text()
                                print(f"⚠️ Scheduled publish failed: {path} HTTP {resp.status}: {err[:200]}")
                except Exception as e:
                    print(f"❌ Scheduled publish error: {path}: {e}")
        except Exception as e:
            print(f"❌ Scheduler loop error: {e}")

        await asyncio.sleep(60)  # 每分钟检查


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    import asyncio
    print("🚀 WebBot启动中...")
    init_database()
    print("✅ 数据库初始化完成")
    # 启动定时发布后台任务
    task = asyncio.create_task(scheduled_publish_loop())
    print("⏰ Scheduled publish checker started (every 60s)")
    yield
    # 关闭时清理
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    print("🛑 WebBot关闭中...")

# 创建FastAPI应用
app = FastAPI(
    title="WebBot API",
    description="Web Content Management System",
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={
        "tryItOutEnabled": True,
        "displayRequestDuration": True,
        "filter": True
    }
)

# 自定义 OpenAPI 模式，添加 bearerAuth security scheme（用于 Swagger UI Authorize 按钮）
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema.setdefault("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/api/v1/auth/login",
                    "scopes": {}
                }
            }
        }
    }
    # 让 Swagger UI 在所有端点上显示 Authorize 按钮
    openapi_schema["security"] = [{"OAuth2PasswordBearer": []}]
    app.openapi_schema = openapi_schema
    return openapi_schema

app.openapi = custom_openapi

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 认证中间件：保护写操作 API 端点 ──────────────────────────────────
EXEMPT_WRITE_PATHS = frozenset([
    "/api/v1/auth/login",
    "/api/v1/auth/filebot-token",
    "/api/v1/track",
    "/api/v1/feedback/submit",
    "/api/v1/feedback/QueueProblemForm",
    "/api/v1/mail/status",
    "/content/upload/",
    "/api/v1/components/health",
    "/api/v1/search/ai-query",
    "/api/v1/search/ai-query/save",
    "/api/v1/pages/lock",
    "/api/v1/pages/unlock",
    "/api/v1/pages/scheduled",
    "/api/v1/pages/approval-status",
    "/api/v1/pages/approve",
    "/api/v1/pages/unapprove",
])

# 前缀豁免：整棵子树放行（demo 数据定位，同 track/feedback 公开写接口）。
# 生产环境如需保护，移除该前缀并给前端接入 token。
EXEMPT_WRITE_PREFIXES = frozenset([
    "/api/v1/experiments",
    "/api/v1/track",
])

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    import json as _json
    from starlette.responses import JSONResponse as _JSONResponse
    from fastapi.responses import Response as _Response

    # 保护写操作 + IO converter 写方法（GET 只读且已有限流/大小上限/SSRF 防护，豁免以便浏览器直测与 mustache datasource 集成）
    if request.method in ("POST", "PUT", "DELETE", "PATCH") or (request.url.path.startswith("/api/v1/io/") and request.method != "GET"):
        path = request.url.path
        # 如果是静态文件请求，放行
        if path.startswith("/static/") or path.startswith("/mustache/") or path.startswith("/gcweb-assets/"):
            pass
        # 检查是否在白名单中
        elif path not in EXEMPT_WRITE_PATHS and not any(path.startswith(p) for p in EXEMPT_WRITE_PREFIXES) and path.startswith("/api/v1/"):
            auth_header = request.headers.get("Authorization", "")
            token = None
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
            # Fall back to filebot_token cookie (HttpOnly, set by FileBot login)
            cookie_token = request.cookies.get("filebot_token")

            # Try Authorization header first, then cookie
            payload = None
            if token:
                payload = decode_access_token(token)
            if not payload and cookie_token:
                payload = decode_access_token(cookie_token)

            if not payload:
                return _JSONResponse(
                    status_code=401,
                    content={"detail": "无效的认证凭据"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

            user_id = payload.get("sub")
            if not user_id:
                return _JSONResponse(
                    status_code=401,
                    content={"detail": "无效的认证凭据"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

            user = get_user_by_id(user_id)
            if not user:
                user = get_user_by_username(user_id)
            if not user:
                return _JSONResponse(
                    status_code=401,
                    content={"detail": "用户不存在"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not user.get("is_active"):
                return _JSONResponse(
                    status_code=403,
                    content={"detail": "用户未激活"},
                )

    response = await call_next(request)
    return response

def get_db_connection():
    """获取WebBot数据库连接"""
    try:
        conn = sqlite3.connect(WEBBOT_DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        raise

def get_filebot_db_connection():
    """获取FileBot只读数据库连接"""
    try:
        conn = sqlite3.connect(FILEBOT_DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
    except sqlite3.Error as e:
        print(f"FileBot DB connection error: {e}")
        return None

def get_all_table_names(conn):
    """Get all user table names from a database connection"""
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [row[0] for row in cursor.fetchall()]

def migrate_webbot_tables():
    """Migrate WebBot-owned tables from filebot.db to webbot.db (one-time)"""
    webbot_tables = ["webbot_page", "webbot_tasks", "webbot_tag", "webbot_page_tag",
                     "component_templates", "component_versions", "component_instances",
                     "ai_configurations", "component_current_versions"]
    
    if not os.path.exists(FILEBOT_DB_PATH):
        return  # No source database to migrate from
    
    try:
        src_conn = sqlite3.connect(FILEBOT_DB_PATH)
        src_conn.row_factory = sqlite3.Row
        src_tables = get_all_table_names(src_conn)
        
        dst_conn = get_db_connection()
        dst_tables = get_all_table_names(dst_conn)
        
        migrated_any = False
        for table in webbot_tables:
            if table in src_tables and table not in dst_tables:
                print(f"📦 Migrating table: {table}")
                # Get CREATE TABLE statement
                cursor = src_conn.execute(
                    f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'"
                )
                row = cursor.fetchone()
                if row and row[0]:
                    dst_conn.execute(row[0])
                
                # Copy all data
                rows = src_conn.execute(f"SELECT * FROM {table}").fetchall()
                if rows:
                    columns = [desc[0] for desc in src_conn.execute(f"SELECT * FROM {table}").description]
                    placeholders = ",".join(["?"] * len(columns))
                    col_names = ",".join(columns)
                    for row_data in rows:
                        dst_conn.execute(
                            f"INSERT OR IGNORE INTO {table} ({col_names}) VALUES ({placeholders})",
                            list(row_data)
                        )
                    print(f"  → Copied {len(rows)} rows")
                
                # Copy indexes
                idx_cursor = src_conn.execute(
                    f"SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='{table}' AND sql IS NOT NULL"
                )
                for idx_row in idx_cursor:
                    try:
                        dst_conn.execute(idx_row[0])
                    except sqlite3.Error:
                        pass  # Index may already exist
                
                migrated_any = True
                dst_conn.commit()
                print(f"✅ Migrated table: {table}")
        
        if not migrated_any:
            print("✓ WebBot tables already up to date")
        
        src_conn.close()
        dst_conn.close()
        
    except sqlite3.Error as e:
        print(f"⚠️  Migration skipped (non-critical): {e}")

def init_database():
    """Initialize WebBot database tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Run migration from filebot.db first (one-time)
        migrate_webbot_tables()
        
        # webbot_page table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='webbot_page'")
        if not cursor.fetchone():
            print("📦 Creating webbot_page table...")
            cursor.execute("""
                CREATE TABLE webbot_page (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT,
                    language TEXT DEFAULT 'en',
                    parent_path TEXT,
                    other_language_path TEXT,
                    status TEXT DEFAULT 'draft',
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_published TIMESTAMP,
                    metadata TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_webbot_page_parent ON webbot_page(parent_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_webbot_page_language ON webbot_page(language)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_webbot_page_status ON webbot_page(status)")
            print("✅ webbot_page table created")
        
        # webbot_tasks table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='webbot_tasks'")
        if not cursor.fetchone():
            print("🤖 Creating webbot_tasks table...")
            cursor.execute("""
                CREATE TABLE webbot_tasks (
                    id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    page_id TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    ai_model TEXT,
                    prompt TEXT,
                    result TEXT,
                    error_message TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
            print("✅ webbot_tasks table created")
        
        # webbot_tag table (for page tagging)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='webbot_tag'")
        if not cursor.fetchone():
            print("🏷️  Creating webbot_tag table...")
            cursor.execute("""
                CREATE TABLE webbot_tag (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    slug TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✅ webbot_tag table created")
        
        # webbot_page_tag table (many-to-many)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='webbot_page_tag'")
        if not cursor.fetchone():
            print("🔗 Creating webbot_page_tag table...")
            cursor.execute("""
                CREATE TABLE webbot_page_tag (
                    page_id TEXT NOT NULL,
                    tag_id TEXT NOT NULL,
                    PRIMARY KEY (page_id, tag_id),
                    FOREIGN KEY (page_id) REFERENCES webbot_page(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES webbot_tag(id) ON DELETE CASCADE
                )
            """)
            print("✅ webbot_page_tag table created")
        
        # webbot_uploaded_files table (disk-based file upload tracking)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='webbot_uploaded_files'")
        if not cursor.fetchone():
            print("📁 Creating webbot_uploaded_files table...")
            cursor.execute("""
                CREATE TABLE webbot_uploaded_files (
                    id TEXT PRIMARY KEY,
                    original_filename TEXT NOT NULL,
                    stored_filename TEXT NOT NULL,
                    folder_path TEXT,
                    file_size INTEGER,
                    mime_type TEXT,
                    file_type TEXT,
                    title TEXT,
                    publish_status TEXT DEFAULT 'draft',
                    document_metadata TEXT,
                    uploaded_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploaded_folder ON webbot_uploaded_files(folder_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploaded_status ON webbot_uploaded_files(publish_status)")
            print("✅ webbot_uploaded_files table created")

        conn.commit()
        conn.close()
        print(f"📊 WebBot database ready at: {WEBBOT_DB_PATH}")
        
    except sqlite3.Error as e:
        print(f"Database init error: {e}")
        raise

# ========== 磁盘上传 - 上传目录 ==========
# 所有通过 /content/upload/ 上传的文件保存在此目录
WEBBOT_UPLOADS_DIR = os.environ.get(
    "WEBBOT_UPLOADS_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "uploads")
)
os.makedirs(WEBBOT_UPLOADS_DIR, exist_ok=True)
print(f"📁 WebBot uploads dir: {WEBBOT_UPLOADS_DIR}")


# 包含路由
if ANALYTICS_ENABLED and analytics_router:
    app.include_router(analytics_router)
    print("✅ Analytics路由已加载 (/api/v1/analytics)")

if VERSIONS_ENABLED and versions_router:
    app.include_router(versions_router)
    print("✅ Versions路由已加载 (/api/v1/versions)")
    
if SCHEDULE_ENABLED:
    app.include_router(schedule_router)
    print("✅ Schedule路由已加载")

# 文件路由
if FILES_ENABLED and files_router:
    app.include_router(files_router)
    print("✅ 文件路由已加载")
else:
    print("⚠️  文件路由未加载")

# 组件路由
if COMPONENTS_ENABLED and components_router:
    app.include_router(components_router)
    print("✅ 组件路由已加载")
else:
    print("⚠️  组件路由未加载")

if MUSTACHE_ENABLED and mustache_router:
    app.include_router(mustache_router)
    print("✅ Mustache渲染路由已加载 (顶级 /mustache/{path})")

if AUTH_ENABLED and auth_router:
    app.include_router(auth_router)

if SEARCH_ENABLED and search_router:
    app.include_router(search_router)

if TAGS_ENABLED and tags_router:
    app.include_router(tags_router)

if MAIL_ENABLED and mail_router:
    app.include_router(mail_router)

if FEEDBACK_ENABLED and feedback_router:
    app.include_router(feedback_router)

if TRACK_ENABLED and track_router:
    app.include_router(track_router)
    print("✅ Tracking路由已加载 (/api/v1/track)")

if REFERENCES_ENABLED and references_router:
    app.include_router(references_router)
    print("✅ References路由已加载 (/api/v1/pages/.../references)")

if TRANSLATE_ENABLED and translate_router:
    app.include_router(translate_router)
    print("✅ Translate路由已加载 (/api/v1/translate)")

app.include_router(experiments_router)
print("✅ Experiments路由已加载 (/api/v1/experiments)")

if IO_ENABLED and io_router:
    app.include_router(io_router)
    print("✅ IO路由已加载 (/api/v1/io/convert — URL→JSON)")

# ==================== CanadaSite 公开页面（/en /fr 动态渲染输出） ====================
# prod.webfilebot.com/en/... → 从数据库(webbot_page)实时渲染，改完立即生效，无需发布
# 渲染复用 _render_preview（与 preview/publish 同一套逻辑）
from .routes.pages import _render_preview  # noqa: E402


def _norm_public_page_path(lang: str, path: str) -> str:
    """/en/xxx.html → /canadasite/en/xxx；/en → /canadasite/en"""
    p = path.strip("/")
    if p.endswith(".html"):
        p = p[:-5]
    return f"/canadasite/{lang}/{p}" if p else f"/canadasite/{lang}"


@app.get("/en", response_model=None)
async def public_page_en_root(request: Request):
    """CanadaSite EN 首页（DB 动态渲染）"""
    return await _render_preview(request, "/canadasite/en", None)


@app.get("/en/{path:path}", response_model=None)
async def public_page_en(request: Request, path: str):
    """CanadaSite EN 子页（DB 动态渲染）"""
    return await _render_preview(request, _norm_public_page_path("en", path), None)


@app.get("/fr", response_model=None)
async def public_page_fr_root(request: Request):
    """CanadaSite FR 首页（DB 动态渲染）"""
    return await _render_preview(request, "/canadasite/fr", None)


@app.get("/fr/{path:path}", response_model=None)
async def public_page_fr(request: Request, path: str):
    """CanadaSite FR 子页（DB 动态渲染）"""
    return await _render_preview(request, _norm_public_page_path("fr", path), None)


# 页面路由（必须最后注册，避免 catch-all 拦截其他路由）
app.include_router(pages_router)
app.include_router(pages_v1_router)
app.include_router(ai_router)

# ==================== FileBot文档代理路由 ====================

# ==================== FileBot文档代理路由 ====================
# 提供/content/dam/路径访问已发布的FileBot文档
# 增强安全性：隐藏FileBot API后端，统一访问控制

import asyncio
import requests
from fastapi.responses import Response
from fastapi import HTTPException

# FileBot PostgreSQL 连接（同机直连，不经过 HTTP）
FILEBOT_PG_URL = os.environ.get(
    "FILEBOT_PG_URL",
    "postgresql://filebot:filebot@localhost:5432/filebot"
)

def _pg_conn():
    """获取 FileBot PostgreSQL 连接（短连接，自动关闭）"""
    import psycopg2
    return psycopg2.connect(FILEBOT_PG_URL, connect_timeout=2)


# 1×1 透明 GIF 占位图（所有方式都失败时返回）
PLACEHOLDER_GIF = (
    b"GIF89a"
    b"\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
    b"!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00"
    b"\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


@app.get("/content/dam/{path:path}")
async def proxy_filebot_document(path: str, thumbnail: bool = False):
    """
    代理访问FileBot文档 — 并发极速模式
    所有URL pattern并发尝试，首次成功即返回，2秒总超时。
    全失败则返回1×1透明GIF（不阻塞页面）。
    """
    if not path.startswith('/'):
        path = '/' + path

    bypass_headers = {"X-WebBot-Access": "true"}
    short_timeout = 2

    # === 优先尝试直接文件系统读取（同机，毫秒级） ===
    # FileBot 数据目录结构：{FILEBOT_DATA}/files/boarding/canadasite/content/dam{path}
    _fb_data = Path("/home/hongb/.openclaw/workspace/filebot/backend/data")
    _fs_candidates = [
        _fb_data / "files" / "boarding" / "canadasite" / "content" / "dam" / path.lstrip("/"),
        _fb_data / "files" / "boarding" / "canada-site" / "content" / "dam" / path.lstrip("/"),
        _fb_data / "files" / path.lstrip("/"),
        _fb_data / path.lstrip("/"),
    ]
    for _fs_path in _fs_candidates:
        if _fs_path.is_file():
            _mime, _ = mimetypes.guess_type(str(_fs_path))
            return FileResponse(
                path=str(_fs_path),
                media_type=_mime or "application/octet-stream",
                headers={"Cache-Control": "public, max-age=86400"}
            )

    # === 第二优先级：PostgreSQL 直查（同机，毫秒级） ===
    # FileBot storage_path 示例：files/boarding/canadasite/content/dam{path}
    # 用 path 列匹配（/content/dam/... 或 /boarding/... 两种格式）
    try:
        _conn = _pg_conn()
        _cur = _conn.cursor()
        # 匹配多种 path 格式
        _like_pattern = f"%/content/dam{path}"
        _cur.execute(
            "SELECT storage_path FROM documents "
            "WHERE path = %s OR path LIKE %s OR path = %s "
            "LIMIT 1",
            (path, _like_pattern, f"/boarding{path}" if not path.startswith("/boarding") else path)
        )
        _row = _cur.fetchone()
        _cur.close()
        _conn.close()
        if _row and _row[0]:
            # storage_path 可能是相对路径（files/boarding/...）或绝对路径
            _sp = _row[0]
            if _sp.startswith("/"):
                _db_path = Path(_sp)
            else:
                # 相对路径：相对于 FILEBOT_DATA_ROOT
                _fb_root = Path("/home/hongb/.openclaw/workspace/filebot/backend/data")
                _db_path = _fb_root / _sp
            if _db_path.is_file():
                _mime, _ = mimetypes.guess_type(str(_db_path))
                return FileResponse(
                    path=str(_db_path),
                    media_type=_mime or "application/octet-stream",
                    headers={"Cache-Control": "public, max-age=86400"}
                )
    except Exception as _pg_err:
        print(f"[proxy_filebot_document] PG query failed: {_pg_err}")

    # === URL 并发尝试 ===
    if thumbnail:
        # 缩略图：优先 FileBot thumbnail API（6ms 命中）
        urls_to_try = [
            f"http://localhost:8001/api/v1/documents/content/dam{path}/thumbnail",
            f"http://localhost:8001/api/v1/documents/by-path/content/dam{path}/thumbnail",
            f"http://localhost:8001/api/v1/documents/boarding/canadasite{path}/thumbnail",
            f"http://localhost:8001/api/v1/documents/boarding/canadasite/content/dam{path}/thumbnail",
            f"http://localhost:8001/content/dam{path}",
            f"https://www.canada.ca/content/dam{path}",
        ]
    else:
        # 全图：优先 FileBot 文档API（by-path 可匹配 content/dam 路径）
        urls_to_try = [
            f"http://localhost:8001/api/v1/documents/by-path/content/dam{path}",
            f"http://localhost:8001/content/dam{path}",
            f"http://localhost:8001/api/v1/documents/by-path/boarding/canadasite{path}",
            f"http://localhost:8001/api/v1/documents/by-path/boarding/canadasite/content/dam{path}",
            f"https://www.canada.ca/content/dam{path}",
        ]

    # 去重
    seen = set()
    unique_urls = [u for u in urls_to_try if u not in seen and not seen.add(u)]

    async def _try_url(url: str):
        """并发尝试一个URL"""
        def _fetch():
            try:
                r = requests.get(url, headers=bypass_headers, timeout=short_timeout)
                return r if r.status_code == 200 else None
            except Exception:
                return None
        return await asyncio.to_thread(_fetch)

    # 并发发起所有请求，最早成功者获胜
    tasks = {asyncio.create_task(_try_url(u)): u for u in unique_urls}
    done, pending = await asyncio.wait(
        tasks.keys(),
        timeout=short_timeout + 0.5,  # 总超时2.5秒
        return_when=asyncio.FIRST_COMPLETED
    )

    # 取消所有未完成的请求
    for p in pending:
        p.cancel()

    # 找第一个成功的响应
    response = None
    for t in done:
        resp = t.result()
        if resp is not None:
            response = resp
            break
    # 取消剩余已完成的（非成功）任务
    for t in done:
        result = t.result()
        if result is not None and result is not response:
            pass  # ignore non-200 responses

    if response is None:
        # 所有方式都失败 → 返回透明占位GIF
        return Response(
            content=PLACEHOLDER_GIF,
            media_type="image/gif",
            status_code=200  # 返回200让浏览器不报错
        )

    content_type = response.headers.get("Content-Type", "application/octet-stream")
    content_data = response.content

    # 缩略图缩放
    if thumbnail and content_type and content_type.startswith("image/"):
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(content_data))
            max_w = 200
            w, h = img.size
            if w > max_w:
                ratio = max_w / float(w)
                new_h = int(h * ratio)
                img = img.resize((max_w, new_h), Image.LANCZOS)
                buf = io.BytesIO()
                fmt = img.format or 'JPEG'
                if fmt.upper() == 'JPEG':
                    img.save(buf, format='JPEG', quality=85, optimize=True)
                else:
                    img.save(buf, format=fmt)
                content_data = buf.getvalue()
        except Exception as e:
            print(f"Thumbnail resize failed for {path}: {e}")

    return Response(content=content_data, media_type=content_type)


# ==================== FileBot上传代理路由 ====================
# 提供/content/upload/路径上传文件到FileBot
# 隐藏FileBot端口8001，统一通过webbot代理上传

# 提供/boarding/路径访问旧版导入的AEM图片（兼容 bookmarklet 导入的图片）
# 这些图片的 Document.path = /boarding/canadasite/...
@app.get("/boarding/{path:path}")
async def proxy_boarding_file(path: str, thumbnail: bool = False):
    """代理/boarding路径到FileBot，兼容旧版bookmarklet导入的图片"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🏠 Boarding proxy request: path=/{path}")
    
    import httpx
    def try_fetch(url):
        try:
            resp = httpx.get(url, timeout=15.0)
            return resp
        except Exception:
            return None
    
    filebot_urls = [
        f"http://localhost:8001/api/v1/documents/by-path/boarding/{path}",
        f"http://localhost:8001/api/v1/documents/by-path/{path}",
        f"http://localhost:8001/content/dam/{path}",
    ]
    
    response = None
    for url in filebot_urls:
        try:
            resp = try_fetch(url)
            if resp and resp.status_code == 200:
                response = resp
                logger.info(f"  ✅ Boarding proxy success from {url}")
                break
        except Exception as e:
            logger.warning(f"  ⚠️  Boarding proxy failed {url}: {e}")
            continue
    
    if not response:
        logger.warning(f"  ❌ Boarding proxy all failed for path=/{path}")
        return Response(status_code=404)
    
    ct = response.headers.get("Content-Type", "application/octet-stream")
    return Response(content=response.content, media_type=ct)



# ========== 磁盘上传 - 辅助函数 ==========

import uuid as _uuid
import shutil
import json as _json

# FileBot 数据根目录（用于存放实际文件）
_FILEBOT_DATA_DIR = Path(os.environ.get(
    "FILEBOT_DATA_DIR",
    "/home/hongb/.openclaw/workspace/filebot/backend/data"
))
_DAM_PROXY_BASE = Path(os.environ.get(
    "DAM_PROXY_BASE",
    "/opt/webfilebot/filebot-backend/data"
))


def _copy_to_dam_proxy(doc: dict):
    """
    Copy published file to the dam proxy directory so /content/dam/ URLs work.
    The dam proxy serves from _DAM_PROXY_BASE / folder_path_lstrip / stored_filename.
    """
    folder_path = doc.get("folder_path", "")
    stored_filename = doc.get("stored_filename", "")
    if not folder_path or not stored_filename:
        return
    
    # Source: _FILEBOT_DATA_DIR / "files" / folder_path[1:] / stored_filename
    rel_dir = folder_path.lstrip("/")
    src = _FILEBOT_DATA_DIR / "files" / rel_dir / stored_filename
    
    # Dest: _DAM_PROXY_BASE / rel_dir / stored_filename
    dst = _DAM_PROXY_BASE / rel_dir / stored_filename
    
    if not src.exists():
        print(f"⚠️  Source file not found for dam copy: {src}")
        return
    
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(dst))
    print(f"📋 Copied to dam proxy: {dst}")


def _get_conn():
    """获取 webbot.db 连接"""
    conn = sqlite3.connect(WEBBOT_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _detect_file_type(mime_type: str, filename: str) -> str:
    """根据 MIME 或扩展名推断文件类型"""
    if mime_type and mime_type.startswith("image/"):
        return "image"
    ext = os.path.splitext(filename)[1].lower()
    image_exts = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".tiff", ".tif"}
    if ext in image_exts:
        return "image"
    video_exts = {".mp4", ".webm", ".avi", ".mov", ".wmv", ".flv", ".mkv"}
    if ext in video_exts:
        return "video"
    audio_exts = {".mp3", ".wav", ".ogg", ".flac", ".aac", ".wma"}
    if ext in audio_exts:
        return "audio"
    doc_exts = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv"}
    if ext in doc_exts:
        return "document"
    return "other"


def _normalize_upload_path(folder_path: str) -> str:
    """规范化上传路径：去掉 /boarding 前缀，清理多余斜杠"""
    p = folder_path
    # 去掉 /boarding 前缀
    if p.startswith("/boarding"):
        p = p[len("/boarding"):]
    # 确保以 / 开头
    if not p.startswith("/"):
        p = "/" + p
    # 去掉末尾斜杠
    p = p.rstrip("/")
    return p


def _save_file_to_disk(temp_path: str, filename: str, folder_path: str) -> str:
    """
    保存文件到 FileBot 数据目录
    返回文件相对路径: files/boarding{normalized_path}/{filename}
    """
    norm_path = _normalize_upload_path(folder_path)
    # 目标路径: data/files/boarding{norm_path}/{filename}
    rel_dir = f"files/boarding{norm_path}"
    abs_dir = _FILEBOT_DATA_DIR / rel_dir
    os.makedirs(abs_dir, exist_ok=True)
    
    # 确保文件名唯一
    dest_path = abs_dir / filename
    if dest_path.exists():
        base, ext = os.path.splitext(filename)
        counter = 1
        while True:
            new_name = f"{base}_{counter}{ext}"
            dest_path = abs_dir / new_name
            if not dest_path.exists():
                break
            counter += 1
    
    shutil.copy2(temp_path, str(dest_path))
    return f"{rel_dir}/{dest_path.name}"


def _ensure_folder_records(pg, folder_path_str: str):
    """
    确保 folder_path_str 对应的所有父文件夹在 FileBot PostgreSQL folders 表中存在。
    递归创建缺失的文件夹记录（从 app 根级开始至最深子文件夹）。

    路径格式: /boarding/canadasite/content/dam/Sample/Financial
    首段为 app slug，之后的每一段均为一个子文件夹。
    """
    if not folder_path_str or not folder_path_str.strip("/"):
        return

    route = folder_path_str.strip("/").split("/")
    if len(route) < 2:
        return

    app_slug = route[0]

    with pg.cursor() as cur:
        # 查找 app 记录
        cur.execute("SELECT id FROM apps WHERE slug = %s", (app_slug,))
        app_row = cur.fetchone()
        if not app_row:
            print(f"[folder-create] App '{app_slug}' not found, skipping")
            return
        app_id = app_row[0]

        parent_path = None
        for i, seg in enumerate(route):
            current_path = "/" + "/".join(route[: i + 1])

            # 跳过已存在的文件夹
            cur.execute("SELECT 1 FROM folders WHERE path = %s", (current_path,))
            if cur.fetchone():
                parent_path = current_path
                continue

            # 创建文件夹记录
            if i == 0:
                # app 根文件夹
                cur.execute(
                    """INSERT INTO folders (path, app_id, name, parent_folder_path,
                       is_system_folder, created_by, updated_by, created_at, updated_at)
                       VALUES (%s, %s, %s, '/', true, 'system', 'system', NOW(), NOW())
                       ON CONFLICT (path) DO NOTHING""",
                    (current_path, app_id, f"{app_slug.capitalize()} Root"),
                )
            else:
                cur.execute(
                    """INSERT INTO folders (path, app_id, name, parent_folder_path,
                       is_system_folder, created_by, updated_by, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, false, 'system', 'system', NOW(), NOW())
                       ON CONFLICT (path) DO NOTHING""",
                    (current_path, app_id, seg, parent_path),
                )

            print(f"[folder-create] Created folder record: {current_path}")
            parent_path = current_path


def _save_file_to_uploads(temp_path: str, filename: str, folder_path: str) -> str:
    """
    保存文件到 webbot 上传目录（备选）
    返回文件在 webbot 上传目录的相对路径
    """
    norm_path = _normalize_upload_path(folder_path) if folder_path else "/"
    abs_dir = Path(WEBBOT_UPLOADS_DIR) / norm_path.lstrip("/")
    os.makedirs(abs_dir, exist_ok=True)
    
    dest_path = abs_dir / filename
    if dest_path.exists():
        base, ext = os.path.splitext(filename)
        counter = 1
        while True:
            new_name = f"{base}_{counter}{ext}"
            dest_path = abs_dir / new_name
            if not dest_path.exists():
                break
            counter += 1
    
    shutil.copy2(temp_path, str(dest_path))
    return str(dest_path.relative_to(Path(WEBBOT_UPLOADS_DIR)))


@app.post("/content/upload/")
async def disk_upload(request: Request):
    """
    磁盘上传：将文件保存到本地磁盘，写入 webbot.db，返回文档信息
    （替换原有的 FileBot API 代理）
    """
    import uuid as _uuid
    import tempfile
    from datetime import datetime
    
    # 解析 multipart form data
    form = await request.form()
    
    # 获取上传文件
    upload_file = None
    for field_name in ("file", "document", "upload"):
        f = form.get(field_name)
        if f and hasattr(f, "filename") and f.filename:
            upload_file = f
            break
    
    if not upload_file:
        return Response(
            content=_json.dumps({"detail": "Missing file"}),
            status_code=400,
            media_type="application/json"
        )
    
    original_filename = upload_file.filename
    title = form.get("title", "") or os.path.splitext(original_filename)[0]
    folder_path = form.get("folder_path", "")
    
    # 读取文件内容到临时文件
    content = await upload_file.read()
    file_size = len(content)
    
    # 生成存储文件名（UUID + 原始扩展名）
    ext = os.path.splitext(original_filename)[1]
    stored_filename = str(_uuid.uuid4()) + ext
    
    # 写入临时文件，再拷贝到目标目录
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    try:
        tmp.write(content)
        tmp.close()
        
        # 尝试保存到 FileBot 数据目录
        storage_rel = None
        try:
            if folder_path:
                storage_rel = _save_file_to_disk(tmp.name, stored_filename, folder_path)
        except Exception as e:
            print(f"⚠️  Failed to save to FileBot data dir: {e}")
        
        # 如果 FileBot 数据目录保存失败，保存到 webbot 上传目录
        if not storage_rel:
            storage_rel = _save_file_to_uploads(tmp.name, stored_filename, folder_path)
    finally:
        os.unlink(tmp.name)
    
    # 确定 MIME 类型
    mime_type, _ = mimetypes.guess_type(original_filename)
    if not mime_type:
        mime_type = "application/octet-stream"
    
    file_type = _detect_file_type(mime_type, original_filename)
    
    # ── 写入 FileBot PostgreSQL ─────────────────────────────────────
    # 图片元数据统一存放在 FileBot 数据库，WebBot 不保留独立 SQLite
    doc_id = str(_uuid.uuid4())
    try:
        _filetype_map = {
            'image/jpeg': 'JPEG', 'image/png': 'PNG', 'image/gif': 'OTHER',
            'image/webp': 'OTHER', 'image/tiff': 'TIFF',
            'application/pdf': 'PDF', 'text/html': 'HTML',
            'application/msword': 'DOC',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
            'text/plain': 'TXT',
        }
        pg_filetype = _filetype_map.get(mime_type, 'OTHER')

        # 构造 FileBot 路径格式：带 /boarding 前缀
        fp = (folder_path or '').strip()
        if fp and not fp.startswith('/boarding'):
            fp = '/boarding' + ('' if fp.startswith('/') else '/') + fp
        pg_folder_path = fp
        pg_path = fp.rstrip('/') + '/' + stored_filename if fp else stored_filename

        # storage_path: 用与 FileBot 一致的绝对路径格式
        pg_storage_path = None
        if storage_rel and storage_rel.startswith('files/'):
            pg_storage_path = str(_FILEBOT_DATA_DIR / storage_rel)

        pg = _pg_conn()
        try:
            # 确保文件夹记录存在（递归创建所有缺失的父文件夹）
            if fp:
                _ensure_folder_records(pg, fp)

            with pg.cursor() as cur:
                cur.execute(
                    """INSERT INTO documents
                       (path, folder_path, title, status, type,
                        original_filename, stored_filename, file_size, file_type,
                        mime_type, uploaded_by, publish_status, storage_path,
                        document_metadata, created_at, updated_at)
                       VALUES (%s, %s, %s, 'ACTIVE', 'GENERAL',
                               %s, %s, %s, %s::filetype,
                               %s, %s, 'UNPUBLISHED'::publishstatus, %s,
                               %s::json, NOW(), NOW())
                       ON CONFLICT (path) DO NOTHING""",
                    (
                        pg_path, pg_folder_path, title,
                        original_filename, stored_filename, file_size, pg_filetype,
                        mime_type, '085e6327-ecfc-4b34-ba4d-7f89e076ed91', pg_storage_path,
                        '{"source": "webbot_upload"}'
                    )
                )
            pg.commit()
            # Copy uploaded file to dam proxy directory so /content/dam/ URLs work immediately
            try:
                _copy_to_dam_proxy({"folder_path": fp, "stored_filename": stored_filename})
            except Exception as dam_e:
                print(f"⚠️  Dam proxy copy failed (non-fatal): {dam_e}")
        except Exception as pg_e:
            print(f"⚠️  Failed to write to FileBot PostgreSQL: {pg_e}")
        finally:
            try:
                pg.close()
            except Exception:
                pass
    except Exception as e:
        print(f"⚠️  PostgreSQL sync failed (non-fatal): {e}")
    
    # 构建响应
    response_data = {
        "id": doc_id,
        "stored_filename": stored_filename,
        "original_filename": original_filename,
        "mime_type": mime_type,
        "file_size": file_size,
        "file_type": file_type,
        "title": title,
        "folder_path": folder_path,
        "publish_status": "draft",
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Also store in webbot_uploaded_files for document lookup by id
    try:
        webbot_conn = _get_conn()
        webbot_conn.execute(
            """INSERT INTO webbot_uploaded_files
               (id, original_filename, stored_filename, folder_path,
                file_size, mime_type, file_type, title, publish_status,
                document_metadata, uploaded_by, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (doc_id, original_filename, stored_filename, folder_path,
             file_size, mime_type, file_type, title,
             "draft",
             _json.dumps({"source": "webbot_upload"}),
             "system",
             datetime.utcnow().isoformat(),
             datetime.utcnow().isoformat())
        )
        webbot_conn.commit()
        webbot_conn.close()
    except Exception as e:
        print(f"⚠️  Failed to store doc in webbot_uploaded_files: {e}")

    return Response(
        content=_json.dumps(response_data),
        status_code=200,
        media_type="application/json"
    )


# ========== 磁盘上传 - 文档操作 ==========

@app.get("/content/documents/")
async def list_documents(
    folder_path: str = None,
    folder_path__like: str = None,
    original_filename__like: str = None,
    title__like: str = None,
    ai_category: str = None,
    ai_tag: str = None,
    limit: int = 50,
    offset: int = 0
):
    """列出上传的文档（查询 FileBot PostgreSQL）"""
    pg = None
    cur = None
    try:
        pg = _pg_conn()
        cur = pg.cursor()
        
        where_clauses = []
        params = []
        
        if folder_path:
            fp = _normalize_upload_path(folder_path)
            if fp.startswith("/"):
                fp = "/boarding" + fp
            else:
                fp = "/boarding/" + fp
            where_clauses.append("folder_path = %s")
            params.append(fp)
        if folder_path__like:
            fp = _normalize_upload_path(folder_path__like)
            if fp.startswith("/"):
                fp = "/boarding" + fp
            else:
                fp = "/boarding/" + fp
            where_clauses.append("folder_path LIKE %s")
            params.append(fp)
        if original_filename__like:
            where_clauses.append("original_filename ILIKE %s")
            params.append('%' + original_filename__like + '%')
        if title__like:
            where_clauses.append("title ILIKE %s")
            params.append('%' + title__like + '%')
        if ai_category:
            where_clauses.append("ai_category ILIKE %s")
            params.append('%' + ai_category + '%')
        if ai_tag:
            # ai_tags column is JSON array like [{"tag": "contract", "score": 0.98}, ...]
            # json_typeof check avoids errors on NULL or scalar ai_tags values
            where_clauses.append("path IN (SELECT path FROM documents d2, json_array_elements(d2.ai_tags) elem WHERE elem->>'tag' = %s AND json_typeof(d2.ai_tags) = 'array')")
            params.append(ai_tag)
        
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # 先查数据
        cur.execute(
            f"SELECT * FROM documents {where_sql} ORDER BY created_at DESC LIMIT %s OFFSET %s",
            params + [limit, offset]
        )
        rows = cur.fetchall()
        col_names = [desc[0] for desc in cur.description]
        
        # 再查总数（在另一个 cursor 上，避免覆盖 col_names）
        cur2 = pg.cursor()
        cur2.execute(
            f"SELECT COUNT(*) FROM documents {where_sql}",
            params
        )
        total = cur2.fetchone()[0]
        cur2.close()
        _data_root = str(_FILEBOT_DATA_DIR) + "/"
        documents = []
        for row in rows:
            d = dict(zip(col_names, row))
            # Map fields to match frontend expectations
            fp = d.get("folder_path", "") or ""
            sf = d.get("stored_filename", "") or ""
            if fp and sf:
                d["storage_path"] = fp.rstrip("/") + "/" + sf
            else:
                d["storage_path"] = sf or ""
            d["thumbnail_status"] = d.get("thumbnail_status") or None
            documents.append(d)
        
        return {
            "documents": documents,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        print(f"⚠️  list_documents PG query failed: {e}")
        return {"documents": [], "total": 0, "limit": limit, "offset": offset, "error": str(e)}
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            pg.close()
        except Exception:
            pass


@app.get("/content/documents/{doc_id}")
async def get_document(doc_id: str):
    """获取单个文档"""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT * FROM webbot_uploaded_files WHERE id = ?",
            (doc_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Document not found")
        d = dict(row)
        if d.get("document_metadata"):
            try:
                d["document_metadata"] = _json.loads(d["document_metadata"])
            except (_json.JSONDecodeError, TypeError):
                pass
        return d
    finally:
        conn.close()


@app.put("/content/documents/{doc_id}")
async def update_document(doc_id: str, request: Request):
    """更新文档（发布、修改元数据等）"""
    body = await request.json()
    conn = _get_conn()
    try:
        # Check if document exists
        cursor = conn.execute(
            "SELECT * FROM webbot_uploaded_files WHERE id = ?",
            (doc_id,)
        )
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Build updates
        updates = []
        params = []
        
        if "publish_status" in body:
            updates.append("publish_status = ?")
            params.append(body["publish_status"])
        if "title" in body:
            updates.append("title = ?")
            params.append(body["title"])
        if "document_metadata" in body:
            updates.append("document_metadata = ?")
            params.append(_json.dumps(body["document_metadata"]))
        
        if updates:
            from datetime import datetime
            updates.append("updated_at = ?")
            params.append(datetime.utcnow().isoformat())
            params.append(doc_id)
            
            conn.execute(
                f"UPDATE webbot_uploaded_files SET {', '.join(updates)} WHERE id = ?",
                params
            )
            conn.commit()
            
            # Sync publish_status to FileBot PostgreSQL
            if "publish_status" in body:
                try:
                    pg = _pg_conn()
                    with pg.cursor() as pg_cur:
                        pg_cur.execute(
                            "UPDATE documents SET publish_status = %s::publishstatus, updated_at = NOW() WHERE stored_filename = %s",
                            (body["publish_status"], existing["stored_filename"])
                        )
                    pg.commit()
                    pg.close()
                except Exception as pg_e:
                    print(f"⚠️  Failed to sync publish_status to PostgreSQL: {pg_e}")
                
                # Copy file to dam proxy directory for /content/dam/ serving
                if body["publish_status"].upper() == "PUBLISHED":
                    _copy_to_dam_proxy(dict(existing))
        
        # Return updated document
        cursor = conn.execute(
            "SELECT * FROM webbot_uploaded_files WHERE id = ?",
            (doc_id,)
        )
        d = dict(cursor.fetchone())
        if d.get("document_metadata"):
            try:
                d["document_metadata"] = _json.loads(d["document_metadata"])
            except (_json.JSONDecodeError, TypeError):
                pass
        return d
    finally:
        conn.close()


@app.get("/content/documents/{doc_id}/download")
async def download_document(doc_id: str):
    """下载文档文件"""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT * FROM webbot_uploaded_files WHERE id = ?",
            (doc_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc = dict(row)
        folder_path = doc.get("folder_path", "")
        stored_filename = doc.get("stored_filename", "")
        original_filename = doc.get("original_filename", stored_filename)
        mime_type = doc.get("mime_type", "application/octet-stream")
        
        # Try FileBot data dir first
        if folder_path:
            norm_path = _normalize_upload_path(folder_path)
            fb_path = _FILEBOT_DATA_DIR / "files" / "boarding" / norm_path.lstrip("/") / stored_filename
            if fb_path.is_file():
                return FileResponse(
                    path=str(fb_path),
                    media_type=mime_type,
                    filename=original_filename
                )
        
        # Try webbot uploads dir
        if folder_path:
            norm_path = _normalize_upload_path(folder_path)
            wb_path = Path(WEBBOT_UPLOADS_DIR) / norm_path.lstrip("/") / stored_filename
            if wb_path.is_file():
                return FileResponse(
                    path=str(wb_path),
                    media_type=mime_type,
                    filename=original_filename
                )
        
        # Try direct path
        for base in [_FILEBOT_DATA_DIR, Path(WEBBOT_UPLOADS_DIR)]:
            candidate = base / stored_filename
            if candidate.is_file():
                return FileResponse(
                    path=str(candidate),
                    media_type=mime_type,
                    filename=original_filename
                )
        
        raise HTTPException(status_code=404, detail="File not found on disk")
    finally:
        conn.close()


# ========== AI Q&A Proxy (port 8001) ==========

@app.post("/api/v1/search/ai-query")
@app.post("/api/v1/search/ai-query/save")
async def proxy_ai_query(request: Request):
    """
    Proxy AI query requests to FileBot port 8001.
    Forwarded endpoints:
      POST /api/v1/search/ai-query       - Generate answer
      POST /api/v1/search/ai-query/save   - Save Q&A page
    """
    body = await request.body()
    auth = request.headers.get("authorization", "")
    target_path = request.url.path
    
    target_url = f"http://localhost:8001{target_path}"
    if request.url.query:
        target_url += "?" + request.url.query
    
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = auth
    headers["X-WebBot-Access"] = "true"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(target_url, data=body, headers=headers, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                resp_body = await resp.read()
                resp_headers = {k: v for k, v in resp.headers.items()
                               if k.lower() not in ("transfer-encoding", "content-encoding", "content-length")}
                return Response(
                    content=resp_body,
                    status_code=resp.status,
                    media_type=resp.content_type,
                    headers=resp_headers
                )
    except aiohttp.ClientConnectorError:
        raise HTTPException(status_code=503, detail="Cannot connect to AI query service (port 8001)")
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="AI query timed out (Ollama may be overloaded)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI query proxy failed: {str(e)}")


# 添加静态文件服务（前端界面）
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    # 添加编辑器路径路由（在静态文件服务之前）
    @app.get("/static/editor.html")
    async def serve_editor():
        """提供编辑器页面（无路径参数）"""
        from fastapi.responses import FileResponse
        import os
        editor_path = os.path.join(frontend_dir, "editor.html")
        if os.path.exists(editor_path):
            return FileResponse(editor_path, media_type="text/html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
        else:
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": "Editor file not found"}, status_code=404)
    
    @app.get("/static/editor.html/{path:path}")
    async def serve_editor_with_path(path: str = ""):
        """
        提供带有路径参数的编辑器页面
        格式: /static/editor.html/en/contact → 返回编辑器页面，前端JS会处理路径
        """
        from fastapi.responses import FileResponse
        import os
        
        # 返回编辑器HTML文件
        editor_path = os.path.join(frontend_dir, "editor.html")
        if os.path.exists(editor_path):
            return FileResponse(editor_path, media_type="text/html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
        else:
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": "Editor file not found"}, status_code=404)

    @app.get("/static/analybot.html")
    async def serve_analybot_live(
        experiment_id: str = "exp-testpage",
        title: str = "AnalyBot - Live A/B Experiment Dashboard",
        subtitle: str = "Live A/B Testing &amp; Analytics · real beacon data",
        api_base: str = "/api/v1/experiments",
        stats_base: str = "/api/v1/track/ab/stats",
        poll_interval: int = 10000,
        show_mock: str = "true",
    ):
        """
        Real-data AnalyBot dashboard rendered from a Mustache template.
        All parameters overridable via query string, e.g.
        /static/analybot.html?experiment_id=exp-passport-cta&poll_interval=5000&show_mock=false
        """
        import pystache
        from fastapi.responses import HTMLResponse
        tpl_path = os.path.join(frontend_dir, "analybot-live.mustache")
        if not os.path.exists(tpl_path):
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": "AnalyBot template not found"}, status_code=404)
        with open(tpl_path, "r", encoding="utf-8") as f:
            tpl = f.read()
        html = pystache.render(tpl, {
            "experiment_id": experiment_id,
            "title": title,
            "subtitle": subtitle,
            "api_base": api_base,
            "stats_base": stats_base,
            "poll_interval": poll_interval,
            "show_mock": "true" if str(show_mock).lower() in ("1", "true", "yes") else "false",
        })
        return HTMLResponse(html, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    
    app.mount("/static", StaticFiles(directory=frontend_dir, html=True), name="static")
    print(f"📁 静态文件目录: {frontend_dir}")
else:
    print(f"⚠️  前端目录不存在: {frontend_dir}")

# 添加GCWeb/WET-BOEW静态文件服务 (加拿大政府网站标准)
gcweb_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(gcweb_dir):
    app.mount("/gcweb", StaticFiles(directory=gcweb_dir, html=True), name="gcweb")
    print(f"📁 GCWeb静态文件目录: {gcweb_dir}")
else:
    print(f"⚠️  GCWeb目录不存在: {gcweb_dir}")

# 添加/etc/designs静态文件服务 (Canada.ca WET主题路径)
# 指向nginx同源目录 /var/www/canada-designs/
etc_designs_dir = "/var/www/canada-designs"
if os.path.exists(etc_designs_dir):
    app.mount("/etc/designs", StaticFiles(directory=etc_designs_dir, html=True), name="etc-designs")
    print(f"📁 /etc/designs 静态文件目录: {etc_designs_dir}")
else:
    print(f"⚠️ /etc/designs 目录不存在: {etc_designs_dir}")

# 添加site/目录静态文件服务 (指向FileBot publish目录)
FILEBOT_PUBLISH_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "filebot",
    "backend",
    "data",
    "publish"
)
os.makedirs(FILEBOT_PUBLISH_DIR, exist_ok=True)
app.mount("/site", StaticFiles(directory=FILEBOT_PUBLISH_DIR, html=True), name="site")
app.mount("/publish", StaticFiles(directory=FILEBOT_PUBLISH_DIR, html=True), name="publish")
print(f"📁 发布站点目录 (FileBot): {FILEBOT_PUBLISH_DIR}")

@app.get("/")
async def root():
    """根端点，重定向到前端界面或返回API信息"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/navigation.html")


@app.get("/editor.html")
async def editor_redirect():
    """重定向 /editor.html 到 /static/editor.html 以保持向后兼容性"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/editor.html")


@app.get("/filebot-picker.html")
async def filebot_picker_redirect():
    """重定向 /filebot-picker.html 到 /static/filebot-picker.html 以保持向后兼容性"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/filebot-picker.html")

@app.get("/frontend/auto-token.html")
async def auto_token_redirect():
    """重定向 /frontend/auto-token.html 到 /static/auto-token.html"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/auto-token.html")

@app.get("/frontend/{filename}")
async def frontend_file_redirect(filename: str):
    """重定向 /frontend/{filename} 到 /static/{filename}"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/static/{filename}")


@app.get("/api/v1/export-folder")
async def export_folder(path: str = "/canadasite", depth: int = Query(1, ge=1, le=20)):
    """
    导出指定文件夹下的页面，支持深度控制。
    depth=1 仅当前路径，depth=2 包含直接子页，以此类推。
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    export_path = path.rstrip('/')
    if not export_path:
        export_path = '/'
    if not export_path.startswith('/'):
        export_path = '/' + export_path

    cursor.execute("""
        SELECT id, parent_path, path, title, language, description, keywords,
               content, status, metadata, hide_in_navigation, other_language_path
        FROM webbot_page
        ORDER BY path
    """)
    all_pages = cursor.fetchall()
    conn.close()

    base_parts = export_path.strip('/').split('/') if export_path != '/' else []
    base_depth = len(base_parts)

    result = []
    for page in all_pages:
        page_path = page['path']
        page_parts = page_path.strip('/').split('/')

        if page_path == export_path:
            result.append(dict(page))
        elif page_path.startswith(export_path + '/'):
            additional_levels = len(page_parts) - base_depth
            if additional_levels <= depth - 1:
                result.append(dict(page))

    return {
        "path": export_path,
        "depth": depth,
        "total": len(result),
        "pages": result
    }


@app.get("/api")
async def api_info():
    """API信息端点"""
    return {
        "name": "WebBot API",
        "version": "1.0.0",
        "description": "AI增强的网站内容管理系统",
        "status": "running",
        "database": "connected" if os.path.exists(WEBBOT_DB_PATH) else "not_found",
        "endpoints": {
            "pages": "/api/v1/pages",
            "ai_tasks": "/api/v1/ai/tasks",
            "ai_create": "/api/v1/ai/create-page",
            "ai_optimize": "/api/v1/ai/optimize-page",
            "ai_review": "/api/v1/ai/review-page",
            "ai_delete": "/api/v1/ai/suggest-deletion",
            "files": "/api/v1/files" if FILES_ENABLED else "disabled",
            "components": "/api/v1/components" if COMPONENTS_ENABLED else "disabled",
            "mail": "/api/v1/mail" if MAIL_ENABLED else "disabled",
            "feedback": "/api/v1/feedback" if FEEDBACK_ENABLED else "disabled"
        }
    }

@app.get("/favicon.ico")
async def favicon():
    """返回一个空favicon以避免404错误"""
    from fastapi.responses import Response
    return Response(content=b"", media_type="image/x-icon")

@app.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    print("🌐 启动WebBot服务器...")
    print(f"📁 WebBot数据库路径: {WEBBOT_DB_PATH}")
    print("🔗 API地址: http://localhost:8000")
    print("📚 API文档: http://localhost:8000/docs")
    print("🤖 AI功能: 创页、修正、审查、删除建议")
    uvicorn.run(app, host="0.0.0.0", port=8000)
# GCWeb组件资产静态文件服务
import os as _os
from fastapi.responses import FileResponse as _FileResponse, Response as _Response

gcweb_components_dir = _os.path.normpath(_os.path.join(_os.path.dirname(__file__), "..", "GCWeb"))
if _os.path.exists(gcweb_components_dir):
    @app.get("/gcweb-assets/{path:path}")
    async def serve_gcweb_assets(path: str):
        full_path = _os.path.normpath(_os.path.join(gcweb_components_dir, path))
        if full_path.startswith(gcweb_components_dir) and _os.path.exists(full_path) and _os.path.isfile(full_path):
            return _FileResponse(full_path)
        return _Response(status_code=404)
    print(f"📁 GCWeb组件资产目录: {gcweb_components_dir}")
else:
    print(f"⚠️  GCWeb组件目录不存在: {gcweb_components_dir}")
