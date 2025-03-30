"""
Search-related API routes for the search-comparisons application.

This module contains route definitions for search-related endpoints,
including the main comparison endpoint that handles searching across
multiple engines and computing similarity metrics.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

from ...api.models import SearchRequest, SearchResult, SearchResponse
from ...services.search_service import get_results_with_fallback, compare_results, SearchService
from ...services.query_transformation import transform_query_with_boosts

# Create router
router = APIRouter(
    prefix="/api",
    tags=["search"],
    responses={404: {"description": "Not found"}},
)

# Set up logging
logger = logging.getLogger(__name__)

search_service = SearchService()

class TransformQueryRequest(BaseModel):
    """Request model for query transformation."""
    query: str
    field_boosts: Dict[str, float]

class TransformQueryResponse(BaseModel):
    """Response model for query transformation."""
    transformed_query: str

@router.post("/search/compare")
async def compare_search_engines(
    search_request: SearchRequest
) -> Dict[str, Any]:
    """
    Compare search results from multiple academic search engines.
    
    Takes a search query and list of sources, retrieves results from each source,
    and calculates similarity metrics between the result sets.
    
    Args:
        search_request: Request object containing query, sources, metrics, and fields
    
    Returns:
        Dict[str, Any]: Dictionary containing results from each source and comparison metrics
    
    Raises:
        HTTPException: If the request is invalid or if there's an error retrieving results
    """
    try:
        # Log the incoming request
        logger.info(f"Search request received: {search_request.model_dump_json()}")
        
        # Validate request
        if not search_request.query:
            raise HTTPException(status_code=400, detail="Search query cannot be empty")
        
        if not search_request.sources:
            raise HTTPException(status_code=400, detail="At least one source must be specified")
        
        if not search_request.metrics:
            raise HTTPException(status_code=400, detail="At least one metric must be specified")
        
        # Log if this is a transformed query
        if search_request.useTransformedQuery:
            logger.info(f"Using transformed query: {search_request.query}")
            if search_request.originalQuery:
                logger.info(f"Original query was: {search_request.originalQuery}")
        
        # Get results from each source with fallback mechanisms
        results = await get_results_with_fallback(
            query=search_request.query,
            sources=search_request.sources,
            fields=search_request.fields,
            max_results=search_request.max_results
        )
        
        # Check if we got any results
        if not results:
            logger.warning("No results found from any source")
            raise HTTPException(status_code=404, detail="No results found from any source")
        
        # Log result counts
        for source, source_results in results.items():
            logger.info(f"Retrieved {len(source_results)} results from {source}")
        
        # Compare results using specified metrics and fields
        comparison = compare_results(
            sources_results=results,
            metrics=search_request.metrics,
            fields=search_request.fields
        )
        
        # Return combined results and comparison
        return {
            "query": search_request.query,
            "originalQuery": search_request.originalQuery,
            "sources": search_request.sources,
            "metrics": search_request.metrics,
            "fields": search_request.fields,
            "results": results,
            "comparison": comparison
        }
    except Exception as e:
        logger.error(f"Error in search comparison: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search comparison failed: {str(e)}")

@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    """Handle search requests.

    Args:
        request: The search request containing query and parameters

    Returns:
        SearchResponse containing search results
    """
    try:
        results = await search_service.search(request)
        return SearchResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transform-query", response_model=TransformQueryResponse)
async def transform_query(request: TransformQueryRequest) -> TransformQueryResponse:
    """Transform a query with field boosts.

    Args:
        request: The request containing query and field boosts

    Returns:
        TransformQueryResponse containing the transformed query
    """
    try:
        transformed_query = transform_query_with_boosts(request.query, request.field_boosts)
        return TransformQueryResponse(transformed_query=transformed_query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 