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
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

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

router = APIRouter(tags=["import"])

# Max path segments for folder depth
MAX_PATH_DEPTH = 10


class ImportPageRequest(BaseModel):
    url: str = Field(..., description="Full URL of the page being imported (e.g. https://www.canada.ca/en/...)")
    html: str = Field("", description="Raw HTML content of the page (required if is_image is False)")
    title: str = Field("", description="Page title (optional — auto-extracted from HTML if empty)")
    folder_path: str = Field("", description="Target folder path in FileBot (optional — auto-detected from URL)")
    is_image: bool = Field(False, description="Set to true if this is an image upload")
    image_data: str = Field("", description="Base64-encoded image data (required if is_image is True)")


class ImportPageResponse(BaseModel):
    success: bool
    path: str
    folder_path: str
    title: str
    stored_filename: str
    file_size: int
    url: str


def extract_title_from_html(html: str) -> str:
    """Extract <title> from HTML, strip ' - Canada.ca' suffix, return empty string if not found."""
    m = re.search(r'<title[^>]*>([^<]+)</title>', html, re.I | re.S)
    if not m:
        return ""
    title = m.group(1).strip()
    # Remove " - Canada.ca" suffix (common on canada.ca pages)
    title = re.sub(r'\s*[-–—]\s*Canada\.ca\s*$', '', title, flags=re.I)
    return title


def url_to_path_segments(url: str) -> list[str]:
    """Convert a URL path to folder/name segments, filtering empty segments."""
    parsed = urlparse(url)
    path = parsed.path.rstrip('/')
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


def _push_to_webbot(req: ImportPageRequest, title: str,
                    target_folder_path: str, stored_filename: str,
                    absolute_path: Path):
    """
    Push the imported page to WebBot (port 8000) so it appears in the
    WebBot page tree.  Non-fatal: errors are logged but never raise.
    """
    try:
        # 1. Login to WebBot
        login_resp = http_requests.post(
            f"{WEBBOT_API_BASE}/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"},
            timeout=10,
        )
        if login_resp.status_code != 200:
            logger.warning(f"WebBot login failed: {login_resp.status_code} {login_resp.text[:200]}")
            return
        webbot_token = login_resp.json()["access_token"]

        # 2. Transform FileBot path to WebBot path
        #    FileBot: /boarding/canadesite/en/...
        #    WebBot:  /canadesite/en/...
        if target_folder_path.startswith("/boarding/"):
            webbot_path = target_folder_path[len("/boarding"):]
        else:
            webbot_path = target_folder_path

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

        # other_language_path: <link rel="alternate" hreflang="fr" href="/fr/...">
        #   → webbot path: prepend /canadasite
        other_language_path = ""
        fr_link = re.search(
            r'<link[^>]*rel=[\"\']alternate[\"\'][^>]*hreflang=[\"\']fr[\"\'][^>]*href=[\"\']([^\"\']+)[\"\']',
            html_content, re.I
        )
        if not fr_link:
            fr_link = re.search(
                r'<link[^>]*hreflang=[\"\']fr[\"\'][^>]*rel=[\"\']alternate[\"\'][^>]*href=[\"\']([^\"\']+)[\"\']',
                html_content, re.I
            )
        if fr_link:
            fr_path = fr_link.group(1)
            # Strip full domain prefix if present
            fr_path = re.sub(r'^https?://(www\.)?canada\.ca', '', fr_path, flags=re.I)
            # Strip .html suffix
            if fr_path.endswith('.html'):
                fr_path = fr_path[:-5]
            # Convert /fr/... → /canadasite/fr/...
            fr_path = fr_path.rstrip('/')
            if fr_path.startswith('/'):
                other_language_path = '/canadasite' + fr_path
            else:
                other_language_path = '/canadasite/' + fr_path

        # subjects from <meta name="dcterms.subject" content="...">
        subjects = _extract_meta_content(
            r'<meta[^>]*name=[\"\']dcterms\.subject[\"\'][^>]*content=[\"\']([^\"\']+)[\"\']'
        )

        # audience from <meta name="dcterms.audience" content="...">
        audience = _extract_meta_content(
            r'<meta[^>]*name=[\"\']dcterms\.audience[\"\'][^>]*content=[\"\']([^\"\']+)[\"\']'
        )

        # 3. Create page in WebBot
        page_payload = {
            "title": title,
            "path": webbot_path,
            "content": html_content,
            "language": lang,
            "other_language_path": other_language_path or None,
            "status": "published",
            "skip_if_exists": True,
            "metadata": {
                "source_url": req.url,
                "file_path": str(absolute_path),
                "imported_at": datetime.now().isoformat(),
                "import_method": "bookmarklet",
            },
        }

        # Add subjects/audience to metadata if present
        if subjects:
            page_payload["metadata"]["subjects"] = subjects
        if audience:
            page_payload["metadata"]["audience"] = audience

        create_resp = http_requests.post(
            f"{WEBBOT_API_BASE}/api/v1/pages/",
            json=page_payload,
            headers={"Authorization": f"Bearer {webbot_token}"},
            timeout=30,
        )

        if create_resp.status_code in (200, 201):
            logger.info(f"✅ WebBot page created/updated: {webbot_path}")
        else:
            logger.warning(f"WebBot create page returned {create_resp.status_code}: {create_resp.text[:300]}")

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

    # URL path → folder determination (same logic as HTML pages)
    parsed = urlparse(req.url)
    url_path = parsed.path.rstrip('/')
    path_segments = [s for s in url_path.split('/') if s]

    root = "/boarding/canadasite"
    if path_segments:
        target_folder_path = root + '/' + '/'.join(path_segments[:-1]) if len(path_segments) > 1 else root
    else:
        target_folder_path = root

    basename = os.path.basename(url_path) if url_path and url_path != '/' else 'image'
    # Remove existing extension if any, use our ext
    basename = re.sub(r'\.[^./]+$', '', basename)
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', basename)[:64]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    image_id = str(uuid.uuid4())[:8]
    stored_filename = f"{safe_name}_{timestamp}_{image_id}.{ext}"

    # Save to disk
    doc_rel_dir = target_folder_path.lstrip('/')
    data_root = Path(settings.FILE_STORAGE_PATH).resolve()
    if not data_root.exists():
        data_root = Path(settings.DATA_ROOT).resolve()
    absolute_dir = data_root / doc_rel_dir
    absolute_dir.mkdir(parents=True, exist_ok=True)
    absolute_path = absolute_dir / stored_filename
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


