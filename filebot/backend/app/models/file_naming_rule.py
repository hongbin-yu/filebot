from sqlalchemy import Column, DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from ..db.database import Base


class FileNamingRule(Base):
    """文档编号生成规则表 (对应旧系统的recordclass)"""
    __tablename__ = "file_naming_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=True, index=True)  # 规则名称（可选）
    basename = Column(String(50), nullable=False)          # 文档编号前缀，如"PO-"
    max_number = Column(Integer, default=0, nullable=False)  # 当前最大序列号
    increment_by = Column(Integer, default=1, nullable=False)  # 序列号增量
    description = Column(String(500), nullable=True)       # 规则描述
    subfolder_name = Column(String(100), nullable=True)    # 子文件夹名称，用于文件分目录存储
    
    # 外键关系
    app_id = Column(String(36), ForeignKey("apps.id"), nullable=False, index=True)
    
    # 审计字段
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100), nullable=True)  # 创建者用户名
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(100), nullable=True)  # 更新者用户名

    # 关系
    app = relationship("App", back_populates="file_naming_rules")

    def generate_document_number(self) -> str:
        """
        生成下一个文档编号
        格式: {basename}{max_number:04d}
        例如: "PO-1001"
        """
        return f"{self.basename}{self.max_number:04d}"
    
    def generate_filename(self) -> str:
        """
        生成下一个文档编号（兼容旧方法名）
        格式: {basename}{max_number:04d}
        例如: "PO-1001"
        """
        return self.generate_document_number()
    
    def increment_number(self):
        """
        增加序列号，准备下一个文档
        """
        self.max_number += self.increment_by

    def __repr__(self):
        return f"<FileNamingRule(id={self.id}, basename={self.basename}, max_number={self.max_number})>"