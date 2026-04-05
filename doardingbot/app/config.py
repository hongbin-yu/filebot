from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database configuration
    database_url: str = "sqlite:///./doardingbot.db"
    
    # WebBot integration
    webbot_api_url: str = "http://localhost:8000"
    webbot_api_key: Optional[str] = None
    
    # FileBot integration
    filebot_api_url: str = "http://localhost:8001"
    filebot_api_key: Optional[str] = None
    
    # Scraper configuration
    request_timeout: int = 30
    max_content_length: int = 1000000  # 1MB
    user_agent: str = "DoardingBot/1.0 (+https://github.com/your-org/doardingbot)"
    
    class Config:
        env_file = ".env"

settings = Settings()