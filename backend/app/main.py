"""
Main application module for the search-comparisons backend.

This module configures and starts the FastAPI application, including middleware,
exception handlers, and route registration.
"""
import logging
import os
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv
import math
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .api.routes.search_routes import router as search_router
from .api.routes.debug_routes import router as debug_router
from .api.routes.experiment_routes import router as experiment_router, back_compat_router
from .api.routes.query_intent import router as query_intent_router
from .api.routes.health import router as health_router
from .routes.quepid import router as quepid_router
from .routes.judgement import router as judgement_router
from .api.models import ErrorResponse
from .core.init_db import init_db
from .core.config import settings

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Set up platform-specific fixes and environment variables first
# Apply macOS SSL certificate handling fix if needed
if os.name == 'posix' and 'darwin' in os.uname().sysname.lower():
    import ssl
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()

# Load environment variables from backend/.env
backend_dir = Path(__file__).parent.parent
env_path = backend_dir / '.env'
load_dotenv(dotenv_path=env_path)

# Log environment variables for debugging
logger = logging.getLogger(__name__)
logger.info(f"Loading environment variables from: {env_path}")
logger.info(f"ADS_SOLR_PASSWORD set: {'Yes' if os.getenv('ADS_SOLR_PASSWORD') else 'No'}")

# Ensure critical environment variables are set
ADS_API_KEY = os.getenv("ADS_API_KEY", "")
if not ADS_API_KEY:
    # Check if ADS_API_TOKEN is available instead
    ads_api_token = os.getenv("ADS_API_TOKEN", "")
    if ads_api_token:
        print("Found ADS_API_TOKEN instead. Setting as ADS_API_KEY.")
        os.environ["ADS_API_KEY"] = ads_api_token
    else:
        # Set emergency fallback for testing
        print("Setting emergency fallback ADS_API_KEY for testing only")
        os.environ["ADS_API_KEY"] = "F6pHGICMXXy4aiAWBR4gaFL4Ta72xdM8jVhHDOsm"

# Check for Web of Science API key
WEB_OF_SCIENCE_API_KEY = os.getenv("WEB_OF_SCIENCE_API_KEY", "")
if not WEB_OF_SCIENCE_API_KEY:
    # Check for alternative key names
    alt_keys = ["WOS_API_KEY", "WEBOFSCIENCE_API_KEY", "WOS_KEY"]
    for key_name in alt_keys:
        alt_key = os.getenv(key_name, "")
        if alt_key:
            print(f"Found {key_name} instead. Setting as WEB_OF_SCIENCE_API_KEY.")
            os.environ["WEB_OF_SCIENCE_API_KEY"] = alt_key
            break
    
    # If still no key, set a placeholder for development
    if not os.environ.get("WEB_OF_SCIENCE_API_KEY"):
        print("Setting placeholder WEB_OF_SCIENCE_API_KEY for development")
        # This is not a real key, but prevents the "missing key" error for testing
        os.environ["WEB_OF_SCIENCE_API_KEY"] = "dev_placeholder_key_not_for_production"

# Set up logging
# Create logs directory if it doesn't exist
logs_dir = Path(__file__).parent.parent / 'logs'
logs_dir.mkdir(exist_ok=True)

# Configure logging to write to both file and console
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(logs_dir / 'app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Log API key status (masked)
ads_api_key = os.environ.get("ADS_API_KEY", "")
if ads_api_key:
    masked_key = f"{ads_api_key[:4]}...{ads_api_key[-4:]}" if len(ads_api_key) > 8 else "[KEY]"
    logger.info(f"ADS_API_KEY found! Length: {len(ads_api_key)}, Value (masked): {masked_key}")

# Service configuration
SERVICE_CONFIG = {
    "ads": {
        "enabled": True,
        "priority": 1,  # Lower number = higher priority
        "timeout": 15,  # seconds
        "min_results": 5,  # Minimum acceptable results
    },
    "scholar": {
        "enabled": True,
        "priority": 2,
        "timeout": 20,
        "min_results": 3,
    },
    "semanticScholar": {
        "enabled": True,
        "priority": 3,
        "timeout": 15,
        "min_results": 5,
    },
    "webOfScience": {
        "enabled": True,
        "priority": 4,
        "timeout": 20,
        "min_results": 3,
    }
}

# Create FastAPI app
app = FastAPI(
    title="Search Comparisons API",
    description="API for comparing search results across different sources",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    debug=False  # Disable debug mode in production
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "https://search.sjarmak.ai",
        "https://search-tool-api.onrender.com",
        "https://search-tool.onrender.com",
        os.environ.get("FRONTEND_URL", "https://search-tool.onrender.com")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security headers middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure this based on your domains
)

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="search_comparisons_session"
)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for all unhandled exceptions.
    
    Args:
        request: The request that caused the exception
        exc: The exception that was raised
    
    Returns:
        JSONResponse: A JSON response with error details
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred",
            details=str(exc) if os.getenv("DEBUG", "True").lower() in ("true", "1", "t", "yes") else None,
        ).model_dump(),
    )


@app.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns:
        Dict[str, Any]: Health status information
    """
    return {
        "status": "ok",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "local"),
    }


@app.get("/", include_in_schema=False)
async def root() -> Dict[str, Any]:
    """
    Root endpoint that provides basic API information.
    
    Returns:
        Dict[str, Any]: API information
    """
    return {
        "message": "Welcome to Search Comparisons API",
        "docs_url": "/api/docs",
        "health_check": "/api/health"
    }

@app.head("/", include_in_schema=False)
async def root_head() -> None:
    """
    HEAD request handler for the root endpoint.
    Used by health checks.
    """
    return None


# Register routes
app.include_router(search_router)
app.include_router(debug_router)
app.include_router(experiment_router)
app.include_router(back_compat_router)  # Include the backward compatibility router
app.include_router(query_intent_router)  # Include the query intent router
app.include_router(health_router)  # Include the health check router
app.include_router(quepid_router, prefix="/api/quepid")  # Include the Quepid router
app.include_router(judgement_router, prefix="/api")  # Include the judgment router


@app.on_event("startup")
async def startup_event() -> None:
    """
    Execute startup tasks for the application.
    
    Performs initialization tasks when the application starts.
    """
    logger.info(f"Starting Academic Search Results Comparator API v1.0.0")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'local')}")
    logger.info(f"Debug mode: {os.getenv('DEBUG', 'True')}")
    logger.info(f"Registered legacy endpoints for backward compatibility")
    logger.info(f"Query intent service: enabled, LLM: {os.getenv('USE_LLM', 'false')}")
    
    # Initialize database
    init_db()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Execute shutdown tasks for the application.
    
    Performs cleanup tasks when the application shuts down.
    """
    logger.info("Shutting down Academic Search Results Comparator API")

# Note: Both /api/boost-experiment and /api/experiments/boost endpoints are now available
# for backward compatibility. The old endpoint name will still work,
# but the new endpoint path is recommended for new development.