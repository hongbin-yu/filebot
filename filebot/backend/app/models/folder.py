from sqlalchemy import Column, DateTime, String, ForeignKey, Boolean, Integer
# from sqlalchemy.dialects.postgresql import UUID  # 注释掉，使用String代替
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from ..db.database import Base


class Folder(Base):
    """文件夹表 (Folder) - 直接关联应用，移除抽屉层"""
    __tablename__ = "folders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    app_id = Column(String(36), ForeignKey("apps.id"), nullable=False)  # 直接关联应用
    parent_folder_id = Column(String(36), ForeignKey("folders.id"), nullable=True)  # 支持嵌套
    name = Column(String(100), nullable=False, index=True)
    path = Column(String(500), nullable=False, index=True)  # 虚拟路径，如 "/app/folder"
    description = Column(String(500), nullable=True)
    
    # 系统文件夹标志
    is_system_folder = Column(Boolean, default=False, index=True)  # 是否为系统文件夹
    order_index = Column(Integer, default=0)  # 排序索引
    
    # 审计字段（兼容旧系统）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100), nullable=True)  # 创建者用户名
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(100), nullable=True)  # 更新者用户名

    # 关系
    app = relationship("App", back_populates="folders")
    parent = relationship("Folder", remote_side=[id], back_populates="subfolders")
    subfolders = relationship("Folder", back_populates="parent", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="folder", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Folder(id={self.id}, name={self.name}, app_id={self.app_id}, path={self.path})>"