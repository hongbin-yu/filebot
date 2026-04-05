from sqlalchemy import Column, DateTime, String, ForeignKey, Enum, Integer
# from sqlalchemy.dialects.postgresql import UUID  # 注释掉，使用String代替
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from ..db.database import Base


class TaskStatus(enum.Enum):
    """任务状态枚举"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConversionTask(Base):
    """转换任务表"""
    __tablename__ = "conversion_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.QUEUED)
    source_format = Column(String(20), nullable=False)
    target_format = Column(String(20), nullable=False)
    
    # 进度信息
    progress = Column(Integer, default=0)  # 0-100
    current_step = Column(String(100), nullable=True)  # 当前步骤描述
    
    # 时间信息
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # 错误处理
    error_message = Column(String(2000), nullable=True)
    error_traceback = Column(String, nullable=True)  # 详细的错误堆栈
    
    # 系统信息
    worker_id = Column(String(100), nullable=True)  # 处理任务的worker ID
    retry_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    document = relationship("Document", back_populates="conversion_tasks")

    def __repr__(self):
        return f"<ConversionTask(id={self.id}, status={self.status}, progress={self.progress}%)>"