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
        # Return a placeholder result instead of empty list
        no_results_msg = f"Web of Science API key not found in environment variables."
        placeholder = SearchResult(
            title="[Web of Science API Error]",
            author=[],
            abstract=no_results_msg,
            doi=None,
            year=None,
            url="https://webofknowledge.com",
            source="webOfScience",
            rank=1,
            citation_count=0
        )
        return [placeholder]
    
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
                # Return placeholder for error case
                no_results_msg = f"Error accessing Web of Science API: Status {response.status_code}"
                placeholder = SearchResult(
                    title="[Web of Science API Error]",
                    author=[],
                    abstract=no_results_msg,
                    doi=None,
                    year=None,
                    url="https://webofknowledge.com",
                    source="webOfScience",
                    rank=1,
                    citation_count=0
                )
                return [placeholder]
            
            data = response.json()
            
            # Log the API response structure for debugging
            if 'hits' in data and len(data['hits']) > 0:
                first_hit = data['hits'][0]
                logger.debug(f"First WoS result structure: {first_hit}")
                if 'document' in first_hit:
                    doc_fields = list(first_hit['document'].keys())
                    logger.debug(f"Document fields available: {doc_fields}")
                    # Log title structure specifically
                    if 'title' in first_hit['document']:
                        logger.debug(f"Title field structure: {first_hit['document']['title']}")
            
            # Check if there are results
            documents = data.get('hits', [])
            total = data.get('metadata', {}).get('total', 0)
            
            logger.info(f"WoS query returned {total} total results, {len(documents)} in this page")
            
            if not documents:
                # No results found
                logger.warning(f"No results found in Web of Science for '{query}'")
                no_results_msg = f"The term '{query}' did not match any documents in the Web of Science Core Collection."
                placeholder = SearchResult(
                    title="[No results found in Web of Science database]",
                    author=[],
                    abstract=no_results_msg,
                    doi=None,
                    year=None,
                    url="https://webofknowledge.com",
                    source="webOfScience",
                    rank=1,
                    citation_count=0
                )
                return [placeholder]
            
            # Process the results - COMPLETELY CHANGED TO MATCH WORKING IMPLEMENTATION
            results = []
            for i, doc in enumerate(documents[:num_results], 1):
                try:
                    # Extract fields directly from top-level document or from document.document
                    doc_data = doc.get("document", doc)  # Try document field first, fall back to doc itself
                    
                    # Get title - try different possible locations
                    title = None
                    if "title" in doc_data:
                        title_field = doc_data.get("title")
                        if isinstance(title_field, str):
                            title = title_field
                        elif isinstance(title_field, dict) and "value" in title_field:
                            title = title_field.get("value")
                    
                    # If no title found, use placeholder
                    if not title:
                        title = f"[Web of Science Record #{i}]"
                    
                    # Get DOI - try different possible locations
                    doi = None
                    if "identifiers" in doc_data:
                        identifiers = doc_data.get("identifiers")
                        if isinstance(identifiers, dict):
                            doi = identifiers.get("doi")
                        elif isinstance(identifiers, dict) and "identifiers" in identifiers:
                            for id_item in identifiers.get("identifiers", []):
                                if id_item.get("type") == "doi":
                                    doi = id_item.get("value")
                                    break
                    
                    # Get authors - try different possible locations
                    authors = []
                    if "names" in doc_data and "authors" in doc_data.get("names", {}):
                        author_list = doc_data.get("names", {}).get("authors", [])
                        for author in author_list:
                            display_name = author.get("displayName")
                            if display_name:
                                authors.append(display_name)
                    elif "authors" in doc_data:
                        author_obj = doc_data.get("authors", {})
                        if "authors" in author_obj:
                            for author in author_obj.get("authors", []):
                                name_parts = []
                                if author.get("lastName"):
                                    name_parts.append(author.get("lastName"))
                                if author.get("firstName"):
                                    name_parts.append(author.get("firstName"))
                                if name_parts:
                                    authors.append(" ".join(name_parts))
                    
                    # Get year - try different possible locations
                    year = None
                    if "source" in doc_data and "publishYear" in doc_data.get("source", {}):
                        year_str = doc_data.get("source", {}).get("publishYear")
                        if year_str:
                            try:
                                year = int(year_str)
                            except (ValueError, TypeError):
                                year = None
                    
                    # Get citation count
                    citation_count = 0
                    if "metrics" in doc_data and "citationCount" in doc_data.get("metrics", {}):
                        citation_count = doc_data.get("metrics", {}).get("citationCount", 0)
                    
                    # Create URL - use DOI or WoS ID
                    url = None
                    uid = doc_data.get('uid')
                    if uid:
                        url = f"https://www.webofscience.com/wos/woscc/full-record/{uid}"
                    elif doi:
                        url = f"https://doi.org/{doi}"
                    
                    # Create abstract
                    abstract = ""
                    if "abstract" in doc_data:
                        abstract_obj = doc_data.get("abstract", {})
                        if isinstance(abstract_obj, dict) and "abstract" in abstract_obj:
                            for item in abstract_obj.get("abstract", []):
                                if "value" in item:
                                    abstract = item.get("value", "")
                                    break
                    
                    # Create result object
                    result = SearchResult(
                        title=title,
                        author=authors,
                        abstract=abstract,
                        doi=doi,
                        year=year,
                        url=url,
                        source="webOfScience",
                        rank=i,
                        citation_count=citation_count
                    )
                    results.append(result)
                    logger.debug(f"Processed WoS result {i}: {title}")
                except Exception as e:
                    logger.error(f"Error processing WoS result {i}: {str(e)}")
                    continue
            
            logger.info(f"Retrieved {len(results)} results from Web of Science")
            return results
            
    except Exception as e:
        logger.error(f"Error in WoS API request: {str(e)}")
        # Create a placeholder result for exception case
        no_results_msg = f"Error accessing Web of Science API: {str(e)}"
        placeholder = SearchResult(
            title="[Web of Science API Error]",
            author=[],
            abstract=no_results_msg,
            doi=None,
            year=None,
            url="https://webofknowledge.com",
            source="webOfScience",
            rank=1,
            citation_count=0
        )
        return [placeholder]


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