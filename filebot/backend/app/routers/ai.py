"""
AI feature routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import logging

from ..db.database import get_db
from ..models.document import Document
from ..models.user import User
from ..models.crawl_task import CrawlTask, CrawlTaskStatus
from ..schemas.ai import (
    AIClassifyRequest, AIClassifyResponse, AICategoryResult,
    WebsiteCrawlRequest, WebsiteCrawlResponse, WebsiteCrawlStatus,
    WebsiteCrawlTaskList, SitemapImportRequest, SitemapImportResponse
)
from ..ai.ai_classifier import classifier, AICategory
from ..ai.website_crawler import crawl_website_task
from ..ai.scrapling_crawler import parse_sitemap_urls
from ..routers.auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/classify", response_model=AIClassifyResponse)
async def classify_document(
    request: AIClassifyRequest,
    db: Session = Depends(get_db)
):
    """
    Classify a document
    
    Supports direct text input or document path lookup
    """
    if request.document_id:
        # Classify by document id (path)
        document = db.query(Document).filter(Document.path == request.document_id).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {request.document_id} not found"
            )
        
        result = classifier.classify_document(document, db, extract_text=request.extract_text)
        
    elif request.text:
        # Classify text directly
        result = classifier.classify_text(request.text, model=request.model)
        
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide document_id or text"
        )
    
    return AIClassifyResponse(
        success=result["success"],
        category=result["category"].value if result.get("category") else None,
        ai_category=result.get("ai_category"),
        document_type=result.get("document_type"),
        confidence=result.get("confidence", 0.0),
        processing_time=result.get("processing_time", 0.0),
        model=result.get("model"),
        raw_response=result.get("raw_response"),
        error=result.get("error")
    )

@router.post("/classify-batch", response_model=List[AIClassifyResponse])
async def classify_documents_batch(
    document_paths: List[str],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Batch classify documents
    
    Returns task ID, actual processing happens in background
    """
    # Validate documents exist
    documents = db.query(Document).filter(Document.path.in_(document_paths)).all()
    if len(documents) != len(document_paths):
        found_paths = [doc.path for doc in documents]
        missing_paths = set(document_paths) - set(found_paths)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documents not found: {missing_paths}"
        )
    
    # TODO: Implement background batch processing
    # For now, process synchronously
    results = []
    for document in documents:
        result = classifier.classify_document(document, db)
        results.append(AIClassifyResponse(
            document_id=document.path,
            success=result["success"],
            category=result["category"].value if result.get("category") else None,
            ai_category=result.get("ai_category"),
            document_type=result.get("document_type"),
            confidence=result.get("confidence", 0.0),
            processing_time=result.get("processing_time", 0.0),
            model=result.get("model"),
            raw_response=result.get("raw_response"),
            error=result.get("error")
        ))
    
    return results

@router.get("/test-connection")
async def test_ai_connection():
    """Test AI service connection"""
    is_connected = classifier.test_connection()
    
    if is_connected:
        return {
            "status": "connected",
            "service": "ollama",
            "url": classifier.ollama_url,
            "default_model": classifier.default_model
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to connect to Ollama service, please ensure the service is running"
        )

@router.get("/categories")
async def get_ai_categories():
    """Get available AI classification categories"""
    categories = []
    for category in AICategory:
        categories.append({
            "value": category.value,
            "label": category.name,
            "document_type": category.to_document_type().value
        })
    
    return {
        "categories": categories,
        "count": len(categories)
    }

