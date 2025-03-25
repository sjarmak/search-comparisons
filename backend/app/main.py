"""
Main application module for the search-comparisons backend.

This module configures and starts the FastAPI application, including middleware,
exception handlers, and route registration.
"""
import logging
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import search_routes, debug_routes, experiment_routes
from .api.models import ErrorResponse
from .core.config import settings

# Setup logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
            details=str(exc) if settings.DEBUG else None,
        ).dict(),
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
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Include routers
app.include_router(search_routes.router)
app.include_router(debug_routes.router)
app.include_router(experiment_routes.router)


@app.on_event("startup")
async def startup_event() -> None:
    """
    Execute startup tasks for the application.
    
    Performs initialization tasks when the application starts.
    """
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Execute shutdown tasks for the application.
    
    Performs cleanup tasks when the application shuts down.
    """
    logger.info(f"Shutting down {settings.PROJECT_NAME}")