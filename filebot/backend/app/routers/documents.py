from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, Path as FastaPath, Request
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload, selectinload
from typing import List, Optional, Dict, Any
import uuid
import os
import logging
import shutil
import tempfile
import base64
from datetime import datetime
from pathlib import Path
from io import BytesIO
import PyPDF2
from PIL import Image
from urllib.parse import urlparse

from app.db.database import get_db
from app.core.security import get_current_active_user, get_current_active_user_allow_query, get_current_user, oauth2_scheme
from app.core.config import settings
from app.models.user import User
from app.models.app import App
from app.models.folder import Folder
from app.models.document import Document, ConversionStatus, FileType, DocumentStatus, DocumentType, PublishStatus
from app.models.page import Page
from app.models.file_naming_rule import FileNamingRule
from app.models.device import Device, DeviceType, DeviceStatus
from app.schemas.document import (
    DocumentCreate, DocumentResponse, DocumentUpdate,
    PageCreate, PageResponse, PageUpdate
)
from app.services.conversion_worker import create_conversion_task_for_document
from app.core.path_utils import (
    generate_storage_paths, 
    ensure_directory_exists, 
    make_filename_safe,
    copy_to_static_directory,
    remove_from_static_directory,
    get_static_file_url
)

router = APIRouter()


# ========== Permission Check Helpers ==========

def check_folder_access(
    folder_path: str,
    current_user: User,
    db: Session,
    require_owner: bool = False
) -> Folder:
    """Check user permission to access a folder
    
    Args:
        folder_path: folder path
        current_user: current user
        db: database session
        require_owner: whether user must be folder owner (app owner)
    
    Returns:
        Folder object (if permission check passes)
    
    Raises:
        HTTPException: if folder not found or user lacks permission
    """
# Superuser can access all resources
    if current_user.is_superuser or current_user.username == "public":
        folder = db.query(Folder).options(
            joinedload(Folder.app)
        ).filter(Folder.path == folder_path).first()
        
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found"
            )
        return folder
    
    # Get folder and associated app
    folder = db.query(Folder).options(
        joinedload(Folder.app)
    ).filter(Folder.path == folder_path).first()
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )
    
    # Check app permission
    app = folder.app
    if app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to access this folder"
        )
    
    # If owner is required, verify user is app owner
    if require_owner and app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can perform this operation"
        )
    
    return folder


def get_folder_by_identifier_or_path(
    folder_identifier: str,
    current_user: User,
    db: Session,
    require_owner: bool = False,
    create_if_not_exists: bool = False
) -> Folder:
    """Get folder by ID or path with permission check (path-first)
    
    Args:
        folder_identifier: folder path (e.g. /test-admin/public-documents) or UUID (deprecated)
        current_user: current user
        db: database session
        require_owner: whether user must be folder owner (app owner)
        create_if_not_exists: auto-create folder if not found
    
    Returns:
        Folder object (if permission check passes)
    
    Raises:
        HTTPException: if folder not found or user lacks permission
    
    Note: path identifiers recommended, UUID support deprecated
    """
    logger = logging.getLogger(__name__)
    
    # Try path first (path-first strategy)
    folder = None
    
    # Check if path format (starts with /)
    if folder_identifier.startswith('/'):
        # Search by path directly
        folder = db.query(Folder).options(
            joinedload(Folder.app)
        ).filter(Folder.path == folder_identifier).first()
        if folder:
            logger.info(f"Found folder by path: {folder_identifier}")
    else:
        # Could be UUID or encoded path
        # Try path lookup first (might be encoded path)
        try:
            import urllib.parse
            decoded_path = urllib.parse.unquote(folder_identifier)
            if decoded_path.startswith('/'):
                folder = db.query(Folder).options(
                    joinedload(Folder.app)
                ).filter(Folder.path == decoded_path).first()
                if folder:
                    logger.info(f"Found folder by decoded path: {decoded_path} (original: {folder_identifier})")
        except:
            pass
    
    # If not found, try as path with / prefix (backward compatible for bare names)
    if not folder:
        path = '/' + folder_identifier
        folder = db.query(Folder).options(
            joinedload(Folder.app)
        ).filter(Folder.path == path).first()
        if folder:
            logger.info(f"Found folder by adding / prefix: {path} (original: {folder_identifier})")
    
    # If folder does not exist and creation is allowed
    if not folder and create_if_not_exists:
        # Use folder_identifier as path (may have / prefix)
        path = folder_identifier
        if not path.startswith('/'):
            path = '/' + path
            
        # Parse path: format is /app-slug/folder-path
        parts = path.strip('/').split('/')
        if len(parts) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid path format, expected /app-slug/folder-path"
            )
    
    # If folder does not exist and creation is allowed
    if not folder and create_if_not_exists:
        # Parse path: format is /app-slug/folder-path
        parts = path.strip('/').split('/')
        if len(parts) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid path format, expected /app-slug/folder-path"
            )
        
        app_slug = parts[0]
        folder_path_parts = parts[1:]
        
        # Find app
        app = db.query(App).filter(App.slug == app_slug).first()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"App '{app_slug}' not found"
            )
        
        # Check app permission (superuser can bypass)
        if not current_user.is_superuser and app.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to create folder in this app"
            )
        
        # Recursively create folders and all parents
        current_path = ''
        parent_folder = None
        
        for i, folder_name in enumerate(folder_path_parts):
            current_path = f'/{app_slug}/{'/'.join(folder_path_parts[:i+1])}'
            
            # Check if folder already exists
            existing_folder = db.query(Folder).filter(Folder.path == current_path).first()
            if existing_folder:
                parent_folder = existing_folder
                continue
            
            # Create new folder
            new_folder = Folder(
                name=folder_name,
                path=current_path,
                app_id=app.id,
                parent_folder_path=parent_folder.path if parent_folder else None,
                created_by=current_user.username,
                updated_by=current_user.username
            )
            db.add(new_folder)
            db.commit()
            db.refresh(new_folder)
            parent_folder = new_folder
            
            print(f"Created folder: {current_path}")
        
        folder = parent_folder
        # Reload associated app object
        folder = db.query(Folder).options(
            joinedload(Folder.app)
        ).filter(Folder.path == folder.path).first()
    
    # If folder still does not exist (and creation disabled)
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )
    
    # Superuser can access all resources
    if current_user.is_superuser or current_user.username == "public":
        return folder
    
    # Check app permission
    app = folder.app
    if app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to access this folder"
        )
    
    # If owner is required, verify user is app owner
    if require_owner and app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can perform this operation"
        )
    
    return folder


def check_document_access(
    document_path: str,
    current_user: User,
    db: Session,
    require_owner: bool = False
) -> Document:
    """Check user permission to access a document
    
    Args:
        document_path: document path
        current_user: current user
        db: database session
        require_owner: whether user must be document owner (app owner)
    
    Returns:
        Document object (if permission check passes)
    """
    # Superuser can access all resources
    if current_user.is_superuser or current_user.username == "public":
        document = db.query(Document).options(
            joinedload(Document.folder).joinedload(Folder.app)
        ).filter(Document.path == document_path).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        return document
    
    # Get document with associated folder and app
    document = db.query(Document).options(
            joinedload(Document.folder).joinedload(Folder.app)
        ).filter(Document.path == document_path).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check app permission
    app = document.folder.app
    if app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to access this document"
        )
    
    # If owner is required, verify user is app owner
    if require_owner and app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can perform this operation"
        )
    
    return document


def get_document_by_identifier(
    document_identifier: str,
    current_user: User,
    db: Session,
    require_owner: bool = False
) -> Document:
    """通过路径获取文档并检查权限
    
    Supports path format: "/app_slug/folder_path/filename" or "/content/dam/..."
    
    Args:
        document_identifier: document path
        current_user: current user
        db: database session
        require_owner: whether user must be document owner (app owner)
    
    Returns:
        Document object (if permission check passes)
    """
    # Handle as path (path-based lookup)
    # Normalize path: ensure leading slash
    path = document_identifier
    if not path.startswith('/'):
        path = '/' + path
    
    # Find document
    # Try path field match first (new system)
    document = db.query(Document).options(
        joinedload(Document.folder).joinedload(Folder.app)
    ).filter(Document.path == path).first()
    
    if not document:
        # Try storage_path match (relative path)
        from app.core.config import settings as app_settings
        from pathlib import Path
        
        data_root = Path(app_settings.DATA_ROOT)
        # Try to interpret path relative to data_root
        # Path format: app_slug/folder_path/filename
        if path.startswith('/'):
            path = path[1:]  # Remove leading slash
        
        document = db.query(Document).options(
            joinedload(Document.folder).joinedload(Folder.app)
        ).filter(Document.storage_path == path).first()
    
    if not document:
        # Finally try combined lookup (legacy system)
        # Path format: /app_slug/folder_path/filename
        # Parse app slug, folder path and filename
        parts = path.strip('/').split('/')
        if len(parts) >= 2:
            app_slug = parts[0]
            filename = parts[-1]
            folder_parts = parts[1:-1]
            folder_path = '/' + '/'.join(folder_parts) if folder_parts else '/'
            
            # Find by app and folder
            app = db.query(App).filter(App.slug == app_slug).first()
            if app:
                folder = db.query(Folder).filter(
                    Folder.app_id == app.id,
                    Folder.path == folder_path
                ).first()
                if folder:
                    document = db.query(Document).options(
                        joinedload(Document.folder).joinedload(Folder.app)
                    ).filter(
                        Document.folder_path == folder.path,
                        Document.original_filename.like(f'%{filename}%')
                    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_identifier}"
        )
    
    # Check app permission (reuse check_document_access logic)
    app = document.folder.app
    if current_user.is_superuser or current_user.username == "public":
        return document
    
    if app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to access this document"
        )
    
    # If owner is required, verify user is app owner
    if require_owner and app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can perform this operation"
        )
    
    return document


