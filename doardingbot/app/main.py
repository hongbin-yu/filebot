from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager

from app.config import settings
from app.models.base import init_db, get_db
from app.routes.import_routes import router as import_router
from app.routes.extract_routes import router as extract_router
from app.routes.download_routes import router as download_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("doardingbot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("Starting DoardingBot...")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
    
    # Check WebBot connectivity
    try:
        import requests
        response = requests.get(f"{settings.webbot_api_url}/health", timeout=5)
        if response.status_code == 200:
            logger.info(f"WebBot connection successful: {settings.webbot_api_url}")
        else:
            logger.warning(f"WebBot health check returned {response.status_code}")
    except Exception as e:
        logger.warning(f"WebBot connection check failed: {str(e)}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down DoardingBot...")

# Create FastAPI app
app = FastAPI(
    title="DoardingBot API",
    description="Web page importer and converter for WebBot and FileBot",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(import_router)
app.include_router(extract_router)
app.include_router(download_router)

# Basic endpoints
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "DoardingBot",
        "version": "1.0.0",
        "description": "Web page importer for WebBot and FileBot",
        "endpoints": {
            "import": "/api/v1/import/jobs",
            "extract": "/api/extract/",
            "download": "/api/download/pages (step1) and /api/download/process (step2)",
            "health": "/health",
            "docs": "/docs"
        },
        "integrations": {
            "webbot": settings.webbot_api_url,
            "filebot": settings.filebot_api_url
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    from app.services.integration_service import IntegrationService
    
    # Create integration service (no DB dependency for basic health)
    integration = IntegrationService()
    
    # Check external services
    webbot_healthy = integration.check_webbot_health()
    filebot_healthy = integration.check_filebot_health()
    
    status = "healthy" if webbot_healthy else "degraded"
    
    return {
        "status": status,
        "service": "DoardingBot",
        "integrations": {
            "webbot": {
                "available": webbot_healthy,
                "url": settings.webbot_api_url
            },
            "filebot": {
                "available": filebot_healthy,
                "url": settings.filebot_api_url
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8002,  # Different port from WebBot (8000) and FileBot (8001)
        reload=True
    )