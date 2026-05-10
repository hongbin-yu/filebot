"""
Website crawling service
Crawl website content and import as documents
"""

import logging
import time
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import re
from sqlalchemy.orm import Session
import email.utils  # 用于解析HTTP日期格式

from ..models.document import Document, DocumentType, DocumentStatus, FileType, ConversionStatus
from ..models.folder import Folder
from ..schemas.document import DocumentCreate
import os
import hashlib
from pathlib import Path

# Scrapling爬虫导入
from .scrapling_crawler import ScraplingCrawler

def create_document(db: Session, document_data: DocumentCreate, folder_path: str, html_content: str = None) -> Document:
    """
    创建文档记录并保存文件内容
    
    实际实现：保存文件到文件系统并创建数据库记录
    现在支持纯path架构: {app_slug}/{folder_path}/{safe_filename}
    """
    logger = logging.getLogger(__name__)
    

    
    try:
        # 生成唯一的文件ID
        # 获取文件夹信息
        folder = db.query(Folder).filter(Folder.path == folder_path).first()
        if not folder:
            logger.error(f"文件夹不存在: {folder_path}")
            raise ValueError(f"文件夹 {folder_path} 不存在")
        
        # 获取应用信息（用于纯path架构）
        from ..models.app import App
        from ..core.path_utils import generate_storage_paths, make_filename_safe
        from ..core.config import settings
        
        app = db.query(App).filter(App.id == folder.app_id).first()
        if not app:
            logger.error(f"应用不存在: {folder.app_id}")
            raise ValueError(f"应用 {folder.app_id} 不存在")
        
        # 使用纯path架构生成存储路径
        app_slug = app.slug or to_slug(app.name)
        folder_path = folder.path if folder.path else f"/{folder.name}"
        original_filename = document_data.original_filename or f"{file_id}.{document_data.file_type.value}"
        safe_filename = make_filename_safe(original_filename)
        data_root = Path(settings.DATA_ROOT)
        
        # ====== PATH-BASED DEDUP: Check DB before filesystem numbering ======
        # Compute the expected URL path without generate_unique_filename's -N suffix
        clean_folder = folder_path
        if clean_folder.startswith(f'/{app_slug}'):
            clean_folder = clean_folder[len(app_slug)+1:]
            if clean_folder and not clean_folder.startswith('/'):
                clean_folder = '/' + clean_folder
        expected_url_path = f"/{app_slug}{clean_folder}/{safe_filename}"
        
        # 移除 .html 后缀：URL 路径应使用干净路径（不含扩展名）
        # 磁盘文件（storage_path/stored_filename）仍保留 .html
        expected_url_path = re.sub(r'\.html?$', '', expected_url_path)
        
        existing_by_path = db.query(Document).filter(
            Document.path == expected_url_path
        ).first()
        
        if existing_by_path:
            logger.info(f"Found document with same path, updating instead of creating numbered file: path={expected_url_path}, id={existing_by_path.id}")
            # Reuse existing document's storage info
            final_filename = existing_by_path.stored_filename or safe_filename
            url_path = existing_by_path.path
            
            if existing_by_path.storage_path:
                storage_path = data_root / existing_by_path.storage_path
            else:
                storage_path = data_root / f"{app_slug}{clean_folder}/{final_filename}"
            
            # Ensure directory exists and write content
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Update existing document metadata (content will be written later by caller)
            existing_by_path.original_filename = original_filename
            existing_by_path.stored_filename = final_filename
            existing_by_path.storage_path = str(storage_path.relative_to(data_root))
            existing_by_path.path = url_path
            existing_by_path.parent_folder_path = folder_path
            existing_by_path.document_metadata = document_data.document_metadata or {}
            existing_by_path.updated_at = func.now()
            if document_data.uploaded_by:
                existing_by_path.updated_by = str(document_data.uploaded_by)
            
            db.commit()
            db.refresh(existing_by_path)
            logger.info(f"Updated document by path: ID={existing_by_path.id}, path={url_path}")
            return existing_by_path
        
        # ====== Check for orphaned files on filesystem (no DB record but file exists) ======
        expected_storage_path = data_root / f"{app_slug}{clean_folder}" / safe_filename
        if expected_storage_path.exists():
            logger.info(f"Found orphaned file at {expected_storage_path}, will reuse path instead of creating numbered version")
            storage_path = expected_storage_path
            url_path = expected_url_path
            final_filename = safe_filename
        else:
            # ====== No collision: create with normal filesystem dedup ======
            storage_path, url_path, final_filename = generate_storage_paths(
                original_filename=original_filename,
                app_slug=app_slug,
                folder_path=folder_path,
                data_root=data_root
            )
        
        # 确保目录存在
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 旧路径兼容（向后兼容）
        # 格式: data/documents/{folder_path}/
        docs_dir = Path("data/documents") / folder_path
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        # 构建文件路径 - 使用safe_filename（纯path架构）
        file_name = final_filename  # 使用生成的安全文件名
        file_path = storage_path  # 使用纯path架构的存储路径
        
        # 检查是否已存在相同存储路径的文档（防止重复）
        existing_doc = db.query(Document).filter(
            (Document.storage_path == str(storage_path.relative_to(data_root))) |
            (Document.stored_filename == final_filename)
        ).first()
        if existing_doc:
            logger.warning(f"文档已存在，跳过创建: storage_path='{storage_path}', 现有ID={existing_doc.path}")
            return existing_doc
        
        # 同时创建旧路径兼容文件（可选，用于向后兼容）
        # 如果需要，可以在这里复制文件到旧路径
        old_file_path = docs_dir / file_name
        if not old_file_path.exists() and file_path.exists():
            try:
                import shutil
                shutil.copy2(file_path, old_file_path)
                logger.debug(f"创建向后兼容文件: {old_file_path}")
            except Exception as e:
                logger.warning(f"创建向后兼容文件失败: {e}")
        
        # 对于HTML文档，保存实际内容或创建占位符
        logger.debug(f"create_document: 文件类型: {document_data.file_type}, 路径: {file_path}")
        # 修复：比较枚举值而不是枚举成员
        # 获取文件类型值，支持枚举和字符串
        file_type_value = document_data.file_type.value if hasattr(document_data.file_type, 'value') else document_data.file_type.lower()
        if file_type_value in ['html', 'htm']:
            write_success = False
            actual_size = 0
            
            # 检查html_content是否有效（非None且非空字符串）
            logger.info(f"create_document: html_content 类型: {type(html_content)}, 长度: {len(html_content) if html_content else 0}, 非空: {bool(html_content)}, 去空后非空: {bool(html_content and html_content.strip())}")
            # 确定要写入的内容：多级回退策略
            content_to_write = None
            content_source = None
            
            # 第一优先级：html_content参数（来自爬虫的response.text）
            if html_content and html_content.strip():
                content_to_write = html_content
                content_source = 'html_content parameter'
                logger.info(f"使用html_content参数，长度: {len(content_to_write)}")
            # 第二优先级：元数据中的original_html（原始HTML）
            elif document_data.document_metadata and 'original_html' in document_data.document_metadata:
                metadata_content = document_data.document_metadata.get('original_html')
                if metadata_content and metadata_content.strip():
                    content_to_write = metadata_content
                    content_source = 'original_html metadata'
                    logger.info(f"使用元数据中的original_html，长度: {len(content_to_write)}")
            # 第三优先级：元数据中的html_content（旧字段，向后兼容）
            elif document_data.document_metadata and 'html_content' in document_data.document_metadata:
                metadata_content = document_data.document_metadata.get('html_content')
                if metadata_content and metadata_content.strip():
                    content_to_write = metadata_content
                    content_source = 'html_content metadata (legacy)'
                    logger.info(f"使用元数据中的html_content（旧字段），长度: {len(content_to_write)}")
            # 第四优先级：元数据中的extracted_text（提取的纯文本）
            elif document_data.document_metadata and 'extracted_text' in document_data.document_metadata:
                metadata_content = document_data.document_metadata.get('extracted_text')
                if metadata_content and metadata_content.strip():
                    # 将纯文本包装成基本HTML
                    wrapped_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{document_data.title}</title>
    <meta charset="utf-8">
    <meta name="description" content="{document_data.description[:200] if document_data.description else ''}">
    <meta name="source-url" content="{document_data.original_url or ''}">
