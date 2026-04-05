"""
增强版转换路由 - 集成实际转换功能
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


# ========== 权限检查辅助函数 ==========

def check_document_access_for_conversion(
    document_id: uuid.UUID,
    current_user: User,
    db: Session
) -> Document:
    """检查用户是否有权限访问文档（用于转换操作）"""
    from app.routers.documents import check_document_access
    return check_document_access(document_id, current_user, db)


# ========== ConversionTask (转换任务) 路由 ==========

@router.get("/tasks", response_model=List[ConversionTaskResponse])
def get_conversion_tasks(
    document_id: Optional[uuid.UUID] = Query(None, description="按文档ID筛选"),
    status_filter: Optional[TaskStatus] = Query(None, description="按任务状态筛选"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取转换任务列表"""
    # 构建基础查询
    query = db.query(ConversionTask).options(
        joinedload(ConversionTask.document).joinedload(Document.folder)
        .joinedload(Folder.app)
    )
    
    # 应用权限筛选
    if not current_user.is_superuser:
        user_apps_subquery = db.query(App.id).filter(App.owner_id == current_user.id).subquery()
        
        query = query.join(Document).join(Folder).join(App)
        query = query.filter(App.id.in_(user_apps_subquery))
    
    # 应用筛选条件
    if document_id:
        query = query.filter(ConversionTask.document_id == document_id)
    
    if status_filter:
        query = query.filter(ConversionTask.status == status_filter)
    
    # 排序和分页
    query = query.order_by(ConversionTask.created_at.desc())
    tasks = query.offset(skip).limit(limit).all()
    
    return tasks


