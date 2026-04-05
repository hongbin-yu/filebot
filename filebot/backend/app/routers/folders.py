from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, select
from typing import List, Optional
import uuid
import logging
import re
import unicodedata
from pydantic import BaseModel

from app.db.database import get_db
from app.models.folder import Folder
from app.models.document import Document
from app.models.app import App
from app.models.user import User
from app.schemas.app import FolderCreate, FolderUpdate, FolderResponse
from app.core.security import get_current_active_user

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


@router.get("/", response_model=List[FolderResponse])
def get_folders(
    app_id: Optional[str] = Query(None, description="应用ID或slug"),
    parent_folder_id: Optional[str] = Query(None, description="父文件夹ID（留空表示根文件夹）"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取文件夹列表（可按应用和父文件夹过滤）"""
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
    
    # 使用子查询获取每个文件夹的文档数量
    from sqlalchemy import func
    
    # 创建文档计数的子查询
    doc_count_subquery = db.query(
        Document.folder_id,
        func.count(Document.id).label('document_count')
    ).group_by(Document.folder_id).subquery()
    
    # 修改查询以左连接文档计数
    folders_with_counts = query.outerjoin(
        doc_count_subquery,
        Folder.id == doc_count_subquery.c.folder_id
    ).with_entities(
        Folder,
        func.coalesce(doc_count_subquery.c.document_count, 0).label('document_count')
    ).order_by(Folder.name).all()
    
    # 将文档计数添加到文件夹对象中
    folders = []
    for folder_obj, doc_count in folders_with_counts:
        # 将文件夹对象转换为字典，添加document_count字段
        folder_dict = {c.name: getattr(folder_obj, c.name) for c in folder_obj.__table__.columns}
        folder_dict['document_count'] = doc_count
        folders.append(folder_dict)
    
    return folders


@router.post("/", response_model=FolderResponse)
def create_folder(
    folder_data: FolderCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建文件夹"""
    logger.info(f"创建文件夹请求: {folder_data.dict()}, 用户: {current_user.username}")
    
    # 验证应用存在
    app = db.query(App).filter(App.id == str(folder_data.app_id)).first()
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
    
    # 检查文件夹名称是否已存在（在同一应用和父文件夹下）
    existing_folder = db.query(Folder).filter(
        Folder.name == folder_data.name,
        Folder.app_id == str(folder_data.app_id),
        Folder.parent_folder_id == str(folder_data.parent_folder_id) if folder_data.parent_folder_id else None
    ).first()
    
    if existing_folder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此位置下已存在同名的文件夹"
        )
    
    # 获取父文件夹路径（如果存在）
    parent_path = ""
    if folder_data.parent_folder_id:
        parent_folder = db.query(Folder).filter(Folder.id == str(folder_data.parent_folder_id)).first()
        if parent_folder:
            parent_path = parent_folder.path
            # 验证父文件夹属于同一个应用
            if parent_folder.app_id != str(folder_data.app_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="父文件夹不属于同一个应用"
                )
    
    # 生成文件夹路径
    app_slug = app.slug if app.slug else to_slug(app.name)
    folder_path = generate_folder_path(
        folder_name=folder_data.name,
        app_slug=app_slug,
        parent_path=parent_path
    )
    
    # 创建文件夹记录
    db_folder = Folder(
        id=str(uuid.uuid4()),
        app_id=str(folder_data.app_id),  # 确保是字符串
        parent_folder_id=str(folder_data.parent_folder_id) if folder_data.parent_folder_id else None,
        name=folder_data.name,
        path=folder_path,  # 使用生成的路径
        description=folder_data.description,
        created_by=current_user.username
    )
    
    db.add(db_folder)
    db.commit()
    db.refresh(db_folder)
    
    return db_folder


@router.get("/{folder_id}", response_model=FolderResponse)
def get_folder(
    folder_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取文件夹详情"""
    # 查询文件夹并计算文档数量
    from sqlalchemy import func
    
    # 创建文档计数的子查询
    doc_count_subquery = db.query(
        Document.folder_id,
        func.count(Document.id).label('document_count')
    ).filter(Document.folder_id == folder_id).group_by(Document.folder_id).subquery()
    
    # 查询文件夹及其文档计数
    folder_with_count = db.query(
        Folder,
        func.coalesce(doc_count_subquery.c.document_count, 0).label('document_count')
    ).outerjoin(
        doc_count_subquery,
        Folder.id == doc_count_subquery.c.folder_id
    ).filter(Folder.id == folder_id).first()
    
    if not folder_with_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件夹不存在"
        )
    
    folder_obj, doc_count = folder_with_count
    
    # 验证权限（通过应用）
    app = db.query(App).filter(App.id == folder_obj.app_id).first()
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
    
    # 将文档计数添加到文件夹对象中
    folder_dict = {c.name: getattr(folder_obj, c.name) for c in folder_obj.__table__.columns}
    folder_dict['document_count'] = doc_count
    
    return folder_dict


@router.put("/{folder_id}", response_model=FolderResponse)
def update_folder(
    folder_id: str,
    folder_data: FolderUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新文件夹"""
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件夹不存在"
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
            Folder.id != folder_id
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


@router.delete("/{folder_id}")
def delete_folder(
    folder_id: str,
    recursive: bool = Query(False, description="是否递归删除子文件夹和文档"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除文件夹
    
    如果recursive=True，将递归删除所有子文件夹及其文档。
    如果recursive=False（默认），则只删除空文件夹。
    """
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件夹不存在"
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
            detail="没有权限删除此文件夹"
        )
    
    # 检查文件夹是否为空（如果不递归删除）
    if not recursive:
        subfolders_count = db.query(Folder).filter(Folder.parent_folder_id == folder_id).count()
        
        from app.models.document import Document
        documents_count = db.query(Document).filter(Document.folder_id == folder_id).count()
        
        if subfolders_count > 0 or documents_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"文件夹包含 {subfolders_count} 个子文件夹和 {documents_count} 个文档。请使用 recursive=true 参数进行递归删除。"
            )
    
    # 递归删除所有子文件夹和文档
    def delete_folder_recursive(folder_id: str):
        # 获取所有子文件夹
        subfolders = db.query(Folder).filter(Folder.parent_folder_id == folder_id).all()
        
        # 递归删除子文件夹
        for subfolder in subfolders:
            delete_folder_recursive(subfolder.id)
        
        # 删除当前文件夹的所有文档
        from app.models.document import Document
        db.query(Document).filter(Document.folder_id == folder_id).delete()
        
        # 删除当前文件夹
        db.query(Folder).filter(Folder.id == folder_id).delete()
    
    # 开始事务
    try:
        if recursive:
            delete_folder_recursive(folder_id)
        else:
            db.delete(folder)
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除文件夹时发生错误: {str(e)}"
        )
    
    message = "文件夹删除成功"
    if recursive:
        message = "文件夹及其所有子文件夹和文档已成功删除"
    
    return {"message": message}


@router.patch("/{folder_id}/move", response_model=FolderResponse)
def move_folder(
    folder_id: str,
    move_request: MoveFolderRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """移动文件夹到新的父文件夹（只能在同一应用内移动）"""
    # 获取要移动的文件夹
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件夹不存在"
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
    
    # 更新路径
    # 需要重新生成路径，使用应用slug和新的父文件夹结构
    def get_folder_path(folder_obj):
        """获取文件夹的完整路径（递归构建）"""
        if not folder_obj.parent_folder_id:
            # 根文件夹，路径格式: /app_slug/folder_slug
            app_slug = current_app.slug if current_app.slug else to_slug(current_app.name)
            folder_slug = to_slug(folder_obj.name)
            return f"/{app_slug}/{folder_slug}"
        else:
            # 有父文件夹，递归获取父路径
            parent_folder = db.query(Folder).filter(Folder.id == folder_obj.parent_folder_id).first()
            if not parent_folder:
                # 不应该发生，但处理异常情况
                return f"/unknown/{to_slug(folder_obj.name)}"
            parent_path = get_folder_path(parent_folder)
            return f"{parent_path.rstrip('/')}/{to_slug(folder_obj.name)}"
    
    # 更新文件夹路径
    folder.path = get_folder_path(folder)
    
    # 更新更新时间
    folder.updated_at = func.now()
    folder.updated_by = current_user.username
    
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