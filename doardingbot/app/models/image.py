from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, ForeignKey, JSON, LargeBinary
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class ImportedImage(Base):
    """Stores images extracted from web pages"""
    __tablename__ = "imported_images"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    imported_page_id = Column(String(36), ForeignKey("imported_pages.id"))
    
    # Source information
    source_url = Column(String(2000), nullable=False)  # Original image URL
    alt_text = Column(String(500), nullable=True)
    title = Column(String(500), nullable=True)
    caption = Column(String(1000), nullable=True)
    
    # Image metadata
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    file_size = Column(Integer, nullable=True)  # In bytes
    mime_type = Column(String(100), nullable=True)
    file_extension = Column(String(10), nullable=True)
    
    # Processing status
    status = Column(String(20), default="pending")  # pending, downloaded, uploaded_to_filebot, failed
    download_error = Column(Text, nullable=True)
    upload_error = Column(Text, nullable=True)
    
    # FileBot integration
    filebot_document_id = Column(String(36), nullable=True)
    filebot_document_number = Column(String(100), nullable=True)
    filebot_storage_path = Column(String(500), nullable=True)
    filebot_access_url = Column(String(500), nullable=True)
    
    # Local storage (temporary)
    local_file_path = Column(String(500), nullable=True)
    local_file_hash = Column(String(64), nullable=True)  # SHA256 hash
    
    # Timestamps
    downloaded_at = Column(DateTime(timezone=True), nullable=True)
    uploaded_to_filebot_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    imported_page = relationship("ImportedPage", back_populates="images")