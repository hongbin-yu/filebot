from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, Response
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from pathlib import Path
import logging
import os
import httpx

from app.db.database import get_db, init_db
from app.core.config import settings
from app.core.security import create_first_superuser

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# OAuth2 方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    # 启动时
    logger.info("启动 FileBot 应用...")
    
    # 初始化数据库
    init_db()
    
    # 创建默认超级用户
    db = next(get_db())
    try:
        create_first_superuser(db)
        logger.info("默认用户初始化完成")
    except Exception as e:
        logger.warning(f"创建默认用户时出错: {e}")
    finally:
        db.close()
    
    yield
    
    # 关闭时
    logger.info("关闭 FileBot 应用...")


# 创建FastAPI应用
app = FastAPI(
    title="FileBot API",
    description="Document Management and Conversion System",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|172\.29\.152\.245|10\.0\.0\.\d+|([a-zA-Z0-9-]+\.)*canada\.ca)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint, health check"""
    return {
        "message": "Welcome to FileBot API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/api/health"
    }


@app.get("/api/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    from app.core.config import settings
    from sqlalchemy import text
    import os
    import shutil
    
    # 检查数据库连接
    database_status = "connected"
    try:
        # 执行一个简单的查询来测试数据库连接
        result = db.execute(text("SELECT 1")).fetchone()
        if result and result[0] == 1:
            database_status = "connected"
        else:
            database_status = "disconnected"
            logger.error("数据库查询返回异常结果")
    except Exception as e:
        logger.error(f"数据库连接检查失败: {e}")
        database_status = "disconnected"
    
    # 检查存储路径
    storage_status = {"available": False}
    try:
        # 检查主存储路径
        storage_path = settings.FILE_STORAGE_PATH
        temp_path = settings.TEMP_STORAGE_PATH
        
        # 确保存储目录存在
        os.makedirs(storage_path, exist_ok=True)
        os.makedirs(temp_path, exist_ok=True)
        
        # 检查是否可写
        test_file = os.path.join(temp_path, ".health_check")
        with open(test_file, "w") as f:
            f.write("health check")
        os.remove(test_file)
        
        # 获取磁盘空间信息
        total, used, free = shutil.disk_usage(storage_path)
        
        storage_status = {
            "available": True,
            "free_space": free,
            "total_space": total,
            "used_space": used
        }
    except Exception as e:
        logger.error(f"存储检查失败: {e}")
        storage_status = {"available": False}
    
    # 确定整体状态
    overall_status = "ok"  # 前端期望 'ok'
    if database_status != "connected" or not storage_status["available"]:
        overall_status = "unhealthy"
    
    return {
        "status": overall_status,
        "service": "filebot-api",
        "database": database_status,
        "storage": storage_status
    }


# 导入路由
from app.routers import auth, users, apps, documents, search, conversion, file_naming_rules, device, ai, features, folders, export, pages, import_to_webbot, import_page, track, groups, permissions, groups, permissions, ai_query, mustache, institutions, content
from app.models.institution import Institution  # ensure table is registered before init_db

# 注册路由
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"])
app.include_router(apps.router, prefix=f"{settings.API_V1_STR}/apps", tags=["Apps"])
app.include_router(documents.router, prefix=f"{settings.API_V1_STR}/documents", tags=["Documents"])
app.include_router(pages.router, prefix=f"{settings.API_V1_STR}/pages", tags=["Pages"])
app.include_router(search.router, prefix=f"{settings.API_V1_STR}/search", tags=["Search"])
app.include_router(ai_query.router, prefix=f"{settings.API_V1_STR}", tags=["AI Query"])
app.include_router(conversion.router, prefix=f"{settings.API_V1_STR}/conversion", tags=["Conversion"])
app.include_router(file_naming_rules.router, prefix=f"{settings.API_V1_STR}", tags=["File Naming Rules"])
app.include_router(device.router, prefix=f"{settings.API_V1_STR}/devices", tags=["Device Management"])
app.include_router(ai.router, prefix=f"{settings.API_V1_STR}/ai", tags=["AI Features"])
app.include_router(features.router, prefix=f"{settings.API_V1_STR}/features", tags=["Feature Management"])
app.include_router(folders.router, prefix=f"{settings.API_V1_STR}/folders", tags=["Folders"])
app.include_router(groups.router, prefix=f"{settings.API_V1_STR}/groups", tags=["Groups"])
app.include_router(permissions.router, prefix=f"{settings.API_V1_STR}/permissions", tags=["Permissions"])
app.include_router(export.router, prefix=f"{settings.API_V1_STR}/export", tags=["Export"])
app.include_router(institutions.router, prefix=f"{settings.API_V1_STR}/institutions", tags=["Institutions"])
app.include_router(import_to_webbot.router, prefix=f"{settings.API_V1_STR}", tags=["WebBot"])
app.include_router(import_page.router, prefix=f"{settings.API_V1_STR}", tags=["Import"])
app.include_router(content.router, prefix=f"{settings.API_V1_STR}", tags=["Content"])
app.include_router(track.router)
app.include_router(mustache.router)

# 静态文件服务 - 用于已发布的文档
# 确保静态目录存在
static_path = Path(settings.STATIC_FILES_PATH)
static_path.mkdir(parents=True, exist_ok=True)

# 挂载静态文件服务
app.mount("/static/files", StaticFiles(directory=str(static_path)), name="static_files")
logger.info(f"静态文件服务已挂载: /static/files -> {static_path}")

# Webbot GCWeb 设计文件服务 - /etc/designs -> ../webbot/etc/designs
_designs_path = Path(__file__).resolve().parent.parent.parent / "webbot" / "etc" / "designs"
if _designs_path.exists():
    app.mount("/etc/designs", StaticFiles(directory=str(_designs_path)), name="gcweb_designs")
    logger.info(f"Webbot GCWeb 设计文件已挂载: /etc/designs -> {_designs_path}")
else:
    logger.warning(f"Webbot GCWeb 设计文件目录不存在: {_designs_path}")

# Canada.ca 页面静态代理 — 让 HTML 页面内的 /en/xxx, /fr/xxx, /content/dam/xxx 能正确访问
# 这些页面是从 www.canada.ca 爬取的，内部链接引用网站根路径
_data_base = Path(__file__).resolve().parent / "data" / "boarding" / "canadasite"

_en_path = _data_base / "en"
if _en_path.exists():
    app.mount("/en", StaticFiles(directory=str(_en_path)), name="boarding_en")
    logger.info(f"Boarding 英语页面已挂载: /en -> {_en_path}")
else:
    logger.warning(f"Boarding 英语页面目录不存在: {_en_path}")

_fr_path = _data_base / "fr"
if _fr_path.exists():
    app.mount("/fr", StaticFiles(directory=str(_fr_path)), name="boarding_fr")
    logger.info(f"Boarding 法语页面已挂载: /fr -> {_fr_path}")
else:
    logger.warning(f"Boarding 法语页面目录不存在: {_fr_path}")

# Publish 目录 — 从 webbot 发布的静态 HTML 页面
_publish_path = Path(__file__).resolve().parent / "data" / "publish"
_publish_path.mkdir(parents=True, exist_ok=True)
app.mount("/publish", StaticFiles(directory=str(_publish_path), html=True), name="publish")
logger.info(f"发布目录已挂载: /publish -> {_publish_path}")

_dam_path = _data_base / "content" / "dam"
_dam_path.mkdir(parents=True, exist_ok=True)


class DamProxyASGI:
    """
    自定义 ASGI app：/content/dam/ 代理 + 本地缓存
    1. 检查本地文件，有则直接返回
    2. 没有则从 www.canada.ca 抓取，缓存到本地，然后返回
    """
    def __init__(self, local_path: Path, designs_path: Path | None = None):
        self.local_path = local_path
        self.designs_path = designs_path
        import mimetypes as mt
        mt.init()
        self.mt = mt

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self._send_error(send, 404, "Not Found")
            return

        # scope["path"] 是完整路径（如 /content/dam/government/xxx.jpg）
        # root_path 是 mount 前缀（/content/dam），需要去除以获取相对路径
        path = scope["path"]
        root_path = scope.get("root_path", "")
        
        # 手动去除 root_path 前缀，类似 StaticFiles.get_path 的逻辑
        if root_path and path.startswith(root_path):
            stripped = path[len(root_path):]
        else:
            stripped = path
        rel_path = stripped.lstrip("/")
        local_file = self.local_path / rel_path

        # 特殊处理：/content/dam/etc/designs/... → 从本地 designs 目录提供
        # 有些爬取的页面引用了 /content/dam/etc/designs/ 路径，但实际文件在 /etc/designs/
        if rel_path.startswith("etc/designs/") and self.designs_path:
            designs_file = self.designs_path / rel_path[len("etc/designs/"):]
            if designs_file.exists() and designs_file.is_file():
                return await self._send_file(send, designs_file)

        # 1) 本地命中
        if local_file.exists() and local_file.is_file():
            return await self._send_file(send, local_file)

        # 2) 代理到 Canada.ca 并缓存
        # scope["path"] 已去除 /content/dam 前缀，所以恢复完整路径
        # 恢复完整 /content/dam 路径
        remote_url = f"https://www.canada.ca/content/dam/{rel_path}"
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                resp = await client.get(remote_url)
                if resp.status_code == 200:
                    # 缓存到本地
                    local_file.parent.mkdir(parents=True, exist_ok=True)
                    local_file.write_bytes(resp.content)

                    content_type = resp.headers.get("content-type") or \
                        self.mt.guess_type(str(local_file))[0] or "application/octet-stream"
                    await send({
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [
                            (b"content-type", content_type.encode()),
                            (b"cache-control", b"public, max-age=86400"),
                            (b"x-cache", b"MISS"),
                        ],
                    })
                    await send({
                        "type": "http.response.body",
                        "body": resp.content,
                        "more_body": False,
                    })
                    logger.info(f"🔄 代理缓存: {remote_url} -> {local_file}")
                    return
        except Exception as e:
            logger.error(f"代理失败 {remote_url}: {e}")

        await self._send_error(send, 404, "Not Found")

    async def _send_file(self, send, file_path: Path):
        """Send file content (stream for large files, full send for small files)"""
        content_type = self.mt.guess_type(str(file_path))[0] or "application/octet-stream"
        file_size = file_path.stat().st_size
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", content_type.encode()),
                (b"content-length", str(file_size).encode()),
                (b"cache-control", b"public, max-age=86400"),
                (b"x-cache", b"HIT"),
            ],
        })
        with open(file_path, "rb") as f:
            more = True
            while more:
                chunk = f.read(65536)
                more = len(chunk) == 65536
                await send({
                    "type": "http.response.body",
                    "body": chunk,
                    "more_body": more,
                })

    async def _send_error(self, send, status, message):
        import json
        body = json.dumps({"detail": message}).encode()
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json")],
        })
        await send({
            "type": "http.response.body",
            "body": body,
            "more_body": False,
        })


app.mount("/content/dam", DamProxyASGI(_dam_path, designs_path=_designs_path if _designs_path.exists() else None), name="boarding_dam")
logger.info(f"Boarding 资源代理+缓存已挂载: /content/dam -> {_dam_path} (未命中时自动从 canada.ca 抓取)")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )