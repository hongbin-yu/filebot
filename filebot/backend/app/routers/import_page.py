"""
Import page from browser bookmarklet.
POST /api/v1/import-page

The bookmarklet runs on canada.ca domain, fetches page HTML (same-origin),
and POSTs it here for storage in FileBot.

The import also pushes the page to WebBot (port 8000) so both systems stay in sync.

Usage:
  curl -X POST http://localhost:8001/api/v1/import-page \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <token>" \
    -d '{
      "url": "https://www.canada.ca/en/services/benefits",
      "html": "<html>...</html>",
      "title": "Benefits"
    }'
"""
import json
import logging
import os
import queue
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import sqlalchemy

import requests as http_requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user_allow_query
from app.db.database import SessionLocal, get_db
from app.models.user import User
from app.models.app import App
from app.models.folder import Folder
from app.models.document import Document, FileType, DocumentStatus, PublishStatus
from app.core.config import settings

# WebBot config
WEBBOT_API_BASE = os.environ.get("WEBBOT_API_BASE", "http://localhost:8000")

logger = logging.getLogger(__name__)

# ── WebBot Token Cache (shared across all import requests) ──────────────
_webbot_token_cache = {"token": None, "expires_at": 0}
_webbot_token_lock = threading.Lock()

# ── Background Import Queue ────────────────────────────────────────────
# WebBot pushes are offloaded here so the bookmarklet returns quickly.
# This uses a simple in-process thread; no Redis required.
_import_worker_thread: threading.Thread = None
_import_worker_lock = threading.Lock()
_import_task_queue = queue.Queue(maxsize=2000)


def _start_import_worker():
    """Start the background worker thread (idempotent)."""
    global _import_worker_thread
    with _import_worker_lock:
        if _import_worker_thread is not None and _import_worker_thread.is_alive():
            return
        _import_worker_thread = threading.Thread(target=_import_worker_loop, daemon=True)
        _import_worker_thread.start()
        logger.info("Background import worker started")


def _import_worker_loop():
    """Background worker: processes queued import tasks in FIFO order."""
    while True:
        try:
            task = _import_task_queue.get()
            if task is None:
                break  # sentinel — allows clean shutdown
            _process_import_task(task)
        except Exception:
            logger.exception("Import worker: unhandled error")


def _process_import_task(task):
    """Process one post-import task (currently: WebBot push)."""
    req, title, target_folder_path, stored_filename, absolute_path = task
    try:
        _push_to_webbot_with_token(req, title, target_folder_path, stored_filename, absolute_path)
    except Exception:
        logger.exception(f"Import worker: WebBot push failed for {req.url}")

router = APIRouter()

# Max path segments for folder depth
MAX_PATH_DEPTH = 10


class ImportPageRequest(BaseModel):
    url: str = Field("", description="Full URL of the page being imported (e.g. https://www.canada.ca/en/...). Can be empty if save_snapshot is set.")
    html: str = Field("", description="Raw HTML content of the page (required if is_image is False)")
    title: str = Field("", description="Page title (optional — auto-extracted from HTML if empty)")
    folder_path: str = Field("", description="Target folder path in FileBot (optional — auto-detected from URL)")
    is_image: bool = Field(False, description="Set to true if this is an image upload")
    image_data: str = Field("", description="Base64-encoded image data (required if is_image is True)")
    redirect_to: Optional[str] = Field(None, description="If set, this page is a redirect. Value is the redirect target URL. When set, backend stores only metadata, no content.")
    save_snapshot: Optional[dict] = Field(None, description="If set, saves a client-side snapshot (bookmarklet baseline). Expected: {sitemap_url, snapshot: {pages, images}}")


class ImportPageResponse(BaseModel):
    success: bool
    path: str
    folder_path: str
    title: str
    stored_filename: str
    file_size: int
    url: str
    redirect_to: str = ""


def extract_title_from_html(html: str) -> str:
    """Extract <title> from HTML, strip ' - Canada.ca' suffix, return empty string if not found."""
    m = re.search(r'<title[^>]*>([^<]+)</title>', html, re.I | re.S)
    if not m:
        return ""
    title = m.group(1).strip()
    # Remove " - Canada.ca" suffix (common on canada.ca pages)
    title = re.sub(r'\s*[-–—]\s*Canada\.ca\s*$', '', title, flags=re.I)
    return title


