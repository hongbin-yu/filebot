import requests
from readability import Document
from bs4 import BeautifulSoup
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import time

logger = logging.getLogger(__name__)

class ScraperService:
    """Service for scraping web page content"""
    
    def __init__(self, timeout: int = 30, user_agent: str = None):
        self.timeout = timeout
        self.user_agent = user_agent or "DoardingBot/1.0 (+https://github.com/your-org/doardingbot)"
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification for simplicity
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
        })
    
    def scrape_url(self, url: str) -> Dict[str, Any]:
        """
        Scrape a single URL and extract content
        
        Returns:
            Dict containing title, content, language, and metadata
        """
        try:
            logger.info(f"Scraping URL: {url}")
            
            # Fetch the page
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = self._extract_title(soup, url)
            
            # Extract main content using readability
            doc = Document(response.text)
            content_html = doc.summary()
            
            # Clean HTML
            content_cleaned = self._clean_html(content_html)
            
            # Extract metadata
            metadata = self._extract_metadata(soup, url, response)
            
            # Detect language (simple detection)
            language = self._detect_language(soup, response)
            
            return {
                "success": True,
                "title": title,
                "content": content_cleaned,
                "content_type": "html",
                "language": language,
                "metadata": metadata,
                "response_status": response.status_code,
                "content_length": len(response.content),
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {url}: {str(e)}")
            return {
                "success": False,
                "error": f"Request error: {str(e)}",
                "title": None,
                "content": None,
                "metadata": {"error_type": "request_error"}
            }
        except Exception as e:
            logger.error(f"Unexpected error scraping {url}: {str(e)}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "title": None,
                "content": None,
                "metadata": {"error_type": "unexpected_error"}
            }
    
    def _extract_title(self, soup: BeautifulSoup, url: str) -> str:
        """Extract page title"""
        # Try various title selectors
        title_selectors = [
            soup.find("title"),
            soup.find("meta", property="og:title"),
            soup.find("meta", property="twitter:title"),
            soup.find("h1"),
        ]
        
        for selector in title_selectors:
            if selector:
                title = selector.get_text().strip() if hasattr(selector, 'get_text') else selector.get("content", "")
                if title:
                    return title[:500]  # Limit length
        
        # Fallback to URL
        parsed_url = urlparse(url)
        return parsed_url.netloc or url[:100]
    
    def _clean_html(self, html: str) -> str:
        """Clean and normalize HTML"""
        if not html:
            return ""
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style tags
        for script in soup(["script", "style", "noscript", "iframe"]):
            script.decompose()
        
        # Remove empty tags
        for tag in soup.find_all():
            if len(tag.get_text(strip=True)) == 0 and not tag.find_all():
                tag.decompose()
        
        # Get cleaned HTML
        cleaned = str(soup)
        
        # Limit size
        if len(cleaned) > 1000000:  # 1MB limit
            cleaned = cleaned[:1000000] + "... [truncated]"
        
        return cleaned
    
    def _extract_metadata(self, soup: BeautifulSoup, url: str, response: requests.Response) -> Dict[str, Any]:
        """Extract metadata from page"""
        metadata = {
            "source_url": url,
            "fetched_at": time.time(),
            "content_type": response.headers.get("Content-Type", ""),
            "encoding": response.encoding,
        }
        
        # Meta tags
        meta_tags = {}
        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property") or meta.get("itemprop")
            content = meta.get("content")
            if name and content:
                meta_tags[name] = content
        
        metadata["meta_tags"] = meta_tags
        
        # Open Graph / Twitter Card data
        og_data = {}
        for meta in soup.find_all("meta", property=lambda x: x and x.startswith("og:")):
            og_data[meta["property"]] = meta.get("content", "")
        metadata["open_graph"] = og_data
        
        # Links
        links = []
        for link in soup.find_all("a", href=True):
            links.append({
                "text": link.get_text(strip=True)[:100],
                "href": link["href"]
            })
        metadata["links"] = links[:50]  # Limit
        
        return metadata
    
    def _detect_language(self, soup: BeautifulSoup, response: requests.Response) -> str:
        """Simple language detection"""
        # Check HTML lang attribute
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            lang = html_tag.get("lang")[:2].lower()
            if lang in ["en", "zh", "es", "fr", "de", "ja", "ko", "ru"]:
                return lang
        
        # Check Content-Language header
        content_lang = response.headers.get("Content-Language", "")
        if content_lang:
            lang = content_lang[:2].lower()
            if lang in ["en", "zh", "es", "fr", "de", "ja", "ko", "ru"]:
                return lang
        
        # Default to English
        return "en"
    
    def batch_scrape(self, urls: list) -> Dict[str, Dict[str, Any]]:
        """Scrape multiple URLs"""
        results = {}
        for url in urls:
            results[url] = self.scrape_url(url)
            # Be polite - small delay between requests
            time.sleep(0.5)
        
        return results