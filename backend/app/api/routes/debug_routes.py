"""
Debug API routes for the search-comparisons application.

This module contains route definitions for debug-related endpoints,
used for diagnostics, testing, and development purposes.
"""
import logging
import os
import time
from typing import Dict, List, Any, Optional
import httpx

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.responses import JSONResponse

from ...api.models import SearchResult
from ...services.ads_service import get_bibcode_from_doi, get_ads_results
from ...services.scholar_service import get_scholar_direct_html, get_scholar_results
from ...services.semantic_scholar_service import get_semantic_scholar_results, get_paper_details_by_doi
from ...services.web_of_science_service import get_web_of_science_results, get_wos_auth_token
from ...services.search_service import get_paper_details

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/debug",
    tags=["debug"],
    responses={404: {"description": "Not found"}},
)


@router.get("/sources")
async def list_available_sources() -> Dict[str, Any]:
    """
    List all available search sources and their configuration.
    
    Returns configuration information for each search source, including
    whether it's enabled, its priority order, and timeout settings.
    
    Returns:
        Dict[str, Any]: Dictionary of available sources and their settings
    """
    # Import service configuration
    from ...services.search_service import SERVICE_CONFIG
    
    return {
        "sources": SERVICE_CONFIG,
        "timestamp": time.time()
    }


@router.get("/env")
async def get_environment_info() -> Dict[str, Any]:
    """
    Get information about the runtime environment.
    
    Returns information about the current environment, including
    Python version, environment variables (with sensitive data masked),
    and runtime settings.
    
    Returns:
        Dict[str, Any]: Dictionary of environment information
    """
    import sys
    import platform
    
    # Get environment variables (masking sensitive ones)
    env_vars = {}
    sensitive_vars = ["API_KEY", "SECRET", "PASSWORD", "TOKEN"]
    
    for key, value in os.environ.items():
        # Skip internal or non-string values
        if not isinstance(value, str):
            continue
            
        # Mask sensitive values
        if any(sensitive in key.upper() for sensitive in sensitive_vars) and value:
            if len(value) > 8:
                masked_value = f"{value[:4]}...{value[-4:]}"
            else:
                masked_value = "[MASKED]"
            env_vars[key] = masked_value
        else:
            env_vars[key] = value
    
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "environment": os.environ.get("APP_ENVIRONMENT", "unknown"),
        "debug": os.environ.get("DEBUG", "False").lower() in ("true", "1", "t"),
        "environment_variables": env_vars,
        "timestamp": time.time()
    }


@router.get("/ping/{source}")
async def ping_source(source: str) -> Dict[str, Any]:
    """
    Ping a specific search source to check if it's available.
    
    Sends a basic request to the specified search source to verify
    that the service is accessible and responding.
    
    Args:
        source: Name of the search source to ping
    
    Returns:
        Dict[str, Any]: Dictionary with ping results
    
    Raises:
        HTTPException: If the source doesn't exist or if the ping fails
    """
    start_time = time.time()
    success = False
    message = ""
    
    try:
        if source == "ads":
            # Test ADS by getting a known DOI
            bibcode = await get_bibcode_from_doi("10.1086/160554")
            success = bibcode is not None
            message = f"Successfully retrieved bibcode: {bibcode}" if success else "Failed to retrieve bibcode"
            
        elif source == "scholar":
            # Test Scholar by getting HTML for a simple query
            html = await get_scholar_direct_html("astronomy", 1)
            success = html is not None and len(html) > 0
            message = f"Successfully retrieved HTML ({len(html)} bytes)" if success else "Failed to retrieve HTML"
            
        elif source == "semanticScholar":
            # Test Semantic Scholar by getting a paper details
            paper = await get_paper_details_by_doi("10.1086/160554")
            success = paper is not None
            message = "Successfully retrieved paper details" if success else "Failed to retrieve paper details"
            
        elif source == "webOfScience":
            # Test Web of Science by getting an auth token
            token = await get_wos_auth_token()
            success = token is not None
            message = "Successfully retrieved auth token" if success else "Failed to retrieve auth token"
            
        else:
            raise HTTPException(status_code=404, detail=f"Unknown source: {source}")
            
    except Exception as e:
        success = False
        message = f"Error pinging {source}: {str(e)}"
        logger.error(message)
    
    # Calculate response time
    elapsed_time = (time.time() - start_time) * 1000  # Convert to milliseconds
    
    return {
        "source": source,
        "success": success,
        "message": message,
        "response_time_ms": round(elapsed_time, 2),
        "timestamp": time.time()
    }


