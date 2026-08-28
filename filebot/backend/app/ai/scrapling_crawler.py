"""
Website crawler based on Scrapling framework
Uses pure path architecture to store files
"""

import logging
import re
import time
import uuid
import warnings
from typing import List, Dict, Any, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, urlunparse
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

# Scrapling imports
from scrapling.fetchers import Fetcher, DynamicFetcher, StealthyFetcher
from scrapling.parser import fromstring

# HTML解析器(用于处理格式错误的HTML)
try:
    from lxml.html.soupparser import fromstring as soupparser_fromstring
    SOUP_PARSER_AVAILABLE = True
except ImportError:
    SOUP_PARSER_AVAILABLE = False
    soupparser_fromstring = None

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False
    BeautifulSoup = None

# FileBot imports
from ..models.document import Document, DocumentType, DocumentStatus, FileType, ConversionStatus
from ..models.folder import Folder
from ..models.app import App
from ..schemas.document import DocumentCreate
from ..core.path_utils import generate_storage_paths, make_filename_safe
from ..core.config import settings

logger = logging.getLogger(__name__)

# 忽略Scrapling的废弃警告
warnings.filterwarnings("ignore", message=".*deprecated.*")
warnings.filterwarnings("ignore", message=".*v0.3.*")

# ===== 爬虫去重/过滤配置 =====

# 系统/模板页面列表 - 这些页面的URL路径中出现以下片段时跳过爬取
SYSTEM_PAGE_FRAGMENTS = {
    'footer', 'header', 'mustache-templates', 'standard-page-template', 'template-container',
    '404', 'search', 'sitemap', 'test', 'test-create-post', 'test-filepath-2', 'test-contact-page',
    'mobile', 'index', 'whats-new', 'government-services-portal', 'privacy-policy-compliance',
    'administrative-tribunals-support-service', 'canada-water-agency',
    'canadian-coast-guard', 'chief-military-judge', 'defence-investment-agency',
    'defence-research-development', 'democratic-institutions', 'economic-development-quebec-regions',
    'farm-products-council', 'heritage-information-network', 'impact-assessment-agency',
    'independent-review-panel-defence-acquisition', 'indigenous-northern-affairs',
    'intelligence-commissioner', 'law-commission-canada', 'leader-government-house-commons',
    'library-archives', 'management-advisory-board-rcmp', 'military-grievances-external-review',
    'military-police-complaints', 'national-battlefields-commission', 'national-film-board',
    'national-seniors-council', 'northern-pipeline-agency',
    'occupational-health-and-safety-tribunal-canada',
    'office-federal-ombudsperson-victims-crime', 'ombudsman-national-defence-forces',
    'pacific-economic-development', 'patented-medicine-prices-review', 'polar-knowledge',
    'prairies-economic-development', 'procurement-ombudsman',
    'rcmp-external-review-committee',
    'secretariat-national-security-intelligence-committee-parliamentarians',
    'security-intelligence-service', 'shared-services', 'special-operations-forces-command',
    'taxpayers-ombudsperson', 'transportation-agency', 'transportation-safety-board',
    'women-gender-equality', 'one-canadian-economy',
}

# 编号副本正则:services-4, mobile-3 等历史残留
NUMBERED_DUPLICATE_RE = re.compile(r'^(.+)-\d+$')


