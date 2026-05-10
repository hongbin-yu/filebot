"""
Enhanced conversion routes - integrated actual conversion functionality
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
import uuid
import logging

from app.db.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.app import App
from app.models.folder import Folder
from app.models.document import Document, ConversionStatus as DocConversionStatus
from app.models.conversion_task import ConversionTask, TaskStatus
from app.schemas.conversion import (
    ConversionTaskCreate, ConversionTaskResponse, ConversionTaskUpdate,
    FileUploadRequest, FileUploadResponse, BatchConversionRequest, BatchConversionResponse
)
from app.services.conversion_worker import ConversionWorker, create_conversion_task_for_document
from app.services.conversion_service import get_conversion_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== Permission Check Helpers ==========

def check_document_access_for_conversion(
    document_path: str,
    current_user: User,
    db: Session
) -> Document:
    """Check user permission to access document for conversion operations"""
    from app.routers.documents import check_document_access
    return check_document_access(document_path, current_user, db)


# ========== ConversionTask Routes ==========

@router.get("/tasks", response_model=List[ConversionTaskResponse])
def get_conversion_tasks(
    document_path: Optional[str] = Query(None, description="Filter by document path"),
    status_filter: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get conversion task list"""
    # Build base query
    query = db.query(ConversionTask).options(
        joinedload(ConversionTask.document).joinedload(Document.folder)
        .joinedload(Folder.app)
    )
    
    # Apply permission filter
    if not current_user.is_superuser:
        user_apps_subquery = db.query(App.id).filter(App.owner_id == current_user.id).subquery()
        
        query = query.join(Document).join(Folder).join(App)
        query = query.filter(App.id.in_(user_apps_subquery))
    
    # Apply filters
    if document_path:
        query = query.filter(ConversionTask.document_path == document_path)
    
    if status_filter:
        query = query.filter(ConversionTask.status == status_filter)
    
    # Sort and paginate
    query = query.order_by(ConversionTask.created_at.desc())
    tasks = query.offset(skip).limit(limit).all()
    
    return tasks


@router.get("/tasks/{task_id}", response_model=ConversionTaskResponse)
def get_conversion_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get conversion task details"""
    task = db.query(ConversionTask).options(
        joinedload(ConversionTask.document).joinedload(Document.folder)
        .joinedload(Folder.app)
    ).filter(ConversionTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversion task not found"
        )
    
    # Check document permission
    check_document_access_for_conversion(task.document_path, current_user, db)
    
    return task


@router.post("/tasks", response_model=ConversionTaskResponse)
def create_conversion_task(
    task_data: ConversionTaskCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new conversion task and process it immediately"""
    # Check document permission
    document = check_document_access_for_conversion(task_data.document_path, current_user, db)
    
    # Check if there's already an active conversion task
    existing_task = db.query(ConversionTask).filter(
        ConversionTask.document_path == task_data.document_path,
        ConversionTask.status.in_([TaskStatus.QUEUED, TaskStatus.PROCESSING])
    ).first()
    
    if existing_task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document already has a conversion task with status '{existing_task.status.value}'"
        )
    
    # Create conversion task
    import uuid as uuid_module
    task = ConversionTask(
        id=str(uuid_module.uuid4()),
        document_path=task_data.document_path,
        source_format=task_data.source_format,
        target_format=task_data.target_format,
        status=TaskStatus.QUEUED,
        progress=task_data.progress or 0,
        current_step=task_data.current_step,
        error_message=task_data.error_message,
        error_traceback=task_data.error_traceback,
        worker_id=task_data.worker_id,
        retry_count=task_data.retry_count or 0
    )
    
    # Update document conversion status
    document.conversion_status = DocConversionStatus.PENDING
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Process task in background
    background_tasks.add_task(process_conversion_task_background, task.id, db)
    
    return task


