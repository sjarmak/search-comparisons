"""
ADS (Astrophysics Data System) service module for the search-comparisons application.

This module handles interactions with the ADS API for searching publications
and retrieving bibliographic information.
"""
import os
import logging
import json
from typing import List, Dict, Any, Optional, Union, TypedDict, Literal

import httpx

from ..api.models import SearchResult
from ..utils.http import safe_api_request
from ..utils.cache import get_cache_key, load_from_cache, save_to_cache

# Setup logging
logger = logging.getLogger(__name__)

# API Constants
ADS_API_URL = "https://api.adsabs.harvard.edu/v1/search/query"
NUM_RESULTS = 20
TIMEOUT_SECONDS = 15

# Type definitions
class ADSFieldMapping(TypedDict):
    """Type definition for ADS field mappings."""
    title: str
    authors: str
    abstract: str
    doi: str
    year: str
    citation_count: str
    doctype: str
    property: str

class ADSQueryParams(TypedDict):
    """Type definition for ADS query parameters."""
    q: str
    fl: str
    rows: int
    sort: str

# Field mappings
ADS_FIELD_MAPPING = {
    "title": "title",
    "author": "author",
    "abstract": "abstract",
    "year": "year",
    "citation_count": "citation_count",
    "doctype": "doctype",
    "property": "property",
    "bibcode": "bibcode",
    "doi": "doi",
    "keyword": "keyword",
    "pub": "pub",
    "volume": "volume",
    "page": "page",
    "aff": "aff",
    "inst": "inst",
    "lang": "lang",
    "orcid": "orcid",
    "read_count": "read_count",
    "vizier": "vizier"
}