class ScraplingCrawler:
    """Website crawler based on Scrapling"""

    def __init__(
        self,
        db: Session,
        task_id: str = None,
        use_stealth: bool = False,
        use_dynamic: bool = False,
        max_concurrent: int = 5
    ):
        """
        Initialize Scrapling crawler

        Args:
            db: Database session
            task_id: Crawl task ID (optional)
            use_stealth: Whether to use stealth mode (bypass anti-crawling)
            use_dynamic: Whether to use dynamic rendering (for JavaScript)
            max_concurrent: Maximum concurrent requests
        """
        self.db = db
        self.task_id = task_id

        # 选择fetcher类型
        if use_dynamic:
            self.fetcher = DynamicFetcher()
            self.fetcher_type = 'dynamic'
            logger.info(f"使用DynamicFetcher(动态渲染)")
        elif use_stealth:
            self.fetcher = StealthyFetcher()
            self.fetcher_type = 'stealth'
            logger.info(f"使用StealthyFetcher(隐身模式)")
        else:
            self.fetcher = Fetcher()
            self.fetcher_type = 'standard'
            logger.info(f"使用Fetcher(标准模式)")

        # 状态跟踪
        self.visited_urls: Set[str] = set()
        self.stats: Dict[str, Any] = {
            'total_pages': 0,
            'successful_pages': 0,
            'failed_pages': 0,
            'total_images': 0,
            'downloaded_images': 0,
            'failed_images': 0,
            'start_time': time.time()
        }

    def _fetch_url(self, url: str):
        """
        使用适当的fetcher获取URL内容

        Args:
            url: 要获取的URL

        Returns:
            Response对象或None
        """
        try:
            # 根据fetcher类型选择正确的方法
            if self.fetcher_type == 'dynamic' or self.fetcher_type == 'stealth':
                # DynamicFetcher和StealthyFetcher使用fetch()方法
                if hasattr(self.fetcher, 'fetch'):
                    return self.fetcher.fetch(url)
                elif hasattr(self.fetcher, 'get'):
                    # 回退到get()方法
                    return self.fetcher.get(url)
            else:
                # 标准Fetcher使用get()方法
                if hasattr(self.fetcher, 'get'):
                    return self.fetcher.get(url)
                elif hasattr(self.fetcher, 'fetch'):
                    # 回退到fetch()方法
                    return self.fetcher.fetch(url)

            # 如果都没有,尝试通用方法
            logger.warning(f"未知的fetcher API,fetcher类型: {self.fetcher_type}")
            return None

        except Exception as e:
            logger.error(f"获取URL失败: {url}, 错误: {str(e)}")
            return None

    def _parse_html(self, html_content: str):
        """
        尝试多种解析器解析HTML,处理格式错误的HTML

        Args:
            html_content: HTML字符串

        Returns:
            lxml.html.HtmlElement对象或None
        """
        if not html_content or len(html_content.strip()) == 0:
            logger.warning("HTML内容为空")
            return None

        # 尝试1: 使用标准Scrapling解析器
        try:
            soup = fromstring(html_content)
            logger.warning("✅ 使用标准Scrapling解析器成功")
            return soup
        except Exception as e1:
            logger.warning(f"❌ 标准解析器失败: {str(e1)[:100]}")

        # 尝试2: 使用soupparser(更宽松的解析器)
        if SOUP_PARSER_AVAILABLE and soupparser_fromstring:
            try:
                soup = soupparser_fromstring(html_content)
                logger.warning("✅ 使用soupparser解析器成功")
                return soup
            except Exception as e2:
                logger.warning(f"❌ soupparser解析器失败: {str(e2)[:100]}")

        # 尝试3: 使用BeautifulSoup(最宽松)
        if BEAUTIFULSOUP_AVAILABLE and BeautifulSoup:
            try:
                # BeautifulSoup返回不同的对象,需要适配XPath调用
                # 这里返回BeautifulSoup对象,后续需要调整XPath调用
                soup = BeautifulSoup(html_content, 'html.parser')
                logger.warning("✅ 使用BeautifulSoup解析器成功(注意:XPath不可用)")
                return soup
            except Exception as e3:
                logger.warning(f"❌ BeautifulSoup解析器失败: {str(e3)[:100]}")

        logger.error("❌ 所有HTML解析器都失败了")
        return None

    def _update_task_status(self, **kwargs):
        """更新爬取任务状态(与旧系统兼容)"""
        if not self.task_id:
            return

        try:
            from ..models.crawl_task import CrawlTask, CrawlTaskStatus

            crawl_task = self.db.query(CrawlTask).filter(CrawlTask.task_id == self.task_id).first()
            if not crawl_task:
                return

            # 更新字段
            if 'status' in kwargs:
                status = kwargs['status']
                crawl_task.status = CrawlTaskStatus[status.upper()] if hasattr(CrawlTaskStatus, status.upper()) else status

            if 'current_status' in kwargs:
                crawl_task.current_status = kwargs['current_status'][:500]

            if 'pages_crawled' in kwargs:
                crawl_task.pages_crawled = kwargs['pages_crawled']

            if 'pages_processed' in kwargs:
                crawl_task.pages_processed = kwargs['pages_processed']

            if 'images_crawled' in kwargs:
                crawl_task.images_crawled = kwargs['images_crawled']

            if 'current_url' in kwargs:
                crawl_task.current_url = kwargs['current_url'][:2000]

            if 'stats' in kwargs:
                crawl_task.stats = kwargs['stats']

            # 计算进度
            if 'progress' in kwargs:
                crawl_task.progress = kwargs['progress']
            elif crawl_task.total_pages > 0 and 'pages_crawled' in kwargs:
                crawl_task.progress = min(100, int((kwargs['pages_crawled'] / crawl_task.total_pages) * 100))

            # 更新时间戳
            from datetime import datetime
            crawl_task.updated_at = datetime.now()

            self.db.commit()

        except Exception as e:
            logger.error(f"更新任务状态失败: {self.task_id}, 错误: {str(e)}")

    def create_document_with_path(
        self,
        document_data: DocumentCreate,
        folder_path: str,
        content: Any = None,
        is_binary: bool = False
    ) -> Document:
        """
        使用纯path架构创建文档

        Args:
            document_data: 文档创建数据
            folder_path: 目标文件夹路径
            content: 文件内容(文本或二进制)
            is_binary: 是否为二进制内容(默认False,即文本)

        Returns:
            创建的文档对象
        """
        try:
            # 获取文件夹和应用信息
            folder = self.db.query(Folder).filter(Folder.path == folder_path).first()
            if not folder:
                logger.error(f"文件夹不存在: {folder_path}")
                raise ValueError(f"文件夹 {folder_path} 不存在")

            app = self.db.query(App).filter(App.id == folder.app_id).first()
            if not app:
                logger.error(f"应用不存在: {folder.app_id}")
                raise ValueError(f"应用 {folder.app_id} 不存在")

            logger.info(f"create_document_with_path: 文件夹={folder.name}({folder_path}), 应用={app.name}({app.id})")
            logger.info(f"create_document_with_path: 文档标题={document_data.title[:50]}")

            # 获取应用slug和文件夹路径
            app_slug = app.slug or to_slug(app.name)
            folder_path = folder.path if folder.path else f"/{folder.name}"

            # 生成安全的文件名
            original_filename = document_data.original_filename or "untitled.html"
            safe_filename = make_filename_safe(original_filename)
            data_root = Path(settings.DATA_ROOT)

            # ====== PATH-BASED DEDUP: Check DB before filesystem numbering ======
            # Compute the expected URL path without generate_unique_filename's -N suffix
            # Replicate the app_slug dedup logic from generate_storage_paths
            clean_folder = folder_path
            if clean_folder.startswith(f'/{app_slug}'):
                clean_folder = clean_folder[len(app_slug)+1:]
                if clean_folder and not clean_folder.startswith('/'):
                    clean_folder = '/' + clean_folder
            expected_url_path = f"/{app_slug}{clean_folder}/{safe_filename}"

            # 移除 .html 后缀:URL 路径应使用干净路径(不含扩展名)
            # 磁盘文件(storage_path/stored_filename)仍保留 .html
            expected_url_path = re.sub(r'\.html?$', '', expected_url_path)

            # Check DB for existing document at this exact deterministic path
            existing_by_path = self.db.query(Document).filter(
                Document.path == expected_url_path
            ).first()

            if existing_by_path:
                logger.info(f"Found document with same path, updating instead of creating numbered file: path={expected_url_path}, id={existing_by_path.path}")

                # Reuse existing document's storage info
                final_filename = existing_by_path.stored_filename or safe_filename
                url_path = existing_by_path.path

                if existing_by_path.storage_path:
                    storage_path = data_root / existing_by_path.storage_path
                else:
                    storage_path = data_root / f"{app_slug}{clean_folder}/{final_filename}"

                # Ensure directory exists
                storage_path.parent.mkdir(parents=True, exist_ok=True)

                # Determine content to write
                content_to_write = content
                if content_to_write is None:
                    content_to_write = "" if not is_binary else b""
                if not content_to_write and not is_binary and document_data.document_metadata:
                    if document_data.file_type == FileType.HTML:
                        content_to_write = document_data.document_metadata.get('original_html') or \
                                         document_data.document_metadata.get('html_content') or \
                                         document_data.document_metadata.get('extracted_text', '') or ""

                # Write content to existing file (overwrite)
                if is_binary:
                    with open(storage_path, 'wb') as f:
                        f.write(content_to_write)
                else:
                    with open(storage_path, 'w', encoding='utf-8') as f:
                        f.write(content_to_write)

                file_size = storage_path.stat().st_size

                # Update existing document metadata
                existing_by_path.title = document_data.title
                existing_by_path.description = document_data.description
                existing_by_path.original_filename = original_filename
                existing_by_path.stored_filename = final_filename
                existing_by_path.storage_path = str(storage_path.relative_to(data_root))
                existing_by_path.file_type = FileType(document_data.file_type.value)
                existing_by_path.file_size = file_size
                existing_by_path.mime_type = document_data.mime_type
                existing_by_path.document_metadata = document_data.document_metadata or {}
                existing_by_path.updated_at = func.now()
                existing_by_path.updated_by = str(document_data.uploaded_by)

                if existing_by_path.conversion_status == ConversionStatus.FAILED:
                    existing_by_path.conversion_status = ConversionStatus.PENDING

                self.db.commit()
                self.db.refresh(existing_by_path)
                logger.info(f"Updated document by path: ID={existing_by_path.path}, path={url_path}")
                return existing_by_path

            # ====== URL-BASED DEDUP (check before filesystem numbering) ======
            # Search across ALL folders for existing doc with the same URL
            # This prevents generating -N suffix duplicates when re-crawling
            existing_by_url = None
            normalized_url = None
            if document_data.document_metadata:
                normalized_url = document_data.document_metadata.get('url')

            if normalized_url:
                existing_by_url = self.db.query(Document).filter(
                    Document.document_metadata.op('->>')('url') == normalized_url
                ).first()

                if existing_by_url:
                    logger.info(f"Found existing document by URL, updating instead of creating numbered file: URL={normalized_url}, existing_path={existing_by_url.path}, target_path={expected_url_path}")

                    # Determine storage info - reuse existing or use the correct path
                    final_filename = existing_by_url.stored_filename or safe_filename

                    if existing_by_url.storage_path:
                        storage_path = data_root / existing_by_url.storage_path
                    else:
                        storage_path = data_root / f"{app_slug}{clean_folder}/{final_filename}"

                    # If path has changed, clean up old file
                    old_storage = data_root / existing_by_url.storage_path if existing_by_url.storage_path else None

                    # Use expected (correct) URL path
                    url_path = expected_url_path

                    # Ensure target directory exists
                    storage_path.parent.mkdir(parents=True, exist_ok=True)

                    # Determine content to write
                    content_to_write = content
                    if content_to_write is None:
                        content_to_write = "" if not is_binary else b""
                    if not content_to_write and not is_binary and document_data.document_metadata:
                        if document_data.file_type == FileType.HTML:
                            content_to_write = document_data.document_metadata.get('original_html') or \
                                             document_data.document_metadata.get('html_content') or \
                                             document_data.document_metadata.get('extracted_text', '') or ""

                    # Write content to storage file
                    if is_binary:
                        with open(storage_path, 'wb') as f:
                            f.write(content_to_write)
                    else:
                        with open(storage_path, 'w', encoding='utf-8') as f:
                            f.write(content_to_write)

                    file_size = storage_path.stat().st_size

                    # Clean up old storage file if different from new
                    if old_storage and old_storage.exists() and old_storage != storage_path:
                        try:
                            old_storage.unlink()
                            logger.info(f"Cleaned up old storage file: {old_storage}")
                        except Exception as e:
                            logger.warning(f"Could not clean up old storage file {old_storage}: {e}")

                    # Remove old numbered duplicate files if the path changed
                    if existing_by_url.path != url_path:
                        # Clean up old file on filesystem with the old filename stem pattern
                        old_dir = (data_root / existing_by_url.storage_path).parent if existing_by_url.storage_path else storage_path.parent
                        old_stem = Path(existing_by_url.stored_filename or '').stem
                        for old_file in old_dir.glob(f"{old_stem}-[0-9]*.html"):
                            try:
                                old_file.unlink()
                                logger.info(f"Cleaned up old numbered file: {old_file}")
                            except Exception as e:
                                logger.warning(f"Could not clean up {old_file}: {e}")

                    # Update existing document record
                    existing_by_url.title = document_data.title
                    existing_by_url.description = document_data.description
                    existing_by_url.original_filename = original_filename
                    existing_by_url.stored_filename = final_filename
                    existing_by_url.storage_path = str(storage_path.relative_to(data_root))
                    existing_by_url.path = url_path
                    existing_by_url.parent_folder_path = folder_path
                    existing_by_url.file_type = FileType(document_data.file_type.value)
                    existing_by_url.file_size = file_size
                    existing_by_url.mime_type = document_data.mime_type
                    existing_by_url.document_metadata = document_data.document_metadata or {}
                    existing_by_url.updated_at = func.now()
                    existing_by_url.updated_by = str(document_data.uploaded_by)

                    if existing_by_url.conversion_status == ConversionStatus.FAILED:
                        existing_by_url.conversion_status = ConversionStatus.PENDING

                    self.db.commit()
                    self.db.refresh(existing_by_url)
                    logger.info(f"Updated document by URL: ID={existing_by_url.path}, path={url_path}")
                    return existing_by_url

            # ====== Check for orphaned files on filesystem (no DB record but file exists) ======
            expected_storage_path = data_root / f"{app_slug}{clean_folder}" / safe_filename
            if expected_storage_path.exists():
                logger.info(f"Found orphaned file at {expected_storage_path}, will reuse path instead of creating numbered version")
                storage_path = expected_storage_path
                url_path = expected_url_path
                final_filename = safe_filename
            else:
                # ====== No collision: create document (without numbered suffix) ======
                # Use deterministic path (same as expected_url_path)
                storage_path = data_root / f"{app_slug}{clean_folder}" / safe_filename
                url_path = expected_url_path
                final_filename = safe_filename
                storage_path.parent.mkdir(parents=True, exist_ok=True)

            # Ensure directory exists
            storage_path.parent.mkdir(parents=True, exist_ok=True)

            # Determine content to write
            content_to_write = content
            if content_to_write is None:
                content_to_write = "" if not is_binary else b""

            if not content_to_write and not is_binary and document_data.document_metadata:
                if document_data.file_type == FileType.HTML:
                    content_to_write = document_data.document_metadata.get('original_html') or \
                                     document_data.document_metadata.get('html_content') or \
                                     document_data.document_metadata.get('extracted_text', '') or ""

            # Write file
            if is_binary:
                with open(storage_path, 'wb') as f:
                    f.write(content_to_write)
            else:
                with open(storage_path, 'w', encoding='utf-8') as f:
                    f.write(content_to_write)

            file_size = storage_path.stat().st_size

            # Create new document record (pure path-based PK)
            document = Document(
                title=document_data.title,
                description=document_data.description,
                original_filename=original_filename,
                stored_filename=final_filename,  # 只存储文件名,不包含路径
                storage_path=str(storage_path.relative_to(data_root)),  # 相对路径
                path=url_path,
                parent_folder_path=folder_path,  # 父文件夹路径
                file_type=FileType(document_data.file_type.value),
                file_size=file_size,
                mime_type=document_data.mime_type,
                folder_path=folder_path,
                document_metadata=document_data.document_metadata or {},
                status=DocumentStatus.ACTIVE,
                uploaded_by=str(document_data.uploaded_by),
                conversion_status=ConversionStatus.PENDING
            )

            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)

            logger.info(f"创建文档成功(纯path架构): ID={document.path}, 路径={storage_path}")
            return document

        except Exception as e:
            logger.error(f"创建文档失败: {str(e)}", exc_info=True)
            self.db.rollback()
            raise

    def crawl(
        self,
        url: str,
        depth: int,
        folder_path: str,
        include_images: bool = True,
        follow_external_links: bool = False,
        respect_robots_txt: bool = True
    ) -> Dict[str, Any]:
        """
        爬取网站(主入口点)

        Args:
            url: 起始URL
            depth: 爬取深度
            folder_path: 目标文件夹路径
            include_images: 是否包含图像
            follow_external_links: 是否跟踪外部链接
            respect_robots_txt: 是否遵守robots.txt

        Returns:
            爬取结果统计
        """
        # 验证文件夹
        folder = self.db.query(Folder).filter(Folder.path == folder_path).first()
        if not folder:
            raise ValueError(f"文件夹 {folder_path} 不存在")

        logger.info(f"开始Scrapling爬取: {url}, 深度: {depth}, 文件夹: {folder.name}")

        # 存储根文件夹路径,用于图片文件夹创建
        self.root_folder_path = folder_path

        # 更新任务状态
        self._update_task_status(
            status="crawling",
            current_status=f"Starting crawl: {url}",
            current_url=url
        )

        # 初始化统计
        self.stats = {
            'total_pages': 0,
            'successful_pages': 0,
            'failed_pages': 0,
            'total_images': 0,
            'downloaded_images': 0,
            'failed_images': 0,
            'start_time': time.time(),
            'urls': []
        }

        try:
            # 开始爬取
            self._crawl_recursive(
                url=url,
                base_url=self._get_base_url(url),
                current_depth=0,
                max_depth=depth,
                folder_path=folder_path,
                include_images=include_images,
                follow_external_links=follow_external_links
            )

            # EN↔FR 页面配对:只在 canada.ca 站点执行,且限定当前文件夹
            if url.startswith('https://www.canada.ca') or url.startswith('http://www.canada.ca'):
                paired_count = self._pair_en_fr_pages(folder_path=folder_path)
                if paired_count > 0:
                    logger.info(f"EN↔FR 配对完成: 建立了 {paired_count} 个页面的语言关联")
            else:
                logger.info(f"非 canada.ca 站点,跳过 EN↔FR 配对")

            # 更新最终状态
            self.stats['end_time'] = time.time()
            self.stats['duration'] = self.stats['end_time'] - self.stats['start_time']

            self._update_task_status(
                status="completed",
                current_status=f"Crawl complete: {self.stats['successful_pages']} pages successful",
                pages_crawled=self.stats['total_pages'],
                pages_processed=self.stats['successful_pages'],
                images_crawled=self.stats['total_images'],
                stats=self.stats
            )

            logger.info(f"Scrapling爬取完成: {self.stats}")
            return self.stats

        except Exception as e:
            logger.error(f"爬取过程中发生错误: {str(e)}", exc_info=True)
            self.stats['error'] = str(e)

            self._update_task_status(
                status="failed",
                current_status=f"Crawl failed: {str(e)[:100]}",
                stats=self.stats
            )
            raise

    def _get_base_url(self, url: str) -> str:
        """从URL提取基础URL"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _crawl_recursive(
        self,
        url: str,
        base_url: str,
        current_depth: int,
        max_depth: int,
        folder_path: str,
        include_images: bool,
        follow_external_links: bool
    ):
        """递归爬取URL(Scrapling实现)"""
        # 深度限制检查
        if current_depth > max_depth:
            return

        # 检查是否已访问
        if url in self.visited_urls:
            return

        # 标记为已访问
        self.visited_urls.add(url)
        self.stats['total_pages'] += 1

        logger.info(f"Scrapling爬取: {url} (深度 {current_depth}/{max_depth})")

        # 检查是否是已知二进制文件扩展名(PDF等),直接下载保存为二进制文档
        BINARY_EXTENSION_MAP = {
            '.pdf':  ('application/pdf',  'PDF'),
            '.doc':  ('application/msword',  'DOC'),
            '.docx': ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'DOCX'),
            '.xls':  ('application/vnd.ms-excel',  'XLS'),
            '.xlsx': ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'XLSX'),
            '.ppt':  ('application/vnd.ms-powerpoint',  'PPT'),
            '.pptx': ('application/vnd.openxmlformats-officedocument.presentationml.presentation', 'PPTX'),
            '.zip':  ('application/zip',  'ZIP'),
        }
        url_lower = url.lower()
        parsed_url = urlparse(url)
        has_binary_ext = False
        binary_mime = None
        binary_ext_found = None
        for ext, (mime, _) in BINARY_EXTENSION_MAP.items():
            if url_lower.endswith(ext) or url_lower.rstrip('/').endswith(ext):
                has_binary_ext = True
                binary_mime = mime
                binary_ext_found = ext
                break

        if has_binary_ext:
            logger.info(f"检测到二进制文件: {url} (类型: {binary_mime})")
            try:
                response = self._fetch_url(url)
                if response and response.status == 200:
                    # 获取二进制内容
                    binary_content = None
                    if hasattr(response, 'content'):
                        binary_content = response.content
                    elif hasattr(response, 'body'):
                        binary_content = response.body
                    elif hasattr(response, 'read'):
                        binary_content = response.read()
                    elif hasattr(response, 'raw'):
                        binary_content = response.raw.read() if callable(response.raw.read) else response.raw
                    else:
                        # 回退:尝试获取原生 Scrapling response 的原始字节
                        try:
                            binary_content = bytes(response)
                        except:
                            binary_content = None

                    if binary_content:
                        self._save_binary_document(url, binary_content, binary_mime, binary_ext_found, folder_path)
                        self.stats['total_pages'] += 1  # 已包含在 visited_urls 之前的计数中
                        return
                    else:
                        logger.warning(f"无法获取二进制内容: {url}")
                else:
                    status = response.status if response else "无响应"
                    logger.warning(f"二进制文件请求失败: {url}, 状态码: {status}")
            except Exception as e:
                logger.error(f"下载二进制文件失败: {url}, 错误: {e}")
            self.stats['failed_pages'] += 1
            return

        # 系统/模板页面过滤:检查URL路径段是否匹配跳过清单
        normalized_url = normalize_canada_url(url)
        parsed_url = urlparse(normalized_url)
        path_segments = [s for s in parsed_url.path.strip('/').split('/') if s]
        for segment in path_segments:
            # 移除 .html 后再检查
            clean_seg = re.sub(r'\.html?$', '', segment, flags=re.IGNORECASE)
            if clean_seg in SYSTEM_PAGE_FRAGMENTS:
                logger.info(f"跳过系统/模板页面: {url} (匹配: {clean_seg})")
                self.stats['failed_pages'] += 1  # 统计为已处理但不爬取
                return

        # ====== URL DEDUP: 检查DB中是否已存在该URL的文档 ======
        # 如果已存在,跳过爬取(避免重新下载已导入的页面)
        existing_doc = self.db.query(Document).filter(
            Document.document_metadata.op('->>')('url') == normalized_url
        ).first()
        if existing_doc:
            logger.info(f"⏭️ 跳过已存在的页面: {url} (文档路径: {existing_doc.path})")
            # 不增加total_pages计数(已计入首次爬取)
            self.stats['total_pages'] -= 1  # 前面已+1,这里抵消
            self.stats['urls'].append({
                'url': url,
                'title': existing_doc.title or url,
                'status': 'skipped',
                'document_id': existing_doc.path
            })
            # 仍然需要提取子链接进行递归爬取(如果depth允许)
            # 读取已保存的HTML以提取子链接
            try:
                from ..core.config import settings
                from pathlib import Path
                data_root = Path(settings.DATA_ROOT)
                if existing_doc.storage_path:
                    saved_path = data_root / existing_doc.storage_path
                    if saved_path.exists():
                        saved_html = saved_path.read_text(encoding='utf-8')
                        # 解析已保存HTML以提取子链接
                        saved_soup = self._parse_html(saved_html)
                        if saved_soup and current_depth < max_depth:
                            internal_links = self._extract_internal_links(saved_soup, url, base_url)
                            for link in internal_links:
                                if follow_external_links or self._is_internal_link(link, base_url):
                                    self._crawl_recursive(
                                        url=link,
                                        base_url=base_url,
                                        current_depth=current_depth + 1,
                                        max_depth=max_depth,
                                        folder_path=folder_path,
                                        include_images=include_images,
                                        follow_external_links=follow_external_links
                                    )
            except Exception as e:
                logger.warning(f"从已保存页面提取子链接失败: {e}")
            return

        # 定期更新任务状态
        if self.stats['total_pages'] % 10 == 0:
            self._update_task_status(
                current_status=f"Crawling: {url[:100]}...",
                current_url=url,
                pages_crawled=self.stats['total_pages'],
                pages_processed=self.stats['successful_pages'],
                images_crawled=self.stats['total_images']
            )

        try:
            # 使用Scrapling fetcher获取页面
            response = self._fetch_url(url)

            if not response or response.status != 200:
                status_code = response.status if response else "无响应"
                logger.warning(f"页面请求失败: {url}, 状态码: {status_code}")
                self.stats['failed_pages'] += 1
                return

            # 获取HTML内容
            html_content = str(response.html_content)

            # 解析HTML(使用多解析器回退)
            soup = self._parse_html(html_content)
            if not soup:
                logger.error(f"无法解析HTML内容: {url}")
                self.stats['failed_pages'] += 1
                return

            # 提取页面信息 - 适配不同解析器类型
            page_title = url  # 默认值

            # 检查是否是BeautifulSoup对象
            if hasattr(soup, 'title') and hasattr(soup.title, 'string'):
                # BeautifulSoup对象
                page_title = soup.title.string.strip() if soup.title and soup.title.string else url
                logger.info(f"使用BeautifulSoup提取标题: {page_title[:50]}")
            elif hasattr(soup, 'xpath'):
                # lxml对象(标准或soupparser)
                title_elements = soup.xpath('//title')
                page_title = title_elements[0].text.strip() if title_elements else url
                logger.info(f"使用XPath提取标题: {page_title[:50]}")
            else:
                logger.warning(f"未知的解析器类型,无法提取标题,使用URL: {url}")
                page_title = url

            # 处理页面标题(移除" - Canada.ca"后缀,翻译中文到英文)
            original_title = page_title
            page_title = process_page_title(page_title, url)
            if page_title != original_title:
                logger.info(f"标题处理: '{original_title[:50]}...' -> '{page_title[:50]}...'")

            # 规范化URL(移除"/content/canadasite"前缀和参数)
            normalized_url = normalize_canada_url(url)
            if normalized_url != url:
                logger.info(f"URL规范化: '{url}' -> '{normalized_url}'")

            # 提取多语言alternate链接(用于 EN↔FR 配对)
            fr_alternate_url = None
            en_alternate_url = None
            try:
                if hasattr(soup, 'xpath'):
                    # 查找 <link rel="alternate" hreflang="..." href="...">
                    alt_links = soup.xpath('//link[@rel="alternate"][@hreflang]')
                    for alt in alt_links:
                        hl = alt.get('hreflang', '').lower()
                        href = alt.get('href', '')
                        if hl == 'fr' and href:
                            fr_alternate_url = normalize_canada_url(href)
                        elif hl == 'en' and href:
                            en_alternate_url = normalize_canada_url(href)
            except Exception as e:
                logger.debug(f"提取alternate链接失败: {e}")

            # 创建文档数据
            from ..schemas.document import DocumentCreate

            # 计算文件大小
            file_size = len(html_content.encode('utf-8'))

            # 管理员用户ID
            admin_user_id = "4dad6fa1-d521-417f-8877-efe95fcf1f04"

            # 根据规范化后的URL路径获取或创建对应的文件夹
            folder_path_for_url = get_folder_for_url(
                db=self.db,
                root_folder_path=folder_path,
                url=normalized_url,
                username="system"  # 系统用户
            )

            # 从原始URL中提取文件名(不用normalized_url,因为会剥掉.html)
            parsed_url = urlparse(url)
            url_path = parsed_url.path

            # 提取文件名(URL路径的最后一部分)
            url_filename = "index.html"  # 默认文件名(首页等)
            if url_path:
                path_parts = url_path.rstrip('/').split('/')
                if path_parts and path_parts[-1]:
                    last_part = path_parts[-1]
                    if '.' in last_part:
                        url_filename = last_part
                    else:
                        # 扩展名时:用URL最后一段而不是页面标题(保持与文件夹名一致)
                        url_filename = f"{last_part}.html"

            # 确保文件名有.html扩展名
            if not url_filename.endswith(('.html', '.htm')):
                url_filename = f"{url_filename}.html"

            # 回退:如果URL无法提取有效文件名(如域名根路径),用页面标题
            # 原则:每个文件必须有title和文件ID,文件ID缺失时用title
            if url_filename == "index.html" and page_title and page_title != "Untitled Page":
                # URL根路径且页面有实际标题→用sanitized标题作为文件名
                from ..core.path_utils import make_filename_safe
                title_filename = make_filename_safe(page_title)
                # 限制长度
                if len(title_filename) > 200:
                    title_filename = title_filename[:200]
                if title_filename and len(title_filename) > 5:
                    url_filename = f"{title_filename}.html"
                    logger.info(f"URL为空路径,使用页面标题作为文件名: {url_filename}")

            document_data = DocumentCreate(
                title=page_title[:255],
                description=f"Webpage crawled from {normalized_url}",
                original_filename=url_filename,
                file_size=file_size,
                file_type=FileType.HTML,
                mime_type="text/html",
                folder_path=folder_path_for_url,
                uploaded_by=admin_user_id,
                document_metadata={
                    'url': normalized_url,  # 使用规范化后的URL作为主标识
                    'original_url': url,     # 保存原始URL供参考
                    'crawled_at': time.time(),
                    'depth': current_depth,
                    'original_html': html_content[:10000],  # 保存部分HTML用于预览
                    # EN↔FR 配对信息(从页面 alternate link 提取)
                    'fr_alternate_url': fr_alternate_url,
                    'en_alternate_url': en_alternate_url,
                }
            )

            # 创建文档记录(使用纯path架构)
            document = self.create_document_with_path(
                document_data=document_data,
                folder_path=folder_path_for_url,
                content=html_content,
                is_binary=False
            )

            self.stats['successful_pages'] += 1
            self.stats['urls'].append({
                'url': url,
                'title': page_title,
                'status': 'success',
                'document_id': document.path
            })

            # 提取图片
            if include_images:
                self._extract_images(soup, url, folder_path_for_url, base_url)

            # 提取内部链接并递归爬取
            if current_depth < max_depth:
                internal_links = self._extract_internal_links(soup, url, base_url)

                for link in internal_links:
                    if follow_external_links or self._is_internal_link(link, base_url):
                        self._crawl_recursive(
                            url=link,
                            base_url=base_url,
                            current_depth=current_depth + 1,
                            max_depth=max_depth,
                            folder_path=folder_path,
                            include_images=include_images,
                            follow_external_links=follow_external_links
                        )

        except Exception as e:
            logger.error(f"爬取页面失败: {url}, 错误: {str(e)}")
            self.stats['failed_pages'] += 1
            self.stats['urls'].append({
                'url': url,
                'title': 'Error',
                'status': 'failed',
                'error': str(e)
            })

    def _save_binary_document(self, url: str, binary_content: bytes, mime_type: str, ext: str, parent_folder_path: str):
        """
        将二进制文件(PDF等)保存为文档,不尝试解析为HTML
        """
        try:
            from ..schemas.document import DocumentCreate
            from ..core.path_utils import make_filename_safe

            # 从URL提取文件名
            parsed_url = urlparse(url)
            url_path = parsed_url.path
            filename = url_path.rstrip('/').split('/')[-1] if url_path else "download"

            # 确保有正确扩展名
            if not filename.lower().endswith(ext):
                filename = f"{filename}{ext}"

            # 使用页面标题(文件名去掉扩展名)
            title = filename.rsplit(ext, 1)[0] if filename.lower().endswith(ext) else filename
            if len(title) > 255:
                title = title[:255]

            # 管理员用户ID
            admin_user_id = "4dad6fa1-d521-417f-8877-efe95fcf1f04"

            # 映射file_type
            ext_lower = ext.lower()
            if ext_lower == '.pdf':
                file_type = FileType.PDF
            elif ext_lower in ('.doc', '.docx'):
                file_type = FileType.DOC
            elif ext_lower in ('.xls', '.xlsx'):
                file_type = FileType.XLS
            elif ext_lower in ('.ppt', '.pptx'):
                file_type = FileType.OTHER
            else:
                file_type = FileType.OTHER

            # 获取文件夹路径
            target_folder = parent_folder_path
            normalized_url = normalize_canada_url(url)
            if hasattr(self, "root_folder_path") and self.root_folder_path:
                try:
                    target_folder = get_folder_for_url(
                        db=self.db,
                        root_folder_path=self.root_folder_path,
                        url=normalized_url,
                        username="system"
                    )
                except Exception as e:
                    logger.warning(f"获取二进制文件文件夹失败,使用页面文件夹: {e}")
                    target_folder = parent_folder_path

            document_data = DocumentCreate(
                title=title,
                description=f"File downloaded from {normalized_url}",
                original_filename=filename,
                file_size=len(binary_content),
                file_type=file_type,
                mime_type=mime_type,
                folder_path=target_folder,
                uploaded_by=admin_user_id,
                document_metadata={
                    'url': normalized_url,
                    'original_url': url,
                    'crawled_at': time.time(),
                    'source_type': 'binary_download'
                }
            )

            document = self.create_document_with_path(
                document_data=document_data,
                folder_path=target_folder,
                content=binary_content,
                is_binary=True
            )

            if document:
                logger.info(f"二进制文件保存成功: {url}")
                self.stats.setdefault('downloaded_files', 0)
                self.stats['downloaded_files'] += 1
            else:
                logger.warning(f"二进制文件保存失败(document为None): {url}")
        except Exception as e:
            logger.error(f"保存二进制文件失败: {url}, 错误: {e}")

    def _extract_images(self, soup, page_url: str, folder_path: str, base_url: str = None):
        """
        提取页面中的图片。
        - Canada.ca 站点:只搜 <main> 区域内 /content/canadasite 路径的图片
        - 其他站点:搜全页 //img[@src](如 WD-DEO 等老 ASP 站无 <main> 标签)
        跳过系统文件夹(/etc/)的图片
        """
        try:
            is_canada = base_url and "canada.ca" in base_url
            logger.info(f"_extract_images called for page: {page_url}, folder: {folder_path}, is_canada={is_canada}")
            if is_canada:
                img_elements = soup.xpath('//main//img[@src]')
                logger.info(f"Found {len(img_elements)} image elements in <main>")
            else:
                img_elements = soup.xpath('//img[@src]')
                logger.info(f"Found {len(img_elements)} image elements in full page")

            for img_element in img_elements:
                img_src = img_element.get('src')
                if not img_src:
                    continue

                # 跳过系统文件夹(/etc/)中的图片(如WET模板图片、logo等)
                if img_src.startswith('/etc/') or '/etc/' in img_src:
                    logger.debug(f"跳过系统文件夹图片: {img_src}")
                    continue

                # Canada.ca 只处理 /content/canadasite 路径的图片
                # 其他站点接受所有图片
                if is_canada:
                    if not img_src.startswith('/content/canadasite'):
                        logger.debug(f"跳过非/content/canadasite图片: {img_src}")
                        continue

                img_url = urljoin(page_url, img_src)

                # 检查是否有效图片URL
                if not img_url or img_url.startswith('data:'):
                    continue

                # 跳过外部域名的图片(只下载当前站点域名下的图片)
                if base_url and not self._is_internal_link(img_url, base_url):
                    logger.debug(f"跳过外部域名图片: {img_url}")
                    continue

                # 检查是否是/content/dam文件夹中的图片(用户特别关注的路径)
                is_content_dam = '/content/dam/' in img_url
                if is_content_dam:
                    logger.info(f"发现/content/dam图片: {img_url}")

                # 确定目标文件夹路径
                # 对于/content/dam图片,使用图片URL对应的文件夹;其他图片使用页面文件夹
                target_folder_path = folder_path  # 默认使用页面文件夹

                if hasattr(self, 'root_folder_path') and self.root_folder_path:
                    try:
                        # 为图片URL获取对应的文件夹
                        target_folder_path = get_folder_for_url(
                            db=self.db,
                            root_folder_path=self.root_folder_path,
                            url=normalize_canada_url(img_url),
                            username="system"
                        )
                        logger.info(f"图片文件夹路径: {img_url} -> 文件夹路径: {target_folder_path}")
                    except Exception as e:
                        logger.warning(f"获取图片文件夹失败,使用页面文件夹: {str(e)}")
                        target_folder_path = folder_path
                else:
                    logger.warning(f"root_folder_path未定义,使用页面文件夹")
                    target_folder_path = folder_path

                self.stats['total_images'] += 1

                # ====== IMAGE DEDUP: 检查图片URL是否已在DB中 ======
                normalized_img_url = normalize_canada_url(img_url)
                existing_img = self.db.query(Document).filter(
                    Document.document_metadata.op('->>')('url') == normalized_img_url
                ).first()
                if existing_img:
                    logger.info(f"⏭️ 跳过已存在的图片: {normalized_img_url}")
                    self.stats['total_images'] -= 1  # 刚加了1,这里抵消
                    self.stats['downloaded_images'] += 1  # 视为已下载
                    continue

                try:
                    # 使用Scrapling下载图片
                    response = self._fetch_url(img_url)

                    if not response:
                        logger.warning(f"图片获取返回空响应: {img_url}")
                        self.stats['failed_images'] += 1
                        continue

                    if response.status != 200:
                        logger.warning(f"图片获取失败: {img_url}, 状态码: {response.status}")
                        self.stats['failed_images'] += 1
                        continue

                    # 调试:记录Response类型和属性
                    logger.info(f"Response类型: {type(response)}, 属性: {[attr for attr in dir(response) if not attr.startswith('_')][:10]}")

                    # 获取图片信息
                    img_filename = img_url.split('/')[-1]
                    if not img_filename or '.' not in img_filename:
                        img_filename = f"image_{uuid.uuid4().hex[:8]}.jpg"

                    # 确定文件类型（先看URL扩展名，再看Content-Type）
                    content_type = response.headers.get('Content-Type', '')
                    file_extension = '.jpg'  # 默认
                    mime_type = 'image/jpeg'  # 默认
                    
                    # 从URL路径中推断扩展名（最可靠）
                    url_lower = img_url.lower()
                    if url_lower.endswith('.svg'):
                        file_extension = '.svg'
                        mime_type = 'image/svg+xml'
                    elif url_lower.endswith('.png'):
                        file_extension = '.png'
                        mime_type = 'image/png'
                    elif url_lower.endswith('.gif'):
                        file_extension = '.gif'
                        mime_type = 'image/gif'
                    elif url_lower.endswith('.webp'):
                        file_extension = '.webp'
                        mime_type = 'image/webp'
                    elif url_lower.endswith(('.jpg', '.jpeg')):
                        file_extension = '.jpg'
                        mime_type = 'image/jpeg'
                    else:
                        # URL无扩展名时回退到Content-Type
                        if 'image/png' in content_type:
                            file_extension = '.png'
                            mime_type = 'image/png'
                        elif 'image/gif' in content_type:
                            file_extension = '.gif'
                            mime_type = 'image/gif'
                        elif 'image/webp' in content_type:
                            file_extension = '.webp'
                            mime_type = 'image/webp'
                        elif 'image/svg+xml' in content_type:
                            file_extension = '.svg'
                            mime_type = 'image/svg+xml'

                    # 确保文件名有正确扩展名
                    if not img_filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg")):
                        img_filename = f"{img_filename.split('.')[0]}{file_extension}"

                    # 获取图片二进制内容
                    # 兼容不同Response对象的属性
                    image_content = None
                    if hasattr(response, 'content'):
                        image_content = response.content
                    elif hasattr(response, 'body'):
                        image_content = response.body
                    elif hasattr(response, 'read'):
                        image_content = response.read()
                    elif hasattr(response, 'raw'):
                        image_content = response.raw.read() if callable(response.raw.read) else response.raw
                    else:
                        # 尝试获取响应数据
                        logger.warning(f"无法获取图片内容,Response类型: {type(response)}")
                        self.stats['failed_images'] += 1
                        continue

                    if not image_content:
                        logger.warning(f"图片内容为空: {img_url}")
                        self.stats['failed_images'] += 1
                        continue

                    # 规范化图片URL(移除参数等)
                    normalized_img_url = normalize_canada_url(img_url)

                    # 从URL中提取标题
                    img_title = img_filename.rsplit('.', 1)[0]

                    # 创建图片文档数据
                    from ..schemas.document import DocumentCreate

                    # 管理员用户ID
                    admin_user_id = "4dad6fa1-d521-417f-8877-efe95fcf1f04"

                    document_data = DocumentCreate(
                        title=img_title[:255],
                        description=f"Image downloaded from {normalized_img_url}",
                        original_filename=img_filename,
                        file_size=len(image_content),
                        file_type=FileType.JPEG if file_extension in ['.jpg', '.jpeg'] else \
                                 FileType.PNG if file_extension == '.png' else \
                                 FileType.GIF if file_extension == '.gif' else \
                                 FileType.WEBP if file_extension == '.webp' else \
                                 FileType.SVG if file_extension == '.svg' else \
                                 FileType.OTHER,
                        mime_type=mime_type,
                        folder_path=target_folder_path,
                        uploaded_by=admin_user_id,
                        document_metadata={
                            'url': normalized_img_url,
                            'original_url': img_url,
                            'crawled_at': time.time(),
                            'is_content_dam': is_content_dam,
                            'source_page': page_url
                        }
                    )

                    # 使用相同的create_document_with_path方法保存图片
                    # 这会自动处理重复检测(基于规范化后的URL)和文件写入
                    logger.info(f"准备保存图片: {img_url}, 文件夹路径: {target_folder_path}, 大小: {len(image_content)} bytes, 是否为/content/dam图片: {is_content_dam}")
                    print(f"[DEBUG] 准备保存图片: {img_url}, 大小: {len(image_content)} bytes")
                    document = self.create_document_with_path(
                        document_data=document_data,
                        folder_path=target_folder_path,
                        content=image_content,
                        is_binary=True
                    )

                    if document:
                        logger.info(f"图片保存成功: {img_url}")
                        self.stats['downloaded_images'] += 1

                except Exception as e:
                    logger.warning(f"下载或保存图片失败: {img_url}, 错误: {str(e)}")
                    self.stats['failed_images'] += 1

        except Exception as e:
            logger.error(f"提取图片失败: {str(e)}")

    def _extract_internal_links(self, soup, page_url: str, base_url: str) -> List[str]:
        """提取内部链接"""
        links = []

        try:
            a_elements = soup.xpath('//a[@href]')

            for a_element in a_elements:
                href = a_element.get('href')

                # 跳过空链接、JavaScript链接等
                if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                    continue

                # 构建完整URL
                full_url = urljoin(page_url, href)

                # 添加到链接列表
                if full_url not in links:
                    links.append(full_url)

        except Exception as e:
            logger.error(f"提取链接失败: {str(e)}")

        return links

    def _is_internal_link(self, url: str, base_url: str) -> bool:
        """检查是否为内部链接"""
        try:
            parsed_url = urlparse(url)
            parsed_base = urlparse(base_url)

            # 比较域名
            return parsed_url.netloc == parsed_base.netloc

        except Exception:
            return False

    def _pair_en_fr_pages(self, folder_path: str = None) -> int:
        """
        根据 document_metadata 里的 fr_alternate_url / en_alternate_url
        自动建立 EN↔FR 页面配对,写入 document_metadata.other_lang_page_id

        Args:
            folder_path: 限定只配对该文件夹下的文档(避免遍历全库)

        Returns:
            配对数
        """
        paired = 0
        try:
            from ..models.document import Document
            from ..models.folder import Folder
            import json

            # 限定配对范围:只查指定文件夹下的文档
            query = self.db.query(Document).filter(
                Document.document_metadata.isnot(None)
            )
            if folder_path:
                # 查找该文件夹及其子文件夹中的所有文档
                from sqlalchemy import or_
                target_folders = self.db.query(Folder).filter(
                    Folder.path.startswith(folder_path)
                ).all()
                folder_ids = [f.id for f in target_folders]
                if folder_ids:
                    query = query.filter(Document.folder_id.in_(folder_ids))
                else:
                    # 如果文件夹不存在,不做配对
                    logger.warning(f"配对文件夹不存在: {folder_path}, 跳过配对")
                    return 0

            en_docs = query.all()

            # ====== 构建URL→文档的快速查找字典(避免内层循环每次查DB) ======
            fr_docs_list = self.db.query(Document).filter(
                Document.document_metadata.isnot(None)
            ).all()
            fr_by_url = {}  # url -> Document
            for fd in fr_docs_list:
                fd_meta = fd.document_metadata or {}
                if isinstance(fd_meta, str):
                    try:
                        fd_meta = json.loads(fd_meta)
                    except:
                        continue
                fd_url = fd_meta.get('url', '')
                if fd_url:
                    fr_by_url[fd_url] = fd

            for en_doc in en_docs:
                meta = en_doc.document_metadata or {}
                if isinstance(meta, str):
                    try:
                        meta = json.loads(meta)
                    except:
                        continue

                fr_alt_url = meta.get('fr_alternate_url')
                if not fr_alt_url:
                    continue

                # 使用字典快速查找FR文档(O(1) vs O(n))
                fd = fr_by_url.get(fr_alt_url)
                if fd:
                    # 配对成功:EN → FR
                    en_meta = en_doc.document_metadata
                    if isinstance(en_meta, dict):
                        en_meta['other_lang_page_id'] = str(fd.path)
                        en_doc.document_metadata = en_meta

                    # 配对成功:FR → EN
                    fr_meta = fd.document_metadata
                    if isinstance(fr_meta, dict):
                        fr_meta['other_lang_page_id'] = str(en_doc.path)
                        fd.document_metadata = fr_meta

                    self.db.commit()
                    paired += 1
                    logger.info(f"EN↔FR 配对: {meta.get('url','?')} ⟷ {fr_alt_url}")
                else:
                    logger.debug(f"未找到FR对应页面: en={meta.get('url','?')}, fr_alt={fr_alt_url}")

            return paired
        except Exception as e:
            logger.error(f"EN/FR 配对失败: {e}")
            return 0

    # ===== Sitemap 导入 =====

    def crawl_from_sitemap(self, sitemap_url: str, folder_path: str, include_images: bool = True, max_depth: int = 0) -> Dict[str, Any]:
        """
        从 sitemap.xml 导入所有 URL 并逐个爬取

        Args:
            sitemap_url: sitemap.xml 的 URL
            folder_path: 目标文件夹路径
            include_images: 是否下载图片
            max_depth: 从每个种子 URL 开始的递归深度(0=只抓当前页,1=当前页+子链接,2=再往下一层)

        Returns:
            爬取结果统计
        """
        # 验证文件夹
        folder = self.db.query(Folder).filter(Folder.path == folder_path).first()
        if not folder:
            raise ValueError(f"文件夹 {folder_path} 不存在")

        self.root_folder_path = folder_path

        # 解析 sitemap 获取 URL 列表
        logger.info(f"开始解析 sitemap: {sitemap_url}")
        all_urls = parse_sitemap_urls(sitemap_url)
        logger.info(f"Sitemap 解析完成: 共 {len(all_urls)} 个 URL")

        # 初始化统计数据
        self.stats = {
            'total_pages': 0,
            'successful_pages': 0,
            'failed_pages': 0,
            'total_images': 0,
            'downloaded_images': 0,
            'failed_images': 0,
            'start_time': time.time(),
            'urls': [],
            'sitemap_url': sitemap_url,
            'total_from_sitemap': len(all_urls)
        }

        self._update_task_status(
            status="crawling",
            current_status=f"Importing {len(all_urls)} URLs from sitemap...",
            pages_processed=0
        )

        base_url = self._get_base_url(all_urls[0]) if all_urls else sitemap_url

        for i, page_url in enumerate(all_urls):
            # 每个 URL 从 depth=0 开始递归爬取
            self._crawl_recursive(
                url=page_url,
                base_url=base_url,
                current_depth=0,
                max_depth=max_depth,
                folder_path=folder_path,
                include_images=include_images,
                follow_external_links=False
            )

            # 每 50 个 URL 更新一次状态
            if (i + 1) % 50 == 0:
                self._update_task_status(
                    current_status=f"Sitemap import: {i+1}/{len(all_urls)} URLs processed",
                    pages_crawled=self.stats['total_pages'],
                    pages_processed=self.stats['successful_pages'],
                    images_crawled=self.stats['total_images']
                )
                logger.info(f"Sitemap 导入进度: {i+1}/{len(all_urls)}")

        # EN↔FR 页面配对
        paired_count = self._pair_en_fr_pages()
        if paired_count > 0:
            logger.info(f"EN↔FR 配对完成: 建立了 {paired_count} 个页面的语言关联")

        # 更新最终状态
        self.stats['end_time'] = time.time()
        self.stats['duration'] = self.stats['end_time'] - self.stats['start_time']

        self._update_task_status(
            status="completed",
            current_status=f"Sitemap import complete: {self.stats['successful_pages']}/{len(all_urls)} pages",
            pages_crawled=self.stats['total_pages'],
            pages_processed=self.stats['successful_pages'],
            images_crawled=self.stats['total_images'],
            stats=self.stats
        )

        logger.info(f"Sitemap 导入完成: {self.stats}")
        return self.stats


def parse_sitemap_urls(sitemap_url: str, max_urls: int = 50000) -> List[str]:
    """
    解析 sitemap.xml 并提取所有 <loc> URL

    支持:
    - 标准 sitemap(含 <url><loc>...</loc></url>)
    - Sitemap index(含 <sitemap><loc>...</loc></sitemap>,递归解析子 sitemap)
    - GZip 压缩的 .xml.gz

    Args:
        sitemap_url: sitemap.xml 的 URL
        max_urls: 最大提取 URL 数量

    Returns:
        提取的所有 URL 列表
    """
    import httpx
    import xml.etree.ElementTree as ET
    import gzip
    from io import BytesIO

    urls = []
    visited_sitemaps = set()

    def _fetch_and_parse(url: str) -> Optional[bytes]:
        """获取并返回 sitemap XML 内容"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; FileBotCrawler/1.0)'
            }
            resp = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
            if resp.status_code != 200:
                logger.warning(f"Sitemap 请求失败: {url}, 状态码: {resp.status_code}")
                return None

            content = resp.content

            # 如果是 gzip 压缩
            if url.endswith('.gz'):
                try:
                    content = gzip.decompress(content)
                except:
                    logger.warning(f"GZip 解压失败: {url}")
                    pass

            return content
        except Exception as e:
            logger.warning(f"获取 sitemap 失败: {url}, 错误: {e}")
            return None

    def _parse_sitemap_xml(content: bytes) -> bool:
        """解析 sitemap XML,返回是否是 sitemap index"""
        nonlocal urls
        try:
            root = ET.fromstring(content)
            # 处理命名空间
            ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            # 检查是否为 sitemap index
            if root.tag.endswith('sitemapindex'):
                sitemap_tags = root.findall('.//sm:sitemap/sm:loc', ns) or root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if not sitemap_tags:
                    sitemap_tags = root.findall('.//loc')

                logger.info(f"Sitemap index 发现 {len(sitemap_tags)} 个子 sitemap")
                for loc in sitemap_tags:
                    sub_url = loc.text.strip()
                    if sub_url not in visited_sitemaps and len(urls) < max_urls:
                        visited_sitemaps.add(sub_url)
                        content = _fetch_and_parse(sub_url)
                        if content:
                            _parse_sitemap_xml(content)
                return True

            # 标准 sitemap
            url_tags = root.findall('.//sm:url/sm:loc', ns) or root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            if not url_tags:
                url_tags = root.findall('.//url/loc') or root.findall('.//loc')

            for loc in url_tags:
                if len(urls) >= max_urls:
                    break
                urls.append(loc.text.strip())

            logger.info(f"从 sitemap 提取了 {len(url_tags)} 个 URL")
            return False
        except Exception as e:
            logger.warning(f"XML 解析失败: {e}")
            return False

    # 开始解析
    visited_sitemaps.add(sitemap_url)
    content = _fetch_and_parse(sitemap_url)
    if content:
        _parse_sitemap_xml(content)

    # 去重并按原始顺序保留
    seen = set()
    unique_urls = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)

    logger.info(f"Sitemap 解析完成: {len(unique_urls)} 个去重后的 URL")
    return unique_urls


