from sqlalchemy import Column, DateTime, String, JSON, ForeignKey
# from sqlalchemy.dialects.postgresql import UUID  # 注释掉，使用String代替
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from ..db.database import Base


class App(Base):
    """应用表 (App) - 直接关联文件夹，移除抽屉层"""
    __tablename__ = "apps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, index=True)
    slug = Column(String(120), nullable=True, unique=True, index=True)  # URL友好标识符
    description = Column(String(500), nullable=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    settings = Column(JSON, default=dict)  # 应用配置
    
    # 新增字段用于统一仪表板
    redirect_url = Column(String(500), nullable=True)  # 重定向URL，用于集成WebBot等外部应用
    icon = Column(String(200), nullable=True)  # 图标URL或图标名称
    
    # 审计字段（兼容旧系统）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100), nullable=True)  # 创建者用户名
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(100), nullable=True)  # 更新者用户名

    # 关系
    owner = relationship("User", back_populates="apps")
    folders = relationship("Folder", back_populates="app", cascade="all, delete-orphan")
    file_naming_rules = relationship("FileNamingRule", back_populates="app", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<App(id={self.id}, name={self.name}, slug={self.slug}, owner_id={self.owner_id})>"