def download_and_store_dam_images(html: str, page_url: str, current_user) -> tuple[str, int, int]:
    """Download ALL canada.ca images from a page and store locally.
    
    Fetches the ORIGINAL page from canada.ca to extract real image URLs
    (the bookmarklet replaces these in the passed HTML with broken bare filenames).
    Downloads each image, creates a FileBot Document record, and rewrites the
    fresh copy of the HTML with correct /content/dam/... paths.
    
    - /content/dam/... images → stored at original path (served by existing proxy)
    - Non-DAM images (/content/canadasite/..., AEM adaptive) → stored at
      /content/dam/{path_before_jcr_content}/{filename}
      (path hierarchy preserved, only _jcr_content/... stripped)
    
    Returns: (rewritten_html, downloaded_count, error_count)
        rewritten_html: fresh page HTML with all image URLs pointing to
            locally-served /content/dam/... paths.
        downloaded_count: number of images successfully processed
        error_count: number of images that failed
    """
    from pathlib import Path
    
    data_root = Path(settings.FILE_STORAGE_PATH).resolve()
    if not data_root.exists():
        data_root = Path(settings.DATA_ROOT).resolve()
    
    db = SessionLocal()
    downloaded = 0
    errors = 0
    
    # ── Step 1: Fetch original page HTML from canada.ca ──
    # The bookmarklet-modified req.html has broken image URLs (bare filenames).
    # We need the original page to get real image URLs.
    try:
        orig_resp = http_requests.get(page_url, timeout=30, 
                                       headers={"User-Agent": "FileBot-Import/1.0"})
        if orig_resp.status_code != 200:
            logger.warning(f"  ⚠️  Could not fetch original page (HTTP {orig_resp.status_code}), "
                           f"falling back to provided HTML")
            original_html = html
        else:
            original_html = orig_resp.text
            logger.info(f"  📄 Fetched original page ({len(original_html)} bytes)")
    except Exception as e:
        logger.warning(f"  ⚠️  Could not fetch original page: {e}, falling back to provided HTML")
        original_html = html
    
    # ── Step 2: Extract ALL image URLs from the ORIGINAL page HTML ──
    image_urls = {}  # url_rel_path → {remote: str, doc_path: str, needs_rewrite: bool}
    
    for m in re.finditer(r'''<img[^>]+src=(["'])([^"']+)\1''', original_html, re.IGNORECASE):
        src = m.group(2).strip()
        if not src:
            continue
        # Skip data URIs and system /etc/ designs
        if src.startswith('data:') or '/etc/designs/' in src:
            continue
        
        # Resolve to absolute URL
        if src.startswith('http'):
            parsed = urlparse(src)
            if 'canada.ca' not in parsed.netloc:
                continue
            rel_path = parsed.path
            remote_url = src
        else:
            rel_path = src
            remote_url = f"https://www.canada.ca{src}" if src.startswith('/') else None
            if not remote_url:
                continue
        
        # Normalize: ensure starts with /
        if not rel_path.startswith('/'):
            rel_path = '/' + rel_path
        
        # Skip /etc/designs/ (WET template assets, served locally via Vite proxy)
        if '/etc/designs/' in rel_path:
            continue
        
        if rel_path in image_urls:
            continue  # Already seen
        
        # Determine document path and whether HTML needs rewriting
        # Strip _jcr_content from ALL paths (both DAM and non-DAM)
        clean_path = rel_path
        if '/content/dam/' in rel_path:
            # DAM image — may contain _jcr_content from adaptive imaging
            needs_rewrite = False
        else:
            # Non-DAM → store under /content/dam/{original_path}
            needs_rewrite = True

        # Strip /content/canadasite prefix from canada.ca AEM pages
        if clean_path.startswith('/content/canadasite'):
            clean_path = clean_path[len('/content/canadasite'):]

        # Check for _jcr_content — indicates AEM rendered/cached image
        jcr_idx = clean_path.find('/_jcr_content')
        if jcr_idx != -1:
            filename_part = clean_path[jcr_idx:]
            orig_fn = os.path.basename(filename_part.rstrip('/'))
            if '/content/dam/' in rel_path:
                # DAM URL: preserve folder structure before _jcr_content
                # e.g. /content/dam/canadasite/en/_jcr_content/img.jpg → /content/dam/canadasite/en/img.jpg
                clean_path = clean_path[:jcr_idx]
                if orig_fn not in ('', '/'):
                    clean_path = clean_path.rstrip('/') + '/' + orig_fn
            else:
                # Non-DAM URL: preserve folder hierarchy before _jcr_content
                # Same rule as DAM: strip _jcr_content but keep folders & filename
                # e.g. /en/benefits/_jcr_content/renditions/img.jpg → /en/benefits/img.jpg
                clean_path = clean_path[:jcr_idx]
                if orig_fn not in ('', '/'):
                    clean_path = clean_path.rstrip('/') + '/' + orig_fn

        if '/content/dam/' in rel_path:
            # DAM image: store at cleaned path under /content/dam/
            if rel_path != clean_path:
                doc_path = clean_path
                needs_rewrite = True
            else:
                doc_path = clean_path
        else:
            # Non-DAM: preserve path hierarchy under /content/dam/
            # _jcr_content already stripped above
            doc_path = f"/content/dam{clean_path}"
        
        image_urls[rel_path] = {
            "remote": remote_url,
            "doc_path": doc_path,
            "needs_rewrite": needs_rewrite,
        }
    
    if not image_urls:
        logger.info("No images found in original page, skipping download")
        db.close()
        return (html, 0, 0)
    
    logger.info(f"Found {len(image_urls)} images to process")
    
    # ── Step 3: Download ALL images in parallel ──
    # Track what to rewrite: for non-DAM images, replace rel_path with doc_path
    rewrite_map = {}  # rel_path → doc_path  (only for non-DAM)
    
    # Phase 3a: Concurrent download — this is the bottleneck for slow pages
    # We use a ThreadPoolExecutor so N image downloads happen concurrently
    # instead of sequentially. SQLite serializes writes anyway, so the
    # HTTP fetch phase is where parallelism matters most.
    MAX_CONCURRENT_DOWNLOADS = min(len(image_urls), 10)  # cap to avoid rate-limit hammering
    
    download_results = {}  # doc_path → {content, content_type, rel_path, doc_path, remote_url, needs_rewrite}
    
    # First pass: skip already-existing images to avoid redundant work
    for rel_path, info in sorted(image_urls.items()):
        existing = db.query(Document).filter(Document.path == info["doc_path"]).first()
        if existing:
            logger.info(f"  ⏭️  Image already exists: {info['doc_path']}")
            if info["needs_rewrite"]:
                rewrite_map[rel_path] = info["doc_path"]
        else:
            download_results[info["doc_path"]] = {
                "rel_path": rel_path,
                "doc_path": info["doc_path"],
                "remote_url": info["remote"],
                "needs_rewrite": info["needs_rewrite"],
            }
    
    def _download_one(doc_path: str, remote_url: str) -> dict:
        """Download a single image. Returns result dict or error dict."""
        try:
            resp = http_requests.get(
                remote_url, timeout=30,
                headers={"User-Agent": "FileBot-Import/1.0"},
            )
            if resp.status_code != 200:
                return {"doc_path": doc_path, "error": f"HTTP {resp.status_code}"}
            content_type = resp.headers.get("Content-Type", "application/octet-stream")
            url_path = urlparse(remote_url).path
            orig_ext = os.path.splitext(url_path)[1].lower()
            return {
                "doc_path": doc_path,
                "content": resp.content,
                "content_type": content_type,
                "url_ext": orig_ext,
            }
        except Exception as e:
            return {"doc_path": doc_path, "error": str(e)}
    
    to_download = [
        (d["doc_path"], d["remote_url"])
        for d in download_results.values()
    ]
    
    if to_download:
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS) as pool:
            futures = {
                pool.submit(_download_one, dp, url): dp
                for dp, url in to_download
            }
            for future in as_completed(futures):
                result = future.result()
                dp = result["doc_path"]
                if "error" in result:
                    logger.warning(f"  ⚠️  Failed to download {dp}: {result['error']}")
                    download_results[dp]["error"] = True
                else:
                    download_results[dp]["content"] = result["content"]
                    download_results[dp]["content_type"] = result["content_type"]
                    download_results[dp]["url_ext"] = result["url_ext"]
    
    # ── Step 4: Process downloaded images sequentially (DB writes) ──
    valid_exts = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg', '.tiff', '.tif', '.ico'}
    ft_map = {
        '.png': FileType.PNG, '.jpg': FileType.JPEG, '.jpeg': FileType.JPEG,
        '.gif': FileType.GIF, '.webp': FileType.WEBP, '.bmp': FileType.BMP,
        '.svg': FileType.SVG, '.tiff': FileType.TIFF, '.tif': FileType.TIFF,
        '.ico': FileType.OTHER,
    }
    ext_map = {
        'image/png': '.png', 'image/jpeg': '.jpg', 'image/jpg': '.jpg',
        'image/gif': '.gif', 'image/webp': '.webp', 'image/bmp': '.bmp',
        'image/svg+xml': '.svg', 'image/tiff': '.tiff', 'image/x-icon': '.ico',
    }
    
    for d in download_results.values():
        if d.get("error"):
            errors += 1
            continue
        
        content = d.get("content")
        if content is None:
            errors += 1
            continue
        
        file_size = len(content)
        content_type = d.get("content_type", "application/octet-stream")
        doc_path = d["doc_path"]
        rel_path = d["rel_path"]
        
        url_ext = d.get("url_ext", "")
        if url_ext in valid_exts:
            ext = url_ext
        else:
            ext = ext_map.get(content_type, '.png')
        
        file_type = ft_map.get(ext, FileType.PNG)
        
        storage_rel = doc_path.lstrip('/')
        storage_rel = f"files/boarding/canadasite/{storage_rel}"
        abs_path = data_root / storage_rel
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_bytes(content)
        
        folder_path = str(Path(doc_path).parent)
        
        # Ensure folder hierarchy exists in DB
        try:
            boarding_app = db.query(App).filter(App.slug == 'boarding').first()
            root_app_id = boarding_app.id if boarding_app else None
            _parts = folder_path.strip('/').split('/')
            _cur = ''
            for _part in _parts:
                _cur = _cur + '/' + _part if _cur else '/' + _part
                _exist = db.query(Folder).filter(Folder.path == _cur).first()
                if not _exist:
                    _parent = '/'.join(_cur.split('/')[:-1]) or None
                    _folder_app_id = root_app_id
                    if _parent:
                        _pf = db.query(Folder).filter(Folder.path == _parent).first()
                        if _pf and _pf.app_id:
                            _folder_app_id = _pf.app_id
                    _f = Folder(
                        path=_cur,
                        parent_folder_path=_parent,
                        name=_part,
                        app_id=_folder_app_id,
                        created_by=str(current_user.id),
                    )
                    db.add(_f)
                    db.flush()
        except Exception as e:
            logger.warning(f"  ⚠️  Folder creation warning for {folder_path}: {e}")
        
        page_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now()
        
        try:
            doc = Document(
                path=doc_path,
                folder_path=folder_path,
                document_number=page_id,
                title=os.path.splitext(os.path.basename(doc_path))[0] or "Imported Image",
                original_filename=os.path.basename(doc_path),
                stored_filename=os.path.basename(doc_path),
                file_size=file_size,
                file_type=file_type,
                mime_type=content_type or "image/png",
                storage_path=storage_rel,
                status=DocumentStatus.ACTIVE,
                publish_status=PublishStatus.PUBLISHED,
                document_metadata={
                    "source_url": d["remote_url"],
                    "imported_at": timestamp.isoformat(),
                    "import_method": "bookmarklet_image_download",
                    "url": doc_path,
                },
                uploaded_by=str(current_user.id),
                created_at=timestamp,
                created_by=str(current_user.id),
            )
            db.add(doc)
            db.commit()
            downloaded += 1
            logger.info(f"  ✅ Downloaded & stored: {doc_path} ({file_size} bytes, {content_type})")
            if d.get("needs_rewrite"):
                rewrite_map[rel_path] = doc_path
        except Exception as e:
            db.rollback()
            logger.warning(f"  ❌ Failed to create document for {doc_path}: {e}")
            errors += 1
    
    db.close()
    logger.info(f"📸 Image download complete: {downloaded} saved, {errors} errors")
    
    # ── Step 4: Rewrite HTML ──
    # Start from the ORIGINAL page HTML (fresh from canada.ca) and replace
    # non-DAM image URLs with /content/dam/imported/... paths.
    # /content/dam/ images are left as-is — they already work via the existing proxy.
    if rewrite_map:
        rewritten_html = original_html
        for old_path, new_path in sorted(rewrite_map.items(), key=lambda x: -len(x[0])):
            rewritten_html = rewritten_html.replace(old_path, new_path)
        logger.info(f"  ✏️  Rewrote {len(rewrite_map)} image URLs in HTML")
        return (rewritten_html, downloaded, errors)
    else:
        # No non-DAM images to rewrite; use original HTML with /content/dam/ URLs untouched
        return (original_html, downloaded, errors)

