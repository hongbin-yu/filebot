"""Institution model"""
from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.sql import func
import uuid

from ..db.database import Base


class Institution(Base):
    """部门/机构表"""
    __tablename__ = "institutions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), unique=True, nullable=False, index=True)     # "Employment and Social Development Canada"
    slug = Column(String(100), unique=True, nullable=False, index=True)      # "esdc"
    description = Column(Text, nullable=True)                                # optional description
    domain = Column(String(200), nullable=True)                              # "canada.ca"
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Institution(id={self.id}, name={self.name}, slug={self.slug})>"
