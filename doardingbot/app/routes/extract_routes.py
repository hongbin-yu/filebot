"""
Simplified extraction API for DoardingBot
Based on user requirements: simple extraction, independent service, one-time use per website
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
import logging
import tempfile
import os
from pathlib import Path
import uuid

from app.services.scraper_service import ScraperService
from app.services.image_service import ImageExtractionService
from app.services.integration_service import IntegrationService

router = APIRouter(prefix="/api/extract", tags=["extract"])
logger = logging.getLogger(__name__)

class ExtractRequest(BaseModel):
    """Simple extraction request"""
    urls: List[HttpUrl]
    extract_images: bool = True
    send_to_webbot: bool = True
    send_images_to_filebot: bool = True

class ExtractResponse(BaseModel):
    """Simple extraction response"""
    job_id: str
    status: str  # processing, completed, failed
    message: str
    pages: List[Dict[str, Any]] = []
    errors: List[str] = []

@router.post("/", response_model=ExtractResponse)
async def extract_urls(request: ExtractRequest):
    """
    Simple URL extraction endpoint
    
    - Extracts page content and images
    - Sends page content to WebBot (if enabled)
    - Sends images to FileBot (if enabled)
    - Returns immediate results (no background jobs)
    """
    job_id = str(uuid.uuid4())
    logger.info(f"Starting extraction job {job_id} for {len(request.urls)} URLs")
    
    response = ExtractResponse(
        job_id=job_id,
        status="processing",
        message=f"Processing {len(request.urls)} URLs",
        pages=[],
        errors=[]
    )
    
    try:
        # Initialize services
        scraper = ScraperService()
        image_service = ImageExtractionService()
        integration = IntegrationService()
        
        # Check service availability
        webbot_available = integration.check_webbot_health() if request.send_to_webbot else False
        filebot_available = integration.check_filebot_health() if request.send_images_to_filebot else False
        
        if request.send_to_webbot and not webbot_available:
            logger.warning("WebBot is not available, page content will not be sent")
            response.errors.append("WebBot is not available")
        
        if request.send_images_to_filebot and not filebot_available:
            logger.warning("FileBot is not available, images will not be sent")
            response.errors.append("FileBot is not available")
        
        # Process each URL
        for url in request.urls:
            url_str = str(url)
            page_result = {
                "url": url_str,
                "title": None,
                "content_extracted": False,
                "webbot_page_id": None,
                "images": []
            }
            
            try:
                # Step 1: Extract page content
                logger.info(f"Extracting content from {url_str}")
                scrape_result = scraper.scrape_url(url_str)
                
                if not scrape_result.get("success", False):
                    error_msg = f"Failed to extract content from {url_str}: {scrape_result.get('error', 'Unknown error')}"
                    logger.error(error_msg)
                    response.errors.append(error_msg)
                    continue
                
                page_result["title"] = scrape_result.get("title", "Untitled")
                page_result["content_extracted"] = True
                
                # Step 2: Send to WebBot (if enabled and available)
                webbot_page_id = None
                if request.send_to_webbot and webbot_available:
                    try:
                        # Convert HTML to markdown if needed
                        html_content = scrape_result.get("content", "")
                        if html_content:
                            # Simple conversion - just use first 5000 chars for now
                            # In a real implementation, use html2text or similar
                            content_for_webbot = html_content[:5000]
                            
                            # TODO: Call WebBot API to create page
                            # For now, just simulate
                            webbot_page_id = f"webbot-{uuid.uuid4()}"
                            page_result["webbot_page_id"] = webbot_page_id
                            logger.info(f"Page would be sent to WebBot with ID: {webbot_page_id}")
                    except Exception as e:
                        error_msg = f"Failed to send page to WebBot: {str(e)}"
                        logger.error(error_msg)
                        response.errors.append(error_msg)
                
                # Step 3: Extract and process images (if enabled)
                if request.extract_images and scrape_result.get("content"):
                    try:
                        # Extract image URLs from HTML
                        html_content = scrape_result.get("content", "")
                        images_info = image_service.extract_images_from_html(html_content, url_str)
                        
                        # Create temp directory for image downloads
                        with tempfile.TemporaryDirectory() as temp_dir:
                            temp_path = Path(temp_dir)
                            
                            # Download images
                            image_urls = [img["url"] for img in images_info[:5]]  # Limit to 5 images
                            download_results = image_service.batch_download_images(image_urls, temp_path)
                            
                            for download_result in download_results["successful"]:
                                image_result = {
                                    "url": download_result["original_url"],
                                    "downloaded": True,
                                    "local_path": download_result["local_path"],
                                    "filebot_document_id": None
                                }
                                
                                # Send to FileBot (if enabled and available)
                                if request.send_images_to_filebot and filebot_available:
                                    try:
                                        # TODO: Call FileBot upload API
                                        # For now, just simulate
                                        filebot_id = f"filebot-{uuid.uuid4()}"
                                        image_result["filebot_document_id"] = filebot_id
                                        logger.info(f"Image would be sent to FileBot with ID: {filebot_id}")
                                    except Exception as e:
                                        error_msg = f"Failed to send image to FileBot: {str(e)}"
                                        logger.error(error_msg)
                                        response.errors.append(error_msg)
                                
                                page_result["images"].append(image_result)
                            
                            for failed_url in download_results["failed"]:
                                logger.warning(f"Failed to download image: {failed_url}")
                                response.errors.append(f"Failed to download image: {failed_url}")
                    
                    except Exception as e:
                        error_msg = f"Failed to process images for {url_str}: {str(e)}"
                        logger.error(error_msg)
                        response.errors.append(error_msg)
                
                response.pages.append(page_result)
                
            except Exception as e:
                error_msg = f"Error processing URL {url_str}: {str(e)}"
                logger.error(error_msg)
                response.errors.append(error_msg)
        
        # Update response status
        if response.errors and len(response.errors) == len(request.urls):
            response.status = "failed"
            response.message = f"All {len(request.urls)} URLs failed"
        elif response.errors:
            response.status = "completed_with_errors"
            response.message = f"Processed {len(request.urls)} URLs with {len(response.errors)} errors"
        else:
            response.status = "completed"
            response.message = f"Successfully processed {len(request.urls)} URLs"
        
        logger.info(f"Extraction job {job_id} completed with status: {response.status}")
        return response
        
    except Exception as e:
        error_msg = f"Unexpected error in extraction job {job_id}: {str(e)}"
        logger.error(error_msg)
        response.status = "failed"
        response.message = error_msg
        response.errors.append(error_msg)
        return response