from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用信息
    APP_NAME: str = "FileBot"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天
    
    # 数据库配置 - 使用SQLite（轻量级）
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./filebot.db"
    )
    
    # Redis配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # 文件存储配置
    FILE_STORAGE_PATH: str = os.getenv("FILE_STORAGE_PATH", "./data/files")
    TEMP_STORAGE_PATH: str = os.getenv("TEMP_STORAGE_PATH", "./data/temp")
    DATA_ROOT: str = os.getenv("DATA_ROOT", "./data")  # 数据根目录
    STATIC_FILES_PATH: str = os.getenv("STATIC_FILES_PATH", "./static/files")  # 静态文件目录（已发布文件）
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS: List[str] = [
        ".tiff", ".tif", ".pdf", ".doc", ".docx", 
        ".jpg", ".jpeg", ".png", ".pcl", ".ps", ".txt"
    ]
    
    # CORS配置
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8001",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8001",
        "http://127.0.0.1:5173",
    ]
    
    # 转换配置
    CONVERSION_TIMEOUT: int = 300  # 5分钟
    CONCURRENT_CONVERSIONS: int = 5
    
    # 默认用户配置
    DEFAULT_SUPERUSER_EMAIL: str = "admin@filebot.com"
    DEFAULT_SUPERUSER_USERNAME: str = "admin"
    DEFAULT_SUPERUSER_PASSWORD: str = "admin123"
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/filebot.log"
    
    # 开发模式
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()