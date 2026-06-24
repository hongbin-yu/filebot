"""
Mustache template rendering routes for FileBot
Connects directly to webbot.db for template config storage.
"""
from fastapi import APIRouter, HTTPException, Request, Form, Query
from fastapi.responses import Response, HTMLResponse
import sqlite3
import json
import os
import traceback
import urllib.parse
from typing import Optional
from pathlib import Path
import psycopg2
import psycopg2.extras

router = APIRouter(prefix="", tags=["mustache"])

# Webbot DB path — resolves relative to filebot backend directory
_WEBBOT_DB_PATH = os.environ.get(
    "WEBBOT_DB_PATH",
    str(Path(__file__).resolve().parent.parent.parent.parent.parent / "webbot" / "app" / "webbot.db")
)
_FILEBOT_DB_URL = os.environ.get(
    "FILEBOT_DATABASE_URL",
    os.environ.get("DATABASE_URL", "postgresql://filebot:filebot@localhost:5432/filebot")
)


def get_db_connection() -> sqlite3.Connection:
    """Connect to webbot.db (SQLite, shared with webbot)."""
    conn = sqlite3.connect(_WEBBOT_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_filebot_db_connection():
    """Connect to filebot PostgreSQL for datasource queries (documents table)."""
    return psycopg2.connect(_FILEBOT_DB_URL)


def _query_local_api(path: str, params: dict, cursor) -> Optional[list]:
    """
    Handle local /api/v1/ datasource requests via direct SQL (skip HTTP + auth).
    For filebot: queries documents_old table with path prefix /boarding mapping.
    Returns data or None if the path is not handled.
    """
    # /api/v1/pages/ — list pages from documents_old
    if path == "/api/v1/pages" or path == "/api/v1/pages/":
        path_val = params.get("path", [None])[0]
        limit = int(params.get("limit", ["100"])[0])
        skip = int(params.get("skip", ["0"])[0])
        prefix_val = params.get("prefix", [None])[0]

        fb_conn = get_filebot_db_connection()
        fb_cursor = fb_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        try:
            # Pass LIKE patterns as parameters to avoid psycopg2's %-format specifier parsing
            like_exclusions = (
                '%/jcr-content/%', '%.png', '%.jpg', '%.svg', '%/content/dam/%'
            )
            _BASE = "SELECT path, title, parent_folder_path FROM documents WHERE"
            _LIKE_FILTER = (
                " AND path NOT LIKE %s AND path NOT LIKE %s"
                + " AND path NOT LIKE %s AND path NOT LIKE %s"
                + " AND path NOT LIKE %s"
            )

            if prefix_val:
                # Map /canadasite/... → /publish/...
                if prefix_val.startswith("/canadasite/"):
                    fb_prefix = "/publish" + prefix_val[len("/canadasite"):]
                else:
                    fb_prefix = prefix_val
                normalized = fb_prefix.rstrip("/") + "/"
                sql = (
                    _BASE
                    + " (path LIKE %s OR parent_folder_path LIKE %s)"
                    + _LIKE_FILTER
                    + " ORDER BY title ASC LIMIT %s OFFSET %s"
                )
                fb_cursor.execute(
                    sql,
                    (normalized + "%", normalized + "%") + like_exclusions + (limit, skip)
                )
            elif path_val is None or path_val == "":
                sql = (
                    _BASE + " parent_folder_path IS NULL"
                    + _LIKE_FILTER
                    + " ORDER BY title ASC LIMIT %s OFFSET %s"
                )
                fb_cursor.execute(sql, like_exclusions + (limit, skip))
            else:
                # Map /canadasite/... → /publish/...
                if path_val.startswith("/canadasite/"):
                    fb_path = "/publish" + path_val[len("/canadasite"):]
                else:
                    fb_path = path_val
                normalized = fb_path.rstrip("/")
                sql = (
                    _BASE + " parent_folder_path = %s"
                    + _LIKE_FILTER
                    + " ORDER BY title ASC LIMIT %s OFFSET %s"
                )
                fb_cursor.execute(sql, (normalized,) + like_exclusions + (limit, skip))

            rows = []
            for row in fb_cursor.fetchall():
                page_dict = dict(row)
                # Strip /publish and /canadasite prefixes for publish server paths
                for key in ("path", "parent_folder_path"):
                    val = page_dict.get(key, "")
                    if val:
                        if val.startswith("/publish"):
                            val = val[len("/publish"):]
                        if val.startswith("/canadasite"):
                            val = val[len("/canadasite"):]  # /canadasite is root, so becomes /
                        # Remove .html suffix from path since mustache template adds it
                        if val.endswith(".html"):
                            val = val[:-5]
                        page_dict[key] = val
                rows.append(page_dict)
            return rows
        finally:
            fb_conn.close()

    return None


@router.get("/mustache/{path:path}")
async def render_mustache(path: str, request: Request):
    """
    Render a Mustache template stored as a webbot page.
    Path: /mustache/{path} — the mustache template page path (e.g. mustache-templates/page-list)
    Config is stored in the page's content field.
    Supports datasource + template rendering, and query param override.
    """
    import chevron

    # Determine full DB path
    full_path = path
    if not full_path.startswith("/canadasite/"):
        full_path = f"/canadasite/{path.lstrip('/')}"

    # Try path variants
    path_variants = [
        full_path,
        full_path.rstrip("/"),
        full_path + "/",
        f"/{path.lstrip('/')}",
        f"/{path.lstrip('/')}".rstrip("/"),
        f"/{path.lstrip('/')}/",
    ]

    conn = get_db_connection()
    cursor = conn.cursor()

    # Find the page
    page = None
    used_path = None
    for variant in path_variants:
        cursor.execute("SELECT * FROM webbot_page WHERE path = ?", (variant,))
        row = cursor.fetchone()
        if row:
            page = dict(row)
            used_path = variant
            break

    if not page:
        # Try static file fallback
        static_path = Path(_WEBBOT_DB_PATH).parent.parent.parent.parent / "frontend" / "mustache-templates"
        static_file = static_path / f"{path.replace('/', os.sep)}.html"
        if static_file.exists():
            content = static_file.read_text(encoding="utf-8")
            conn.close()
            return HTMLResponse(content=content, status_code=200)
        # Check static/templates
        static_path2 = Path(_WEBBOT_DB_PATH).parent.parent.parent.parent / "static" / "mustache-templates"
        static_file2 = static_path2 / f"{path.replace('/', os.sep)}.html"
        if static_file2.exists():
            content = static_file2.read_text(encoding="utf-8")
            conn.close()
            return HTMLResponse(content=content, status_code=200)

        conn.close()
        return HTMLResponse(
            content=f"<div class='alert alert-warning'>Template not found: {path}</div>",
            status_code=200
        )

    # Parse configuration from content
    raw_content = page["content"]
    if not raw_content:
        conn.close()
        return HTMLResponse(
            content="<div class='alert alert-danger'>Config page content is empty</div>",
            status_code=200
        )

    # Extract JSON from HTML content
    config_json = raw_content
    if "{" in raw_content and "}" in raw_content:
        start_idx = raw_content.find("{")
        end_idx = raw_content.rfind("}") + 1
        if start_idx < end_idx:
            extracted = raw_content[start_idx:end_idx]
            try:
                json.loads(extracted, strict=False)
                config_json = extracted
            except json.JSONDecodeError:
                pass

    try:
        config = json.loads(config_json, strict=False)
    except json.JSONDecodeError as e:
        conn.close()
        return HTMLResponse(
            content=f"<div class='alert alert-danger'>Invalid config JSON: {str(e)}</div>",
            status_code=200
        )

    # Get template
    template = config.get("template", "")
    if not template:
        conn.close()
        return HTMLResponse(
            content="<div class='alert alert-danger'>Missing template field in config</div>",
            status_code=200
        )

    # Initialize data
    data = config.get("data", {})

    # Get datasource
    datasource = config.get("datasource", config.get("dataresource"))
    query_datasource = request.query_params.get("datasource")
    if query_datasource:
        datasource = query_datasource

    # Fetch datasource
    if datasource:
        try:
            import aiohttp

            url = datasource
            if not url.startswith("http"):
                base_url = str(request.base_url).rstrip("/")
                url = f"{base_url}{url}"

            # Try direct DB query for local /api/v1/ endpoints
            datasource_data = None
            parsed = urllib.parse.urlparse(url)
            if parsed.path.startswith("/api/v1/pages/") or parsed.path == "/api/v1/pages":
                params = urllib.parse.parse_qs(parsed.query)
                datasource_data = _query_local_api(parsed.path, params, cursor)

            if datasource_data is not None:
                data["datasource_loaded"] = True
                data["datasource_raw"] = datasource_data
                if isinstance(datasource_data, dict):
                    data = {**data, **datasource_data}
                elif isinstance(datasource_data, list):
                    data = datasource_data
                else:
                    data["items"] = datasource_data
            else:
                # Fallback to HTTP fetch with auth header forwarding
                headers = {}
                auth_header = request.headers.get("Authorization")
                if auth_header:
                    headers["Authorization"] = auth_header

                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, timeout=10) as resp:
                        if resp.status == 200:
                            datasource_data = await resp.json()
                            data["datasource_loaded"] = True
                            data["datasource_raw"] = datasource_data
                            if isinstance(datasource_data, dict):
                                data = {**data, **datasource_data}
                            elif isinstance(datasource_data, list):
                                data = datasource_data
                            else:
                                data["items"] = datasource_data
        except Exception as e:
            print(f"Mustache datasource fetch failed: {datasource} - {str(e)}")
            data["datasource_loaded"] = False
            data["datasource_error"] = str(e)

    conn.close()

    # Render template
    try:
        result = chevron.render(template, data)
        return HTMLResponse(content=result, status_code=200)
    except Exception as e:
        return HTMLResponse(
            content=f"<div class='alert alert-danger'>Render error: {str(e)}</div>",
            status_code=200
        )


@router.post("/render-mustache")
async def render_mustache_template(
    template: str = Form(..., description="Mustache template"),
    json_data: str = Form(..., description="JSON data"),
    escape_html: bool = Form(True, description="HTML escaping")
):
    """
    Render Mustache template (direct POST call, no DB needed).
    """
    import chevron

    try:
        data = json.loads(json_data)
        result = chevron.render(template, data)

        return {
            "success": True,
            "html": result,
            "error": None
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "html": "",
            "error": f"JSON parse error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "html": "",
            "error": f"Render error: {str(e)}"
        }
