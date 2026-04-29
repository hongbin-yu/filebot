from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, select
from typing import List, Optional
import uuid
import logging
import re
import unicodedata
from pydantic import BaseModel

from pathlib import Path

from app.db.database import get_db
from app.models.folder import Folder
from app.models.document import Document
from app.models.app import App
from app.models.user import User
from app.schemas.app import FolderCreate, FolderUpdate, FolderResponse
from app.core.security import get_current_active_user
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def to_slug(text: str) -> str:
    """
    Convert a string to a URL-friendly slug
    Similar to frontend toSlug function
    """
    if not text:
        return ''
    
    # Convert to lowercase
    text = text.lower()
    
    # Normalize and remove accents
    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    
    # Replace spaces and special characters
    text = re.sub(r'[^a-z0-9\s-]', '', text)  # Remove non-alphanumeric except spaces and hyphens
    text = re.sub(r'[\s-]+', '-', text)  # Replace spaces and multiple hyphens with single hyphen
    text = text.strip('-')  # Trim hyphens from start and end
    
    return text


def generate_folder_path(folder_name: str, app_slug: str, parent_path: str = "") -> str:
    """
    Generate a hierarchical path for a folder in the new architecture
    Format: /{app_slug}/{folder_slug} or with parent folders
    """
    folder_slug = to_slug(folder_name)
    
    if parent_path:
        # If parent path exists, append folder slug to it
        return f"{parent_path.rstrip('/')}/{folder_slug}"
    else:
        # Root folder in app
        return f"/{app_slug}/{folder_slug}"


class MoveFolderRequest(BaseModel):
    """移动文件夹请求模型（只能在同一应用内移动）"""
    target_parent_folder_id: Optional[str] = None  # 目标父文件夹ID（留空表示移动到应用根目录）


def update_folder_path_recursive(
    folder_id: str,
    new_parent_folder_path: str,
    db: Session
):
    """
    递归更新文件夹及其所有子文件夹和文档的路径
    
    Args:
        folder_id: 要更新的文件夹ID
        new_parent_folder_path: 新的父文件夹路径（对于根文件夹是/app_slug，对于子文件夹是父文件夹的完整路径）
        db: 数据库会话
    """
    # 获取当前文件夹
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        return
    
    # 获取应用信息以生成文件夹slug
    app = db.query(App).filter(App.id == folder.app_id).first()
    if not app:
        app_slug = "unknown"
    else:
        app_slug = app.slug if app.slug else to_slug(app.name)
    
    # 计算当前文件夹的新路径
    # 文件夹的完整路径 = parent_folder_path + '/' + folder_slug
    # 但注意：new_parent_folder_path 已经是父文件夹的完整路径
    # 对于根文件夹，new_parent_folder_path 是 /app_slug
    # 对于子文件夹，new_parent_folder_path 是父文件夹的完整路径
    
    # 生成文件夹slug
    folder_slug = to_slug(folder.name)
    
    # 计算文件夹的新完整路径
    if new_parent_folder_path == f"/{app_slug}":
        # 这是根文件夹（在应用下）
        new_folder_path = f"/{app_slug}/{folder_slug}"
    else:
        # 子文件夹
        new_folder_path = f"{new_parent_folder_path.rstrip('/')}/{folder_slug}"
    
    # 更新文件夹的path和parent_folder_path
    folder.path = new_folder_path
    folder.parent_folder_path = new_parent_folder_path
    
    # 更新此文件夹中所有文档的parent_folder_path
    # 文档的parent_folder_path应该是文件夹的完整路径
    db.query(Document).filter(Document.folder_id == folder_id).update(
        {"parent_folder_path": new_folder_path}
    )
    
    # 递归更新所有子文件夹
    # 注意：子文件夹的new_parent_folder_path应该是当前文件夹的新完整路径
    subfolders = db.query(Folder).filter(Folder.parent_folder_id == folder_id).all()
    for subfolder in subfolders:
        update_folder_path_recursive(subfolder.id, new_folder_path, db)


