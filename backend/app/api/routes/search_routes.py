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

from ...api.models import SearchRequest, SearchResult, SearchResponse, SearchRequestWithBoosts, BoostConfig
from ...services.search_service import get_results_with_fallback, compare_results, SearchService
from ...services.query_transformation import transform_query_with_boosts
from ...services.boost_service import apply_all_boosts

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

class SearchRequestWithBoosts(SearchRequest):
    """Extended search request model that includes boost configurations."""
    boost_config: Optional[BoostConfig] = None

@router.post("/search/compare")
async def compare_search_engines(
    search_request: SearchRequestWithBoosts
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
            max_results=search_request.max_results,
            use_transformed_query=search_request.useTransformedQuery,
            original_query=search_request.originalQuery
        )
        
        # Check if we got any results
        if not any(results.values()):
            raise HTTPException(status_code=404, detail="No results found from any source")
        
        # Apply boosts if configured
        if search_request.boost_config:
            logger.info(f"Applying boosts with config: {search_request.boost_config.model_dump_json()}")
            for source, source_results in results.items():
                if source_results:
                    # Create a boost config dictionary from the BoostConfig model
                    boost_config = {
                        "citation_boost": search_request.boost_config.citation_boost,
                        "min_citations": search_request.boost_config.min_citations,
                        "recency_boost": search_request.boost_config.recency_boost,
                        "reference_year": search_request.boost_config.reference_year,
                        "doctype_boosts": search_request.boost_config.doctype_boosts
                    }
                    boosted_results = await apply_all_boosts(
                        source_results,
                        boost_config
                    )
                    results[source] = boosted_results
                    logger.info(f"Retrieved {len(boosted_results)} results from {source}")
        
        # Compare results if we have multiple sources
        comparison_metrics = {}
        if len(search_request.sources) > 1:
            comparison_metrics = compare_results(
                results,
                search_request.metrics,
                search_request.fields
            )
        
        return {
            "query": search_request.query,
            "sources": search_request.sources,
            "metrics": search_request.metrics,
            "fields": search_request.fields,
            "results": results,
            "comparison": comparison_metrics
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error in search comparison: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error in search comparison: {str(e)}")

@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequestWithBoosts) -> SearchResponse:
    """Handle search requests.

    Args:
        request: The search request containing query and parameters

    Returns:
        SearchResponse containing search results
    """
    try:
        results = await search_service.search(request)
        
        # Apply boosts if configured
        if request.boost_config:
            # Create a boost config dictionary from the BoostConfig model
            boost_config = {
                "citation_boost": request.boost_config.citation_boost,
                "min_citations": request.boost_config.min_citations,
                "recency_boost": request.boost_config.recency_boost,
                "reference_year": request.boost_config.reference_year,
                "doctype_boosts": request.boost_config.doctype_boosts
            }
            results = await apply_all_boosts(
                results,
                boost_config
            )
        
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