def to_slug(text: str) -> str:
    """
    将字符串转换为URL友好的slug

    Args:
        text: 原始文本

    Returns:
        URL友好的slug
    """
    if not text:
        return ""

    import re

    # 转换为小写
    slug = text.lower()

    # 替换非字母数字字符为连字符
    slug = re.sub(r'[^a-z0-9]+', '-', slug)

    # 移除开头和结尾的连字符
    slug = slug.strip('-')

    # 如果结果为空,使用随机字符串
    if not slug:
        slug = f"page-{uuid.uuid4().hex[:8]}"

    return slug


def create_folder_slug(segment: str) -> str:
    """
    为URL路径段创建文件夹slug,支持中文字符翻译

    Args:
        segment: URL路径段(可能包含中文)

    Returns:
        文件夹slug
    """
    if not segment:
        return ""

    import re

    # 检测是否包含中文字符
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', segment))

    folder_name = segment

    if has_chinese:
        logger.info(f"路径段包含中文: {segment},尝试翻译")
        # 尝试翻译中文路径段
        try:
            # 使用translate_chinese_title函数翻译
            translated = translate_chinese_title(segment)
            if translated and translated != segment:
                folder_name = translated
                logger.info(f"路径段翻译: '{segment}' -> '{translated}'")
        except Exception as e:
            logger.warning(f"路径段翻译失败: {str(e)[:100]}")

    # 使用to_slug转换为URL友好格式
    folder_slug = to_slug(folder_name)

    # 如果slug为空,使用原始段的哈希值
    if not folder_slug:
        import hashlib
        segment_hash = hashlib.md5(segment.encode('utf-8')).hexdigest()[:8]
        folder_slug = f"folder-{segment_hash}"

    return folder_slug


