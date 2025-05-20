"""
Caching utilities for the search-comparisons application.

This module provides functions for caching search results to reduce API calls
and improve performance. It handles generating cache keys, saving results to
the cache, and loading results from the cache.
"""
import os
import json
import time
import hashlib
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from ..api.models import SearchResult

# Setup logging
logger = logging.getLogger(__name__)

# Cache configuration
CACHE_DIR = os.environ.get('CACHE_DIR', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'cache'))
CACHE_EXPIRY = int(os.environ.get('CACHE_EXPIRY', 86400))  # Default: 1 day in seconds


def get_cache_key(
    source: str,
    query: str,
    fields: List[str],
    num_results: Optional[int] = None,
    qf: Optional[str] = None,
    field_boosts: Optional[Dict[str, float]] = None
) -> str:
    """
    Generate a cache key for storing search results.
    
    Creates a unique key based on the source, query, requested fields, number of results,
    query field weights (qf), and field boosts if provided. This allows for caching based
    on the specific search parameters.
    
    Args:
        source: The search engine source (e.g., 'ads', 'scholar')
        query: The search query string
        fields: List of requested fields
        num_results: Maximum number of results to return (optional)
        qf: Query field weights (optional)
        field_boosts: Dictionary mapping field names to boost values (optional)
    
    Returns:
        str: A unique cache key as a hex string
    """
    # Handle the case when query is a list by converting it to a string
    if isinstance(query, list):
        query = " ".join(str(item) for item in query)
    
    # Create a string to hash, include num_results and qf if provided
    results_str = f":{num_results}" if num_results is not None else ""
    qf_str = f":{qf}" if qf is not None else ""
    
    # Add field_boosts to the hash input if provided
    field_boosts_str = ""
    if field_boosts:
        # Sort the field boosts by field name for consistent hashing
        sorted_boosts = sorted(field_boosts.items())
        field_boosts_str = ":" + ":".join(f"{field}^{weight}" for field, weight in sorted_boosts)
    
    hash_input = f"{source}:{query}:{':'.join(sorted(fields))}{results_str}{qf_str}{field_boosts_str}"
    
    # Create SHA-256 hash
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()


def save_to_cache(key: str, data: List[SearchResult], expiry: int = CACHE_EXPIRY) -> bool:
    """
    Save search results to the cache.
    
    Writes the search results to a JSON file in the cache directory with the
    specified expiration time.
    
    Args:
        key: The cache key (from get_cache_key)
        data: List of SearchResult objects to cache
        expiry: Cache expiry time in seconds (default: CACHE_EXPIRY)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure cache directory exists
        os.makedirs(CACHE_DIR, exist_ok=True)
        
        # Prepare cache path
        cache_path = Path(CACHE_DIR) / f"{key}.json"
        
        # Convert SearchResult objects to dictionaries
        serializable_data = [result.dict() for result in data]
        
        # Prepare cache content with metadata
        cache_content = {
            "timestamp": time.time(),
            "expiry": expiry,
            "results": serializable_data
        }
        
        # Write to cache file
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_content, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"Saved {len(data)} results to cache with key {key}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving to cache: {str(e)}")
        return False


def load_from_cache(key: str) -> Optional[List[SearchResult]]:
    """
    Load search results from the cache if available and not expired.
    
    Checks if a cache file exists for the given key and whether it has expired.
    If valid, loads and returns the cached results.
    
    Args:
        key: The cache key (from get_cache_key)
    
    Returns:
        Optional[List[SearchResult]]: List of SearchResult objects if cache hit,
                                     None if cache miss or expired
    """
    try:
        # Prepare cache path
        cache_path = Path(CACHE_DIR) / f"{key}.json"
        
        # Check if cache file exists
        if not cache_path.exists():
            logger.debug(f"Cache miss: No cache file found for key {key}")
            return None
        
        # Read cache file
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_content = json.load(f)
        
        # Check if cache has expired
        timestamp = cache_content.get("timestamp", 0)
        expiry = cache_content.get("expiry", CACHE_EXPIRY)
        
        if time.time() - timestamp > expiry:
            logger.debug(f"Cache expired for key {key}")
            return None
        
        # Convert dictionaries back to SearchResult objects
        results = [SearchResult(**item) for item in cache_content.get("results", [])]
        
        logger.debug(f"Cache hit: Loaded {len(results)} results for key {key}")
        return results
        
    except Exception as e:
        logger.error(f"Error loading from cache: {str(e)}")
        return None 