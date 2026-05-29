from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import uuid
import re
import unicodedata

from app.db.database import get_db
from app.core.security import get_current_active_user, has_app_access
from app.models.user import User
from app.models.app import App
from app.models.folder import Folder
from app.models.permission import Permission
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


# ========== App Routes ==========

@router.get("/", response_model=List[AppResponse])
def get_apps(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's app list
    - superuser/public: see all apps
    - others: see own apps + apps they have permission on
    """
    if current_user.is_superuser or current_user.username == "public":
        apps = db.query(App).offset(skip).limit(limit).all()
    else:
        # Get apps owned by user
        owned_apps = db.query(App).filter(App.owner_id == current_user.id)
        # Get apps where user has direct permission
        permitted_app_ids = [
            row[0] for row in db.query(Permission.resource_id)
            .filter(
                Permission.resource_type == "app",
                Permission.user_id == current_user.id,
            )
            .all()
        ]
        # Get apps where user's groups have permission
        from app.models.group import GroupMember
        user_group_ids = [
            row[0] for row in db.query(GroupMember.group_id)
            .filter(GroupMember.user_id == current_user.id)
            .all()
        ]
        if user_group_ids:
            group_permitted_ids = [
                row[0] for row in db.query(Permission.resource_id)
                .filter(
                    Permission.resource_type == "app",
                    Permission.group_id.in_(user_group_ids),
                )
                .all()
            ]
            permitted_app_ids = list(set(permitted_app_ids + group_permitted_ids))

        all_app_ids = [row[0] for row in owned_apps.with_entities(App.id).all()] + permitted_app_ids
        all_app_ids = list(set(all_app_ids))

        if all_app_ids:
            apps = db.query(App).filter(App.id.in_(all_app_ids)).offset(skip).limit(limit).all()
        else:
            apps = []

    return apps


@router.get("/client", response_model=List[AppResponse])
def get_client_apps(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Client-facing endpoint: always filter by user permissions.
    Unlike GET /apps, this does NOT return all apps for superusers/public.
    Only returns apps the user has explicit permission to access.
    """
    # Apps owned by user
    owned_apps = db.query(App).filter(App.owner_id == current_user.id)
    owned_ids = [row[0] for row in owned_apps.with_entities(App.id).all()]
    
    # Apps where user has direct permission
    permitted_ids = [
        row[0] for row in db.query(Permission.resource_id)
        .filter(
            Permission.resource_type == "app",
            Permission.user_id == current_user.id,
        )
        .all()
    ]
    
    # Apps where user's groups have permission
    from app.models.group import GroupMember
    user_group_ids = [
        row[0] for row in db.query(GroupMember.group_id)
        .filter(GroupMember.user_id == current_user.id)
        .all()
    ]
    if user_group_ids:
        group_permitted_ids = [
            row[0] for row in db.query(Permission.resource_id)
            .filter(
                Permission.resource_type == "app",
                Permission.group_id.in_(user_group_ids),
            )
            .all()
        ]
        permitted_ids = list(set(permitted_ids + group_permitted_ids))
    
    all_ids = list(set(owned_ids + permitted_ids))
    
    if not all_ids:
        return []
    
    apps = db.query(App).filter(App.id.in_(all_ids)).offset(skip).limit(limit).all()
    return apps


@router.post("/", response_model=AppResponse)
def create_app(
    app_data: AppCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new app"""
    # Generate or validate slug
    if not app_data.slug or app_data.slug.strip() == "":
        # Auto-generate slug from name
        base_slug = to_slug(app_data.name)
        if not base_slug:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to generate a valid slug from app name, please provide slug manually"
            )
        slug = generate_unique_slug(base_slug, db)
    else:
        slug = app_data.slug
        # Check slug uniqueness
        existing_app = db.query(App).filter(App.slug == slug).first()
        if existing_app:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "This slug is already in use",
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
    
    # Create app
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
    """Get a single app (supports UUID or slug)"""
    # Try UUID first
    app = db.query(App).filter(App.id == app_identifier).first()
    # If not found, try slug
    if not app:
        app = db.query(App).filter(App.slug == app_identifier).first()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )
    
    # Permission check (public user bypasses)
    if current_user.username != "public":
        if not current_user.is_superuser and app.owner_id != current_user.id:
            if not has_app_access(current_user, app.id, "read", db):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No permission to access this app"
                )

    return app


@router.get("/by-slug/{slug}", response_model=AppResponse)
def get_app_by_slug(
    slug: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a single app by slug (path-priority interface)"""
    app = db.query(App).filter(App.slug == slug).first()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"App not found (slug: {slug})"
        )
    
    # Permission check
    if current_user.username != "public":
        if not current_user.is_superuser and app.owner_id != current_user.id:
            if not has_app_access(current_user, app.id, "read", db):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No permission to access this app"
                )

    return app


@router.put("/{app_identifier}", response_model=AppResponse)
def update_app(
    app_identifier: str,
    app_data: AppUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an app (supports UUID or slug)"""
    # Try UUID first
    app = db.query(App).filter(App.id == app_identifier).first()
    # If not found, try slug
    if not app:
        app = db.query(App).filter(App.slug == app_identifier).first()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )
    
    # Permission check
    if not current_user.is_superuser and app.owner_id != current_user.id:
        if not has_app_access(current_user, app.id, "write", db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to update this app"
            )

    # Update fields
    if app_data.slug is not None and app_data.slug != app.slug:
        # Check new slug uniqueness (excluding current app)
        existing_app = db.query(App).filter(
            App.slug == app_data.slug,
            App.id != app.id
        ).first()
        if existing_app:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "This slug is already in use",
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
    """Delete an app (also deletes associated folders and documents, supports UUID or slug)"""
    # Try UUID first
    app = db.query(App).filter(App.id == app_identifier).first()
    # If not found, try slug
    if not app:
        app = db.query(App).filter(App.slug == app_identifier).first()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )
    
    # Permission check
    if not current_user.is_superuser and app.owner_id != current_user.id:
        if not has_app_access(current_user, app.id, "admin", db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to delete this app"
            )

    # Delete app (cascade deletes folders and documents)
    db.delete(app)
    db.commit()
    
    return {"message": "App deleted successfully"}


# ========== App Folders Routes ==========

@router.get("/{app_identifier}/folders", response_model=List[FolderResponse])
def get_app_folders(
    app_identifier: str,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all folders under an app (direct association, no drawer)"""
    # Find app
    app = db.query(App).filter(App.id == app_identifier).first()
    if not app:
        app = db.query(App).filter(App.slug == app_identifier).first()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )
    
    # Permission check
    if not current_user.is_superuser and app.owner_id != current_user.id:
        if not has_app_access(current_user, app.id, "read", db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to access this app's folders"
            )

    # Get folders
    folders = db.query(Folder).filter(
        Folder.app_id == app.id
    ).offset(skip).limit(limit).all()

    return folders