def translate_chinese_title(chinese_title: str) -> str:
    """
    翻译中文标题到英文

    尝试使用googletrans(如果可用),否则使用词汇表翻译

    Args:
        chinese_title: 中文标题

    Returns:
        翻译后的英文标题
    """
    if not chinese_title:
        return chinese_title

    # 尝试使用googletrans进行真正的翻译
    try:
        from googletrans import Translator
        translator = Translator()

        # 限制标题长度,避免超长
        if len(chinese_title) <= 500:
            translated = translator.translate(chinese_title, src='zh-CN', dest='en')
            if translated and translated.text:
                logger.info(f"googletrans翻译成功: '{chinese_title[:50]}...' -> '{translated.text[:50]}...'")
                return translated.text
        else:
            logger.warning(f"标题过长({len(chinese_title)}字符),跳过googletrans翻译")
    except ImportError:
        logger.info("googletrans未安装,使用词汇表翻译")
    except Exception as e:
        logger.warning(f"googletrans翻译失败: {str(e)[:100]}")

    # 回退到词汇表翻译
    simple_translations = {
        # 导航和页面标题
        "首页": "Home", "主页": "Home", "关于": "About", "关于我们": "About Us",
        "服务": "Services", "服务项目": "Services", "联系": "Contact", "联系我们": "Contact Us",
        "新闻": "News", "新闻动态": "News", "帮助": "Help", "帮助中心": "Help Center",
        "搜索": "Search", "搜索功能": "Search",

        # Canada.ca特定词汇
        "加拿大": "Canada", "政府": "Government", "联邦政府": "Federal Government",
        "公共服务": "Public Services", "在线服务": "Online Services", "移动应用": "Mobile App",
        "移动版": "Mobile Version", "网站地图": "Site Map", "隐私政策": "Privacy Policy",
        "使用条款": "Terms of Use", "无障碍访问": "Accessibility", "官方语言": "Official Languages",

        # 常见功能
        "登录": "Login", "注册": "Register", "账户": "Account", "个人资料": "Profile",
        "设置": "Settings", "通知": "Notifications", "消息": "Messages", "收藏": "Favorites",
        "历史记录": "History", "下载": "Download", "上传": "Upload", "分享": "Share",

        # 内容类型
        "文章": "Article", "博客": "Blog", "报告": "Report", "文档": "Document",
        "指南": "Guide", "教程": "Tutorial", "常见问题": "FAQ", "问答": "Q&A",
        "资源": "Resources", "工具": "Tools", "应用程序": "Application",

        # 部门和服务
        "税务": "Tax", "税务服务": "Tax Services", "就业": "Employment", "就业服务": "Employment Services",
        "医疗": "Healthcare", "医疗服务": "Healthcare Services", "教育": "Education", "教育服务": "Education Services",
        "移民": "Immigration", "移民服务": "Immigration Services", "旅游": "Travel", "旅游信息": "Travel Information",

        # 移动相关词汇(针对en/mobile.html)
        "移动": "Mobile", "手机": "Mobile Phone", "平板": "Tablet", "设备": "Device",
        "响应式": "Responsive", "适配": "Adaptive", "优化": "Optimized", "版本": "Version",
        "应用": "App", "应用程序": "Application", "下载应用": "Download App",
        "移动友好": "Mobile-Friendly", "触摸屏": "Touchscreen", "手势": "Gestures",
    }

    translated_title = chinese_title
    # 按长度排序,先替换长短语
    sorted_translations = dict(sorted(simple_translations.items(), key=lambda x: len(x[0]), reverse=True))

    for chinese, english in sorted_translations.items():
        if chinese in translated_title:
            translated_title = translated_title.replace(chinese, english)
            logger.info(f"标题词汇翻译: '{chinese}' -> '{english}'")

    return translated_title


