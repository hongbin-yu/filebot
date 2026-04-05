import requests
import logging
import tempfile
import os
import hashlib
from urllib.parse import urljoin, urlparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup
from PIL import Image as PILImage
import io
import magic
import time

logger = logging.getLogger(__name__)

class ImageExtractionService:
    """Service for extracting and processing images from web pages"""
    
    def __init__(self, timeout: int = 30, max_image_size: int = 10 * 1024 * 1024):  # 10MB
        self.timeout = timeout
        self.max_image_size = max_image_size
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "DoardingBot/1.0 (+https://github.com/your-org/doardingbot)",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        })
    
    def extract_images_from_html(self, html: str, base_url: str) -> List[Dict[str, Any]]:
        """
        Extract image information from HTML
        
        Args:
            html: HTML content
            base_url: Base URL for resolving relative image URLs
            
        Returns:
            List of image information dictionaries
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            images = []
            
            # Find all img tags
            img_tags = soup.find_all('img')
            
            for img in img_tags:
                img_data = self._extract_image_data(img, base_url)
                if img_data:
                    images.append(img_data)
            
            # Also look for picture/source tags
            picture_tags = soup.find_all('picture')
            for picture in picture_tags:
                sources = picture.find_all('source')
                for source in sources:
                    if source.get('srcset'):
                        # Parse srcset (can contain multiple images with descriptors)
                        srcset = source.get('srcset')
                        # Simple parsing - take the first URL
                        urls = [url.strip().split()[0] for url in srcset.split(',') if url.strip()]
                        if urls:
                            img_data = self._extract_image_data_from_url(urls[0], base_url, source)
                            if img_data:
                                images.append(img_data)
            
            logger.info(f"Extracted {len(images)} images from HTML")
            return images
            
        except Exception as e:
            logger.error(f"Error extracting images from HTML: {str(e)}")
            return []
    
    def _extract_image_data(self, img_tag, base_url: str) -> Optional[Dict[str, Any]]:
        """Extract data from an img tag"""
        try:
            src = img_tag.get('src')
            if not src:
                return None
            
            # Resolve relative URL
            image_url = urljoin(base_url, src)
            
            # Get other attributes
            alt = img_tag.get('alt', '')
            title = img_tag.get('title', '')
            
            # Try to get dimensions
            width = img_tag.get('width')
            height = img_tag.get('height')
            
            # Parse dimensions if they're strings
            if width:
                try:
                    width = int(width)
                except:
                    width = None
            
            if height:
                try:
                    height = int(height)
                except:
                    height = None
            
            return {
                'url': image_url,
                'alt': alt,
                'title': title,
                'width': width,
                'height': height,
                'tag_name': 'img',
                'attributes': dict(img_tag.attrs)
            }
            
        except Exception as e:
            logger.error(f"Error extracting image data: {str(e)}")
            return None
    
    def _extract_image_data_from_url(self, url: str, base_url: str, source_tag=None) -> Optional[Dict[str, Any]]:
        """Extract image data from a URL"""
        try:
            image_url = urljoin(base_url, url)
            
            attributes = {}
            if source_tag:
                attributes = dict(source_tag.attrs)
            
            return {
                'url': image_url,
                'alt': '',
                'title': '',
                'width': None,
                'height': None,
                'tag_name': 'source',
                'attributes': attributes
            }
            
        except Exception as e:
            logger.error(f"Error extracting image data from URL: {str(e)}")
            return None
    
    def download_image(self, image_url: str, temp_dir: Path) -> Optional[Dict[str, Any]]:
        """
        Download an image to a temporary file
        
        Args:
            image_url: URL of the image to download
            temp_dir: Directory to save temporary file
            
        Returns:
            Dict with image metadata and local file path, or None if failed
        """
        try:
            logger.info(f"Downloading image: {image_url}")
            
            # Download image
            response = self.session.get(image_url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"URL {image_url} is not an image (Content-Type: {content_type})")
                return None
            
            # Check file size
            content_length = response.headers.get('Content-Length')
            if content_length:
                file_size = int(content_length)
                if file_size > self.max_image_size:
                    logger.warning(f"Image too large: {file_size} bytes (max: {self.max_image_size})")
                    return None
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                dir=temp_dir,
                suffix='.tmp',
                delete=False
            )
            temp_path = Path(temp_file.name)
            
            # Download content
            file_size = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file_size += len(chunk)
                    if file_size > self.max_image_size:
                        logger.warning(f"Image exceeded size limit during download")
                        temp_file.close()
                        os.unlink(temp_path)
                        return None
                    temp_file.write(chunk)
            
            temp_file.close()
            
            # Get file hash
            file_hash = self._calculate_file_hash(temp_path)
            
            # Detect MIME type
            mime_type = self._detect_mime_type(temp_path)
            
            # Get image dimensions
            width, height = self._get_image_dimensions(temp_path)
            
            # Determine file extension
            extension = self._get_file_extension(mime_type, image_url)
            
            # Rename file with proper extension
            final_path = temp_path.with_suffix(extension)
            os.rename(temp_path, final_path)
            
            return {
                'success': True,
                'local_path': str(final_path),
                'file_size': file_size,
                'file_hash': file_hash,
                'mime_type': mime_type,
                'width': width,
                'height': height,
                'extension': extension,
                'original_url': image_url
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download image {image_url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading image {image_url}: {str(e)}")
            return None
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _detect_mime_type(self, file_path: Path) -> str:
        """Detect MIME type of a file"""
        try:
            mime = magic.Magic(mime=True)
            return mime.from_file(str(file_path))
        except:
            # Fallback to file extension
            return 'application/octet-stream'
    
    def _get_image_dimensions(self, file_path: Path) -> Tuple[Optional[int], Optional[int]]:
        """Get image dimensions using PIL"""
        try:
            with PILImage.open(file_path) as img:
                return img.size  # (width, height)
        except:
            return None, None
    
    def _get_file_extension(self, mime_type: str, image_url: str) -> str:
        """Determine file extension from MIME type or URL"""
        # Map common MIME types to extensions
        mime_to_ext = {
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'image/svg+xml': '.svg',
            'image/bmp': '.bmp',
            'image/tiff': '.tiff',
        }
        
        # Try MIME type first
        if mime_type in mime_to_ext:
            return mime_to_ext[mime_type]
        
        # Fallback: extract from URL
        parsed_url = urlparse(image_url)
        path = parsed_url.path
        if '.' in path:
            ext = Path(path).suffix.lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.tiff', '.tif']:
                return ext
        
        # Default
        return '.jpg'
    
    def batch_download_images(self, image_urls: List[str], temp_dir: Path) -> Dict[str, Any]:
        """
        Download multiple images
        
        Args:
            image_urls: List of image URLs
            temp_dir: Directory for temporary files
            
        Returns:
            Dict with download results
        """
        results = {
            'successful': [],
            'failed': [],
            'total': len(image_urls)
        }
        
        for url in image_urls:
            result = self.download_image(url, temp_dir)
            if result:
                results['successful'].append(result)
            else:
                results['failed'].append(url)
            
            # Be polite - small delay between requests
            time.sleep(0.2)
        
        logger.info(f"Batch download: {len(results['successful'])} successful, {len(results['failed'])} failed")
        return results