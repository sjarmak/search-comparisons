"""
Health check routes for the application.

This module provides endpoints for monitoring the application's health and status.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..dependencies import get_db
from ...core.config import settings

router = APIRouter()

@router.get("/health")
async def health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Health check endpoint that verifies the application's status.
    
    Args:
        db: Database session dependency
        
    Returns:
        Dict[str, Any]: Health status information including database connectivity
    """
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "ok",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "llm_enabled": settings.LLM_ENABLED,
        "local_llm_enabled": settings.LOCAL_LLM_ENABLED
    } 