@router.get("/", response_model=List[FolderResponse])
def get_folders(
    app_id: Optional[str] = Query(None, description="应用ID或slug"),
    parent_folder_id: Optional[str] = Query(None, description="父文件夹ID（留空表示根文件夹）"),
    parent_folder_path: Optional[str] = Query(None, description="父文件夹路径（用于路径系统）"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取文件夹列表（可按应用和父文件夹过滤）"""
    # 调试日志：记录API调用参数
    logger.info(f"📂 get_folders API called: app_id={app_id}, parent_folder_id={parent_folder_id}, parent_folder_path={parent_folder_path}, user={current_user.username}")
    
    query = db.query(Folder)
    
    # 根据app_id过滤（如果提供）
    if app_id:
        # 查找应用（支持UUID和slug）
        app = db.query(App).filter(
            (App.id == app_id) | (App.slug == app_id)
        ).first()
        
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="应用不存在"
            )
        
        # 验证权限
        # 特殊处理：public用户可以访问所有应用的文件夹（用于Client门户）
        if current_user.username != "public":
            if not current_user.is_superuser and app.owner_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="没有权限访问此应用的文件夹"
                )
        
        query = query.filter(Folder.app_id == app.id)
        
        # 同时按应用路径过滤，确保文件夹路径以应用slug开头
        app_slug_to_use = app.slug if app.slug else to_slug(app.name)
        app_path = f"/{app_slug_to_use}"
        # 添加路径过滤：文件夹路径必须以应用路径开头
        query = query.filter(Folder.path.startswith(app_path))
        
        logger.info(f"  → 应用过滤: app.id={app.id}, app.slug={app.slug}, app.name={app.name}, app_path={app_path}")
    
    # 根据parent_folder_id过滤
    if parent_folder_id is not None:
        if parent_folder_id == "" or parent_folder_id == "null":
            # 获取根文件夹（parent_folder_id为None）
            query = query.filter(Folder.parent_folder_id.is_(None))
        else:
            # 验证父文件夹存在且在同一应用下
            parent_folder = db.query(Folder).filter(Folder.id == parent_folder_id).first()
            if not parent_folder:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="父文件夹不存在"
                )
            
            # 如果指定了app_id，确保父文件夹属于同一个应用
            if app_id and parent_folder.app_id != app.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="父文件夹不属于指定应用"
                )
            
            query = query.filter(Folder.parent_folder_id == parent_folder_id)
    
    # 根据parent_folder_path过滤（如果提供）
    if parent_folder_path is not None:
        logger.info(f"  → parent_folder_path过滤: {parent_folder_path}")
        if parent_folder_path == "" or parent_folder_path == "null" or parent_folder_path == "-":
            # 根文件夹：parent_folder_path为空或特定标记
            query = query.filter(Folder.parent_folder_path.is_(None) | (Folder.parent_folder_path == "") | (Folder.parent_folder_path == "-"))
        else:
            # 验证父文件夹路径存在（可选）
            # 注意：这里不验证是否属于同一应用，因为parent_folder_path本身应该包含应用信息
            query = query.filter(Folder.parent_folder_path == parent_folder_path)
    elif app_id and parent_folder_id is None:
        # 如果没有提供parent_folder_path，但提供了app_id且没有parent_folder_id，
        # 默认返回应用根目录的直接子文件夹
        app_root_path = f"/{app_slug_to_use}"
        logger.info(f"  → 默认过滤: 返回应用根目录的直接子文件夹，parent_folder_path = {app_root_path}")
        
        # 先尝试按parent_folder_path过滤
        query = query.filter(Folder.parent_folder_path == app_root_path)
        
        # 如果没有找到（可能数据不一致），尝试基于路径深度过滤
        # 计算找到的文件夹数量
        from sqlalchemy import func
        test_query = query.with_entities(func.count(Folder.id))
        count_result = test_query.scalar()
        
        if count_result == 0:
            logger.info(f"  → 没有找到parent_folder_path = {app_root_path}的文件夹，尝试基于路径深度过滤")
            # 重新构建查询
            query = db.query(Folder).filter(Folder.app_id == app.id)
            # 重新应用路径过滤
            query = query.filter(Folder.path.startswith(app_root_path))
            # 过滤直接子文件夹：路径深度为2（/{app_slug}/folder-name）
            # 使用SQLite的LENGTH和REPLACE函数计算斜杠数量
            query = query.filter(
                func.length(Folder.path) - func.length(func.replace(Folder.path, '/', '')) == 2
            )
    
    # 使用子查询获取每个文件夹的文档数量
    from sqlalchemy import func
    from sqlalchemy.orm import joinedload
    
    # 创建文档计数的子查询
    doc_count_subquery = db.query(
        Document.folder_id,
        func.count(Document.id).label('document_count')
    ).group_by(Document.folder_id).subquery()
    
    # 修改查询以左连接文档计数，并加载app关系以获取app_slug
    folders_with_counts = query.options(joinedload(Folder.app)).outerjoin(
        doc_count_subquery,
        Folder.id == doc_count_subquery.c.folder_id
    ).with_entities(
        Folder,
        func.coalesce(doc_count_subquery.c.document_count, 0).label('document_count')
    ).order_by(Folder.name).all()
    
    # 将文档计数添加到文件夹对象中并确保app关系已加载
    folders = []
    for folder_obj, doc_count in folders_with_counts:
        # 设置document_count属性，以便response_model可以序列化
        folder_obj.document_count = doc_count
        folders.append(folder_obj)
    
    # 调试：记录查询条件摘要
    logger.info(f"  → 查询条件摘要: app_id={app_id}, parent_folder_id={parent_folder_id}, parent_folder_path={parent_folder_path}")
    logger.info(f"  → 返回文件夹数量: {len(folders)}")
    
    # 记录前10个文件夹的应用分布
    if folders:
        app_distribution = {}
        for f in folders[:20]:  # 检查前20个
            app_key = f.app_id[:8] + "..." if f.app_id else "None"
            app_distribution[app_key] = app_distribution.get(app_key, 0) + 1
        
        logger.info(f"  → 应用分布（前20个）: {app_distribution}")
        
        if len(folders) <= 10:
            for i, f in enumerate(folders):
                logger.info(f"    [{i}] id={f.id}, name={f.name}, path={f.path}, app_id={f.app_id}")
        else:
            # 只记录前5个和后5个
            for i, f in enumerate(folders[:5]):
                logger.info(f"    [{i}] id={f.id}, name={f.name}, path={f.path}, app_id={f.app_id}")
            logger.info(f"    ... 还有 {len(folders)-10} 个文件夹 ...")
            for i, f in enumerate(folders[-5:], start=len(folders)-5):
                logger.info(f"    [{i}] id={f.id}, name={f.name}, path={f.path}, app_id={f.app_id}")
    
    return folders


@router.post("/", response_model=FolderResponse)
def create_folder(
    folder_data: FolderCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建文件夹"""
    logger.info(f"创建文件夹请求: {folder_data.dict()}, 用户: {current_user.username}")
    
    # 验证应用存在 - 支持通过UUID或slug查找
    app = None
    app_id_str = str(folder_data.app_id)
    
    # 先尝试按UUID查找
    try:
        import uuid as uuid_module
        # 检查是否是有效的UUID格式
        uuid_obj = uuid_module.UUID(app_id_str)
        app = db.query(App).filter(App.id == app_id_str).first()
    except ValueError:
        # 不是有效的UUID，尝试按slug查找
        app = db.query(App).filter(App.slug == app_id_str).first()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="应用不存在"
        )
    
    # 验证权限
    if not current_user.is_superuser and app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限在此应用下创建文件夹"
        )
    
    # 首先获取父文件夹信息（路径解析优先于UUID）
    parent_path = ""
    parent_folder = None
    parent_folder_uuid = None
    if folder_data.parent_folder_id:
        parent_folder_id_str = str(folder_data.parent_folder_id)
        
        # 尝试按UUID查找父文件夹
        try:
            import uuid as uuid_module
            uuid_obj = uuid_module.UUID(parent_folder_id_str)
            parent_folder = db.query(Folder).filter(Folder.id == parent_folder_id_str).first()
        except ValueError:
            # 不是有效的UUID，尝试按路径查找
            path = parent_folder_id_str
            if not path.startswith('/'):
                path = '/' + path
            parent_folder = db.query(Folder).filter(Folder.path == path).first()
        
        if parent_folder:
            parent_path = parent_folder.path
            parent_folder_uuid = str(parent_folder.id)
            # 验证父文件夹属于同一个应用
            if parent_folder.app_id != str(app.id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="父文件夹不属于同一个应用"
                )
    
    # 检查文件夹名称是否已存在（在同一应用和父文件夹下）
    # 使用父文件夹的UUID进行精确匹配（避免路径字符串比较问题）
    existing_folder_filter = [
        Folder.name == folder_data.name,
        Folder.app_id == str(app.id),
    ]
    if parent_folder_uuid:
        existing_folder_filter.append(Folder.parent_folder_id == parent_folder_uuid)
    else:
        existing_folder_filter.append(Folder.parent_folder_id == None)
    
    existing_folder = db.query(Folder).filter(*existing_folder_filter).first()
    
    if existing_folder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此位置下已存在同名的文件夹"
        )
    
    # 生成文件夹路径
    app_slug = app.slug if app.slug else to_slug(app.name)
    folder_path = generate_folder_path(
        folder_name=folder_data.name,
        app_slug=app_slug,
        parent_path=parent_path
    )
    
    # 计算 parent_folder_path
    if folder_data.parent_folder_id and parent_folder:
        # 有父文件夹，parent_folder_path 是父文件夹的完整路径
        parent_folder_path = parent_folder.path
    else:
        # 根文件夹，parent_folder_path 是 /app_slug
        # 根据用户要求，不能有空字符串，空字符串用"-"替代
        parent_folder_path = f"/{app_slug}" if app_slug else "-"
    
    # 🐛 DEBUG: 打印即将创建的文件夹信息
    print(f"[DEBUG] 创建文件夹: name={folder_data.name!r} parent_folder_id={folder_data.parent_folder_id!r}")
    print(f"  → parent_folder={parent_folder.path if parent_folder else None} (id={parent_folder_uuid})")
    print(f"  → app_slug={app_slug} parent_path={parent_path}")
    print(f"  → 生成的文件夹路径={folder_path}")
    print(f"  → parent_folder_path={parent_folder_path}")
    # ===============================================
    
    # 创建文件夹记录
    db_folder = Folder(
        id=str(uuid.uuid4()),
        app_id=str(app.id),  # 使用应用的UUID ID
        parent_folder_id=str(parent_folder.id) if parent_folder else None,
        name=folder_data.name,
        path=folder_path,  # 使用生成的路径
        parent_folder_path=parent_folder_path,
        description=folder_data.description,
        created_by=current_user.username
    )
    
    db.add(db_folder)
    db.commit()
    db.refresh(db_folder)
    
    return db_folder


