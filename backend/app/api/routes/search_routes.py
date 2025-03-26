"""
Search-related API routes for the search-comparisons application.

This module contains route definitions for search-related endpoints,
including the main comparison endpoint that handles searching across
multiple engines and computing similarity metrics.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Any, Optional

from ...api.models import SearchRequest, SearchResult
from ...services.search_service import get_results_with_fallback, compare_results

# Create router
router = APIRouter(
    prefix="/api",
    tags=["search"],
    responses={404: {"description": "Not found"}},
)


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
    # Validate request
    if not search_request.query:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    
    if not search_request.sources:
        raise HTTPException(status_code=400, detail="At least one source must be specified")
    
    if not search_request.metrics:
        raise HTTPException(status_code=400, detail="At least one metric must be specified")
    
    # Get results from each source with fallback mechanisms
    results = await get_results_with_fallback(
        query=search_request.query,
        sources=search_request.sources,
        fields=search_request.fields
    )
    
    # Check if we got any results
    if not results:
        raise HTTPException(status_code=404, detail="No results found from any source")
    
    # Compare results using specified metrics and fields
    comparison = compare_results(
        sources_results=results,
        metrics=search_request.metrics,
        fields=search_request.fields
    )
    
    # Return combined results and comparison
    return {
        "query": search_request.query,
        "sources": search_request.sources,
        "metrics": search_request.metrics,
        "fields": search_request.fields,
        "results": results,
        "comparison": comparison
    } 