@router.get("/tasks/{task_id}", response_model=ConversionTaskResponse)
def get_conversion_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取转换任务详情"""
    task = db.query(ConversionTask).options(
        joinedload(ConversionTask.document).joinedload(Document.folder)
        .joinedload(Folder.app)
    ).filter(ConversionTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="转换任务不存在"
        )
    
    # 检查文档权限
    check_document_access_for_conversion(task.document_id, current_user, db)
    
    return task


@router.post("/tasks", response_model=ConversionTaskResponse)
def create_conversion_task(
    task_data: ConversionTaskCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建新的转换任务并立即处理"""
    # 检查文档权限
    document = check_document_access_for_conversion(task_data.document_id, current_user, db)
    
    # 检查是否已有活跃的转换任务
    existing_task = db.query(ConversionTask).filter(
        ConversionTask.document_id == task_data.document_id,
        ConversionTask.status.in_([TaskStatus.QUEUED, TaskStatus.PROCESSING])
    ).first()
    
    if existing_task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文档已有一个{existing_task.status.value}状态的转换任务"
        )
    
    # 创建转换任务 - 确保ID为字符串
    import uuid as uuid_module
    task = ConversionTask(
        id=str(uuid_module.uuid4()),
        document_id=task_data.document_id,
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
    
    # 更新文档的转换状态
    document.conversion_status = DocConversionStatus.PENDING
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # 立即在后台处理任务
    background_tasks.add_task(process_conversion_task_background, task.id, db)
    
    return task


@router.put("/tasks/{task_id}", response_model=ConversionTaskResponse)
def update_conversion_task(
    task_id: uuid.UUID,
    task_update: ConversionTaskUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新转换任务信息"""
    task = db.query(ConversionTask).options(
        joinedload(ConversionTask.document)
    ).filter(ConversionTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="转换任务不存在"
        )
    
    # 检查文档权限
    check_document_access_for_conversion(task.document_id, current_user, db)
    
    # 更新字段
    update_data = task_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    
    # 如果任务状态变化，更新关联文档的转换状态
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
    """删除转换任务"""
    task = db.query(ConversionTask).options(
        joinedload(ConversionTask.document)
    ).filter(ConversionTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="转换任务不存在"
        )
    
    # 检查文档权限
    check_document_access_for_conversion(task.document_id, current_user, db)
    
    # 只能删除非活跃状态的任务
    if task.status in [TaskStatus.QUEUED, TaskStatus.PROCESSING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无法删除{task.status.value}状态的任务"
        )
    
    db.delete(task)
    db.commit()
    
    return {"message": "转换任务删除成功"}


# ========== 转换队列管理 ==========

@router.get("/queue")
def get_conversion_queue(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取转换队列（待处理和进行中的任务）"""
    query = db.query(ConversionTask).options(
        joinedload(ConversionTask.document).joinedload(Document.folder)
        .joinedload(Folder.app)
    ).filter(
        ConversionTask.status.in_([TaskStatus.QUEUED, TaskStatus.PROCESSING])
    )
    
    # 应用权限筛选
    if not current_user.is_superuser:
        user_apps_subquery = db.query(App.id).filter(App.owner_id == current_user.id).subquery()
        
        query = query.join(Document).join(Folder).join(App)
        query = query.filter(App.id.in_(user_apps_subquery))
    
    # 排序：先按状态（进行中优先），再按创建时间
    from sqlalchemy import case
    status_order = case(
        (ConversionTask.status == TaskStatus.PROCESSING, 1),
        (ConversionTask.status == TaskStatus.QUEUED, 2),
        else_=3
    )
    
    query = query.order_by(status_order, ConversionTask.created_at.asc())
    tasks = query.offset(skip).limit(limit).all()
    
    # 统计信息
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
    """重试失败的转换任务"""
    query = db.query(ConversionTask).options(
        joinedload(ConversionTask.document).joinedload(Document.folder)
        .joinedload(Folder.app)
    ).filter(ConversionTask.status == TaskStatus.FAILED)
    
    # 应用权限筛选
    if not current_user.is_superuser:
        user_apps_subquery = db.query(App.id).filter(App.owner_id == current_user.id).subquery()
        
        query = query.join(Document).join(Folder).join(App)
        query = query.filter(App.id.in_(user_apps_subquery))
    
    # 如果指定了任务ID，只重试这些任务
    if task_ids:
        query = query.filter(ConversionTask.id.in_(task_ids))
    
    failed_tasks = query.all()
    
    retried_count = 0
    retried_task_ids = []
    
    for task in failed_tasks:
        # 重置任务状态
        task.status = TaskStatus.QUEUED
        task.progress = 0
        task.current_step = None
        task.error_message = None
        task.error_traceback = None
        task.retry_count += 1
        
        # 更新文档状态
        task.document.conversion_status = DocConversionStatus.PENDING
        
        retried_count += 1
        retried_task_ids.append(task.id)
        
        # 如果提供了background_tasks，立即重试
        if background_tasks:
            background_tasks.add_task(process_conversion_task_background, task.id, db)
    
    if retried_count > 0:
        db.commit()
    
    return {
        "message": f"已重试 {retried_count} 个失败任务",
        "retried_count": retried_count,
        "task_ids": [str(task_id) for task_id in retried_task_ids]
    }


# ========== 批量转换操作 ==========

@router.post("/batch", response_model=BatchConversionResponse)
def batch_convert_documents(
    batch_request: BatchConversionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """批量转换文档"""
    queued_documents = []
    failed_documents = []
    task_ids = []
    
    for doc_id in batch_request.document_ids:
        try:
            # 检查文档权限
            document = check_document_access_for_conversion(doc_id, current_user, db)
            
            # 创建转换任务
            task = create_conversion_task_for_document(db, doc_id, batch_request.target_format)
            if task:
                queued_documents.append(doc_id)
                task_ids.append(task.id)
                
                # 立即在后台处理任务
                background_tasks.add_task(process_conversion_task_background, task.id, db)
            else:
                failed_documents.append(doc_id)
                
        except HTTPException:
            # 文档不存在或没有权限
            failed_documents.append(doc_id)
        except Exception as e:
            logger.error(f"为文档 {doc_id} 创建转换任务失败: {e}")
            failed_documents.append(doc_id)
    
    return BatchConversionResponse(
        task_count=len(queued_documents),
        queued_documents=queued_documents,
        failed_documents=failed_documents
    )


# ========== 转换服务状态 ==========

@router.get("/status")
def get_conversion_service_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取转换服务状态统计"""
    # 总任务统计
    total_tasks = db.query(ConversionTask).count()
    
    # 按状态统计
    status_stats = {}
    for status in TaskStatus:
        count = db.query(ConversionTask).filter(ConversionTask.status == status).count()
        status_stats[status.value] = count
    
    # 用户特定的统计
    user_stats = {}
    if not current_user.is_superuser:
        user_apps = db.query(App.id).filter(App.owner_id == current_user.id).subquery()
        user_tasks_count = db.query(ConversionTask).join(Document).join(Folder)\
            .join(App).filter(App.id.in_(user_apps)).count()
        user_stats["total_tasks"] = user_tasks_count
    
    # 获取转换服务支持的格式
    conversion_service = get_conversion_service()
    supported_formats = conversion_service.get_supported_formats()
    
    return {
        "service_status": "active",
        "total_tasks": total_tasks,
        "status_stats": status_stats,
        "user_stats": user_stats,
        "supported_formats": supported_formats,
        "capabilities": {
            "async_processing": True,
            "background_tasks": True,
            "real_time_progress": True
        }
    }


# ========== 直接转换测试接口 ==========

@router.post("/test-convert")
async def test_conversion(
    file: UploadFile = File(...),
    target_format: str = Query("pdf", description="目标格式"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """测试文件转换（直接上传并转换）"""
    from pathlib import Path
    import tempfile
    import shutil
    
    # 验证文件类型
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ['.txt', '.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {file_extension}"
        )
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        source_path = Path(tmp_file.name)
    
    try:
        # 创建目标文件
        target_filename = f"converted_{Path(file.filename).stem}.pdf"
        target_path = Path(tempfile.gettempdir()) / target_filename
        
        # 执行转换
        conversion_service = get_conversion_service()
        source_format = file_extension.lstrip('.')
        
        success, message, metadata = conversion_service.convert_file(
            source_path, target_path,
            source_format=source_format,
            target_format=target_format
        )
        
        if success:
            # 返回转换后的文件
            from fastapi.responses import FileResponse
            return FileResponse(
                path=target_path,
                filename=target_filename,
                media_type='application/pdf'
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"转换失败: {message}"
            )
            
    finally:
        # 清理临时文件
        if source_path.exists():
            source_path.unlink()


# ========== 辅助函数 ==========

def process_conversion_task_background(task_id: uuid.UUID, db_session):
    """后台处理转换任务"""
    try:
        worker = ConversionWorker(db_session)
        success = worker.process_task(task_id)
        logger.info(f"后台处理转换任务 {task_id}: {'成功' if success else '失败'}")
    except Exception as e:
        logger.error(f"后台处理转换任务 {task_id} 时出错: {e}")