def get_document_file_path(document: Document, settings) -> Path:
    """
    Get the actual storage file path of a document
    
    Build path from document storage info:
    1. Use new path system first (storage_path)
    2. If document has full_storage_path, use device storage path
    3. Otherwise, use default storage path
    4. Fallback to legacy crawler storage path (data/documents/)
    """
    # 1. Use new path system first
    if document.storage_path:
        # Build full path
        storage_path = Path(settings.DATA_ROOT) / document.storage_path
        if storage_path.exists():
            return storage_path
        else:
            print(f"[Path System Warning] Storage path not found: {storage_path}, falling back to legacy")
    
    # 2. Use legacy system (backward compatible)
    if document.full_storage_path and document.stored_filename:
        # Use device storage path
        return Path(document.full_storage_path) / document.stored_filename
    
    # Try multiple possible storage locations
    possible_paths = []
    
    # 1. Default storage path
    default_path = Path(settings.FILE_STORAGE_PATH) / "original" / document.stored_filename
    possible_paths.append(default_path)
    
    # 2. Legacy crawler storage path (data/documents/)
    old_crawler_path = Path("data/documents") / document.stored_filename
    possible_paths.append(old_crawler_path)
    
    # 3. Use stored_filename directly (if absolute path)
    if document.stored_filename and os.path.isabs(document.stored_filename):
        possible_paths.append(Path(document.stored_filename))
    
    # Check which path exists
    for path in possible_paths:
        if path.exists():
            return path
    
    # If no path exists, return default (will cause 404 but gives clear exception)
    return default_path


def get_document_pdf_path(document: Document, settings) -> Optional[Path]:
    """
    Get the PDF file path of a document (if converted)
    """
    if document.converted_pdf_path:
        return Path(document.converted_pdf_path)
    return None


def generate_thumbnail_for_image_document(
    document: Document,
    db: Session,
    settings
) -> bool:
    """
    为图像文档生成缩略图并更新元数据
    
    Generate 100x100 PNG thumbnail, store as base64 in document_metadata.original_html,
    and set conversion_status to COMPLETED.
    
    Args:
        document: Document object
        db: database session
        settings: application config
    
    Returns:
        bool: whether successful
    """
    # Import ThumbnailStatus before try block to avoid Python 3.12+ scoping issues
    from app.models.document import ThumbnailStatus

    try:
        # Get document file path
        file_path = get_document_file_path(document, settings)
        if not file_path or not file_path.exists():
            logging.error(f"Document file not found: {document.path}")
            return False
        
        # Open image file
        with Image.open(file_path) as img:
            # Convert to RGB (if needed)
            if img.mode not in ["RGB", "RGBA", "L"]:
                img = img.convert("RGB")
            
            # Generate 100x100 thumbnail (maintain aspect ratio)
            img.thumbnail((100, 100), Image.Resampling.LANCZOS)
            
            # If image is RGBA mode, add white background
            if img.mode == "RGBA":
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
                img = background
            
            # Save to BytesIO buffer (PNG format)
            buffer = BytesIO()
            img.save(buffer, format="PNG", optimize=True)
            buffer.seek(0)
            
            # Convert to base64 string
            thumbnail_base64 = base64.b64encode(buffer.read()).decode("utf-8")
            
            # Update document metadata
            if not document.document_metadata:
                document.document_metadata = {}
            
            # Store base64 thumbnail in original_html field (per boss request)
            document.document_metadata["original_html"] = thumbnail_base64
            
            # Also store thumbnail info (optional)
            document.document_metadata["thumbnail_base64_png"] = thumbnail_base64
            document.document_metadata["thumbnail_generated"] = True
            document.document_metadata["thumbnail_size"] = "100x100"
            document.document_metadata["thumbnail_format"] = "PNG"
            
            # Update conversion status to COMPLETED
            document.conversion_status = ConversionStatus.COMPLETED
            
            # Update thumbnail status
            document.thumbnail_status = ThumbnailStatus.GENERATED
            document.thumbnail_generated_at = datetime.utcnow()
            
            # Save changes to database
            db.add(document)
            db.commit()
            
            logging.info(f"Generated thumbnail for image document {document.path} successfully")
            return True
            
    except Exception as e:
        logging.error(f"Failed to generate image thumbnail: {str(e)}", exc_info=True)
        # Update error status
        document.thumbnail_status = ThumbnailStatus.FAILED
        document.thumbnail_error = str(e)[:1000]
        db.add(document)
        db.commit()
        return False


# ========== Document Routes ==========

