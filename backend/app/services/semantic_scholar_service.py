"""
Semantic Scholar service module for the search-comparisons application.

This module handles interactions with the Semantic Scholar API, including
searching for publications and retrieving bibliographic information.
"""
import os
import logging
import time
import random
import asyncio
from typing import List, Dict, Any, Optional

import httpx

from ..api.models import SearchResult
from ..utils.http import safe_api_request
from ..utils.cache import get_cache_key, save_to_cache, load_from_cache

# Setup logging
logger = logging.getLogger(__name__)

# API Constants
SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
NUM_RESULTS = 20
TIMEOUT_SECONDS = 30  # Increased timeout
MAX_RETRIES = 5

# Field mappings to convert API response fields to our model fields
FIELD_MAPPING = {
    "title": "title",
    "authors": "authors",
    "abstract": "abstract",
    "year": "year",
    "doi": "externalIds.DOI",
    "citation_count": "citationCount"
}

# Fields to request from the API
API_FIELDS = [
    "title",
    "abstract",
    "authors",
    "year",
    "citationCount",
    "externalIds",
    "url"
]


async def get_semantic_scholar_results(
    query: str, 
    fields: List[str],
    num_results: int = NUM_RESULTS
) -> List[SearchResult]:
    """
    Get search results from the Semantic Scholar API.
    
    Queries the Semantic Scholar API with the given search terms and returns
    results formatted as SearchResult objects.
    
    Args:
        query: Search query string
        fields: List of fields to include in results
        num_results: Maximum number of results to return
    
    Returns:
        List[SearchResult]: List of search results from Semantic Scholar
    """
    # Check cache first - now using the shared cache mechanism
    cache_key = get_cache_key("semanticScholar", query, fields)
    cached_results = load_from_cache(cache_key)
    
    if cached_results is not None:
        logger.info(f"Retrieved {len(cached_results)} Semantic Scholar results from cache")
        return cached_results
    
    # Set headers with API key if available
    headers = {}
    if SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY
    
    # Set query parameters
    params = {
        "query": query,
        "limit": num_results,
        "fields": ",".join(API_FIELDS)
    }
    
    # Implement progressive backoff for retries
    base_delay = 2  # seconds
    
    for attempt in range(MAX_RETRIES):
        try:
            # Add delay on retries - exponential backoff
            if attempt > 0:
                retry_delay = base_delay * (2 ** (attempt - 1)) + random.random()  # 2, 4, 8, 16... + jitter
                logger.info(f"Semantic Scholar retry {attempt+1}/{MAX_RETRIES}, waiting {retry_delay:.2f}s")
                await asyncio.sleep(retry_delay)
            
            logger.info(f"Making Semantic Scholar API request (attempt {attempt+1}/{MAX_RETRIES})")
            
            async with httpx.AsyncClient() as client:
                # More direct way of making the request with better timeout handling
                response = await client.get(
                    SEMANTIC_SCHOLAR_API_URL,
                    params=params,
                    headers=headers,
                    timeout=TIMEOUT_SECONDS
                )
                
                # Handle rate limiting explicitly
                if response.status_code == 429:
                    retry_after = int(response.headers.get('retry-after', 1))
                    logger.warning(f"Semantic Scholar API rate limit hit. Retrying after {retry_after}s")
                    await asyncio.sleep(retry_after + random.random())
                    continue
                
                # Check for other errors
                if response.status_code != 200:
                    logger.error(f"Error fetching from Semantic Scholar. Status: {response.status_code}")
                    if response.status_code >= 500:  # Server error, retry
                        continue
                    else:  # Client error, don't retry
                        break
                
                # Parse JSON response
                data = response.json()
                papers = data.get("data", [])
                
                if not papers:
                    logger.warning(f"No results found from Semantic Scholar for query: {query}")
                    break
                
                logger.info(f"Received {len(papers)} results from Semantic Scholar")
                
                # Process results
                results: List[SearchResult] = []
                
                for rank, paper in enumerate(papers, 1):
                    try:
                        # Extract author names (maximum 3 to match other engines)
                        authors = []
                        if paper.get("authors"):
                            for author in paper["authors"][:3]:
                                name = author.get("name")
                                if name:
                                    authors.append(name)
                        
                        # Extract DOI if available
                        doi = None
                        if paper.get("externalIds") and paper["externalIds"].get("DOI"):
                            doi = paper["externalIds"]["DOI"]
                        
                        # Create URL (paper URL or DOI URL)
                        url = paper.get("url", "")
                        if not url and doi:
                            url = f"https://doi.org/{doi}"
                        
                        # Create result object
                        result = SearchResult(
                            title=paper.get("title", ""),
                            authors=authors,
                            abstract=paper.get("abstract", ""),
                            doi=doi,
                            year=paper.get("year"),
                            url=url,
                            source="semanticScholar",
                            rank=rank,
                            citation_count=paper.get("citationCount")
                        )
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Error processing Semantic Scholar result {rank}: {str(e)}")
                
                # Save to cache and return if we have results
                if results:
                    logger.info(f"Retrieved {len(results)} results from Semantic Scholar")
                    save_to_cache(cache_key, results)
                    return results
                
                # No results found after successful request
                break
                
        except httpx.TimeoutException:
            logger.warning(f"Semantic Scholar API timeout (attempt {attempt+1})")
            # Continue to next retry
        except Exception as e:
            logger.error(f"Error retrieving results from Semantic Scholar (attempt {attempt+1}): {str(e)}")
            # Continue to next retry
    
    # If we reach here, all attempts failed or returned no results
    logger.warning(f"No results found in Semantic Scholar for '{query}' after {MAX_RETRIES} attempts")
    
    # Create a placeholder result
    no_results_msg = f"The term '{query}' did not match any documents in Semantic Scholar, or the API rate limit was exceeded."
    placeholder = SearchResult(
        title="[No results found in Semantic Scholar]",
        authors=[],
        abstract=no_results_msg,
        doi=None,
        year=None,
        url="https://www.semanticscholar.org/",
        source="semanticScholar",
        rank=1,
        citation_count=0
    )
    results = [placeholder]
    
    # Save to cache
    save_to_cache(cache_key, results)
    return results