def process_page_title(title: str, url: str = "") -> str:
    """
    处理页面标题,根据用户需求:
    1. 移除英文标题中的 " - Canada.ca" 后缀(注意空格)
    2. 将中文标题翻译成英文(需要时)

    Args:
        title: 原始页面标题
        url: 页面URL(用于上下文)

    Returns:
        处理后的标题
    """
    if not title or title == url:
        return title

    processed_title = title.strip()

    # 1. 移除 " - Canada.ca" 后缀(canada.ca SEO 规范)
    # 检查标题是否以 " - Canada.ca - Gouvernement du Canada" 结尾(法语)
    if processed_title.endswith(" - Canada.ca - Gouvernement du Canada"):
        processed_title = processed_title[:-33].rstrip()
    # 检查标题是否以 " - Canada.ca" 结尾(英文)
    elif processed_title.endswith(" - Canada.ca"):
        processed_title = processed_title[:-12].rstrip()

    # 2. 简单中文检测和处理(基础实现)
    # 检测是否包含中文字符
    import re
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', processed_title))

    if has_chinese:
        # 检测到中文标题,调用翻译函数
        logger.info(f"检测到中文标题: {processed_title[:100]}")

        # 使用translate_chinese_title函数进行翻译
        processed_title = translate_chinese_title(processed_title)

        # 检查翻译后是否仍有中文字符
        still_has_chinese = bool(re.search(r'[\u4e00-\u9fff]', processed_title))
        if still_has_chinese:
            logger.warning(f"标题中仍有未翻译的中文: {processed_title[:100]}")

    # 移除多余的空格
    processed_title = processed_title.strip()

    # 如果处理后为空,返回原始标题
    if not processed_title:
        return title

    logger.info(f"标题处理: 原始='{title[:50]}...', 处理='{processed_title[:50]}...'")
    return processed_title


