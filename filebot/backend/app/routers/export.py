"""
Export API routes
Provides JSON format data export functionality
"""
import json
import logging
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
    app_id: str,
    include_folders: bool = Query(True, description="Whether to include folders"),
    include_documents: bool = Query(False, description="Whether to include documents"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Export a single app's data
    """
    logger = logging.getLogger(__name__)
    logger.info("Exporting app: %s", app_id)
    # Get app
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    # Check user permission
    if current_user.role not in ["admin", "superuser"] and app.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="No permission to access this app")

    # Build export data
    export_data = {
        "id": app.id,
        "name": app.name,
        "slug": app.slug,
        "description": app.description,
        "created_at": app.created_at.isoformat() if app.created_at else None,
        "updated_at": app.updated_at.isoformat() if app.updated_at else None,
        "created_by": app.created_by if app.created_by else None,
        "settings": app.settings if hasattr(app, 'settings') else {},
        "folders": []
    }

    # Include folders if requested
    if include_folders:
        folders_query = db.query(Folder).filter(Folder.app_id == app_id)

        # Include documents if requested
        if include_documents:
            folders_query = folders_query.options(joinedload(Folder.documents))

        folders = folders_query.all()

        for folder in folders:
            folder_data = {
                "name": folder.name,
                "path": folder.path,
                "description": folder.description,
                "app_id": app_id,
                "app_name": app.name,
                "parent_folder_path": folder.parent_folder_path if folder.parent_folder_path else None,
                "created_at": folder.created_at.isoformat() if folder.created_at else None,
                "updated_at": folder.updated_at.isoformat() if folder.updated_at else None,
                "created_by": folder.created_by if folder.created_by else None,
                "document_count": len(folder.documents) if hasattr(folder, 'documents') else 0,
                "documents": []
            }

            # Include documents if requested
            if include_documents and hasattr(folder, 'documents'):
                for document in folder.documents:
                    doc_data = {
                        "path": document.path,
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
                        "created_by": document.created_by if document.created_by else None,
                        "document_metadata": json.loads(document.document_metadata) if isinstance(document.document_metadata, str) else (document.document_metadata or {})
                    }
                    folder_data["documents"].append(doc_data)

            export_data["folders"].append(folder_data)

    return export_data


@router.get("/folder/{folder_path:path}", response_model=FolderExport)
def export_folder(
    folder_path: str,
    include_documents: bool = Query(True, description="Whether to include documents"),
    recursive: bool = Query(False, description="Whether to recursively include subfolders"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Export a single folder's data by path
    """
    # Get folder
    folder = db.query(Folder).filter(Folder.path == folder_path).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Get app to check permission
    app = db.query(App).filter(App.id == folder.app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Associated app not found")

    # Check user permission
    if current_user.role not in ["admin", "superuser"] and app.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="No permission to access this folder")

    # Build export data
    export_data = {
        "name": folder.name,
        "path": folder.path,
        "description": folder.description,
        "app_id": folder.app_id,
        "app_name": app.name,
        "parent_folder_path": folder.parent_folder_path if folder.parent_folder_path else None,
        "created_at": folder.created_at.isoformat() if folder.created_at else None,
        "updated_at": folder.updated_at.isoformat() if folder.updated_at else None,
        "created_by": folder.created_by if folder.created_by else None,
        "document_count": db.query(Document).filter(Document.folder_path == folder.path).count(),
        "documents": [],
        "subfolders": []
    }

    # Include documents if requested
    if include_documents:
        documents = db.query(Document).filter(Document.folder_path == folder.path).all()
        for document in documents:
            doc_data = {
                "path": document.path,
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
                "created_by": document.created_by if document.created_by else None,
                "document_metadata": json.loads(document.document_metadata) if isinstance(document.document_metadata, str) else (document.document_metadata or {})
            }
            export_data["documents"].append(doc_data)

    # Recursively include subfolders if requested
    if recursive:
        subfolders = db.query(Folder).filter(Folder.parent_folder_path == folder.path).all()
        for subfolder in subfolders:
            # Recursively export subfolder
            subfolder_data = export_folder(
                subfolder.path,
                include_documents=include_documents,
                recursive=True,
                db=db,
                current_user=current_user
            )
            export_data["subfolders"].append(subfolder_data)

    return export_data


@router.get("/full", response_model=FullExport)
def export_full(
    app_slug: Optional[str] = Query(None, description="Filter by app slug"),
    format: str = Query("json", description="Export format, supports json"),
    download: bool = Query(False, description="Whether to download as file"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Export full data (with filtering support)
    """
    # Only admins can export full data
    if current_user.role not in ["admin", "superuser"]:
        raise HTTPException(status_code=403, detail="Admin permission required")

    # Query apps
    apps_query = db.query(App)
    if app_slug:
        apps_query = apps_query.filter(App.slug == app_slug)

    apps = apps_query.all()

    # Build export data
    export_data = {
        "export_time": datetime.utcnow().isoformat(),
        "exported_by": {
            "id": current_user.id,
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
        # Get app's folders
        folders = db.query(Folder).filter(Folder.app_id == app.id).all()

        app_data = {
            "id": app.id,
            "name": app.name,
            "slug": app.slug,
            "description": app.description,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "updated_at": app.updated_at.isoformat() if app.updated_at else None,
            "created_by": app.created_by if app.created_by else None,
            "settings": app.settings if hasattr(app, 'settings') else {},
            "folders": []
        }

        folder_count = 0
        document_count = 0

        for folder in folders:
            # Get folder's documents
            documents = db.query(Document).filter(Document.folder_path == folder.path).all()

            folder_data = {
                "name": folder.name,
                "path": folder.path,
                "description": folder.description,
                "app_id": app.id,
                "app_name": app.name,
                "parent_folder_path": folder.parent_folder_path if folder.parent_folder_path else None,
                "created_at": folder.created_at.isoformat() if folder.created_at else None,
                "updated_at": folder.updated_at.isoformat() if folder.updated_at else None,
                "created_by": folder.created_by if folder.created_by else None,
                "document_count": len(documents),
                "documents": []
            }

            for document in documents:
                doc_data = {
                    "path": document.path,
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
                    "created_by": document.created_by if document.created_by else None,
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

    # Return based on format parameter
    if format.lower() == "json":
        if download:
            # Return as file download
            filename = f"filebot_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            content = json.dumps(export_data, ensure_ascii=False, indent=2)
            return Response(
                content=content,
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            # Return JSON directly
            return JSONResponse(content=export_data)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")


@router.post("/custom")
def export_custom(
    options: ExportOptions,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Custom export
    """
    # Only admins can do custom exports
    if current_user.role not in ["admin", "superuser"]:
        raise HTTPException(status_code=403, detail="Admin permission required")

    # TODO: Implement custom export logic based on options
    # Return placeholder response for now
    return {
        "message": "Custom export feature in development",
        "options": options.dict(),
        "export_time": datetime.utcnow().isoformat()
    }