def get_ads_api_key() -> str:
    """
    Get the ADS API key from environment variables.
    
    Returns:
        str: The API key if found, empty string otherwise
    """
    api_key = os.environ.get("ADS_API_KEY", "")
    
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
    
    Args:
        doi: DOI string to search for
        
    Returns:
        Optional[str]: Bibcode string if found, None otherwise
    """
    if not doi:
        logger.warning("Empty DOI provided to get_bibcode_from_doi")
        return None
    
    # Get API key
    ads_api_key = get_ads_api_key()
    if not ads_api_key:
        logger.error("Cannot query ADS API without an API key")
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            # Set headers with API key
            headers = {
                "Authorization": f"Bearer {ads_api_key}",
                "Content-Type": "application/json",
            }
            
            # Format DOI query
            query = f'doi:"{doi}"'
            
            # Set query parameters
            params: ADSQueryParams = {
                "q": query,
                "fl": "bibcode",
                "rows": 1,
                "sort": "score desc"
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

def _get_default_fields() -> List[str]:
    """
    Get the default fields to retrieve from ADS API.
    
    Returns:
        List[str]: List of default field names
    """
    return [
        "id", "bibcode", "title", "author", "year", "citation_count",
        "abstract", "doctype", "property", "pub", "volume", "page",
        "doi", "keyword"
    ]

def _get_sort_parameter(intent: Optional[str], sort: Optional[str]) -> str:
    """
    Determine the sort parameter based on intent or provided sort.
    
    Args:
        intent: Query intent (e.g., "influential", "recent")
        sort: Explicit sort parameter
        
    Returns:
        str: Sort parameter for ADS API
    """
    if sort:
        return sort
    
    if not intent:
        return "score desc"  # Default sort by relevance score
        
    if "influential" in intent or "highly cited" in intent or "popular" in intent:
        logger.info(f"Sorting by citation count for intent: {intent}")
        return "citation_count desc"
    elif "recent" in intent:
        logger.info(f"Sorting by date for intent: {intent}")
        return "date desc"
    
    return "score desc"

def _map_fields_to_ads(fields: List[str]) -> List[str]:
    """
    Map requested fields to ADS API fields.
    
    Args:
        fields: List of requested fields
        
    Returns:
        List[str]: List of mapped ADS API fields
    """
    ads_fields = ["bibcode", "id"]  # Always include these
    for field in fields:
        if field in ADS_FIELD_MAPPING:
            ads_field = ADS_FIELD_MAPPING[field]
            if ads_field not in ads_fields:
                ads_fields.append(ads_field)
    return ads_fields

def _create_search_result(doc: Dict[str, Any], rank: int) -> SearchResult:
    """
    Create a SearchResult object from an ADS API document.
    
    Args:
        doc: Document from ADS API
        rank: Rank of the result
        
    Returns:
        SearchResult: Processed search result
    """
    return SearchResult(
        title=doc.get("title", [""])[0] if isinstance(doc.get("title"), list) else doc.get("title", ""),
        author=doc.get("author", []),
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

async def get_ads_results(
    query: str,
    fields: Optional[List[str]] = None,
    num_results: int = NUM_RESULTS,
    use_cache: bool = False,
    intent: Optional[str] = None,
    sort: Optional[str] = None,
    qf: Optional[str] = None,  # Query field weights (e.g., "title^50 author^30")
    field_boosts: Optional[Dict[str, float]] = None  # Field boosts for query transformation
) -> List[SearchResult]:
    """
    Get search results from ADS API.
    
    Args:
        query: Search query string
        fields: List of fields to retrieve
        num_results: Maximum number of results to return
        use_cache: Whether to use caching
        intent: Query intent (e.g., "influential", "recent")
        sort: Sort parameter (e.g., "citation_count desc", "date desc")
        qf: Query field weights (e.g., "title^50 author^30")
        field_boosts: Dictionary mapping field names to boost values for query transformation
        
    Returns:
        List[SearchResult]: List of search results
    """
    try:
        # Log input parameters
        logger.info("=== ADS API Request Parameters ===")
        logger.info(f"Query: {query}")
        logger.info(f"Fields: {fields}")
        logger.info(f"Num results: {num_results}")
        logger.info(f"Intent: {intent}")
        logger.info(f"Sort: {sort}")
        logger.info(f"QF parameter: {qf}")
        logger.info(f"Field boosts: {field_boosts}")
        
        # Set default fields if not provided
        fields = fields or _get_default_fields()
        
        # Get API key
        ads_api_key = get_ads_api_key()
        if not ads_api_key:
            logger.error("ADS API key not configured")
            return []
        
        # Transform query if field boosts are provided
        effective_query = query
        if field_boosts:
            effective_query = transform_query_with_boosts(query, field_boosts)
            logger.info(f"Transformed query with field boosts: {effective_query}")
        
        # Check cache first if enabled
        if use_cache:
            cache_key = get_cache_key("ads_api", effective_query, fields, num_results, qf)
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
            
            # Prepare query parameters
            params: ADSQueryParams = {
                "q": effective_query,
                "fl": ",".join(_map_fields_to_ads(fields)),
                "rows": num_results,
                "sort": _get_sort_parameter(intent, sort)
            }
            
            # Add qf parameter if provided
            if qf:
                try:
                    logger.info(f"Processing qf parameter: {qf}")
                    # Split into field-weight pairs and validate
                    field_weights = []
                    for fw in qf.split():
                        logger.info(f"Processing field weight pair: {fw}")
                        if "^" in fw:
                            field, weight = fw.split("^")
                            # Convert field to lowercase for case-insensitive matching
                            field = field.lower()
                            logger.info(f"Field: {field}, Weight: {weight}")
                            # Check if field exists in mapping
                            if field in ADS_FIELD_MAPPING:
                                # Use the mapped field name
                                mapped_field = ADS_FIELD_MAPPING[field]
                                logger.info(f"Mapped field {field} to {mapped_field}")
                                try:
                                    # Validate weight is a positive number
                                    weight_float = float(weight)
                                    if weight_float > 0:
                                        field_weights.append(f"{mapped_field}^{weight}")
                                        logger.info(f"Added field weight: {mapped_field}^{weight}")
                                    else:
                                        logger.warning(f"Invalid weight value in qf parameter: {weight} for field {field}")
                                except ValueError:
                                    logger.warning(f"Invalid weight format in qf parameter: {weight} for field {field}")
                            else:
                                logger.warning(f"Invalid field name in qf parameter: {field}")
                        else:
                            logger.warning(f"Invalid field weight format in qf parameter: {fw}")
                    
                    if field_weights:
                        params["qf"] = " ".join(field_weights)
                        logger.info(f"Final qf parameter: {params['qf']}")
                    else:
                        logger.warning("No valid field weights found in qf parameter")
                except Exception as e:
                    logger.error(f"Error formatting qf parameter: {str(e)}")
            
            # Log request details
            logger.info("=== ADS API Request Details ===")
            logger.info(f"URL: {ADS_API_URL}")
            logger.info(f"Query: {effective_query}")
            logger.info(f"Parameters: {json.dumps(params, indent=2)}")
            logger.info(f"Field weights (qf): {params.get('qf', 'None')}")
            logger.info(f"Field boosts: {field_boosts}")
            
            # Make request
            response_data = await safe_api_request(
                client, 
                "GET", 
                ADS_API_URL, 
                headers=headers, 
                params=params,
                timeout=TIMEOUT_SECONDS
            )
            
            # Log response data for debugging
            logger.info("=== ADS API Response Details ===")
            logger.info(f"Status: {response_data.get('responseHeader', {}).get('status', 'unknown')}")
            logger.info(f"Response time: {response_data.get('responseHeader', {}).get('QTime', 'unknown')}ms")
            logger.info(f"Response params: {json.dumps(response_data.get('responseHeader', {}).get('params', {}), indent=2)}")
            logger.info(f"Number of results: {response_data.get('response', {}).get('numFound', 'unknown')}")
            
            # Check if we got a response
            docs = response_data.get("response", {}).get("docs", [])
            if not docs:
                logger.warning(f"No results found from ADS API for query: {effective_query}")
                return []
            
            # Process results
            results = [_create_search_result(doc, rank) for rank, doc in enumerate(docs, 1)]
            
            # Save to cache if enabled
            if use_cache and results:
                save_to_cache(cache_key, results)
            
            logger.info(f"Retrieved {len(results)} results from ADS API")
            return results
            
    except Exception as e:
        logger.error(f"Error retrieving results from ADS API: {str(e)}")
        return [] 