"""Pages routes — 基于文档路径而非 UUID"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
import os
import uuid
import re
import json
import sqlite3
import threading
import httpx
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, urljoin

from app.db.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.folder import Folder as FolderModel
from app.models.document import Document
from app.models.document import DocumentStatus as DocStatus, DocumentType, FileType, PublishStatus, ThumbnailStatus
from app.models.page import Page
from app.schemas.document import PageResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# SQLite path for webbot navigation page data
WEBBOT_DB_PATH = os.environ.get("WEBBOT_DB_PATH", "/opt/webfilebot/webbot/data/webbot.db")

def _get_webbot_conn():
    """Get a read-only-mindful SQLite connection to the webbot page db."""
    conn = sqlite3.connect(WEBBOT_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

class NavigationPageItem(BaseModel):
    """Navigation page list item — mirrors webbot PageListItem format"""
    id: str
    title: str = ""
    description: Optional[str] = ""
    language: str = "en"
    status: str = "draft"
    path: Optional[str] = None
    parent_path: Optional[str] = None
    other_language_path: Optional[str] = None
    has_children: bool = False
    created_at: Optional[str] = None
    last_modified: Optional[str] = None
    tags: List[str] = []
    metadata: Optional[Dict[str, Any]] = None

class SinglePageResponse(BaseModel):
    """Single page detail response — mirrors webbot PageResponse"""
    id: str
    title: str = ""
    description: Optional[str] = ""
    content: Optional[str] = ""
    language: str = "en"
    status: str = "draft"
    path: Optional[str] = None
    parent_path: Optional[str] = None
    other_language_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    last_modified: Optional[str] = None
    keywords: Optional[str] = None
    hide_in_navigation: bool = False
    scheduled_publish: Optional[str] = None
    approved: int = 0
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    current_version: int = 0
    tags: List[str] = []

def _query_navigation_pages(parent_path: Optional[str] = None, prefix: Optional[str] = None, skip: int = 0, limit: int = 100, order_by: str = "title"):
    """Query webbot_page (SQLite) for navigation page listing.
    
    Args:
        parent_path: If set, filter by parent_path = this value. If None and prefix is None, return root pages (parent_path IS NULL).
        prefix: If set, filter by path LIKE 'prefix%' (overrides parent_path).
        skip: Offset
        limit: Max items
        order_by: ORDER BY column
    """
    import sqlite3 as _sqlite3
    conn = _get_webbot_conn()
    c = conn.cursor()
    try:
        if prefix:
            norm = prefix.rstrip('/')
            c.execute(
                "SELECT * FROM webbot_page WHERE path LIKE ? ORDER BY path ASC LIMIT ? OFFSET ?",
                (f"{norm}/%", limit, skip)
            )
        elif parent_path is not None:
            c.execute(
                "SELECT * FROM webbot_page WHERE parent_path = ? ORDER BY title ASC LIMIT ? OFFSET ?",
                (parent_path, limit, skip)
            )
        else:
            # Root: pages with parent_path = '/' OR parent_path IS NULL (legacy orphans)
            c.execute(
                "SELECT * FROM webbot_page WHERE parent_path = '/' OR parent_path IS NULL ORDER BY title ASC LIMIT ? OFFSET ?",
                (limit, skip)
            )
        rows = c.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            # Parse metadata JSON string
            if d.get("metadata"):
                if isinstance(d["metadata"], str):
                    try:
                        d["metadata"] = json.loads(d["metadata"])
                    except json.JSONDecodeError:
                        d["metadata"] = {}
            else:
                d["metadata"] = {}
            # Parse tags (stored as comma-separated or NULL)
            if d.get("tags") is None:
                d["tags"] = []
            elif isinstance(d["tags"], str):
                d["tags"] = [t.strip() for t in d["tags"].split(",") if t.strip()]
            # Check has_children
            page_path = d.get("path", "")
            c2 = conn.cursor()
            c2.execute("SELECT COUNT(*) FROM webbot_page WHERE parent_path = ?", (page_path,))
            d["has_children"] = c2.fetchone()[0] > 0
            c2.close()
            result.append(d)
        return result
    finally:
        conn.close()

def _query_navigation_page_by_path(path: str) -> Optional[dict]:
    """Query a single page from webbot_page by exact path."""
    import sqlite3 as _sqlite3
    conn = _get_webbot_conn()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM webbot_page WHERE path = ?", (path,))
        row = c.fetchone()
        if not row:
            return None
        d = dict(row)
        if d.get("metadata"):
            if isinstance(d["metadata"], str):
                try:
                    d["metadata"] = json.loads(d["metadata"])
                except json.JSONDecodeError:
                    d["metadata"] = {}
        else:
            d["metadata"] = {}
        return d
    finally:
        conn.close()


class PublishRequest(BaseModel):
    html_content: str
    title: Optional[str] = None


PUBLISH_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "publish"
BOARDING_DIR = Path(__file__).resolve().parent.parent / "data" / "boarding"
PUBLISH_APP_SLUG = "publish"

# Canada.ca 域名前缀 — 用于解析远程图片
CANADA_CA_DOMAINS = ["www.canada.ca", "canada.ca"]

# 本地图片来源目录
# 1. content/dam 缓存
LOCAL_DAM_DIR = BOARDING_DIR / "canadasite" / "content" / "dam"
# 2. /etc/designs 目录
DESIGNS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "webbot" / "etc" / "designs"
# 3. 爬取的 butch 缓存（直接丢在数据根目录）
BOARDING_ROOT = BOARDING_DIR / "canadasite"


def _is_webbot_request(request: Request) -> bool:
    """检查是否为WebBot内部请求"""
    return request.headers.get("X-WebBot-Access") == "true"


def _get_publish_app(db: Session):
    """获取publish应用记录"""
    from app.models.app import App
    return db.query(App).filter(App.slug == PUBLISH_APP_SLUG).first()


def _ensure_folder(db: Session, folder_path: str, app_id: str, created_by: str = "webbot"):
    """确保文件夹存在，递归创建父文件夹"""
    folder = db.query(FolderModel).filter(FolderModel.path == folder_path).first()
    if folder:
        return folder

    parent = None
    parent_path = str(Path(folder_path).parent)
    if parent_path and parent_path != "." and parent_path != folder_path:
        parent = _ensure_folder(db, parent_path, app_id, created_by)

    name = Path(folder_path).name
    folder = FolderModel(
        path=folder_path,
        app_id=app_id,
        parent_folder_path=parent.path if parent else None,
        name=name,
        title=name,
        created_by=created_by,
    )
    db.add(folder)
    db.flush()
    logger.info(f"Created folder: {folder_path}")
    return folder


def _find_asset_source(asset_url: str, page_path: str) -> Optional[tuple[bytes, str]]:
    """
    解析资源URL，找到数据源文件（图片、CSS、JS、favicon 等）。
    
    Args:
        asset_url: 资源URL（绝对路径如 /content/dam/xxx.jpg, /etc/designs/xxx.css）
        page_path: 页面在 Webbot 中的原始路径，用于解析相对路径
        
    Returns:
        (bytes, content_type) 或 None
    
    搜索顺序：
    1. content/dam 本地缓存（boarding/canadasite/content/dam/）
    2. /etc/designs 本地目录
    3. boarding 根目录
    4. www.canada.ca 远程下载
    """
    if not asset_url or asset_url.startswith("data:"):
        return None

    parsed = urlparse(asset_url)

    # 跳过非 canada.ca 的外部 URL
    if parsed.netloc and parsed.netloc not in CANADA_CA_DOMAINS:
        logger.debug(f"Skipping external URL: {asset_url}")
        return None

    path_part = parsed.path.lstrip("/")

    # ===== 1. content/dam 缓存 =====
    dam_rel = path_part
    if path_part.startswith("content/dam/"):
        dam_rel = path_part[len("content/dam/"):]
    dam_candidate = LOCAL_DAM_DIR / dam_rel
    if dam_candidate.exists() and dam_candidate.is_file():
        data = dam_candidate.read_bytes()
        import mimetypes
        ct = mimetypes.guess_type(str(dam_candidate))[0] or "application/octet-stream"
        logger.info(f"  ✓ Asset: {asset_url} -> {dam_candidate}")
        return (data, ct)

    # ===== 2. /etc/designs 目录 =====
    des_rel = path_part[len("etc/designs/"):] if path_part.startswith("etc/designs/") else path_part
    des_candidate = DESIGNS_DIR / des_rel
    if des_candidate.exists() and des_candidate.is_file():
        data = des_candidate.read_bytes()
        import mimetypes
        ct = mimetypes.guess_type(str(des_candidate))[0] or "application/octet-stream"
        logger.info(f"  ✓ Asset: {asset_url} -> {des_candidate}")
        return (data, ct)

    # ===== 3. 相对路径（在 boarding 中按原始页面路径解析）=============
    if not parsed.netloc and not asset_url.startswith("/"):
        orig_page_dir = BOARDING_DIR / page_path.lstrip("/")
        orig_page_dir = orig_page_dir.parent
        resolved = (orig_page_dir / asset_url).resolve()
        if resolved.exists() and resolved.is_file():
            data = resolved.read_bytes()
            import mimetypes
            ct = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
            logger.info(f"  ✓ Asset (relative): {asset_url} -> {resolved}")
            return (data, ct)

    # ===== 4. boarding 根目录下直接找 =====
    root_candidate = BOARDING_ROOT / path_part
    if root_candidate.exists() and root_candidate.is_file():
        data = root_candidate.read_bytes()
        import mimetypes
        ct = mimetypes.guess_type(str(root_candidate))[0] or "application/octet-stream"
        logger.info(f"  ✓ Asset: {asset_url} -> {root_candidate}")
        return (data, ct)

    # ===== 5. canada.ca 远程下载 =====
    remote_url = f"https://www.canada.ca/{path_part}"
    try:
        resp = httpx.get(remote_url, follow_redirects=True, timeout=30)
        if resp.status_code == 200:
            ct = resp.headers.get("content-type", "application/octet-stream")
            logger.info(f"  ✓ Asset (remote): {remote_url}")
            return (resp.content, ct)
    except Exception as e:
        logger.warning(f"  Remote fetch failed: {remote_url} -> {e}")

    logger.warning(f"  ✗ Asset not found: {asset_url}")
    return None


def _extract_asset_urls(html: str) -> set[str]:
    """
    从 HTML 中提取所有资源引用 URL（图片、CSS、JS、favicon 等）。
    返回去重的 URL 集合。
    """
    urls = set()

    patterns = [
        # <img src="..."
        (r'<img[^>]*?src\s*=\s*["\']([^"\'\s]+)["\']', re.IGNORECASE),
        # <link href="..."  (CSS, favicon, etc)
        (r'<link[^>]*?href\s*=\s*["\']([^"\'\s]+)["\']', re.IGNORECASE),
        # <script src="..."
        (r'<script[^>]*?src\s*=\s*["\']([^"\'\s]+)["\']', re.IGNORECASE),
    ]

    for pattern, flags in patterns:
        for match in re.finditer(pattern, html, flags):
            url = match.group(1).strip()
            urls.add(url)

    return urls


def _copy_publish_assets(html: str, page_path: str, publish_dir: Path) -> list[dict]:
    """
    扫描HTML中的所有资源引用（图片、CSS、JS、favicon 等），
    复制到 publish 目录，保持与URL路径一致的文件结构。
    不重写HTML中的URL。
    
    publish 独立服务器运行在 8003 端口，把 publish 目录挂载到根路径，
    因此资源路径自动匹配（如 /content/dam/xxx → publish/content/dam/xxx）。
    
    Args:
        html: 原始 HTML 内容
        page_path: 页面原始路径，如 /canadasite/en/contact
        publish_dir: publish 根目录
    
    Returns:
        copied_assets_info list
    """
    copied = []
    asset_urls = _extract_asset_urls(html)
    assets_to_copy = [s for s in sorted(asset_urls) if s and not s.startswith("data:")]

    for src in assets_to_copy:
        # 只处理 /content/dam 或 /etc/designs 下的资源
        is_dam = src.startswith("/content/dam/") or src.startswith("content/dam/")
        is_designs = src.startswith("/etc/designs/") or src.startswith("etc/designs/")
        if not is_dam and not is_designs:
            continue

        parsed = urlparse(src)

        # 跳过外部URL
        if parsed.netloc and parsed.netloc not in CANADA_CA_DOMAINS:
            continue

        # 提取路径（去前导 /）
        url_path = parsed.path.lstrip("/") if parsed.path else ""
        if not url_path:
            continue

        # 目标路径：publish_dir / url_path
        dest = (publish_dir / url_path).resolve()

        # 安全校验（防止 path traversal）
        try:
            dest.relative_to(publish_dir.resolve())
        except ValueError:
            logger.warning(f"  ✗ Path traversal skipped: {src} -> {dest}")
            continue

        # 已存在则跳过
        if dest.exists() and dest.is_file():
            logger.debug(f"  Already exists: {dest}")
            continue

        # 找来源并复制
        logger.info(f"  Copying asset: {src}")
        result = _find_asset_source(src, page_path)
        if result:
            data, ct = result
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            copied.append({
                "src": src,
                "dest": str(dest),
                "size": len(data),
                "content_type": ct,
            })
            logger.info(f"    -> {dest} ({len(data)} bytes)")
        else:
            logger.warning(f"  ✗ Could not resolve source for: {src}")

    return copied

def _save_published_page(html: str, page_path: str, extension: str = ".html") -> tuple[str, int, list[dict]]:
    """
    发布页面：写入HTML + 复制图片。
    去掉 /canadasite 前缀，直接按 /en/xxx 路径写入。
    
    例：/canadasite/en/canadian-heritage → publish/en/canadian-heritage.html
    """
    # 去掉 /canadasite 前缀
    rel_path = page_path.lstrip("/")
    if rel_path.startswith("canadasite/"):
        rel_path = rel_path[len("canadasite/"):]
    output_file = PUBLISH_DIR / f"{rel_path}{extension}"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: 复制资源（图片、CSS、JS等）到 publish 目录
    copied_assets = _copy_publish_assets(html, page_path, PUBLISH_DIR)

    # Step 2: 写入原始HTML（不重写URL）
    output_file.write_text(html, encoding="utf-8")
    html_len = len(html)
    logger.info(f"Published: {output_file} ({html_len} bytes, {len(copied_assets)} assets)")

    return str(output_file), html_len, copied_assets


# ─── CDN Pre-cache ───────────────────────────────────────────────

CDN_BASE = "https://cdn.webfilebot.com"


def _cdn_refresh_paths(url_paths: list[str]):
    """异步刷新 CDN 缓存。GET ?__cache_refresh=1 强制 Worker 回源更新 R2。"""
    def _do():
        with httpx.Client(timeout=10.0) as client:
            for p in url_paths:
                try:
                    r = client.get(f"{CDN_BASE}{p}", params={"__cache_refresh": "1"})
                    if r.status_code == 200:
                        logger.info(f"CDN refreshed: {p}")
                    else:
                        logger.warning(f"CDN refresh {p} → {r.status_code}")
                except Exception as e:
                    logger.warning(f"CDN refresh failed for {p}: {e}")

    threading.Thread(target=_do, daemon=True).start()


def _cdn_delete_paths(url_paths: list[str]):
    """异步删除 CDN 缓存。GET ?__cache_delete=1 强制 Worker 删除 R2。"""
    def _do():
        with httpx.Client(timeout=10.0) as client:
            for p in url_paths:
                try:
                    r = client.get(f"{CDN_BASE}{p}", params={"__cache_delete": "1"})
                    if r.status_code == 200:
                        logger.info(f"CDN deleted: {p}")
                    else:
                        logger.warning(f"CDN delete {p} → {r.status_code}")
                except Exception as e:
                    logger.warning(f"CDN delete failed for {p}: {e}")

    threading.Thread(target=_do, daemon=True).start()


@router.post("/publish")
def publish_page(
    path: str = Query(..., description="Page path, e.g. /canadasite/en/contact"),
    publish_req: PublishRequest = Body(..., description="Published HTML content"),
    output_dir: Optional[str] = Query(None, description="Override output directory"),
    extension: str = Query(".html", description="File extension for published file (e.g. .html, .json)"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    保存发布的页面HTML到publish目录
    仅接受WebBot内部请求（X-WebBot-Access header），
    由WebBot负责外部身份认证和权限控制

    同时会在filebot数据库中创建对应的文件夹和文档记录，
    使发布页面显示在filebot前端的publish应用下。

    处理流程：
    1. 扫描HTML中的<img>标签，解析图片源文件
    2. 将图片复制到 publish 目录
    3. 重写<img src>为 publish 相对路径
    4. 写入重写后的HTML
    5. 创建FileBot数据库记录
    """
    # 安全检查：必须来自WebBot内部
    if not request or not _is_webbot_request(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Only WebBot internal requests are allowed"
        )

    if not path or not path.startswith("/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path must start with /")

    # Step 1: Write HTML file + copy images
    output_file, html_len, copied_images = _save_published_page(
        publish_req.html_content, path, extension
    )

    # 计算 CDN URL 路径
    rel_path = path.lstrip("/")
    if rel_path.startswith("canadasite/"):
        rel_path = rel_path[len("canadasite/"):]
    # 预缓存 HTML 页面 + 所有复制的图片/资源
    cdn_paths = [f"/{rel_path}{extension}"]
    for img in copied_images:
        if img.get("src"):
            cdn_paths.append(img["src"])

    # Step 2: Create database records (folder + document) under publish app
    try:
        publish_app = _get_publish_app(db)
        if not publish_app:
            logger.warning(f"Publish app '{PUBLISH_APP_SLUG}' not found in DB, skipping DB records")
            _cdn_refresh_paths(cdn_paths)
            return {
                "success": True,
                "path": path,
                "output_file": output_file,
                "html_length": html_len,
                "copied_images": copied_images,
                "db_record_created": False,
                "db_warning": f"App '{PUBLISH_APP_SLUG}' not found"
            }

        # Build folder hierarchy under /publish/...
        # 去掉 /canadasite 前缀
        path_parts = rel_path.split("/")
        doc_name = path_parts[-1]  # e.g. "en"
        folder_rel_parts = path_parts[:-1]  # e.g. "canadasite"
        folder_path = f"/{PUBLISH_APP_SLUG}"
        if folder_rel_parts:
            folder_path += "/" + "/".join(folder_rel_parts)
        doc_path = f"{folder_path}/{doc_name}{extension}"

        # Ensure folder exists
        folder = _ensure_folder(db, folder_path, publish_app.id)

        # Determine MIME type and FileType based on extension
        ext_lower = extension.lower()
        if ext_lower == ".json":
            mime_type = "application/json"
            file_type = FileType.OTHER
        elif ext_lower in (".xml", ".txt"):
            mime_type = "application/xml" if ext_lower == ".xml" else "text/plain"
            file_type = FileType.OTHER
        else:
            mime_type = "text/html"
            file_type = FileType.HTML

        # Use passed title, fall back to doc_name
        real_title = (publish_req.title or "").strip() or doc_name

        # Check if document already exists (update it) or create new
        existing_doc = db.query(Document).filter(Document.path == doc_path).first()
        if existing_doc:
            existing_doc.title = real_title
            existing_doc.file_size = html_len
            existing_doc.updated_by = "webbot"
            existing_doc.publish_status = PublishStatus.PUBLISHED
            existing_doc.parent_folder_path = folder_path
            logger.info(f"Updated existing document: {doc_path}")
        else:
            # Find uploader user
            uploader = db.query(User).filter(User.username == "webbot").first()
            if not uploader:
                uploader = db.query(User).filter(User.is_superuser == True).first()
            if not uploader:
                uploader = db.query(User).filter(User.id == publish_app.owner_id).first()
            uploader_id = uploader.id if uploader else publish_app.owner_id

            doc = Document(
                path=doc_path,
                folder_path=folder_path,
                parent_folder_path=folder_path,
                original_filename=f"{doc_name}{extension}",
                stored_filename=f"{doc_name}{extension}",
                file_size=html_len,
                file_type=file_type,
                mime_type=mime_type,
                title=real_title,
                storage_path=output_file,
                full_storage_path=output_file,
                publish_status=PublishStatus.PUBLISHED,
                status=DocStatus.ACTIVE,
                type=DocumentType.GENERAL,
                uploaded_by=uploader_id,
                created_by="webbot",
                conversion_status=None,
                thumbnail_status=ThumbnailStatus.NOT_APPLICABLE,
            )
            db.add(doc)
            logger.info(f"Created document: {doc_path}")

        db.commit()
        logger.info(f"DB records created for published page: {path}")

        _cdn_refresh_paths(cdn_paths)

        return {
            "success": True,
            "path": path,
            "output_file": output_file,
            "html_length": html_len,
            "copied_images": copied_images,
            "db_record_created": True,
            "document_path": doc_path,
            "folder_path": folder_path,
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create DB records for published page: {e}")
        import traceback
        traceback.print_exc()
        # HTML file was already written, pre-cache it anyway
        _cdn_refresh_paths(cdn_paths)
        # return without DB records
        return {
            "success": True,
            "path": path,
            "output_file": output_file,
            "html_length": html_len,
            "copied_images": copied_images,
            "db_record_created": False,
            "db_error": str(e),
        }


@router.post("/unpublish")
def unpublish_page(
    path: str = Query(..., description="Page path, e.g. /canadasite/en/canadian-heritage"),
    extension: str = Query(".html", description="File extension used when published (e.g. .html, .json)"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Unpublish a page: delete from /publish folder and set publish_status to UNPUBLISHED.

    处理流程：
    1. 从 publish 目录删除 HTML 文件
    2. 将 FileBot DB 中的文档 publish_status 设为 UNPUBLISHED
    """
    # 安全检查：必须来自WebBot内部
    if not request or not _is_webbot_request(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Only WebBot internal requests are allowed"
        )

    if not path or not path.startswith("/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path must start with /")

    # 计算 publish 文件路径（与 publish_page 一致）
    rel_path = path.lstrip("/")
    if rel_path.startswith("canadasite/"):
        rel_path = rel_path[len("canadasite/"):]
    publish_file = (PUBLISH_DIR / rel_path).resolve()

    # 安全校验：确保路径在 PUBLISH_DIR 内
    try:
        publish_file.relative_to(PUBLISH_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")

    # 如果没扩展名，使用指定的 extension
    if not publish_file.suffix:
        publish_file = publish_file.with_suffix(extension)

    file_deleted = False
    if publish_file.exists():
        publish_file.unlink()
        file_deleted = True
        logger.info(f"Deleted publish file: {publish_file}")
    else:
        logger.warning(f"Publish file not found: {publish_file}")

    # 更新 DB 记录
    db_updated = False
    try:
        publish_app = _get_publish_app(db)
        if publish_app:
            # 构建 DB 中的 document path
            doc_rel_path = rel_path
            if not doc_rel_path.endswith(extension):
                doc_rel_path += extension
            doc_path = f"/{PUBLISH_APP_SLUG}/{doc_rel_path}"

            existing_doc = db.query(Document).filter(Document.path == doc_path).first()
            if existing_doc:
                existing_doc.publish_status = PublishStatus.UNPUBLISHED
                db.commit()
                db_updated = True
                logger.info(f"Set publish_status=UNPUBLISHED for document: {doc_path}")
            else:
                logger.warning(f"No document found in DB for path: {doc_path}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update DB for unpublish: {e}")

    # 删除 CDN 缓存（只删 HTML 页面，图片由其他页面共享，不过期再删）
    cdn_url_path = f"/{rel_path}"
    if not cdn_url_path.endswith(extension):
        cdn_url_path += extension
    _cdn_delete_paths([cdn_url_path])

    return {
        "success": True,
        "path": path,
        "file_deleted": file_deleted,
        "db_updated": db_updated,
        "publish_file": str(publish_file),
    }


@router.get("/path")
def get_pages_by_path(
    path: str = Query(..., description="Folder path, e.g. /boarding/canadasite/fr"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    include_subfolders: bool = Query(False, description="是否递归包含子文件夹中的文档"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """按文件夹路径获取所有文档的页面
    
    先查 PostgreSQL 的 folders → documents → pages 链路。
    如果文件夹不存在，回退到 SQLite webbot_page（导航页面数据），
    按 parent_path 返回子页面列表。
    """
    if not path or not path.startswith('/'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path must start with /")

    normalized = path.rstrip('/')

    # 先尝试从 PostgreSQL folders 查询
    folder = db.query(FolderModel).filter(FolderModel.path == normalized).first()

    if folder:
        # Postgres documents pages (existing logic)
        if include_subfolders:
            folder_path_prefix = f"{normalized}/"
            subfolders = db.query(FolderModel).filter(
                FolderModel.parent_folder_path.like(f"{folder_path_prefix}%")
            ).all()
            folder_paths = [folder.path] + [f.path for f in subfolders]
            docs = db.query(Document).filter(Document.folder_path.in_(folder_paths)).all()
        else:
            docs = db.query(Document).filter(Document.folder_path == folder.path).all()

        if not docs:
            return []

        doc_paths = [d.path for d in docs]
        pages = db.query(Page).filter(
            Page.document_path.in_(doc_paths)
        ).order_by(Page.document_path, Page.page_number).offset(skip).limit(limit).all()
        return pages

    # 回退到 SQLite webbot_page（导航页面）
    try:
        import sqlite3 as _sqlite3
        if normalized == '':
            # root path → pages with parent_path = '/' OR IS NULL
            parent_path = None
        else:
            parent_path = normalized

        raw = _query_navigation_pages(
            parent_path=parent_path,
            skip=skip,
            limit=limit
        )
        # Convert to NavigationPageItem list
        items = []
        for row in raw:
            items.append(NavigationPageItem(**row))
        return items
    except (_sqlite3.Error, FileNotFoundError) as e:
        logger.warning(f"SQLite fallback failed: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Folder not found: {path}")


@router.get("/", response_model=List[NavigationPageItem])
def list_pages(
    skip: int = 0,
    limit: int = 100,
    path: Optional[str] = Query(None, description="Parent page path, returns direct children. e.g. /en returns pages with parent_path=/en"),
    prefix: Optional[str] = Query(None, description="Path prefix filter, returns all pages whose path starts with this prefix"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """列出导航页面（从 webbot_page SQLite）
    
    - 如果指定 path 参数，返回该路径的直接子页面
    - 如果指定 prefix 参数，返回路径前缀匹配的所有页面
    - 都不指定则返回根页面（parent_path IS NULL）
    """
    import sqlite3 as _sqlite3
    try:
        if prefix:
            # Prefix-based query (recursive)
            raw = _query_navigation_pages(prefix=prefix, skip=skip, limit=limit, order_by="path")
        elif path is not None:
            norm = path.rstrip('/')
            if not norm:
                # path=/ → root pages (parent_path = '/' OR IS NULL)
                raw = _query_navigation_pages(parent_path=None, skip=skip, limit=limit)
            else:
                raw = _query_navigation_pages(parent_path=norm, skip=skip, limit=limit)
        else:
            # Root pages
            raw = _query_navigation_pages(parent_path=None, skip=skip, limit=limit)

        items = [NavigationPageItem(**row) for row in raw]
        return items
    except (_sqlite3.Error, FileNotFoundError) as e:
        logger.warning(f"SQLite query failed: {e}")
        return []


@router.get("/by-path", response_model=SinglePageResponse)
def get_page_by_path(
    path: str = Query(..., description="Full page path, e.g. /canadasite/en"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """根据完整路径获取单个页面详情（从 webbot_page SQLite）"""
    import sqlite3 as _sqlite3
    try:
        d = _query_navigation_page_by_path(path)
        if not d:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Page not found: {path}")

        # Parse tags
        tags = d.get("tags")
        if tags is None:
            tags = []
        elif isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        return SinglePageResponse(
            id=d.get("id", d.get("path", "")),
            title=d.get("title", ""),
            description=d.get("description", ""),
            content=d.get("content", ""),
            language=d.get("language", "en"),
            status=d.get("status", "draft"),
            path=d.get("path"),
            parent_path=d.get("parent_path"),
            other_language_path=d.get("other_language_path"),
            metadata=d.get("metadata"),
            created_at=d.get("created_at"),
            last_modified=d.get("last_modified"),
            keywords=d.get("keywords"),
            hide_in_navigation=bool(d.get("hide_in_navigation", False)),
            scheduled_publish=d.get("scheduled_publish"),
            approved=int(d.get("approved", 0)),
            approved_at=d.get("approved_at"),
            approved_by=d.get("approved_by"),
            current_version=int(d.get("current_version", 0)),
            tags=tags,
        )
    except (_sqlite3.Error, FileNotFoundError) as e:
        logger.warning(f"SQLite by-path query failed: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Page not found: {path}")
