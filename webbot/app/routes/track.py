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
import urllib.request
import urllib.error
import time

router = APIRouter(prefix="/api/v1/track", tags=["tracking"])

import os

DB_PATH = os.environ.get(
    "WEBBOT_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "webbot.db")
)


# ── IP Geo-location Cache (in-memory + sqlite fallback) ──
_GEO_CACHE = {}  # ip_str -> {country, region, ts}
_GEO_CACHE_MAX_AGE = 86400  # 24h
_GEO_CACHE_HITS = 0
_GEO_CACHE_MISS = 0

_GEO_CACHE_DB = "app/geo_cache.db"


def _ensure_geo_cache_table():
    conn = sqlite3.connect(_GEO_CACHE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS geo_cache (
            ip TEXT PRIMARY KEY,
            country TEXT DEFAULT '',
            region TEXT DEFAULT '',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def _geo_lookup(ip: str) -> dict:
    """Resolve IP → {country, region}. Uses in-memory cache, then sqlite, then ip-api.com."""
    global _GEO_CACHE_HITS, _GEO_CACHE_MISS

    # 1. In-memory cache
    cached = _GEO_CACHE.get(ip)
    if cached and (time.time() - cached["ts"]) < _GEO_CACHE_MAX_AGE:
        _GEO_CACHE_HITS += 1
        return cached

    # 2. SQLite cache
    _ensure_geo_cache_table()
    conn = sqlite3.connect(_GEO_CACHE_DB)
    row = conn.execute("SELECT country, region FROM geo_cache WHERE ip = ?", (ip,)).fetchone()
    conn.close()
    if row:
        result = {"country": row[0] or "", "region": row[1] or "", "ts": time.time()}
        _GEO_CACHE[ip] = result
        _GEO_CACHE_HITS += 1
        return result

    # 3. External API call (ip-api.com, free, no key needed, 45 req/min)
    _GEO_CACHE_MISS += 1
    result = {"country": "", "region": "", "ts": time.time()}
    try:
        url = f"http://ip-api.com/json/{ip}?fields=country,regionName,status"
        req = urllib.request.Request(url, headers={"User-Agent": "WebBot/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            if data.get("status") == "success":
                result["country"] = data.get("country", "")
                result["region"] = data.get("regionName", "")
    except Exception:
        pass  # silently fall back to empty location

    # Cache in both memory and sqlite
    _GEO_CACHE[ip] = result
    try:
        conn = sqlite3.connect(_GEO_CACHE_DB)
        conn.execute(
            "REPLACE INTO geo_cache (ip, country, region, updated_at) VALUES (?, ?, ?, datetime('now'))",
            (ip, result["country"], result["region"])
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

    return result

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
            country TEXT DEFAULT '',
            region TEXT DEFAULT '',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Add columns if table already exists (migration)
    for col in ["country", "region"]:
        try:
            conn.execute(f"ALTER TABLE pageview_log ADD COLUMN {col} TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # column already exists
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
async def track_pageview(request: Request):
    """Receive and log a pageview event from the tracking script.
    
    Note: navigator.sendBeacon() sends Content-Type: text/plain,
    so we parse the JSON body manually instead of using Pydantic auto-validation.
    """
    _ensure_table()

    # Parse body (sendBeacon sends text/plain, not application/json)
    try:
        body = await request.json()
    except Exception:
        try:
            raw = await request.body()
            body = json.loads(raw.decode())
        except Exception:
            return Response(content='{"ok":false,"error":"invalid json"}', status_code=400, media_type="application/json")

    path = body.get("path", "")
    host = body.get("host", "")
    lang = body.get("lang", "")
    ref = body.get("ref", "")
    sw = body.get("sw", 0)
    sh = body.get("sh", 0)

    # Hash IP for privacy (no raw IP stored)
    ip_raw = request.client.host if request.client and request.client.host else "unknown"
    ip_hash = hashlib.sha256(ip_raw.encode()).hexdigest()[:16]

    # Geo lookup (IP never stored, only location)
    geo = _geo_lookup(ip_raw)
    country = geo.get("country", "")
    region = geo.get("region", "")

    user_agent = request.headers.get("user-agent", "")

    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO pageview_log (path, host, ip_hash, user_agent, referrer, language, screen_width, screen_height, country, region)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        path,
        host,
        ip_hash,
        user_agent,
        ref,
        lang,
        sw,
        sh,
        country,
        region,
    ))
    conn.commit()
    conn.close()

    return {"ok": True, "path": path}


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


@router.get("/geo")
async def get_geo_stats(days: int = 30):
    """Geographic breakdown: by country and by region (province/state)."""
    _ensure_table()
    conn = get_db()
    c = conn.cursor()

    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

    # By country
    c.execute("""
        SELECT COALESCE(NULLIF(country, ''), 'Unknown') as loc, COUNT(*) as views
        FROM pageview_log
        WHERE timestamp >= ?
        GROUP BY loc
        ORDER BY views DESC
    """, (cutoff,))
    by_country = [{"location": r[0], "views": r[1]} for r in c.fetchall()]

    # By region (province/state) within known countries
    c.execute("""
        SELECT COALESCE(NULLIF(country, ''), 'Unknown') as country,
               COALESCE(NULLIF(region, ''), 'Unknown') as region,
               COUNT(*) as views
        FROM pageview_log
        WHERE timestamp >= ?
        GROUP BY country, region
        ORDER BY views DESC
    """, (cutoff,))
    by_region = [{"country": r[0], "region": r[1], "views": r[2]} for r in c.fetchall()]

    conn.close()
    return {
        "period_days": days,
        "by_country": by_country,
        "by_region": by_region,
        "cache_hits": _GEO_CACHE_HITS,
        "cache_misses": _GEO_CACHE_MISS,
    }


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
