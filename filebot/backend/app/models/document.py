from sqlalchemy import Column, DateTime, String, Integer, BigInteger, ForeignKey, Enum, Boolean, JSON, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from ..db.database import Base


class ConversionStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ThumbnailStatus(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    GENERATED = "GENERATED"
    FAILED = "FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class FileType(enum.Enum):
    TIFF = "tiff"
    PDF = "pdf"
    DOC = "doc"
    DOCX = "docx"
    JPEG = "jpeg"
    JPG = "jpg"
    PNG = "png"
    GIF = "gif"
    WEBP = "webp"
    BMP = "bmp"
    SVG = "svg"
    PCL = "pcl"
    PS = "ps"
    TXT = "txt"
    HTML = "html"
    HTM = "htm"
    OTHER = "other"


class DocumentStatus(enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    PROCESSING = "processing"


class DocumentType(enum.Enum):
    GENERAL = "general"
    INVOICE = "invoice"
    CONTRACT = "contract"
    REPORT = "report"
    OTHER = "other"


class ClassificationStatus(enum.Enum):
    UNCLASSIFIED = "unclassified"
    AI_CLASSIFIED = "ai_classified"
    NEEDS_MANUAL = "needs_manual"
    MANUAL_CLASSIFIED = "manual_classified"
    REVIEW_NEEDED = "review_needed"


class PublishStatus(enum.Enum):
    PUBLISHED = "PUBLISHED"
    UNPUBLISHED = "UNPUBLISHED"


class Document(Base):
    """文档表 (Document) - 使用路径作为主键，彻底移除UUID"""
    __tablename__ = "documents"

    # path 即主键
    path = Column(String(500), primary_key=True)
    folder_path = Column(String(500), ForeignKey("folders.path"), nullable=False, index=True)  # 父文件夹路径
    
    # 旧系统兼容字段
    document_number = Column(String(100), nullable=True, unique=True, index=True)
    title = Column(String(255), nullable=True, index=True)
    description = Column(String(1000), nullable=True)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.ACTIVE)
    type = Column(Enum(DocumentType), default=DocumentType.GENERAL)
    comments = Column(String(2000), nullable=True)
    publish_status = Column(Enum(PublishStatus), default=PublishStatus.UNPUBLISHED)
    
    # 文件信息
    original_filename = Column(String(255), nullable=False, index=True)
    stored_filename = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_type = Column(Enum(FileType), nullable=False)
    mime_type = Column(String(100), nullable=False)
    
    # 存储设备
    device_id = Column(String(36), ForeignKey("devices.id"), nullable=True, index=True)
    storage_subfolder = Column(String(255), nullable=True)
    full_storage_path = Column(String(500), nullable=True)
    
    # 路径信息
    storage_path = Column(String(500), nullable=True, index=True)          # 物理存储路径
    parent_folder_path = Column(String(500), nullable=True, index=True)    # 旧字段，保留兼容
    
    # 转换信息
    conversion_status = Column(Enum(ConversionStatus), default=ConversionStatus.PENDING)
    converted_pdf_path = Column(String(500), nullable=True)
    conversion_error = Column(String(1000), nullable=True)
    
    # 缩略图
    thumbnail_status = Column(Enum(ThumbnailStatus), default=ThumbnailStatus.PENDING)
    thumbnail_path = Column(String(500), nullable=True)
    thumbnail_generated_at = Column(DateTime(timezone=True), nullable=True)
    thumbnail_error = Column(String(1000), nullable=True)
    
    # 元数据
    page_count = Column(Integer, nullable=True)
    resolution = Column(String(50), nullable=True)
    document_metadata = Column(JSON, default=dict)
    
    # AI处理
    ai_category = Column(String(100), nullable=True)
    ai_confidence = Column(Float, nullable=True, default=0.0)
    ai_tags = Column(JSON, nullable=True)
    ai_summary = Column(Text, nullable=True)
    vector_embedding = Column(JSON, nullable=True)
    is_indexed = Column(Boolean, default=False)
    classification_status = Column(Enum(ClassificationStatus), default=ClassificationStatus.UNCLASSIFIED)
    
    # 系统信息
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    is_archived = Column(Boolean, default=False)
    
    # 审计字段
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(100), nullable=True)

    # 关系
    folder = relationship("Folder", back_populates="documents")
    uploader = relationship("User", back_populates="documents")
    device = relationship("Device", back_populates="documents")
    pages = relationship("Page", back_populates="document", cascade="all, delete-orphan", foreign_keys="Page.document_path")
    conversion_tasks = relationship("ConversionTask", back_populates="document", cascade="all, delete-orphan", foreign_keys="ConversionTask.document_path")

    def __repr__(self):
        return f"<Document(path={self.path}, filename={self.original_filename})>"

    @property
    def folder_path_prop(self) -> str:
        """获取文件夹路径"""
        return self.folder_path or self.parent_folder_path or ''

    @property
    def url(self) -> str:
        """获取文档的公开URL"""
        return self.path or ''

    @property
    def preview_url(self) -> str:
        """获取预览URL"""
        return self.path or ''
