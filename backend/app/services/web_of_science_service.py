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

# API Constants
WOS_API_URL = "https://api.clarivate.com/apis/wos-starter/v1/documents"
WOS_AUTH_URL = "https://api.clarivate.com/apis/wos-api/auth/v1/token"
WOS_API_KEY = os.environ.get("WOS_API_KEY", "")
WOS_API_SECRET = os.environ.get("WOS_API_SECRET", "")
NUM_RESULTS = 20
TIMEOUT_SECONDS = 20

# Field mappings
FIELD_MAPPING = {
    "title": "title",
    "authors": "authors",
    "abstract": "abstract",
    "doi": "doi",
    "year": "publicationYear",
    "citation_count": "citationCount"
}

# Auth token cache
auth_token: Optional[str] = None


async def get_wos_auth_token() -> Optional[str]:
    """
    Get an authentication token for the Web of Science API.
    
    Uses the API key and secret to authenticate with the Web of Science API
    and returns an access token for subsequent requests.
    
    Returns:
        Optional[str]: Authentication token if successful, None otherwise
    """
    global auth_token
    
    # Return cached token if available
    if auth_token:
        return auth_token
    
    # Check if credentials are available
    if not WOS_API_KEY or not WOS_API_SECRET:
        logger.error("WOS_API_KEY or WOS_API_SECRET not found in environment")
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            # Prepare auth request
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
            }
            
            data = {
                "grant_type": "client_credentials"
            }
            
            # Make request with basic auth
            logger.info("Requesting Web of Science auth token")
            response = await client.post(
                WOS_AUTH_URL,
                headers=headers,
                data=data,
                auth=(WOS_API_KEY, WOS_API_SECRET),
                timeout=TIMEOUT_SECONDS
            )
            
            # Check response
            response.raise_for_status()
            response_data = response.json()
            
            # Extract token
            token = response_data.get("access_token")
            if not token:
                logger.error("No access token returned from Web of Science auth endpoint")
                return None
                
            # Cache and return token
            auth_token = token
            logger.info("Successfully obtained Web of Science auth token")
            return token
            
    except Exception as e:
        logger.error(f"Error getting Web of Science auth token: {str(e)}")
        return None


async def get_web_of_science_results(
    query: str, 
    fields: List[str],
    num_results: int = NUM_RESULTS
) -> List[SearchResult]:
    """
    Get search results from the Web of Science API.
    
    Authenticates with the Web of Science API, performs the search query,
    and formats the results as SearchResult objects.
    
    Args:
        query: Search query string
        fields: List of fields to include in results
        num_results: Maximum number of results to return
    
    Returns:
        List[SearchResult]: List of search results from Web of Science
    """
    # Get auth token
    token = await get_wos_auth_token()
    if not token:
        logger.error("Unable to authenticate with Web of Science API")
        return []
    
    try:
        async with httpx.AsyncClient() as client:
            # Set headers with auth token
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "X-ApiKey": WOS_API_KEY
            }
            
            # Set query parameters
            params = {
                "q": query,
                "count": num_results,
                "sortField": "relevance"
            }
            
            # Make request
            logger.info(f"Querying Web of Science API with: {query}")
            response_data = await safe_api_request(
                client, 
                "GET", 
                WOS_API_URL, 
                headers=headers, 
                params=params,
                timeout=TIMEOUT_SECONDS
            )
            
            # Check if we got a response
            documents = response_data.get("hits", [])
            if not documents:
                logger.warning(f"No results found from Web of Science for query: {query}")
                return []
            
            # Process results
            results: List[SearchResult] = []
            
            for rank, doc in enumerate(documents, 1):
                # Get document data
                doc_data: Dict[str, Any] = doc.get("document", {})
                
                # Extract title
                title = ""
                for title_data in doc_data.get("title", {}).get("titles", []):
                    if title_data.get("type") == "item":
                        title = title_data.get("value", "")
                        break
                
                # Extract authors
                authors: List[str] = []
                for author in doc_data.get("authors", {}).get("authors", []):
                    name_parts = []
                    if author.get("lastName"):
                        name_parts.append(author.get("lastName"))
                    if author.get("firstName"):
                        name_parts.append(author.get("firstName"))
                    if name_parts:
                        authors.append(" ".join(name_parts))
                
                # Extract abstract
                abstract = ""
                for abstract_data in doc_data.get("abstract", {}).get("abstract", []):
                    abstract = abstract_data.get("value", "")
                    break
                
                # Extract DOI
                doi = None
                for id_data in doc_data.get("identifiers", {}).get("identifiers", []):
                    if id_data.get("type") == "doi":
                        doi = id_data.get("value")
                        break
                
                # Extract year
                year = None
                pub_info = doc_data.get("source", {}).get("publishYear", None)
                if pub_info:
                    try:
                        year = int(pub_info)
                    except (ValueError, TypeError):
                        year = None
                
                # Extract citation count
                citation_count = None
                metrics = doc_data.get("metrics", {})
                if metrics:
                    citation_count = metrics.get("citationCount", 0)
                
                # Create result object
                result = SearchResult(
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    doi=doi,
                    year=year,
                    url=f"https://www.webofscience.com/wos/woscc/full-record/{doc_data.get('uid')}" if doc_data.get('uid') else None,
                    source="webOfScience",
                    rank=rank,
                    citation_count=citation_count
                )
                results.append(result)
            
            logger.info(f"Retrieved {len(results)} results from Web of Science")
            return results
            
    except Exception as e:
        logger.error(f"Error retrieving results from Web of Science: {str(e)}")
        return []


async def get_wos_paper_details(doi: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed paper information from Web of Science using a DOI.
    
    Authenticates with the Web of Science API and retrieves comprehensive
    metadata for a paper identified by its DOI.
    
    Args:
        doi: Digital Object Identifier for the paper
    
    Returns:
        Optional[Dict[str, Any]]: Paper details if found, None otherwise
    """
    if not doi:
        logger.warning("Empty DOI provided to get_wos_paper_details")
        return None
    
    # Get auth token
    token = await get_wos_auth_token()
    if not token:
        logger.error("Unable to authenticate with Web of Science API")
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            # Set headers with auth token
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "X-ApiKey": WOS_API_KEY
            }
            
            # Set query parameters
            params = {
                "q": f"DO=({doi})"
            }
            
            # Make request
            logger.info(f"Querying Web of Science API for DOI: {doi}")
            response_data = await safe_api_request(
                client, 
                "GET", 
                WOS_API_URL, 
                headers=headers, 
                params=params,
                timeout=TIMEOUT_SECONDS
            )
            
            # Check if we got a response
            documents = response_data.get("hits", [])
            if not documents:
                logger.warning(f"No document found for DOI: {doi} in Web of Science")
                return None
            
            # Return first matching document
            logger.info(f"Found document for DOI: {doi} in Web of Science")
            return documents[0].get("document", {})
            
    except Exception as e:
        logger.error(f"Error retrieving paper details for DOI {doi} from Web of Science: {str(e)}")
        return None 