@router.post("/import-page", response_model=ImportPageResponse)
def import_page(
    req: ImportPageRequest,
    current_user: User = Depends(get_current_active_user_allow_query),
):
    """Import a page (URL + HTML content) into FileBot as a new document."""

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
                                app_id=app_id,
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
            parent_path = str(Path(folder_path).parent)
            last_segment = os.path.basename(folder_path)
            # Find app_id from parent folder chain
            leaf_app_id = None
            probe = db.query(Folder).filter(Folder.path == parent_path).first()
            if probe and probe.app_id:
                leaf_app_id = probe.app_id
            if not leaf_app_id:
                boarding_app = db.query(App).filter(App.slug == 'boarding').first()
                leaf_app_id = boarding_app.id if boarding_app else None
            leaf_folder = Folder(
                path=folder_path,
                parent_folder_path=parent_path if parent_path != folder_path else None,
                name=last_segment,
                app_id=leaf_app_id,
                created_by=str(current_user.id),
            )
            db.add(leaf_folder)
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
    safe_filename = re.sub(r'[^a-zA-Z0-9_\-]', '_', url_basename)[:64]
    stored_filename = f"{safe_filename}_{timestamp}_{page_id}.html"

    doc_rel_dir = target_folder_path.lstrip('/')
    data_root = Path(settings.FILE_STORAGE_PATH).resolve()
    if not data_root.exists():
        data_root = Path(settings.DATA_ROOT).resolve()
    absolute_dir = data_root / doc_rel_dir
    absolute_dir.mkdir(parents=True, exist_ok=True)
    absolute_path = absolute_dir / stored_filename

    html_bytes = req.html.encode('utf-8')
    file_size = len(html_bytes)
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
            }
            db.commit()

            # Push to WebBot even for updates
            _push_to_webbot(req, title, target_folder_path, stored_filename, absolute_path)

            return ImportPageResponse(
                success=True,
                path=doc_path,
                folder_path=doc_folder_path,
                title=title,
                stored_filename=stored_filename,
                file_size=file_size,
                url=req.url,
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
            },
            uploaded_by=str(current_user.id),
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        logger.info(f"📄 Created document: {doc_path}")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create document for {req.url}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create document: {str(e)}")
    finally:
        db.close()

    # ── Push to WebBot ────────────────────────────────────────────────
    _push_to_webbot(req, title, target_folder_path, stored_filename, absolute_path)

    return ImportPageResponse(
        success=True,
        path=doc_path,
        folder_path=doc_folder_path,
        title=title,
        stored_filename=stored_filename,
        file_size=file_size,
        url=req.url,
    )