@router.get("/", response_model=List[DocumentResponse])
def get_documents(
    folder_path: Optional[str] = Query(None, description="Filter by folder path, exact match, format: /app_slug/folder/subfolder"),
    parent_folder_path: Optional[str] = Query(None, description="Filter by parent folder path (LIKE match), returns docs in folder + all subfolders, format: /app_slug/folder"),
    path_prefix: Optional[str] = Query(None, description="Filter by document path prefix (LIKE match), returns all descendant docs under path, format: /app_slug/folder/sub"),
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Records to return"),
    status_filter: Optional[DocumentStatus] = Query(None, description="Filter by document status"),
    type_filter: Optional[DocumentType] = Query(None, description="Filter by document type"),
    conversion_status_filter: Optional[ConversionStatus] = Query(None, description="Filter by conversion status"),
    search_term: Optional[str] = Query(None, description="Search document title or description"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取文档列表
    
    Supports multiple filter conditions:
    - By folder path
    - By document status
    - By document type
    - By conversion status
    - By title/description search
    """
    logger = logging.getLogger(__name__)
    
    # Build base query
    # Note: use selectinload instead of joinedload to avoid query.join() conflicts
    query = db.query(Document).options(
        selectinload(Document.folder).selectinload(Folder.app)
    )
    
    # Add permission filter: only visible apps
    if not current_user.is_superuser:
        # Subquery: get all app IDs owned by current user
        user_apps_subquery = db.query(App.id).filter(App.owner_id == current_user.id).subquery()
        
        # Filter via folder->app chain (no drawer layer)
        query = query.join(Folder).join(App)
        query = query.filter(App.id.in_(user_apps_subquery))
    
    # Apply filter conditions
    if folder_path:
        # Filter by folder path
        # Ensure path starts with /
        path = folder_path
        if not path.startswith('/'):
            path = '/' + path
        
        # 查找文件夹
        folder = db.query(Folder).filter(Folder.path == path).first()
        if not folder:
            # Folder not found, return empty list
            return []
        
        # 检查权限
        app = folder.app
        if not current_user.is_superuser and app.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to access this folder"
            )
        
        # Filter documents
        query = query.filter(Document.folder_path == folder.path)
    
    if parent_folder_path:
        # LIKE match: get docs in this folder and all subfolders
        path = parent_folder_path
        if not path.startswith('/'):
            path = '/' + path
        # Ensure trailing slash so /boarding doesn't match /boarding-extra
        like_path = path.rstrip('/') + '/%'
        query = query.filter(Document.folder_path.like(like_path))
    
    if path_prefix:
        # LIKE match on document path: get all descendant docs under this path prefix
        prefix = path_prefix
        if not prefix.startswith('/'):
            prefix = '/' + prefix
        # Use 'prefix%' to match everything under the path
        query = query.filter(Document.path.like(prefix + '%'))
    
    if status_filter:
        query = query.filter(Document.status == status_filter)
    
    if type_filter:
        query = query.filter(Document.type == type_filter)
    
    if conversion_status_filter:
        query = query.filter(Document.conversion_status == conversion_status_filter)
    
    if search_term:
        search_pattern = f"%{search_term}%"
        query = query.filter(
            (Document.title.ilike(search_pattern)) |
            (Document.description.ilike(search_pattern)) |
            (Document.document_number.ilike(search_pattern))
        )
    
    # Sort and paginate
    query = query.order_by(Document.created_at.desc())
    documents = query.offset(skip).limit(limit).all()
    
    return documents


@router.get("/path", response_model=List[DocumentResponse])
def get_documents_by_path(
    path: str = Query(..., description="Folder path, format: /app_slug/folder/subfolder"),
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Records to return"),
    status_filter: Optional[DocumentStatus] = Query(None, description="Filter by document status"),
    type_filter: Optional[DocumentType] = Query(None, description="Filter by document type"),
    conversion_status_filter: Optional[ConversionStatus] = Query(None, description="Filter by conversion status"),
    search_term: Optional[str] = Query(None, description="Search document title or description"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """根据文件夹路径获取文档列表
    
    Get all documents under the specified folder path.
    Path format: /app_slug/folder/subfolder
    """
    # Validate path format
    if not path or not path.startswith('/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path must start with /, format: /app_slug/folder/subfolder"
        )
    
    # Find folder by path
    folder = db.query(Folder).filter(Folder.path == path).first()
    if not folder:
        # Folder not found, return empty (or try parent_folder_path?)
        # New system: also try parent_folder_path lookup
        # For safety, verify folder exists first
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No folder found for path: {path}"
        )
    
    # Verify user has permission to access this folder
    folder = check_folder_access(folder.path, current_user, db)
    
    # Now query documents by folder path (reuse get_documents logic)
    # Build base query
    query = db.query(Document).options(
        joinedload(Document.folder).joinedload(Folder.app)
    )
    
    # Add permission filter: only visible apps
    if not current_user.is_superuser:
        # Subquery: get all app IDs owned by current user
        user_apps_subquery = db.query(App.id).filter(App.owner_id == current_user.id).subquery()
        
        # Filter via folder->app chain (no drawer layer)
        query = query.join(Folder).join(App)
        query = query.filter(App.id.in_(user_apps_subquery))
    
    # Filter by folder ID
    query = query.filter(Document.folder_path == folder.path)
    
    # Apply other filter conditions
    if status_filter:
        query = query.filter(Document.status == status_filter)
    
    if type_filter:
        query = query.filter(Document.type == type_filter)
    
    if conversion_status_filter:
        query = query.filter(Document.conversion_status == conversion_status_filter)
    
    if search_term:
        search_pattern = f"%{search_term}%"
        query = query.filter(
            (Document.title.ilike(search_pattern)) |
            (Document.description.ilike(search_pattern)) |
            (Document.document_number.ilike(search_pattern))
        )
    
    # Sort and paginate
    query = query.order_by(Document.created_at.desc())
    documents = query.offset(skip).limit(limit).all()
    
    return documents


@router.get("/by-path-detail/{path:path}", response_model=DocumentResponse)
def get_document_by_path_detail(
    path: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """通过完整路径获取文档详情
    
    Path format: /app_slug/folder_path/document_filename
    Example: /my-app/marketing/brochure.pdf
    
    Supports both new and legacy document systems:
    1. New documents: match by path field directly
    2. Legacy documents: match by combining folder path and filename
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Normalize path: ensure leading slash
    if not path.startswith('/'):
        path = '/' + path
    
    logger.info(f"Get document details by path: {path}")
    
    # Method 1: try path field match (new system, paths like /content/dam/...)
    document = db.query(Document).options(
        joinedload(Document.folder).joinedload(Folder.app)
    ).filter(Document.path == path).first()
    
    if document:
        logger.info(f"Found document by path field: {document.path}, path: {path}")
        # Check access permission
        return check_document_access(document.path, current_user, db)
    
    # Method 1.5: try legacy prefix path fields (backward compat)
    # New format: /boarding/canadasite/... (no prefix)
    # Legacy format 1: /content/boarding/...
    # Legacy format 2: /content/dam/boarding/...
    for prefix in ['/content', '/content/dam']:
        url_path = f"{prefix}{path}"
        document = db.query(Document).options(
            joinedload(Document.folder).joinedload(Folder.app)
        ).filter(Document.path == url_path).first()
        if document:
            logger.info(f"Found document by {prefix} path field: {document.path}, url_path: {url_path}")
            return check_document_access(document.path, current_user, db)
    
    # Method 2: try storage_path field match
    # storage_path stored without leading slash (e.g. "boarding/canadasite/...")
    # Try both with / and without /
    document = db.query(Document).options(
        joinedload(Document.folder).joinedload(Folder.app)
    ).filter(Document.storage_path == path).first()
    
    if not document:
        # Remove leading slash and try again
        storage_path = path.lstrip('/')
        document = db.query(Document).options(
            joinedload(Document.folder).joinedload(Folder.app)
        ).filter(Document.storage_path == storage_path).first()
    
    if document:
        logger.info(f"Found document by storage_path field: {document.path}, path: {path}")
        # Check access permission
        return check_document_access(document.path, current_user, db)
    
    # Method 3: parse path into app slug, folder path and filename
    # 路径格式: /app_slug/folder_path/document_filename
    path_parts = path.strip('/').split('/')
    if len(path_parts) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid path format, need at least app slug and filename"
        )
    
    app_slug = path_parts[0]
    filename = path_parts[-1]
    folder_path_parts = path_parts[1:-1]  # Middle part is folder path
    folder_path = '/' + '/'.join(folder_path_parts) if folder_path_parts else '/' + app_slug
    
    logger.info(f"Parsing path: app_slug={app_slug}, folder_path={folder_path}, filename={filename}")
    
    # Find app
    app = db.query(App).filter(App.slug == app_slug).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"App not found: {app_slug}"
        )
    
    # 查找文件夹
    folder = db.query(Folder).filter(
        Folder.app_id == app.id,
        Folder.path == folder_path
    ).first()
    
    if not folder:
        # Try parent folder path
        folder = db.query(Folder).filter(
            Folder.app_id == app.id,
            Folder.parent_folder_path == folder_path
        ).first()
        
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Folder not found: {folder_path}"
            )
    
    # Sanitize filename comparison
    from ..core.path_utils import make_filename_safe
    from pathlib import Path as PathLib
    
    path_obj = PathLib(filename)
    stem = path_obj.stem
    ext = path_obj.suffix.lower()
    safe_stem = make_filename_safe(stem)
    safe_filename = f"{safe_stem}{ext}" if ext else safe_stem
    
    # Find document (by storage filename)
    document = db.query(Document).options(
        joinedload(Document.folder).joinedload(Folder.app)
    ).filter(
        Document.folder_path == folder.path,
        Document.stored_filename == safe_filename
    ).first()
    
    if not document:
        # Try matching by original filename
        document = db.query(Document).options(
            joinedload(Document.folder).joinedload(Folder.app)
        ).filter(
            Document.folder_path == folder.path,
            Document.original_filename == filename
        ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {filename} (path: {path})"
        )
    
    logger.info(f"Found document by folder and filename: {document.path}")
    
    # Check access permission
    return check_document_access(document.path, current_user, db)


@router.get("/{document_identifier:path}/pages", response_model=List[PageResponse])
def get_document_pages(
    document_identifier: str,
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Records to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all pages of a document by identifier (UUID or path)"""
    # Verify document access and get document object
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # Get page list
    pages = db.query(Page).filter(
        Page.document_id == document.path
    ).order_by(Page.page_number).offset(skip).limit(limit).all()
    
    return pages


@router.get("/{document_identifier:path}/pages/{page_id}", response_model=PageResponse)
def get_document_page(
    document_identifier: str,
    page_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific page of a document by identifier (UUID or path)"""
    # Verify document access and get document object
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # Get page
    page = db.query(Page).filter(
        Page.id == page_id,
        Page.document_id == document.path
    ).first()
    
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found or does not belong to this document"
        )
    
    return page


@router.put("/{document_identifier:path}/pages/{page_id}", response_model=PageResponse)
def update_document_page(
    document_identifier: str,
    page_id: uuid.UUID,
    page_update: PageUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update page info by identifier (UUID or path) - mainly for index fields"""
    # Verify document access and get document object
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # Get page
    page = db.query(Page).filter(
        Page.id == page_id,
        Page.document_id == document.path
    ).first()
    
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found or does not belong to this document"
        )
    
    # If page number changed, check for conflicts
    if page_update.page_number and page_update.page_number != page.page_number:
        existing_page = db.query(Page).filter(
            Page.document_id == document.path,
            Page.page_number == page_update.page_number,
            Page.id != page_id
        ).first()
        
        if existing_page:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A page with this number already exists in the document"
            )
    
    # Update fields
    update_data = page_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(page, field, value)
    
    # Update audit fields
    page.updated_by = page_update.updated_by or current_user.username
    
    db.commit()
    db.refresh(page)
    
    return page


@router.delete("/{document_identifier:path}/pages/{page_id}")
def delete_document_page(
    document_identifier: str,
    page_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a page by identifier (UUID or path)"""
    # Verify document access and get document object
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # Get page
    page = db.query(Page).filter(
        Page.id == page_id,
        Page.document_id == document.path
    ).first()
    
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found or does not belong to this document"
        )
    
    db.delete(page)
    db.commit()
    
    return {"message": "Page deleted successfully"}


