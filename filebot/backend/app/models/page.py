from sqlalchemy import Column, DateTime, String, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from ..db.database import Base


class Page(Base):
    """页面表 (Page)"""
    __tablename__ = "pages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_path = Column(String(500), ForeignKey("documents.path"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)  # 页码，从1开始

    # 索引字段（最多9个，兼容旧系统）
    index1 = Column(String(255), nullable=True, index=True)
    index2 = Column(String(255), nullable=True, index=True)
    index3 = Column(String(255), nullable=True, index=True)
    index4 = Column(String(255), nullable=True, index=True)
    index5 = Column(String(255), nullable=True, index=True)
    index6 = Column(String(255), nullable=True, index=True)
    index7 = Column(String(255), nullable=True, index=True)
    index8 = Column(String(255), nullable=True, index=True)
    index9 = Column(String(255), nullable=True, index=True)

    # 文件路径
    original_page_path = Column(String(500), nullable=True)  # 原始页面文件路径（如单页TIFF）
    converted_page_path = Column(String(500), nullable=True)  # 转换后页面路径（PDF单页）
    thumbnail_path = Column(String(500), nullable=True)  # 缩略图路径

    # 尺寸信息
    width = Column(Integer, nullable=True)  # 宽度（像素）
    height = Column(Integer, nullable=True)  # 高度（像素）

    # 其他元数据
    ocr_text = Column(Text, nullable=True)  # OCR识别的文本（如果做了OCR）

    # 审计字段（兼容旧系统）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100), nullable=True)  # 创建者用户名
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(100), nullable=True)  # 更新者用户名

    # 关系
    document = relationship("Document", back_populates="pages", foreign_keys=[document_path])

    def __repr__(self):
        return f"<Page(id={self.id}, doc_path={self.document_path}, page={self.page_number})>"
