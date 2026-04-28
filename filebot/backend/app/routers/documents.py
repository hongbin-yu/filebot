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


# ========== 权限检查辅助函数 ==========

def check_folder_access(
    folder_id: uuid.UUID,
    current_user: User,
    db: Session,
    require_owner: bool = False
) -> Folder:
    """检查用户是否有权限访问文件夹
    
    Args:
        folder_id: 文件夹ID
        current_user: 当前用户
        db: 数据库会话
        require_owner: 是否要求用户必须是文件夹的所有者（应用所有者）
    
    Returns:
        Folder对象（如果权限检查通过）
    
    Raises:
        HTTPException: 如果文件夹不存在或用户没有权限
    """
    # 将UUID转换为字符串进行查询
    folder_id_str = str(folder_id)
    
    # 超级用户可以访问所有资源
    if current_user.is_superuser or current_user.username == "public":
        folder = db.query(Folder).options(
            joinedload(Folder.app)
        ).filter(Folder.id == folder_id_str).first()
        
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件夹不存在"
            )
        return folder
    
    # 获取文件夹及其关联的应用
    folder = db.query(Folder).options(
        joinedload(Folder.app)
    ).filter(Folder.id == folder_id_str).first()
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件夹不存在"
        )
    
    # 检查应用权限
    app = folder.app
    if app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限访问此文件夹"
        )
    
    # 如果要求所有者，确保用户是应用所有者
    if require_owner and app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有所有者才能执行此操作"
        )
    
    return folder


def get_folder_by_identifier_or_path(
    folder_identifier: str,
    current_user: User,
    db: Session,
    require_owner: bool = False,
    create_if_not_exists: bool = False
) -> Folder:
    """通过ID或路径获取文件夹并进行权限检查（路径优先）
    
    Args:
        folder_identifier: 文件夹路径（如'/test-admin/public-documents'）或UUID（已弃用）
        current_user: 当前用户
        db: 数据库会话
        require_owner: 是否要求用户必须是文件夹的所有者（应用所有者）
        create_if_not_exists: 如果文件夹不存在，是否自动创建
    
    Returns:
        Folder对象（如果权限检查通过）
    
    Raises:
        HTTPException: 如果文件夹不存在或用户没有权限
    
    注意：建议使用路径标识符，UUID支持已弃用
    """
    logger = logging.getLogger(__name__)
    
    # 优先按路径查找（路径优先策略）
    folder = None
    
    # 检查是否是路径格式（以/开头）
    if folder_identifier.startswith('/'):
        # 直接按路径查找
        folder = db.query(Folder).options(
            joinedload(Folder.app)
        ).filter(Folder.path == folder_identifier).first()
        if folder:
            logger.info(f"✅ 通过路径找到文件夹: {folder_identifier}")
    else:
        # 可能是UUID或编码路径
        # 先尝试按路径查找（可能传入的是编码路径）
        try:
            import urllib.parse
            decoded_path = urllib.parse.unquote(folder_identifier)
            if decoded_path.startswith('/'):
                folder = db.query(Folder).options(
                    joinedload(Folder.app)
                ).filter(Folder.path == decoded_path).first()
                if folder:
                    logger.info(f"✅ 通过解码路径找到文件夹: {decoded_path} (原始: {folder_identifier})")
        except:
            pass
    
    # 如果没找到，尝试按UUID查找（向后兼容）
    if not folder:
        # 检查是否是UUID格式
        import re
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
        if uuid_pattern.match(folder_identifier):
            folder = db.query(Folder).options(
                joinedload(Folder.app)
            ).filter(Folder.id == folder_identifier).first()
            if folder:
                logger.warning(f"⚠️  通过UUID找到文件夹: {folder_identifier} (路径: {folder.path})")
        else:
            # 既不是路径也不是UUID，尝试作为路径处理（添加/前缀）
            path = '/' + folder_identifier
            folder = db.query(Folder).options(
                joinedload(Folder.app)
            ).filter(Folder.path == path).first()
            if folder:
                logger.info(f"✅ 通过添加/前缀找到文件夹: {path} (原始: {folder_identifier})")
    
    # 如果文件夹不存在且允许创建
    if not folder and create_if_not_exists:
        # 使用folder_identifier作为路径（可能已经添加了/前缀）
        path = folder_identifier
        if not path.startswith('/'):
            path = '/' + path
            
        # 解析路径：格式为 /app-slug/folder-path
        parts = path.strip('/').split('/')
        if len(parts) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="路径格式无效，应为 /app-slug/folder-path"
            )
    
    # 如果文件夹不存在且允许创建
    if not folder and create_if_not_exists:
        # 解析路径：格式为 /app-slug/folder-path
        parts = path.strip('/').split('/')
        if len(parts) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="路径格式无效，应为 /app-slug/folder-path"
            )
        
        app_slug = parts[0]
        folder_path_parts = parts[1:]
        
        # 查找应用
        app = db.query(App).filter(App.slug == app_slug).first()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"应用 '{app_slug}' 不存在"
            )
        
        # 检查应用权限（超级用户可以跳过）
        if not current_user.is_superuser and app.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限在此应用中创建文件夹"
            )
        
        # 递归创建文件夹和所有父文件夹
        current_path = ''
        parent_folder = None
        
        for i, folder_name in enumerate(folder_path_parts):
            current_path = f'/{app_slug}/{'/'.join(folder_path_parts[:i+1])}'
            
            # 检查文件夹是否已存在
            existing_folder = db.query(Folder).filter(Folder.path == current_path).first()
            if existing_folder:
                parent_folder = existing_folder
                continue
            
            # 创建新文件夹
            new_folder = Folder(
                name=folder_name,
                path=current_path,
                app_id=app.id,
                parent_folder_id=parent_folder.id if parent_folder else None,
                created_by=current_user.username,
                updated_by=current_user.username
            )
            db.add(new_folder)
            db.commit()
            db.refresh(new_folder)
            parent_folder = new_folder
            
            print(f"已创建文件夹: {current_path}")
        
        folder = parent_folder
        # 重新加载关联的应用对象
        folder = db.query(Folder).options(
            joinedload(Folder.app)
        ).filter(Folder.id == folder.id).first()
    
    # 如果文件夹仍然不存在（且不允许创建）
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件夹不存在"
        )
    
    # 超级用户可以访问所有资源
    if current_user.is_superuser or current_user.username == "public":
        return folder
    
    # 检查应用权限
    app = folder.app
    if app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限访问此文件夹"
        )
    
    # 如果要求所有者，确保用户是应用所有者
    if require_owner and app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有所有者才能执行此操作"
        )
    
    return folder


def check_document_access(
    document_id: uuid.UUID,
    current_user: User,
    db: Session,
    require_owner: bool = False
) -> Document:
    """检查用户是否有权限访问文档
    
    Args:
        document_id: 文档ID
        current_user: 当前用户
        db: 数据库会话
        require_owner: 是否要求用户必须是文档的所有者（应用所有者）
    
    Returns:
        Document对象（如果权限检查通过）
    """
    # 将UUID转换为字符串进行查询
    document_id_str = str(document_id)
    
    # 超级用户可以访问所有资源
    if current_user.is_superuser or current_user.username == "public":
        document = db.query(Document).options(
            joinedload(Document.folder).joinedload(Folder.app)
        ).filter(Document.id == document_id_str).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在"
            )
        return document
    
    # 获取文档及其关联的文件夹和应用
    document = db.query(Document).options(
            joinedload(Document.folder).joinedload(Folder.app)
        ).filter(Document.id == document_id_str).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
    
    # 检查应用权限
    app = document.folder.app
    if app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限访问此文档"
        )
    
    # 如果要求所有者，确保用户是应用所有者
    if require_owner and app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有所有者才能执行此操作"
        )
    
    return document


