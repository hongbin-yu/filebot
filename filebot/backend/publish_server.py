"""
独立发布服务器
在独立端口上直接提供 publish 目录的文件访问。
默认端口：8003

访问示例：
  http://localhost:8003/en/canadian-heritage.html
  http://localhost:8003/content/dam/pch/images/ministers/marc-miller.jpg
  http://localhost:8003/etc/designs/canada/wet-boew/assets/sig-blk-en.svg
"""
import os
import sys
import logging
from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
from starlette.responses import PlainTextResponse
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("publish-server")

# Publish directory
PUBLISH_DIR = Path(__file__).parent / "data" / "publish"
PUBLISH_DIR = PUBLISH_DIR.resolve()

if not PUBLISH_DIR.exists() or not PUBLISH_DIR.is_dir():
    logger.error(f"Publish directory not found: {PUBLISH_DIR}")
    sys.exit(1)

logger.info(f"Publish directory: {PUBLISH_DIR}")


async def index(request):
    """Root page - show list of published pages"""
    html_pages = sorted(PUBLISH_DIR.rglob("*.html"))
    links = []
    for page in html_pages:
        rel = page.relative_to(PUBLISH_DIR)
        links.append(f'<li><a href="/{rel}">/{rel}</a> ({page.stat().st_size} bytes)</li>')

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Published Pages</title>
<style>body{{font-family:sans-serif;margin:2em}} a{{color:#c4390d}} li{{margin:0.3em 0}}</style>
</head>
<body>
<h1>📄 Published Pages</h1>
<p>{len(html_pages)} pages · <a href="/content/dam/">/content/dam</a></p>
<ul>{"".join(links)}</ul>
</body></html>"""
    return PlainTextResponse(html, media_type="text/html")


routes = [
    # Serve publish directory at root level
    Mount("/", app=StaticFiles(directory=str(PUBLISH_DIR), html=True), name="publish"),
]

app = Starlette(
    routes=routes,
    on_startup=[lambda: logger.info("Publish server started")],
)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8003
    logger.info(f"Starting publish server on port {port}")
    uvicorn.run("publish_server:app", host="0.0.0.0", port=port, log_level="info")