# ========== File Operation Routes ==========

@router.post("/upload/")
async def upload_document(
    file: UploadFile = File(...),
    folder_path: str = Form(..., description="Folder path, format: /app_slug/folder/subfolder"),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    document_type: DocumentType = Form(DocumentType.GENERAL),
    naming_rule_id: Optional[uuid.UUID] = Form(None),
    device_id: Optional[uuid.UUID] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """上传文档文件（路径优先，兼容UUID）
    
    Note: only saves basic file info, actual processing and conversion happens asynchronously
    
    If naming_rule_id is provided, generates document_number using naming rules.
    Document number format: {basename}{sequence}, e.g. "PO-1001"
    System filenames use UUID for uniqueness.
    
    If naming rule has subfolder_name or device_id is provided, files are stored in device subfolders.
    Organizes files by type in subdirectories to avoid dumping all files in one directory.
    """
    logger = logging.getLogger(__name__)
    
    # 🐛 DEBUG: print received parameters
    print(f"\n{'='*60}")
    print(f"[DEBUG] upload_document received request:")
    print(f"  folder_path={folder_path!r}")
    # folder_path available as str
    print(f"  title={title!r}")
    print(f"  file.filename={file.filename!r}")
    print(f"  current_user={current_user.id} ({current_user.username})")
    print(f"  is_superuser={current_user.is_superuser}")
    
    # Get folder by path
    folder = get_folder_by_identifier_or_path(folder_path, current_user, db, create_if_not_exists=True)
    # 🐛 DEBUG: Show resolved folder info
    print(f"[DEBUG] Folder resolution: folder_path={folder_path!r} → folder.path={folder.path!r}")
    # ======================================
    logger.info(f"✅ upload_document: 通过路径找到文件夹: {folder_path}")
    
    # If naming_rule_id provided, validate rule and get next document number
    generated_document_number = None
    naming_rule = None
    
    if naming_rule_id:
        # Get naming rule
        naming_rule = db.query(FileNamingRule).filter(
            FileNamingRule.id == str(naming_rule_id)
        ).first()
        
        if not naming_rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Naming rule not found"
            )
        
        # Validate naming rule belongs to same app
        # Find app ID via folder->app chain
        app_from_folder = folder.app
        if str(naming_rule.app_id) != str(app_from_folder.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Naming rule does not belong to current app"
            )
        
        # Generate document number (e.g. "PO-1001")
        generated_document_number = f"{naming_rule.basename}{naming_rule.max_number:04d}"
        
        # Increment sequence number
        naming_rule.max_number += naming_rule.increment_by
        naming_rule.updated_by = current_user.username
    
    # Check file size (100MB limit)
    file_size = 0
    temp_file_path = None
    try:
        # Save to temp file
        temp_dir = Path("/tmp/filebot/uploads")
        temp_dir.mkdir(parents=True, exist_ok=True)
        # 🐛 Fix: file.filename may contain path separators (e.g. wet-boew/assets/.../file.png),
        # Use Path().name to extract just the filename, avoid creating nonexistent subdirectories
        temp_basename = Path(file.filename).name
        temp_file_path = temp_dir / f"{uuid.uuid4()}_{temp_basename}"
        
        with open(temp_file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                file_size += len(chunk)
                if file_size > 100 * 1024 * 1024:  # 100MB limit
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File size cannot exceed 100MB"
                    )
                buffer.write(chunk)
        
        # Determine file type and extension
        original_uploaded_filename = file.filename
        file_extension = Path(original_uploaded_filename).suffix.lower()
        
        # Map extension to FileType enum
        extension_to_type = {
            'tiff': FileType.TIFF, 'tif': FileType.TIFF,
            'pdf': FileType.PDF,
            'doc': FileType.DOC, 'docx': FileType.DOCX,
            'jpeg': FileType.JPEG, 'jpg': FileType.JPG,
            'png': FileType.PNG,
            'pcl': FileType.PCL,
            'ps': FileType.PS,
            'txt': FileType.TXT,
            'html': FileType.HTML, 'htm': FileType.HTML
        }
        
        # Remove dot from extension
        ext_without_dot = file_extension.lstrip('.')
        file_type = extension_to_type.get(ext_without_dot, FileType.OTHER)
        
        # Determine MIME type
        # Prefer upload Content-Type; if octet-stream infer from extension
        from_mime = file.content_type or "application/octet-stream"
        extension_to_mime = {
            'html': 'text/html', 'htm': 'text/html',
            'pdf': 'application/pdf',
            'png': 'image/png',
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'svg': 'image/svg+xml',
            'tiff': 'image/tiff', 'tif': 'image/tiff',
            'txt': 'text/plain'
        }
        if from_mime in ('application/octet-stream', '') and ext_without_dot in extension_to_mime:
            mime_type = extension_to_mime[ext_without_dot]
        else:
            mime_type = from_mime
        
        # Determine display filename
        # original_filename preserves user-uploaded filename
        original_filename = original_uploaded_filename
        
        # Note: stored_filename will be set to safe_filename after generate_storage_paths
        # No longer using UUID as filename, using path structure
        
        # If using naming rule, generate document_number
        document_number = None
        if generated_document_number:
            # Generate document number using naming rule (e.g. "PO-1001")
            document_number = generated_document_number
        
        # ========== Device Selection and Storage Path Determination ==========
        selected_device = None
        storage_subfolder = None
        full_storage_path = None
        
        # Calculate file size (MB)
        file_size_mb = file_size // (1024 * 1024) + 1  # Round up
        
        # Case 1: device_id specified
        if device_id:
            selected_device = db.query(Device).filter(
                Device.id == str(device_id),
                Device.is_active == True
            ).first()
            
            if not selected_device:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Specified device not found or not active"
                )
            
            if not selected_device.can_store_file(file_size_mb):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Device '{selected_device.name}' out of space, cannot store file"
                )
        
        # Case 2: using naming rule with subfolder_name, auto-select device
        elif naming_rule and naming_rule.subfolder_name:
            # Get all active storage devices
            storage_devices = db.query(Device).filter(
                Device.is_active == True,
                Device.type == DeviceType.STORAGE  # Use only primary storage devices
            ).all()
            
            if not storage_devices:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No available storage devices, please create one first"
                )
            
            # Select best device
            selected_device = Device.find_best_device_for_storage(storage_devices, file_size_mb)
            
            if not selected_device:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="All storage devices out of space, cannot store file"
                )
            
            # Use naming rule subfolder name
            storage_subfolder = naming_rule.subfolder_name
        
        # Case 3: default storage (no device)
        
        # If device selected, determine storage path
        if selected_device:
            # Ensure device path exists
            if not selected_device.path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Device '{selected_device.name}' has no configured storage path"
                )
            
            # Determine subfolder path
            if not storage_subfolder:
                storage_subfolder = "default"  # Default subfolder
            
            # Build full storage path
            full_storage_path = str(Path(selected_device.path) / storage_subfolder)
            
            # Create subfolder (if not exists)
            Path(full_storage_path).mkdir(parents=True, exist_ok=True)
        
        # ========== End Device Selection and Storage Path Determination ==========
        
        # ========== Path System: Generate Storage Path and URL Path ==========
        # Get app info (via folder)
        app = folder.app
        if not app or not app.slug:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot determine app info, unable to generate storage path"
            )
        
        # Generate storage path and URL path
        data_root = Path(settings.DATA_ROOT)
        storage_path_obj, url_path, safe_filename = generate_storage_paths(
            original_filename=original_filename,
            app_slug=app.slug,
            folder_path=folder.path,
            data_root=data_root
        )
        
        # Ensure directory exists
        if not ensure_directory_exists(storage_path_obj.parent):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Cannot create storage directory: {storage_path_obj.parent}"
            )
        
        # Calculate relative storage path (relative to DATA_ROOT)
        try:
            storage_path = str(storage_path_obj.relative_to(data_root))
        except ValueError:
            # If path outside data_root, use absolute path
            storage_path = str(storage_path_obj)
        
        # Set storage filename to safe filename (path structure, no UUID)
        stored_filename = safe_filename
        
        print(f"[Path System] Generated paths:")
        print(f"  Storage path: {storage_path}")
        print(f"  URL path: {url_path}")
        print(f"  Safe filename: {safe_filename}")
        print(f"  Stored filename: {stored_filename}")
        
        # ========== End Path System Restructuring ==========
        
        # Create document record
        document = Document(
            folder_path=folder.path,
            uploaded_by=str(current_user.id),
            
            # Document info
            title=title or Path(original_filename).stem,
            description=description,
            document_number=document_number,  # Set document number if using naming rule
            status=DocumentStatus.ACTIVE,
            type=document_type,
            comments=f"上传文件: {original_uploaded_filename}" + 
                     (f" (使用命名规则: {naming_rule.basename})" if naming_rule else ""),
            
            # File info
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_size=file_size,
            file_type=file_type,
            mime_type=mime_type,
            
            # Storage device info
            device_id=str(selected_device.id) if selected_device else None,
            storage_subfolder=storage_subfolder,
            full_storage_path=full_storage_path,
            
            # Path system fields
            storage_path=storage_path,
            path=url_path,
            parent_folder_path=folder.path if folder and hasattr(folder, 'path') else None,
            
            # Conversion status
            conversion_status=ConversionStatus.PENDING,
            
            # Audit fields
            created_by=current_user.username
        )
        
        db.add(document)
        
        # Save naming rule update if used
        if naming_rule:
            db.add(naming_rule)
        
        db.commit()
        db.refresh(document)
        
        # ========== Path System: File Storage ==========
        # Use new path system to store file
        target_path = storage_path_obj
        
        # If device selected, allocate storage space
        if selected_device:
            if not selected_device.allocate_space(file_size_mb):
                # Rollback transaction (delete document record)
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Device '{selected_device.name}' space allocation failed"
                )
            
            # Save device capacity update
            db.add(selected_device)
            db.commit()
        
        # Move file to new path
        print(f"[Path System] Moving file to: {target_path}")
        shutil.move(str(temp_file_path), str(target_path))
        
        # Verify file was moved
        if not target_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"File move failed: {target_path} does not exist"
            )
        
        print(f"[Path System] File moved successfully, size: {target_path.stat().st_size} bytes")
        # ========== End Path System Restructuring ==========
        
        # Define supported image file types
        image_file_types = {FileType.JPEG, FileType.JPG, FileType.PNG, FileType.TIFF}
        
        conversion_task = None
        
        # If image file, generate thumbnail and mark complete
        if document.file_type in image_file_types:
            print(f"[Image Processing] Detected image file: {document.file_type}, generating thumbnail")
            success = generate_thumbnail_for_image_document(document, db, settings)
            if success:
                print(f"[Image Processing] Thumbnail generated successfully, document {document.path} marked complete")
                # Image files do not need PDF conversion task
                conversion_task = None
            else:
                print(f"[Image Processing] Thumbnail generation failed, still creating PDF conversion task")
                # If thumbnail fails, create PDF conversion task as fallback
                conversion_task = create_conversion_task_for_document(
                    db, document.path, target_format="pdf"
                )
        else:
            # Non-image file, create PDF conversion task
            conversion_task = create_conversion_task_for_document(
                db, document.path, target_format="pdf"
            )
        
        # Prepare response data
        response_data = {
            "message": "File uploaded successfully, conversion task created",
            "document_path": document.path,
            "conversion_task_id": str(conversion_task.id) if conversion_task else None,
            "original_filename": original_filename,
            "document_number": document_number,  # Document number generated if using naming rule
            "naming_rule_used": naming_rule.basename if naming_rule else None,
            "next_sequence_number": naming_rule.max_number if naming_rule else None,
            # Path system info
            "storage_path": storage_path,
            "path": url_path,
            "safe_filename": safe_filename
        }
        
        return response_data
        
    except Exception as e:
        if temp_file_path and temp_file_path.exists():
            temp_file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )


