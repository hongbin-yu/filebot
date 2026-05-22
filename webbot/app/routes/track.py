"""
WebBot Pageview Tracking — 轻量自建访问统计
零外部依赖，无 Cookie，符合隐私合规
"""

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from typing import Optional
import sqlite3
import hashlib
from datetime import datetime, timedelta
import json

router = APIRouter(prefix="/api/v1/track", tags=["tracking"])

DB_PATH = "app/webbot.db"

TRACKING_SCRIPT = """(function(){
  try {
    var d={path:location.pathname,host:location.hostname,lang:(document.documentElement.lang||''),ref:(document.referrer||''),sw:screen.width,sh:screen.height};
    navigator.sendBeacon('/api/v1/track',JSON.stringify(d));
  }catch(e){}
})();"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_table():
    """Create pageview_log table if not exists."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS pageview_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            host TEXT DEFAULT '',
            ip_hash TEXT DEFAULT '',
            user_agent TEXT DEFAULT '',
            referrer TEXT DEFAULT '',
            language TEXT DEFAULT '',
            screen_width INTEGER DEFAULT 0,
            screen_height INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_pageview_path ON pageview_log(path)
    """)
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_pageview_ts ON pageview_log(timestamp)
    """)
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_pageview_date ON pageview_log(date(timestamp))
    """)
    conn.commit()
    conn.close()


# ---- Pageview data model for POST ----

class PageviewData(BaseModel):
    path: str
    host: Optional[str] = ""
    lang: Optional[str] = ""
    ref: Optional[str] = ""
    sw: Optional[int] = 0
    sh: Optional[int] = 0


# ---- Endpoints ----

@router.get("/track.js")
async def get_tracking_script():
    """Return the tracking JavaScript for injection."""
    return Response(
        content=TRACKING_SCRIPT,
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=86400"}
    )


@router.post("")
async def track_pageview(data: PageviewData, request: Request):
    """Receive and log a pageview event from the tracking script."""
    _ensure_table()

    # Hash IP for privacy (no raw IP stored)
    ip_raw = request.client.host if request.client and request.client.host else "unknown"
    ip_hash = hashlib.sha256(ip_raw.encode()).hexdigest()[:16]

    user_agent = request.headers.get("user-agent", "")

    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO pageview_log (path, host, ip_hash, user_agent, referrer, language, screen_width, screen_height)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.path,
        data.host,
        ip_hash,
        user_agent,
        data.ref,
        data.lang,
        data.sw,
        data.sh,
    ))
    conn.commit()
    conn.close()

    return {"ok": True, "path": data.path}


@router.get("/daily")
async def get_daily_stats(days: int = 30):
    """Get daily pageview counts for the last N days."""
    _ensure_table()
    conn = get_db()
    c = conn.cursor()

    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    c.execute("""
        SELECT date(timestamp) as day, COUNT(*) as views
        FROM pageview_log
        WHERE timestamp >= ?
        GROUP BY day
        ORDER BY day ASC
    """, (cutoff,))
    daily = [{"date": r["day"], "views": r["views"]} for r in c.fetchall()]

    # Total
    c.execute("SELECT COUNT(*) FROM pageview_log WHERE timestamp >= ?", (cutoff,))
    total = c.fetchone()[0]

    conn.close()
    return {"period_days": days, "total": total, "daily": daily}


@router.get("/top-pages")
async def get_top_pages(days: int = 30, limit: int = 20):
    """Get most visited pages for the last N days."""
    _ensure_table()
    conn = get_db()
    c = conn.cursor()

    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    c.execute("""
        SELECT path, COUNT(*) as views, COUNT(DISTINCT ip_hash) as unique_visitors
        FROM pageview_log
        WHERE timestamp >= ?
        GROUP BY path
        ORDER BY views DESC
        LIMIT ?
    """, (cutoff, limit))
    pages = [{"path": r["path"], "views": r["views"], "unique_visitors": r["unique_visitors"]} for r in c.fetchall()]

    conn.close()
    return {"days": days, "pages": pages}


@router.get("/summary")
async def get_tracking_summary():
    """Quick summary of tracking data."""
    _ensure_table()
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM pageview_log")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(DISTINCT path) FROM pageview_log")
    unique_paths = c.fetchone()[0]

    c.execute("SELECT COUNT(DISTINCT ip_hash) FROM pageview_log")
    unique_visitors = c.fetchone()[0]

    today = datetime.utcnow().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM pageview_log WHERE date(timestamp) = ?", (today,))
    today_views = c.fetchone()[0]

    c.execute("SELECT MIN(date(timestamp)) FROM pageview_log")
    first_record = c.fetchone()[0]

    conn.close()
    return {
        "total_pageviews": total,
        "unique_paths": unique_paths,
        "approximate_unique_visitors": unique_visitors,
        "today_views": today_views,
        "first_record_date": first_record,
    }
