"""
WebBot Versions API — 页面发布版本管理
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import sqlite3
import json
import re
import aiohttp
from datetime import datetime

from .. import versioning

router = APIRouter(prefix="/api/v1/versions", tags=["versions"])

DB_PATH = "app/webbot.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/page")
async def list_page_versions(
    path: str = Query(..., description="Page path, e.g. /canadasite/en/service"),
):
    """获取指定页面的所有发布版本及页面元数据"""
    versions = versioning.get_versions(path)

    # 获取页面元数据
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT id, title, navigation_title, language, status, parent_path, "
        "current_version, approved, approved_at, approved_by, scheduled_publish, last_published "
        "FROM webbot_page WHERE path = ?", (path,)
    )
    page = c.fetchone()
    conn.close()

    if not page:
        raise HTTPException(status_code=404, detail=f"Page not found: {path}")

    return {
        "page_path": path,
        "version_count": len(versions),
        "versions": versions,
        "metadata": dict(page),
    }


@router.get("/page/version")
async def get_specific_version(
    path: str = Query(..., description="Page path"),
    version: int = Query(..., description="Version number"),
):
    """获取指定版本的完整内容（content + metadata）"""
    snap = versioning.get_version(path, version)
    if snap is None:
        raise HTTPException(status_code=404, detail=f"Version v{version} not found for {path}")
    return snap


@router.get("/page/diff")
async def diff_versions(
    path: str = Query(..., description="Page path"),
    v1: int = Query(..., description="Older version to compare"),
    v2: int = Query(..., description="Newer version to compare"),
):
    """对比两个版本的页面内容"""
    snap1 = versioning.get_version(path, v1)
    snap2 = versioning.get_version(path, v2)
    if snap1 is None:
        raise HTTPException(status_code=404, detail=f"Version v{v1} not found")
    if snap2 is None:
        raise HTTPException(status_code=404, detail=f"Version v{v2} not found")
    return {
        "page_path": path,
        "v1": {
            "version": v1,
            "created_at": snap1["created_at"],
            "content": snap1.get("content", ""),
        },
        "v2": {
            "version": v2,
            "created_at": snap2["created_at"],
            "content": snap2.get("content", ""),
        },
    }


def _extract_footer(page_content: str) -> str:
    """从页面内容中提取 footer HTML"""
    footer_match = re.search(
        r'<footer[^>]*id=[\"\']wb-info[\"\'][^>]*>.*?</footer>',
        page_content or "", re.DOTALL | re.IGNORECASE
    )
    if footer_match:
        return footer_match.group(0)
    return ""


async def _load_template(path: str, page_path: str) -> str:
    """
    从 mustache template page 加载渲染后的模板片段。
    pages.py 中 render_mustache_template 的逻辑。
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM webbot_page WHERE path = ?", (path,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return ""
    try:
        tmpl_config = json.loads(row[0])
        tmpl_content = tmpl_config.get("template", row[0])
    except json.JSONDecodeError:
        tmpl_content = row[0]
    try:
        import chevron
        return chevron.render(tmpl_content, {"path": page_path})
    except Exception:
        return tmpl_content


@router.post("/page/rollback")
async def rollback_page(
    path: str = Query(..., description="Page path"),
    version: int = Query(..., description="Version to rollback to"),
):
    """
    回滚到指定版本：取历史版本的 content（页面正文），
    用当前系统模板重新渲染（header/footer 使用当前模板），
    然后通过 FileBot API 重新发布。
    """
    # 1. 获取历史 content
    content = versioning.rollback_to_version(path, version)
    if content is None:
        raise HTTPException(status_code=404, detail=f"Version v{version} not found for {path}")

    # 2. 加载当前页面数据
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM webbot_page WHERE path = ?", (path,))
    page = cursor.fetchone()
    if not page:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Page not found: {path}")
    page = dict(page)
    conn.close()

    page_language = page.get("language", "en")
    page_title = page.get("navigation_title") or page.get("title", "Untitled")

    now = datetime.utcnow()
    date_modified_str = now.strftime("%Y-%m-%d")
    date_modified_html = (
        f'<div class="row">\n'
        f'    <div class="col-md-12">\n'
        f'        <dl id="wb-dtmd">\n'
        f'            <dt>Date modified:</dt>\n'
        f'            <dd><time property="dateModified">{date_modified_str}</time></dd>\n'
        f'        </dl>\n'
        f'    </div>\n'
        f'</div>'
    )

    # 3. 加载系统模板片段（当前版本的 head/header/footer）
    head_html = await _load_template("/canadasite/mustache-templates/gethead", path)
    header_en_html = await _load_template("/canadasite/mustache-templates/getheader_en", path)
    header_fr_html = await _load_template("/canadasite/mustache-templates/getheader_fr", path)
    header_html = header_en_html if page_language == "en" else header_fr_html

    # Footer: 从现有页面内容中提取，或加载模板
    footer_html = _extract_footer(page.get("content", ""))
    if not footer_html:
        footer_row = cursor.execute(
            "SELECT content FROM webbot_page WHERE path = ?",
            ("/canadasite/mustache-templates/getfooter",)
        ).fetchone()
        if footer_row:
            try:
                footer_config = json.loads(footer_row[0])
                footer_content = footer_config.get("template", footer_row[0])
            except json.JSONDecodeError:
                footer_content = footer_row[0]
            footer_html = footer_content

    # 4. 组装完整 HTML
    full_html = versioning.assemble_page_html(
        content=content,
        head=head_html,
        header=header_html,
        footer=footer_html,
        date_modified=date_modified_str,
        language=page_language,
        title=page_title,
        page_path=path,
        header_en=header_en_html,
        header_fr=header_fr_html,
        date_modified_html=date_modified_html,
    )

    # 5. 通过 FileBot API 重新发布
    filebot_publish_url = "http://localhost:8001/api/v1/pages/publish"
    async with aiohttp.ClientSession() as session:
        async with session.post(
            filebot_publish_url,
            params={"path": path},
            json={"html_content": full_html},
            headers={"X-WebBot-Access": "true"}
        ) as fb_resp:
            if fb_resp.status != 200:
                fb_error = await fb_resp.text()
                raise HTTPException(status_code=502, detail=f"Rollback publish failed: {fb_error}")
            fb_result = await fb_resp.json()

    # 6. 更新 DB 状态
    conn = get_db()
    now_iso = now.isoformat()
    conn.execute(
        "UPDATE webbot_page SET status = 'published', last_published = ? WHERE path = ?",
        (now_iso, path)
    )
    conn.commit()
    conn.close()

    return {
        "success": True,
        "path": path,
        "rolled_back_to": version,
        "note": f"Rolled back to v{version}. Page content restored from historical version, rendered with current templates.",
    }


@router.get("/summary")
async def versions_summary():
    """获取所有有版本的页面摘要"""
    return versioning.get_all_versions_summary()