@router.post("/crawl-website", response_model=WebsiteCrawlResponse)
async def crawl_website(
    request: WebsiteCrawlRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Crawl website content and import to specified folder
    
    This is a long-running task that executes in the background
    """
    import uuid
    from datetime import datetime
    from ..models.folder import Folder
    
    # Validate folder exists by path
    folder = db.query(Folder).filter(Folder.path == request.folder_path).first()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folder {request.folder_path} not found"
        )
    
    # Validate URL format
    try:
        from urllib.parse import urlparse
        parsed_url = urlparse(request.url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("Invalid URL")
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL format, please provide full URL (e.g., https://example.com)"
        )
    
    # Generate task ID
    task_id = f"crawl_{uuid.uuid4().hex[:12]}"
    
    # Create crawl task record
    crawl_task = CrawlTask(
        task_id=task_id,
        status=CrawlTaskStatus.PENDING,
        url=request.url,
        depth=request.depth,
        folder_path=folder.path,
        include_images=1 if request.include_images else 0,
        follow_external_links=1 if request.follow_external_links else 0,
        respect_robots_txt=1 if request.respect_robots_txt else 0,
        total_pages=estimate_page_count(request.url, request.depth),
        started_at=datetime.now(),
        created_by=current_user.username if current_user else "system",
        current_status="Task created, waiting to start..."
    )
    
    db.add(crawl_task)
    db.commit()
    db.refresh(crawl_task)
    
    logger.info(f"Created crawl task: {task_id}, URL: {request.url}, folder: {folder.name}")
    
    # Start background crawl task
    background_tasks.add_task(
        crawl_website_background,
        task_id=task_id,
        url=request.url,
        depth=request.depth,
        folder_path=folder.path,
        include_images=request.include_images,
        follow_external_links=request.follow_external_links,
        respect_robots_txt=request.respect_robots_txt,
        db=db
    )
    
    return WebsiteCrawlResponse(
        task_id=task_id,
        status="pending",
        url=request.url,
        depth=request.depth,
        estimated_pages=estimate_page_count(request.url, request.depth),
        started_at=datetime.now(),
        message="Website crawl task started, will run in background"
    )


@router.get("/crawl-tasks", response_model=WebsiteCrawlTaskList)
async def get_crawl_tasks(
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get list of all website crawl tasks
    
    Supports pagination and status filtering
    """
    from datetime import datetime
    from sqlalchemy import desc
    
    # Build query
    query = db.query(CrawlTask)
    
    # Status filter
    if status_filter:
        try:
            status_enum = CrawlTaskStatus(status_filter)
            query = query.filter(CrawlTask.status == status_enum)
        except ValueError:
            return WebsiteCrawlTaskList(
                tasks=[],
                total=0,
                pending=0,
                active=0,
                completed=0,
                failed=0
            )
    
    # Get total count (for pagination)
    total = query.count()
    
    # Apply pagination and sorting (newest first)
    tasks = query.order_by(desc(CrawlTask.created_at)).offset(offset).limit(limit).all()
    
    # Convert to response model
    task_responses = []
    for task in tasks:
        status_value = task.status.value if hasattr(task.status, 'value') else str(task.status)
        
        task_responses.append(WebsiteCrawlStatus(
            task_id=task.task_id,
            status=status_value,
            url=task.url,
            depth=task.depth,
            pages_crawled=task.pages_crawled or 0,
            pages_processed=task.pages_processed or 0,
            images_crawled=task.images_crawled or 0,
            errors=task.errors or [],
            started_at=task.started_at if task.started_at else task.created_at,
            updated_at=task.updated_at or datetime.now(),
            estimated_completion=None
        ))
    
    # Count tasks by status
    stats_query = db.query(CrawlTask.status, func.count(CrawlTask.id).label('count'))
    stats = {}
    if not status_filter:
        stats = {row[0]: row[1] for row in stats_query.group_by(CrawlTask.status).all()}
    
    pending_count = stats.get(CrawlTaskStatus.PENDING, 0)
    active_count = stats.get(CrawlTaskStatus.CRAWLING, 0) + stats.get(CrawlTaskStatus.PROCESSING, 0)
    completed_count = stats.get(CrawlTaskStatus.COMPLETED, 0)
    failed_count = stats.get(CrawlTaskStatus.FAILED, 0) + stats.get(CrawlTaskStatus.CANCELLED, 0)
    
    return WebsiteCrawlTaskList(
        tasks=task_responses,
        total=total,
        pending=pending_count,
        active=active_count,
        completed=completed_count,
        failed=failed_count
    )


@router.get("/crawl-status/{task_id}", response_model=WebsiteCrawlStatus)
async def get_crawl_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Get website crawl task status
    """
    crawl_task = db.query(CrawlTask).filter(CrawlTask.task_id == task_id).first()
    if not crawl_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    status_value = crawl_task.status.value if hasattr(crawl_task.status, 'value') else str(crawl_task.status)
    
    return WebsiteCrawlStatus(
        task_id=crawl_task.task_id,
        status=status_value,
        url=crawl_task.url,
        depth=crawl_task.depth,
        pages_crawled=crawl_task.pages_crawled or 0,
        pages_processed=crawl_task.pages_processed or 0,
        images_crawled=crawl_task.images_crawled or 0,
        errors=crawl_task.errors or [],
        started_at=crawl_task.started_at if crawl_task.started_at else crawl_task.created_at,
        updated_at=crawl_task.updated_at or crawl_task.created_at,
        estimated_completion=None
    )


@router.post("/cancel-task/{task_id}", response_model=WebsiteCrawlStatus)
async def cancel_crawl_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Cancel a crawl task
    
    Supports canceling pending tasks.
    Already running/crawling tasks are marked as cancelled,
    the background crawler will stop on next status check.
    """
    crawl_task = db.query(CrawlTask).filter(CrawlTask.task_id == task_id).first()
    if not crawl_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    if crawl_task.status in [CrawlTaskStatus.COMPLETED, CrawlTaskStatus.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task has already ended ({crawl_task.status.value}), cannot cancel"
        )
    
    crawl_task.status = CrawlTaskStatus.CANCELLED
    db.commit()
    
    status_value = crawl_task.status.value if hasattr(crawl_task.status, 'value') else str(crawl_task.status)
    return WebsiteCrawlStatus(
        task_id=crawl_task.task_id,
        status=status_value,
        url=crawl_task.url,
        depth=crawl_task.depth,
        pages_crawled=crawl_task.pages_crawled or 0,
        pages_processed=crawl_task.pages_processed or 0,
        images_crawled=crawl_task.images_crawled or 0,
        errors=crawl_task.errors or [],
        started_at=crawl_task.started_at or crawl_task.created_at,
        updated_at=crawl_task.updated_at or crawl_task.created_at,
        estimated_completion=None
    )


def crawl_website_background(
    task_id: str,
    url: str,
    depth: int,
    folder_path: str,
    include_images: bool,
    follow_external_links: bool,
    respect_robots_txt: bool,
    db: Session
):
    """
    Background crawl task function
    """
    from datetime import datetime
    
    logger.info(f"Starting website crawl: {url}, depth: {depth}, task ID: {task_id}")
    
    try:
        # Update task status to crawling
        crawl_task = db.query(CrawlTask).filter(CrawlTask.task_id == task_id).first()
        if crawl_task:
            crawl_task.status = CrawlTaskStatus.CRAWLING
            crawl_task.current_status = "Starting website crawl..."
            crawl_task.started_at = datetime.now()
            db.commit()
        
        # Execute crawl task
        result = crawl_website_task(
            task_id=task_id,
            url=url,
            depth=depth,
            folder_path=folder_path,
            include_images=include_images,
            follow_external_links=follow_external_links,
            respect_robots_txt=respect_robots_txt,
            db=db
        )
        
        # Update task status
        if crawl_task:
            if result.get('success'):
                crawl_task.status = CrawlTaskStatus.COMPLETED
                crawl_task.current_status = "Crawl completed"
                crawl_task.stats = result.get('stats', {})
                crawl_task.pages_crawled = result.get('stats', {}).get('total_pages', 0)
                crawl_task.pages_processed = result.get('stats', {}).get('successful_pages', 0)
                crawl_task.images_crawled = result.get('stats', {}).get('total_images', 0)
                crawl_task.progress = 100
                crawl_task.completed_at = datetime.now()
                logger.info(f"Website crawl completed: {url}, task ID: {task_id}, stats: {result.get('stats', {})}")
            else:
                crawl_task.status = CrawlTaskStatus.FAILED
                crawl_task.current_status = f"Crawl failed: {result.get('error', 'Unknown error')}"
                crawl_task.error_message = result.get('error', 'Unknown error')
                logger.error(f"Website crawl failed: {url}, task ID: {task_id}, error: {result.get('error')}")
            
            db.commit()
            
    except Exception as e:
        logger.error(f"Crawl task execution exception: {task_id}, error: {str(e)}")
        try:
            crawl_task = db.query(CrawlTask).filter(CrawlTask.task_id == task_id).first()
            if crawl_task:
                crawl_task.status = CrawlTaskStatus.FAILED
                crawl_task.current_status = f"Task execution error: {str(e)[:200]}"
                crawl_task.error_message = str(e)
                crawl_task.error_traceback = str(e)
                db.commit()
        except:
            pass


# ===== Sitemap Import =====

def sitemap_import_background(
    task_id: str,
    sitemap_url: str,
    folder_path: str,
    include_images: bool,
    max_depth: int = 0,
    db: Session = None
):
    """
    Background sitemap import task
    """
    from datetime import datetime
    from ..ai.scrapling_crawler import ScraplingCrawler
    
    logger.info(f"Starting Sitemap import: {sitemap_url}, folder path: {folder_path}")
    
    try:
        # Update task status
        crawl_task = db.query(CrawlTask).filter(CrawlTask.task_id == task_id).first()
        if crawl_task:
            crawl_task.status = CrawlTaskStatus.CRAWLING
            crawl_task.current_status = f"Parsing sitemap: {sitemap_url}..."
            crawl_task.started_at = datetime.now()
            db.commit()
        
        # Read crawl depth
        depth = max_depth
        if crawl_task:
            depth = crawl_task.depth if crawl_task.depth is not None else max_depth
        
        # Create crawler and execute sitemap import
        crawler = ScraplingCrawler(db, task_id=task_id, use_stealth=False, use_dynamic=False)
        stats = crawler.crawl_from_sitemap(
            sitemap_url=sitemap_url,
            folder_path=folder_path,
            include_images=include_images,
            max_depth=depth
        )
        
        # Update task status
        if crawl_task:
            crawl_task.status = CrawlTaskStatus.COMPLETED
            crawl_task.current_status = f"Sitemap import complete: {stats.get('successful_pages', 0)} pages imported"
            crawl_task.stats = stats
            crawl_task.pages_crawled = stats.get('total_pages', 0)
            crawl_task.pages_processed = stats.get('successful_pages', 0)
            crawl_task.images_crawled = stats.get('total_images', 0)
            crawl_task.total_pages = stats.get('total_from_sitemap', 0)
            crawl_task.progress = 100
            crawl_task.completed_at = datetime.now()
            logger.info(f"Sitemap import completed: {sitemap_url}, stats: {stats}")
            db.commit()
            
    except Exception as e:
        logger.error(f"Sitemap import failed: {task_id}, error: {str(e)}")
        try:
            crawl_task = db.query(CrawlTask).filter(CrawlTask.task_id == task_id).first()
            if crawl_task:
                crawl_task.status = CrawlTaskStatus.FAILED
                crawl_task.current_status = f"Sitemap import failed: {str(e)[:200]}"
                crawl_task.error_message = str(e)
                crawl_task.error_traceback = str(e)
                db.commit()
        except:
            pass


@router.post("/crawl-from-sitemap", response_model=SitemapImportResponse)
async def crawl_from_sitemap(
    request: SitemapImportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Import and crawl website content from sitemap.xml
    
    Parse sitemap.xml to get URL list, then crawl each page.
    Supports standard sitemap and sitemap index (auto-recursive parsing of sub-sitemaps).
    """
    import uuid
    from datetime import datetime
    from ..models.folder import Folder
    
    # Validate folder by path
    folder = db.query(Folder).filter(Folder.path == request.folder_path).first()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folder {request.folder_path} not found"
        )
    
    # Quick parse sitemap to estimate URL count
    total_urls = None
    try:
        urls = parse_sitemap_urls(request.sitemap_url, max_urls=100)
        total_urls = max(len(urls), 0) if urls else None
    except:
        pass
    
    # Generate task ID
    task_id = f"sitemap_{uuid.uuid4().hex[:12]}"
    
    # Create crawl task record
    crawl_task = CrawlTask(
        task_id=task_id,
        status=CrawlTaskStatus.PENDING,
        url=request.sitemap_url,
        depth=request.depth,
        folder_path=folder.path,
        include_images=1 if request.include_images else 0,
        follow_external_links=0,
        respect_robots_txt=1,
        total_pages=total_urls or 0,
        started_at=datetime.now(),
        created_by=current_user.username if current_user else "system",
        current_status="Sitemap import task created, parsing sitemap..."
    )
    
    db.add(crawl_task)
    db.commit()
    db.refresh(crawl_task)
    
    logger.info(f"Created Sitemap import task: {task_id}, URL: {request.sitemap_url}")
    
    # Start background task
    background_tasks.add_task(
        sitemap_import_background,
        task_id=task_id,
        sitemap_url=request.sitemap_url,
        folder_path=folder.path,
        include_images=request.include_images,
        max_depth=request.depth,
        db=db
    )
    
    return SitemapImportResponse(
        task_id=task_id,
        status="pending",
        sitemap_url=request.sitemap_url,
        total_urls=total_urls,
        started_at=datetime.now(),
        message="Sitemap import task started, will run in background"
    )


def estimate_page_count(url: str, depth: int) -> int:
    """Estimate page count (simple implementation)"""
    base_pages = 10
    multiplier = 5 ** (depth - 1)
    return min(base_pages * multiplier, 1000)
