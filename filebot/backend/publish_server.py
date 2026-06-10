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
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.responses import PlainTextResponse, JSONResponse, Response, FileResponse
from starlette.requests import Request
import uvicorn
import httpx
import json

# Admin 看板 HTML 路径
_ADMIN_HTML = Path(__file__).resolve().parent.parent.parent / "webbot" / "static" / "admin" / "analytics.html"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("publish-server")

# 内网 FileBot API 地址（AI Search）
FILEBOT_API_URL = "http://localhost:8001/api/v1"

# 内网 Webbot 追踪 API
WEBBOT_TRACK_URL = "http://localhost:8000/api/v1/track"

TRACKING_SCRIPT = """(function(){
  try {
    var d={path:location.pathname,host:location.hostname,lang:(document.documentElement.lang||''),ref:(document.referrer||''),sw:screen.width,sh:screen.height};
    navigator.sendBeacon('/api/v1/track',JSON.stringify(d));
  }catch(e){}
})();"""

# Publish directory
PUBLISH_DIR = Path(__file__).parent / "data" / "publish"
PUBLISH_DIR = PUBLISH_DIR.resolve()

if not PUBLISH_DIR.exists() or not PUBLISH_DIR.is_dir():
    logger.error(f"Publish directory not found: {PUBLISH_DIR}")
    sys.exit(1)

logger.info(f"Publish directory: {PUBLISH_DIR}")


async def serve_track_js(request):
    """Serve tracking JS — hit the same origin for sendBeacon POST."""
    return Response(
        content=TRACKING_SCRIPT,
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=3600", "Access-Control-Allow-Origin": "*"}
    )


async def proxy_track(request):
    """Proxy tracking POST to internal webbot API."""
    try:
        body = await request.body()
        headers = {
            "Content-Type": request.headers.get("content-type", "application/json"),
            "User-Agent": request.headers.get("user-agent", ""),
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(WEBBOT_TRACK_URL, content=body, headers=headers)
            if resp.status_code == 200:
                return JSONResponse(resp.json())
            return JSONResponse({"ok": False}, status_code=502)
    except httpx.ConnectError:
        logger.warning("Track proxy: webbot unreachable")
        return JSONResponse({"ok": True, "cached": True}, status_code=200)
    except Exception as e:
        logger.warning(f"Track proxy failed: {e}")
        return JSONResponse({"ok": True, "cached": True}, status_code=200)


async def index_page(request):
    """Root page - show list of published pages."""
    html_pages = sorted(PUBLISH_DIR.rglob("*.html"))
    links = [
        f'<li><a href="/{page.relative_to(PUBLISH_DIR)}">/{page.relative_to(PUBLISH_DIR)}</a> ({page.stat().st_size} bytes)</li>'
        for page in html_pages
    ]
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


# 从环境变量读取服务 token，否则启动时用 admin 密码获取
SERVICE_TOKEN = os.environ.get("PUBLISH_SERVER_TOKEN", "")

async def ensure_service_token():
    """确保有可用的服务 token 用于代理 FileBot API 请求。"""
    global SERVICE_TOKEN
    if SERVICE_TOKEN:
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{FILEBOT_API_URL}/auth/login",
                data={"username": "admin", "password": "admin123"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code == 200:
                SERVICE_TOKEN = resp.json()["access_token"]
                logger.info("AI Search service token acquired")
            else:
                logger.warning(f"Failed to get service token: {resp.status_code}")
    except Exception as e:
        logger.warning(f"Cannot get service token: {e}")


async def proxy_mustache(request):
    """Proxy mustache template rendering to FileBot backend (port 8001)."""
    path = request.url.path  # e.g. /mustache/mustache-templates/page-list
    qs = request.url.query  # e.g. datasource=...
    target = f"http://localhost:8001{path}"
    if qs:
        target += "?" + qs
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(target)
            return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type", "text/html"))
    except httpx.ConnectError:
        logger.warning("Mustache proxy: FileBot 8001 unreachable")
        return PlainTextResponse("Mustache service unavailable", status_code=502)
    except Exception as e:
        logger.warning(f"Mustache proxy failed: {e}")
        return PlainTextResponse(f"Mustache proxy error: {e}", status_code=502)


async def proxy_ai_search(request):
    """Proxy AI search to internal FileBot backend."""
    q = request.query_params.get("q", "")
    lang = request.query_params.get("lang", "en")
    top_k = request.query_params.get("top_k", "5")
    site = request.query_params.get("site", "")

    if not q:
        return JSONResponse({"error": "Missing query parameter 'q'"}, status_code=400)

    try:
        if not SERVICE_TOKEN:
            await ensure_service_token()

        headers = {"Authorization": f"Bearer {SERVICE_TOKEN}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{FILEBOT_API_URL}/search/ai",
                params={"q": q, "lang": lang, "top_k": top_k, "site": site},
                headers=headers,
            )
            return JSONResponse(resp.json(), status_code=resp.status_code)
    except httpx.ConnectError:
        logger.warning("AI Search proxy: FileBot unreachable")
        return JSONResponse({"error": "AI search service unavailable"}, status_code=502)
    except Exception as e:
        logger.warning(f"AI Search proxy failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=502)


routes = [
    Route("/mustache/{path:path}", endpoint=proxy_mustache),
    Route("/api/v1/track/track.js", endpoint=serve_track_js),
    Route("/api/v1/track", endpoint=proxy_track, methods=["POST"]),
    Route("/api/v1/ai-search", endpoint=proxy_ai_search),
    Route("/admin/analytics", endpoint=lambda r: FileResponse(str(_ADMIN_HTML)) if _ADMIN_HTML.exists() else PlainTextResponse("Not found", status_code=404)),
    Mount("/", app=StaticFiles(directory=str(PUBLISH_DIR), html=True), name="publish"),
]

app = Starlette(
    routes=routes,
    on_startup=[
        lambda: logger.info("Publish server started"),
        ensure_service_token,
    ],
)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8003
    logger.info(f"Starting publish server on port {port}")
    uvicorn.run("publish_server:app", host="0.0.0.0", port=port, log_level="info")
