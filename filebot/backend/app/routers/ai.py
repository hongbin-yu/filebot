"""
AI功能路由
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import logging

from ..db.database import get_db
from ..models.document import Document
from ..models.user import User
from ..models.crawl_task import CrawlTask
from ..schemas.ai import (
    AIClassifyRequest, AIClassifyResponse, AICategoryResult,
    WebsiteCrawlRequest, WebsiteCrawlResponse, WebsiteCrawlStatus,
    WebsiteCrawlTaskList
)
from ..ai.ai_classifier import classifier, AICategory
from ..ai.website_crawler import crawl_website_task
from ..routers.auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/classify", response_model=AIClassifyResponse)
async def classify_document(
    request: AIClassifyRequest,
    db: Session = Depends(get_db)
):
    """
    分类文档
    
    支持直接提供文本内容或文档ID
    """
    if request.document_id:
        # 通过文档ID分类
        document = db.query(Document).filter(Document.id == request.document_id).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文档 {request.document_id} 不存在"
            )
        
        result = classifier.classify_document(document, db, extract_text=request.extract_text)
        
    elif request.text:
        # 直接分类文本
        result = classifier.classify_text(request.text, model=request.model)
        
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须提供 document_id 或 text"
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
    document_ids: List[str],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    批量分类文档
    
    返回任务ID，实际处理在后台进行
    """
    # 验证文档存在
    documents = db.query(Document).filter(Document.id.in_(document_ids)).all()
    if len(documents) != len(document_ids):
        found_ids = [doc.id for doc in documents]
        missing_ids = set(document_ids) - set(found_ids)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"以下文档不存在: {missing_ids}"
        )
    
    # TODO: 实现后台批量处理
    # 目前先简单同步处理
    results = []
    for document in documents:
        result = classifier.classify_document(document, db)
        results.append(AIClassifyResponse(
            document_id=document.id,
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
    """测试AI服务连接"""
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
            detail="无法连接到Ollama服务，请确保服务正在运行"
        )

@router.get("/categories")
async def get_ai_categories():
    """获取可用的AI分类类别"""
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
    爬取网站内容并导入到指定文件夹
    
    这是一个长时间运行的任务，会在后台执行
    """
    import uuid
    from datetime import datetime
    from ..models.folder import Folder
    from ..models.crawl_task import CrawlTask, CrawlTaskStatus
    
    # 验证文件夹是否存在
    folder = db.query(Folder).filter(Folder.id == request.folder_id).first()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文件夹 {request.folder_id} 不存在"
        )
    
    # 验证URL格式
    try:
        from urllib.parse import urlparse
        parsed_url = urlparse(request.url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("无效的URL")
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的URL格式，请提供完整的URL（如 https://example.com）"
        )
    
    # 生成任务ID
    task_id = f"crawl_{uuid.uuid4().hex[:12]}"
    
    # 创建爬取任务记录
    crawl_task = CrawlTask(
        task_id=task_id,
        status=CrawlTaskStatus.PENDING,
        url=request.url,
        depth=request.depth,
        folder_id=request.folder_id,
        include_images=1 if request.include_images else 0,
        follow_external_links=1 if request.follow_external_links else 0,
        respect_robots_txt=1 if request.respect_robots_txt else 0,
        total_pages=estimate_page_count(request.url, request.depth),
        started_at=datetime.now(),
        created_by=current_user.username if current_user else "system",
        current_status="任务已创建，等待开始..."
    )
    
    db.add(crawl_task)
    db.commit()
    db.refresh(crawl_task)
    
    logger.info(f"创建爬取任务: {task_id}, URL: {request.url}, 文件夹: {folder.name}")
    
    # 启动后台爬取任务
    background_tasks.add_task(
        crawl_website_background,
        task_id=task_id,
        url=request.url,
        depth=request.depth,
        folder_id=request.folder_id,
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
        message="网站爬取任务已开始，将在后台执行"
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
    获取所有网站爬取任务列表
    
    支持分页和状态过滤
    """
    from sqlalchemy import desc
    
    # 构建查询
    query = db.query(CrawlTask)
    
    # 状态过滤
    if status_filter:
        from ..models.crawl_task import CrawlTaskStatus
        try:
            status_enum = CrawlTaskStatus(status_filter)
            query = query.filter(CrawlTask.status == status_enum)
        except ValueError:
            # 如果状态值无效，返回空列表
            return WebsiteCrawlTaskList(
                tasks=[],
                total=0,
                pending=0,
                active=0,
                completed=0,
                failed=0
            )
    
    # 获取总数（用于分页）
    total = query.count()
    
    # 应用分页和排序（最新的在前面）
    tasks = query.order_by(desc(CrawlTask.created_at)).offset(offset).limit(limit).all()
    
    # 转换为响应模型
    task_responses = []
    for task in tasks:
        # 转换状态枚举值为字符串
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
            updated_at=task.updated_at,
            estimated_completion=None
        ))
    
    # 统计各种状态的任务数
    stats_query = db.query(CrawlTask.status, func.count(CrawlTask.id).label('count'))
    if status_filter:
        # 如果已过滤状态，统计就不需要了
        stats = {}
    else:
        stats = {row[0]: row[1] for row in stats_query.group_by(CrawlTask.status).all()}
    
    # 计算各状态数量
    from ..models.crawl_task import CrawlTaskStatus
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
    获取网站爬取任务状态
    """
    # 从数据库获取任务状态
    crawl_task = db.query(CrawlTask).filter(CrawlTask.task_id == task_id).first()
    if not crawl_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 {task_id} 不存在"
        )
    
    # 转换状态枚举值为字符串
    status_value = crawl_task.status.value if hasattr(crawl_task.status, 'value') else str(crawl_task.status)
    
    # 转换为WebsiteCrawlStatus响应
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
        updated_at=crawl_task.updated_at,
        estimated_completion=None  # 可以基于进度计算，但暂时留空
    )

def crawl_website_background(
    task_id: str,
    url: str,
    depth: int,
    folder_id: str,
    include_images: bool,
    follow_external_links: bool,
    respect_robots_txt: bool,
    db: Session
):
    """
    后台爬取网站的任务函数
    """
    from ..models.crawl_task import CrawlTask, CrawlTaskStatus
    from datetime import datetime
    
    logger.info(f"开始爬取网站: {url}, 深度: {depth}, 任务ID: {task_id}")
    
    try:
        # 更新任务状态为爬取中
        crawl_task = db.query(CrawlTask).filter(CrawlTask.task_id == task_id).first()
        if crawl_task:
            crawl_task.status = CrawlTaskStatus.CRAWLING
            crawl_task.current_status = "开始爬取网站..."
            crawl_task.started_at = datetime.now()
            db.commit()
        
        # 调用网站爬取任务
        result = crawl_website_task(
            task_id=task_id,
            url=url,
            depth=depth,
            folder_id=folder_id,
            include_images=include_images,
            follow_external_links=follow_external_links,
            respect_robots_txt=respect_robots_txt,
            db=db
        )
        
        # 更新任务状态
        if crawl_task:
            if result.get('success'):
                crawl_task.status = CrawlTaskStatus.COMPLETED
                crawl_task.current_status = "爬取完成"
                crawl_task.stats = result.get('stats', {})
                crawl_task.pages_crawled = result.get('stats', {}).get('total_pages', 0)
                crawl_task.pages_processed = result.get('stats', {}).get('successful_pages', 0)
                crawl_task.images_crawled = result.get('stats', {}).get('total_images', 0)
                crawl_task.progress = 100
                crawl_task.completed_at = datetime.now()
                logger.info(f"网站爬取完成: {url}, 任务ID: {task_id}, 结果: {result.get('stats', {})}")
            else:
                crawl_task.status = CrawlTaskStatus.FAILED
                crawl_task.current_status = f"爬取失败: {result.get('error', '未知错误')}"
                crawl_task.error_message = result.get('error', '未知错误')
                logger.error(f"网站爬取失败: {url}, 任务ID: {task_id}, 错误: {result.get('error')}")
            
            db.commit()
            
    except Exception as e:
        logger.error(f"爬取任务执行异常: {task_id}, 错误: {str(e)}")
        # 更新任务状态为失败
        try:
            crawl_task = db.query(CrawlTask).filter(CrawlTask.task_id == task_id).first()
            if crawl_task:
                crawl_task.status = CrawlTaskStatus.FAILED
                crawl_task.current_status = f"任务执行异常: {str(e)[:200]}"
                crawl_task.error_message = str(e)
                crawl_task.error_traceback = str(e)
                db.commit()
        except:
            pass  # 忽略更新错误

def estimate_page_count(url: str, depth: int) -> int:
    """预估页面数量（简单实现）"""
    # 简单的估算逻辑
    base_pages = 10
    multiplier = 5 ** (depth - 1)  # 指数增长
    return min(base_pages * multiplier, 1000)  # 限制最大1000页