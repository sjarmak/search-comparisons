"""
Query Intent API routes.

This module provides API endpoints for query intent interpretation and transformation.
"""
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Body
from pydantic import BaseModel

from app.services.query_intent.service import QueryIntentService
from app.services.query_intent.llm_service import LLMService
from app.services.query_intent.cache_service import CacheService
from app.services.query_intent.documentation_service import DocumentationService
from app.core.config import settings

# Configure logger for this module
logger = logging.getLogger(__name__)

# Create router with proper prefix and tags
router = APIRouter(
    prefix="/api",
    tags=["query-intent"],
    responses={404: {"description": "Not found"}}
)

# Initialize services
docs_service = DocumentationService()
llm_service = LLMService.from_config()
cache_service = CacheService(max_size=1000, ttl=3600)
query_intent_service = QueryIntentService()

class QueryRequest(BaseModel):
    """Request model for query interpretation."""
    query: str
    use_cache: bool = True

class QueryResponse(BaseModel):
    """Response model for query interpretation."""
    original_query: str
    intent: str
    explanation: str
    transformed_query: str
    results: Dict[str, Any] = {"numFound": 0, "docs": []}
    error: Optional[str] = None

@router.post("/intent-transform-query", response_model=QueryResponse)
async def transform_query(request: QueryRequest) -> QueryResponse:
    """
    Transform a search query based on inferred intent.
    
    Args:
        request: Query request containing the search query
        
    Returns:
        QueryResponse: Response containing the transformed query and results
    """
    try:
        # Get transformed query and results
        result = await query_intent_service.search(
            query=request.query,
            use_cache=request.use_cache
        )
        
        return QueryResponse(
            original_query=request.query,
            intent=result.get("intent", "unknown"),
            explanation=result.get("explanation", ""),
            transformed_query=result.get("transformed_query", request.query),
            results=result.get("results", {"numFound": 0, "docs": []})
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error transforming query: {str(e)}"
        )

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Check the health of the query intent service.
    
    Returns:
        Dict[str, Any]: Health status information
    """
    try:
        return await query_intent_service.health_check()
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 