@router.get("/ancestors-by-path", response_model=List[FolderResponse])
def get_folder_ancestors_by_path(
    path: str = Query(..., description="文件夹完整路径，如 /app_slug/folder/subfolder"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    根据文件夹路径获取所有祖先文件夹列表（从根到当前文件夹）
    
    路径格式: /{app_slug}/{folder_slug}/{subfolder_slug}
    返回: [根文件夹, ..., 当前文件夹]
    
    使用 query parameter 而非 path parameter，避免 URL 编码 / 导致路由冲突
    """
    logger = logging.getLogger(__name__)
    logger.info(f"📂 get_folder_ancestors_by_path called with path: '{path}'")
    
    # 确保路径以斜杠开头
    if not path.startswith('/'):
        path = '/' + path
    
    # 分割路径为各个层级
    parts = [p for p in path.split('/') if p]
    if len(parts) < 1:
        return []
    
    # 构建所有前缀路径并查询
    # 注意：某些层级（如 /boarding）可能不是独立的文件夹，根文件夹可能是 /boarding/canadasite
    # 因此不直接在未找到时break，而是跳过缺失的层级，继续构建
    ancestors = []
    prefix = ""
    for i, part in enumerate(parts):
        prefix = f"{prefix}/{part}"
        folder = db.query(Folder).filter(Folder.path == prefix).first()
        if folder:
            # 验证权限
            if not current_user.is_superuser:
                app = db.query(App).filter(App.id == folder.app_id).first()
                if app and current_user.username != "public" and app.owner_id != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"没有权限访问此文件夹: {prefix}"
                    )
            ancestors.append(folder)
    
    logger.info(f"📂 get_folder_ancestors_by_path: found {len(ancestors)} ancestors for path '{path}'")
    return ancestors


@router.get("/{folder_identifier}", response_model=FolderResponse)
def get_folder(
    folder_identifier: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取文件夹详情（路径优先，兼容UUID）
    
    注意：建议使用路径标识符，UUID支持已弃用
    路径格式：/{app_slug}/{folder_path}
    示例：/boarding/canadasite/en/employment-social-development
    """
    logger = logging.getLogger(__name__)
    
    # 优先按路径查找（路径优先策略）
    folder = None
    
    # 检查是否是路径格式（以/开头）
    if folder_identifier.startswith('/'):
        # 直接按路径查找
        folder = db.query(Folder).filter(Folder.path == folder_identifier).first()
        if folder:
            logger.info(f"✅ 通过路径找到文件夹: {folder_identifier}")
    else:
        # 可能是UUID或编码路径
        # 先尝试按路径查找（可能传入的是编码路径）
        # 尝试解码路径（如果包含编码字符）
        try:
            import urllib.parse
            decoded_path = urllib.parse.unquote(folder_identifier)
            if decoded_path.startswith('/'):
                folder = db.query(Folder).filter(Folder.path == decoded_path).first()
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
            folder = db.query(Folder).filter(Folder.id == folder_identifier).first()
            if folder:
                logger.warning(f"⚠️  通过UUID找到文件夹: {folder_identifier} (路径: {folder.path})")
                logger.warning(f"⚠️  建议使用路径标识符: {folder.path}")
        else:
            # 既不是路径也不是UUID，尝试作为路径处理（添加/前缀）
            path = '/' + folder_identifier
            folder = db.query(Folder).filter(Folder.path == path).first()
            if folder:
                logger.info(f"✅ 通过添加/前缀找到文件夹: {path} (原始: {folder_identifier})")
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文件夹不存在 (标识符: {folder_identifier})"
        )
    
    # 计算文档数量
    from sqlalchemy import func
    doc_count = db.query(func.count(Document.id)).filter(
        Document.folder_id == folder.id
    ).scalar() or 0
    
    # 验证权限（通过应用）
    app = db.query(App).filter(App.id == folder.app_id).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="关联的应用不存在"
        )
    
    # 特殊处理：public用户可以访问所有文件夹（用于Client门户）
    if current_user.username != "public":
        if not current_user.is_superuser and app.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此文件夹"
            )
    
    # 设置document_count属性，以便response_model可以序列化
    folder.document_count = doc_count
    
    return folder


