"""
Web of Science service module for the search-comparisons application.

This module handles interactions with the Web of Science API, including
searching for publications and retrieving bibliographic information.
"""
import os
import logging
from typing import List, Dict, Any, Optional, Union

import httpx

from ..api.models import SearchResult
from ..utils.http import safe_api_request

# Setup logging
logger = logging.getLogger(__name__)

# API Constants - Exactly matching the search-engine-comparator
WOS_API_URL = "https://api.clarivate.com/apis/wos-starter/v1/"
WOS_API_KEY = os.environ.get("WEB_OF_SCIENCE_API_KEY", "")  # Using the exact environment variable name

# Log the API key for debugging (masking most of it)
if WOS_API_KEY:
    masked_key = f"{WOS_API_KEY[:4]}...{WOS_API_KEY[-4:]}" if len(WOS_API_KEY) > 8 else "[MASKED]"
    logger.info(f"WEB_OF_SCIENCE_API_KEY found in environment: {masked_key}")
else:
    logger.error("WEB_OF_SCIENCE_API_KEY not found in environment - searched for 'WEB_OF_SCIENCE_API_KEY'")
    # Try alternate environment variable names
    alternate_keys = ["WOS_API_KEY", "WEBOFSCIENCE_API_KEY", "WOS_KEY"]
    for alt_key in alternate_keys:
        alt_value = os.environ.get(alt_key)
        if alt_value:
            logger.info(f"Found alternative key '{alt_key}' - using this instead")
            WOS_API_KEY = alt_value
            break

NUM_RESULTS = 20
TIMEOUT_SECONDS = 30  # Increased to match search-engine-comparator

# Field mappings
FIELD_MAPPING = {
    "title": "title",
    "authors": "authors",
    "abstract": "abstract",
    "doi": "doi",
    "year": "publishYear",
    "citation_count": "citationCount"
}