async def get_paper_details_by_doi(doi: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed paper information from Semantic Scholar using a DOI.
    
    Retrieves comprehensive metadata for a specific paper identified by its
    Digital Object Identifier (DOI).
    
    Args:
        doi: Digital Object Identifier for the paper
    
    Returns:
        Optional[Dict[str, Any]]: Paper details if found, None otherwise
    """
    if not doi:
        logger.warning("Empty DOI provided to get_paper_details_by_doi")
        return None
    
    api_url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
    
    fields = [
        "title",
        "abstract",
        "authors",
        "year",
        "citationCount",
        "citations",
        "references",
        "embedding",
        "tldr",
        "fieldsOfStudy"
    ]
    
    try:
        async with httpx.AsyncClient() as client:
            # Set headers with API key if available
            headers = {
                "Content-Type": "application/json",
            }
            
            if SEMANTIC_SCHOLAR_API_KEY:
                headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY
            
            # Set query parameters
            params = {
                "fields": ",".join(fields)
            }
            
            # Make request
            logger.info(f"Retrieving paper details from Semantic Scholar for DOI: {doi}")
            paper_data = await safe_api_request(
                client, 
                "GET", 
                api_url, 
                headers=headers, 
                params=params,
                timeout=TIMEOUT_SECONDS
            )
            
            if not paper_data:
                logger.warning(f"No data found for DOI: {doi} from Semantic Scholar")
                return None
            
            logger.info(f"Successfully retrieved paper details for DOI: {doi} from Semantic Scholar")
            return paper_data
            
    except Exception as e:
        logger.error(f"Error retrieving paper details for DOI {doi} from Semantic Scholar: {str(e)}")
        return None 