def get_document_by_identifier(
    document_identifier: str,
    current_user: User,
    db: Session,
    require_owner: bool = False
) -> Document:
    """通过标识符（UUID 或路径）获取文档并检查权限
    
    支持两种标识符格式：
    1. UUID格式: "550e8400-e29b-41d4-a716-446655440000"
    2. 路径格式: "/app_slug/folder_path/filename" 或 "/content/dam/..."
    
    Args:
        document_identifier: 文档标识符（UUID字符串或路径）
        current_user: 当前用户
        db: 数据库会话
        require_owner: 是否要求用户必须是文档的所有者（应用所有者）
    
    Returns:
        Document对象（如果权限检查通过）
    """
    import uuid as uuid_module
    
    # 首先尝试作为UUID解析
    try:
        doc_uuid = uuid_module.UUID(document_identifier)
        # 调用现有的check_document_access函数
        return check_document_access(doc_uuid, current_user, db, require_owner)
    except ValueError:
        # 不是有效的UUID，尝试作为路径处理
        pass
    
    # 作为路径处理
    # 规范化路径：确保以斜杠开头
    path = document_identifier
    if not path.startswith('/'):
        path = '/' + path
    
    # 查找文档
    # 首先尝试通过path字段匹配（新文档系统）
    document = db.query(Document).options(
        joinedload(Document.folder).joinedload(Folder.app)
    ).filter(Document.path == path).first()
    
    if not document:
        # 尝试通过storage_path匹配（相对路径）
        from app.core.config import settings as app_settings
        from pathlib import Path
        
        data_root = Path(app_settings.DATA_ROOT)
        # 尝试将路径解释为相对于data_root的存储路径
        # 路径格式可能是: app_slug/folder_path/filename
        if path.startswith('/'):
            path = path[1:]  # 移除开头的斜杠
        
        document = db.query(Document).options(
            joinedload(Document.folder).joinedload(Folder.app)
        ).filter(Document.storage_path == path).first()
    
    if not document:
        # 最后尝试通过组合路径查找（旧系统）
        # 路径格式: /app_slug/folder_path/filename
        # 需要解析出应用slug、文件夹路径和文件名
        parts = path.strip('/').split('/')
        if len(parts) >= 2:
            app_slug = parts[0]
            filename = parts[-1]
            folder_parts = parts[1:-1]
            folder_path = '/' + '/'.join(folder_parts) if folder_parts else '/'
            
            # 通过应用和文件夹查找
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
                        Document.folder_id == folder.id,
                        Document.original_filename.like(f'%{filename}%')
                    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文档不存在: {document_identifier}"
        )
    
    # 检查应用权限（复用check_document_access中的逻辑）
    app = document.folder.app
    if current_user.is_superuser or current_user.username == "public":
        return document
    
    if app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限访问此文档"
        )
    
    # 如果要求所有者，确保用户是应用所有者
    if require_owner and app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有所有者才能执行此操作"
        )
    
    return document


def get_document_file_path(document: Document, settings) -> Path:
    """
    获取文档的实际存储文件路径
    
    根据文档的存储信息构建路径：
    1. 优先使用新的路径系统 (storage_path)
    2. 如果文档有 full_storage_path，使用设备存储路径
    3. 否则，使用默认存储路径
    4. 兼容旧版本爬虫存储路径 (data/documents/)
    """
    # 1. 优先使用新的路径系统
    if document.storage_path:
        # 构建完整路径
        storage_path = Path(settings.DATA_ROOT) / document.storage_path
        if storage_path.exists():
            return storage_path
        else:
            print(f"[路径系统警告] 存储路径不存在: {storage_path}，回退到旧系统")
    
    # 2. 使用旧系统（保持向后兼容）
    if document.full_storage_path and document.stored_filename:
        # 使用设备存储路径
        return Path(document.full_storage_path) / document.stored_filename
    
    # 尝试多个可能的存储位置
    possible_paths = []
    
    # 1. 默认存储路径
    default_path = Path(settings.FILE_STORAGE_PATH) / "original" / document.stored_filename
    possible_paths.append(default_path)
    
    # 2. 旧版本爬虫存储路径 (data/documents/)
    old_crawler_path = Path("data/documents") / document.stored_filename
    possible_paths.append(old_crawler_path)
    
    # 3. 直接使用 stored_filename（如果它是绝对路径）
    if document.stored_filename and os.path.isabs(document.stored_filename):
        possible_paths.append(Path(document.stored_filename))
    
    # 检查哪个路径存在
    for path in possible_paths:
        if path.exists():
            return path
    
    # 如果没有路径存在，返回默认路径（将导致404错误，但至少会抛出明确的异常）
    return default_path


def get_document_pdf_path(document: Document, settings) -> Optional[Path]:
    """
    获取文档的PDF文件路径（如果已转换）
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
    
    生成100x100 PNG缩略图，存储为base64字符串在document_metadata.original_html中，
    并设置conversion_status为COMPLETED。
    
    参数:
        document: Document对象
        db: 数据库会话
        settings: 应用配置
    
    返回:
        bool: 是否成功
    """
    # Import ThumbnailStatus before try block to avoid Python 3.12+ scoping issues
    from app.models.document import ThumbnailStatus

    try:
        # 获取文档文件路径
        file_path = get_document_file_path(document, settings)
        if not file_path or not file_path.exists():
            logging.error(f"文档文件不存在: {document.id}")
            return False
        
        # 打开图像文件
        with Image.open(file_path) as img:
            # 转换为RGB（如果需要）
            if img.mode not in ["RGB", "RGBA", "L"]:
                img = img.convert("RGB")
            
            # 生成100x100缩略图（保持宽高比）
            img.thumbnail((100, 100), Image.Resampling.LANCZOS)
            
            # 如果图像是RGBA模式，添加白色背景
            if img.mode == "RGBA":
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])  # 使用alpha通道作为遮罩
                img = background
            
            # 保存到BytesIO缓冲区（PNG格式）
            buffer = BytesIO()
            img.save(buffer, format="PNG", optimize=True)
            buffer.seek(0)
            
            # 转换为base64字符串
            thumbnail_base64 = base64.b64encode(buffer.read()).decode("utf-8")
            
            # 更新文档元数据
            if not document.document_metadata:
                document.document_metadata = {}
            
            # 将base64缩略图存储在original_html字段中（按照老板要求）
            document.document_metadata["original_html"] = thumbnail_base64
            
            # 同时存储缩略图信息（可选）
            document.document_metadata["thumbnail_base64_png"] = thumbnail_base64
            document.document_metadata["thumbnail_generated"] = True
            document.document_metadata["thumbnail_size"] = "100x100"
            document.document_metadata["thumbnail_format"] = "PNG"
            
            # 更新转换状态为已完成
            document.conversion_status = ConversionStatus.COMPLETED
            
            # 更新缩略图状态
            document.thumbnail_status = ThumbnailStatus.GENERATED
            document.thumbnail_generated_at = datetime.utcnow()
            
            # 保存更改到数据库
            db.add(document)
            db.commit()
            
            logging.info(f"为图像文档 {document.id} 生成缩略图成功")
            return True
            
    except Exception as e:
        logging.error(f"生成图像缩略图失败: {str(e)}", exc_info=True)
        # 更新错误状态
        document.thumbnail_status = ThumbnailStatus.FAILED
        document.thumbnail_error = str(e)[:1000]
        db.add(document)
        db.commit()
        return False


# ========== Document (文档) 路由 ==========

