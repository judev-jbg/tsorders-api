"""
TS Orders API - Main Application
FastAPI backend for Toolstock Orders Management
"""
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os
import logging
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.getenv("LOG_FILE", "tsorders.log")),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=os.getenv("APP_NAME", "TS Orders API"),
    version=os.getenv("APP_VERSION", "1.0.0"),
    description="Backend API for Toolstock Orders and Shipment Management",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
origins = os.getenv("CORS_ORIGINS", "").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# API Key verification dependency
async def verify_api_key(api_key: str = Header(None, alias="api-key")):
    """
    Verify API key from request header.

    Args:
        api_key: API key from 'api-key' header

    Raises:
        HTTPException: If API key is missing or invalid
    """
    expected_key = os.getenv("API_KEY")

    if not api_key:
        logger.warning("Request without API key")
        raise HTTPException(status_code=401, detail="NO AUTORIZADO")

    if api_key != expected_key:
        logger.warning(f"Invalid API key attempt: {api_key[:10]}...")
        raise HTTPException(status_code=401, detail="NO AUTORIZADO")

    return api_key


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions globally"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Error interno del servidor",
            "detail": str(exc) if os.getenv("DEBUG") == "True" else None
        }
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Execute on application startup"""
    logger.info("=" * 60)
    logger.info(f"Starting {os.getenv('APP_NAME', 'TS Orders API')}")
    logger.info(f"Version: {os.getenv('APP_VERSION', '1.0.0')}")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # Test database connection
    from app.database import test_connection
    if test_connection():
        logger.info("✓ Database connection verified")
    else:
        logger.error("✗ Database connection failed - check configuration")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Execute on application shutdown"""
    logger.info("=" * 60)
    logger.info(f"Shutting down {os.getenv('APP_NAME', 'TS Orders API')}")
    logger.info("=" * 60)


# Root endpoint
@app.get("/", tags=["Health"])
async def root():
    """
    API health check and information endpoint
    """
    return {
        "name": os.getenv("APP_NAME", "TS Orders API"),
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "status": "running",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "timestamp": datetime.now().isoformat(),
        "docs": "/docs",
        "redoc": "/redoc"
    }


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring
    """
    from app.database import test_connection

    db_status = "healthy" if test_connection() else "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }


# Import and include routers
from app import routes, auth_routes

# Authentication routes (public)
app.include_router(auth_routes.router)

# Protected routes (require JWT)
app.include_router(routes.router)

logger.info("✓ All routes registered")
