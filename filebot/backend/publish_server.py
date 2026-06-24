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
from starlette.middleware import Middleware
from starlette.exceptions import HTTPException
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

# 简单密码保护（用于 ca.webfilebot.com，开发阶段使用）
SITE_PASSWORD = os.environ.get("PUBLISH_SITE_PASSWORD", "webfilebot2026")
PASSWORD_COOKIE = "publish_pass"
CDN_BYPASS_HEADER = "x-publish-bypass"
CDN_BYPASS_SECRET = "webfilebot2026"  # 与 SITE_PASSWORD 一致，CDN Worker 需要带此 header
LOGIN_PATH = "/__login__"

# Publish directory
PUBLISH_DIR = Path(os.environ.get("PUBLISH_DIR", Path(__file__).parent / "data" / "publish"))
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


PASSWORD_LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Access Required</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:linear-gradient(135deg,#0a1628,#1a2744);min-height:100vh;display:flex;align-items:center;justify-content:center;color:#e0e6f0}
.login-box{background:#1e293b;padding:48px 40px;border-radius:16px;width:100%;max-width:400px;margin:20px;box-shadow:0 20px 50px rgba(0,0,0,.4)}
h1{font-size:22px;font-weight:700;margin-bottom:6px}p.sub{color:#94a3b8;font-size:14px;margin-bottom:28px}
label{display:block;font-size:13px;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
input[type=password]{width:100%;padding:12px 16px;background:#0f172a;border:1px solid #334155;border-radius:10px;color:#e0e6f0;font-size:15px;outline:none;transition:border-color .2s}
input[type=password]:focus{border-color:#3b82f6;box-shadow:0 0 0 3px rgba(59,130,246,.15)}
button{width:100%;padding:13px;background:linear-gradient(135deg,#3b82f6,#2563eb);border:none;border-radius:10px;color:#fff;font-size:15px;font-weight:600;cursor:pointer;margin-top:20px;transition:transform .15s,box-shadow .15s}
.error{display:none;background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);color:#fca5a5;padding:10px 14px;border-radius:8px;font-size:13px;margin-bottom:16px}
</style>
</head>
<body>
<div class="login-box">
<h1>\U0001f512 Site in Development</h1>
<p class="sub">This site is under development. Enter the password to continue.</p>
<div class="error" id="error">Incorrect password. Try again.</div>
<form method="post" action="/__login__">
<label>Password</label>
<input type="password" name="password" placeholder="Enter password" required autofocus>
<button type="submit">Continue</button>
</form>
</div>
<script>
var url=new URL(window.location.href);if(url.searchParams.get('failed')==='1'){document.getElementById('error').style.display='block'}
</script>
</body>
</html>"""


async def serve_login_page(request: Request):
    """Serve the password login form."""
    return Response(PASSWORD_LOGIN_HTML, media_type="text/html")


async def handle_login(request: Request):
    """Validate password and set cookie."""
    form = await request.form()
    pw = form.get("password", "")
    if pw == SITE_PASSWORD:
        resp = Response(status_code=302)
        resp.headers["Location"] = "/"
        resp.set_cookie(PASSWORD_COOKIE, "granted", max_age=86400 * 7, path="/", httponly=True, samesite="strict")
        return resp
    resp = Response(status_code=302)
    resp.headers["Location"] = LOGIN_PATH + "?failed=1"
    return resp


class HtmlExtensionMiddleware:
    """对无扩展名的 URL 自动补全 .html（Starlette html=True 不生效的 workaround）。"""
    def __init__(self, app, publish_dir: str):
        self.app = app
        self.publish_dir = publish_dir

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "") or scope.get("root_path", "")
        # 只处理无扩展名（或路径以 / 结尾）且不以特殊前缀开头的请求
        if path and not path.startswith("/__") and not path.startswith(LOGIN_PATH):
            last_segment = path.rstrip("/").rsplit("/", 1)[-1] if path.rstrip("/") else ""
            if last_segment and "." not in last_segment:
                candidate = os.path.join(self.publish_dir, path.lstrip("/") + ".html")
                if os.path.isfile(candidate):
                    scope["path"] = path.rstrip("/") + ".html"
        await self.app(scope, receive, send)


class PasswordMiddleware:
    """Check password cookie before serving any page."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "") or scope.get("root_path", "")
        if path.startswith(LOGIN_PATH):
            await self.app(scope, receive, send)
            return
        if path.startswith("/__"):
            await self.app(scope, receive, send)
            return
        # CDN bypass: 检查 secret header
        headers_dict = {}
        for header, value in scope.get("headers", []):
            headers_dict[header.decode("latin-1").lower()] = value.decode("latin-1")
        if headers_dict.get(CDN_BYPASS_HEADER) == CDN_BYPASS_SECRET:
            await self.app(scope, receive, send)
            return
        # Cookie 认证
        cookies = {}
        if "cookie" in headers_dict:
            cookie_str = headers_dict["cookie"]
            for c in cookie_str.split(";"):
                if "=" in c:
                    k, v = c.split("=", 1)
                    cookies[k.strip()] = v.strip()
        if cookies.get(PASSWORD_COOKIE) == "granted":
            await self.app(scope, receive, send)
            return
        headers = [
            (b"location", LOGIN_PATH.encode()),
            (b"content-length", b"0"),
        ]
        await send({
            "type": "http.response.start",
            "status": 302,
            "headers": headers,
        })
        await send({"type": "http.response.body", "body": b""})


routes = [
    Route(LOGIN_PATH, endpoint=serve_login_page),
    Route(LOGIN_PATH, endpoint=handle_login, methods=["POST"]),
    Route("/mustache/{path:path}", endpoint=proxy_mustache),
    Route("/api/v1/track/track.js", endpoint=serve_track_js),
    Route("/api/v1/track", endpoint=proxy_track, methods=["POST"]),
    Route("/api/v1/ai-search", endpoint=proxy_ai_search),
    Route("/admin/analytics", endpoint=lambda r: FileResponse(str(_ADMIN_HTML)) if _ADMIN_HTML.exists() else PlainTextResponse("Not found", status_code=404)),
    Mount("/", app=StaticFiles(directory=str(PUBLISH_DIR), html=True), name="publish"),
]


# 404 异常处理：en/fr 路径下找不到页面时，返回 error-404.html
async def not_found_handler(request: Request, exc: HTTPException) -> Response:
    if exc.status_code == 404:
        path = request.url.path
        if path.startswith('/en/'):
            error_page = PUBLISH_DIR / "en" / "error-404.html"
            if error_page.exists():
                return FileResponse(str(error_page), status_code=404)
        elif path.startswith('/fr/'):
            error_page = PUBLISH_DIR / "fr" / "error-404.html"
            if error_page.exists():
                return FileResponse(str(error_page), status_code=404)
    return PlainTextResponse("Not Found", status_code=404)

app = Starlette(
    routes=routes,
    middleware=[
        Middleware(HtmlExtensionMiddleware, publish_dir=str(PUBLISH_DIR)),
        Middleware(PasswordMiddleware),
    ],
    exception_handlers={
        HTTPException: not_found_handler,
    },
    on_startup=[
        lambda: logger.info("Publish server started"),
        ensure_service_token,
    ],
)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8003
    logger.info(f"Starting publish server on port {port}")
    uvicorn.run("publish_server:app", host="0.0.0.0", port=port, log_level="info")