@router.get("/{document_identifier:path}/download")
def download_document(
    request: Request,
    document_identifier: str,
    download_type: str = Query("original", description="Download type: original or pdf"),
    preview: bool = Query(False, description="Enable preview mode (skip publish status check)"),
    current_user: User = Depends(get_current_active_user_allow_query),
    db: Session = Depends(get_db)
):
    """Download document file by identifier (UUID or path)
    
    Supports downloading original file or converted PDF.
    """
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    import logging
    logger = logging.getLogger(__name__)
    
    # Preview mode (from editor/admin UI): skip publish status check
    if preview:
        logger.info(f"Preview mode accessing doc {document.path}, skipping publish status check")
    else:
        # Check publish status: only PUBLISHED docs accessible via URL
        # Allow access if publish_status is None (legacy docs)
        
        # Check for WebBot request (special permission for unpublished docs)
        is_webbot_request = request.headers.get("X-WebBot-Access") == "true"
        if is_webbot_request:
            logger.info(f"WebBot request accessing unpublished doc {document.path}, skipping publish status check")
        elif document.publish_status is not None and document.publish_status != PublishStatus.PUBLISHED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Document not published, cannot access via URL"
            )
    
    # TODO: Build actual file path based on configured storage path
    # This is just an example implementation
    
    file_path = None
    filename = document.original_filename
    
    if download_type == "pdf" and document.converted_pdf_path:
        # Download PDF version
        file_path = document.converted_pdf_path
        filename = f"{Path(document.original_filename).stem}.pdf"
    else:
        # Download original file
        file_path = get_document_file_path(document, settings)
        filename = document.original_filename
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Determine media_type from document mime_type or file extension
    media_type = document.mime_type if document.mime_type else "application/octet-stream"
    
    # If mime_type is empty/unknown, infer from extension
    if not media_type or media_type == "application/octet-stream":
        if filename.lower().endswith(('.html', '.htm')):
            media_type = "text/html"
        elif filename.lower().endswith('.pdf'):
            media_type = "application/pdf"
        elif filename.lower().endswith(('.jpg', '.jpeg')):
            media_type = "image/jpeg"
        elif filename.lower().endswith('.png'):
            media_type = "image/png"
        elif filename.lower().endswith('.tiff') or filename.lower().endswith('.tif'):
            media_type = "image/tiff"
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type,
        content_disposition_type="inline" if preview else "attachment"
    )


@router.get("/{document_identifier:path}/preview/html")
def preview_html_document(
    request: Request,
    document_identifier: str,
    current_user: User = Depends(get_current_active_user_allow_query),
    db: Session = Depends(get_db)
):
    """HTML preview endpoint - display HTML inline so resources (e.g. /etc/designs/...) load in same-origin iframe"""
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # Only HTML files allowed
    if document.file_type != FileType.HTML:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HTML files are supported for preview"
        )
    
    file_path = get_document_file_path(document, settings)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return FileResponse(
        path=file_path,
        filename=document.original_filename,
        media_type="text/html; charset=utf-8",
        content_disposition_type="inline"
    )


@router.post("/{document_identifier:path}/extract-pages")
async def extract_pages_from_pdf(
    document_identifier: str,
    page_numbers: List[int] = Query(..., description="Page numbers to extract (1-based)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Extract specified page from PDF document by identifier
    
    Note: The generated PDF is a temporary file and will not be saved to the system
    """
    # Verify document access and get document object
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # Check if document is PDF
    if document.file_type != FileType.PDF:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only extract pages from PDF files"
        )
    
    # Get PDF file path
    pdf_path = None
    if document.converted_pdf_path and os.path.exists(document.converted_pdf_path):
        # Use converted PDF version
        pdf_path = document.converted_pdf_path
    else:
        # Use original file (assumed to be PDF)
        pdf_path = get_document_file_path(document, settings)
    
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF file not found"
        )
    
    # Validate page numbers
    try:
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            total_pages = len(pdf_reader.pages)
            
            # Check page range
            for page_num in page_numbers:
                if page_num < 1 or page_num > total_pages:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Page {page_num} out of range (document has {total_pages} pages)"
                    )
            
            # Create PDF writer
            pdf_writer = PyPDF2.PdfWriter()
            
            # Extract specified page
            for page_num in page_numbers:
                page = pdf_reader.pages[page_num - 1]  # Convert to 0-based index
                pdf_writer.add_page(page)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_path = temp_file.name
                # Write extracted page
                with open(temp_path, 'wb') as output_file:
                    pdf_writer.write(output_file)
            
            # Generate download filename
            original_stem = Path(document.original_filename).stem
            if len(page_numbers) == 1:
                download_filename = f"{original_stem}_page{page_numbers[0]}.pdf"
            else:
                page_range = f"pages_{'-'.join(map(str, page_numbers))}"
                download_filename = f"{original_stem}_{page_range}.pdf"
            
            # Return file response (temp file auto-cleaned after send)
            return FileResponse(
                path=temp_path,
                filename=download_filename,
                media_type="application/pdf",
                background=lambda: os.unlink(temp_path)  # Delete temp file after sending
            )
    
    except PyPDF2.errors.PdfReadError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot read PDF file, may be corrupted or not a valid PDF"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting page: {str(e)}"
        )


@router.post("/{document_identifier:path}/extract-tiff-pages")
async def extract_pages_from_tiff(
    document_identifier: str,
    page_numbers: List[int] = Query(..., description="Page numbers to extract (1-based)"),
    output_format: str = Query("pdf", description="Output format: 'pdf' or 'tiff'"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Extract specified page from TIFF document by identifier
    
    Note: The generated file is a temporary file and will not be saved to the system
    """
    # Verify document access and get document object
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # Check if document is TIFF
    if document.file_type not in [FileType.TIFF, FileType.JPEG, FileType.JPG, FileType.PNG]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only extract pages from image files (TIFF/JPEG/PNG)"
        )
    
    # Validate output format
    if output_format.lower() not in ["pdf", "tiff"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Output format must be 'pdf' or 'tiff'"
        )
    
    # Get file path
    file_path = get_document_file_path(document, settings)
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    try:
        # Open TIFF file
        with Image.open(file_path) as img:
            # Get TIFF page count (if multi-page TIFF)
            page_count = 0
            try:
                while True:
                    img.seek(page_count)
                    page_count += 1
            except EOFError:
                # End of file, page_count now has total pages
                pass
            
            # Single-page image case
            if page_count == 0:
                page_count = 1
            
            # Check page range
            for page_num in page_numbers:
                if page_num < 1 or page_num > page_count:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Page number {page_num} out of range (document has {page_count} pages)"
                    )
            
            # Process based on output format
            if output_format.lower() == "pdf":
                return _extract_tiff_pages_to_pdf(
                    file_path, page_numbers, document.original_filename
                )
            else:  # tiff
                return _extract_tiff_pages_to_tiff(
                    file_path, page_numbers, document.original_filename
                )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting page: {str(e)}"
        )