@router.get("/", response_model=List[DocumentResponse])
def get_documents(
    folder_id: Optional[uuid.UUID] = Query(None, description="按文件夹ID筛选（已弃用，建议使用folder_path）"),
    folder_path: Optional[str] = Query(None, description="按文件夹路径筛选，格式: /app_slug/folder/subfolder（推荐）"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    status_filter: Optional[DocumentStatus] = Query(None, description="按文档状态筛选"),
    type_filter: Optional[DocumentType] = Query(None, description="按文档类型筛选"),
    conversion_status_filter: Optional[ConversionStatus] = Query(None, description="按转换状态筛选"),
    search_term: Optional[str] = Query(None, description="搜索文档标题或描述"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取文档列表（路径优先，兼容UUID）
    
    支持多种筛选条件：
    - 按文件夹路径筛选（推荐）
    - 按文件夹ID筛选（已弃用）
    - 按文档状态筛选
    - 按文档类型筛选
    - 按转换状态筛选
    - 按标题/描述搜索
    
    注意：建议使用folder_path参数，folder_id参数已弃用
    """
    logger = logging.getLogger(__name__)
    
    # 检查参数冲突
    if folder_id and folder_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能同时提供folder_id和folder_path参数"
        )
    
    # 记录警告如果使用folder_id
    if folder_id:
        logger.warning(f"⚠️  get_documents: 使用已弃用的folder_id参数: {folder_id}，建议使用folder_path")
    
    # 构建基础查询
    # 注意：使用 selectinload 代替 joinedload 以避免与后续 query.join() 冲突
    query = db.query(Document).options(
        selectinload(Document.folder).selectinload(Folder.app)
    )
    
    # 添加权限筛选：只能查看自己有权限的应用下的文档
    if not current_user.is_superuser:
        # 子查询：获取当前用户拥有的所有应用ID
        user_apps_subquery = db.query(App.id).filter(App.owner_id == current_user.id).subquery()
        
        # 通过文件夹→应用链进行筛选（移除抽屉层）
        query = query.join(Folder).join(App)
        query = query.filter(App.id.in_(user_apps_subquery))
    
    # 应用筛选条件
    if folder_id:
        # 验证用户是否有权限访问该文件夹
        folder = check_folder_access(folder_id, current_user, db)
        # 将UUID转换为字符串进行查询，因为数据库中的folder_id是字符串类型
        query = query.filter(Document.folder_id == str(folder_id))
    elif folder_path:
        # 通过文件夹路径筛选
        # 确保路径以斜杠开头
        path = folder_path
        if not path.startswith('/'):
            path = '/' + path
        
        # 查找文件夹
        folder = db.query(Folder).filter(Folder.path == path).first()
        if not folder:
            # 文件夹不存在，返回空列表
            return []
        
        # 检查权限
        app = folder.app
        if not current_user.is_superuser and app.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此文件夹"
            )
        
        # 筛选文档
        query = query.filter(Document.folder_id == str(folder.id))
    
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
    
    # 排序和分页
    query = query.order_by(Document.created_at.desc())
    documents = query.offset(skip).limit(limit).all()
    
    return documents


@router.get("/path", response_model=List[DocumentResponse])
def get_documents_by_path(
    path: str = Query(..., description="文件夹路径，格式: /app_slug/folder/subfolder"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    status_filter: Optional[DocumentStatus] = Query(None, description="按文档状态筛选"),
    type_filter: Optional[DocumentType] = Query(None, description="按文档类型筛选"),
    conversion_status_filter: Optional[ConversionStatus] = Query(None, description="按转换状态筛选"),
    search_term: Optional[str] = Query(None, description="搜索文档标题或描述"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """根据文件夹路径获取文档列表
    
    通过文件夹路径获取该路径下的所有文档。
    路径格式: /app_slug/folder/subfolder
    """
    # 验证路径格式
    if not path or not path.startswith('/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="路径必须以斜杠开头，格式: /app_slug/folder/subfolder"
        )
    
    # 通过路径查找文件夹
    folder = db.query(Folder).filter(Folder.path == path).first()
    if not folder:
        # 如果文件夹不存在，返回空列表（或者可以尝试通过parent_folder_path查找？）
        # 对于新系统，我们也可以尝试通过parent_folder_path查找文档
        # 但为了安全起见，先检查文件夹是否存在
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"找不到路径对应的文件夹: {path}"
        )
    
    # 验证用户是否有权限访问该文件夹
    try:
        # check_folder_access期望UUID，但我们的folder.id是字符串
        # 转换为UUID进行验证
        import uuid as uuid_module
        folder_uuid = uuid_module.UUID(folder.id)
        folder = check_folder_access(folder_uuid, current_user, db)
    except ValueError:
        # 如果ID不是有效的UUID，仍然进行基本权限检查
        if not current_user.is_superuser:
            # 检查用户是否拥有该应用
            app = db.query(App).filter(App.id == folder.app_id).first()
            if not app or app.owner_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="没有权限访问此文件夹"
                )
    
    # 现在使用文件夹ID查询文档（重用get_documents的逻辑）
    # 构建基础查询
    query = db.query(Document).options(
        joinedload(Document.folder).joinedload(Folder.app)
    )
    
    # 添加权限筛选：只能查看自己有权限的应用下的文档
    if not current_user.is_superuser:
        # 子查询：获取当前用户拥有的所有应用ID
        user_apps_subquery = db.query(App.id).filter(App.owner_id == current_user.id).subquery()
        
        # 通过文件夹→应用链进行筛选（移除抽屉层）
        query = query.join(Folder).join(App)
        query = query.filter(App.id.in_(user_apps_subquery))
    
    # 按文件夹ID筛选
    query = query.filter(Document.folder_id == folder.id)
    
    # 应用其他筛选条件
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
    
    # 排序和分页
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
    
    路径格式: /app_slug/folder_path/document_filename
    示例: /my-app/marketing/brochure.pdf
    
    支持新旧文档系统：
    1. 新文档：通过path字段直接匹配
    2. 旧文档：通过文件夹路径和文件名组合查找
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # 规范化路径：确保以斜杠开头
    if not path.startswith('/'):
        path = '/' + path
    
    logger.info(f"通过路径获取文档详情: {path}")
    
    # 方法1：首先尝试通过path字段直接匹配（新文档系统，路径如 /content/dam/...）
    document = db.query(Document).options(
        joinedload(Document.folder).joinedload(Folder.app)
    ).filter(Document.path == path).first()
    
    if document:
        logger.info(f"通过path字段找到文档: {document.id}, path: {path}")
        # 检查访问权限
        return check_document_access(document.id, current_user, db)
    
    # 方法1.5：尝试通过旧前缀的path字段匹配（兼容旧数据）
    # 新格式: /boarding/canadasite/... (无前缀)
    # 旧格式1: /content/boarding/...
    # 旧格式2: /content/dam/boarding/...
    for prefix in ['/content', '/content/dam']:
        url_path = f"{prefix}{path}"
        document = db.query(Document).options(
            joinedload(Document.folder).joinedload(Folder.app)
        ).filter(Document.path == url_path).first()
        if document:
            logger.info(f"通过{prefix} path字段找到文档: {document.id}, url_path: {url_path}")
            return check_document_access(document.id, current_user, db)
    
    # 方法2：尝试通过storage_path字段匹配
    # storage_path 存储时不带头斜杠(如 "boarding/canadasite/...")
    # 所以同时尝试带/和不带/两种格式
    document = db.query(Document).options(
        joinedload(Document.folder).joinedload(Folder.app)
    ).filter(Document.storage_path == path).first()
    
    if not document:
        # 去掉开头的斜杠再试一次
        storage_path = path.lstrip('/')
        document = db.query(Document).options(
            joinedload(Document.folder).joinedload(Folder.app)
        ).filter(Document.storage_path == storage_path).first()
    
    if document:
        logger.info(f"通过storage_path字段找到文档: {document.id}, path: {path}")
        # 检查访问权限
        return check_document_access(document.id, current_user, db)
    
    # 方法3：解析路径为应用slug、文件夹路径和文件名
    # 路径格式: /app_slug/folder_path/document_filename
    path_parts = path.strip('/').split('/')
    if len(path_parts) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="路径格式无效，至少需要应用slug和文件名"
        )
    
    app_slug = path_parts[0]
    filename = path_parts[-1]
    folder_path_parts = path_parts[1:-1]  # 中间部分为文件夹路径
    folder_path = '/' + '/'.join(folder_path_parts) if folder_path_parts else '/' + app_slug
    
    logger.info(f"解析路径: app_slug={app_slug}, folder_path={folder_path}, filename={filename}")
    
    # 查找应用
    app = db.query(App).filter(App.slug == app_slug).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"应用不存在: {app_slug}"
        )
    
    # 查找文件夹
    folder = db.query(Folder).filter(
        Folder.app_id == app.id,
        Folder.path == folder_path
    ).first()
    
    if not folder:
        # 尝试使用父文件夹路径
        folder = db.query(Folder).filter(
            Folder.app_id == app.id,
            Folder.parent_folder_path == folder_path
        ).first()
        
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文件夹不存在: {folder_path}"
            )
    
    # 安全化文件名比较
    from ..core.path_utils import make_filename_safe
    from pathlib import Path as PathLib
    
    path_obj = PathLib(filename)
    stem = path_obj.stem
    ext = path_obj.suffix.lower()
    safe_stem = make_filename_safe(stem)
    safe_filename = f"{safe_stem}{ext}" if ext else safe_stem
    
    # 查找文档（通过存储文件名）
    document = db.query(Document).options(
        joinedload(Document.folder).joinedload(Folder.app)
    ).filter(
        Document.folder_id == folder.id,
        Document.stored_filename == safe_filename
    ).first()
    
    if not document:
        # 尝试通过原始文件名查找
        document = db.query(Document).options(
            joinedload(Document.folder).joinedload(Folder.app)
        ).filter(
            Document.folder_id == folder.id,
            Document.original_filename == filename
        ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文档不存在: {filename} (路径: {path})"
        )
    
    logger.info(f"通过文件夹和文件名找到文档: {document.id}")
    
    # 检查访问权限
    return check_document_access(document.id, current_user, db)


@router.get("/{document_identifier:path}/pages", response_model=List[PageResponse])
def get_document_pages(
    document_identifier: str,
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """通过标识符（UUID 或路径）获取文档的所有页面"""
    # 先验证文档访问权限并获取文档对象
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # 获取页面列表
    pages = db.query(Page).filter(
        Page.document_id == document.id
    ).order_by(Page.page_number).offset(skip).limit(limit).all()
    
    return pages


@router.get("/{document_identifier:path}/pages/{page_id}", response_model=PageResponse)
def get_document_page(
    document_identifier: str,
    page_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """通过标识符（UUID 或路径）获取文档的特定页面"""
    # 先验证文档访问权限并获取文档对象
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # 获取页面
    page = db.query(Page).filter(
        Page.id == page_id,
        Page.document_id == document.id
    ).first()
    
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="页面不存在或不属于此文档"
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
    """通过标识符（UUID 或路径）更新页面信息（主要用于更新索引字段）"""
    # 先验证文档访问权限并获取文档对象
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # 获取页面
    page = db.query(Page).filter(
        Page.id == page_id,
        Page.document_id == document.id
    ).first()
    
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="页面不存在或不属于此文档"
        )
    
    # 如果修改了页码，检查是否与其他页面冲突
    if page_update.page_number and page_update.page_number != page.page_number:
        existing_page = db.query(Page).filter(
            Page.document_id == document.id,
            Page.page_number == page_update.page_number,
            Page.id != page_id
        ).first()
        
        if existing_page:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="此文档中已存在该页码的页面"
            )
    
    # 更新字段
    update_data = page_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(page, field, value)
    
    # 更新审计字段
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
    """通过标识符（UUID 或路径）删除页面"""
    # 先验证文档访问权限并获取文档对象
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # 获取页面
    page = db.query(Page).filter(
        Page.id == page_id,
        Page.document_id == document.id
    ).first()
    
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="页面不存在或不属于此文档"
        )
    
    db.delete(page)
    db.commit()
    
    return {"message": "页面删除成功"}


# ========== 文件操作路由 ==========

@router.post("/upload/")
async def upload_document(
    file: UploadFile = File(...),
    folder_path: Optional[str] = Form(None, description="文件夹路径，格式: /app_slug/folder/subfolder（推荐）"),
    folder_id: Optional[uuid.UUID] = Form(None, description="文件夹ID（已弃用，建议使用folder_path）"),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    document_type: DocumentType = Form(DocumentType.GENERAL),
    naming_rule_id: Optional[uuid.UUID] = Form(None),
    device_id: Optional[uuid.UUID] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """上传文档文件（路径优先，兼容UUID）
    
    注意：这里只保存文件基本信息，实际的文件处理和转换通过异步任务完成
    
    如果提供了 naming_rule_id，将使用文件命名规则生成文档编号（document_number）
    文档编号格式：{basename}{序列号}，如"PO-1001"
    系统存储的文件名使用UUID确保唯一性，用户不关心系统文件名
    
    如果命名规则包含 subfolder_name 或提供了 device_id，文件将存储到设备的子文件夹中
    实现文件按类型分目录存储，避免所有文件堆在同一个目录
    
    支持通过文件夹路径（推荐）或文件夹ID（已弃用）指定目标文件夹。
    """
    logger = logging.getLogger(__name__)
    
    # 🐛 DEBUG: 打印接收到的参数
    print(f"\n{'='*60}")
    print(f"[DEBUG] upload_document 接收到请求:")
    print(f"  folder_path={folder_path!r}")
    print(f"  folder_id={folder_id!r}")
    print(f"  title={title!r}")
    print(f"  file.filename={file.filename!r}")
    print(f"  current_user={current_user.id} ({current_user.username})")
    print(f"  is_superuser={current_user.is_superuser}")
    
    # 检查至少提供了一个文件夹标识符
    if not folder_path and not folder_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须提供folder_path（推荐）或folder_id参数"
        )
    
    # 记录警告如果使用folder_id
    if folder_id:
        logger.warning(f"⚠️  upload_document: 使用已弃用的folder_id参数: {folder_id}，建议使用folder_path")
    
    # 获取文件夹（路径优先）
    if folder_path:
        # 使用路径查找文件夹，如果不存在则自动创建
        folder = get_folder_by_identifier_or_path(folder_path, current_user, db, create_if_not_exists=True)
        logger.info(f"✅ upload_document: 通过路径找到文件夹: {folder_path}")
        # 确保folder_id指向实际文件夹的ID（修复用folder_path时folder_id=None的bug）
        folder_id = folder.id
    else:
        # 使用ID查找文件夹（向后兼容）
        folder = check_folder_access(folder_id, current_user, db)
        logger.warning(f"⚠️  upload_document: 通过UUID找到文件夹: {folder_id} (路径: {folder.path})")
    
    # 如果提供了命名规则ID，验证规则并获取下一个文档编号
    generated_document_number = None
    naming_rule = None
    
    if naming_rule_id:
        # 获取命名规则
        naming_rule = db.query(FileNamingRule).filter(
            FileNamingRule.id == str(naming_rule_id)
        ).first()
        
        if not naming_rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="命名规则不存在"
            )
        
        # 验证命名规则属于同一个应用
        # 通过文件夹→应用链找到应用ID
        app_from_folder = folder.app
        if str(naming_rule.app_id) != str(app_from_folder.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="命名规则不属于当前应用"
            )
        
        # 生成文档编号（如"PO-1001"）
        generated_document_number = f"{naming_rule.basename}{naming_rule.max_number:04d}"
        
        # 递增序列号
        naming_rule.max_number += naming_rule.increment_by
        naming_rule.updated_by = current_user.username
    
    # 检查文件大小（限制为100MB）
    file_size = 0
    temp_file_path = None
    try:
        # 保存到临时文件
        temp_dir = Path("/tmp/filebot/uploads")
        temp_dir.mkdir(parents=True, exist_ok=True)
        # 🐛 修复: file.filename 可能包含路径分隔符（如 wet-boew/assets/.../file.png），
        # 使用 Path().name 仅取文件名部分，避免创建不存在的子目录
        temp_basename = Path(file.filename).name
        temp_file_path = temp_dir / f"{uuid.uuid4()}_{temp_basename}"
        
        with open(temp_file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                file_size += len(chunk)
                if file_size > 100 * 1024 * 1024:  # 100MB限制
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="文件大小不能超过100MB"
                    )
                buffer.write(chunk)
        
        # 确定文件类型和扩展名
        original_uploaded_filename = file.filename
        file_extension = Path(original_uploaded_filename).suffix.lower()
        
        # 映射扩展名到FileType枚举
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
        
        # 去掉扩展名前的点
        ext_without_dot = file_extension.lstrip('.')
        file_type = extension_to_type.get(ext_without_dot, FileType.OTHER)
        
        # 确定MIME类型
        # 优先使用上传时声明的 Content-Type；如果为 octet-stream 则根据扩展名推断
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
        
        # 确定最终显示的文件名
        # original_filename 保持用户上传的原始文件名
        original_filename = original_uploaded_filename
        
        # 注意：stored_filename将在generate_storage_paths调用后设置为safe_filename
        # 不再使用UUID作为文件名，采用纯path结构
        
        # 如果使用命名规则，生成文档编号（document_number）
        document_number = None
        if generated_document_number:
            # 使用命名规则生成文档编号（如"PO-1001"）
            document_number = generated_document_number
        
        # ========== 设备选择和存储路径确定 ==========
        selected_device = None
        storage_subfolder = None
        full_storage_path = None
        
        # 计算文件大小（MB）
        file_size_mb = file_size // (1024 * 1024) + 1  # 向上取整
        
        # 情况1：指定了device_id
        if device_id:
            selected_device = db.query(Device).filter(
                Device.id == str(device_id),
                Device.is_active == True
            ).first()
            
            if not selected_device:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="指定的设备不存在或未激活"
                )
            
            if not selected_device.can_store_file(file_size_mb):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"设备 '{selected_device.name}' 空间不足，无法存储文件"
                )
        
        # 情况2：使用命名规则，且规则指定了subfolder_name，自动选择设备
        elif naming_rule and naming_rule.subfolder_name:
            # 获取所有活跃的存储设备
            storage_devices = db.query(Device).filter(
                Device.is_active == True,
                Device.type == DeviceType.STORAGE  # 只使用主存储设备
            ).all()
            
            if not storage_devices:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="没有可用的存储设备，请先创建设备"
                )
            
            # 选择最佳设备
            selected_device = Device.find_best_device_for_storage(storage_devices, file_size_mb)
            
            if not selected_device:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="所有存储设备空间不足，无法存储文件"
                )
            
            # 使用命名规则的子文件夹名称
            storage_subfolder = naming_rule.subfolder_name
        
        # 情况3：使用默认存储（不指定设备）
        
        # 如果选择了设备，确定存储路径
        if selected_device:
            # 确保设备路径存在
            if not selected_device.path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"设备 '{selected_device.name}' 没有配置存储路径"
                )
            
            # 确定子文件夹路径
            if not storage_subfolder:
                storage_subfolder = "default"  # 默认子文件夹
            
            # 构建完整存储路径
            full_storage_path = str(Path(selected_device.path) / storage_subfolder)
            
            # 创建子文件夹（如果不存在）
            Path(full_storage_path).mkdir(parents=True, exist_ok=True)
        
        # ========== 设备选择和存储路径确定结束 ==========
        
        # ========== 路径系统重构：生成存储路径和URL路径 ==========
        # 获取应用信息（通过文件夹）
        app = folder.app
        if not app or not app.slug:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无法确定应用信息，无法生成存储路径"
            )
        
        # 生成存储路径和URL路径
        data_root = Path(settings.DATA_ROOT)
        storage_path_obj, url_path, safe_filename = generate_storage_paths(
            original_filename=original_filename,
            app_slug=app.slug,
            folder_path=folder.path,
            data_root=data_root
        )
        
        # 确保目录存在
        if not ensure_directory_exists(storage_path_obj.parent):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"无法创建存储目录: {storage_path_obj.parent}"
            )
        
        # 计算相对存储路径（相对于DATA_ROOT）
        try:
            storage_path = str(storage_path_obj.relative_to(data_root))
        except ValueError:
            # 如果路径不在data_root下，使用绝对路径
            storage_path = str(storage_path_obj)
        
        # 设置存储文件名为安全文件名（纯path结构，不使用UUID）
        stored_filename = safe_filename
        
        print(f"[路径系统] 生成的路径:")
        print(f"  存储路径: {storage_path}")
        print(f"  URL路径: {url_path}")
        print(f"  安全文件名: {safe_filename}")
        print(f"  存储文件名: {stored_filename}")
        
        # ========== 路径系统重构结束 ==========
        
        # 创建文档记录 - 确保所有UUID都转换为字符串
        import uuid as uuid_module
        document = Document(
            id=str(uuid_module.uuid4()),  # 显式设置ID为字符串
            folder_id=str(folder_id),
            uploaded_by=str(current_user.id),
            
            # 文档信息
            title=title or Path(original_filename).stem,
            description=description,
            document_number=document_number,  # 如果使用命名规则，设置文档编号
            status=DocumentStatus.ACTIVE,
            type=document_type,
            comments=f"上传文件: {original_uploaded_filename}" + 
                     (f" (使用命名规则: {naming_rule.basename})" if naming_rule else ""),
            
            # 文件信息
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_size=file_size,
            file_type=file_type,
            mime_type=mime_type,
            
            # 存储设备信息
            device_id=str(selected_device.id) if selected_device else None,
            storage_subfolder=storage_subfolder,
            full_storage_path=full_storage_path,
            
            # 路径系统字段
            storage_path=storage_path,
            path=url_path,
            parent_folder_path=folder.path if folder and hasattr(folder, 'path') else None,
            
            # 转换状态
            conversion_status=ConversionStatus.PENDING,
            
            # 审计字段
            created_by=current_user.username
        )
        
        db.add(document)
        
        # 如果使用了命名规则，保存规则更新
        if naming_rule:
            db.add(naming_rule)
        
        db.commit()
        db.refresh(document)
        
        # ========== 路径系统重构：文件存储 ==========
        # 使用新路径系统存储文件
        target_path = storage_path_obj
        
        # 如果选择了设备，分配存储空间
        if selected_device:
            if not selected_device.allocate_space(file_size_mb):
                # 回滚事务（删除文档记录）
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"设备 '{selected_device.name}' 空间分配失败"
                )
            
            # 保存设备容量更新
            db.add(selected_device)
            db.commit()
        
        # 移动文件到新路径
        print(f"[路径系统] 移动文件到: {target_path}")
        shutil.move(str(temp_file_path), str(target_path))
        
        # 验证文件已移动
        if not target_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"文件移动失败: {target_path} 不存在"
            )
        
        print(f"[路径系统] 文件移动成功，大小: {target_path.stat().st_size} 字节")
        # ========== 路径系统重构结束 ==========
        
        # 定义支持的图像文件类型
        image_file_types = {FileType.JPEG, FileType.JPG, FileType.PNG, FileType.TIFF}
        
        conversion_task = None
        
        # 如果是图像文件，直接生成缩略图并标记为已完成
        if document.file_type in image_file_types:
            print(f"[图像处理] 检测到图像文件: {document.file_type}，生成缩略图")
            success = generate_thumbnail_for_image_document(document, db, settings)
            if success:
                print(f"[图像处理] 缩略图生成成功，文档 {document.id} 标记为已完成")
                # 图像文件不需要PDF转换任务
                conversion_task = None
            else:
                print(f"[图像处理] 缩略图生成失败，但仍创建PDF转换任务")
                # 如果缩略图生成失败，仍创建PDF转换任务作为后备
                conversion_task = create_conversion_task_for_document(
                    db, document.id, target_format="pdf"
                )
        else:
            # 非图像文件，创建PDF转换任务
            conversion_task = create_conversion_task_for_document(
                db, document.id, target_format="pdf"
            )
        
        # 准备响应数据
        response_data = {
            "message": "文件上传成功，转换任务已创建",
            "document_id": str(document.id),
            "conversion_task_id": str(conversion_task.id) if conversion_task else None,
            "original_filename": original_filename,
            "document_number": document_number,  # 如果使用命名规则生成的文档编号
            "naming_rule_used": naming_rule.basename if naming_rule else None,
            "next_sequence_number": naming_rule.max_number if naming_rule else None,
            # 路径系统信息
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
            detail=f"文件上传失败: {str(e)}"
        )


@router.get("/{document_identifier:path}/download")
def download_document(
    request: Request,
    document_identifier: str,
    download_type: str = Query("original", description="下载类型: original 或 pdf"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """通过标识符（UUID 或路径）下载文档文件
    
    支持下载原始文件或转换后的PDF
    """
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # 检查发布状态：只有PUBLISHED状态的文档可以通过URL访问
    # 如果publish_status为None（旧文档），允许访问以保持向后兼容
    
    # 检查是否为WebBot请求（特殊权限允许访问未发布文档）
    import logging
    logger = logging.getLogger(__name__)
    is_webbot_request = request.headers.get("X-WebBot-Access") == "true"
    if is_webbot_request:
        logger.info(f"WebBot请求访问未发布文档 {document.id}，跳过发布状态检查")
    elif document.publish_status is not None and document.publish_status != PublishStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="文档未发布，无法通过URL访问"
        )
    
    # TODO: 根据配置的存储路径构建实际文件路径
    # 这里只是一个示例实现
    
    file_path = None
    filename = document.original_filename
    
    if download_type == "pdf" and document.converted_pdf_path:
        # 下载PDF版本
        file_path = document.converted_pdf_path
        filename = f"{Path(document.original_filename).stem}.pdf"
    else:
        # 下载原始文件
        file_path = get_document_file_path(document, settings)
        filename = document.original_filename
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    # 确定media_type：使用文档的mime_type，如果不存在则根据文件扩展名判断
    media_type = document.mime_type if document.mime_type else "application/octet-stream"
    
    # 如果mime_type为空或未知，根据文件扩展名设置
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
        media_type=media_type
    )


@router.get("/{document_identifier:path}/preview/html")
def preview_html_document(
    request: Request,
    document_identifier: str,
    current_user: User = Depends(get_current_active_user_allow_query),
    db: Session = Depends(get_db)
):
    """HTML预览端点 - 内联显示HTML文件内容，使其引用资源（如/etc/designs/...）可在同源iframe中正常加载"""
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # 只允许HTML文件
    if document.file_type != FileType.HTML:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持HTML文件的预览"
        )
    
    file_path = get_document_file_path(document, settings)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
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
    page_numbers: List[int] = Query(..., description="要提取的页码列表（从1开始）"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """通过标识符（UUID 或路径）从PDF文档中提取指定页面，生成新的临时PDF文件
    
    注意：生成的PDF是临时文件，不会保存到系统中
    """
    # 验证文档访问权限并获取文档对象
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # 检查文档是否为PDF
    if document.file_type != FileType.PDF:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能从PDF文件中提取页面"
        )
    
    # 获取PDF文件路径
    pdf_path = None
    if document.converted_pdf_path and os.path.exists(document.converted_pdf_path):
        # 使用已转换的PDF版本
        pdf_path = document.converted_pdf_path
    else:
        # 使用原始文件（假设已经是PDF）
        pdf_path = get_document_file_path(document, settings)
    
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF文件不存在"
        )
    
    # 验证页码有效性
    try:
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            total_pages = len(pdf_reader.pages)
            
            # 检查页码范围
            for page_num in page_numbers:
                if page_num < 1 or page_num > total_pages:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"页码 {page_num} 超出范围（文档共有 {total_pages} 页）"
                    )
            
            # 创建PDF写入器
            pdf_writer = PyPDF2.PdfWriter()
            
            # 提取指定页面
            for page_num in page_numbers:
                page = pdf_reader.pages[page_num - 1]  # 转换为0-based索引
                pdf_writer.add_page(page)
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_path = temp_file.name
                # 写入提取的页面
                with open(temp_path, 'wb') as output_file:
                    pdf_writer.write(output_file)
            
            # 生成下载文件名
            original_stem = Path(document.original_filename).stem
            if len(page_numbers) == 1:
                download_filename = f"{original_stem}_page{page_numbers[0]}.pdf"
            else:
                page_range = f"pages_{'-'.join(map(str, page_numbers))}"
                download_filename = f"{original_stem}_{page_range}.pdf"
            
            # 返回文件响应（临时文件会在发送后自动清理）
            return FileResponse(
                path=temp_path,
                filename=download_filename,
                media_type="application/pdf",
                background=lambda: os.unlink(temp_path)  # 发送后删除临时文件
            )
    
    except PyPDF2.errors.PdfReadError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法读取PDF文件，文件可能已损坏或不是有效的PDF"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提取页面时发生错误: {str(e)}"
        )


@router.post("/{document_identifier:path}/extract-tiff-pages")
async def extract_pages_from_tiff(
    document_identifier: str,
    page_numbers: List[int] = Query(..., description="要提取的页码列表（从1开始）"),
    output_format: str = Query("pdf", description="输出格式: 'pdf' 或 'tiff'"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """通过标识符（UUID 或路径）从TIFF文档中提取指定页面，生成新的临时文件
    
    注意：生成的文件是临时文件，不会保存到系统中
    """
    # 验证文档访问权限并获取文档对象
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # 检查文档是否为TIFF
    if document.file_type not in [FileType.TIFF, FileType.JPEG, FileType.JPG, FileType.PNG]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能从图像文件（TIFF/JPEG/PNG）中提取页面"
        )
    
    # 验证输出格式
    if output_format.lower() not in ["pdf", "tiff"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="输出格式必须是 'pdf' 或 'tiff'"
        )
    
    # 获取文件路径
    file_path = get_document_file_path(document, settings)
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    try:
        # 打开TIFF文件
        with Image.open(file_path) as img:
            # 获取TIFF页数（如果是多页TIFF）
            page_count = 0
            try:
                while True:
                    img.seek(page_count)
                    page_count += 1
            except EOFError:
                # 到达文件结尾，page_count现在包含总页数
                pass
            
            # 单页图像的情况
            if page_count == 0:
                page_count = 1
            
            # 检查页码范围
            for page_num in page_numbers:
                if page_num < 1 or page_num > page_count:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"页码 {page_num} 超出范围（文档共有 {page_count} 页）"
                    )
            
            # 根据输出格式处理
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
            detail=f"提取页面时发生错误: {str(e)}"
        )


def _extract_tiff_pages_to_pdf(
    tiff_path: str,
    page_numbers: List[int],
    original_filename: str
) -> FileResponse:
    """从TIFF提取页面并生成PDF"""
    try:
        images = []
        
        # 提取指定页面
        for page_num in page_numbers:
            with Image.open(tiff_path) as img:
                # 跳转到指定页面（0-based索引）
                img.seek(page_num - 1)
                
                # 转换为RGB模式（如果需要）
                if img.mode not in ["RGB", "L"]:
                    img = img.convert("RGB")
                
                images.append(img.copy())
        
        # 创建临时PDF文件
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_path = temp_file.name
            
            # 保存第一页
            images[0].save(temp_path, "PDF", save_all=True, 
                          append_images=images[1:] if len(images) > 1 else [])
        
        # 生成下载文件名
        original_stem = Path(original_filename).stem
        if len(page_numbers) == 1:
            download_filename = f"{original_stem}_page{page_numbers[0]}.pdf"
        else:
            page_range = f"pages_{'-'.join(map(str, page_numbers))}"
            download_filename = f"{original_stem}_{page_range}.pdf"
        
        # 返回文件响应
        return FileResponse(
            path=temp_path,
            filename=download_filename,
            media_type="application/pdf",
            background=lambda: os.unlink(temp_path)  # 发送后删除临时文件
        )
    
    except Exception as e:
        # 清理临时文件（如果存在）
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise e


def _extract_tiff_pages_to_tiff(
    tiff_path: str,
    page_numbers: List[int],
    original_filename: str
) -> FileResponse:
    """从TIFF提取页面并生成新的TIFF"""
    try:
        images = []
        
        # 提取指定页面
        for page_num in page_numbers:
            with Image.open(tiff_path) as img:
                # 跳转到指定页面（0-based索引）
                img.seek(page_num - 1)
                images.append(img.copy())
        
        # 创建临时TIFF文件
        with tempfile.NamedTemporaryFile(suffix='.tiff', delete=False) as temp_file:
            temp_path = temp_file.name
            
            # 保存第一页
            images[0].save(temp_path, "TIFF", save_all=True, 
                          append_images=images[1:] if len(images) > 1 else [],
                          compression="tiff_deflate")
        
        # 生成下载文件名
        original_stem = Path(original_filename).stem
        if len(page_numbers) == 1:
            download_filename = f"{original_stem}_page{page_numbers[0]}.tiff"
        else:
            page_range = f"pages_{'-'.join(map(str, page_numbers))}"
            download_filename = f"{original_stem}_{page_range}.tiff"
        
        # 返回文件响应
        return FileResponse(
            path=temp_path,
            filename=download_filename,
            media_type="image/tiff",
            background=lambda: os.unlink(temp_path)  # 发送后删除临时文件
        )
    
    except Exception as e:
        # 清理临时文件（如果存在）
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise e


@router.post("/{document_identifier:path}/retry-conversion")
def retry_document_conversion(
    document_identifier: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """通过标识符（UUID 或路径）重新尝试文档转换（针对转换失败的文档）"""
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    if document.conversion_status not in [ConversionStatus.FAILED, ConversionStatus.PENDING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文档当前状态为 {document.conversion_status.value}，无法重新转换"
        )
    
    # 重置转换状态
    document.conversion_status = ConversionStatus.PENDING
    document.conversion_error = None
    document.updated_by = current_user.username
    
    db.commit()
    db.refresh(document)
    
    # TODO: 触发异步转换任务
    
    return {
        "message": "转换任务已重新启动",
        "document_id": str(document.id),
        "conversion_status": document.conversion_status.value
    }

# ========== TIFF预览相关路由 ==========

@router.get("/{document_identifier:path}/tiff-info")
def get_tiff_info(
    document_identifier: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """通过标识符（UUID 或路径）获取TIFF文件的详细信息（页数、每页尺寸等）"""
    # 验证文档访问权限并获取文档对象
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # 检查文档是否为TIFF
    if document.file_type not in [FileType.TIFF, FileType.JPEG, FileType.JPG, FileType.PNG]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能获取图像文件（TIFF/JPEG/PNG）的信息"
        )
    
    # 获取文件路径
    file_path = get_document_file_path(document, settings)
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    try:
        with Image.open(file_path) as img:
            # 获取图像信息
            width, height = img.size
            mode = img.mode
            format = img.format
            
            # 获取页数（对于多页TIFF）
            page_count = 0
            try:
                while True:
                    img.seek(page_count)
                    page_count += 1
            except EOFError:
                # 到达文件结尾，page_count现在包含总页数
                pass
            
            # 单页图像的情况
            if page_count == 0:
                page_count = 1
            
            # 获取每页尺寸（假设所有页面尺寸相同）
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
                    # 如果无法读取某页，跳过
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
            detail=f"读取TIFF文件时发生错误: {str(e)}"
        )


@router.get("/{document_identifier:path}/tiff-thumbnail/{page_number}")
def get_tiff_thumbnail(
    document_identifier: str,
    page_number: int = FastaPath(..., ge=1, description="页码（从1开始）"),
    width: int = Query(200, ge=50, le=800, description="缩略图宽度"),
    height: int = Query(200, ge=50, le=800, description="缩略图高度"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """通过标识符（UUID 或路径）获取TIFF文件指定页面的缩略图"""
    # 验证文档访问权限并获取文档对象
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # 检查文档是否为TIFF
    if document.file_type not in [FileType.TIFF, FileType.JPEG, FileType.JPG, FileType.PNG]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能获取图像文件（TIFF/JPEG/PNG）的缩略图"
        )
    
    # 获取文件路径
    file_path = get_document_file_path(document, settings)
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    try:
        with Image.open(file_path) as img:
            # 获取页数
            page_count = 0
            try:
                while True:
                    img.seek(page_count)
                    page_count += 1
            except EOFError:
                pass
            
            if page_count == 0:
                page_count = 1
            
            # 检查页码范围
            if page_number < 1 or page_number > page_count:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"页码 {page_number} 超出范围（文档共有 {page_count} 页）"
                )
            
            # 跳转到指定页面
            img.seek(page_number - 1)
            
            # 转换为RGB模式（如果需要）
            if img.mode not in ["RGB", "RGBA", "L"]:
                img = img.convert("RGB")
            
            # 生成缩略图
            img.thumbnail((width, height), Image.Resampling.LANCZOS)
            
            # 保存为JPEG格式（压缩率较高）
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_path = temp_file.name
                
                # 如果是RGBA模式，需要添加白色背景
                if img.mode == "RGBA":
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])  # 使用alpha通道作为遮罩
                    img = background
                
                img.save(temp_path, "JPEG", quality=85, optimize=True)
            
            # 生成文件名
            original_stem = Path(document.original_filename).stem
            download_filename = f"{original_stem}_page{page_number}_thumbnail.jpg"
            
            # 返回文件响应
            return FileResponse(
                path=temp_path,
                filename=download_filename,
                media_type="image/jpeg",
                background=lambda: os.unlink(temp_path)  # 发送后删除临时文件
            )
    
    except Exception as e:
        # 清理临时文件（如果存在）
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成缩略图时发生错误: {str(e)}"
        )


@router.get("/{document_identifier:path}/tiff-preview/{page_number}")
def get_tiff_preview(
    document_identifier: str,
    page_number: int = FastaPath(..., ge=1, description="页码（从1开始）"),
    max_width: int = Query(1200, ge=100, le=2500, description="预览图最大宽度"),
    max_height: int = Query(1600, ge=100, le=2500, description="预览图最大高度"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """通过标识符（UUID 或路径）获取TIFF文件指定页面的预览图像（质量较高，适合查看）"""
    # 验证文档访问权限并获取文档对象
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # 检查文档是否为TIFF
    if document.file_type not in [FileType.TIFF, FileType.JPEG, FileType.JPG, FileType.PNG]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能获取图像文件（TIFF/JPEG/PNG）的预览图"
        )
    
    # 获取文件路径
    file_path = get_document_file_path(document, settings)
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    try:
        with Image.open(file_path) as img:
            # 获取页数
            page_count = 0
            try:
                while True:
                    img.seek(page_count)
                    page_count += 1
            except EOFError:
                pass
            
            if page_count == 0:
                page_count = 1
            
            # 检查页码范围
            if page_number < 1 or page_number > page_count:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"页码 {page_number} 超出范围（文档共有 {page_count} 页）"
                )
            
            # 跳转到指定页面
            img.seek(page_number - 1)
            
            # 转换为RGB模式（如果需要）
            if img.mode not in ["RGB", "RGBA", "L"]:
                img = img.convert("RGB")
            
            # 调整大小（保持宽高比）
            original_width, original_height = img.size
            ratio = min(max_width / original_width, max_height / original_height)
            
            if ratio < 1:  # 只有在需要缩小的情况下才调整大小
                new_width = int(original_width * ratio)
                new_height = int(original_height * ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 保存为JPEG格式（较高质量）
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_path = temp_file.name
                
                # 如果是RGBA模式，需要添加白色背景
                if img.mode == "RGBA":
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                
                img.save(temp_path, "JPEG", quality=90, optimize=True)
            
            # 生成文件名
            original_stem = Path(document.original_filename).stem
            download_filename = f"{original_stem}_page{page_number}_preview.jpg"
            
            # 返回文件响应
            return FileResponse(
                path=temp_path,
                filename=download_filename,
                media_type="image/jpeg",
                background=lambda: os.unlink(temp_path)  # 发送后删除临时文件
            )
    
    except Exception as e:
        # 清理临时文件（如果存在）
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成预览图时发生错误: {str(e)}"
        )


# ========== 批量操作路由 ==========

@router.post("/batch/archive")
def batch_archive_documents(
    document_identifiers: List[str],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """通过标识符（UUID 或路径）批量归档文档"""
    updated_count = 0
    
    for doc_identifier in document_identifiers:
        try:
            document = get_document_by_identifier(doc_identifier, current_user, db)
            document.is_archived = True
            document.updated_by = current_user.username
            updated_count += 1
        except HTTPException:
            # 跳过没有权限或找不到的文档
            continue
    
    if updated_count > 0:
        db.commit()
    
    return {
        "message": f"成功归档 {updated_count}/{len(document_identifiers)} 个文档",
        "updated_count": updated_count
    }


@router.post("/batch/delete")
def batch_delete_documents(
    document_identifiers: List[str],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """通过标识符（UUID 或路径）批量删除文档"""
    deleted_count = 0
    
    for doc_identifier in document_identifiers:
        try:
            document = get_document_by_identifier(doc_identifier, current_user, db)
            db.delete(document)
            deleted_count += 1
        except HTTPException:
            # 跳过没有权限或找不到的文档
            continue
    
    if deleted_count > 0:
        db.commit()
    
    return {
        "message": f"成功删除 {deleted_count}/{len(document_identifiers)} 个文档",
        "deleted_count": deleted_count
    }


@router.get("/by-path/{path:path}")
def download_document_by_path(
    request: Request,
    path: str,
    download_type: str = Query("original", description="下载类型: original 或 pdf"),
    db: Session = Depends(get_db)
):
    """
    根据原始URL路径下载文档
    
    路径格式: /content/dam/cra-arc/camp-promo/features/cvtp_bnnr_360x203.jpg
    会匹配 document_metadata.url 中包含该路径的文档
    """
    import json
    
    # 清理路径，确保以斜杠开头
    if not path.startswith('/'):
        path = '/' + path
    
    logger = logging.getLogger(__name__)
    logger.info(f"尝试通过路径查找文档: {path}")
    
    # 存储最终匹配的路径
    final_path = path
    
    # 如果路径以/content开头，也尝试不带/content的版本（为了前端预览）
    # 例如：/content/dam/... 也尝试 /dam/...
    alternative_paths = []
    if path.startswith('/content/'):
        alternative_paths.append(path[len('/content'):])  # 移除开头的/content
    elif not path.startswith('/content/') and path != '/content':
        # 如果路径不以/content开头，尝试添加/content前缀
        alternative_paths.append('/content' + path)
    
    # 手动处理用户认证（支持匿名访问图片文件）
    current_user = None
    if request:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # 移除"Bearer "前缀
            from app.core.security import get_current_user
            user = get_current_user(db, token)
            if user and user.is_active:
                current_user = user
                logger.info(f"通过token认证用户: {current_user.username}")
    
    # 如果没有认证用户，创建public用户
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
        logger.info("使用public用户（匿名访问）")
    
    # 查询所有文档，查找匹配的URL
    all_documents = db.query(Document).all()
    matched_documents = []
    
    # 尝试的路径列表：原始路径 + 替代路径
    paths_to_try = [path] + alternative_paths
    logger.info(f"尝试匹配的路径列表: {paths_to_try}")
    
    for doc in all_documents:
        matched = False
        
        # 方法1：首先检查新的path字段（如果有）
        if doc.path:
            url_path = doc.path
            # 检查是否匹配任何一个路径
            for try_path in paths_to_try:
                # 如果路径完全匹配或以路径开头
                if url_path == try_path or url_path.endswith(try_path):
                    matched_documents.append((doc, url_path, try_path))
                    logger.info(f"文档 {doc.id} 通过path字段匹配路径 {try_path} (url_path: {url_path})")
                    matched = True
                    break  # 找到一个匹配就停止检查其他路径
        
        # 方法2：如果没有匹配，回退到检查document_metadata.url
        if not matched and doc.document_metadata:
            try:
                metadata = json.loads(doc.document_metadata) if isinstance(doc.document_metadata, str) else doc.document_metadata
                url = metadata.get('url') or metadata.get('original_url')
                if url:
                    parsed = urlparse(url)
                    url_path = parsed.path
                    
                    # 检查是否匹配任何一个路径
                    for try_path in paths_to_try:
                        # 如果路径完全匹配或以路径开头
                        if url_path == try_path or url_path.endswith(try_path):
                            matched_documents.append((doc, url, try_path))
                            logger.info(f"文档 {doc.id} 匹配路径 {try_path} (原始URL: {url})")
                            matched = True
                            break  # 找到一个匹配就停止检查其他路径
            except (json.JSONDecodeError, TypeError):
                continue
    
    if not matched_documents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到路径匹配的文档。尝试的路径: {paths_to_try}"
        )
    
    # 如果有多个匹配，选择第一个（TODO: 可能需要更精确的匹配）
    if len(matched_documents) > 1:
        logger.warning(f"找到 {len(matched_documents)} 个匹配文档，使用第一个")
    
    document, matched_url, matched_path = matched_documents[0]
    logger.info(f"使用匹配的文档: {document.id}, 路径: {matched_path}")
    
    # 检查是否是图片文件类型（允许公开访问）
    is_image_file = document.file_type in [
        FileType.JPG, FileType.JPEG, FileType.PNG, FileType.TIFF
    ]
    
    # 对于所有通过URL路径访问的文档，都必须已发布
    # 首先获取完整的文档信息
    document_id_str = str(document.id)
    document = db.query(Document).options(
        joinedload(Document.folder).joinedload(Folder.app)
    ).filter(Document.id == document_id_str).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
    
    # 检查发布状态：只有PUBLISHED状态的文档可以通过URL访问
    # 如果publish_status为None（旧文档），允许访问以保持向后兼容
    
    # 检查是否为WebBot请求（特殊权限允许访问未发布文档）
    is_webbot_request = request.headers.get("X-WebBot-Access") == "true"
    if is_webbot_request:
        logger.info(f"WebBot请求访问未发布文档 {document.id}，跳过发布状态检查")
    elif document.publish_status is not None and document.publish_status != PublishStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="文档未发布，无法通过URL访问"
        )
    
    if is_image_file:
        # 对于图片文件，跳过进一步的权限检查
        logger.info(f"图片文件 {document.original_filename} 跳过权限检查，允许公开访问")
    else:
        # 对于非图片文件，进行完整的权限检查
        document = check_document_access(document.id, current_user, db)
    
    # 直接提供文件下载，复用 download_document 的逻辑
    # 确定文件路径和文件名
    file_path = None
    filename = document.original_filename
    
    if download_type == "pdf" and document.converted_pdf_path:
        # 下载PDF版本
        file_path = document.converted_pdf_path
        filename = f"{Path(document.original_filename).stem}.pdf"
    else:
        # 下载原始文件
        file_path = get_document_file_path(document, settings)
        filename = document.original_filename
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    # 确定media_type：使用文档的mime_type，如果不存在则根据文件扩展名判断
    media_type = document.mime_type if document.mime_type else "application/octet-stream"
    
    # 如果mime_type为空或未知，根据文件扩展名设置
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
    
    logger.info(f"通过路径找到文档: {document.id}, 文件: {filename}, 类型: {media_type}")
    
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
    download_type: str = Query("original", description="下载类型: original 或 pdf"),
    db: Session = Depends(get_db)
):
    """使用层次化路径格式直接访问文件
    
    路径格式: /files/app-name/folder/subfolder/filename.jpg
    对应存储: data/{app_slug}/{folder_path}/{safe_filename}
    
    支持新旧文档系统：
    1. 新文档：使用storage_path和path字段
    2. 旧文档：通过应用、文件夹和文件名查找
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # 规范化路径：移除首尾斜杠
    if folder_path.startswith('/'):
        folder_path = folder_path[1:]
    if folder_path.endswith('/'):
        folder_path = folder_path[:-1]
    
    # 安全化文件名，同时保留扩展名
    from pathlib import Path as PathLib
    path_obj = PathLib(filename)
    stem = path_obj.stem
    ext = path_obj.suffix.lower()
    
    # 安全化文件名主干
    safe_stem = make_filename_safe(stem)
    safe_filename = f"{safe_stem}{ext}" if ext else safe_stem
    
    # 构建存储路径和URL路径
    storage_path = f"{app_slug}/{folder_path}/{safe_filename}"
    url_path = f"/content/dam/{app_slug}/{folder_path}/{safe_filename}"
    
    logger.info(f"尝试通过层次化路径访问文件: app={app_slug}, folder={folder_path}, filename={filename}")
    logger.info(f"规范化路径: folder_path={folder_path}, safe_filename={safe_filename}")
    logger.info(f"生成的存储路径: {storage_path}, URL路径: {url_path}")
    
    # 查询文档：多策略查找
    document = None
    
    # 策略1：精确匹配storage_path或url_path（新系统）
    document = db.query(Document).filter(
        (Document.storage_path == storage_path) | 
        (Document.path == url_path)
    ).first()
    
    if not document:
        # 策略2：查找应用和文件夹，然后匹配文件名（旧系统）
        logger.warning(f"未找到精确匹配的文档，尝试通过应用和文件夹查找")
        
        # 获取应用
        app = db.query(App).filter(App.slug == app_slug).first()
        if not app:
            raise HTTPException(status_code=404, detail=f"应用不存在: {app_slug}")
        
        # 查找文件夹（精确匹配路径）
        folder = db.query(Folder).filter(
            Folder.app_id == app.id, 
            Folder.path == folder_path
        ).first()
        
        if not folder:
            # 尝试查找路径相似的文件夹（大小写不敏感）
            folder = db.query(Folder).filter(
                Folder.app_id == app.id,
                Folder.path.ilike(f"%{folder_path}%")
            ).first()
            
        if not folder:
            raise HTTPException(status_code=404, detail=f"文件夹不存在: {folder_path} (应用: {app_slug})")
        
        # 在指定文件夹中查找文档
        # 先尝试精确匹配original_filename
        document = db.query(Document).filter(
            Document.folder_id == folder.id,
            Document.original_filename == filename
        ).first()
        
        if not document:
            # 尝试安全化文件名匹配
            document = db.query(Document).filter(
                Document.folder_id == folder.id,
                Document.original_filename.ilike(f"%{safe_stem}%")
            ).first()
        
        if not document:
            # 最后尝试任何包含文件名的文档
            document = db.query(Document).filter(
                Document.folder_id == folder.id,
                Document.original_filename.ilike(f"%{filename}%")
            ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"在文件夹中未找到匹配的文档: {folder_path}/{filename}"
            )
    
    # 检查是否为图片文件类型（允许公开访问）
    # 基于文件类型和MIME类型判断
    image_file_types = [FileType.JPG, FileType.JPEG, FileType.PNG, FileType.TIFF]
    is_image_file = (
        document.file_type in image_file_types or
        (document.mime_type and document.mime_type.startswith("image/"))
    )
    
    # 手动处理用户认证
    current_user = None
    if request:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # 移除"Bearer "前缀
            from app.core.security import get_current_user
            user = get_current_user(db, token)
            if user and user.is_active:
                current_user = user
                logger.info(f"通过token认证用户: {current_user.username}")
    
    # 如果没有认证用户，创建public用户
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
        logger.info("使用public用户（匿名访问）")
    
    # 检查发布状态：只有PUBLISHED状态的文档可以通过URL访问
    # 如果publish_status为None（旧文档），允许访问以保持向后兼容
    
    # 检查是否为WebBot请求（特殊权限允许访问未发布文档）
    is_webbot_request = request.headers.get("X-WebBot-Access") == "true"
    if is_webbot_request:
        logger.info(f"WebBot请求访问未发布文档 {document.id}，跳过发布状态检查")
    elif document.publish_status is not None and document.publish_status != PublishStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="文档未发布，无法通过URL访问"
        )
    
    if is_image_file:
        # 对于图片文件，跳过进一步的权限检查
        logger.info(f"图片文件 {document.original_filename} 跳过权限检查，允许公开访问")
    else:
        # 对于非图片文件，进行完整的权限检查
        from app.routers.documents import check_document_access
        document = check_document_access(document.id, current_user, db)
    
    # 确定文件路径和文件名
    file_path = None
    output_filename = document.original_filename
    
    if download_type == "pdf" and document.converted_pdf_path:
        # 下载PDF版本
        file_path = document.converted_pdf_path
        output_filename = f"{Path(document.original_filename).stem}.pdf"
    else:
        # 下载原始文件
        file_path = get_document_file_path(document, settings)
        output_filename = document.original_filename
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    # 确定media_type：使用文档的mime_type，如果不存在则根据文件扩展名判断
    media_type = document.mime_type if document.mime_type else "application/octet-stream"
    
    # 如果mime_type为空或未知，根据文件扩展名设置
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
    
    logger.info(f"通过层次化路径找到文档: {document.id}, 文件: {output_filename}, 类型: {media_type}")
    
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
    """通过标识符（UUID 或路径）获取文档详情"""
    document = get_document_by_identifier(document_identifier, current_user, db)
    return document


@router.put("/{document_identifier:path}", response_model=DocumentResponse)
def update_document(
    document_identifier: str,
    document_update: DocumentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """通过标识符（UUID 或路径）更新文档信息"""
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # 如果修改了文档编号，检查是否与现有文档冲突
    if document_update.document_number and document_update.document_number != document.document_number:
        existing_doc = db.query(Document).filter(
            Document.document_number == document_update.document_number,
            Document.id != document.id
        ).first()
        
        if existing_doc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文档编号已存在"
            )
    
    # 更新字段
    update_data = document_update.dict(exclude_unset=True)
    
    # 检查发布状态是否在更新数据中
    publish_status_changed = False
    old_publish_status = document.publish_status
    new_publish_status = None
    
    if 'publish_status' in update_data:
        new_publish_status = update_data['publish_status']
        publish_status_changed = (old_publish_status != new_publish_status)
    
    for field, value in update_data.items():
        setattr(document, field, value)
    
    # 更新审计字段
    document.updated_by = document_update.updated_by or current_user.username
    
    db.commit()
    db.refresh(document)
    
    # 处理发布状态变化
    if publish_status_changed:
        try:
            if new_publish_status == PublishStatus.PUBLISHED:
                # 文档被发布：复制到静态目录
                result = copy_to_static_directory(document, settings)
                if not result.get('success'):
                    logger.warning(f"发布文档时复制到静态目录失败: {result.get('error')}")
                else:
                    logger.info(f"文档发布成功，已复制到静态目录: {document.id}")
                    # 静态URL可以通过get_static_file_url函数动态生成
                    # 不需要存储在数据库中
                        
            elif old_publish_status == PublishStatus.PUBLISHED:
                # 文档被取消发布：从静态目录删除
                result = remove_from_static_directory(document, settings)
                if not result.get('success'):
                    logger.warning(f"取消发布文档时从静态目录删除失败: {result.get('error')}")
                else:
                    logger.info(f"文档取消发布成功，已从静态目录删除: {document.id}")
                    # 不需要清除静态URL，因为它是动态生成的
                    
        except Exception as e:
            logger.error(f"处理发布状态变化时出错: {e}", exc_info=True)
            # 不返回错误，仅记录日志，避免影响主要更新操作
    
    return document


@router.delete("/{document_identifier:path}")
def delete_document(
    document_identifier: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """通过标识符（UUID 或路径）删除文档
    
    注意：会同时删除关联的页面和转换任务
    """
    document = get_document_by_identifier(document_identifier, current_user, db)
    
    # 删除物理文件（TODO: 需要配置存储路径）
    # 这里暂时只删除数据库记录
    
    db.delete(document)
    db.commit()
    
    return {"message": "文档删除成功"}


# ========== Page (页面) 路由 ==========

