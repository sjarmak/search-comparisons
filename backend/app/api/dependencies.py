"""
Dependencies for FastAPI application.

This module provides dependency functions for the FastAPI application,
including database session management and other shared resources.
"""
from app.core.database import get_db

# Re-export get_db for convenience
__all__ = ['get_db'] 