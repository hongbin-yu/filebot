"""
转换工作器

处理实际的文档转换任务，与数据库交互更新任务状态。
"""
import logging
import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.document import Document, ConversionStatus as DocConversionStatus
from app.models.conversion_task import ConversionTask, TaskStatus
from .conversion_service import get_conversion_service, ConversionError

logger = logging.getLogger(__name__)


class ConversionWorker:
    """转换工作器"""
    
    def __init__(self, db: Session):
        self.db = db
        self.conversion_service = get_conversion_service()
    
    def process_task(self, task_id: uuid.UUID) -> bool:
        """处理单个转换任务"""
        # 获取任务
        task = self.db.query(ConversionTask).options(
            joinedload(ConversionTask.document)
        ).filter(ConversionTask.id == task_id).first()
        
        if not task:
            logger.error(f"任务不存在: {task_id}")
            return False
        
        if task.status != TaskStatus.QUEUED:
            logger.warning(f"任务状态不是QUEUED: {task_id} ({task.status})")
            return False
        
        # 获取关联的文档
        document = task.document
        if not document:
            logger.error(f"文档不存在: {task.document_id}")
            self._mark_task_failed(task, "关联的文档不存在")
            return False
        
        # 检查文档文件是否存在
        # TODO: 需要实现文件存储路径逻辑
        source_path = self._get_document_path(document)
        if not source_path or not source_path.exists():
            logger.error(f"文档文件不存在: {document.stored_filename}")
            self._mark_task_failed(task, "文档文件不存在")
            return False
        
        try:
            # 更新任务状态为处理中
            task.status = TaskStatus.PROCESSING
            task.started_at = datetime.utcnow()
            task.current_step = "开始转换"
            task.progress = 10
            
            # 更新文档状态
            document.conversion_status = DocConversionStatus.PROCESSING
            
            self.db.commit()
            
            # 确定目标路径
            target_filename = f"{document.id}.pdf"
            target_path = Path(settings.FILE_STORAGE_PATH) / "converted" / target_filename
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 执行转换
            logger.info(f"开始转换任务 {task_id}: {source_path} -> {target_path}")
            task.current_step = "执行转换"
            task.progress = 30
            self.db.commit()
            
            # 调用转换服务
            success, message, metadata = self.conversion_service.convert_file(
                source_path, target_path,
                source_format=task.source_format,
                target_format=task.target_format
            )
            
            if success:
                # 转换成功
                task.status = TaskStatus.COMPLETED
                task.progress = 100
                task.current_step = "转换完成"
                task.completed_at = datetime.utcnow()
                
                # 更新文档状态
                document.conversion_status = DocConversionStatus.COMPLETED
                document.converted_pdf_path = str(target_path)
                
                # 记录元数据
                if metadata:
                    # 可以存储到document.document_metadata中
                    if "page_count" in metadata:
                        document.page_count = metadata.get("page_count")
                
                logger.info(f"转换任务完成: {task_id}")
                self.db.commit()
                return True
            else:
                # 转换失败
                self._mark_task_failed(task, message)
                logger.error(f"转换失败: {task_id} - {message}")
                return False
                
        except ConversionError as e:
            self._mark_task_failed(task, str(e))
            logger.error(f"转换错误: {task_id} - {e}")
            return False
        except Exception as e:
            self._mark_task_failed(task, f"未知错误: {str(e)}")
            logger.exception(f"处理任务时发生未知错误: {task_id}")
            return False
    
    def _mark_task_failed(self, task: ConversionTask, error_message: str) -> None:
        """标记任务为失败"""
        task.status = TaskStatus.FAILED
        task.error_message = error_message[:2000]  # 限制长度
        task.progress = 0
        task.current_step = "转换失败"
        task.completed_at = datetime.utcnow()
        
        # 更新文档状态
        if task.document:
            task.document.conversion_status = DocConversionStatus.FAILED
            task.document.conversion_error = error_message[:1000]
        
        self.db.commit()
    
    def _get_document_path(self, document: Document) -> Optional[Path]:
        """获取文档的存储路径"""
        if document.stored_filename:
            # 原始文件存储在 FILE_STORAGE_PATH/original/ 目录下
            original_dir = Path(settings.FILE_STORAGE_PATH) / "original"
            return original_dir / document.stored_filename
        return None
    
    def retry_failed_task(self, task_id: uuid.UUID) -> bool:
        """重试失败的任务"""
        task = self.db.query(ConversionTask).filter(
            ConversionTask.id == task_id,
            ConversionTask.status == TaskStatus.FAILED
        ).first()
        
        if not task:
            logger.error(f"失败的任务不存在或状态不正确: {task_id}")
            return False
        
        # 重置任务状态
        task.status = TaskStatus.QUEUED
        task.progress = 0
        task.current_step = None
        task.error_message = None
        task.error_traceback = None
        task.retry_count += 1
        
        # 重置文档状态
        if task.document:
            task.document.conversion_status = DocConversionStatus.PENDING
            task.document.conversion_error = None
        
        self.db.commit()
        logger.info(f"已重置失败任务: {task_id}，重试次数: {task.retry_count}")
        return True


# 后台任务处理函数（用于Celery或BackgroundTasks）
def process_conversion_task_async(task_id: uuid.UUID, db_session_factory):
    """异步处理转换任务（用于Celery）"""
    from app.db.database import SessionLocal
    
    db = SessionLocal()
    try:
        worker = ConversionWorker(db)
        success = worker.process_task(task_id)
        return success
    finally:
        db.close()


def create_conversion_task_for_document(
    db: Session,
    document_id: uuid.UUID,
    target_format: str = "pdf"
) -> Optional[ConversionTask]:
    """为文档创建转换任务"""
    # 获取文档
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        logger.error(f"文档不存在: {document_id}")
        return None
    
    # 检查是否已有活跃的转换任务
    existing_task = db.query(ConversionTask).filter(
        ConversionTask.document_id == document_id,
        ConversionTask.status.in_([TaskStatus.QUEUED, TaskStatus.PROCESSING])
    ).first()
    
    if existing_task:
        logger.warning(f"文档已有活跃的转换任务: {document_id} ({existing_task.status})")
        return existing_task
    
    # 创建转换任务 - 确保ID为字符串
    task = ConversionTask(
        id=str(uuid.uuid4()),
        document_id=document_id,
        source_format=document.file_type.value,
        target_format=target_format,
        status=TaskStatus.QUEUED,
        progress=0
    )
    
    # 更新文档状态
    document.conversion_status = DocConversionStatus.PENDING
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    logger.info(f"创建转换任务: {task.id} 为文档 {document_id}")
    return task