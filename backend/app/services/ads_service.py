"""
ADS (Astrophysics Data System) service module for the search-comparisons application.

This module handles interactions with the ADS API, including searching
for publications and retrieving bibliographic information.
"""
import os
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple

import httpx

from ..api.models import SearchResult
from ..utils.http import safe_api_request

# Setup logging
logger = logging.getLogger(__name__)

# API Constants
ADS_API_URL = "https://api.adsabs.harvard.edu/v1/search/query"
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


async def get_ads_results(
    query: str, 
    fields: List[str], 
    num_results: int = NUM_RESULTS
) -> List[SearchResult]:
    """
    Get search results from the ADS API.
    
    Queries the ADS API with the given search terms and returns results
    formatted as SearchResult objects.
    
    Args:
        query: Search query string
        fields: List of fields to include in results
        num_results: Maximum number of results to return (default: NUM_RESULTS)
    
    Returns:
        List[SearchResult]: List of search results from ADS
    """
    # Get API key at runtime
    ads_api_key = get_ads_api_key()
    if not ads_api_key:
        return []
    
    try:
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
                logger.warning(f"No results found from ADS for query: {query}")
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
            
            logger.info(f"Retrieved {len(results)} results from ADS")
            return results
            
    except Exception as e:
        logger.error(f"Error retrieving results from ADS: {str(e)}")
        return [] 