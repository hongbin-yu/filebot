from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import enum


# 枚举类
class ConversionStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileType(str, enum.Enum):
    TIFF = "tiff"
    PDF = "pdf"
    DOC = "doc"
    DOCX = "docx"
    JPEG = "jpeg"
    JPG = "jpg"
    PNG = "png"
    PCL = "pcl"
    PS = "ps"
    TXT = "txt"
    HTML = "html"
    HTM = "htm"
    OTHER = "other"


class DocumentStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    PROCESSING = "processing"


class PublishStatus(str, enum.Enum):
    """发布状态枚举"""
    PUBLISHED = "PUBLISHED"
    UNPUBLISHED = "UNPUBLISHED"


class DocumentType(str, enum.Enum):
    GENERAL = "general"
    INVOICE = "invoice"
    CONTRACT = "contract"
    REPORT = "report"
    OTHER = "other"


# Document 基础模型
class DocumentBase(BaseModel):
    """文档基础模型"""
    # 旧系统兼容字段
    document_number: Optional[str] = Field(None, max_length=100, description="文档编号")
    title: Optional[str] = Field(None, max_length=255, description="文档标题")
    description: Optional[str] = Field(None, max_length=1000, description="文档描述")
    status: Optional[DocumentStatus] = Field(DocumentStatus.ACTIVE, description="文档状态")
    publish_status: Optional[PublishStatus] = Field(PublishStatus.UNPUBLISHED, description="发布状态")
    type: Optional[DocumentType] = Field(DocumentType.GENERAL, description="文档类型")
    comments: Optional[str] = Field(None, max_length=2000, description="备注")
    
    # 文件信息
    original_filename: str = Field(..., max_length=255, description="原始文件名")
    file_size: int = Field(..., ge=0, description="文件大小（字节）")
    file_type: FileType = Field(..., description="文件类型")
    mime_type: str = Field(..., max_length=100, description="MIME类型")
    
    # 转换信息
    conversion_status: Optional[ConversionStatus] = Field(ConversionStatus.PENDING, description="转换状态")
    
    # 元数据
    page_count: Optional[int] = Field(None, ge=0, description="页数")
    resolution: Optional[str] = Field(None, max_length=50, description="分辨率")
    document_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="其他元数据")
    
    # AI处理信息
    ai_category: Optional[str] = Field(None, max_length=100, description="AI分类类别")
    ai_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="AI分类置信度")
    ai_tags: Optional[Dict[str, Any]] = Field(None, description="AI提取的标签")
    ai_summary: Optional[str] = Field(None, description="AI生成的摘要")
    classification_status: Optional[str] = Field(None, description="分类状态")
    
    # 系统信息
    is_archived: Optional[bool] = Field(False, description="是否已归档")


class DocumentCreate(DocumentBase):
    """文档创建模型"""
    folder_id: uuid.UUID = Field(..., description="所属文件夹ID")
    uploaded_by: uuid.UUID = Field(..., description="上传用户ID")
    created_by: Optional[str] = Field(None, description="创建者用户名")
    
    # 存储文件名由系统生成
    stored_filename: Optional[str] = Field(None, description="存储文件名（系统生成）")
    converted_pdf_path: Optional[str] = Field(None, description="转换后PDF路径")
    conversion_error: Optional[str] = Field(None, description="转换错误信息")
    
    @validator("stored_filename")
    def generate_stored_filename(cls, v):
        """如果未提供存储文件名，则生成UUID"""
        if v is None:
            return str(uuid.uuid4())
        return v


class DocumentUpdate(BaseModel):
    """文档更新模型"""
    document_number: Optional[str] = Field(None, max_length=100, description="文档编号")
    title: Optional[str] = Field(None, max_length=255, description="文档标题")
    description: Optional[str] = Field(None, max_length=1000, description="文档描述")
    status: Optional[DocumentStatus] = Field(None, description="文档状态")
    publish_status: Optional[PublishStatus] = Field(None, description="发布状态")
    type: Optional[DocumentType] = Field(None, description="文档类型")
    comments: Optional[str] = Field(None, max_length=2000, description="备注")
    
    conversion_status: Optional[ConversionStatus] = Field(None, description="转换状态")
    converted_pdf_path: Optional[str] = Field(None, description="转换后PDF路径")
    conversion_error: Optional[str] = Field(None, description="转换错误信息")
    
    page_count: Optional[int] = Field(None, ge=0, description="页数")
    resolution: Optional[str] = Field(None, max_length=50, description="分辨率")
    document_metadata: Optional[Dict[str, Any]] = Field(None, description="其他元数据")
    
    is_archived: Optional[bool] = Field(None, description="是否已归档")
    updated_by: Optional[str] = Field(None, description="更新者用户名")


