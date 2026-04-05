import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import time

from app.models.imported_page import ImportJob, ImportedPage
from app.schemas.import_schema import ImportRequest, ImportSourceType, PageStatus
from app.services.scraper_service import ScraperService
from app.services.conversion_service import ConversionService
from app.services.integration_service import IntegrationService

logger = logging.getLogger(__name__)

class ImportService:
    """Main service for coordinating import process"""
    
    def __init__(self, db: Session):
        self.db = db
        self.scraper = ScraperService()
        self.converter = ConversionService()
        self.integration = IntegrationService()
    
    def create_import_job(self, import_request: ImportRequest) -> ImportJob:
        """Create a new import job"""
        import_job = ImportJob(
            name=import_request.name,
            source_type=import_request.source_type.value,
            status="pending",
            total_urls=len(import_request.urls)
        )
        
        self.db.add(import_job)
        self.db.commit()
        self.db.refresh(import_job)
        
        # Create imported page records
        for url in import_request.urls:
            imported_page = ImportedPage(
                import_job_id=import_job.id,
                source_url=str(url),
                status="pending"
            )
            self.db.add(imported_page)
        
        self.db.commit()
        
        logger.info(f"Created import job {import_job.id} with {len(import_request.urls)} URLs")
        return import_job
    
    def process_import_job(self, job_id: str) -> ImportJob:
        """Process an import job (extract, convert, integrate)"""
        # Get the job
        import_job = self.db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if not import_job:
            raise ValueError(f"Import job {job_id} not found")
        
        # Update status
        import_job.status = "processing"
        self.db.commit()
        
        # Get all pages for this job
        pages = self.db.query(ImportedPage).filter(
            ImportedPage.import_job_id == job_id
        ).all()
        
        successful = 0
        failed = 0
        errors = []
        
        # Process each page
        for page in pages:
            try:
                self._process_single_page(page, import_job)
                successful += 1
                page.status = PageStatus.SENT_TO_WEBBOT.value
            except Exception as e:
                failed += 1
                page.status = PageStatus.FAILED.value
                page.integration_error = str(e)
                errors.append(f"URL {page.source_url}: {str(e)}")
            
            # Update page timestamp
            page.updated_at = datetime.utcnow()
            self.db.commit()
            
            # Small delay to be polite
            time.sleep(0.2)
        
        # Update job status
        import_job.successful_imports = successful
        import_job.failed_imports = failed
        import_job.errors = "\n".join(errors) if errors else None
        
        if failed == 0:
            import_job.status = "completed"
        elif successful > 0:
            import_job.status = "completed_with_errors"
        else:
            import_job.status = "failed"
        
        import_job.completed_at = datetime.utcnow()
        self.db.commit()
        
        return import_job
    
    def _process_single_page(self, page: ImportedPage, import_job: ImportJob):
        """Process a single page through the pipeline"""
        logger.info(f"Processing page: {page.source_url}")
        
        # Step 1: Scrape the page
        scrape_result = self.scraper.scrape_url(page.source_url)
        page.extracted_at = datetime.utcnow()
        
        if not scrape_result["success"]:
            page.extraction_error = scrape_result.get("error")
            page.status = PageStatus.FAILED.value
            self.db.commit()
            raise Exception(f"Scraping failed: {scrape_result.get('error')}")
        
        # Update page with scraped data
        page.title = scrape_result["title"]
        page.content = scrape_result["content"]
        page.content_type = scrape_result["content_type"]
        page.language = scrape_result["language"]
        page.metadata = scrape_result["metadata"]
        page.status = PageStatus.EXTRACTED.value
        self.db.commit()
        
        # Step 2: Convert for WebBot
        webbot_data = self.converter.prepare_for_webbot(
            html=scrape_result["content"],
            title=scrape_result["title"],
            metadata=scrape_result["metadata"]
        )
        page.status = PageStatus.CONVERTED.value
        page.converted_at = datetime.utcnow()
        self.db.commit()
        
        # Step 3: Send to WebBot
        integration_result = self.integration.send_to_webbot(webbot_data)
        
        if integration_result["success"]:
            page.webbot_page_id = integration_result["webbot_page_id"]
            page.webbot_page_url = integration_result["webbot_page_url"]
            page.sent_to_webbot_at = datetime.utcnow()
            page.status = PageStatus.SENT_TO_WEBBOT.value
            logger.info(f"Successfully sent to WebBot: {page.webbot_page_id}")
        else:
            page.integration_error = integration_result["error"]
            page.status = PageStatus.FAILED.value
            raise Exception(f"WebBot integration failed: {integration_result['error']}")
        
        self.db.commit()
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get detailed status of an import job"""
        import_job = self.db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if not import_job:
            return {"error": "Job not found"}
        
        # Get pages for this job
        pages = self.db.query(ImportedPage).filter(
            ImportedPage.import_job_id == job_id
        ).all()
        
        # Calculate progress
        total = len(pages)
        if total == 0:
            progress = 0
        else:
            completed = sum(1 for p in pages if p.status == PageStatus.SENT_TO_WEBBOT.value)
            progress = (completed / total) * 100
        
        return {
            "job_id": import_job.id,
            "name": import_job.name,
            "status": import_job.status,
            "progress": progress,
            "total_urls": import_job.total_urls,
            "successful_imports": import_job.successful_imports,
            "failed_imports": import_job.failed_imports,
            "created_at": import_job.created_at,
            "completed_at": import_job.completed_at,
            "pages": [
                {
                    "id": p.id,
                    "source_url": p.source_url,
                    "title": p.title,
                    "status": p.status,
                    "webbot_page_id": p.webbot_page_id,
                    "webbot_page_url": p.webbot_page_url,
                    "error": p.extraction_error or p.conversion_error or p.integration_error
                }
                for p in pages
            ]
        }
    
    def list_jobs(self, limit: int = 50, offset: int = 0) -> List[ImportJob]:
        """List import jobs"""
        return self.db.query(ImportJob)\
            .order_by(ImportJob.created_at.desc())\
            .offset(offset)\
            .limit(limit)\
            .all()