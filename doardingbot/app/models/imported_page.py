from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class ImportJob(Base):
    """Tracks import jobs/batches"""
    __tablename__ = "import_jobs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=True)
    source_type = Column(String(50), default="url")  # url, rss, sitemap, batch
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    total_urls = Column(Integer, default=0)
    successful_imports = Column(Integer, default=0)
    failed_imports = Column(Integer, default=0)
    errors = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    imported_pages = relationship("ImportedPage", back_populates="import_job", cascade="all, delete-orphan")

class ImportedPage(Base):
    """Stores imported pages before sending to WebBot/FileBot"""
    __tablename__ = "imported_pages"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    import_job_id = Column(String(36), ForeignKey("import_jobs.id"), nullable=True)
    source_url = Column(String(2000), nullable=False)
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)
    content_type = Column(String(50), default="html")  # html, markdown, text
    language = Column(String(10), default="en")
    page_metadata = Column(JSON, nullable=True)  # Store original page metadata
    
    # Processing status
    status = Column(String(20), default="pending")  # pending, extracted, converted, sent_to_webbot, sent_to_filebot, failed
    extraction_error = Column(Text, nullable=True)
    conversion_error = Column(Text, nullable=True)
    integration_error = Column(Text, nullable=True)
    
    # WebBot integration
    webbot_page_id = Column(String(36), nullable=True)
    webbot_page_url = Column(String(500), nullable=True)
    
    # FileBot integration  
    filebot_file_id = Column(String(36), nullable=True)
    filebot_file_path = Column(String(500), nullable=True)
    
    # Timestamps
    extracted_at = Column(DateTime(timezone=True), nullable=True)
    converted_at = Column(DateTime(timezone=True), nullable=True)
    sent_to_webbot_at = Column(DateTime(timezone=True), nullable=True)
    sent_to_filebot_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    import_job = relationship("ImportJob", back_populates="imported_pages")
    images = relationship("ImportedImage", back_populates="imported_page", cascade="all, delete-orphan")