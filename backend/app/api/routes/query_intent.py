"""
Query Intent API routes.

This module defines the FastAPI routes for the query intent service,
which provides endpoints for query transformation and intent analysis.
"""
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Request, Query

from ...services.llm.agent import QueryAgent

# Configure logger for this module
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(
    prefix="/api/query-intent",
    tags=["query-intent"],
    responses={404: {"description": "Not found"}}
)

# Singleton instance of the query agent
_query_agent: Optional[QueryAgent] = None


def get_query_agent() -> QueryAgent:
    """
    Get or create the singleton query agent instance.
    
    Returns:
        QueryAgent: Query transformation agent
    """
    global _query_agent
    if _query_agent is None:
        _query_agent = QueryAgent()
    return _query_agent


@router.get("/transform")
async def transform_query(
    query: str = Query(..., description="The original search query to transform"),
    agent: QueryAgent = Depends(get_query_agent)
) -> Dict[str, Any]:
    """
    Transform a search query based on the inferred intent.
    
    Args:
        query: Original search query
        agent: Query transformation agent dependency
        
    Returns:
        Dict[str, Any]: Transformation result
    """
    logger.info(f"Received query transformation request: {query}")
    
    try:
        result = agent.transform_query(query)
        return result
    except Exception as e:
        logger.error(f"Error transforming query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error transforming query: {str(e)}"
        )


@router.get("/analyze")
async def analyze_query(
    query: str = Query(..., description="The search query to analyze"),
    agent: QueryAgent = Depends(get_query_agent)
) -> Dict[str, Any]:
    """
    Analyze the complexity and structure of a search query.
    
    Args:
        query: Search query to analyze
        agent: Query transformation agent dependency
        
    Returns:
        Dict[str, Any]: Analysis results
    """
    logger.info(f"Received query analysis request: {query}")
    
    try:
        result = agent.analyze_query_complexity(query)
        return result
    except Exception as e:
        logger.error(f"Error analyzing query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing query: {str(e)}"
        )


@router.get("/suggest")
async def suggest_improvements(
    query: str = Query(..., description="The search query to suggest improvements for"),
    agent: QueryAgent = Depends(get_query_agent)
) -> Dict[str, Any]:
    """
    Suggest improvements for a search query.
    
    Args:
        query: Search query to improve
        agent: Query transformation agent dependency
        
    Returns:
        Dict[str, Any]: Suggestions for query improvement
    """
    logger.info(f"Received query improvement request: {query}")
    
    try:
        suggestions = agent.suggest_improvements(query)
        return {
            "query": query,
            "suggestions": suggestions,
            "suggestion_count": len(suggestions)
        }
    except Exception as e:
        logger.error(f"Error suggesting improvements: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error suggesting improvements: {str(e)}"
        )


@router.get("/health")
async def health_check(
    agent: QueryAgent = Depends(get_query_agent)
) -> Dict[str, Any]:
    """
    Check the health status of the query intent service.
    
    Args:
        agent: Query transformation agent dependency
        
    Returns:
        Dict[str, Any]: Health status information
    """
    try:
        # Check LLM service health
        llm_health = agent.llm_service.health_check()
        
        return {
            "status": "ok" if llm_health["status"] == "ok" else "degraded",
            "llm_service": llm_health,
            "agent_initialized": agent is not None,
            "message": "Query intent service is operational"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Service health check failed: {str(e)}",
            "error": str(e)
        } 