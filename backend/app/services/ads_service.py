"""
ADS (Astrophysics Data System) service module for the search-comparisons application.

This module handles interactions with the ADS API and Solr, including searching
for publications and retrieving bibliographic information.
"""
import os
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Union, Literal

import httpx
import aiohttp

from ..api.models import SearchResult
from ..utils.http import safe_api_request
from ..utils.cache import get_cache_key, load_from_cache, save_to_cache

# Setup logging
logger = logging.getLogger(__name__)

# API Constants
ADS_API_URL = "https://api.adsabs.harvard.edu/v1/search/query"
ADS_SOLR_PROXY_URL = os.environ.get("ADS_SOLR_PROXY_URL", "https://scix-solr-proxy.onrender.com/solr/select")
ADS_QUERY_METHOD = os.environ.get("ADS_QUERY_METHOD", "solr_first").lower()  # Options: solr_only, api_only, solr_first (default)
NUM_RESULTS = 20
TIMEOUT_SECONDS = 15

# Field mappings
ADS_FIELD_MAPPING = {
    "title": "title",
    "authors": "author",
    "abstract": "abstract",
    "doi": "doi",
    "year": "year",
    "citation_count": "citation_count",
    "doctype": "doctype",
    "property": "property"
}

# Solr specific fields
SOLR_FIELD_MAPPING = {
    "title": "title",
    "authors": "author",
    "abstract": "abstract",
    "doi": "identifier",  # Solr uses 'identifier' field which contains DOIs
    "year": "year",
    "citation_count": "citation_count",
    "doctype": "doctype",
    "property": "property",
    "url": "url"
}


def get_ads_api_key() -> str:
    """
    Get the ADS API key from environment variables.
    
    Checks both ADS_API_KEY and ADS_API_TOKEN environment variables.
    
    Returns:
        str: The API key if found, empty string otherwise
    """
    api_key = os.environ.get("ADS_API_KEY", "")
    if not api_key:
        api_key = os.environ.get("ADS_API_TOKEN", "")
        
    if not api_key:
        logger.error("ADS_API_KEY not found in environment")
    else:
        # Log masked key for debugging
        masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "[KEY]"
        logger.debug(f"Using ADS API key: {masked_key}")
        
    return api_key

def get_ads_solr_password() -> str:
    """
    Get the ADS Solr password from environment variables.
    
    Returns:
        str: The password if found, empty string otherwise
    """
    solr_password = os.environ.get("ADS_SOLR_PASSWORD", "")
        
    if not solr_password:
        logger.error("ADS_SOLR_PASSWORD not found in environment")
    else:
        # Log masked key for debugging
        masked_key = f"{solr_password[:4]}...{solr_password[-4:]}" if len(solr_password) > 8 else "[KEY]"
        logger.debug(f"Using ADS Solr password: {masked_key}")
        
    return solr_password

async def get_bibcode_from_doi(doi: str) -> Optional[str]:
    """
    Retrieve a bibcode from the ADS API using a DOI.
    
    Searches the ADS API for a paper with the given DOI and returns its bibcode.
    
    Args:
        doi: DOI string to search for
    
    Returns:
        Optional[str]: Bibcode string if found, None otherwise
    """
    if not doi:
        logger.warning("Empty DOI provided to get_bibcode_from_doi")
        return None
    
    # Get API key at runtime
    ads_api_key = get_ads_api_key()
    if not ads_api_key:
        return None
    
    # Format DOI query
    query = f"doi:\"{doi}\""
    
    try:
        async with httpx.AsyncClient() as client:
            # Set API key
            headers = {
                "Authorization": f"Bearer {ads_api_key}",
                "Content-Type": "application/json",
            }
            
            # Set query parameters
            params = {
                "q": query,
                "fl": "bibcode",
                "rows": 1
            }
            
            # Make request
            logger.debug(f"Querying ADS API for DOI: {doi}")
            response_data = await safe_api_request(
                client, 
                "GET", 
                ADS_API_URL, 
                headers=headers, 
                params=params,
                timeout=TIMEOUT_SECONDS
            )
            
            # Check if we got a response
            docs = response_data.get("response", {}).get("docs", [])
            if not docs:
                logger.warning(f"No results found for DOI: {doi}")
                return None
                
            # Extract bibcode
            bibcode = docs[0].get("bibcode")
            if not bibcode:
                logger.warning(f"Bibcode not found in response for DOI: {doi}")
                return None
                
            logger.info(f"Found bibcode {bibcode} for DOI: {doi}")
            return bibcode
            
    except Exception as e:
        logger.error(f"Error retrieving bibcode for DOI {doi}: {str(e)}")
        return None


