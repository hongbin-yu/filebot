import html2text
import logging
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

class ConversionService:
    """Service for converting HTML to other formats"""
    
    def __init__(self):
        # Configure html2text converter
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = False
        self.html_converter.ignore_tables = False
        self.html_converter.ignore_emphasis = False
        self.html_converter.body_width = 0  # No wrapping
        self.html_converter.single_line_break = False
        self.html_converter.mark_code = True
    
    def html_to_markdown(self, html: str, title: str = None) -> str:
        """
        Convert HTML to Markdown
        
        Args:
            html: HTML content
            title: Optional title to prepend
            
        Returns:
            Markdown content
        """
        try:
            if not html or html.strip() == "":
                return ""
            
            # Convert HTML to Markdown
            markdown = self.html_converter.handle(html)
            
            # Clean up common issues
            markdown = self._clean_markdown(markdown)
            
            # Add title if provided
            if title and title.strip():
                title_md = f"# {title.strip()}\n\n"
                markdown = title_md + markdown
            
            return markdown
            
        except Exception as e:
            logger.error(f"Error converting HTML to Markdown: {str(e)}")
            # Fallback: extract text from HTML
            return self._html_to_text_fallback(html, title)
    
    def _clean_markdown(self, markdown: str) -> str:
        """Clean up markdown formatting issues"""
        # Remove excessive blank lines
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        
        # Fix code block formatting
        markdown = re.sub(r'```\s*\n```', '', markdown)
        
        # Remove HTML comments
        markdown = re.sub(r'<!--.*?-->', '', markdown, flags=re.DOTALL)
        
        # Fix image links
        markdown = re.sub(r'!\[\]\((.*?)\)', r'![Image](\1)', markdown)
        
        # Trim whitespace
        markdown = markdown.strip()
        
        return markdown
    
    def _html_to_text_fallback(self, html: str, title: str = None) -> str:
        """Fallback method to extract text from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for element in soup(["script", "style", "noscript", "iframe"]):
                element.decompose()
            
            # Get text
            text = soup.get_text(separator='\n', strip=True)
            
            # Clean up
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = '\n'.join(lines)
            
            if title and title.strip():
                text = f"# {title.strip()}\n\n{text}"
            
            return text
            
        except Exception as e:
            logger.error(f"Fallback conversion failed: {str(e)}")
            return title or "Imported content"
    
    def prepare_for_webbot(self, html: str, title: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Prepare content for WebBot API
        
        Returns:
            Dict with title, content, language, and metadata
        """
        # Convert to Markdown
        markdown_content = self.html_to_markdown(html, title)
        
        # Extract language from metadata
        language = "en"
        if metadata and "language" in metadata:
            language = metadata["language"]
        
        # Prepare WebBot page data
        webbot_page = {
            "title": title[:200] if title else "Imported Page",
            "content": markdown_content,
            "language": language,
            "status": "draft",
            "metadata": metadata or {}
        }
        
        return webbot_page
    
    def prepare_for_filebot(self, html: str, title: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Prepare content for FileBot storage
        
        Returns:
            Dict with file content and metadata
        """
        # For FileBot, we might want to store as HTML or Markdown
        # Let's store as both for flexibility
        markdown_content = self.html_to_markdown(html, title)
        
        file_data = {
            "original_html": html,
            "markdown_content": markdown_content,
            "title": title,
            "metadata": metadata or {},
            "file_name": self._generate_filename(title, "html"),
            "content_type": "text/html"
        }
        
        return file_data
    
    def _generate_filename(self, title: str, extension: str) -> str:
        """Generate a filename from title"""
        if not title:
            import time
            return f"imported_{int(time.time())}.{extension}"
        
        # Clean title for filename
        filename = re.sub(r'[^\w\s-]', '', title.lower())
        filename = re.sub(r'[-\s]+', '_', filename)
        filename = filename[:50]  # Limit length
        
        return f"{filename}.{extension}"