</head>
<body>
    <h1>{document_data.title}</h1>
    <p>Original URL: <a href="{document_data.original_url}">{document_data.original_url}</a></p>
    <hr>
    <pre>{metadata_content[:5000]}</pre>
    <p><i>Note: This file contains extracted text content only. Original HTML was not saved.</i></p>
</body>
</html>"""
                    content_to_write = wrapped_html
                    content_source = 'extracted_text metadata (wrapped as HTML)'
                    logger.info(f"使用extracted_text包装为HTML，长度: {len(content_to_write)}")
            
            if content_to_write:
                # 保存实际的HTML内容，最多重试3次
                for attempt in range(3):
                    try:
                        logger.debug(f"尝试写入HTML内容 (尝试 {attempt+1}/3), 来源: {content_source}, 长度: {len(content_to_write)}")
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content_to_write)
                        
                        # 验证写入的内容 - 检查文件大小
                        expected_size = len(content_to_write.encode('utf-8'))
                        if file_path.exists():
                            actual_file_size = file_path.stat().st_size
                            if actual_file_size == expected_size:
                                actual_size = expected_size
                                logger.info(f"保存HTML内容成功: {file_name}, 大小: {actual_size} 字节")
                                write_success = True
                                break
                            else:
                                logger.warning(f"文件大小不匹配! 预期: {expected_size}, 实际: {actual_file_size} (尝试 {attempt+1})")
                                # 如果文件大小为0，可能文件被锁定或其他问题，等待后重试
                                if actual_file_size == 0:
                                    time.sleep(0.1 * (attempt + 1))
                                    continue
                        else:
                            logger.error(f"文件不存在，写入可能失败: {file_path}")
                    except Exception as write_error:
                        logger.error(f"写入HTML文件失败 (尝试 {attempt+1}): {write_error}")
                        if attempt < 2:  # 不是最后一次尝试
                            time.sleep(0.1 * (attempt + 1))
                            continue
            
            # 如果写入失败或html_content无效，创建占位符
            if not write_success:
                logger.warning(f"HTML内容写入失败，使用占位符: {file_name}")
                # 创建占位符HTML文件
                placeholder_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{document_data.title}</title>
    <meta charset="utf-8">
    <meta name="description" content="{document_data.description[:200] if document_data.description else ''}">
    <meta name="source-url" content="{document_data.original_url or ''}">
</head>
<body>
    <h1>{document_data.title}</h1>
    <p>Crawled from <a href="{document_data.original_url}">{document_data.original_url}</a></p>
    <p>Crawl time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}</p>
    <hr>
    <div>
        <p>Original content was not saved in this file. Content should be obtained during crawling.</p>
        <p>This file is a placeholder for document creation workflow.</p>
    </div>
</body>
</html>"""
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(placeholder_html)
                    actual_size = len(placeholder_html.encode('utf-8'))
                    
                    # 验证占位符写入
                    if file_path.exists() and file_path.stat().st_size == actual_size:
                        logger.warning(f"使用HTML占位符，未提供实际内容: {file_name}, 大小: {actual_size} 字节")
                    else:
                        logger.error(f"占位符写入验证失败! 文件大小: {file_path.stat().st_size if file_path.exists() else 0}")
                        # 最后手段：创建空文件
                        file_path.touch()
                        actual_size = 0
                except Exception as e:
                    logger.error(f"写入占位符失败: {e}")
                    # 最后手段：创建空文件
                    try:
                        file_path.touch()
                        actual_size = 0
                    except:
                        logger.error(f"无法创建任何文件: {file_name}")
        else:
            # 对于其他文件类型，创建空文件
            try:
                file_path.touch()
                actual_size = 0
                logger.info(f"创建空文件占位符: {file_name}")
            except Exception as e:
                logger.error(f"创建空文件失败: {e}")
                actual_size = 0
        
        # 计算文件哈希（使用文件内容计算）
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        # 从metadata中提取原始URL
        original_url = None
        if document_data.document_metadata:
            original_url = document_data.document_metadata.get('url') or document_data.document_metadata.get('original_url')
        
        # 创建数据库记录（使用纯path架构）
        logger.debug(f"file_type: {document_data.file_type}, type: {type(document_data.file_type)}")
        document = Document(
            title=document_data.title,
            description=document_data.description,
            original_filename=document_data.original_filename,
            stored_filename=safe_filename,  # 只存储安全文件名，不包含路径
            storage_path=str(storage_path.relative_to(data_root)),  # 相对存储路径
            path=url_path,  # 公共URL路径
            folder_path=folder_path,  # 父文件夹路径
            file_type=FileType(document_data.file_type.value),
            file_size=actual_size,
            mime_type=document_data.mime_type,
            document_metadata=document_data.document_metadata or {},
            status=DocumentStatus.ACTIVE,
            uploaded_by=str(document_data.uploaded_by),
            conversion_status=ConversionStatus.PENDING
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        logger.info(f"创建文档成功: ID={file_id}, 标题='{document_data.title}', 文件='{file_name}'")
        
        return document
        
    except Exception as e:
        logger.error(f"创建文档失败: {str(e)}")
        db.rollback()
        raise


def get_filetype_for_filename(filename: str) -> FileType:
    """
    根据文件扩展名获取对应的FileType枚举值
    
    Args:
        filename: 文件名或扩展名
        
    Returns:
        FileType枚举值
    """
    import os
    
    # 获取文件扩展名
    _, ext = os.path.splitext(filename)
    ext = ext.lower().lstrip('.')
    
    # 映射扩展名到FileType
    extension_to_filetype = {
        # 图像格式
        'jpg': FileType.JPG,
        'jpeg': FileType.JPEG,
        'png': FileType.PNG,
        'gif': FileType.OTHER,  # GIF没有对应的枚举，使用OTHER
        'bmp': FileType.OTHER,
        'tiff': FileType.TIFF,
        'tif': FileType.TIFF,
        'webp': FileType.OTHER,
        'svg': FileType.OTHER,
        'ico': FileType.OTHER,
        
        # 文档格式
        'pdf': FileType.PDF,
        'doc': FileType.DOC,
        'docx': FileType.DOCX,
        'txt': FileType.TXT,
        
        # HTML格式
        'html': FileType.HTML,
        'htm': FileType.HTM,
        
        # 其他
        'pcl': FileType.PCL,
        'ps': FileType.PS,
    }
    
    # 返回对应的枚举值，如果找不到则返回OTHER
    return extension_to_filetype.get(ext, FileType.OTHER)


def to_slug(text: str) -> str:
    """
    Convert a string to a URL-friendly slug
    Similar to frontend toSlug function and backend folders.py to_slug
    """
    if not text:
        return ''
    
    import unicodedata
    import re
    
    # Convert to lowercase
    text = text.lower()
    
    # Normalize and remove accents
    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    
    # Replace spaces and special characters
    text = re.sub(r'[^a-z0-9\s-]', '', text)  # Remove non-alphanumeric except spaces and hyphens
    text = re.sub(r'[\s-]+', '-', text)  # Replace spaces and multiple hyphens with single hyphen
    text = text.strip('-')  # Trim hyphens from start and end
    
    return text


def get_folder_for_url(db: Session, root_folder_path: str, url: str, username: str = "system") -> str:
    """
    根据URL路径创建或获取对应的嵌套文件夹结构（纯path架构）
    
    Args:
        db: 数据库会话
        root_folder_path: 根文件夹路径
        url: 页面URL
        username: 创建者用户名（默认为"system"）
    
    Returns:
        str: 最终的子文件夹路径
    """
    logger = logging.getLogger(__name__)
    
    try:
        # 获取根文件夹信息
        root_folder = db.query(Folder).filter(Folder.path == root_folder_path).first()
        if not root_folder:
            logger.error(f"根文件夹不存在: {root_folder_path}")
            return root_folder_path
        
        # 解析URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path
        
        # 去除文件名部分（最后一个斜杠之后的内容）
        if '/' in path:
            if '.' in path.split('/')[-1]:
                path = '/'.join(path.split('/')[:-1]) + '/'
            elif not path.endswith('/'):
                path = path + '/'
        
        if path == '/':
            return root_folder_path
        
        path_segments = [segment for segment in path.strip('/').split('/') if segment]
        
        if not path_segments:
            return root_folder_path
        
        MAX_DEPTH = 10
        if len(path_segments) > MAX_DEPTH:
            logger.warning(f"URL路径段({len(path_segments)})超过最大限制({MAX_DEPTH})，截断后: {path_segments[:MAX_DEPTH]}")
            path_segments = path_segments[:MAX_DEPTH]
        
        logger.info(f"URL路径解析: {url} -> 路径段: {path_segments}")
        
        # 从根文件夹开始，逐级创建或获取子文件夹
        current_folder = root_folder
        
        for i, segment in enumerate(path_segments):
            folder_slug = to_slug(segment)
            if not folder_slug:
                folder_slug = f"folder-{i+1}"
            
            expected_path = f"{current_folder.path}/{folder_slug}" if current_folder.path else f"/{folder_slug}"
            
            # 查找是否存在同路径的子文件夹
            subfolder = db.query(Folder).filter(
                Folder.path == expected_path
            ).first()
            
            if subfolder:
                current_folder = subfolder
                continue
            
            logger.info(f"创建子文件夹: {folder_slug} (原始路径段: {segment})，父文件夹: {current_folder.name}")
            
            full_path = '/' + '/'.join(path_segments[:i+1])
            description = f"Auto-created folder for crawled website path: {full_path}"
            
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
            
            current_folder = new_folder
        
        logger.info(f"URL {url} 对应的文件夹路径: {current_folder.path}")
        return current_folder.path
        
    except Exception as e:
        logger.error(f"获取URL对应文件夹失败: {url}, 错误: {str(e)}")
        return root_folder_path


logger = logging.getLogger(__name__)

class WebsiteCrawler:
    """网站爬取器"""
    
    def __init__(self, db: Session, task_id: str = None):
        self.db = db
        self.task_id = task_id
        self.visited_urls: Set[str] = set()
        self.session = requests.Session()
        # 禁用SSL验证（开发环境）
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def _update_task_status(self, status: str = None, current_status: str = None, 
                          pages_crawled: int = None, pages_processed: int = None,
                          images_crawled: int = None, progress: int = None,
                          current_url: str = None, stats: Dict[str, Any] = None):
        """更新爬取任务状态"""
        if not self.task_id:
            return
        
        try:
            from ..models.crawl_task import CrawlTask, CrawlTaskStatus
            
            crawl_task = self.db.query(CrawlTask).filter(CrawlTask.task_id == self.task_id).first()
            if not crawl_task:
                return
            
            # 更新字段
            if status:
                crawl_task.status = CrawlTaskStatus[status.upper()] if hasattr(CrawlTaskStatus, status.upper()) else status
            if current_status:
                crawl_task.current_status = current_status[:500]  # 限制长度
            if pages_crawled is not None:
                crawl_task.pages_crawled = pages_crawled
            if pages_processed is not None:
                crawl_task.pages_processed = pages_processed
            if images_crawled is not None:
                crawl_task.images_crawled = images_crawled
            if current_url:
                crawl_task.current_url = current_url[:2000]
            if stats:
                crawl_task.stats = stats
            
            # 计算进度（如果有总页面数）
            if progress is not None:
                crawl_task.progress = progress
            elif crawl_task.total_pages > 0 and pages_crawled is not None:
                crawl_task.progress = min(100, int((pages_crawled / crawl_task.total_pages) * 100))
            
            # 更新时间戳
            from datetime import datetime
            crawl_task.updated_at = datetime.now()
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"更新任务状态失败: {self.task_id}, 错误: {str(e)}")
            # 忽略错误，不中断爬取
    
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
        爬取网站
        
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
        
        # 解析基础URL
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        logger.info(f"开始爬取网站: {url}, 深度: {depth}, 文件夹: {folder.name}")
        
        # 更新任务状态为爬取中
        self._update_task_status(
            status="crawling",
            current_status=f"Starting crawl: {url}",
            current_url=url
        )
        
        # 初始化统计
        stats = {
            'total_pages': 0,
            'successful_pages': 0,
            'failed_pages': 0,
            'skipped_pages': 0,  # 新增：跳过的页面数（未修改）
            'total_images': 0,
            'downloaded_images': 0,
            'failed_images': 0,
            'start_time': time.time(),
            'urls': []
        }
        
        # 检查robots.txt（简化版）
        if respect_robots_txt:
            try:
                robots_url = urljoin(base_url, '/robots.txt')
                robots_response = self.session.get(robots_url, timeout=5)
                if robots_response.status_code == 200:
                    logger.info(f"找到robots.txt: {robots_url}")
                    # 这里可以解析robots.txt，但为了简化，我们只记录
            except:
                pass  # 忽略robots.txt错误
        
        # 开始爬取
        try:
            self._crawl_recursive(
                url=url,
                base_url=base_url,
                current_depth=0,
                max_depth=depth,
                include_images=include_images,
                follow_external_links=follow_external_links,
                stats=stats
            )
        except Exception as e:
            logger.error(f"爬取过程中发生错误: {str(e)}")
            stats['error'] = str(e)
            # 更新任务状态为失败
            self._update_task_status(
                status="failed",
                current_status=f"Crawl failed: {str(e)[:100]}",
                stats=stats
            )
            raise
        
        # 计算总时间
        stats['total_time'] = time.time() - stats['start_time']
        logger.info(f"爬取完成: 总计 {stats['total_pages']} 页, 成功 {stats['successful_pages']} 页, 失败 {stats['failed_pages']} 页, 时间 {stats['total_time']:.2f}秒")
        
        # 更新最终状态
        self._update_task_status(
            status="completed",
            current_status=f"Crawl complete: {stats['total_pages']} pages, {stats['successful_pages']} successful",
            pages_crawled=stats['total_pages'],
            pages_processed=stats['successful_pages'],
            images_crawled=stats['total_images'],
            progress=100,
            stats=stats
        )
        
        return stats
    
    def _crawl_recursive(
        self,
        url: str,
        base_url: str,
        current_depth: int,
        max_depth: int,
        folder_path: str,
        include_images: bool,
        follow_external_links: bool,
        stats: Dict[str, Any]
    ):
        """递归爬取URL"""
        # 检查深度限制
        if current_depth > max_depth:
            return
        
        # 检查是否已访问
        if url in self.visited_urls:
            return
        
        # 标记为已访问
        self.visited_urls.add(url)
        stats['total_pages'] += 1
        
        logger.info(f"爬取: {url} (深度 {current_depth}/{max_depth})")
        
        # 更新任务状态（每10个页面更新一次，避免过多数据库操作）
        if stats['total_pages'] % 10 == 0:
            self._update_task_status(
                current_status=f"Crawling: {url[:100]}...",
                current_url=url,
                pages_crawled=stats['total_pages'],
                pages_processed=stats['successful_pages'],
                images_crawled=stats['total_images']
            )
        
        try:
            # 检查是否有相同URL的现有文档
            existing_doc = None
            last_modified_from_db = None
            
            # 查询具有相同URL的现有文档（URL存储在document_metadata['url']中）
            # 使用更高效的查询：查找document_metadata中包含指定URL的文档
            from ..models.document import Document
            from sqlalchemy import func
            
            # 方法1：使用JSON_EXTRACT（SQLite）或直接查询JSON字段
            try:
                # 尝试使用JSON查询
                existing_doc = self.db.query(Document).filter(
                    Document.document_metadata['url'].astext == url
                ).first()
            except Exception as e:
                logger.warning(f"JSON查询失败，使用全表扫描: {e}")
                # 回退到全表扫描
                all_docs = self.db.query(Document).all()
                for doc in all_docs:
                    if doc.document_metadata and 'url' in doc.document_metadata:
                        if doc.document_metadata['url'] == url:
                            existing_doc = doc
                            break
            
            if existing_doc:
                # 获取存储的last_modified时间戳
                if existing_doc.document_metadata and 'last_modified' in existing_doc.document_metadata:
                    last_modified_from_db = existing_doc.document_metadata['last_modified']
            
            # 准备请求头
            headers = {}
            if last_modified_from_db:
                # 将存储的时间戳转换为HTTP日期格式
                # 假设last_modified_from_db是字符串格式的时间戳
                try:
                    # 如果是unix时间戳，转换为datetime
                    if isinstance(last_modified_from_db, (int, float)):
                        import datetime
                        dt = datetime.datetime.fromtimestamp(last_modified_from_db, tz=datetime.timezone.utc)
                        headers['If-Modified-Since'] = email.utils.format_datetime(dt, usegmt=True)
                    elif isinstance(last_modified_from_db, str):
                        # 假设已经是HTTP日期格式
                        headers['If-Modified-Since'] = last_modified_from_db
                except Exception as e:
                    logger.warning(f"无法解析last_modified时间戳: {last_modified_from_db}, 错误: {e}")
            
            # 获取页面
            response = self.session.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            
            # 检查是否为304 Not Modified（内容未修改）
            if response.status_code == 304:
                logger.info(f"页面未修改，跳过: {url}")
                stats['skipped_pages'] = stats.get('skipped_pages', 0) + 1
                stats['urls'].append({
                    'url': url,
                    'title': existing_doc.title if existing_doc else 'Unknown',
                    'status': 'skipped_not_modified',
                    'document_id': existing_doc.path if existing_doc else None
                })
                return
            
            # 获取当前页面的Last-Modified头
            last_modified_header = response.headers.get('Last-Modified')
            current_last_modified = None
            
            # 如果页面提供了Last-Modified头，检查是否与存储的相同
            if last_modified_header and existing_doc:
                try:
                    # 解析HTTP日期格式
                    parsed_date = email.utils.parsedate_to_datetime(last_modified_header)
                    current_last_modified = parsed_date.timestamp()
                    
                    # 比较与存储的时间戳
                    if last_modified_from_db and abs(current_last_modified - float(last_modified_from_db)) < 1:
                        logger.info(f"页面last_modified未变化，跳过: {url}")
                        stats['skipped_pages'] = stats.get('skipped_pages', 0) + 1
                        stats['urls'].append({
                            'url': url,
                            'title': existing_doc.title if existing_doc else 'Unknown',
                            'status': 'skipped_not_modified',
                            'document_id': existing_doc.path if existing_doc else None
                        })
                        return
                except Exception as e:
                    logger.warning(f"无法解析Last-Modified头: {last_modified_header}, 错误: {e}")
            
            # 解析HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 提取页面标题
            title = soup.title.string if soup.title else url
            # 清理标题
            title = re.sub(r'\s+', ' ', title).strip()[:200]  # 限制长度
            
            # 提取主要内容 - 更智能的内容提取
            # 首先尝试常见的内容区域选择器
            main_content = None
            content_selectors = [
                'main',
                'article',
                '.main-content',
                '#content',
                '.content',
                '#main',
                '.post-content',
                '.entry-content',
                '.article-content',
                '.story-content',
                '#article',
                '.article',
                'section',
                '.section'
            ]
            
            for selector in content_selectors:
                if selector.startswith('.') or selector.startswith('#'):
                    main_content = soup.select_one(selector)
                else:
                    main_content = soup.find(selector)
                if main_content:
                    logger.debug(f"使用内容选择器找到内容区域: {selector}")
                    break
            
            # 如果没找到，尝试启发式方法：找到包含最多文本的div
            if not main_content:
                # 找到所有div元素，计算文本长度
                divs = soup.find_all('div')
                if divs:
                    # 排除常见的非内容容器
                    non_content_classes = ['nav', 'navigation', 'menu', 'header', 'footer', 
                                         'sidebar', 'aside', 'ad', 'advertisement', 'banner',
                                         'comments', 'related', 'widget', 'social', 'share']
                    
                    best_div = None
                    max_text_length = 0
                    
                    for div in divs:
                        # 跳过非内容div
                        div_classes = div.get('class', [])
                        if isinstance(div_classes, str):
                            div_classes = [div_classes]
                        
                        # 检查是否包含非内容类
                        is_non_content = False
                        for cls in div_classes:
                            if any(nc in cls.lower() for nc in non_content_classes):
                                is_non_content = True
                                break
                        
                        if is_non_content:
                            continue
                        
                        # 计算文本长度
                        text = div.get_text()
                        text_length = len(text.strip())
                        
                        if text_length > max_text_length and text_length > 100:  # 至少100字符
                            max_text_length = text_length
                            best_div = div
                    
                    if best_div:
                        main_content = best_div
                        logger.debug("使用启发式方法找到内容区域")
            
            # 如果还是没找到，使用body
            if not main_content:
                main_content = soup.find('body')
                if main_content:
                    logger.debug("使用body作为内容区域")
            
            # 从选定的内容区域提取文本
            if main_content:
                # 创建副本以避免修改原始soup
                content_area = BeautifulSoup(str(main_content), 'html.parser')
                
                # 移除常见的非内容元素
                non_content_tags = [
                    'nav', 'header', 'footer', 'aside', 'script', 'style',
                    'iframe', 'form', 'button', 'input', 'select', 'textarea'
                ]
                
                for tag in non_content_tags:
                    for element in content_area.find_all(tag):
                        element.decompose()
                
                # 移除广告和社交分享元素
                ad_selectors = ['.ad', '.advertisement', '.banner', '.ads', 
                              '.social', '.share', '.comments', '.related']
                for selector in ad_selectors:
                    for element in content_area.select(selector):
                        element.decompose()
                
                content = content_area.get_text()
            else:
                content = soup.get_text()
            
            # 清理内容：移除多余空白
            content = re.sub(r'\s+', ' ', content).strip()
            
            # 清理内容
            content = re.sub(r'\s+', ' ', content).strip()
            
            # 提取元描述
            meta_description = ''
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                meta_description = meta_desc['content']
            
            # 从URL提取原始文件名
            parsed_url = urlparse(url)
            url_path = parsed_url.path
            if url_path.endswith('/'):
                url_path = url_path[:-1]
            original_filename = os.path.basename(url_path) if url_path else "index"
            if not original_filename or '.' not in original_filename:
                original_filename = f"{original_filename or 'index'}.html"
            
            # 根据URL路径获取或创建对应的文件夹
            # 使用根文件夹路径（用户选择的文件夹）作为起点
            # 用户名使用"system"，因为爬虫是系统任务
            folder_id_for_url = get_folder_for_url(
                db=self.db,
                root_folder_path=folder_path,
                url=url,
                username="system"
            )
            
            # 创建文档
            document_data = DocumentCreate(
                title=title[:100],  # 确保不超过数据库限制
                description=f"Webpage crawled from {url}\n{meta_description}"[:500],
                original_filename=original_filename,
                file_size=len(response.content),
                file_type=FileType.HTML,
                mime_type="text/html",
                folder_path=folder_id_for_url,
                uploaded_by="4dad6fa1-d521-417f-8877-efe95fcf1f04",  # 管理员用户ID
                original_url=url,
                document_metadata={
                    'crawled_at': time.time(),
                    'depth': current_depth,
                    'url': url,
                    'response_status': response.status_code,
                    'content_length': len(response.content),
                    'content_type': response.headers.get('Content-Type', ''),
                    'crawler': 'website_crawler',
                    'extracted_text': content[:5000] if content else None,  # 保存提取的文本用于预览
                    'original_html': response.text[:10000] if response.text else None,  # 保存原始HTML用于下载
                    'last_modified': current_last_modified if current_last_modified else time.time()  # 存储last_modified时间戳
                }
            )
            
            # 保存到数据库
            try:
                # 获取HTML内容
                html_content = response.text
                
                # 检查HTML内容是否有效
                if not html_content or not html_content.strip():
                    logger.warning(f"HTML内容为空或只包含空白字符: {url}")
                    # 尝试使用提取的内容作为后备
                    if content and content.strip():
                        logger.info(f"使用提取的内容作为HTML内容，长度: {len(content)}")
                        html_content = content
                    else:
                        logger.error(f"无法获取有效的HTML内容，跳过页面: {url}")
                        stats['failed_pages'] += 1
                        stats['urls'].append({
                            'url': url,
                            'title': title,
                            'status': 'empty_content',
                            'error': 'HTML内容为空'
                        })
                        return
                
                # 调用create_document保存文档
                logger.debug(f"_crawl_recursive: 调用create_document, html_content长度: {len(html_content) if html_content else 0}, 预览: {repr(html_content[:200] if html_content else '')}")
                document = create_document(
                    db=self.db,
                    document_data=document_data,
                    folder_path=folder_id_for_url,
                    html_content=html_content
                )
                logger.info(f"文档保存成功: ID={document.path}, 标题='{title}'")
                
                # 记录成功
                stats['successful_pages'] += 1
                stats['urls'].append({
                    'url': url,
                    'title': title,
                    'status': 'success',
                    'document_id': document.path
                })
                
                logger.info(f"成功爬取并保存页面: {title}")
                
                # 每5个成功页面更新一次任务状态
                if stats['successful_pages'] % 5 == 0:
                    self._update_task_status(
                        current_status=f"Processed {stats['successful_pages']} pages, crawling...",
                        pages_processed=stats['successful_pages']
                    )
                
            except Exception as e:
                logger.error(f"保存文档失败: {str(e)}")
                stats['failed_pages'] += 1
                stats['urls'].append({
                    'url': url,
                    'title': title,
                    'status': 'save_failed',
                    'error': str(e)
                })
                # 不再继续处理此页面的链接
                return
            
            # 提取图像（如果启用）
            if include_images and current_depth < max_depth:
                self._extract_images(soup, url, folder_path, base_url, stats)
            
            # 提取内部链接（递归爬取）
            if current_depth < max_depth:
                internal_links = self._extract_internal_links(soup, url, base_url)
                for link_url in internal_links:
                    if link_url not in self.visited_urls:
                        # 避免无限递归
                        if len(self.visited_urls) < 500:  # 安全限制，从100放宽到500
                            self._crawl_recursive(
                                url=link_url,
                                base_url=base_url,
                                current_depth=current_depth + 1,
                                max_depth=max_depth,
                                include_images=include_images,
                                follow_external_links=follow_external_links,
                                stats=stats
                            )
            
        except requests.RequestException as e:
            logger.error(f"爬取失败 {url}: {str(e)}")
            stats['failed_pages'] += 1
            stats['urls'].append({
                'url': url,
                'title': '',
                'status': 'failed',
                'error': str(e)
            })
        except Exception as e:
            logger.error(f"处理页面时出错 {url}: {str(e)}")
            stats['failed_pages'] += 1
            stats['urls'].append({
                'url': url,
                'title': '',
                'status': 'error',
                'error': str(e)
            })
    
    def _extract_images(self, soup: BeautifulSoup, page_url: str, folder_path: str, base_url: str, stats: Dict[str, Any]):
        """提取并下载页面中的图像"""
        img_tags = soup.find_all('img')
        
        for img in img_tags:
            img_url = img.get('src')
            if not img_url:
                continue
            
            # 处理相对URL
            img_url = urljoin(page_url, img_url)
            
            # 检查是否有效图像URL
            parsed = urlparse(img_url)
            if not parsed.scheme or not parsed.netloc:
                continue
            
            # 检查图片扩展名
            img_path = parsed.path.lower()
            supported_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.ico'}
            if not any(img_path.endswith(ext) for ext in supported_extensions):
                # 没有扩展名或不受支持的扩展名，跳过
                continue
            
            # 跳过外部域名的图片（只下载当前站点域名下的图片）
            if parsed.netloc != urlparse(base_url).netloc:
                logger.debug(f"跳过外部域名图片: {img_url}")
                continue
            
            # 统计
            stats['total_images'] += 1
            
            try:
                # 下载图片
                img_response = self.session.get(img_url, timeout=10)
                img_response.raise_for_status()
                
                # 检查内容类型
                content_type = img_response.headers.get('Content-Type', '')
                if not content_type.startswith('image/'):
                    logger.debug(f"跳过非图片内容: {img_url} (Content-Type: {content_type})")
                    continue
                
                # 获取图片文件名
                img_filename = os.path.basename(parsed.path)
                if not img_filename or '.' not in img_filename:
                    # 生成基于哈希的文件名
                    import hashlib
                    img_hash = hashlib.md5(img_response.content).hexdigest()[:8]
                    # 从Content-Type推断扩展名
                    ext_map = {
                        'image/jpeg': '.jpg',
                        'image/jpg': '.jpg',
                        'image/png': '.png',
                        'image/gif': '.gif',
                        'image/webp': '.webp',
                        'image/bmp': '.bmp',
                        'image/svg+xml': '.svg',
                        'image/x-icon': '.ico'
                    }
                    ext = ext_map.get(content_type, '.jpg')
                    img_filename = f"img_{img_hash}{ext}"
                
                # 根据图片URL路径获取或创建对应的文件夹
                # 使用与HTML页面相同的路径逻辑
                img_folder_id = get_folder_for_url(
                    db=self.db,
                    root_folder_path=folder_path,
                    url=img_url,
                    username="system"
                )
                
                # 创建图片文档
                img_alt = img.get('alt', '')
                img_title = img.get('title', '')
                
                # 生成图片文档的描述
                img_description = f"Image from {page_url}"
                if img_alt:
                    img_description += f", 替代文本: {img_alt}"
                if img_title:
                    img_description += f", 标题: {img_title}"
                
                # 创建图片文档数据
                img_document_data = DocumentCreate(
                    title=img_filename[:100],
                    description=img_description[:500],
                    original_filename=img_filename,
                    file_size=len(img_response.content),
                    file_type=get_filetype_for_filename(img_filename),
                    mime_type=content_type,
                    folder_path=img_folder_id,
                    uploaded_by="4dad6fa1-d521-417f-8877-efe95fcf1f04",  # 管理员用户ID
                    original_url=img_url,
                    document_metadata={
                        'crawled_at': time.time(),
                        'source_page': page_url,
                        'url': img_url,
                        'alt_text': img_alt,
                        'title': img_title,
                        'response_status': img_response.status_code,
                        'content_type': content_type,
                        'crawler': 'website_crawler',
                        'dimensions': 'unknown'  # TODO: 可以尝试解析图片尺寸
                    }
                )
                
                # 保存图片文档
                try:
                    # 对于图片，我们保存二进制内容
                    import tempfile
                    from pathlib import Path
                    
                    # 生成存储时的安全路径（将文件夹路径中的/替换为_）
                    safe_dir_name = img_folder_id.strip('/').replace('/', '_') or 'images'
                    
                    # 创建基于安全目录名的图片存储目录
                    img_docs_dir = Path("data/documents") / safe_dir_name
                    img_docs_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 构建图片文件路径
                    img_file_path = img_docs_dir / img_filename
                    img_storage_path = str(Path(safe_dir_name) / img_filename)
                    
                    # 保存图片文件
                    with open(img_file_path, 'wb') as f:
                        f.write(img_response.content)
                    
                    # 创建数据库记录（使用现有的create_document函数，但需要修改以支持二进制内容）
                    # 暂时直接创建文档记录
                    # 检查是否已存在相同路径的图片文档（防止重复）
                    img_doc_path = f"{img_folder_id}/{img_filename}"
                    existing_img_doc = self.db.query(Document).filter(Document.path == img_doc_path).first()
                    if existing_img_doc:
                        logger.warning(f"图片文档已存在，跳过创建: path='{img_doc_path}'")
                        # 统计跳过的图片
                        stats['skipped_images'] = stats.get('skipped_images', 0) + 1
                        continue
                    
                    # 创建图片文档记录（纯path架构，无id/folder_id）
                    img_document = Document(
                        path=img_doc_path,
                        title=img_filename[:100],
                        description=img_description[:500],
                        original_filename=img_filename,
                        stored_filename=img_filename,
                        storage_path=img_storage_path,
                        file_type=get_filetype_for_filename(img_filename),
                        file_size=len(img_response.content),
                        mime_type=content_type,
                        folder_path=img_folder_id,
                        document_metadata=img_document_data.document_metadata or {},
                        status=DocumentStatus.ACTIVE,
                        uploaded_by=str(img_document_data.uploaded_by),
                        conversion_status=ConversionStatus.PENDING
                    )
                    
                    self.db.add(img_document)
                    self.db.commit()
                    
                    # 统计成功下载的图片
                    stats['downloaded_images'] = stats.get('downloaded_images', 0) + 1
                    logger.info(f"图片下载成功: {img_filename} ({len(img_response.content)} bytes)")
                    
                    # 每10个图片更新一次任务状态
                    if stats['downloaded_images'] % 10 == 0:
                        self._update_task_status(
                            current_status=f"Downloaded {stats['downloaded_images']} images...",
                            images_crawled=stats['downloaded_images']
                        )
                    
                except Exception as e:
                    logger.error(f"保存图片失败 {img_url}: {str(e)}")
                    stats['failed_images'] = stats.get('failed_images', 0) + 1
                
            except Exception as e:
                logger.error(f"下载图片失败 {img_url}: {str(e)}")
                stats['failed_images'] = stats.get('failed_images', 0) + 1
            
            # 限制日志输出
            if stats['total_images'] <= 5:
                logger.debug(f"处理图片: {img_url}")
    
    def _extract_internal_links(self, soup: BeautifulSoup, page_url: str, base_url: str) -> List[str]:
        """提取内部链接"""
        links = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            # 跳过空链接、JavaScript链接等
            if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                continue
            
            # 处理相对URL
            full_url = urljoin(page_url, href)
            
            # 解析URL
            parsed = urlparse(full_url)
            
            # 检查是否为内部链接（相同域名）
            if parsed.netloc == urlparse(base_url).netloc:
                # 确保是HTTP/HTTPS
                if parsed.scheme in ('http', 'https'):
                    links.append(full_url)
        
        # 去重
        return list(set(links))


def crawl_website_task(
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
    后台任务：爬取网站（使用Scrapling框架）
    """
    logger.info(f"开始后台爬取任务 {task_id}: {url}")
    
    try:
        # 使用Scrapling爬虫（针对Canada.ca等JavaScript网站启用动态渲染）
        crawler = ScraplingCrawler(db, task_id=task_id, use_stealth=False, use_dynamic=True)
        stats = crawler.crawl(
            url=url,
            depth=depth,
            folder_path=folder_path,
            include_images=include_images,
            follow_external_links=follow_external_links,
            respect_robots_txt=respect_robots_txt
        )
        
        logger.info(f"Scrapling爬取任务 {task_id} 完成: {stats}")
        
        # TODO: 保存任务结果到数据库或缓存
        
        return {
            'task_id': task_id,
            'status': 'completed',
            'stats': stats,
            'success': True
        }
        
    except Exception as e:
        logger.error(f"Scrapling爬取任务 {task_id} 失败: {str(e)}")
        return {
            'task_id': task_id,
            'status': 'failed',
            'error': str(e),
            'success': False
        }