def normalize_canada_url(url: str) -> str:
    """
    规范化Canada.ca URL,根据用户需求:
    1. 移除"/content/canadasite"前缀
    2. 移除问号后的所有参数

    Args:
        url: 原始URL

    Returns:
        规范化后的URL
    """
    if not url:
        return url

    original_url = url

    # 解析URL
    parsed = urlparse(url)

    # 1. 移除"/content/canadasite"前缀
    path = parsed.path
    if path.startswith('/content/canadasite'):
        path = path[len('/content/canadasite'):]
        # 如果移除后路径为空,设为根路径
        if not path:
            path = '/'

    # 2. 移除 .html / .htm / .php 等扩展名(避免 .html 重复页面)
    path = re.sub(r'\.html?$', '', path, flags=re.IGNORECASE)

    # 3. 如果路径以 /en/ 结尾,保留(空段表示 en 根目录)
    #    防止 /en/services 变成 /en/services(无变化)

    # 4. 移除问号后的所有参数
    # 将查询参数设置为空字符串
    query = ''

    # 重新构建URL
    normalized_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        path,
        parsed.params,
        query,
        parsed.fragment
    ))

    if normalized_url != original_url:
        logger.info(f"URL规范化: '{original_url}' -> '{normalized_url}'")

    return normalized_url