@router.get("/search/{source}")
async def test_search_source(
    source: str, 
    query: str = Query(..., description="Search query string"),
    limit: int = Query(5, description="Maximum number of results to return")
) -> Dict[str, Any]:
    """
    Test search for a specific source with a given query.
    
    Performs a search with the specified search engine and returns
    the raw results for debugging purposes.
    
    Args:
        source: Name of the search source to test
        query: Search query string
        limit: Maximum number of results to return
    
    Returns:
        Dict[str, Any]: Dictionary with search results
    
    Raises:
        HTTPException: If the source doesn't exist or if the search fails
    """
    fields = ["title", "authors", "abstract", "doi", "year", "citation_count"]
    start_time = time.time()
    results: List[SearchResult] = []
    
    try:
        if source == "ads":
            results = await get_ads_results(query, fields, limit)
        elif source == "scholar":
            results = await get_scholar_results(query, fields, limit)
        elif source == "semanticScholar":
            results = await get_semantic_scholar_results(query, fields, limit)
        elif source == "webOfScience":
            results = await get_web_of_science_results(query, fields, limit)
        else:
            raise HTTPException(status_code=404, detail=f"Unknown source: {source}")
            
    except Exception as e:
        logger.error(f"Error testing search for {source}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error testing search: {str(e)}")
    
    # Calculate response time
    elapsed_time = (time.time() - start_time) * 1000  # Convert to milliseconds
    
    return {
        "source": source,
        "query": query,
        "count": len(results),
        "results": results,
        "response_time_ms": round(elapsed_time, 2),
        "timestamp": time.time()
    }


@router.get("/paper/{doi}")
async def get_paper_by_doi(
    doi: str,
    sources: List[str] = Query(None, description="List of sources to query (default: all)")
) -> Dict[str, Any]:
    """
    Get detailed paper information from multiple sources by DOI.
    
    Retrieves comprehensive metadata for a paper identified by its
    Digital Object Identifier (DOI) from multiple search engines.
    
    Args:
        doi: Digital Object Identifier for the paper
        sources: List of sources to query (default: all available)
    
    Returns:
        Dict[str, Any]: Dictionary with paper details from all sources
    
    Raises:
        HTTPException: If the DOI is invalid or if the retrieval fails
    """
    if not doi:
        raise HTTPException(status_code=400, detail="DOI cannot be empty")
    
    try:
        # Get paper details from multiple sources
        paper_details = await get_paper_details(doi, sources)
        
        if not paper_details or not paper_details.get("sources"):
            raise HTTPException(status_code=404, detail=f"No paper found for DOI: {doi}")
        
        return paper_details
        
    except Exception as e:
        logger.error(f"Error retrieving paper details for DOI {doi}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving paper details: {str(e)}")


@router.get("/request-headers")
async def get_request_headers(request: Request) -> Dict[str, Any]:
    """
    Show the headers of the current request.
    
    Returns the headers sent by the client in the current request,
    which can be useful for debugging proxy, CORS, and authentication issues.
    
    Args:
        request: The FastAPI request object
    
    Returns:
        Dict[str, Any]: Dictionary of request headers
    """
    headers = dict(request.headers)
    
    # Mask authorization headers for security
    if "authorization" in headers:
        auth_value = headers["authorization"]
        if len(auth_value) > 15:
            headers["authorization"] = f"{auth_value[:7]}...{auth_value[-7:]}"
        else:
            headers["authorization"] = "[MASKED]"
    
    return {
        "headers": headers,
        "client": {
            "host": request.client.host if request.client else None,
            "port": request.client.port if request.client else None
        },
        "timestamp": time.time()
    } 