def url_to_path_segments(url: str) -> list[str]:
    """Convert a URL path to folder/name segments, filtering empty segments.
    Preserves language prefix (/en/, /fr/) as part of the content hierarchy.
    Strips /content/canadasite prefix from canada.ca AEM-style URLs.
    """
    parsed = urlparse(url)
    path = parsed.path.rstrip('/')
    # Strip /content/canadasite prefix (canada.ca AEM URLs)
    if path.startswith('/content/canadasite'):
        path = path[len('/content/canadasite'):]
    segments = [s for s in path.split('/') if s]
    return segments


def ensure_folder_hierarchy(db: Session, root_folder_path: str, segments: list[str], uploaded_by: str) -> str:
    """
    Walk the folder hierarchy, creating missing folders as needed.
    Returns the leaf folder path.
    """
    current_path = root_folder_path.rstrip('/')

    # Find app_id once
    root_folder = db.query(Folder).filter(Folder.path == root_folder_path).first()
    app_id = root_folder.app_id if root_folder else None
    if not app_id:
        boarding_app = db.query(App).filter(App.slug == 'boarding').first()
        if boarding_app:
            app_id = boarding_app.id

    for seg in segments:
        # Strip .html from URL segments that are page files, not directories
        seg = seg[:-5] if seg.endswith('.html') else seg
        parent_path = current_path
        current_path = parent_path + '/' + seg

        existing = db.query(Folder).filter(Folder.path == current_path).first()
        if not existing:
            folder = Folder(
                path=current_path,
                parent_folder_path=parent_path,
                name=seg,
                app_id=app_id,
                created_by=uploaded_by,
                created_at=datetime.now(),
            )
            db.add(folder)
            db.flush()

    return current_path


def get_or_create_default_app() -> str:
    """
    Get or create a default app for imported pages.
    Returns the root folder path (/boarding/canadasite).
    """
    db: Session = SessionLocal()
    try:
        app = db.query(App).filter(App.slug == "canadasite").first()
        if app:
            return "/boarding/canadasite"

        app_id = str(uuid.uuid4())
        app = App(
            id=app_id,
            name="Canada.ca Import",
            slug="canadasite",
            description="Auto-created for imported pages from canada.ca bookmarklet",
            created_by="system",
        )
        db.add(app)
        db.flush()

        root_path = "/boarding/canadasite"
        folder = Folder(
            path=root_path,
            parent_folder_path="/boarding",
            name="canadasite",
            app_id=app_id,
            created_by="system",
        )
        db.add(folder)
        db.commit()
        return root_path
    except Exception as e:
        db.rollback()
        logger.warning(f"Could not create default app, may already exist: {e}")
        import traceback
        logger.warning(traceback.format_exc())
        return "/boarding/canadasite"
    finally:
        db.close()


def _get_webbot_token() -> str:
    """
    Get a cached WebBot auth token, refreshing only when close to expiry.
    This eliminates `n * login` overhead when N concurrent publishers
    push pages to WebBot simultaneously.
    """
    with _webbot_token_lock:
        now = time.time()
        # Refresh 2 minutes before expiry (typical tokens: 7 days)
        if _webbot_token_cache["token"] and now < _webbot_token_cache["expires_at"] - 120:
            return _webbot_token_cache["token"]

        login_resp = http_requests.post(
            f"{WEBBOT_API_BASE}/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"},
            timeout=10,
        )
        if login_resp.status_code != 200:
            logger.warning(f"WebBot login failed: {login_resp.status_code} {login_resp.text[:200]}")
            raise HTTPException(status_code=502, detail="WebBot login failed")

        data = login_resp.json()
        token = data["access_token"]
        # JWT tokens typically expire in ACCESS_TOKEN_EXPIRE_MINUTES (default: 7 days)
        expires_in = data.get("expires_in", 7 * 24 * 3600)
        _webbot_token_cache["token"] = token
        _webbot_token_cache["expires_at"] = now + expires_in
        logger.info("🔄 Refreshed WebBot auth token")
        return token


