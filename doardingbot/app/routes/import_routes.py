from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.models.base import get_db
from app.schemas.import_schema import (
    ImportRequest, ImportJobResponse, ImportStatusResponse,
    SingleUrlImportRequest, ImportedPageResponse
)
from app.services.import_service import ImportService

router = APIRouter(prefix="/api/v1/import", tags=["import"])
logger = logging.getLogger(__name__)

@router.post("/jobs", response_model=ImportJobResponse)
async def create_import_job(
    import_request: ImportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a new import job
    
    - **urls**: List of URLs to import
    - **name**: Optional name for the job
    - **source_type**: Type of source (url, rss, sitemap, batch)
    - **target_system**: Target system: 'webbot' or 'filebot'
    """
    try:
        import_service = ImportService(db)
        
        # Create the job
        import_job = import_service.create_import_job(import_request)
        
        # Schedule processing in background
        background_tasks.add_task(
            import_service.process_import_job,
            import_job.id
        )
        
        return import_job
        
    except Exception as e:
        logger.error(f"Error creating import job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating import job: {str(e)}")

@router.post("/single", response_model=ImportedPageResponse)
async def import_single_url(
    import_request: SingleUrlImportRequest,
    db: Session = Depends(get_db)
):
    """
    Import a single URL immediately (synchronous)
    
    - **url**: URL to import
    - **name**: Optional name
    - **target_system**: Target system: 'webbot' or 'filebot'
    """
    try:
        # Convert single request to batch request
        batch_request = ImportRequest(
            urls=[import_request.url],
            name=import_request.name,
            source_type="url",
            target_system=import_request.target_system,
            convert_to_markdown=True,
            preserve_images=True
        )
        
        import_service = ImportService(db)
        
        # Create job
        import_job = import_service.create_import_job(batch_request)
        
        # Process immediately (synchronous)
        import_service.process_import_job(import_job.id)
        
        # Get the imported page
        page = db.query(import_service.db.query(ImportedPage).filter(
            ImportedPage.import_job_id == import_job.id
        ).first())
        
        if not page:
            raise HTTPException(status_code=404, detail="Page not found after import")
        
        return page
        
    except Exception as e:
        logger.error(f"Error importing single URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error importing URL: {str(e)}")

@router.get("/jobs/{job_id}", response_model=ImportStatusResponse)
async def get_import_job_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get status of an import job"""
    import_service = ImportService(db)
    status = import_service.get_job_status(job_id)
    
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    
    return ImportStatusResponse(
        job_id=status["job_id"],
        status=status["status"],
        progress=status["progress"],
        message=f"Processed {status['successful_imports']} of {status['total_urls']} URLs",
        details=status
    )

@router.get("/jobs/{job_id}/pages", response_model=List[ImportedPageResponse])
async def get_job_pages(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get all pages for an import job"""
    import_service = ImportService(db)
    
    # Verify job exists
    import_job = db.query(import_service.db.query(ImportJob).filter(
        ImportJob.id == job_id
    ).first())
    
    if not import_job:
        raise HTTPException(status_code=404, detail="Import job not found")
    
    # Get pages
    pages = db.query(import_service.db.query(ImportedPage).filter(
        ImportedPage.import_job_id == job_id
    ).all())
    
    return pages

@router.get("/jobs", response_model=List[ImportJobResponse])
async def list_import_jobs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List import jobs"""
    import_service = ImportService(db)
    jobs = import_service.list_jobs(limit=limit, offset=offset)
    return jobs

@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Check database
        db.execute("SELECT 1")
        
        # Check WebBot connectivity (optional)
        import_service = ImportService(db)
        webbot_healthy = import_service.integration.check_webbot_health()
        
        return {
            "status": "healthy",
            "database": "connected",
            "webbot_available": webbot_healthy,
            "service": "DoardingBot"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unhealthy")