@router.put("/tasks/{task_id}", response_model=ConversionTaskResponse)
def update_conversion_task(
    task_id: uuid.UUID,
    task_update: ConversionTaskUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update conversion task information"""
    task = db.query(ConversionTask).options(
        joinedload(ConversionTask.document)
    ).filter(ConversionTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversion task not found"
        )
    
    # Check document permission
    check_document_access_for_conversion(task.document_path, current_user, db)
    
    # Update fields
    update_data = task_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    
    # If task status changed, update associated document's conversion status
    if task_update.status:
        if task_update.status == TaskStatus.COMPLETED:
            task.document.conversion_status = DocConversionStatus.COMPLETED
        elif task_update.status == TaskStatus.FAILED:
            task.document.conversion_status = DocConversionStatus.FAILED
        elif task_update.status == TaskStatus.PROCESSING:
            task.document.conversion_status = DocConversionStatus.PROCESSING
    
    db.commit()
    db.refresh(task)
    
    return task


@router.delete("/tasks/{task_id}")
def delete_conversion_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a conversion task"""
    task = db.query(ConversionTask).options(
        joinedload(ConversionTask.document)
    ).filter(ConversionTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversion task not found"
        )
    
    # Check document permission
    check_document_access_for_conversion(task.document_path, current_user, db)
    
    # Only allow deleting non-active tasks
    if task.status in [TaskStatus.QUEUED, TaskStatus.PROCESSING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete task with status '{task.status.value}'"
        )
    
    db.delete(task)
    db.commit()
    
    return {"message": "Conversion task deleted successfully"}


# ========== Conversion Queue Management ==========

@router.get("/queue")
def get_conversion_queue(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get conversion queue (queued and processing tasks)"""
    query = db.query(ConversionTask).options(
        joinedload(ConversionTask.document).joinedload(Document.folder)
        .joinedload(Folder.app)
    ).filter(
        ConversionTask.status.in_([TaskStatus.QUEUED, TaskStatus.PROCESSING])
    )
    
    # Apply permission filter
    if not current_user.is_superuser:
        user_apps_subquery = db.query(App.id).filter(App.owner_id == current_user.id).subquery()
        
        query = query.join(Document).join(Folder).join(App)
        query = query.filter(App.id.in_(user_apps_subquery))
    
    # Sort: processing first, then queued, by creation time ascending
    from sqlalchemy import case
    status_order = case(
        (ConversionTask.status == TaskStatus.PROCESSING, 1),
        (ConversionTask.status == TaskStatus.QUEUED, 2),
        else_=3
    )
    
    query = query.order_by(status_order, ConversionTask.created_at.asc())
    tasks = query.offset(skip).limit(limit).all()
    
    # Stats
    queued_count = db.query(ConversionTask).filter(
        ConversionTask.status == TaskStatus.QUEUED
    ).count()
    
    processing_count = db.query(ConversionTask).filter(
        ConversionTask.status == TaskStatus.PROCESSING
    ).count()
    
    return {
        "tasks": tasks,
        "queue_stats": {
            "queued": queued_count,
            "processing": processing_count,
            "total": queued_count + processing_count
        }
    }


@router.post("/queue/retry-failed")
def retry_failed_conversions(
    task_ids: Optional[List[uuid.UUID]] = None,
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retry failed conversion tasks"""
    query = db.query(ConversionTask).options(
        joinedload(ConversionTask.document).joinedload(Document.folder)
        .joinedload(Folder.app)
    ).filter(ConversionTask.status == TaskStatus.FAILED)
    
    # Apply permission filter
    if not current_user.is_superuser:
        user_apps_subquery = db.query(App.id).filter(App.owner_id == current_user.id).subquery()
        
        query = query.join(Document).join(Folder).join(App)
        query = query.filter(App.id.in_(user_apps_subquery))
    
    # If specific task IDs provided, only retry those
    if task_ids:
        query = query.filter(ConversionTask.id.in_(task_ids))
    
    failed_tasks = query.all()
    
    retried_count = 0
    retried_task_ids = []
    
    for task in failed_tasks:
        # Reset task status
        task.status = TaskStatus.QUEUED
        task.progress = 0
        task.current_step = None
        task.error_message = None
        task.error_traceback = None
        task.retry_count += 1
        
        # Update document status
        task.document.conversion_status = DocConversionStatus.PENDING
        
        retried_count += 1
        retried_task_ids.append(task.id)
        
        # If background_tasks provided, retry immediately
        if background_tasks:
            background_tasks.add_task(process_conversion_task_background, task.id, db)
    
    if retried_count > 0:
        db.commit()
    
    return {
        "message": f"Retried {retried_count} failed tasks",
        "retried_count": retried_count,
        "task_ids": [str(task_id) for task_id in retried_task_ids]
    }


# ========== Batch Conversion Operations ==========

@router.post("/batch", response_model=BatchConversionResponse)
def batch_convert_documents(
    batch_request: BatchConversionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Batch convert documents"""
    queued_documents = []
    failed_documents = []
    task_ids = []
    
    for doc_path in batch_request.document_paths:
        try:
            # Check document permission
            document = check_document_access_for_conversion(doc_path, current_user, db)
            
            # Create conversion task
            task = create_conversion_task_for_document(db, doc_path, batch_request.target_format)
            if task:
                queued_documents.append(doc_path)
                task_ids.append(task.id)
                
                # Process in background
                background_tasks.add_task(process_conversion_task_background, task.id, db)
            else:
                failed_documents.append(doc_path)
                
        except HTTPException:
            # Document not found or no permission
            failed_documents.append(doc_path)
        except Exception as e:
            logger.error(f"Failed to create conversion task for document {doc_path}: {e}")
            failed_documents.append(doc_path)
    
    return BatchConversionResponse(
        task_count=len(queued_documents),
        queued_documents=queued_documents,
        failed_documents=failed_documents
    )


# ========== Conversion Service Status ==========

@router.get("/status")
def get_conversion_service_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get conversion service status stats"""
    # Total task count
    total_tasks = db.query(ConversionTask).count()
    
    # Status breakdown
    status_stats = {}
    for status in TaskStatus:
        count = db.query(ConversionTask).filter(ConversionTask.status == status).count()
        status_stats[status.value] = count
    
    # User-specific stats
    user_stats = {}
    if not current_user.is_superuser:
        user_apps = db.query(App.id).filter(App.owner_id == current_user.id).subquery()
        user_tasks_count = db.query(ConversionTask).join(Document).join(Folder)\
            .join(App).filter(App.id.in_(user_apps)).count()
        user_stats["total_tasks"] = user_tasks_count
    
    # Get supported formats
    conversion_service = get_conversion_service()
    supported_formats = conversion_service.get_supported_formats()
    
    return {
        "service_status": "active",
        "total_tasks": total_tasks,
        "status_stats": status_stats,
        "user_stats": user_stats,
        "supported_formats": supported_formats,
    }


# ========== Helper Functions ==========

def process_conversion_task_background(task_id: str, db: Session):
    """Process conversion task in background"""
    logger = logging.getLogger(__name__)
    
    try:
        # Create new db session for background task
        from app.db.database import SessionLocal
        db = SessionLocal()
        
        # Process the task
        converter = ConversionWorker(db)
        logger.info(f"Processing conversion task: {task_id}")
        converter.process_task(task_id)
        
        logger.info(f"Conversion task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Background conversion task {task_id} failed: {str(e)}")
    finally:
        db.close()
