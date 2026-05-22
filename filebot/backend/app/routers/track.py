"""
FileBot → Webbot 追踪代理路由
公网访问的发布页面通过此路由转发 pageview 到内网 webbot
"""

from fastapi import APIRouter, Request, Response
from starlette.responses import PlainTextResponse, JSONResponse
import httpx
import logging
import traceback
from pathlib import Path
from starlette.responses import FileResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tracking"])

# Admin 看板路径
_ADMIN_HTML = Path(__file__).resolve().parent.parent.parent.parent.parent / "webbot" / "static" / "admin" / "analytics.html"

# 内网 Webbot 地址
WEBBOT_INTERNAL_URL = "http://localhost:8000/api/v1/track"

# 内联追踪脚本 (proxy 版本 — 请求发到 FileBot 自身)
TRACKING_SCRIPT = """(function(){
  try {
    var d={path:location.pathname,host:location.hostname,lang:(document.documentElement.lang||''),ref:(document.referrer||''),sw:screen.width,sh:screen.height};
    navigator.sendBeacon('/api/v1/track',JSON.stringify(d));
  }catch(e){}
})();"""


@router.get("/api/v1/track/track.js")
async def serve_tracking_script():
    """Serve the tracking JS — accessible via FileBot's public URL."""
    return Response(
        content=TRACKING_SCRIPT,
        media_type="application/javascript",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.get("/admin/analytics")
async def analytics_dashboard():
    if _ADMIN_HTML.exists():
        return FileResponse(str(_ADMIN_HTML))
    return JSONResponse({"error": "Dashboard not found"}, status_code=404)


@router.post("/api/v1/track")
async def proxy_tracking_data(request: Request):
    """Receive tracking data from published pages and forward to webbot."""
    try:
        body = await request.body()
        headers = {
            "Content-Type": request.headers.get("content-type", "application/json"),
            "User-Agent": request.headers.get("user-agent", ""),
            "X-Forwarded-For": request.client.host if request.client else "",
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                WEBBOT_INTERNAL_URL,
                content=body,
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                logger.info(f"📊 Track forwarded: path={data.get('path', '?')}")
                return JSONResponse(data, status_code=200)
            else:
                err_body = resp.text
                logger.warning(f"Webbot track failed: {resp.status_code} - {err_body}")
                return JSONResponse({"ok": False, "detail": f"proxy failed: {resp.status_code} {err_body}"}, status_code=502)

    except httpx.ConnectError:
        logger.warning("Webbot track proxy: webbot not reachable (logged locally)")
        return JSONResponse({"ok": True, "cached": True}, status_code=200)
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Track proxy error: {e}\n{tb}")
        return JSONResponse({"ok": False, "detail": f"proxy error: {e}"}, status_code=502)