def get_folder_for_url(db: Session, root_folder_path: str, url: str, username: str = "system") -> str:
    """
    根据URL路径创建或获取对应的嵌套文件夹结构(纯path架构)

    Args:
        db: 数据库会话
        root_folder_path: 根文件夹路径
        url: 页面URL
        username: 创建者用户名(默认为"system")

    Returns:
        str: 最终的子文件夹路径
    """
    try:
        # 获取根文件夹信息
        root_folder = db.query(Folder).filter(Folder.path == root_folder_path).first()
        if not root_folder:
            logger.error(f"根文件夹不存在: {root_folder_path}")
            return root_folder_path

        # 解析URL
        parsed = urlparse(url)
        path = parsed.path

        # 始终去掉最后一段路径(它代表文件名,非文件夹)
        if '/' in path:
            parts = path.rstrip('/').split('/')
            if len(parts) > 1:
                path = '/'.join(parts[:-1]) + '/'

        if path == '/':
            return root_folder_path

        path_segments = [segment for segment in path.strip('/').split('/') if segment]

        if not path_segments:
            return root_folder_path

        MAX_DEPTH = 10
        if len(path_segments) > MAX_DEPTH:
            logger.warning(f"URL路径段({len(path_segments)})超过最大限制({MAX_DEPTH}),截断后: {path_segments[:MAX_DEPTH]}")
            path_segments = path_segments[:MAX_DEPTH]

        logger.info(f"URL路径解析: {url} -> 路径段: {path_segments} (原始路径: {path})")

        # 从根文件夹开始,逐级创建或获取子文件夹
        current_folder_path = root_folder_path
        current_folder = root_folder

        for i, segment in enumerate(path_segments):
            folder_slug = create_folder_slug(segment)
            if not folder_slug:
                folder_slug = f"folder-{i+1}"

            expected_path = f"{current_folder.path}/{folder_slug}" if current_folder.path else f"/{folder_slug}"

            # 查找是否存在同名的子文件夹
            subfolder = db.query(Folder).filter(
                Folder.path == expected_path
            ).first()

            if subfolder:
                current_folder_path = subfolder.path
                current_folder = subfolder
                continue

            # 编号重复检测:services-4 → services(历史残留编号版)
            numbered_match = re.match(r'^(.+)-\d+$', folder_slug)
            if numbered_match:
                base_name = numbered_match.group(1)
                base_path = f"{current_folder.path}/{base_name}" if current_folder.path else f"/{base_name}"
                base_folder = db.query(Folder).filter(
                    Folder.path == base_path
                ).first()
                if base_folder:
                    logger.info(f"编号重复检测: '{folder_slug}' → 使用已存在的 '{base_name}' 文件夹")
                    current_folder_path = base_folder.path
                    current_folder = base_folder
                    continue

            # 创建新文件夹
            logger.info(f"创建子文件夹: {folder_slug} (原始路径段: {segment}),父文件夹: {current_folder.name}")

            parsed_display = urlparse(url)
            display_path = parsed_display.path
            if not display_path or display_path == '':
                display_path = '/'
            display_path = re.sub(r'\.(html?|php|asp|x?html?|jsp|aspx)(\?.*)?$', '', display_path, flags=re.IGNORECASE)
            if not display_path.endswith('/') and '.' not in display_path.split('/')[-1]:
                display_path = display_path + '/'

            description = f"Corresponding URL path: {display_path}"

            new_folder = Folder(
                app_id=current_folder.app_id,
                parent_folder_path=current_folder.path,
                name=folder_slug,
                path=expected_path,
                title=folder_slug,
                description=description,
                created_by=username
            )

            db.add(new_folder)
            db.commit()
            db.refresh(new_folder)

            current_folder_path = new_folder.path
            current_folder = new_folder

        logger.info(f"URL {url} 对应的文件夹路径: {current_folder_path}")
        return current_folder_path

    except Exception as e:
        logger.error(f"获取URL对应文件夹失败: {url}, 错误: {str(e)}")
        return root_folder_path


# 兼容性包装器
def create_scrapling_crawler(db: Session, task_id: str = None) -> ScraplingCrawler:
    """
    创建Scrapling爬虫(兼容旧API)

    Args:
        db: 数据库会话
        task_id: 爬取任务ID

    Returns:
        ScraplingCrawler实例
    """
    return ScraplingCrawler(db=db, task_id=task_id)