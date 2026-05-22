"""Pages routes — 基于文档路径而非 UUID"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import logging
import os
import uuid
import re
import httpx
from pathlib import Path
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


class PublishRequest(BaseModel):
    html_content: str


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

    # Step 2: Create database records (folder + document) under publish app
    try:
        publish_app = _get_publish_app(db)
        if not publish_app:
            logger.warning(f"Publish app '{PUBLISH_APP_SLUG}' not found in DB, skipping DB records")
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
        rel_path = path.lstrip("/")
        if rel_path.startswith("canadasite/"):
            rel_path = rel_path[len("canadasite/"):]
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

        # Check if document already exists (update it) or create new
        existing_doc = db.query(Document).filter(Document.path == doc_path).first()
        if existing_doc:
            existing_doc.title = doc_name
            existing_doc.file_size = html_len
            existing_doc.updated_by = "webbot"
            existing_doc.publish_status = PublishStatus.PUBLISHED
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
                original_filename=f"{doc_name}{extension}",
                stored_filename=f"{doc_name}{extension}",
                file_size=html_len,
                file_type=file_type,
                mime_type=mime_type,
                title=doc_name,
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
        # HTML file was already written, just return without DB records
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

    return {
        "success": True,
        "path": path,
        "file_deleted": file_deleted,
        "db_updated": db_updated,
        "publish_file": str(publish_file),
    }


@router.get("/path", response_model=List[PageResponse])
def get_pages_by_path(
    path: str = Query(..., description="Folder path, e.g. /boarding/canadasite/fr"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    include_subfolders: bool = Query(False, description="是否递归包含子文件夹中的文档"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """按文件夹路径获取所有文档的页面"""
    if not path or not path.startswith('/'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path must start with /")

    normalized = path.rstrip('/')
    folder = db.query(Folder).filter(Folder.path == normalized).first()
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Folder not found: {path}")

    # 构建文档查询
    if include_subfolders:
        folder_path_prefix = f"{normalized}/"
        subfolders = db.query(Folder).filter(
            Folder.parent_folder_path.like(f"{folder_path_prefix}%")
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