def _push_to_webbot_with_token(req: ImportPageRequest, title: str,
                                target_folder_path: str, stored_filename: str,
                                absolute_path: Path):
    """
    Push the imported page to WebBot (port 8000) so it appears in the
    WebBot page tree. Uses cached auth token — no login per request.
    Non-fatal: errors are logged but never raise.
    """
    try:
        webbot_token = _get_webbot_token()

        # 2. Build full WebBot page path from folder + stored filename
        #    target_folder_path: /boarding/canadesite/fr/services/defense
        #    stored_filename:    securiserfrontiere.html
        #    webbot_page_path:   /canadasite/fr/services/defense/securiserfrontiere
        if stored_filename:
            page_name = stored_filename
            if page_name.endswith('.html'):
                page_name = page_name[:-5]
            # Full path = (folder path - /boarding) + / + page name (no .html)
            if target_folder_path.startswith("/boarding/"):
                folder_path = target_folder_path[len("/boarding"):]
            else:
                folder_path = target_folder_path
            webbot_path = folder_path.rstrip('/') + '/' + page_name
        else:
            # Fallback if no filename (should not happen)
            if target_folder_path.startswith("/boarding/"):
                webbot_path = target_folder_path[len("/boarding"):]
            else:
                webbot_path = target_folder_path

        # For redirect pages: use PUT to update existing page metadata
        if req.redirect_to:
            redirect_webbot_path = webbot_path
            logger.info(f"🔀 Updating redirect metadata on WebBot page: {redirect_webbot_path}")
            redirect_payload = {
                "metadata": {
                    "redirect_to": req.redirect_to,
                    "import_method": "bookmarklet",
                },
            }
            put_resp = http_requests.put(
                f"{WEBBOT_API_BASE}/api/v1/pages/{redirect_webbot_path}",
                json=redirect_payload,
                headers={"Authorization": f"Bearer {webbot_token}"},
                timeout=15,
            )
            if put_resp.status_code in (200, 201):
                logger.info(f"   ✅ Redirect metadata updated: {redirect_webbot_path} -> {req.redirect_to}")
            else:
                logger.warning(f"   ⚠️ Redirect update status {put_resp.status_code}: {put_resp.text[:200]}")
            return  # Done for redirects - don't try to overwrite real content

        # Build language from URL path
        parsed = urlparse(req.url)
        path_segments = [s for s in parsed.path.split('/') if s]
        lang = "en"  # default
        if path_segments and path_segments[0] in ("en", "fr", "zh"):
            lang = path_segments[0]

        # Read the HTML content
        html_content = absolute_path.read_text(encoding="utf-8") if absolute_path.exists() else req.html

        # ---- Extract Canada.ca metadata from HTML ----
        def _extract_meta_content(pattern: str) -> str:
            m = re.search(pattern, html_content, re.I | re.S)
            return m.group(1).strip() if m else ""

        # other_language_path: <link rel="alternate" hreflang="{other}" ...> of the OTHER language
        #   → webbot path: prepend /canadasite
        # Only accept the other language's alternate (en page → hreflang="fr"; fr page → hreflang="en").
        # Never accept the page's own alternate (self-link) as other_language_path.
        other_language_path = ""
        other_hreflang = {"en": "fr", "fr": "en"}.get(lang)
        if other_hreflang:
            alt_link = re.search(
                rf'<link[^>]*rel=[\"\']alternate[\"\'][^>]*hreflang=[\"\']{other_hreflang}[\"\'][^>]*href=[\"\']([^\"\']+)[\"\']',
                html_content, re.I
            )
            if not alt_link:
                alt_link = re.search(
                    rf'<link[^>]*hreflang=[\"\']{other_hreflang}[\"\'][^>]*rel=[\"\']alternate[\"\'][^>]*href=[\"\']([^\"\']+)[\"\']',
                    html_content, re.I
                )
            if alt_link:
                alt_path = alt_link.group(1)
                # Strip full domain prefix if present
                alt_path = re.sub(r'^https?://(www\.)?canada\.ca', '', alt_path, flags=re.I)
                # Strip .html suffix
                if alt_path.endswith('.html'):
                    alt_path = alt_path[:-5]
                # Convert /fr/... → /canadasite/fr/...
                alt_path = alt_path.rstrip('/')
                if alt_path.startswith('/'):
                    other_language_path = '/canadasite' + alt_path
                else:
                    other_language_path = '/canadasite/' + alt_path
                # Final guard: never self-point
                if other_language_path == webbot_path:
                    other_language_path = ""

        # subjects from <meta name="dcterms.subject" content="...">
        subjects = _extract_meta_content(
            r'<meta[^>]*name=[\"\']dcterms\.subject[\"\'][^>]*content=[\"\']([^\"\']+)[\"\']'
        )

        # audience from <meta name="dcterms.audience" content="...">
        audience = _extract_meta_content(
            r'<meta[^>]*name=[\"\']dcterms\.audience[\"\'][^>]*content=[\"\']([^\"\']+)[\"\']'
        )

        # 3. Upsert page in WebBot — direct DB write, same as import-to-webbot.
        #    Existing pages get UPDATED (content/title/metadata/last_modified),
        #    not skipped, so bookmarklet re-imports refresh WebBot content.
        from app.routers.import_to_webbot import ensure_page_exists, get_webbot_conn

        # file_path 语义 = FileBot 资源目录路径，格式 /canadasite/content/dam/{页面路径}
        # 注意：只给 file_path 元数据加 /content/dam 前缀；webbot_path 保持页面树路径（修复 2026-08-09：之前改写了 webbot_path 本身，导致 bookmarklet 导入页面进了 DAM 树，页面树看不到）
        file_path = webbot_path
        if file_path.startswith("/canadasite/") and "/content/dam" not in file_path:
            file_path = file_path.replace("/canadasite/", "/canadasite/content/dam/", 1)

        parent_path = '/'.join(webbot_path.rstrip('/').split('/')[:-1]) or None
        metadata = {
            "source_url": req.url,
            "file_path": file_path,  # 资源目录路径(如 /canadasite/content/dam/en/services/jobs)，非磁盘绝对路径(曾导致 Resources/Images 找不到图)
            "imported_at": datetime.now().isoformat(),
            "import_method": "bookmarklet",
        }
        if req.redirect_to:
            metadata["redirect_to"] = req.redirect_to
        if subjects:
            metadata["subjects"] = subjects
        if audience:
            metadata["audience"] = audience

        conn = get_webbot_conn()
        try:
            cursor = conn.cursor()
            existing = cursor.execute(
                "SELECT hide_in_navigation, metadata FROM webbot_page WHERE path = ?",
                (webbot_path,),
            ).fetchone()

            # Preserve editor-set metadata (merge import fields on top)
            if existing and existing["metadata"]:
                try:
                    old_meta = json.loads(existing["metadata"]) if isinstance(existing["metadata"], str) else dict(existing["metadata"] or {})
                    old_meta.update(metadata)
                    metadata = old_meta
                except Exception:
                    pass

            result = ensure_page_exists(
                cursor,
                path=webbot_path,
                parent_path=parent_path,
                title=title,
                content=html_content,
                language=lang,
                status="published",
                metadata=metadata,
                hide_in_nav=bool(existing and existing["hide_in_navigation"]),
                other_language_path=other_language_path or None,
            )
            conn.commit()
            logger.info(f"✅ WebBot page {result}: {webbot_path}")
        finally:
            conn.close()

    except Exception as e:
        logger.warning(f"WebBot push failed (non-fatal): {e}")


