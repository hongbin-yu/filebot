from sqlalchemy import Column, DateTime, String, ForeignKey, Enum as SAEnum
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
    """权限表 - 支持用户或组权限"""
    __tablename__ = "permissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    group_id = Column(String(36), ForeignKey("groups.id"), nullable=True, index=True)
    resource_type = Column(SAEnum(ResourceType, values_callable=lambda x: [m.value for m in x]), nullable=False, index=True)
    resource_id = Column(String(36), nullable=False, index=True)
    permission_level = Column(SAEnum(PermissionLevel, values_callable=lambda x: [m.value for m in x]), nullable=False, default=PermissionLevel.READ)

    # 有效期
    expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    user = relationship("User", back_populates="permissions")
    group = relationship("Group", backref="permissions")

    def __repr__(self):
        return f"<Permission(id={self.id}, user_id={self.user_id}, group_id={self.group_id}, resource={self.resource_type}:{self.resource_id}, level={self.permission_level})>"