def _extract_tiff_pages_to_pdf(
    tiff_path: str,
    page_numbers: List[int],
    original_filename: str
) -> FileResponse:
    """Extract pages from TIFF and generate PDF"""
    try:
        images = []
        
        # Extract specified page
        for page_num in page_numbers:
            with Image.open(tiff_path) as img:
                # Jump to specified page (0-based index)
                img.seek(page_num - 1)
                
                # Convert to RGB mode (if needed)
                if img.mode not in ["RGB", "L"]:
                    img = img.convert("RGB")
                
                images.append(img.copy())
        
        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_path = temp_file.name
            
            # Save first page
            images[0].save(temp_path, "PDF", save_all=True, 
                          append_images=images[1:] if len(images) > 1 else [])
        
        # Generate download filename
        original_stem = Path(original_filename).stem
        if len(page_numbers) == 1:
            download_filename = f"{original_stem}_page{page_numbers[0]}.pdf"
        else:
            page_range = f"pages_{'-'.join(map(str, page_numbers))}"
            download_filename = f"{original_stem}_{page_range}.pdf"
        
        # Return file response
        return FileResponse(
            path=temp_path,
            filename=download_filename,
            media_type="application/pdf",
            background=lambda: os.unlink(temp_path)  # Delete temp file after sending
        )
    
    except Exception as e:
        # Clean up temp file (if exists)
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise e


def _extract_tiff_pages_to_tiff(
    tiff_path: str,
    page_numbers: List[int],
    original_filename: str
) -> FileResponse:
    """Extract pages from TIFF and generate new TIFF"""
    try:
        images = []
        
        # Extract specified page
        for page_num in page_numbers:
            with Image.open(tiff_path) as img:
                # Jump to specified page (0-based index)
                img.seek(page_num - 1)
                images.append(img.copy())
        
        # Create temporary TIFF file
        with tempfile.NamedTemporaryFile(suffix='.tiff', delete=False) as temp_file:
            temp_path = temp_file.name
            
            # Save first page
            images[0].save(temp_path, "TIFF", save_all=True, 
                          append_images=images[1:] if len(images) > 1 else [],
                          compression="tiff_deflate")
        
        # Generate download filename
        original_stem = Path(original_filename).stem
        if len(page_numbers) == 1:
            download_filename = f"{original_stem}_page{page_numbers[0]}.tiff"
        else:
            page_range = f"pages_{'-'.join(map(str, page_numbers))}"
            download_filename = f"{original_stem}_{page_range}.tiff"
        
        # Return file response
        return FileResponse(
            path=temp_path,
            filename=download_filename,
            media_type="image/tiff",
            background=lambda: os.unlink(temp_path)  # Delete temp file after sending
        )
    
    except Exception as e:
        # Clean up temp file (if exists)
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise e


@router.post("/{document_identifier:path}/retry-conversion")
def retry_document_conversion(
    document_identifier: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retry document conversion by identifier (UUID or path)"""
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    if document.conversion_status not in [ConversionStatus.FAILED, ConversionStatus.PENDING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document current state is {document.conversion_status.value}, cannot retry conversion"
        )
    
    # Reset conversion status
    document.conversion_status = ConversionStatus.PENDING
    document.conversion_error = None
    document.updated_by = current_user.username
    
    db.commit()
    db.refresh(document)
    
    # TODO: trigger async conversion task
    
    return {
        "message": "Conversion task restarted",
        "document_path": document.path,
        "conversion_status": document.conversion_status.value
    }

# ========== TIFF Preview Routes ==========

@router.get("/{document_identifier:path}/tiff-info")
def get_tiff_info(
    document_identifier: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get TIFF file details by identifier (UUID or path)"""
    # Verify document access and get document object
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # Check if document is TIFF
    if document.file_type not in [FileType.TIFF, FileType.JPEG, FileType.JPG, FileType.PNG]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only get info for image files (TIFF/JPEG/PNG)"
        )
    
    # Get file path
    file_path = get_document_file_path(document, settings)
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    try:
        with Image.open(file_path) as img:
            # Get image info
            width, height = img.size
            mode = img.mode
            format = img.format
            
            # Get page count (for multi-page TIFF)
            page_count = 0
            try:
                while True:
                    img.seek(page_count)
                    page_count += 1
            except EOFError:
                # End of file, page_count now has total pages
                pass
            
            # Single-page image case
            if page_count == 0:
                page_count = 1
            
            # Get page dimensions (assuming uniform)
            page_dimensions = []
            for i in range(page_count):
                try:
                    img.seek(i)
                    page_width, page_height = img.size
                    page_dimensions.append({
                        "page_number": i + 1,
                        "width": page_width,
                        "height": page_height,
                        "mode": img.mode
                    })
                except Exception as e:
                    # If page read fails, skip
                    continue
            
            return {
                "document_id": str(document_id),
                "original_filename": document.original_filename,
                "file_type": document.file_type,
                "mime_type": document.mime_type,
                "total_pages": page_count,
                "format": format,
                "page_dimensions": page_dimensions,
                "file_size_bytes": document.file_size
            }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading TIFF file: {str(e)}"
        )


@router.get("/{document_identifier:path}/tiff-thumbnail/{page_number}")
def get_tiff_thumbnail(
    document_identifier: str,
    page_number: int = FastaPath(..., ge=1, description="Page number (1-based)"),
    width: int = Query(200, ge=50, le=800, description="Thumbnail width"),
    height: int = Query(200, ge=50, le=800, description="Thumbnail height"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get thumbnail of a TIFF page by identifier (UUID or path)"""
    # Verify document access and get document object
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # Check if document is TIFF
    if document.file_type not in [FileType.TIFF, FileType.JPEG, FileType.JPG, FileType.PNG]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only get thumbnail for image files (TIFF/JPEG/PNG)"
        )
    
    # Get file path
    file_path = get_document_file_path(document, settings)
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    try:
        with Image.open(file_path) as img:
            # Get page count
            page_count = 0
            try:
                while True:
                    img.seek(page_count)
                    page_count += 1
            except EOFError:
                pass
            
            if page_count == 0:
                page_count = 1
            
            # Check page range
            if page_number < 1 or page_number > page_count:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Page {page_number} out of range (document has {page_count} pages)"
                )
            
            # Jump to specified page
            img.seek(page_number - 1)
            
            # Convert to RGB mode (if needed)
            if img.mode not in ["RGB", "RGBA", "L"]:
                img = img.convert("RGB")
            
            # Generate thumbnail
            img.thumbnail((width, height), Image.Resampling.LANCZOS)
            
            # Save as JPEG (high compression)
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_path = temp_file.name
                
                # If RGBA mode, add white background
                if img.mode == "RGBA":
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
                    img = background
                
                img.save(temp_path, "JPEG", quality=85, optimize=True)
            
            # Generate filename
            original_stem = Path(document.original_filename).stem
            download_filename = f"{original_stem}_page{page_number}_thumbnail.jpg"
            
            # Return file response
            return FileResponse(
                path=temp_path,
                filename=download_filename,
                media_type="image/jpeg",
                background=lambda: os.unlink(temp_path)  # Delete temp file after sending
            )
    
    except Exception as e:
        # Clean up temp file (if exists)
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating thumbnail: {str(e)}"
        )


@router.get("/{document_identifier:path}/tiff-preview/{page_number}")
def get_tiff_preview(
    document_identifier: str,
    page_number: int = FastaPath(..., ge=1, description="Page number (1-based)"),
    max_width: int = Query(1200, ge=100, le=2500, description="Max preview width"),
    max_height: int = Query(1600, ge=100, le=2500, description="Max preview height"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get preview image of a TIFF page by identifier (UUID or path)"""
    # Verify document access and get document object
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # Check if document is TIFF
    if document.file_type not in [FileType.TIFF, FileType.JPEG, FileType.JPG, FileType.PNG]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only get preview for image files (TIFF/JPEG/PNG)"
        )
    
    # Get file path
    file_path = get_document_file_path(document, settings)
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    try:
        with Image.open(file_path) as img:
            # Get page count
            page_count = 0
            try:
                while True:
                    img.seek(page_count)
                    page_count += 1
            except EOFError:
                pass
            
            if page_count == 0:
                page_count = 1
            
            # Check page range
            if page_number < 1 or page_number > page_count:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Page {page_number} out of range (document has {page_count} pages)"
                )
            
            # Jump to specified page
            img.seek(page_number - 1)
            
            # Convert to RGB mode (if needed)
            if img.mode not in ["RGB", "RGBA", "L"]:
                img = img.convert("RGB")
            
            # Resize (maintain aspect ratio)
            original_width, original_height = img.size
            ratio = min(max_width / original_width, max_height / original_height)
            
            if ratio < 1:  # Only downscale, never upscale
                new_width = int(original_width * ratio)
                new_height = int(original_height * ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Save as JPEG (higher quality)
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_path = temp_file.name
                
                # If RGBA mode, add white background
                if img.mode == "RGBA":
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                
                img.save(temp_path, "JPEG", quality=90, optimize=True)
            
            # Generate filename
            original_stem = Path(document.original_filename).stem
            download_filename = f"{original_stem}_page{page_number}_preview.jpg"
            
            # Return file response
            return FileResponse(
                path=temp_path,
                filename=download_filename,
                media_type="image/jpeg",
                background=lambda: os.unlink(temp_path)  # Delete temp file after sending
            )
    
    except Exception as e:
        # Clean up temp file (if exists)
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating preview: {str(e)}"
        )