def _handle_image_upload(req: ImportPageRequest, current_user: User) -> ImportPageResponse:
    """Handle image upload from bookmarklet.
    Saves base64 image data to disk, creates Document record.
    """
    import base64

    image_data = req.image_data
    if not image_data:
        raise HTTPException(status_code=400, detail="image_data is required when is_image is true")

    # Decode base64 — strip data URI prefix if present
    if ',' in image_data:
        # e.g. "data:image/png;base64,iVBORw0KGgo..."
        header, _, b64 = image_data.partition(',')
        # Detect mime type from header
        mime_match = re.match(r'^data:(image/\w+)', header)
        mime_type = mime_match.group(1) if mime_match else 'image/png'
    else:
        mime_type = 'image/png'
        b64 = image_data

    try:
        raw_bytes = base64.b64decode(b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image data")

    # Determine extension from mime type
    ext_map = {
        'image/png': 'png',
        'image/jpeg': 'jpg',
        'image/jpg': 'jpg',
        'image/gif': 'gif',
        'image/webp': 'webp',
        'image/bmp': 'bmp',
        'image/svg+xml': 'svg',
        'image/tiff': 'tiff',
    }
    valid_exts = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg', '.tiff', '.tif', '.ico'}
    ext = ext_map.get(mime_type, 'png')

    # FileType mapping
    ft_map = {
        'png': FileType.PNG,
        'jpg': FileType.JPEG,
        'jpeg': FileType.JPEG,
        'gif': FileType.GIF,
        'webp': FileType.WEBP,
        'bmp': FileType.BMP,
        'svg': FileType.SVG,
        'tiff': FileType.TIFF,
    }
    file_type = ft_map.get(ext, FileType.OTHER)

    # URL path → folder determination
    # Always extract original filename from the URL first
    parsed = urlparse(req.url)
    url_path = parsed.path.rstrip('/')
    original_filename = os.path.basename(url_path.rstrip('/'))
    if original_filename in ('', '/'):
        original_filename = 'image'

    # Save parsed_url_path before any stripping (for DAM check)
    parsed_url_path = url_path

    # If folder_path explicitly provided, use it directly
    if req.folder_path:
        target_folder_path = req.folder_path.rstrip('/')
    else:
        # Strip /content/canadasite prefix (canada.ca AEM pages)
        if url_path.startswith('/content/canadasite'):
            url_path = url_path[len('/content/canadasite'):]

        # Strip _jcr_content and everything after (all paths)
        jcr_idx = url_path.find('/_jcr_content')
        had_jcr_content = jcr_idx != -1
        if had_jcr_content:
            url_path = url_path[:jcr_idx]

        path_segments = [s for s in url_path.split('/') if s]

        # Use /content/dam/ root so images are served by the proxy
        root = "/boarding/canadasite/content/dam"

        # For DAM URLs, strip the /content/dam/ prefix from url_path
        # so we don't get /content/dam/content/dam/...
        if '/content/dam/' in parsed_url_path:
            dam_rel = re.sub(r'^/?content/dam/', '', url_path)
            dam_segs = [s for s in dam_rel.split('/') if s]
            if dam_segs:
                if had_jcr_content:
                    # _jcr_content stripped, ALL segments are folders
                    target_folder_path = root + '/' + '/'.join(dam_segs)
                else:
                    # Last segment is filename
                    target_folder_path = root + '/' + '/'.join(dam_segs[:-1]) if len(dam_segs) > 1 else root
            else:
                target_folder_path = root
        elif had_jcr_content:
            # Non-DAM _jcr_content: all remaining segments are folders
            # original_filename holds the actual filename
            target_folder_path = root + '/' + '/'.join(path_segments) if path_segments else root
        elif path_segments:
            # No _jcr_content: last segment is the filename
            target_folder_path = root + '/' + '/'.join(path_segments[:-1]) if len(path_segments) > 1 else root
        else:
            target_folder_path = root

    # Use the ORIGINAL filename from the URL, not the truncated path
    # (filename cap raised 64 -> 255 so long URLs are not silently cut; 2026-08-13)
    basename = original_filename
    # Preserve the original extension when it's a known image extension
    # (e.g. photo.jpeg stays photo.jpeg instead of being forced to .jpg),
    # so the stored file matches the extension referenced in the HTML.
    orig_ext = os.path.splitext(basename)[1].lower()
    if orig_ext in valid_exts:
        ext = orig_ext[1:]
        file_type = ft_map.get(ext, FileType.OTHER)
    # Remove existing extension if any, use our ext
    basename = re.sub(r'\.[^./]+$', '', basename)
    # Keep dots in the base name (e.g. image.img.jpg → image.img)
    safe_name = re.sub(r'[^a-zA-Z0-9_\-.]', '_', basename)[:255]
    stored_filename = f"{safe_name}.{ext}"

    # Save to disk
    doc_rel_dir = target_folder_path.lstrip('/')
    data_root = Path(settings.FILE_STORAGE_PATH).resolve()
    if not data_root.exists():
        data_root = Path(settings.DATA_ROOT).resolve()
    absolute_dir = data_root / doc_rel_dir
    absolute_dir.mkdir(parents=True, exist_ok=True)
    absolute_path = absolute_dir / stored_filename
    
    # 同名文件直接覆盖（旧文件应在删除文档记录时同步删除）
    absolute_path.write_bytes(raw_bytes)

    doc_path = target_folder_path + '/' + stored_filename
    file_size = len(raw_bytes)

    title = req.title.strip() or basename or "Imported Image"
    if len(title) > 255:
        title = title[:252] + "..."

    # Ensure folder exists in DB
    db: Session = SessionLocal()
    try:
        # Find app_id for folder creation (relevant for image paths not yet in DB)
        boarding_app = db.query(App).filter(App.slug == 'boarding').first()
        root_app_id = boarding_app.id if boarding_app else None

        folder = db.query(Folder).filter(Folder.path == target_folder_path).first()
        if not folder:
            # Build parent chain
            parts = target_folder_path.strip('/').split('/')
            cur = ''
            for pt in parts:
                pt = pt[:-5] if pt.endswith('.html') else pt  # strip .html from folder names
                cur = cur + '/' + pt if cur else '/' + pt
                exist = db.query(Folder).filter(Folder.path == cur).first()
                if not exist:
                    parent = '/'.join(cur.split('/')[:-1]) or None
                    f = Folder(
                        path=cur,
                        parent_folder_path=parent,
                        name=pt,
                        app_id=root_app_id,
                        created_by=str(current_user.id),
                    )
                    db.add(f)
                    db.flush()

        # Create document
        existing = db.query(Document).filter(Document.path == doc_path).first()
        if existing:
            existing.file_size = file_size
            existing.document_metadata = {
                **(existing.document_metadata or {}),
                "source_url": req.url,
                "imported_at": datetime.now().isoformat(),
                "is_image": True,
            }
            db.commit()
            return ImportPageResponse(
                success=True,
                path=existing.path,
                folder_path=target_folder_path,
                title=title,
                stored_filename=stored_filename,
                file_size=file_size,
                url=req.url,
            )

        doc = Document(
            path=doc_path,
            folder_path=target_folder_path,
            title=title,
            original_filename=stored_filename,
            stored_filename=stored_filename,
            file_size=file_size,
            file_type=file_type,
            mime_type=mime_type,
            storage_path=str(absolute_path),
            status=DocumentStatus.ACTIVE,
            publish_status=PublishStatus.UNPUBLISHED,
            document_metadata={
                "source_url": req.url,
                "imported_at": datetime.now().isoformat(),
                "import_method": "bookmarklet_image",
                "is_image": True,
            },
            uploaded_by=str(current_user.id),
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        logger.info(f"🖼 Created image document: {doc_path} ({file_size} bytes)")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create image document for {req.url}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create image: {str(e)}")
    finally:
        db.close()

    return ImportPageResponse(
        success=True,
        path=doc_path,
        folder_path=target_folder_path,
        title=title,
        stored_filename=stored_filename,
        file_size=file_size,
        url=req.url,
    )


class CheckUrlsRequest(BaseModel):
    urls: List[str] = Field(..., description="List of URLs to check against existing documents")


class CheckUrlsResponse(BaseModel):
    existing: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Map of URL → imported_at ISO timestamp for URLs that already exist"
    )
    checked: int = 0


@router.post("/check-urls", response_model=CheckUrlsResponse)
def check_urls(
    req: CheckUrlsRequest,
    current_user: User = Depends(get_current_active_user_allow_query),
    db: Session = Depends(get_db),
):
    """
    Check which URLs already exist in FileBot.
    Used by the bookmarklet to skip already-imported pages.
    """
    from sqlalchemy import or_

    if not req.urls:
        return CheckUrlsResponse(existing_urls=[], checked=0)

    try:
        conditions = [
            Document.document_metadata['source_url'].as_string() == url
            for url in req.urls
        ]
        existing_docs = db.query(Document).filter(or_(*conditions)).all()

        existing = {}
        for doc in existing_docs:
            meta = doc.document_metadata or {}
            src = meta.get('source_url', '')
            if src and src not in existing:
                existing[src] = meta.get('imported_at')

        return CheckUrlsResponse(
            existing=existing,
            checked=len(req.urls),
        )
    except Exception as e:
        logger.error(f"check-urls failed: {e}")
        return CheckUrlsResponse(existing={}, checked=len(req.urls))




# ── Redirect Target Resolver ────────────────────────────────────────

def _resolve_redirect_target(url: str) -> Optional[str]:
    """Fetch the URL (following redirects) to discover the final target URL.
    
    When the bookmarklet encounters an opaqueredirect (CORS opaque), it cannot 
    see the Location header. The backend handles resolution instead.
    Returns the final resolved URL, or None on failure.
    """
    if not url:
        return None
    try:
        resp = http_requests.get(
            url,
            timeout=15,
            allow_redirects=True,
            headers={"User-Agent": "FileBot-Import/1.0 (redirect resolver)"},
        )
        if resp.status_code == 200 and resp.url != url:
            logger.info(f"  🔀 Redirect resolved: {url} \u2192 {resp.url}")
            return resp.url
        elif resp.status_code == 200:
            logger.info(f"  🔀 Redirect marked but no actual redirect for {url}")
            return None
        else:
            logger.warning(f"  \u26a0\ufe0f  Redirect resolver got HTTP {resp.status_code} for {url}")
            return None
    except Exception as e:
        logger.warning(f"  \u26a0\ufe0f  Redirect resolver failed for {url}: {e}")
        return None

class ResolveRedirectRequest(BaseModel):
    url: str = Field(..., description="URL to resolve redirect target for")

class ResolveRedirectResponse(BaseModel):
    redirect_url: Optional[str] = Field(None, description="Final redirect target URL, or null if not a redirect")

@router.post("/resolve-redirect", response_model=ResolveRedirectResponse)
def resolve_redirect(
    req: ResolveRedirectRequest,
    current_user: User = Depends(get_current_active_user_allow_query),
):
    """Resolve the redirect target of a URL server-side (no CORS issues).
    
    Called by the bookmarklet when it detects a 3xx redirect via redirect: "manual".
    The backend can freely follow redirects and return the final URL.
    """
    if not req.url:
        return ResolveRedirectResponse(redirect_url=None)
    target = _resolve_redirect_target(req.url)
    return ResolveRedirectResponse(redirect_url=target)




class ResolveRedirectRequest(BaseModel):
    url: str = Field(..., description="URL to resolve redirect target for")

class ResolveRedirectResponse(BaseModel):
    redirect_url: Optional[str] = Field(None, description="Final redirect target URL, or null if not a redirect")


@router.post("/resolve-redirect", response_model=ResolveRedirectResponse)
def resolve_redirect(
    req: ResolveRedirectRequest,
    current_user: User = Depends(get_current_active_user_allow_query),
):
    """Resolve the redirect target of a URL server-side (no CORS issues).
    
    Called by the bookmarklet when it detects a 3xx redirect via redirect: "manual".
    The backend can freely follow redirects and return the final URL.
    """
    if not req.url:
        return ResolveRedirectResponse(redirect_url=None)
    target = _resolve_redirect_target(req.url)
    return ResolveRedirectResponse(redirect_url=target)

@router.post("/import-page", response_model=ImportPageResponse)
def import_page(
    req: ImportPageRequest,
    current_user: User = Depends(get_current_active_user_allow_query),
):
    """Import a page (URL + HTML content) into FileBot as a new document."""

    # Ensure background import worker is running (handles WebBot push)
    _start_import_worker()

    # ── Snapshot save (bookmarklet baseline) — check BEFORE url check ──
    if req.save_snapshot:
        _save_bookmarklet_snapshot(req.save_snapshot)

    if not req.url:
        raise HTTPException(status_code=400, detail="url is required")

    # ── Image upload path ────────────────────────────────────────────────
    if req.is_image:
        return _handle_image_upload(req, current_user)

    if not req.html:
        raise HTTPException(status_code=400, detail="html is required for non-image imports")

    # Determine title
    title = req.title.strip() or extract_title_from_html(req.html) or "Imported Page"
    if len(title) > 255:
        title = title[:252] + "..."

    # Determine target folder
    if req.folder_path:
        target_folder_path = req.folder_path.rstrip('/')
        folder_path = target_folder_path
        doc_path = target_folder_path
    else:
        root = get_or_create_default_app()
        segments = url_to_path_segments(req.url)

        # Ensure the root folder exists
        db = next(get_db())
        try:
            root_folder = db.query(Folder).filter(Folder.path == root).first()
            if not root_folder:
                root_folder = Folder(
                    path=root,
                    parent_folder_path="/boarding",
                    name="canadasite",
                    created_by=str(current_user.id),
                )
                db.add(root_folder)
                db.commit()
                db.refresh(root_folder)
        finally:
            db.close()

        if segments:
            # Exclude segments ending in .html from folder hierarchy
            # (they represent page files, not directories)
            folder_segments = [s for s in segments if not s.endswith('.html')]

            if folder_segments:
                db = next(get_db())
                try:
                    for i in range(len(folder_segments)):
                        parent_path = root if i == 0 else (root + '/' + '/'.join(folder_segments[:i]))
                        seg_path = root + '/' + '/'.join(folder_segments[:i+1])

                        existing = db.query(Folder).filter(Folder.path == seg_path).first()
                        if not existing:
                            root_folder_db = db.query(Folder).filter(Folder.path == root).first()
                            app_id = root_folder_db.app_id if root_folder_db else None

                            folder = Folder(
                                path=seg_path,
                                parent_folder_path=parent_path,
                                name=folder_segments[i],
            
                                created_by=str(current_user.id),
                            )
                            db.add(folder)
                            db.flush()

                    db.commit()
                except Exception as e:
                    db.rollback()
                    logger.warning(f"Folder creation warning (import bookmarklet): {e}")
                finally:
                    db.close()

        # Folder path (for DB storage reference) - excludes .html segments
        folder_segments = [s for s in segments if not s.endswith('.html')] if segments else []
        folder_path = root + '/' + '/'.join(folder_segments) if folder_segments else root
        # Document path (logical URL path) - includes .html segment
        doc_path = root + '/' + '/'.join(segments) if segments else root
        target_folder_path = folder_path

    # Make sure the target folder exists (using folder_path which has no .html)
    db = next(get_db())
    try:
        folder = db.query(Folder).filter(Folder.path == folder_path).first()
        if not folder:
            # Recursively create all parent folders from root to leaf
            boarding_app = db.query(App).filter(App.slug == 'boarding').first()
            root_app_id = boarding_app.id if boarding_app else None
            _parts = folder_path.strip('/').split('/')
            _cur = ''
            for _part in _parts:
                _cur = _cur + '/' + _part if _cur else '/' + _part
                _exist = db.query(Folder).filter(Folder.path == _cur).first()
                if not _exist:
                    _parent = '/'.join(_cur.split('/')[:-1]) or None
                    _folder_app_id = root_app_id
                    if _parent:
                        _pf = db.query(Folder).filter(Folder.path == _parent).first()
                        if _pf and _pf.app_id:
                            _folder_app_id = _pf.app_id
                    _f = Folder(
                        path=_cur,
                        parent_folder_path=_parent,
                        name=_part,
                        app_id=_folder_app_id,
                        created_by=str(current_user.id),
                    )
                    db.add(_f)
                    db.flush()
            db.commit()
    finally:
        db.close()

    # Determine app ID from target folder (use folder_path, no .html)
    db = next(get_db())
    app_id = None
    try:
        target_folder = db.query(Folder).filter(Folder.path == folder_path).first()
        if target_folder and target_folder.app_id:
            app_id = target_folder.app_id
        else:
            cur_path = folder_path
            while cur_path and cur_path != '/':
                parent = db.query(Folder).filter(Folder.path == cur_path).first()
                if parent and parent.app_id:
                    app_id = parent.app_id
                    break
                cur_path = str(Path(cur_path).parent)
    finally:
        db.close()

    # Generate storage paths
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    page_id = str(uuid.uuid4())[:8]

    url_path = urlparse(req.url).path.rstrip('/')
    if url_path.endswith('.html'):
        url_path = url_path[:-5]
    url_basename = os.path.basename(url_path) if url_path and url_path != '/' else 'index'
    # Cap raised 64 -> 255 (2026-08-13): long URL paths were silently cut
    # at 64 chars in the leaf filename, truncating the webbot page path.
    safe_filename = re.sub(r'[^a-zA-Z0-9_\-]', '_', url_basename)[:255]
    stored_filename = f"{safe_filename}.html"

    doc_rel_dir = target_folder_path.lstrip('/')
    data_root = Path(settings.FILE_STORAGE_PATH).resolve()
    if not data_root.exists():
        data_root = Path(settings.DATA_ROOT).resolve()
    absolute_dir = data_root / doc_rel_dir
    absolute_dir.mkdir(parents=True, exist_ok=True)
    absolute_path = absolute_dir / stored_filename

    # ── Redirect: only update redirect_to, skip content ──
    if req.redirect_to:
        db = next(get_db())
        try:
            existing_doc = db.query(Document).filter(Document.path == doc_path).first()
            if existing_doc:
                existing_doc.document_metadata = {
                    **(existing_doc.document_metadata or {}),
                    "redirect_to": req.redirect_to,
                    "import_method": "bookmarklet",
                }
            else:
                doc = Document(
                    path=doc_path,
                    title=title,
                    folder_path=str(Path(doc_path).parent) or "",

                    original_filename=stored_filename,
                    stored_filename=stored_filename,
                    file_size=0,
                    file_type=FileType.HTML,
                    mime_type="text/html",
                    storage_path=str(absolute_path),
                    status=DocumentStatus.ACTIVE,
                    publish_status=PublishStatus.UNPUBLISHED,
                    document_metadata={
                        "redirect_to": req.redirect_to,
                        "import_method": "bookmarklet",
                    },
                    uploaded_by=str(current_user.id),
                )
                db.add(doc)
            db.commit()
            logger.info(f"🔄 Redirect recorded: {req.url} → {req.redirect_to}")
        finally:
            db.close()

        # Queue WebBot push in background (non-blocking)
        try:
            _import_task_queue.put_nowait((
                req, title, target_folder_path, stored_filename, absolute_path,
            ))
        except Exception:
            pass  # queue full — non-fatal, page already saved

        return ImportPageResponse(
            success=True,
            path=doc_path,
            folder_path=str(Path(doc_path).parent) or "",
            title=title,
            stored_filename=stored_filename,
            file_size=0,
            url=req.url,
            redirect_to=req.redirect_to or "",
        )

    # Download and store /content/dam/ images locally before saving HTML
    # This ensures images are available from the local file server,
    # without needing to access canada.ca CDN for image serving.
    modified_html, dl_count, err_count = download_and_store_dam_images(
        req.html, req.url, current_user
    )
    
    # Save the rewritten HTML with correct /content/dam/... image paths.
    # The WebBot /content/dam/{path} proxy handler will find locally
    # stored images via FileBot's by-path lookup.
    html_bytes = modified_html.encode('utf-8')
    file_size = len(html_bytes)
    # 同名文件直接覆盖（旧文件应在删除文档记录时同步删除）
    # 如果路径是一个目录（历史遗留问题），先移除
    if absolute_path.is_dir():
        import shutil
        logger.warning(f"Path exists as directory, removing: {absolute_path}")
        shutil.rmtree(absolute_path)
    absolute_path.write_bytes(html_bytes)

    logger.info(f"📄 Saved imported page: {absolute_path} ({file_size} bytes)")

    # Document logical path = URL-derived path (with .html if present)
    # Folder path for Document.folder_path = parent directory
    doc_folder_path = str(Path(doc_path).parent)

    db = next(get_db())
    try:
        existing_doc = db.query(Document).filter(Document.path == doc_path).first()
        if existing_doc:
            existing_doc.title = title
            existing_doc.file_size = file_size
            existing_doc.document_metadata = {
                **(existing_doc.document_metadata or {}),
                "source_url": req.url,
                "imported_at": datetime.now().isoformat(),
                **({"redirect_to": req.redirect_to} if req.redirect_to else {}),
            }
            db.commit()

            # Queue WebBot push in background (non-blocking)
            try:
                _import_task_queue.put_nowait((
                    ImportPageRequest(
                        url=req.url, html=req.html, title=title,
                        folder_path=req.folder_path, is_image=False
                    ),
                    title, target_folder_path, stored_filename, absolute_path,
                ))
            except Exception:
                pass  # queue full — non-fatal, page already saved

            return ImportPageResponse(
                success=True,
                path=doc_path,
                folder_path=doc_folder_path,
                title=title,
                stored_filename=stored_filename,
                file_size=file_size,
                url=req.url,
                redirect_to=req.redirect_to or "",
            )

        doc = Document(
            path=doc_path,
            folder_path=doc_folder_path,
            title=title,
            original_filename=stored_filename,
            stored_filename=stored_filename,
            file_size=file_size,
            file_type=FileType.HTML,
            mime_type="text/html",
            storage_path=str(absolute_path),
            status=DocumentStatus.ACTIVE,
            publish_status=PublishStatus.UNPUBLISHED,
            document_metadata={
                "source_url": req.url,
                "imported_at": datetime.now().isoformat(),
                "import_method": "bookmarklet",
                **({"redirect_to": req.redirect_to} if req.redirect_to else {}),
            },
            uploaded_by=str(current_user.id),
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        logger.info(f"📄 Created document: {doc_path}")

    except sqlalchemy.exc.IntegrityError as e:
        db.rollback()
        logger.warning(f"⚠️ Duplicate import (concurrent): {req.url}")
        return ImportPageResponse(
            success=True,
            path=doc_path,
            folder_path=doc_folder_path,
            title=title,
            stored_filename=stored_filename,
            file_size=file_size,
            url=req.url,
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create document for {req.url}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create document: {str(e)}")
    finally:
        db.close()

    # ── Queue WebBot push in background ───────────────────────────────
    try:
        _import_task_queue.put_nowait((
            req, title, target_folder_path, stored_filename, absolute_path,
        ))
    except Exception:
        pass  # queue full — non-fatal, page already saved

    return ImportPageResponse(
        success=True,
        path=doc_path,
        folder_path=doc_folder_path,
        title=title,
        stored_filename=stored_filename,
        file_size=file_size,
        url=req.url,
            redirect_to=req.redirect_to or "",
    )

# ── Snapshot Import (for client-generated bookmarklet snapshots) ─────────
SNAPSHOT_DIR = "/opt/webfilebot/sitemap_snapshots"


class ImportSnapshotRequest(BaseModel):
    sitemap_url: str = Field(..., description="Sitemap URL (e.g. https://www.canada.ca/en/army.sitemap.xml)")
    snapshot: dict = Field(..., description="Snapshot: {pages: {url: lastmod}, images: [url, ...]}")


class ImportSnapshotResponse(BaseModel):
    success: bool
    path: str
    pages: int
    images: int



def _save_bookmarklet_snapshot(snapshot_data: dict) -> None:
    """Save a snapshot from bookmarklet data (used via import-page endpoint)."""
    sitemap_url = snapshot_data.get("sitemap_url", "")
    snap_content = snapshot_data.get("snapshot", {})
    if not sitemap_url or not snap_content:
        logger.warning("_save_bookmarklet_snapshot: missing sitemap_url or snapshot data")
        return
    from urllib.parse import urlparse as _urlparse
    _parsed = _urlparse(sitemap_url)
    _path = _parsed.path.rstrip("/")
    _parts = _path.split("/")
    _slug = _parts[-1].replace(".sitemap.xml", "").replace(".xml", "")
    _lang = "en"
    for _p in _parts:
        if _p in ("en", "fr"):
            _lang = _p
    _spath = os.path.join(SNAPSHOT_DIR, f"{_slug}_{_lang}.sitemap.json")
    os.makedirs(os.path.dirname(_spath), exist_ok=True)
    _pages = len(snap_content.get("pages", {}))
    _images = len(snap_content.get("images", []))
    import json as _json
    with open(_spath, "w", encoding="utf-8") as _f:
        _json.dump(snap_content, _f, indent=2, ensure_ascii=False)
    logger.info(f"📸 快照已保存: {_spath} (pages={_pages}, images={_images}, filesize={os.path.getsize(_spath)} bytes)")

@router.post("/save-snapshot", response_model=ImportSnapshotResponse)
@router.post("/import-snapshot", response_model=ImportSnapshotResponse)
def import_snapshot(
    req: ImportSnapshotRequest,
    current_user: User = Depends(get_current_active_user_allow_query),
):
    """
    Save a client-generated snapshot for incremental sync baseline.
    
    The bookmarklet generates this during its initial full crawl:
      { pages: {"https://...": "lastmod", ...}, images: ["https://...img.jpg", ...] }
    
    Saved to sitemap_snapshots/{slug}_{lang}.sitemap.json, same format and path
    as incremental_sync.py uses, so the next server-side incremental run can
    compare against the client snapshot instead of re-fetching the sitemap XML.
    """
    from urllib.parse import urlparse as _urlparse

    # Derive filename same way as incremental_sync.py::snapshot_path()
    _parsed = _urlparse(req.sitemap_url)
    _path = _parsed.path.rstrip("/")
    _parts = _path.split("/")
    _slug = _parts[-1].replace(".sitemap.xml", "").replace(".xml", "")
    _lang = "en"
    for _p in _parts:
        if _p in ("en", "fr"):
            _lang = _p

    _spath = os.path.join(SNAPSHOT_DIR, f"{_slug}_{_lang}.sitemap.json")
    os.makedirs(os.path.dirname(_spath), exist_ok=True)

    _pages = len(req.snapshot.get("pages", {}))
    _images = len(req.snapshot.get("images", []))

    with open(_spath, "w", encoding="utf-8") as _f:
        json.dump(req.snapshot, _f, indent=2, ensure_ascii=False)

    logger.info(
        f"📸 快照已保存: {_spath} (pages={_pages}, images={_images}, "
        f"filesize={os.path.getsize(_spath)} bytes)"
    )

    return ImportSnapshotResponse(
        success=True,
        path=_spath,
        pages=_pages,
        images=_images,
    )
