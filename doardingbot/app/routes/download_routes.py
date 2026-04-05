"""
Two-step web page processing for DoardingBot
Step 1: Download web pages to local directory
Step 2: Extract information based on different scenarios
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
import logging
import os
from pathlib import Path
import uuid
import datetime
import hashlib

from app.services.scraper_service import ScraperService
from app.services.image_service import ImageExtractionService

router = APIRouter(prefix="/api/download", tags=["download"])
logger = logging.getLogger(__name__)

# Base directory for downloads
BASE_DOWNLOAD_DIR = Path(__file__).parent.parent.parent / "downloads"

class DownloadRequest(BaseModel):
    """Request to download web pages"""
    urls: List[HttpUrl]
    download_images: bool = False
    preserve_structure: bool = True  # Preserve original directory structure

class DownloadResponse(BaseModel):
    """Response for download operation"""
    job_id: str
    status: str  # processing, completed, failed
    message: str
    downloads: List[Dict[str, Any]] = []
    download_dir: Optional[str] = None
    errors: List[str] = []

class ProcessRequest(BaseModel):
    """Request to process downloaded pages"""
    download_dir: str  # Directory containing downloaded pages
    extraction_type: str = "basic"  # basic, news, technical, ecommerce, custom
    custom_pattern: Optional[str] = None
    extract_images: bool = True

class ProcessResponse(BaseModel):
    """Response for processing operation"""
    job_id: str
    status: str
    message: str
    extracted_data: List[Dict[str, Any]] = []
    errors: List[str] = []

def create_download_directory() -> Path:
    """Create a unique download directory for this job"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    job_id = str(uuid.uuid4())[:8]
    dir_name = f"download_{timestamp}_{job_id}"
    download_dir = BASE_DOWNLOAD_DIR / dir_name
    download_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    (download_dir / "html").mkdir(exist_ok=True)
    (download_dir / "images").mkdir(exist_ok=True)
    (download_dir / "metadata").mkdir(exist_ok=True)
    
    return download_dir

def sanitize_filename(url: str) -> str:
    """Create a safe filename from URL"""
    # Remove protocol and special characters
    import re
    filename = re.sub(r'^https?://', '', url)
    filename = re.sub(r'[^\w\-_.]', '_', filename)
    filename = filename[:200]  # Limit length
    
    # Add hash for uniqueness
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"{filename}_{url_hash}"