async def get_web_of_science_results(
    query: str, 
    fields: List[str],
    num_results: int = NUM_RESULTS
) -> List[SearchResult]:
    """
    Get search results from the Web of Science API.
    
    Uses the Web of Science API key to authenticate and perform the search query,
    then formats the results as SearchResult objects.
    
    Args:
        query: Search query string
        fields: List of fields to include in results
        num_results: Maximum number of results to return
    
    Returns:
        List[SearchResult]: List of search results from Web of Science
    """
    # Check if API key is available
    if not WOS_API_KEY:
        logger.error("WEB_OF_SCIENCE_API_KEY not found in environment")
        return []
    
    logger.info(f"Using WOS_API_KEY: {WOS_API_KEY[:4]}...{WOS_API_KEY[-4:] if len(WOS_API_KEY) > 8 else ''}")
    
    # Format query with proper WoS syntax - EXACTLY as in search-engine-comparator
    wos_query = f'AU=({query}) OR TS=({query})'
    
    # The correct WoS Starter API endpoint
    base_url = f"{WOS_API_URL}documents"
    
    headers = {
        "X-ApiKey": WOS_API_KEY,
        "Accept": "application/json"
    }
    
    params = {
        "db": "WOS",
        "q": wos_query,
        "limit": min(num_results, 50),
        "page": 1
    }
    
    logger.info(f"Making Web of Science API request with query: {wos_query}")
    logger.info(f"Request URL: {base_url}")
    logger.info(f"Request headers: {headers}")
    logger.info(f"Request parameters: {params}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                base_url,
                headers=headers,
                params=params,
                timeout=TIMEOUT_SECONDS
            )
            
            # Log response status
            logger.info(f"Web of Science API response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.warning(f"WoS API error: Status {response.status_code}")
                logger.debug(f"Response: {response.text[:500]}")
                # Return empty list for error case
                return []
            
            data = response.json()
            
            # Check if there are results
            documents = data.get('hits', [])
            total = data.get('metadata', {}).get('total', 0)
            
            logger.info(f"WoS query returned {total} total results, {len(documents)} in this page")
            
            if not documents:
                # No results found
                logger.warning(f"No results found in Web of Science for '{query}'")
                return []
            
            # Process the results
            results = []
            for i, doc in enumerate(documents[:num_results], 1):
                try:
                    # Get document data
                    doc_data = doc.get("document", {})
                    
                    # Extract title
                    title = ""
                    title_obj = doc_data.get("title", {})
                    titles = title_obj.get("titles", [])
                    for title_data in titles:
                        if title_data.get("type") == "item":
                            title = title_data.get("value", "")
                            break
                    
                    # Extract authors
                    authors = []
                    author_obj = doc_data.get("authors", {})
                    author_list = author_obj.get("authors", [])
                    for author in author_list:
                        name_parts = []
                        if author.get("lastName"):
                            name_parts.append(author.get("lastName"))
                        if author.get("firstName"):
                            name_parts.append(author.get("firstName"))
                        if name_parts:
                            authors.append(" ".join(name_parts))
                    
                    # Extract abstract
                    abstract = ""
                    abstract_obj = doc_data.get("abstract", {})
                    abstract_list = abstract_obj.get("abstract", [])
                    for abstract_data in abstract_list:
                        abstract = abstract_data.get("value", "")
                        break
                    
                    # Extract DOI
                    doi = None
                    identifiers = doc_data.get("identifiers", {}).get("identifiers", [])
                    for id_data in identifiers:
                        if id_data.get("type") == "doi":
                            doi = id_data.get("value")
                            break
                    
                    # Extract year
                    year = None
                    source = doc_data.get("source", {})
                    pub_year = source.get("publishYear")
                    if pub_year:
                        try:
                            year = int(pub_year)
                        except (ValueError, TypeError):
                            year = None
                    
                    # Extract citation count
                    citation_count = None
                    metrics = doc_data.get("metrics", {})
                    if metrics:
                        citation_count = metrics.get("citationCount", 0)
                    
                    # Create URL
                    uid = doc_data.get('uid')
                    url = f"https://www.webofscience.com/wos/woscc/full-record/{uid}" if uid else None
                    if doi and not url:
                        url = f"https://doi.org/{doi}"
                    
                    # Create result object
                    result = SearchResult(
                        title=title,
                        authors=authors,
                        abstract=abstract,
                        doi=doi,
                        year=year,
                        url=url,
                        source="webOfScience",
                        rank=i,
                        citation_count=citation_count
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error processing WoS result {i}: {str(e)}")
                    continue
            
            logger.info(f"Retrieved {len(results)} results from Web of Science")
            return results
            
    except Exception as e:
        logger.error(f"Error in WoS API request: {str(e)}")
        return []


async def get_wos_paper_details(doi: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed paper information from Web of Science using a DOI.
    
    Uses the Web of Science API key to retrieve comprehensive
    metadata for a paper identified by its DOI.
    
    Args:
        doi: Digital Object Identifier for the paper
    
    Returns:
        Optional[Dict[str, Any]]: Paper details if found, None otherwise
    """
    if not doi:
        logger.warning("Empty DOI provided to get_wos_paper_details")
        return None
    
    # Check if API key is available
    if not WOS_API_KEY:
        logger.error("WEB_OF_SCIENCE_API_KEY not found in environment")
        return None
    
    # The correct WoS Starter API endpoint
    base_url = f"{WOS_API_URL}documents"
    
    headers = {
        "X-ApiKey": WOS_API_KEY,
        "Accept": "application/json"
    }
    
    params = {
        "db": "WOS",
        "q": f"DO=({doi})"
    }
    
    logger.info(f"Querying Web of Science API for DOI: {doi}")
    logger.info(f"Request URL: {base_url}")
    logger.info(f"Request parameters: {params}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                base_url,
                headers=headers,
                params=params,
                timeout=TIMEOUT_SECONDS
            )
            
            # Log response status
            logger.info(f"Web of Science API response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.warning(f"WoS API error: Status {response.status_code}")
                logger.debug(f"Response: {response.text[:500]}")
                return None
            
            data = response.json()
            
            # Check if we got a response
            documents = data.get("hits", [])
            if not documents:
                logger.warning(f"No document found for DOI: {doi} in Web of Science")
                return None
            
            # Return first matching document
            logger.info(f"Found document for DOI: {doi} in Web of Science")
            return documents[0].get("document", {})
            
    except Exception as e:
        logger.error(f"Error retrieving paper details for DOI {doi} from Web of Science: {str(e)}")
        return None 