class DocumentResponse(DocumentBase):
    """文档响应模型"""
    id: uuid.UUID
    folder_id: uuid.UUID
    uploaded_by: uuid.UUID
    stored_filename: str
    converted_pdf_path: Optional[str]
    conversion_error: Optional[str]
    created_by: Optional[str]
    updated_by: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    # 路径字段
    storage_path: Optional[str] = None
    path: Optional[str] = None  # 公共URL路径（原url_path）
    folder_path: Optional[str] = None  # 父文件夹路径
    parent_folder_path: Optional[str] = None  # 与folder_path相同，保持兼容性
    
    class Config:
        from_attributes = True


# Page 基础模型
class PageBase(BaseModel):
    """页面基础模型"""
    page_number: int = Field(..., ge=1, description="页码（从1开始）")
    
    # 索引字段（最多9个）
    index1: Optional[str] = Field(None, max_length=255, description="索引字段1")
    index2: Optional[str] = Field(None, max_length=255, description="索引字段2")
    index3: Optional[str] = Field(None, max_length=255, description="索引字段3")
    index4: Optional[str] = Field(None, max_length=255, description="索引字段4")
    index5: Optional[str] = Field(None, max_length=255, description="索引字段5")
    index6: Optional[str] = Field(None, max_length=255, description="索引字段6")
    index7: Optional[str] = Field(None, max_length=255, description="索引字段7")
    index8: Optional[str] = Field(None, max_length=255, description="索引字段8")
    index9: Optional[str] = Field(None, max_length=255, description="索引字段9")
    
    # 文件路径
    original_page_path: Optional[str] = Field(None, max_length=500, description="原始页面文件路径")
    converted_page_path: Optional[str] = Field(None, max_length=500, description="转换后页面路径")
    thumbnail_path: Optional[str] = Field(None, max_length=500, description="缩略图路径")
    
    # 尺寸信息
    width: Optional[int] = Field(None, ge=0, description="宽度（像素）")
    height: Optional[int] = Field(None, ge=0, description="高度（像素）")
    
    # OCR文本
    ocr_text: Optional[str] = Field(None, description="OCR识别的文本")


class PageCreate(PageBase):
    """页面创建模型"""
    document_id: uuid.UUID = Field(..., description="所属文档ID")
    created_by: Optional[str] = Field(None, description="创建者用户名")


class PageUpdate(BaseModel):
    """页面更新模型"""
    page_number: Optional[int] = Field(None, ge=1, description="页码")
    
    # 索引字段
    index1: Optional[str] = Field(None, max_length=255, description="索引字段1")
    index2: Optional[str] = Field(None, max_length=255, description="索引字段2")
    index3: Optional[str] = Field(None, max_length=255, description="索引字段3")
    index4: Optional[str] = Field(None, max_length=255, description="索引字段4")
    index5: Optional[str] = Field(None, max_length=255, description="索引字段5")
    index6: Optional[str] = Field(None, max_length=255, description="索引字段6")
    index7: Optional[str] = Field(None, max_length=255, description="索引字段7")
    index8: Optional[str] = Field(None, max_length=255, description="索引字段8")
    index9: Optional[str] = Field(None, max_length=255, description="索引字段9")
    
    original_page_path: Optional[str] = Field(None, max_length=500, description="原始页面文件路径")
    converted_page_path: Optional[str] = Field(None, max_length=500, description="转换后页面路径")
    thumbnail_path: Optional[str] = Field(None, max_length=500, description="缩略图路径")
    
    width: Optional[int] = Field(None, ge=0, description="宽度")
    height: Optional[int] = Field(None, ge=0, description="高度")
    
    ocr_text: Optional[str] = Field(None, description="OCR文本")
    updated_by: Optional[str] = Field(None, description="更新者用户名")


class PageResponse(PageBase):
    """页面响应模型"""
    id: uuid.UUID
    document_id: uuid.UUID
    created_by: Optional[str]
    updated_by: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True