# ========== Batch Operation Routes ==========

@router.post("/batch/archive")
def batch_archive_documents(
    document_identifiers: List[str],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Batch archive documents by identifier (UUID or path)"""
    updated_count = 0
    
    for doc_identifier in document_identifiers:
        try:
            document = get_document_by_identifier(doc_identifier, current_user, db)
            document.is_archived = True
            document.updated_by = current_user.username
            updated_count += 1
        except HTTPException:
            # Skip documents without permission or not found
            continue
    
    if updated_count > 0:
        db.commit()
    
    return {
        "message": f"Successfully archived {updated_count}/{len(document_identifiers)} documents",
        "updated_count": updated_count
    }


@router.post("/batch/delete")
def batch_delete_documents(
    document_identifiers: List[str],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Batch delete documents by identifier (UUID or path)"""
    deleted_count = 0
    
    for doc_identifier in document_identifiers:
        try:
            document = get_document_by_identifier(doc_identifier, current_user, db)
            db.delete(document)
            deleted_count += 1
        except HTTPException:
            # Skip documents without permission or not found
            continue
    
    if deleted_count > 0:
        db.commit()
    
    return {
        "message": f"Successfully deleted {deleted_count}/{len(document_identifiers)} documents",
        "deleted_count": deleted_count
    }


@router.get("/by-path/{path:path}")
def download_document_by_path(
    request: Request,
    path: str,
    download_type: str = Query("original", description="Download type: original or pdf"),
    db: Session = Depends(get_db)
):
    """
    Download document by original URL path
    
    Path format: /content/dam/cra-arc/camp-promo/features/cvtp_bnnr_360x203.jpg
    Matches documents whose document_metadata.url contains this path
    """
    import json
    
    # Clean path, ensure starts with slash
    if not path.startswith('/'):
        path = '/' + path
    
    logger = logging.getLogger(__name__)
    logger.info(f"Trying path lookup: {path}")
    
    # Store final matched path
    final_path = path
    
    # If path starts with /content, also try without /content (for preview)
    # e.g., /content/dam/... also try /dam/...
    alternative_paths = []
    if path.startswith('/content/'):
        alternative_paths.append(path[len('/content'):])  # Remove leading /content
    elif not path.startswith('/content/') and path != '/content':
        # If path does not start with /content, try adding /content prefix
        alternative_paths.append('/content' + path)
    
    # Manual user authentication (supports anonymous image file access)
    current_user = None
    if request:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            from app.core.security import get_current_user
            user = get_current_user(db, token)
            if user and user.is_active:
                current_user = user
                logger.info(f"Authenticated user via token: {current_user.username}")
    
    # No authenticated user, create public user
    if not current_user:
        from app.models.user import User
        current_user = User(
            id=str(uuid.uuid4()),
            username="public",
            email="public@example.com",
            full_name="Public User",
            is_superuser=False,
            is_active=True,
            role="public"
        )
        logger.info("Using public user (anonymous access)")
    
    # Query all documents for matching URL
    all_documents = db.query(Document).all()
    matched_documents = []
    
    # Paths to try: original + alternatives
    paths_to_try = [path] + alternative_paths
    logger.info(f"Trying path list: {paths_to_try}")
    
    for doc in all_documents:
        matched = False
        
        # Method 1: check new path field first
        if doc.path:
            url_path = doc.path
            # Check if any path matches
            for try_path in paths_to_try:
                # If path fully matches or starts with path
                if url_path == try_path or url_path.endswith(try_path):
                    matched_documents.append((doc, url_path, try_path))
                    logger.info(f"Document {doc.id} matches path {try_path} via path field (url_path: {url_path})")
                    matched = True
                    break  # Stop checking other paths on first match
        
        # Method 2: fallback to document_metadata.url
        if not matched and doc.document_metadata:
            try:
                metadata = json.loads(doc.document_metadata) if isinstance(doc.document_metadata, str) else doc.document_metadata
                url = metadata.get('url') or metadata.get('original_url')
                if url:
                    parsed = urlparse(url)
                    url_path = parsed.path
                    
                    # Check if any path matches
                    for try_path in paths_to_try:
                        # If path fully matches or starts with path
                        if url_path == try_path or url_path.endswith(try_path):
                            matched_documents.append((doc, url, try_path))
                            logger.info(f"Document {doc.id} matches path {try_path} (original URL: {url})")
                            matched = True
                            break  # Stop checking other paths on first match
            except (json.JSONDecodeError, TypeError):
                continue
    
    if not matched_documents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No document found matching the path. Tried: {paths_to_try}"
        )
    
    # If multiple matches, use first (TODO: more precise matching)
    if len(matched_documents) > 1:
        logger.warning(f"Found {len(matched_documents)} matching documents, using first")
    
    document, matched_url, matched_path = matched_documents[0]
    logger.info(f"Using matched document: {document.path}, path: {matched_path}")
    
    # Check if image file type (public access allowed)
    is_image_file = document.file_type in [
        FileType.JPG, FileType.JPEG, FileType.PNG, FileType.TIFF
    ]
    
    # All documents accessed via URL path must be published
    # First get full document info
    
    document = db.query(Document).options(
        joinedload(Document.folder).joinedload(Folder.app)
    ).filter(Document.path == document.path).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check publish status: only PUBLISHED docs accessible via URL
    # Allow access if publish_status is None (legacy docs)
    
    # Check for WebBot request (special permission for unpublished docs)
    is_webbot_request = request.headers.get("X-WebBot-Access") == "true"
    if is_webbot_request:
        logger.info(f"WebBot request accessing unpublished doc {document.path}, skipping publish status check")
    elif document.publish_status is not None and document.publish_status != PublishStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Document not published, cannot access via URL"
        )
    
    if is_image_file:
        # Skip further permission check for image files
        logger.info(f"Image file {document.original_filename} skipping permission check, public access allowed")
    else:
        # Full permission check for non-image files
        document = check_document_access(document.path, current_user, db)
    
    # Direct file download, reuse download_document logic
    # Determine file path and filename
    file_path = None
    filename = document.original_filename
    
    if download_type == "pdf" and document.converted_pdf_path:
        # Download PDF version
        file_path = document.converted_pdf_path
        filename = f"{Path(document.original_filename).stem}.pdf"
    else:
        # Download original file
        file_path = get_document_file_path(document, settings)
        filename = document.original_filename
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Determine media_type from document mime_type or file extension
    media_type = document.mime_type if document.mime_type else "application/octet-stream"
    
    # If mime_type is empty/unknown, infer from extension
    if not media_type or media_type == "application/octet-stream":
        if filename.lower().endswith(('.html', '.htm')):
            media_type = "text/html"
        elif filename.lower().endswith('.pdf'):
            media_type = "application/pdf"
        elif filename.lower().endswith(('.jpg', '.jpeg')):
            media_type = "image/jpeg"
        elif filename.lower().endswith('.png'):
            media_type = "image/png"
        elif filename.lower().endswith('.tiff') or filename.lower().endswith('.tif'):
            media_type = "image/tiff"
    
    logger.info(f"Found document by path: {document.path}, file: {filename}, type: {media_type}")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type
    )