@router.get("/by-path/{path:path}", response_model=FolderResponse)
def get_folder_by_path(
    path: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """根据路径获取文件夹详情（路径优先接口）"""
    logger = logging.getLogger(__name__)
    logger.info(f"📂 get_folder_by_path called with path: '{path}'")
    
    # 确保路径以斜杠开头
    if not path.startswith('/'):
        path = '/' + path
    
    # 查询文件夹
    folder = db.query(Folder).filter(Folder.path == path).first()
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文件夹不存在 (路径: {path})"
        )
    
    # 验证权限（通过应用）
    app = db.query(App).filter(App.id == folder.app_id).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="关联的应用不存在"
        )
    
    # 特殊处理：public用户可以访问所有文件夹（用于Client门户）
    if current_user.username != "public":
        if not current_user.is_superuser and app.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此文件夹"
            )
    
    # 计算文档数量
    from sqlalchemy import func
    doc_count = db.query(func.count(Document.id)).filter(
        Document.folder_id == folder.id
    ).scalar() or 0
    
    # 设置document_count属性，以便response_model可以序列化
    folder.document_count = doc_count
    
    return folder


@router.put("/{folder_identifier}", response_model=FolderResponse)
def update_folder(
    folder_identifier: str,
    folder_data: FolderUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新文件夹（路径优先，兼容UUID）
    
    注意：建议使用路径标识符，UUID支持已弃用
    """
    logger = logging.getLogger(__name__)
    
    # 优先按路径查找（路径优先策略）
    folder = None
    
    # 检查是否是路径格式（以/开头）
    if folder_identifier.startswith('/'):
        # 直接按路径查找
        folder = db.query(Folder).filter(Folder.path == folder_identifier).first()
        if folder:
            logger.info(f"✅ 通过路径找到文件夹(更新): {folder_identifier}")
    else:
        # 可能是UUID或编码路径
        # 先尝试按路径查找（可能传入的是编码路径）
        try:
            import urllib.parse
            decoded_path = urllib.parse.unquote(folder_identifier)
            if decoded_path.startswith('/'):
                folder = db.query(Folder).filter(Folder.path == decoded_path).first()
                if folder:
                    logger.info(f"✅ 通过解码路径找到文件夹(更新): {decoded_path} (原始: {folder_identifier})")
        except:
            pass
    
    # 如果没找到，尝试按UUID查找（向后兼容）
    if not folder:
        # 检查是否是UUID格式
        import re
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
        if uuid_pattern.match(folder_identifier):
            folder = db.query(Folder).filter(Folder.id == folder_identifier).first()
            if folder:
                logger.warning(f"⚠️  通过UUID找到文件夹(更新): {folder_identifier} (路径: {folder.path})")
        else:
            # 既不是路径也不是UUID，尝试作为路径处理（添加/前缀）
            path = '/' + folder_identifier
            folder = db.query(Folder).filter(Folder.path == path).first()
            if folder:
                logger.info(f"✅ 通过添加/前缀找到文件夹(更新): {path} (原始: {folder_identifier})")
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文件夹不存在 (标识符: {folder_identifier})"
        )
    
    # 验证权限（通过应用）
    app = db.query(App).filter(App.id == folder.app_id).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="关联的应用不存在"
        )
    
    if not current_user.is_superuser and app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限更新此文件夹"
        )
    
    # 更新字段
    if folder_data.name is not None:
        # 检查名称是否冲突
        existing_folder = db.query(Folder).filter(
            Folder.name == folder_data.name,
            Folder.app_id == folder.app_id,
            Folder.parent_folder_id == folder.parent_folder_id,
            Folder.id != folder.id
        ).first()
        
        if existing_folder:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="此位置下已存在同名的文件夹"
            )
        folder.name = folder_data.name
    
    if folder_data.description is not None:
        folder.description = folder_data.description
    
    if folder_data.path is not None:
        folder.path = folder_data.path
    
    # 更新更新时间
    folder.updated_at = func.now()
    folder.updated_by = current_user.username
    
    db.commit()
    db.refresh(folder)
    
    return folder


def _delete_physical_files(folder: Folder, db: Session):
    """删除文件夹及其子文件夹中所有文档对应的物理文件"""
    data_root = Path(settings.DATA_ROOT)

    def _collect_doc_paths(folder_id: str) -> list:
        paths = []
        # 当前文件夹的文档
        docs = db.query(Document).filter(Document.folder_id == folder_id).all()
        for doc in docs:
            if doc.storage_path:
                paths.append(data_root / doc.storage_path)
            elif doc.full_storage_path and doc.stored_filename:
                paths.append(Path(doc.full_storage_path) / doc.stored_filename)
        # 子文件夹的文档
        subfolders = db.query(Folder).filter(Folder.parent_folder_id == folder_id).all()
        for subfolder in subfolders:
            paths.extend(_collect_doc_paths(subfolder.id))
        return paths

    file_paths = _collect_doc_paths(folder.id)
    for fp in file_paths:
        try:
            if fp.exists():
                fp.unlink()
                logger.info(f"🗑️ 删除物理文件: {fp}")
        except Exception as e:
            logger.warning(f"⚠️ 无法删除物理文件 {fp}: {e}")

    # 删除空的文件夹目录
    folder_dir = data_root / folder.path.lstrip('/') if folder.path else None
    if folder_dir and folder_dir.exists():
        try:
            # 递归删除空目录（shutil.rmtree删除所有内容）
            import shutil
            shutil.rmtree(folder_dir)
            logger.info(f"🗑️ 删除文件夹目录: {folder_dir}")
        except Exception as e:
            logger.warning(f"⚠️ 无法删除文件夹目录 {folder_dir}: {e}")


def _perform_folder_delete(folder: Folder, recursive: bool = False, db: Session = None):
    """执行文件夹删除的核心逻辑（递归删除子文件夹及文档，含物理文件清理）"""
    def _delete_recursive(folder_id: str):
        subfolders = db.query(Folder).filter(Folder.parent_folder_id == folder_id).all()
        for subfolder in subfolders:
            _delete_recursive(subfolder.id)
        from app.models.document import Document
        db.query(Document).filter(Document.folder_id == folder_id).delete()
        db.query(Folder).filter(Folder.id == folder_id).delete()

    if not recursive:
        subfolders_count = db.query(Folder).filter(Folder.parent_folder_id == folder.id).count()
        from app.models.document import Document
        documents_count = db.query(Document).filter(Document.folder_id == folder.id).count()
        if subfolders_count > 0 or documents_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"文件夹包含 {subfolders_count} 个子文件夹和 {documents_count} 个文档。请使用 recursive=true 参数进行递归删除。"
            )

    # 先清理物理文件（在删除DB记录前收集路径）
    if recursive:
        _delete_physical_files(folder, db)
    else:
        data_root = Path(settings.DATA_ROOT)
        docs = db.query(Document).filter(Document.folder_id == folder.id).all()
        for doc in docs:
            if doc.storage_path:
                fp = data_root / doc.storage_path
                if fp.exists():
                    try:
                        fp.unlink()
                    except:
                        pass

    try:
        if recursive:
            _delete_recursive(folder.id)
        else:
            db.delete(folder)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除文件夹时发生错误: {str(e)}"
        )


def _find_folder_by_identifier(db: Session, folder_identifier: str):
    """查找文件夹：路径优先，兼容UUID"""
    logger = logging.getLogger(__name__)
    folder = None

    if folder_identifier.startswith('/'):
        folder = db.query(Folder).filter(Folder.path == folder_identifier).first()
        if folder:
            logger.info(f"✅ 通过路径找到文件夹(删除): {folder_identifier}")
    else:
        try:
            import urllib.parse
            decoded_path = urllib.parse.unquote(folder_identifier)
            if decoded_path.startswith('/'):
                folder = db.query(Folder).filter(Folder.path == decoded_path).first()
                if folder:
                    logger.info(f"✅ 通过解码路径找到文件夹(删除): {decoded_path} (原始: {folder_identifier})")
        except:
            pass

    if not folder:
        import re
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
        if uuid_pattern.match(folder_identifier):
            folder = db.query(Folder).filter(Folder.id == folder_identifier).first()
            if folder:
                logger.warning(f"⚠️  通过UUID找到文件夹(删除): {folder_identifier} (路径: {folder.path})")
        else:
            path = '/' + folder_identifier
            folder = db.query(Folder).filter(Folder.path == path).first()
            if folder:
                logger.info(f"✅ 通过添加/前缀找到文件夹(删除): {path} (原始: {folder_identifier})")

    return folder


def _check_folder_permission(folder: Folder, current_user: User, db: Session):
    """验证用户有权限操作该文件夹"""
    app = db.query(App).filter(App.id == folder.app_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="关联的应用不存在")
    if not current_user.is_superuser and app.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="没有权限删除此文件夹")
    return app


@router.delete("/by-path/{path:path}")
def delete_folder_by_path(
    path: str,
    recursive: bool = Query(False, description="是否递归删除子文件夹和文档"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """根据路径删除文件夹（路径解析版）
    
    路径以 / 开头，例如：/boarding/canadasite/en/some-folder
    如果recursive=True，将递归删除所有子文件夹及其文档。
    如果recursive=False（默认），则只删除空文件夹。
    """
    if not path.startswith('/'):
        path = '/' + path

    folder = db.query(Folder).filter(Folder.path == path).first()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文件夹不存在 (路径: {path})"
        )

    _check_folder_permission(folder, current_user, db)
    _perform_folder_delete(folder, recursive, db)

    message = "文件夹及其所有子文件夹和文档已成功删除" if recursive else "文件夹删除成功"
    return {"message": message}


@router.delete("/{folder_identifier}")
def delete_folder(
    folder_identifier: str,
    recursive: bool = Query(False, description="是否递归删除子文件夹和文档"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除文件夹（路径优先，兼容UUID）
    
    如果recursive=True，将递归删除所有子文件夹及其文档。
    如果recursive=False（默认），则只删除空文件夹。
    注意：带/的路径请使用 /by-path/{path} 接口
    """
    folder = _find_folder_by_identifier(db, folder_identifier)
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文件夹不存在 (标识符: {folder_identifier})"
        )

    _check_folder_permission(folder, current_user, db)
    _perform_folder_delete(folder, recursive, db)

    message = "文件夹及其所有子文件夹和文档已成功删除" if recursive else "文件夹删除成功"
    return {"message": message}