@router.post("/pages", response_model=DownloadResponse)
async def download_pages(request: DownloadRequest):
    """
    Step 1: Download web pages to local directory
    
    - Downloads HTML content
    - Optionally downloads images
    - Saves to organized local directory structure
    - Returns download directory path for next step
    """
    job_id = str(uuid.uuid4())
    logger.info(f"Starting download job {job_id} for {len(request.urls)} URLs")
    
    response = DownloadResponse(
        job_id=job_id,
        status="processing",
        message=f"Downloading {len(request.urls)} pages",
        downloads=[],
        download_dir=None,
        errors=[]
    )
    
    try:
        # Create download directory
        download_dir = create_download_directory()
        response.download_dir = str(download_dir)
        
        # Initialize services with longer timeout for government websites
        scraper = ScraperService(timeout=60)
        
        # Process each URL
        for url in request.urls:
            url_str = str(url)
            download_record = {
                "url": url_str,
                "status": "pending",
                "html_file": None,
                "image_files": [],
                "metadata_file": None,
                "error": None
            }
            
            try:
                logger.info(f"Downloading page: {url_str}")
                
                # Step 1: Fetch page content
                scrape_result = scraper.scrape_url(url_str)
                
                if not scrape_result.get("success", False):
                    error_msg = f"Failed to download {url_str}: {scrape_result.get('error', 'Unknown error')}"
                    logger.error(error_msg)
                    download_record["status"] = "failed"
                    download_record["error"] = error_msg
                    response.errors.append(error_msg)
                    response.downloads.append(download_record)
                    continue
                
                # Step 2: Save HTML content
                html_content = scrape_result.get("html", "")
                html_filename = sanitize_filename(url_str) + ".html"
                html_filepath = download_dir / "html" / html_filename
                
                with open(html_filepath, "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                download_record["html_file"] = str(html_filepath)
                
                # Step 3: Save metadata
                metadata = {
                    "url": url_str,
                    "title": scrape_result.get("title", ""),
                    "language": scrape_result.get("language", "en"),
                    "downloaded_at": datetime.datetime.now().isoformat(),
                    "original_metadata": scrape_result.get("metadata", {})
                }
                
                import json
                metadata_filename = sanitize_filename(url_str) + ".json"
                metadata_filepath = download_dir / "metadata" / metadata_filename
                
                with open(metadata_filepath, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                
                download_record["metadata_file"] = str(metadata_filepath)
                
                # Step 4: Download images (if requested)
                if request.download_images and scrape_result.get("content"):
                    try:
                        image_service = ImageExtractionService()
                        html_content_for_images = scrape_result.get("content", "")
                        images_info = image_service.extract_images_from_html(html_content_for_images, url_str)
                        
                        # Download first 5 images (limit)
                        image_urls = [img["url"] for img in images_info[:5]]
                        download_results = image_service.batch_download_images(
                            image_urls, 
                            download_dir / "images"
                        )
                        
                        for download_result in download_results["successful"]:
                            image_record = {
                                "original_url": download_result["original_url"],
                                "local_path": download_result["local_path"],
                                "file_size": download_result["file_size"],
                                "mime_type": download_result["mime_type"]
                            }
                            download_record["image_files"].append(image_record)
                        
                        for failed_url in download_results["failed"]:
                            logger.warning(f"Failed to download image: {failed_url}")
                    
                    except Exception as e:
                        error_msg = f"Failed to download images for {url_str}: {str(e)}"
                        logger.error(error_msg)
                        # Don't fail the whole download if images fail
                
                download_record["status"] = "completed"
                response.downloads.append(download_record)
                
                logger.info(f"Successfully downloaded {url_str} to {html_filepath}")
                
            except Exception as e:
                error_msg = f"Error processing URL {url_str}: {str(e)}"
                logger.error(error_msg)
                download_record["status"] = "failed"
                download_record["error"] = error_msg
                response.errors.append(error_msg)
                response.downloads.append(download_record)
        
        # Update response status
        completed = sum(1 for d in response.downloads if d["status"] == "completed")
        failed = sum(1 for d in response.downloads if d["status"] == "failed")
        
        if failed == len(request.urls):
            response.status = "failed"
            response.message = f"All {len(request.urls)} downloads failed"
        elif failed > 0:
            response.status = "completed_with_errors"
            response.message = f"Downloaded {completed} pages with {failed} errors"
        else:
            response.status = "completed"
            response.message = f"Successfully downloaded {completed} pages"
        
        logger.info(f"Download job {job_id} completed: {response.message}")
        logger.info(f"Download directory: {download_dir}")
        
        return response
        
    except Exception as e:
        error_msg = f"Unexpected error in download job {job_id}: {str(e)}"
        logger.error(error_msg)
        response.status = "failed"
        response.message = error_msg
        response.errors.append(error_msg)
        return response

@router.post("/process", response_model=ProcessResponse)
async def process_downloaded_pages(request: ProcessRequest):
    """
    Step 2: Extract information from downloaded pages
    
    - Processes HTML files from download directory
    - Different extraction types: basic, news, technical, ecommerce
    - Returns structured extracted data
    """
    job_id = str(uuid.uuid4())
    logger.info(f"Starting processing job {job_id} for directory: {request.download_dir}")
    
    response = ProcessResponse(
        job_id=job_id,
        status="processing",
        message=f"Processing pages from {request.download_dir}",
        extracted_data=[],
        errors=[]
    )
    
    try:
        download_dir = Path(request.download_dir)
        if not download_dir.exists():
            raise HTTPException(status_code=404, detail=f"Download directory not found: {download_dir}")
        
        # Find HTML files
        html_dir = download_dir / "html"
        if not html_dir.exists():
            raise HTTPException(status_code=404, detail=f"HTML directory not found: {html_dir}")
        
        html_files = list(html_dir.glob("*.html"))
        if not html_files:
            raise HTTPException(status_code=404, detail=f"No HTML files found in {html_dir}")
        
        logger.info(f"Found {len(html_files)} HTML files to process")
        
        # Initialize services
        scraper = ScraperService(timeout=60)
        image_service = ImageExtractionService()
        
        # Process each HTML file
        for html_file in html_files:
            try:
                logger.info(f"Processing file: {html_file.name}")
                
                # Read HTML content
                with open(html_file, "r", encoding="utf-8") as f:
                    html_content = f.read()
                
                # Find corresponding metadata file
                metadata_file = download_dir / "metadata" / html_file.with_suffix(".json").name
                metadata = {}
                if metadata_file.exists():
                    import json
                    with open(metadata_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                
                # Extract information based on type
                extracted = {
                    "file": str(html_file),
                    "metadata": metadata,
                    "extraction_type": request.extraction_type,
                    "data": {}
                }
                
                if request.extraction_type == "basic":
                    # Basic extraction: title, main content, images
                    extracted["data"] = extract_basic_info(html_content, metadata.get("url", ""))
                
                elif request.extraction_type == "news":
                    # News article extraction
                    extracted["data"] = extract_news_info(html_content, metadata.get("url", ""))
                
                elif request.extraction_type == "technical":
                    # Technical documentation extraction
                    extracted["data"] = extract_technical_info(html_content, metadata.get("url", ""))
                
                elif request.extraction_type == "ecommerce":
                    # E-commerce product extraction
                    extracted["data"] = extract_ecommerce_info(html_content, metadata.get("url", ""))
                
                elif request.extraction_type == "custom" and request.custom_pattern:
                    # Custom pattern extraction (simplified)
                    extracted["data"] = extract_with_custom_pattern(
                        html_content, 
                        metadata.get("url", ""),
                        request.custom_pattern
                    )
                
                else:
                    # Default to basic
                    extracted["data"] = extract_basic_info(html_content, metadata.get("url", ""))
                
                # Extract image information if requested
                if request.extract_images:
                    images_dir = download_dir / "images"
                    if images_dir.exists():
                        image_files = list(images_dir.glob("*"))
                        extracted["images"] = [
                            {
                                "path": str(img),
                                "name": img.name,
                                "size": img.stat().st_size if img.exists() else 0
                            }
                            for img in image_files[:10]  # Limit to 10 images
                        ]
                
                response.extracted_data.append(extracted)
                
                logger.info(f"Successfully processed {html_file.name}")
                
            except Exception as e:
                error_msg = f"Error processing file {html_file.name}: {str(e)}"
                logger.error(error_msg)
                response.errors.append(error_msg)
        
        # Update response status
        if response.errors and len(response.errors) == len(html_files):
            response.status = "failed"
            response.message = f"All {len(html_files)} files failed"
        elif response.errors:
            response.status = "completed_with_errors"
            response.message = f"Processed {len(html_files)} files with {len(response.errors)} errors"
        else:
            response.status = "completed"
            response.message = f"Successfully processed {len(html_files)} files"
        
        logger.info(f"Processing job {job_id} completed: {response.message}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Unexpected error in processing job {job_id}: {str(e)}"
        logger.error(error_msg)
        response.status = "failed"
        response.message = error_msg
        response.errors.append(error_msg)
        return response

def extract_basic_info(html_content: str, url: str) -> Dict[str, Any]:
    """Extract basic information from HTML"""
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract title
    title = soup.title.string if soup.title else ""
    
    # Extract main content (simplified - just get body text)
    body = soup.body
    content = body.get_text(strip=True)[:5000] if body else ""
    
    # Extract meta description
    description = ""
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        description = meta_desc["content"]
    
    # Extract images (count)
    images = soup.find_all("img")
    image_count = len(images)
    
    # Extract links (count)
    links = soup.find_all("a", href=True)
    link_count = len(links)
    
    return {
        "title": title,
        "description": description,
        "content_preview": content[:500] + "..." if len(content) > 500 else content,
        "content_length": len(content),
        "image_count": image_count,
        "link_count": link_count,
        "language": detect_language(soup),
        "extracted_at": datetime.datetime.now().isoformat()
    }

def extract_news_info(html_content: str, url: str) -> Dict[str, Any]:
    """Extract news article information"""
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Try to find common news article patterns
    article_title = ""
    article_content = ""
    publish_date = ""
    author = ""
    
    # Look for Open Graph tags
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        article_title = og_title["content"]
    
    # Look for article body
    article_body = soup.find("article") or soup.find("div", class_=lambda x: x and any(cls in str(x).lower() for cls in ["article", "post", "content", "body"]))
    if article_body:
        article_content = article_body.get_text(strip=True)[:10000]
    
    # Look for publish date
    time_tag = soup.find("time")
    if time_tag and time_tag.get("datetime"):
        publish_date = time_tag["datetime"]
    
    # Look for author
    author_tag = soup.find("meta", attrs={"name": "author"}) or soup.find("span", class_=lambda x: x and "author" in str(x).lower())
    if author_tag:
        if hasattr(author_tag, "get"):
            author = author_tag.get("content", "") or author_tag.get_text(strip=True)
        else:
            author = author_tag.get_text(strip=True)
    
    return {
        "article_title": article_title or (soup.title.string if soup.title else ""),
        "article_content": article_content[:1000] + "..." if len(article_content) > 1000 else article_content,
        "publish_date": publish_date,
        "author": author,
        "word_count": len(article_content.split()),
        "is_news_article": bool(article_content),
        "extracted_at": datetime.datetime.now().isoformat()
    }

def extract_technical_info(html_content: str, url: str) -> Dict[str, Any]:
    """Extract technical documentation information"""
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for code blocks
    code_blocks = soup.find_all(["code", "pre"])
    code_count = len(code_blocks)
    
    # Extract code snippets
    code_snippets = []
    for i, code in enumerate(code_blocks[:5]):  # Limit to 5 snippets
        code_text = code.get_text(strip=True)
        if code_text and len(code_text) > 10:
            code_snippets.append({
                "index": i,
                "language": guess_programming_language(code_text),
                "preview": code_text[:200] + "..." if len(code_text) > 200 else code_text,
                "length": len(code_text)
            })
    
    # Look for API documentation patterns
    api_endpoints = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if any(pattern in href.lower() for pattern in ["/api/", "/v1/", "/v2/", "/endpoint", "/docs"]):
            api_endpoints.append({
                "text": link.get_text(strip=True)[:100],
                "href": href
            })
    
    return {
        "code_block_count": code_count,
        "code_snippets": code_snippets,
        "api_endpoint_count": len(api_endpoints),
        "api_endpoints": api_endpoints[:10],  # Limit
        "has_technical_content": code_count > 0 or len(api_endpoints) > 0,
        "extracted_at": datetime.datetime.now().isoformat()
    }

def extract_ecommerce_info(html_content: str, url: str) -> Dict[str, Any]:
    """Extract e-commerce product information"""
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for product information
    product_name = ""
    price = ""
    description = ""
    images = []
    
    # Try Open Graph product tags
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        product_name = og_title["content"]
    
    # Look for price
    price_selectors = [
        soup.find("meta", property="product:price:amount"),
        soup.find("span", class_=lambda x: x and any(price_word in str(x).lower() for price_word in ["price", "cost", "amount", "$"])),
        soup.find("div", class_=lambda x: x and any(price_word in str(x).lower() for price_word in ["price", "cost", "amount"]))
    ]
    
    for selector in price_selectors:
        if selector:
            if hasattr(selector, "get"):
                price = selector.get("content", "") or selector.get_text(strip=True)
            else:
                price = selector.get_text(strip=True)
            if price:
                break
    
    # Look for product images
    for img in soup.find_all("img")[:5]:
        src = img.get("src", "")
        alt = img.get("alt", "")
        if src:
            images.append({
                "src": src,
                "alt": alt[:100]
            })
    
    return {
        "product_name": product_name or (soup.title.string if soup.title else ""),
        "price": price,
        "description": soup.find("meta", attrs={"name": "description"}).get("content", "")[:500] if soup.find("meta", attrs={"name": "description"}) else "",
        "image_count": len(images),
        "images": images,
        "is_product_page": bool(product_name and price),
        "extracted_at": datetime.datetime.now().isoformat()
    }

def extract_with_custom_pattern(html_content: str, url: str, pattern: str) -> Dict[str, Any]:
    """Extract using custom pattern (simplified)"""
    # This is a simplified version - in production, you'd parse the pattern
    # and extract accordingly
    return {
        "custom_pattern": pattern,
        "note": "Custom pattern extraction not fully implemented",
        "html_length": len(html_content),
        "extracted_at": datetime.datetime.now().isoformat()
    }

def detect_language(soup) -> str:
    """Detect language from HTML"""
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        lang = html_tag.get("lang")[:2].lower()
        if lang in ["en", "zh", "es", "fr", "de", "ja", "ko", "ru"]:
            return lang
    return "en"

def guess_programming_language(code_text: str) -> str:
    """Guess programming language from code snippet"""
    code_lower = code_text.lower()
    
    if "def " in code_lower or "import " in code_lower or "class " in code_lower:
        return "python"
    elif "function " in code_lower or "var " in code_lower or "const " in code_lower or "let " in code_lower:
        return "javascript"
    elif "#include" in code_lower or "int main" in code_lower:
        return "c/c++"
    elif "<?" in code_lower or "echo " in code_lower:
        return "php"
    elif "public class" in code_lower or "System.out." in code_lower:
        return "java"
    elif "package " in code_lower or "func " in code_lower:
        return "go"
    elif "fn " in code_lower or "let " in code_lower or "match " in code_lower:
        return "rust"
    else:
        return "unknown"