@router.get("/files/{app_slug}/{folder_path:path}/{filename}")
async def serve_file_by_hierarchical_path(
    request: Request,
    app_slug: str,
    folder_path: str,
    filename: str,
    download_type: str = Query("original", description="Download type: original or pdf"),
    db: Session = Depends(get_db)
):
    """使用层次化路径格式直接访问文件
    
    Path format: /files/app-name/folder/subfolder/filename.jpg
    Corresponding storage: data/{app_slug}/{folder_path}/{safe_filename}
    
    Supports both new and legacy document systems:
    1. New documents: uses storage_path and path fields
    2. Legacy documents: lookup by app, folder and filename
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Normalize path: remove leading/trailing slashes
    if folder_path.startswith('/'):
        folder_path = folder_path[1:]
    if folder_path.endswith('/'):
        folder_path = folder_path[:-1]
    
    # Sanitize filename while preserving extension
    from pathlib import Path as PathLib
    path_obj = PathLib(filename)
    stem = path_obj.stem
    ext = path_obj.suffix.lower()
    
    # Sanitize filename stem
    safe_stem = make_filename_safe(stem)
    safe_filename = f"{safe_stem}{ext}" if ext else safe_stem
    
    # Build storage path and URL path
    storage_path = f"{app_slug}/{folder_path}/{safe_filename}"
    url_path = f"/content/dam/{app_slug}/{folder_path}/{safe_filename}"
    
    logger.info(f"Accessing file via hierarchical path: app={app_slug}, folder={folder_path}, filename={filename}")
    logger.info(f"Normalized path: folder_path={folder_path}, safe_filename={safe_filename}")
    logger.info(f"Generated storage path: {storage_path}, URL path: {url_path}")
    
    # Query document: multi-strategy lookup
    document = None
    
    # Strategy 1: exact storage_path or url_path match (new system)
    document = db.query(Document).filter(
        (Document.storage_path == storage_path) | 
        (Document.path == url_path)
    ).first()
    
    if not document:
        # Strategy 2: find app and folder, match filename (legacy)
        logger.warning(f"No exact match found, trying app and folder lookup")
        
        # Get app
        app = db.query(App).filter(App.slug == app_slug).first()
        if not app:
            raise HTTPException(status_code=404, detail=f"App not found: {app_slug}")
        
        # Find folder (exact path match)
        folder = db.query(Folder).filter(
            Folder.app_id == app.id, 
            Folder.path == folder_path
        ).first()
        
        if not folder:
            # Try similar path folder (case-insensitive)
            folder = db.query(Folder).filter(
                Folder.app_id == app.id,
                Folder.path.ilike(f"%{folder_path}%")
            ).first()
            
        if not folder:
            raise HTTPException(status_code=404, detail=f"Folder not found: {folder_path} (app: {app_slug})")
        
        # Find document in specified folder
        # First try exact original_filename match
        document = db.query(Document).filter(
            Document.folder_path == folder.path,
            Document.original_filename == filename
        ).first()
        
        if not document:
            # Try sanitized filename match
            document = db.query(Document).filter(
                Document.folder_path == folder.path,
                Document.original_filename.ilike(f"%{safe_stem}%")
            ).first()
        
        if not document:
            # Finally try any document containing filename
            document = db.query(Document).filter(
                Document.folder_path == folder.path,
                Document.original_filename.ilike(f"%{filename}%")
            ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No matching document found in folder: {folder_path}/{filename}"
            )
    
    # Check if image file type (public access allowed)
    # Based on file type and MIME type
    image_file_types = [FileType.JPG, FileType.JPEG, FileType.PNG, FileType.TIFF]
    is_image_file = (
        document.file_type in image_file_types or
        (document.mime_type and document.mime_type.startswith("image/"))
    )
    
    # Manual user authentication
    current_user = None
    if request:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            from app.core.security import get_current_user
            user = get_current_user(db, token)
            if user and user.is_active:
                current_user = user
                logger.info(f"Authenticated user via token: {current_user.username}")
    
    # No authenticated user, create public user
    if not current_user:
        from app.models.user import User
        current_user = User(
            id=str(uuid.uuid4()),
            username="public",
            email="public@example.com",
            full_name="Public User",
            is_superuser=False,
            is_active=True,
            role="public"
        )
        logger.info("Using public user (anonymous access)")
    
    # Check publish status: only PUBLISHED docs accessible via URL
    # Allow access if publish_status is None (legacy docs)
    
    # Check for WebBot request (special permission for unpublished docs)
    is_webbot_request = request.headers.get("X-WebBot-Access") == "true"
    if is_webbot_request:
        logger.info(f"WebBot request accessing unpublished doc {document.path}, skipping publish status check")
    elif document.publish_status is not None and document.publish_status != PublishStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Document not published, cannot access via URL"
        )
    
    if is_image_file:
        # Skip further permission check for image files
        logger.info(f"Image file {document.original_filename} skipping permission check, public access allowed")
    else:
        # Full permission check for non-image files
        from app.routers.documents import check_document_access
        document = check_document_access(document.path, current_user, db)
    
    # Determine file path and filename
    file_path = None
    output_filename = document.original_filename
    
    if download_type == "pdf" and document.converted_pdf_path:
        # Download PDF version
        file_path = document.converted_pdf_path
        output_filename = f"{Path(document.original_filename).stem}.pdf"
    else:
        # Download original file
        file_path = get_document_file_path(document, settings)
        output_filename = document.original_filename
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Determine media_type from document mime_type or file extension
    media_type = document.mime_type if document.mime_type else "application/octet-stream"
    
    # If mime_type is empty/unknown, infer from extension
    if not media_type or media_type == "application/octet-stream":
        if output_filename.lower().endswith(('.html', '.htm')):
            media_type = "text/html"
        elif output_filename.lower().endswith('.pdf'):
            media_type = "application/pdf"
        elif output_filename.lower().endswith(('.jpg', '.jpeg')):
            media_type = "image/jpeg"
        elif output_filename.lower().endswith('.png'):
            media_type = "image/png"
        elif output_filename.lower().endswith('.tiff') or output_filename.lower().endswith('.tif'):
            media_type = "image/tiff"
        elif output_filename.lower().endswith('.svg'):
            media_type = "image/svg+xml"
    
    logger.info(f"Found document via hierarchical path: {document.path}, file: {output_filename}, type: {media_type}")
    
    return FileResponse(
        path=file_path,
        filename=output_filename,
        media_type=media_type
    )


@router.get("/{document_identifier:path}", response_model=DocumentResponse)
def get_document(
    document_identifier: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get document details by identifier (UUID or path)"""
    document = get_document_by_identifier(document_identifier, current_user, db)
    return document


@router.put("/{document_identifier:path}", response_model=DocumentResponse)
def update_document(
    document_identifier: str,
    document_update: DocumentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update document info by identifier (UUID or path)"""
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # If document number changed, check for conflicts
    if document_update.document_number and document_update.document_number != document.document_number:
        existing_doc = db.query(Document).filter(
            Document.document_number == document_update.document_number,
            Document.path != document.path
        ).first()
        
        if existing_doc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document number already exists"
            )
    
    # Update fields
    update_data = document_update.dict(exclude_unset=True)
    
    # Check if publish status is in update data
    publish_status_changed = False
    old_publish_status = document.publish_status
    new_publish_status = None
    
    if 'publish_status' in update_data:
        new_publish_status = update_data['publish_status']
        publish_status_changed = (old_publish_status != new_publish_status)
    
    for field, value in update_data.items():
        setattr(document, field, value)
    
    # Update audit fields
    document.updated_by = document_update.updated_by or current_user.username
    
    db.commit()
    db.refresh(document)
    
    # Handle publish status changes
    if publish_status_changed:
        try:
            if new_publish_status == PublishStatus.PUBLISHED:
                # Document published: copy to static directory
                result = copy_to_static_directory(document, settings)
                if not result.get('success'):
                    logger.warning(f"Failed to copy published document to static dir: {result.get('error')}")
                else:
                    logger.info(f"Document published, copied to static directory: {document.path}")
                    # Static URL generated dynamically via get_static_file_url
                    # No need to store in database
                        
            elif old_publish_status == PublishStatus.PUBLISHED:
                # Document unpublished: delete from static directory
                result = remove_from_static_directory(document, settings)
                if not result.get('success'):
                    logger.warning(f"Failed to remove unpublished document from static dir: {result.get('error')}")
                else:
                    logger.info(f"Document unpublished, removed from static directory: {document.path}")
                    # No need to clear static URL, it is dynamically generated
                    
        except Exception as e:
            logger.error(f"Error handling publish status change: {e}", exc_info=True)
            # Do not return error, just log to avoid affecting main operation
    
    return document


@router.delete("/{document_identifier:path}")
def delete_document(
    document_identifier: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete document by identifier (UUID or path)
    
    Note: also deletes associated pages and conversion tasks
    """
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # Delete physical file (TODO: configure storage path)
    # Only delete database record for now
    
    db.delete(document)
    db.commit()
    
    return {"message": "Document deleted successfully"}


# ========== Page Routes ==========