@router.patch("/{folder_identifier}/move", response_model=FolderResponse)
def move_folder(
    folder_identifier: str,
    move_request: MoveFolderRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """移动文件夹到新的父文件夹（路径优先，兼容UUID）
    
    只能在同一应用内移动。
    注意：建议使用路径标识符，UUID支持已弃用
    """
    logger = logging.getLogger(__name__)
    
    # 优先按路径查找（路径优先策略）
    folder = None
    
    # 检查是否是路径格式（以/开头）
    if folder_identifier.startswith('/'):
        # 直接按路径查找
        folder = db.query(Folder).filter(Folder.path == folder_identifier).first()
        if folder:
            logger.info(f"✅ 通过路径找到文件夹(移动): {folder_identifier}")
    else:
        # 可能是UUID或编码路径
        # 先尝试按路径查找（可能传入的是编码路径）
        try:
            import urllib.parse
            decoded_path = urllib.parse.unquote(folder_identifier)
            if decoded_path.startswith('/'):
                folder = db.query(Folder).filter(Folder.path == decoded_path).first()
                if folder:
                    logger.info(f"✅ 通过解码路径找到文件夹(移动): {decoded_path} (原始: {folder_identifier})")
        except:
            pass
    
    # 如果没找到，尝试按UUID查找（向后兼容）
    if not folder:
        # 检查是否是UUID格式
        import re
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
        if uuid_pattern.match(folder_identifier):
            folder = db.query(Folder).filter(Folder.id == folder_identifier).first()
            if folder:
                logger.warning(f"⚠️  通过UUID找到文件夹(移动): {folder_identifier} (路径: {folder.path})")
        else:
            # 既不是路径也不是UUID，尝试作为路径处理（添加/前缀）
            path = '/' + folder_identifier
            folder = db.query(Folder).filter(Folder.path == path).first()
            if folder:
                logger.info(f"✅ 通过添加/前缀找到文件夹(移动): {path} (原始: {folder_identifier})")
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文件夹不存在 (标识符: {folder_identifier})"
        )
    
    # 验证权限（当前所在应用）
    current_app = db.query(App).filter(App.id == folder.app_id).first()
    if not current_app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="当前应用不存在"
        )
    
    if not current_user.is_superuser and current_app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限移动此文件夹"
        )
    
    # 检查移动参数
    target_parent_folder_id = move_request.target_parent_folder_id
    
    # 处理移动到应用根目录（target_parent_folder_id为空）
    if not target_parent_folder_id:
        # 移动到应用根目录
        folder.parent_folder_id = None
    
    # 处理同应用内移动（改变父文件夹）
    else:
        # 检查目标父文件夹是否存在
        target_parent_folder = db.query(Folder).filter(Folder.id == target_parent_folder_id).first()
        if not target_parent_folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="目标父文件夹不存在"
            )
        
        # 检查目标父文件夹是否在同一应用内
        if target_parent_folder.app_id != folder.app_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="目标父文件夹不在同一个应用内，文件夹只能在同一应用内移动"
            )
        
        # 防止循环引用（不能移动到自己或自己的子文件夹下）
        if target_parent_folder_id == folder_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能将文件夹移动到自身"
            )
        
        # 递归检查是否移动到子文件夹下
        def is_child_folder(parent_id, child_id):
            """检查parent_id是否是child_id的子文件夹（递归向上查找）"""
            if parent_id == child_id:
                return True
            current = db.query(Folder).filter(Folder.id == child_id).first()
            if not current or not current.parent_folder_id:
                return False
            if current.parent_folder_id == parent_id:
                return True
            return is_child_folder(parent_id, current.parent_folder_id)
        
        if is_child_folder(folder_id, target_parent_folder_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能将文件夹移动到自己的子文件夹下"
            )
        
        # 更新父文件夹ID
        folder.parent_folder_id = target_parent_folder_id
    
    # 计算移动文件夹的新parent_folder_path
    new_parent_folder_path = ""
    if not target_parent_folder_id:
        # 移动到应用根目录，parent_folder_path应该是/app_slug
        app_slug = current_app.slug if current_app.slug else to_slug(current_app.name)
        new_parent_folder_path = f"/{app_slug}" if app_slug else "-"
    else:
        # 移动到另一个文件夹下，parent_folder_path应该是目标父文件夹的完整路径
        target_parent_folder = db.query(Folder).filter(Folder.id == target_parent_folder_id).first()
        if target_parent_folder:
            new_parent_folder_path = target_parent_folder.path
        else:
            # 不应该发生，因为前面已经检查过
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="目标父文件夹不存在"
            )
    
    # 递归更新文件夹及其所有子文件夹和文档的路径
    # 注意：这里我们传入当前文件夹的parent_folder_path，update_folder_path_recursive会处理完整路径计算
    update_folder_path_recursive(folder_id, new_parent_folder_path, db)
    
    # 重新从数据库获取文件夹以获取更新后的数据
    db.commit()
    db.refresh(folder)
    
    return folder


