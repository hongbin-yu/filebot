"""
网站爬取任务模型
"""

from sqlalchemy import Column, DateTime, String, Integer, JSON, Enum, Text
from sqlalchemy.sql import func
import uuid
import enum

from ..db.database import Base


class CrawlTaskStatus(enum.Enum):
    """爬取任务状态枚举"""
    PENDING = "pending"
    CRAWLING = "crawling"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CrawlTask(Base):
    """网站爬取任务表"""
    __tablename__ = "crawl_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(100), unique=True, nullable=False, index=True)  # 前端使用的任务ID
    status = Column(Enum(CrawlTaskStatus), default=CrawlTaskStatus.PENDING)
    
    # 爬取参数
    url = Column(String(2000), nullable=False)
    depth = Column(Integer, default=1)
    folder_path = Column(String(500), nullable=False)  # 目标文件夹路径
    include_images = Column(Integer, default=0)  # 0=否, 1=是
    follow_external_links = Column(Integer, default=0)
    respect_robots_txt = Column(Integer, default=1)
    
    # 进度信息
    pages_crawled = Column(Integer, default=0)
    pages_processed = Column(Integer, default=0)
    images_crawled = Column(Integer, default=0)
    total_pages = Column(Integer, default=0)  # 总页面数（预估或实际）
    
    # 统计信息
    stats = Column(JSON, default={})  # 完整的统计信息
    errors = Column(JSON, default=[])  # 错误列表
    
    # 进度百分比
    progress = Column(Integer, default=0)  # 0-100
    
    # 当前状态描述
    current_status = Column(String(500), nullable=True)  # 当前状态消息
    current_url = Column(String(2000), nullable=True)  # 当前正在爬取的URL
    
    # 时间信息
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # 错误处理
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    
    # 系统信息
    created_by = Column(String(100), nullable=True)  # 创建者（用户名）
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<CrawlTask(id={self.id}, task_id={self.task_id}, status={self.status}, progress={self.progress}%)>"

    def to_status_dict(self):
        """转换为状态字典（用于API响应）"""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "url": self.url,
            "depth": self.depth,
            "pages_crawled": self.pages_crawled,
            "pages_processed": self.pages_processed,
            "images_crawled": self.images_crawled,
            "total_pages": self.total_pages,
            "progress": self.progress,
            "current_status": self.current_status,
            "errors": self.errors or [],
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "stats": self.stats or {}
        }