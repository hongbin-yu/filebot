from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import uuid
import re
import unicodedata

from app.db.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.app import App
from app.models.folder import Folder
from app.schemas.app import AppCreate, AppResponse, AppUpdate, FolderResponse

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


def generate_unique_slug(base_slug: str, db: Session, exclude_app_id: Optional[str] = None) -> str:
    """
    Generate a unique slug by adding numeric suffix if needed
    """
    slug = base_slug
    counter = 1
    
    while True:
        query = db.query(App).filter(App.slug == slug)
        if exclude_app_id:
            query = query.filter(App.id != exclude_app_id)
        
        existing_app = query.first()
        if not existing_app:
            return slug
        
        # Slug exists, try with suffix
        slug = f"{base_slug}-{counter}"
        counter += 1


# ========== App (应用) 路由 ==========

@router.get("/", response_model=List[AppResponse])
def get_apps(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取用户的应用列表（只能看到自己的应用）"""
    # 特殊处理：public用户可以访问所有应用（用于Client门户）
    if current_user.is_superuser or current_user.username == "public":
        # 管理员或public用户可以看到所有应用
        apps = db.query(App).offset(skip).limit(limit).all()
    else:
        # 普通用户只能看到自己的应用
        apps = db.query(App).filter(App.owner_id == current_user.id).offset(skip).limit(limit).all()
    
    return apps


@router.post("/", response_model=AppResponse)
def create_app(
    app_data: AppCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建新应用"""
    # 生成或验证slug
    if not app_data.slug or app_data.slug.strip() == "":
        # 自动从name生成slug
        base_slug = to_slug(app_data.name)
        if not base_slug:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无法从应用名称生成有效的slug，请手动提供slug"
            )
        slug = generate_unique_slug(base_slug, db)
    else:
        slug = app_data.slug
        # 检查slug是否唯一
        existing_app = db.query(App).filter(App.slug == slug).first()
        if existing_app:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "该slug已被使用",
                    "conflict_type": "slug",
                    "existing_app": {
                        "id": existing_app.id,
                        "name": existing_app.name,
                        "slug": existing_app.slug,
                        "description": existing_app.description,
                        "created_at": existing_app.created_at.isoformat() if existing_app.created_at else None,
                        "created_by": existing_app.created_by,
                        "owner_id": existing_app.owner_id
                    }
                }
            )
    
    # 创建应用
    app = App(
        name=app_data.name,
        slug=slug,
        description=app_data.description,
        owner_id=current_user.id,
        settings=app_data.settings or {},
        redirect_url=app_data.redirect_url,
        icon=app_data.icon,
        created_by=app_data.created_by or current_user.username
    )
    
    db.add(app)
    db.commit()
    db.refresh(app)
    
    return app


@router.get("/{app_identifier}", response_model=AppResponse)
def get_app(
    app_identifier: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取单个应用（支持UUID或slug）"""
    # 先尝试按UUID查找
    app = db.query(App).filter(App.id == app_identifier).first()
    # 如果没找到，尝试按slug查找
    if not app:
        app = db.query(App).filter(App.slug == app_identifier).first()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="应用不存在"
        )
    
    # 权限检查
    # 特殊处理：public用户可以访问所有应用（用于Client门户）
    if current_user.username != "public":
        if not current_user.is_superuser and app.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此应用"
            )
    
    return app


@router.get("/by-slug/{slug}", response_model=AppResponse)
def get_app_by_slug(
    slug: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """根据slug获取单个应用（路径优先接口）"""
    app = db.query(App).filter(App.slug == slug).first()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"应用不存在 (slug: {slug})"
        )
    
    # 权限检查
    # 特殊处理：public用户可以访问所有应用（用于Client门户）
    if current_user.username != "public":
        if not current_user.is_superuser and app.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此应用"
            )
    
    return app


@router.put("/{app_identifier}", response_model=AppResponse)
def update_app(
    app_identifier: str,
    app_data: AppUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新应用（支持UUID或slug）"""
    # 先尝试按UUID查找
    app = db.query(App).filter(App.id == app_identifier).first()
    # 如果没找到，尝试按slug查找
    if not app:
        app = db.query(App).filter(App.slug == app_identifier).first()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="应用不存在"
        )
    
    # 权限检查
    if not current_user.is_superuser and app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限更新此应用"
        )
    
    # 更新字段
    if app_data.slug is not None and app_data.slug != app.slug:
        # 检查新slug是否唯一（排除当前应用）
        existing_app = db.query(App).filter(
            App.slug == app_data.slug,
            App.id != app.id
        ).first()
        if existing_app:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "该slug已被使用",
                    "conflict_type": "slug",
                    "existing_app": {
                        "id": existing_app.id,
                        "name": existing_app.name,
                        "slug": existing_app.slug,
                        "description": existing_app.description,
                        "created_at": existing_app.created_at.isoformat() if existing_app.created_at else None,
                        "created_by": existing_app.created_by,
                        "owner_id": existing_app.owner_id
                    }
                }
            )
        app.slug = app_data.slug
    
    if app_data.name is not None:
        app.name = app_data.name
    if app_data.description is not None:
        app.description = app_data.description
    if app_data.settings is not None:
        app.settings = app_data.settings
    if app_data.redirect_url is not None:
        app.redirect_url = app_data.redirect_url
    if app_data.icon is not None:
        app.icon = app_data.icon
    if app_data.updated_by is not None:
        app.updated_by = app_data.updated_by
    else:
        app.updated_by = current_user.username
    
    db.commit()
    db.refresh(app)
    
    return app


@router.delete("/{app_identifier}")
def delete_app(
    app_identifier: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除应用（同时删除关联的文件夹和文档，支持UUID或slug）"""
    # 先尝试按UUID查找
    app = db.query(App).filter(App.id == app_identifier).first()
    # 如果没找到，尝试按slug查找
    if not app:
        app = db.query(App).filter(App.slug == app_identifier).first()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="应用不存在"
        )
    
    # 权限检查
    if not current_user.is_superuser and app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限删除此应用"
        )
    
    # 删除应用（级联删除文件夹和文档）
    db.delete(app)
    db.commit()
    
    return {"message": "应用删除成功"}


# ========== 应用下的文件夹路由 ==========

@router.get("/{app_identifier}/folders", response_model=List[FolderResponse])
def get_app_folders(
    app_identifier: str,
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取应用下的所有文件夹（直接关联，无需抽屉）"""
    # 查找应用
    app = db.query(App).filter(App.id == app_identifier).first()
    if not app:
        app = db.query(App).filter(App.slug == app_identifier).first()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="应用不存在"
        )
    
    # 权限检查
    if not current_user.is_superuser and app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限访问此应用的文件夹"
        )
    
    # 获取文件夹
    folders = db.query(Folder).filter(
        Folder.app_id == app.id
    ).offset(skip).limit(limit).all()
    
    return folders