@router.get("/app/{app_identifier}/tree", response_model=List[dict])
def get_folder_tree(
    app_identifier: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取应用的文件夹树形结构"""
    # 查找应用（支持UUID和slug）
    app = db.query(App).filter(
        (App.id == app_identifier) | (App.slug == app_identifier)
    ).first()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="应用不存在"
        )
    
    # 验证权限
    # 特殊处理：public用户可以访问所有应用的文件夹（用于Client门户）
    if current_user.username != "public":
        if not current_user.is_superuser and app.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此应用的文件夹"
            )
    
    # 获取应用下的所有文件夹
    all_folders = db.query(Folder).filter(Folder.app_id == app.id).all()
    
    # 构建文件夹树
    folder_map = {folder.id: {
        "id": folder.id,
        "name": folder.name,
        "description": folder.description,
        "path": folder.path,
        "parent_folder_id": folder.parent_folder_id,
        "children": []
    } for folder in all_folders}
    
    # 建立父子关系
    root_folders = []
    for folder_id, folder_data in folder_map.items():
        folder_obj = next(f for f in all_folders if f.id == folder_id)
        if folder_obj.parent_folder_id:
            if folder_obj.parent_folder_id in folder_map:
                folder_map[folder_obj.parent_folder_id]["children"].append(folder_data)
            else:
                # 父文件夹不在列表中，也作为根文件夹
                root_folders.append(folder_data)
        else:
            root_folders.append(folder_data)
    
    # 按名称排序
    def sort_folder_tree(folders):
        sorted_folders = sorted(folders, key=lambda x: x["name"])
        for folder in sorted_folders:
            if folder["children"]:
                folder["children"] = sort_folder_tree(folder["children"])
        return sorted_folders
    
    return sort_folder_tree(root_folders)


# 新端点：根据路径获取或创建文件夹
class FolderPathRequest(BaseModel):
    """文件夹路径请求模型"""
    path: str
    create_if_missing: bool = True


@router.post("/by-path", response_model=FolderResponse)
def get_or_create_folder_by_path(
    request: FolderPathRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    根据路径获取文件夹，如果不存在且create_if_missing为True则创建
    
    路径格式: /{app_slug}/{folder_slug}/{subfolder_slug}
    例如: /webbot/documents/images
    """
    path = request.path.strip()
    if not path.startswith('/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="路径必须以斜杠开头"
        )
    
    # 分割路径
    parts = [p for p in path.split('/') if p]
    if len(parts) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="路径必须包含应用slug和至少一个文件夹名称"
        )
    
    app_slug = parts[0]
    folder_parts = parts[1:]
    
    # 查找应用
    app = db.query(App).filter(App.slug == app_slug).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"应用不存在: {app_slug}"
        )
    
    # 验证权限
    if not current_user.is_superuser and app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限在此应用下创建文件夹"
        )
    
    # 递归查找或创建文件夹
    current_parent_id = None
    current_path = f"/{app_slug}"
    created_folders = []
    
    for i, folder_name in enumerate(folder_parts):
        current_path = f"{current_path}/{folder_name}"
        
        # 查找当前层级的文件夹
        folder = db.query(Folder).filter(
            Folder.app_id == app.id,
            Folder.path == current_path
        ).first()
        
        if folder:
            # 文件夹已存在，继续下一层
            current_parent_id = folder.id
            continue
        
        # 文件夹不存在
        if not request.create_if_missing:
            # 如果不允许创建，返回404
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文件夹不存在: {current_path}"
            )
        
        # 创建文件夹
        folder_slug = to_slug(folder_name)
        if folder_slug != folder_name:
            # 如果名称被转换，记录日志
            logger.info(f"文件夹名称'{folder_name}'被转换为slug格式: '{folder_slug}'")
        
        # 验证文件夹名称是否已存在（在同一父文件夹下）
        existing_folder = db.query(Folder).filter(
            Folder.name == folder_name,
            Folder.app_id == app.id,
            Folder.parent_folder_id == (current_parent_id if current_parent_id else None)
        ).first()
        
        if existing_folder:
            # 同名文件夹已存在，使用它
            logger.warning(f"同名文件夹已存在: {folder_name}, 路径: {existing_folder.path}")
            current_parent_id = existing_folder.id
            continue
        
        # 创建新文件夹
        db_folder = Folder(
            id=str(uuid.uuid4()),
            app_id=app.id,
            parent_folder_id=current_parent_id,
            name=folder_name,
            path=current_path,
            description=f"Auto-created folder: {current_path}",
            created_by=current_user.username
        )
        
        db.add(db_folder)
        db.flush()  # 获取ID但不提交
        db.refresh(db_folder)
        
        logger.info(f"创建文件夹: {folder_name}, 路径: {current_path}, ID: {db_folder.id}")
        created_folders.append(db_folder)
        current_parent_id = db_folder.id
    
    # 提交所有更改
    db.commit()
    
    # 返回最后一个文件夹（目标文件夹）
    if current_parent_id:
        target_folder = db.query(Folder).filter(Folder.id == current_parent_id).first()
        if target_folder:
            return target_folder
        else:
            # 这应该不会发生，但以防万一
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="文件夹创建后无法检索"
            )
    else:
        # 如果没有创建文件夹且路径只包含应用slug，返回应用的根文件夹？
        # 实际上这种情况不应该发生，因为路径必须包含至少一个文件夹
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的路径"
        )