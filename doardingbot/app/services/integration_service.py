import requests
import logging
from typing import Optional, Dict, Any
from app.config import settings
from app.schemas.import_schema import WebBotPageCreate

logger = logging.getLogger(__name__)

class IntegrationService:
    """Service for integrating with WebBot and FileBot"""
    
    def __init__(self):
        self.webbot_base_url = settings.webbot_api_url.rstrip("/")
        self.filebot_base_url = settings.filebot_api_url.rstrip("/")
        
    def send_to_webbot(self, page_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send page to WebBot via API
        
        Args:
            page_data: Page data including title, content, language, metadata
            
        Returns:
            Dict with success status and WebBot page ID/URL
        """
        try:
            # Prepare request data
            request_data = WebBotPageCreate(**page_data)
            
            # Make API request
            url = f"{self.webbot_base_url}/api/v1/pages"
            logger.info(f"Sending to WebBot: {url}")
            
            response = requests.post(
                url,
                json=request_data.model_dump(),
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"WebBot response: {result}")
            
            return {
                "success": True,
                "webbot_page_id": result.get("id"),
                "webbot_page_url": f"{self.webbot_base_url}/pages/{result.get('id')}",
                "response_data": result
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"WebBot API request failed: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "webbot_page_id": None,
                "webbot_page_url": None
            }
        except Exception as e:
            error_msg = f"Unexpected error sending to WebBot: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "webbot_page_id": None,
                "webbot_page_url": None
            }
    
    def send_to_filebot(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send file to FileBot via API
        
        Args:
            file_data: File data including content and metadata
            
        Returns:
            Dict with success status and FileBot file ID/path
        """
        try:
            # Note: FileBot API integration needs to be defined
            # For now, we'll create a placeholder implementation
            
            # Check if FileBot is reachable
            health_url = f"{self.filebot_base_url}/health"
            try:
                health_response = requests.get(health_url, timeout=5)
                if health_response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"FileBot not available (health check failed: {health_response.status_code})",
                        "filebot_file_id": None,
                        "filebot_file_path": None
                    }
            except requests.exceptions.RequestException:
                return {
                    "success": False,
                    "error": "FileBot not reachable",
                    "filebot_file_id": None,
                    "filebot_file_path": None
                }
            
            # TODO: Implement actual FileBot API integration
            # This depends on FileBot's API design
            
            # Placeholder response
            logger.warning("FileBot integration not yet implemented")
            
            return {
                "success": False,
                "error": "FileBot integration not yet implemented",
                "filebot_file_id": None,
                "filebot_file_path": None
            }
            
        except Exception as e:
            error_msg = f"Error sending to FileBot: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "filebot_file_id": None,
                "filebot_file_path": None
            }
    
    def check_webbot_health(self) -> bool:
        """Check if WebBot API is healthy"""
        try:
            url = f"{self.webbot_base_url}/health"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def check_filebot_health(self) -> bool:
        """Check if FileBot API is healthy"""
        try:
            url = f"{self.filebot_base_url}/health"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False