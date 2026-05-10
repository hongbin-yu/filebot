from sqlalchemy import Column, DateTime, String, ForeignKey, Boolean, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..db.database import Base


class Folder(Base):
    """文件夹表 (Folder) - 使用路径作为主键，彻底移除UUID"""
    __tablename__ = "folders"

    path = Column(String(500), primary_key=True)  # 路径即主键，如 "/boarding/canadasite/fr/sondages"
    app_id = Column(String(36), ForeignKey("apps.id"), nullable=False)  # 仍关联应用
    parent_folder_path = Column(String(500), ForeignKey("folders.path"), nullable=True, index=True)  # 父路径
    name = Column(String(100), nullable=False, index=True)
    title = Column(String(200), nullable=True)
    description = Column(String(500), nullable=True)
    
    # 系统文件夹标志
    is_system_folder = Column(Boolean, default=False, index=True)
    order_index = Column(Integer, default=0)
    
    # 审计字段
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(100), nullable=True)

    # 关系（基于路径）
    app = relationship("App", back_populates="folders")
    parent = relationship("Folder", remote_side=[path], back_populates="subfolders")
    subfolders = relationship("Folder", back_populates="parent", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="folder", cascade="all, delete-orphan", foreign_keys="Document.folder_path")

    def __repr__(self):
        return f"<Folder(path={self.path}, name={self.name}, app_id={self.app_id})>"

    @property
    def app_slug(self) -> str:
        """从路径提取应用slug
        例如: path='/boarding/canadasite/fr' → slug='boarding'
        """
        if not self.path:
            return ''
        parts = self.path.strip('/').split('/')
        return parts[0] if parts else ''