async def query_ads_solr(
    query: str, 
    fields: List[str], 
    num_results: int = NUM_RESULTS,
    sort: str = "score desc",
    use_cache: bool = False
) -> List[SearchResult]:
    """
    Query the ADS Solr API for search results.
    
    Args:
        query: The search query
        fields: List of fields to return
        num_results: Maximum number of results to return
        sort: Sort order for results
        use_cache: Whether to use cached results
    
    Returns:
        List[SearchResult]: List of search results
    """
    try:
        # Get API key at runtime
        ads_api_key = get_ads_api_key()
        if not ads_api_key:
            logger.error("ADS API key not found")
            return []
        
        # Set up request parameters
        params = {
            "q": query,
            "fl": ",".join(fields),
            "rows": num_results,
            "sort": sort
        }
        
        # Make request to ADS API
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {ads_api_key}",
                "Content-Type": "application/json"
            }
            
            response = await client.get(
                ADS_API_URL,
                params=params,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            
            # Process results
            results = []
            for idx, doc in enumerate(data.get("response", {}).get("docs", []), 1):  # Start rank from 1
                try:
                    # Extract DOI from identifier field if present
                    doi = None
                    if "identifier" in doc:
                        identifiers = doc["identifier"]
                        if isinstance(identifiers, list):
                            for id in identifiers:
                                if id.startswith("doi:"):
                                    doi = id[4:]
                                    break
                        elif isinstance(identifiers, str) and identifiers.startswith("doi:"):
                            doi = identifiers[4:]
                    
                    # Create search result
                    result = SearchResult(
                        title=doc.get("title", [""])[0] if isinstance(doc.get("title"), list) else doc.get("title", ""),
                        authors=doc.get("author", []),
                        abstract=doc.get("abstract", [""])[0] if isinstance(doc.get("abstract"), list) else doc.get("abstract", ""),
                        doi=doi,
                        year=doc.get("year"),
                        url=f"https://ui.adsabs.harvard.edu/abs/{doc.get('bibcode')}/abstract",
                        source="ads",
                        rank=idx,  # Set rank based on index
                        citation_count=doc.get("citation_count", 0),
                        doctype=doc.get("doctype", ""),
                        property=doc.get("property", [])
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error processing document: {str(e)}")
                    continue
            
            # Cache results if enabled
            if use_cache and results:
                cache_key = get_cache_key("ads_solr", query, fields, num_results)
                save_to_cache(cache_key, results)
            
            return results
            
    except Exception as e:
        logger.error(f"Error querying ADS Solr proxy: {str(e)}")
        return []


async def query_ads_api(
    query: str, 
    fields: List[str], 
    num_results: int = NUM_RESULTS,
    sort: str = "score desc",
    use_cache: bool = False
) -> List[SearchResult]:
    """
    Query the official ADS API.
    
    This is the original API query method that requires an API key.
    
    Args:
        query: Search query string
        fields: List of fields to include in results
        num_results: Maximum number of results to return
        sort: Sort parameter for the query (e.g., "score desc", "citation_count desc", "date desc")
        use_cache: Whether to use caching
    
    Returns:
        List[SearchResult]: List of search results from ADS API
    """
    # Get API key at runtime
    ads_api_key = get_ads_api_key()
    if not ads_api_key:
        logger.error("Cannot query ADS API without an API key")
        return []
    
    try:
        # Check cache first if enabled
        if use_cache:
            cache_key = get_cache_key("ads_api", query, fields, num_results)
            cached_results = load_from_cache(cache_key)
            
            if cached_results is not None:
                logger.info(f"Retrieved {len(cached_results)} results from cache for API query")
                return cached_results
        
        async with httpx.AsyncClient() as client:
            # Set headers with API key
            headers = {
                "Authorization": f"Bearer {ads_api_key}", 
                "Content-Type": "application/json",
            }
            
            # Map requested fields to ADS fields
            ads_fields = ["bibcode", "id"]  # Always include these
            for field in fields:
                if field in ADS_FIELD_MAPPING:
                    ads_field = ADS_FIELD_MAPPING[field]
                    if ads_field not in ads_fields:
                        ads_fields.append(ads_field)
            
            # Set query parameters
            params = {
                "q": query,
                "fl": ",".join(ads_fields),
                "rows": num_results,
                "sort": sort
            }
            
            # Make request
            logger.info(f"Querying ADS API with: {query}")
            response_data = await safe_api_request(
                client, 
                "GET", 
                ADS_API_URL, 
                headers=headers, 
                params=params,
                timeout=TIMEOUT_SECONDS
            )
            
            # Check if we got a response
            docs = response_data.get("response", {}).get("docs", [])
            if not docs:
                logger.warning(f"No results found from ADS API for query: {query}")
                return []
            
            # Process results
            results = []
            for rank, doc in enumerate(docs, 1):
                # Create result object
                result = SearchResult(
                    title=doc.get("title", [""])[0] if isinstance(doc.get("title"), list) else doc.get("title", ""),
                    authors=doc.get("author", []),
                    abstract=doc.get("abstract", ""),
                    doi=doc.get("doi", [""])[0] if isinstance(doc.get("doi"), list) else doc.get("doi", ""),
                    year=doc.get("year"),
                    url=f"https://ui.adsabs.harvard.edu/abs/{doc.get('bibcode')}/abstract" if doc.get('bibcode') else None,
                    source="ads",
                    rank=rank,
                    citation_count=doc.get("citation_count", 0),
                    doctype=doc.get("doctype", ""),
                    property=doc.get("property", [])
                )
                results.append(result)
            
            # Save to cache if enabled
            if use_cache and results:
                save_to_cache(cache_key, results)
            
            logger.info(f"Retrieved {len(results)} results from ADS API")
            return results
            
    except Exception as e:
        logger.error(f"Error retrieving results from ADS API: {str(e)}")
        return []


async def get_ads_results(
    query: str,
    fields: List[str] = None,
    num_results: int = 20,
    use_cache: bool = False,
    intent: str = None,
    sort: str = None
) -> List[Any]:
    """
    Get search results from ADS API.
    
    Args:
        query: Search query string
        fields: List of fields to retrieve
        num_results: Maximum number of results to return
        use_cache: Whether to use caching
        intent: Query intent (e.g., "influential", "recent")
        sort: Sort parameter (e.g., "citation_count desc", "date desc")
        
    Returns:
        List[Any]: List of search results
    """
    try:
        # Set default fields if not provided
        if not fields:
            fields = [
                "id", "bibcode", "title", "author", "year", "citation_count",
                "abstract", "doctype", "property", "pub", "volume", "page",
                "doi", "keyword"
            ]
        
        # Determine sort parameter based on intent or provided sort
        sort_param = sort or "score desc"  # Default sort by relevance score
        if not sort and intent:
            if "influential" in intent or "highly cited" in intent or "popular" in intent:
                sort_param = "citation_count desc"
                logger.info(f"Sorting by citation count for intent: {intent}")
            elif "recent" in intent:
                sort_param = "date desc"
                logger.info(f"Sorting by date for intent: {intent}")
        
        # Get API key
        ads_api_key = get_ads_api_key()
        if not ads_api_key:
            logger.error("ADS API key not configured")
            return []
        
        # Prepare query parameters
        params = {
            "q": query,
            "fl": ",".join(fields),
            "rows": num_results,
            "sort": sort_param  # This is the correct way to pass sort parameter
        }
        
        logger.info(f"ADS API request parameters: {params}")
        
        # Make request to ADS API
        async with aiohttp.ClientSession() as session:
            async with session.get(
                ADS_API_URL,
                params=params,
                headers={"Authorization": f"Bearer {ads_api_key}"}
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                # Extract results from response
                results = data.get("response", {}).get("docs", [])
                logger.info(f"Retrieved {len(results)} results from ADS API, sorted by {sort_param}")
                
                return results
                
    except Exception as e:
        logger.error(f"Error getting ADS results: {str(e)}")
        return [] 