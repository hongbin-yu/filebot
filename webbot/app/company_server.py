"""
公司网站静态服务器 (port 8004)
独立于 Canada.ca publish_server，专门服务于 webfilebot.com 公司页面
"""
import os
import sys
import logging
from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse
from starlette.middleware.cors import CORSMiddleware
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("company-server")

# 网站根目录
SITE_DIR = Path(__file__).resolve().parent.parent / "static" / "site"
STATIC_DIR = SITE_DIR.resolve()

if not STATIC_DIR.exists():
    logger.warning(f"Site directory not found, creating: {STATIC_DIR}")
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

logger.info(f"Company site directory: {STATIC_DIR}")

# 静态文件服务（html=True 自动提供 index.html）
# Canada.ca 设计资源（/etc/designs/canada/ 由当前服务器直接提供，
# 因为 Cloudflare tunnel 将 www.webfilebot.com 直接路由到本端口 8004，绕过 nginx）
CANADA_DESIGNS_DIR = "/var/www/canada-designs/canada"
routes = [
    Mount("/etc/designs/canada", app=StaticFiles(directory=CANADA_DESIGNS_DIR), name="canada-designs"),
    Mount("/", app=StaticFiles(directory=str(STATIC_DIR), html=True), name="company-site"),
]

app = Starlette(
    routes=routes,
    on_startup=[lambda: logger.info("Company site server started on port 8004")],
)

# CORS — 允许任何域名加载静态资源（字体/CSS/JS），
# 这样 cdn.webfilebot.com 和 prod.webfilebot.com 都能跨域引用字体文件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Content-Length", "Cache-Control", "ETag", "Last-Modified"],
)

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8004
    logger.info(f"Starting company site server on port {port}")
    uvicorn.run("company_server:app", host="0.0.0.0", port=port, log_level="info")
