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
from datetime import datetime

# 导入认证模块（用于中间件保护）
try:
    from .routes.auth_security import decode_access_token, get_user_by_id
except ImportError:
    def decode_access_token(token): return None
    def get_user_by_id(uid): return None

# 导入路由
try:
    from .routes import pages_router, pages_v1_router, ai_router, files_router, components_router, mustache_router, auth_router, search_router, tags_router, analytics_router, versions_router, schedule_router, mail_router, feedback_router, track_router, references_router, translate_router, COMPONENTS_ENABLED, FILES_ENABLED, MUSTACHE_ENABLED, AUTH_ENABLED, SEARCH_ENABLED, TAGS_ENABLED, ANALYTICS_ENABLED, VERSIONS_ENABLED, SCHEDULE_ENABLED, MAIL_ENABLED, FEEDBACK_ENABLED, TRACK_ENABLED, REFERENCES_ENABLED, TRANSLATE_ENABLED
except ImportError:
    # 备用导入方式
    from routes import pages_router, pages_v1_router, ai_router, files_router, components_router, mustache_router, auth_router, search_router, tags_router, analytics_router, versions_router, schedule_router, mail_router, feedback_router, track_router, references_router, translate_router, COMPONENTS_ENABLED, FILES_ENABLED, MUSTACHE_ENABLED, AUTH_ENABLED, SEARCH_ENABLED, TAGS_ENABLED, ANALYTICS_ENABLED, VERSIONS_ENABLED, SCHEDULE_ENABLED, MAIL_ENABLED, FEEDBACK_ENABLED, TRACK_ENABLED, REFERENCES_ENABLED, TRANSLATE_ENABLED

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
])

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    import json as _json
    from starlette.responses import JSONResponse as _JSONResponse
    from fastapi.responses import Response as _Response

    # 只保护写操作（POST/PUT/DELETE/PATCH）
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        path = request.url.path
        # 如果是静态文件请求，放行
        if path.startswith("/static/") or path.startswith("/mustache/") or path.startswith("/gcweb-assets/"):
            pass
        # 检查是否在白名单中
        elif path not in EXEMPT_WRITE_PATHS and path.startswith("/api/v1/"):
            auth_header = request.headers.get("Authorization", "")
            token = None
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]

            if not token:
                return _JSONResponse(
                    status_code=401,
                    content={"detail": "需要登录认证"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

            payload = decode_access_token(token)
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
        
        conn.commit()
        conn.close()
        print(f"📊 WebBot database ready at: {WEBBOT_DB_PATH}")
        
    except sqlite3.Error as e:
        print(f"Database init error: {e}")
        raise

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


import aiohttp

@app.post("/content/upload/")
async def proxy_filebot_upload(request: Request):
    """
    代理上传文件到FileBot
    前端POST multipart/form-data → /content/upload/ → 转发到 → FileBot /documents/upload/
    """
    body = await request.body()
    content_type = request.headers.get("content-type", "")
    auth_header = request.headers.get("authorization", "")
    
    fb_headers = {
        "Content-Type": content_type,
        "X-WebBot-Access": "true",
    }
    if auth_header:
        fb_headers["Authorization"] = auth_header
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8001/api/v1/documents/upload/",
                data=body,
                headers=fb_headers
            ) as resp:
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
        raise HTTPException(status_code=503, detail="无法连接到FileBot服务")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传代理失败: {str(e)}")


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
etc_designs_dir = os.path.join(os.path.dirname(__file__), "..", "etc", "designs")
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
