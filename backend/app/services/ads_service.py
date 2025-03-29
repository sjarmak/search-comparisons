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

from ..api.models import SearchResult
from ..utils.http import safe_api_request
from ..utils.cache import get_cache_key, load_from_cache, save_to_cache

# Setup logging
logger = logging.getLogger(__name__)

# API Constants
ADS_API_URL = "https://api.adsabs.harvard.edu/v1/search/query"
ADS_SOLR_PROXY_URL = os.environ.get("ADS_SOLR_PROXY_URL", "https://playground.adsabs.harvard.edu/dev/solr/collection1/select")
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
    "property": "property"
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
        logger.debug(f"Using ADS API key: {masked_key}")
        
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
    num_results: int = NUM_RESULTS
) -> List[SearchResult]:
    """
    Query the dev instance of ADS Solr. 
    
    Uses the dev credentials to access Solr instance directly 
    with a GET request and BasicAuth 
    
    Args:
        query: Search query string
        fields: List of fields to include in results
        num_results: Maximum number of results to return
    
    Returns:
        List[SearchResult]: List of search results from ADS Solr
    """
    logger.info(f"Querying ADS Solr directly via proxy with: {query}")
    
    try:
        # Check cache first
        cache_key = get_cache_key("ads_solr", query, fields, num_results)
        cached_results = load_from_cache(cache_key)
        
        if cached_results is not None:
            logger.info(f"Retrieved {len(cached_results)} results from cache for Solr query")
            return cached_results
        
        async with httpx.AsyncClient() as client:
            # Map requested fields to Solr fields
            solr_fields = ["bibcode", "id"]  # Always include these
            for field in fields:
                if field in SOLR_FIELD_MAPPING:
                    solr_field = SOLR_FIELD_MAPPING[field]
                    if solr_field not in solr_fields:
                        solr_fields.append(solr_field)
            
            # Add special fields needed for processing
            if "doi" in fields and "identifier" not in solr_fields:
                solr_fields.append("identifier")
            
            # Set query parameters
            params = {
                "q": query,
                "fl": ",".join(solr_fields),
                "rows": num_results,
                "sort": "score desc",
                "wt": "json"  # Ensure JSON response format
            }
            
            # Get password
            ads_solr_password = get_ads_solr_password()

            # Make request
            logger.info(f"Querying ADS Solr proxy with: {query}")
            response = await client.get(
                ADS_SOLR_PROXY_URL,
                params=params,
                auth=httpx.BasicAuth('ads', ads_solr_password),
                timeout=TIMEOUT_SECONDS
            )
            
            # Check response status
            if response.status_code != 200:
                logger.error(f"Error from Solr proxy: Status {response.status_code}, {response.text}")
                return []
            
            # Parse JSON response
            response_data = response.json()
            
            # Check if we got a response
            docs = response_data.get("response", {}).get("docs", [])
            if not docs:
                logger.warning(f"No results found from ADS Solr for query: {query}")
                return []
            
            # Process results
            results = []
            for rank, doc in enumerate(docs, 1):
                # Extract DOI from identifier field if present
                doi = None
                if "identifier" in doc:
                    identifiers = doc["identifier"] if isinstance(doc["identifier"], list) else [doc["identifier"]]
                    for identifier in identifiers:
                        if isinstance(identifier, str) and identifier.lower().startswith("doi:"):
                            doi = identifier[4:].strip()
                            break
                
                # Handle title field which can be a list or string
                title = ""
                if "title" in doc:
                    if isinstance(doc["title"], list):
                        title = doc["title"][0] if doc["title"] else ""
                    else:
                        title = doc["title"]
                
                # Create result object
                result = SearchResult(
                    title=title,
                    authors=doc.get("author", []),
                    abstract=doc.get("abstract", ""),
                    doi=doi,
                    year=doc.get("year"),
                    url=f"https://ui.adsabs.harvard.edu/abs/{doc.get('bibcode')}/abstract" if doc.get('bibcode') else None,
                    source="ads",
                    rank=rank,
                    citation_count=doc.get("citation_count", 0),
                    doctype=doc.get("doctype", ""),
                    property=doc.get("property", [])
                )
                results.append(result)
            
            # Save to cache
            if results:
                save_to_cache(cache_key, results)
            
            logger.info(f"Retrieved {len(results)} results from ADS Solr")
            return results
            
    except Exception as e:
        logger.error(f"Error retrieving results from ADS Solr: {str(e)}")
        return []


async def query_ads_api(
    query: str, 
    fields: List[str], 
    num_results: int = NUM_RESULTS
) -> List[SearchResult]:
    """
    Query the official ADS API.
    
    This is the original API query method that requires an API key.
    
    Args:
        query: Search query string
        fields: List of fields to include in results
        num_results: Maximum number of results to return
    
    Returns:
        List[SearchResult]: List of search results from ADS API
    """
    # Get API key at runtime
    ads_api_key = get_ads_api_key()
    if not ads_api_key:
        logger.error("Cannot query ADS API without an API key")
        return []
    
    try:
        # Check cache first
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
                "sort": "score desc"
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
            
            # Save to cache
            if results:
                save_to_cache(cache_key, results)
            
            logger.info(f"Retrieved {len(results)} results from ADS API")
            return results
            
    except Exception as e:
        logger.error(f"Error retrieving results from ADS API: {str(e)}")
        return []


async def get_ads_results(
    query: str, 
    fields: List[str], 
    num_results: int = NUM_RESULTS
) -> List[SearchResult]:
    """
    Get search results from ADS, using either Solr or API based on configuration.
    
    This function provides a unified interface to get ADS results, selecting
    the appropriate method (Solr or API) based on environment configuration.
    
    Args:
        query: Search query string
        fields: List of fields to include in results
        num_results: Maximum number of results to return
    
    Returns:
        List[SearchResult]: List of search results from ADS
    """
    # Determine which method to use based on configuration
    if ADS_QUERY_METHOD == "solr_only":
        return await query_ads_solr(query, fields, num_results)
    elif ADS_QUERY_METHOD == "api_only":
        return await query_ads_api(query, fields, num_results)
    else:  # solr_first (default)
        try:
            # Try Solr first
            results = await query_ads_solr(query, fields, num_results)
            if results:
                return results
            
            # If Solr fails or returns empty results, fall back to API
            logger.info("Falling back to ADS API after Solr returned no results")
            return await query_ads_api(query, fields, num_results)
        except Exception as e:
            logger.error(f"Error with Solr query, falling back to API: {str(e)}")
            return await query_ads_api(query, fields, num_results) 