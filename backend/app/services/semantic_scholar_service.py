"""
Semantic Scholar service module for the search-comparisons application.

This module handles interactions with the Semantic Scholar API, including
searching for publications and retrieving bibliographic information.
"""
import os
import logging
from typing import List, Dict, Any, Optional

import httpx

from ..api.models import SearchResult
from ..utils.http import safe_api_request

# Setup logging
logger = logging.getLogger(__name__)

# API Constants
SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
NUM_RESULTS = 20
TIMEOUT_SECONDS = 15

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
                "query": query,
                "limit": num_results,
                "fields": ",".join(API_FIELDS)
            }
            
            # Make request
            logger.info(f"Querying Semantic Scholar API with: {query}")
            response_data = await safe_api_request(
                client, 
                "GET", 
                SEMANTIC_SCHOLAR_API_URL, 
                headers=headers, 
                params=params,
                timeout=TIMEOUT_SECONDS
            )
            
            # Process results
            papers = response_data.get("data", [])
            if not papers:
                logger.warning(f"No results found from Semantic Scholar for query: {query}")
                return []
            
            results: List[SearchResult] = []
            
            for rank, paper in enumerate(papers, 1):
                # Extract author names
                authors = []
                for author in paper.get("authors", []):
                    name = author.get("name")
                    if name:
                        authors.append(name)
                
                # Extract DOI if available
                external_ids = paper.get("externalIds", {})
                doi = external_ids.get("DOI") if external_ids else None
                
                # Create result object
                result = SearchResult(
                    title=paper.get("title", ""),
                    authors=authors,
                    abstract=paper.get("abstract", ""),
                    doi=doi,
                    year=paper.get("year"),
                    url=paper.get("url"),
                    source="semanticScholar",
                    rank=rank,
                    citation_count=paper.get("citationCount")
                )
                results.append(result)
            
            logger.info(f"Retrieved {len(results)} results from Semantic Scholar")
            return results
            
    except Exception as e:
        logger.error(f"Error retrieving results from Semantic Scholar: {str(e)}")
        return []


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