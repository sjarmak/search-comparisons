"""
Main FastAPI application for the query intent service.

This module defines the main FastAPI application for the query intent service,
which provides endpoints for query transformation and intent analysis.
"""
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import query_intent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="ADS Query Intent Service",
    description="API for query interpretation and intent-based transformation",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(query_intent.router)


@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint for the API.
    
    Returns:
        dict: Basic service information
    """
    return {
        "message": "ADS Query Intent Service API",
        "version": "1.0.0",
        "documentation": "/docs",
    }


@app.get("/health", tags=["system"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: Health status information
    """
    return {
        "status": "ok",
        "service": "ads-query-intent",
        "environment": os.getenv("ENVIRONMENT", "development"),
    }