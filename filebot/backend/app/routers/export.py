"""
导出API路由
提供JSON格式的数据导出功能
"""
import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, JSONResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.db.database import get_db
from app.core.security import get_current_active_user
from app.models.app import App
from app.models.folder import Folder
from app.models.document import Document
from app.models.user import User
from app.schemas.export import (
    ExportOptions,
    AppExport,
    FolderExport,
    DocumentExport,
    FullExport
)

router = APIRouter()


@router.get("/app/{app_id}", response_model=AppExport)
def export_app(
    app_id: uuid.UUID,
    include_folders: bool = Query(True, description="是否包含文件夹"),
    include_documents: bool = Query(False, description="是否包含文档"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    导出单个应用的数据
    """
    logger = logging.getLogger(__name__)
    logger.info("导出应用: %s", app_id)
    # 获取应用
    app = db.query(App).filter(App.id == str(app_id)).first()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    
    # 检查用户权限
    if current_user.role not in ["admin", "superuser"] and app.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此应用")
    
    # 构建导出数据
    export_data = {
        "id": str(app.id),
        "name": app.name,
        "slug": app.slug,
        "description": app.description,
        "created_at": app.created_at.isoformat() if app.created_at else None,
        "updated_at": app.updated_at.isoformat() if app.updated_at else None,
        "created_by": str(app.created_by) if app.created_by else None,
        "settings": app.settings if hasattr(app, 'settings') else {},
        "folders": []
    }
    
    # 如果需要包含文件夹
    if include_folders:
        folders_query = db.query(Folder).filter(Folder.app_id == str(app_id))
        
        # 如果需要包含文档
        if include_documents:
            folders_query = folders_query.options(joinedload(Folder.documents))
        
        folders = folders_query.all()
        
        for folder in folders:
            folder_data = {
                "id": str(folder.id),
                "name": folder.name,
                "path": folder.path,
                "description": folder.description,
                "app_id": str(app_id),
                "app_name": app.name,
                "parent_folder_id": str(folder.parent_folder_id) if folder.parent_folder_id else None,
                "created_at": folder.created_at.isoformat() if folder.created_at else None,
                "updated_at": folder.updated_at.isoformat() if folder.updated_at else None,
                "created_by": str(folder.created_by) if folder.created_by else None,
                "document_count": len(folder.documents) if hasattr(folder, 'documents') else 0,
                "documents": []
            }
            
            # 如果需要包含文档
            if include_documents and hasattr(folder, 'documents'):
                for document in folder.documents:
                    doc_data = {
                        "id": str(document.id),
                        "title": document.title,
                        "description": document.description,
                        "document_number": document.document_number,
                        "status": document.status.value if hasattr(document.status, 'value') else document.status,
                        "type": document.type.value if hasattr(document.type, 'value') else document.type,
                        "comments": document.comments,
                        "original_filename": document.original_filename,
                        "stored_filename": document.stored_filename,
                        "file_size": document.file_size,
                        "file_type": document.file_type.value if hasattr(document.file_type, 'value') else document.file_type,
                        "mime_type": document.mime_type,
                        "conversion_status": document.conversion_status.value if hasattr(document.conversion_status, 'value') else document.conversion_status,
                        "created_at": document.created_at.isoformat() if hasattr(document.created_at, 'isoformat') else document.created_at,
                        "updated_at": document.updated_at.isoformat() if hasattr(document.updated_at, 'isoformat') else document.updated_at,
                        "created_by": str(document.created_by) if document.created_by else None,
                        "document_metadata": json.loads(document.document_metadata) if isinstance(document.document_metadata, str) else (document.document_metadata or {})
                    }
                    folder_data["documents"].append(doc_data)
            
            export_data["folders"].append(folder_data)
    
    return export_data


@router.get("/folder/{folder_id}", response_model=FolderExport)
def export_folder(
    folder_id: uuid.UUID,
    include_documents: bool = Query(True, description="是否包含文档"),
    recursive: bool = Query(False, description="是否递归包含子文件夹"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    导出单个文件夹的数据
    """
    # 获取文件夹
    folder = db.query(Folder).filter(Folder.id == str(folder_id)).first()
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    
    # 获取应用以检查权限
    app = db.query(App).filter(App.id == folder.app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="关联应用不存在")
    
    # 检查用户权限
    if current_user.role not in ["admin", "superuser"] and app.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此文件夹")
    
    # 构建导出数据
    export_data = {
        "id": str(folder.id),
        "name": folder.name,
        "path": folder.path,
        "description": folder.description,
        "app_id": str(folder.app_id),
        "app_name": app.name,
        "parent_folder_id": str(folder.parent_folder_id) if folder.parent_folder_id else None,
        "created_at": folder.created_at.isoformat() if folder.created_at else None,
        "updated_at": folder.updated_at.isoformat() if folder.updated_at else None,
        "created_by": str(folder.created_by) if folder.created_by else None,
        "document_count": db.query(Document).filter(Document.folder_id == str(folder_id)).count(),
        "documents": [],
        "subfolders": []
    }
    
    # 如果需要包含文档
    if include_documents:
        documents = db.query(Document).filter(Document.folder_id == str(folder_id)).all()
        for document in documents:
            doc_data = {
                "id": str(document.id),
                "title": document.title,
                "description": document.description,
                "document_number": document.document_number,
                "status": document.status.value if hasattr(document.status, 'value') else document.status,
                "type": document.type.value if hasattr(document.type, 'value') else document.type,
                "comments": document.comments,
                "original_filename": document.original_filename,
                "stored_filename": document.stored_filename,
                "file_size": document.file_size,
                "file_type": document.file_type.value if hasattr(document.file_type, 'value') else document.file_type,
                "mime_type": document.mime_type,
                "conversion_status": document.conversion_status.value if hasattr(document.conversion_status, 'value') else document.conversion_status,
                "created_at": document.created_at.isoformat() if hasattr(document.created_at, 'isoformat') else document.created_at,
                "updated_at": document.updated_at.isoformat() if hasattr(document.updated_at, 'isoformat') else document.updated_at,
                "created_by": str(document.created_by) if document.created_by else None,
                "document_metadata": json.loads(document.document_metadata) if isinstance(document.document_metadata, str) else (document.document_metadata or {})
            }
            export_data["documents"].append(doc_data)
    
    # 如果需要递归包含子文件夹
    if recursive:
        subfolders = db.query(Folder).filter(Folder.parent_folder_id == str(folder_id)).all()
        for subfolder in subfolders:
            # 递归导出子文件夹
            subfolder_data = export_folder(
                uuid.UUID(subfolder.id),
                include_documents=include_documents,
                recursive=True,
                db=db,
                current_user=current_user
            )
            export_data["subfolders"].append(subfolder_data)
    
    return export_data


@router.get("/full", response_model=FullExport)
def export_full(
    app_slug: Optional[str] = Query(None, description="按应用slug过滤"),
    format: str = Query("json", description="导出格式，支持json"),
    download: bool = Query(False, description="是否作为文件下载"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    导出完整数据（支持过滤）
    """
    # 只有管理员可以导出完整数据
    if current_user.role not in ["admin", "superuser"]:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    # 查询应用
    apps_query = db.query(App)
    if app_slug:
        apps_query = apps_query.filter(App.slug == app_slug)
    
    apps = apps_query.all()
    
    # 构建导出数据
    export_data = {
        "export_time": datetime.utcnow().isoformat(),
        "exported_by": {
            "id": str(current_user.id),
            "username": current_user.username,
            "email": current_user.email,
            "role": current_user.role
        },
        "apps": [],
        "total_apps": 0,
        "total_folders": 0,
        "total_documents": 0
    }
    
    for app in apps:
        # 获取应用的文件夹
        folders = db.query(Folder).filter(Folder.app_id == str(app.id)).all()
        
        app_data = {
            "id": str(app.id),
            "name": app.name,
            "slug": app.slug,
            "description": app.description,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "updated_at": app.updated_at.isoformat() if app.updated_at else None,
            "created_by": str(app.created_by) if app.created_by else None,
            "settings": app.settings if hasattr(app, 'settings') else {},
            "folders": []
        }
        
        folder_count = 0
        document_count = 0
        
        for folder in folders:
            # 获取文件夹的文档
            documents = db.query(Document).filter(Document.folder_id == str(folder.id)).all()
            
            folder_data = {
                "id": str(folder.id),
                "name": folder.name,
                "path": folder.path,
                "description": folder.description,
                "app_id": str(app.id),
                "app_name": app.name,
                "parent_folder_id": str(folder.parent_folder_id) if folder.parent_folder_id else None,
                "created_at": folder.created_at.isoformat() if folder.created_at else None,
                "updated_at": folder.updated_at.isoformat() if folder.updated_at else None,
                "created_by": str(folder.created_by) if folder.created_by else None,
                "document_count": len(documents),
                "documents": []
            }
            
            for document in documents:
                doc_data = {
                    "id": str(document.id),
                    "title": document.title,
                    "description": document.description,
                    "document_number": document.document_number,
                    "status": document.status.value if hasattr(document.status, 'value') else document.status,
                    "type": document.type.value if hasattr(document.type, 'value') else document.type,
                    "comments": document.comments,
                    "original_filename": document.original_filename,
                    "stored_filename": document.stored_filename,
                    "file_size": document.file_size,
                    "file_type": document.file_type.value if hasattr(document.file_type, 'value') else document.file_type,
                    "mime_type": document.mime_type,
                    "conversion_status": document.conversion_status.value if hasattr(document.conversion_status, 'value') else document.conversion_status,
                    "created_at": document.created_at.isoformat() if hasattr(document.created_at, 'isoformat') else document.created_at,
                    "updated_at": document.updated_at.isoformat() if hasattr(document.updated_at, 'isoformat') else document.updated_at,
                    "created_by": str(document.created_by) if document.created_by else None,
                    "document_metadata": json.loads(document.document_metadata) if isinstance(document.document_metadata, str) else (document.document_metadata or {})
                }
                folder_data["documents"].append(doc_data)
                document_count += 1
            
            app_data["folders"].append(folder_data)
            folder_count += 1
        
        export_data["apps"].append(app_data)
        export_data["total_apps"] += 1
        export_data["total_folders"] += folder_count
        export_data["total_documents"] += document_count
    
    # 根据format参数返回相应格式
    if format.lower() == "json":
        if download:
            # 作为文件下载
            filename = f"filebot_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            content = json.dumps(export_data, ensure_ascii=False, indent=2)
            return Response(
                content=content,
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            # 直接返回JSON
            return JSONResponse(content=export_data)
    else:
        raise HTTPException(status_code=400, detail=f"不支持的格式: {format}")


@router.post("/custom")
def export_custom(
    options: ExportOptions,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    自定义导出
    """
    # 只有管理员可以自定义导出
    if current_user.role not in ["admin", "superuser"]:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    # TODO: 根据options参数实现自定义导出逻辑
    # 目前先返回一个占位符响应
    return {
        "message": "自定义导出功能开发中",
        "options": options.dict(),
        "export_time": datetime.utcnow().isoformat()
    }