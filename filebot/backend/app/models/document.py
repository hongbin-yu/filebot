from sqlalchemy import Column, DateTime, String, Integer, BigInteger, ForeignKey, Enum, Boolean, JSON, Float, Text
# from sqlalchemy.dialects.postgresql import UUID  # 注释掉，使用String代替
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from ..db.database import Base


class ConversionStatus(enum.Enum):
    """转换状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ThumbnailStatus(enum.Enum):
    """缩略图生成状态枚举"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    GENERATED = "GENERATED"
    FAILED = "FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"  # 对于无法生成缩略图的文件类型


class FileType(enum.Enum):
    """文件类型枚举"""
    TIFF = "tiff"
    PDF = "pdf"
    DOC = "doc"
    DOCX = "docx"
    JPEG = "jpeg"
    JPG = "jpg"
    PNG = "png"
    PCL = "pcl"
    PS = "ps"  # PostScript
    TXT = "txt"
    HTML = "html"
    HTM = "htm"
    OTHER = "other"


class DocumentStatus(enum.Enum):
    """文档状态枚举（兼容旧系统）"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    PROCESSING = "processing"


class DocumentType(enum.Enum):
    """文档类型枚举（兼容旧系统）"""
    GENERAL = "general"
    INVOICE = "invoice"
    CONTRACT = "contract"
    REPORT = "report"
    OTHER = "other"


class ClassificationStatus(enum.Enum):
    """分类状态枚举"""
    UNCLASSIFIED = "unclassified"  # 未分类
    AI_CLASSIFIED = "ai_classified"  # AI已分类
    NEEDS_MANUAL = "needs_manual"  # 需要人工分类
    MANUAL_CLASSIFIED = "manual_classified"  # 人工已分类
    REVIEW_NEEDED = "review_needed"  # 需要审核（AI分类但置信度中等）


class PublishStatus(enum.Enum):
    """发布状态枚举"""
    PUBLISHED = "PUBLISHED"
    UNPUBLISHED = "UNPUBLISHED"


class Document(Base):
    """文档表 (Document)"""
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    folder_id = Column(String(36), ForeignKey("folders.id"), nullable=False)
    
    # 旧系统兼容字段
    document_number = Column(String(100), nullable=True, unique=True, index=True)  # 旧系统的文档编号
    title = Column(String(255), nullable=True, index=True)  # 文档标题
    description = Column(String(1000), nullable=True)  # 文档描述
    status = Column(Enum(DocumentStatus), default=DocumentStatus.ACTIVE)  # 文档状态
    type = Column(Enum(DocumentType), default=DocumentType.GENERAL)  # 文档类型
    comments = Column(String(2000), nullable=True)  # 备注
    publish_status = Column(Enum(PublishStatus), default=PublishStatus.UNPUBLISHED)  # 发布状态
    
    # 文件信息
    original_filename = Column(String(255), nullable=False, index=True)
    stored_filename = Column(String(255), nullable=False)  # 安全化的存储文件名（纯path结构，不使用UUID）
    file_size = Column(BigInteger, nullable=False)  # 字节数
    file_type = Column(Enum(FileType), nullable=False)
    mime_type = Column(String(100), nullable=False)
    
    # 存储设备信息
    device_id = Column(String(36), ForeignKey("devices.id"), nullable=True, index=True)  # 存储设备ID
    storage_subfolder = Column(String(255), nullable=True)  # 存储子文件夹路径（相对路径）
    full_storage_path = Column(String(500), nullable=True)  # 完整存储路径（计算字段）
    
    # 路径系统重构 - 新字段
    # 注意: url_path已重命名为path
    storage_path = Column(String(500), nullable=True, index=True)  # 物理存储路径 (相对于DATA_ROOT)
    path = Column(String(500), nullable=True, index=True)          # 公共URL路径（原url_path）
    parent_folder_path = Column(String(500), nullable=True, index=True)  # 父文件夹路径，用于快速构建完整路径
    
    # 转换信息
    conversion_status = Column(Enum(ConversionStatus), default=ConversionStatus.PENDING)
    converted_pdf_path = Column(String(500), nullable=True)  # 转换后的PDF路径
    conversion_error = Column(String(1000), nullable=True)  # 转换错误信息
    
    # 缩略图信息
    thumbnail_status = Column(Enum(ThumbnailStatus), default=ThumbnailStatus.PENDING)  # 缩略图生成状态
    thumbnail_path = Column(String(500), nullable=True)  # 缩略图存储路径
    thumbnail_generated_at = Column(DateTime(timezone=True), nullable=True)  # 缩略图生成时间
    thumbnail_error = Column(String(1000), nullable=True)  # 缩略图生成错误信息
    
    # 元数据
    page_count = Column(Integer, nullable=True)  # 页数
    resolution = Column(String(50), nullable=True)  # 分辨率，如 "300x300"
    document_metadata = Column(JSON, default=dict)  # 其他元数据
    
    # AI处理信息
    ai_category = Column(String(100), nullable=True)  # AI分类类别
    ai_confidence = Column(Float, nullable=True, default=0.0)  # AI分类置信度
    ai_tags = Column(JSON, nullable=True)  # AI提取的标签
    ai_summary = Column(Text, nullable=True)  # AI生成的摘要
    vector_embedding = Column(JSON, nullable=True)  # 向量嵌入数据
    is_indexed = Column(Boolean, default=False)  # 是否已建立向量索引
    classification_status = Column(Enum(ClassificationStatus), default=ClassificationStatus.UNCLASSIFIED)  # 分类状态
    
    # 系统信息
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    is_archived = Column(Boolean, default=False)
    
    # 审计字段（兼容旧系统）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100), nullable=True)  # 创建者用户名
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(100), nullable=True)  # 更新者用户名

    # 关系
    folder = relationship("Folder", back_populates="documents")
    uploader = relationship("User", back_populates="documents")
    device = relationship("Device", back_populates="documents")  # 存储设备关系
    pages = relationship("Page", back_populates="document", cascade="all, delete-orphan")
    conversion_tasks = relationship("ConversionTask", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(id={self.id}, filename={self.original_filename}, status={self.conversion_status})>"

    @property
    def folder_path(self) -> str:
        """获取文件夹路径（计算属性）"""
        # 优先使用parent_folder_path，如果不存在则尝试从folder关系获取
        if self.parent_folder_path:
            return self.parent_folder_path
        
        # 如果parent_folder_path为空但有folder关系，尝试获取folder.path
        if hasattr(self, 'folder') and self.folder:
            return self.folder.path or ''
        
        return ''