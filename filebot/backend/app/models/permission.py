from sqlalchemy import Column, DateTime, String, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from ..db.database import Base


class ResourceType(enum.Enum):
    """资源类型枚举"""
    APP = "app"
    DRAWER = "drawer"
    FOLDER = "folder"
    DOCUMENT = "document"


class PermissionLevel(enum.Enum):
    """权限级别枚举"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    OWNER = "owner"


class Permission(Base):
    """权限表"""
    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    resource_type = Column(Enum(ResourceType), nullable=False)
    resource_id = Column(UUID(as_uuid=True), nullable=False)  # 对应资源的ID
    permission_level = Column(Enum(PermissionLevel), nullable=False)
    
    # 有效期
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    user = relationship("User", back_populates="permissions")

    def __repr__(self):
        return f"<Permission(user={self.user_id}, resource={self.resource_type}:{self.resource_id}, level={self.permission_level})>"