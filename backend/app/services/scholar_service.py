"""
Google Scholar service module for the search-comparisons application.

This module handles interactions with Google Scholar, including direct search
and fallback mechanisms using Scholarly or direct HTML scraping when needed.
"""
import os
import re
import time
import logging
import asyncio
import random
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta

import httpx
from bs4 import BeautifulSoup

# Only import scholarly if it's available
try:
    from scholarly import scholarly, ProxyGenerator
    SCHOLARLY_AVAILABLE = True
except ImportError:
    SCHOLARLY_AVAILABLE = False

from ..api.models import SearchResult
from ..utils.http import safe_api_request, timeout
from ..utils.cache import get_cache_key, save_to_cache, load_from_cache

# Setup logging
logger = logging.getLogger(__name__)

# Constants
NUM_RESULTS = 20
TIMEOUT_SECONDS = 20
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Proxy management
last_proxy_refresh_time = 0
PROXY_REFRESH_INTERVAL = 3600  # 1 hour in seconds
proxy_generator = None


def setup_scholarly_proxy() -> bool:
    """
    Set up a proxy for Scholarly to avoid Google Scholar blocking.
    
    Configures Scholarly to use Tor or free proxies to make requests to
    Google Scholar, reducing the likelihood of being blocked.
    
    Returns:
        bool: True if proxy setup was successful, False otherwise
    """
    global proxy_generator
    
    if not SCHOLARLY_AVAILABLE:
        logger.warning("Scholarly package not available, cannot set up proxy")
        return False
    
    logger.info("Setting up Scholarly proxy...")
    
    try:
        proxy_generator = ProxyGenerator()
        
        # Try to use Tor if available
        tor_success = proxy_generator.Tor_External(tor_sock_port=9050, tor_control_port=9051)
        if tor_success:
            logger.info("Successfully connected to Tor for Scholarly proxy")
            scholarly.use_proxy(proxy_generator)
            return True
            
        # Fall back to free proxies if Tor is not available
        proxy_success = proxy_generator.FreeProxies()
        if proxy_success:
            logger.info("Successfully set up free proxies for Scholarly")
            scholarly.use_proxy(proxy_generator)
            return True
            
        logger.warning("Failed to set up any proxy for Scholarly")
        return False
        
    except Exception as e:
        logger.error(f"Error setting up Scholarly proxy: {str(e)}")
        return False


async def refresh_scholarly_proxy_if_needed() -> bool:
    """
    Refresh the Scholarly proxy if it hasn't been refreshed recently.
    
    Checks if the proxy refresh interval has passed since the last refresh,
    and refreshes the proxy if needed.
    
    Returns:
        bool: True if proxy was refreshed or didn't need refreshing, False if refresh failed
    """
    global last_proxy_refresh_time
    
    if not SCHOLARLY_AVAILABLE:
        logger.warning("Scholarly package not available, cannot refresh proxy")
        return False
    
    current_time = time.time()
    
    # Check if we need to refresh the proxy
    if current_time - last_proxy_refresh_time < PROXY_REFRESH_INTERVAL:
        return True  # No need to refresh yet
    
    logger.info("Refreshing Scholarly proxy...")
    
    # Update the last refresh time regardless of success to avoid hammering
    last_proxy_refresh_time = current_time
    
    # Set up a new proxy
    return setup_scholarly_proxy()


async def get_scholar_direct_html(
    query: str, 
    num_results: int = NUM_RESULTS
) -> Optional[str]:
    """
    Get Google Scholar search results HTML directly using httpx.
    
    Makes a direct HTTP request to Google Scholar with the search query
    and returns the HTML response for parsing.
    
    Args:
        query: Search query string
        num_results: Maximum number of results to retrieve
    
    Returns:
        Optional[str]: HTML content if successful, None otherwise
    """
    url = "https://scholar.google.com/scholar"
    
    params = {
        "q": query,
        "hl": "en",
        "num": num_results,
        "as_sdt": "0,5"  # Search only articles and patents
    }
    
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://scholar.google.com/",
        "DNT": "1"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Add random delay to avoid looking like a bot
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
            # Make request with timeout
            logger.info(f"Making direct HTML request to Google Scholar for: {query}")
            response = await client.get(
                url, 
                params=params, 
                headers=headers, 
                timeout=TIMEOUT_SECONDS,
                follow_redirects=True
            )
            
            # Check for success
            if response.status_code == 200:
                logger.info("Successfully retrieved Google Scholar HTML")
                return response.text
            else:
                logger.warning(f"Google Scholar HTML request failed with status code: {response.status_code}")
                return None
                
    except Exception as e:
        logger.error(f"Error retrieving Google Scholar HTML: {str(e)}")
        return None


async def parse_scholar_html(html_content: str) -> List[SearchResult]:
    """
    Parse Google Scholar HTML content to extract search results.
    
    Parses the HTML response from Google Scholar to extract publication
    information and returns a list of SearchResult objects.
    
    Args:
        html_content: HTML content from Google Scholar
    
    Returns:
        List[SearchResult]: List of search results parsed from the HTML
    """
    if not html_content:
        return []
    
    results: List[SearchResult] = []
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all result divs
        result_divs = soup.select('div.gs_r.gs_or.gs_scl')
        
        for rank, div in enumerate(result_divs, 1):
            try:
                # Extract title and URL
                title_elem = div.select_one('h3.gs_rt a')
                title = title_elem.text.strip() if title_elem else "Unknown Title"
                url = title_elem['href'] if title_elem and 'href' in title_elem.attrs else None
                
                # Extract authors, venue, year
                byline = div.select_one('.gs_a')
                authors: List[str] = []
                year: Optional[int] = None
                
                if byline:
                    byline_text = byline.text.strip()
                    
                    # Extract authors (before the first dash)
                    if ' - ' in byline_text:
                        author_text = byline_text.split(' - ')[0]
                        authors = [a.strip() for a in author_text.split(',')]
                    
                    # Extract year
                    year_match = re.search(r'\b(19|20)\d{2}\b', byline_text)
                    if year_match:
                        try:
                            year = int(year_match.group(0))
                        except ValueError:
                            year = None
                
                # Extract abstract/snippet
                snippet_elem = div.select_one('.gs_rs')
                abstract = snippet_elem.text.strip() if snippet_elem else None
                
                # Extract citation count if available
                citation_count: Optional[int] = None
                cite_elem = div.select_one('a.gs_or_cit')
                if cite_elem:
                    cite_text = cite_elem.text.strip()
                    cite_match = re.search(r'Cited by (\d+)', cite_text)
                    if cite_match:
                        try:
                            citation_count = int(cite_match.group(1))
                        except ValueError:
                            citation_count = None
                
                # Create result object
                result = SearchResult(
                    title=title,
                    author=authors if isinstance(authors, list) else [authors],
                    abstract=abstract,
                    year=year,
                    url=url,
                    source="scholar",
                    rank=rank,
                    citation_count=citation_count
                )
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error parsing Google Scholar result div: {str(e)}")
                continue
        
        logger.info(f"Parsed {len(results)} results from Google Scholar HTML")
        return results
        
    except Exception as e:
        logger.error(f"Error parsing Google Scholar HTML: {str(e)}")
        return []


async def get_scholar_results_scholarly(
    query: str, 
    fields: List[str],
    num_results: int = NUM_RESULTS
) -> List[SearchResult]:
    """
    Get search results from Google Scholar using the Scholarly library.
    
    Uses the scholarly package to search Google Scholar and extract structured
    publication data with proper error handling.
    
    Args:
        query: Search query string
        fields: List of fields to include in results
        num_results: Maximum number of results to return
    
    Returns:
        List[SearchResult]: List of search results from Google Scholar
    """
    if not SCHOLARLY_AVAILABLE:
        logger.warning("Scholarly package not available")
        return []
    
    try:
        # Refresh proxy if needed
        await refresh_scholarly_proxy_if_needed()
        
        # Create search query object
        search_query = scholarly.search_pubs(query)
        
        # Collect results
        results: List[SearchResult] = []
        
        with timeout(TIMEOUT_SECONDS, timeout_message="Scholarly search timed out"):
            for rank, pub in enumerate(search_query, 1):
                if rank > num_results:
                    break
                
                # Extract fields from scholarly result
                abstract = pub.get('bib', {}).get('abstract', None)
                title = pub.get('bib', {}).get('title', "Unknown Title")
                authors = pub.get('bib', {}).get('author', [])
                year_str = pub.get('bib', {}).get('pub_year', None)
                year = int(year_str) if year_str and year_str.isdigit() else None
                citation_count = pub.get('num_citations', None)
                url = pub.get('pub_url', None)
                
                # Create result object
                result = SearchResult(
                    title=title,
                    author=authors if isinstance(authors, list) else [authors],
                    abstract=abstract,
                    year=year,
                    url=url,
                    source="scholar",
                    rank=rank,
                    citation_count=citation_count
                )
                results.append(result)
        
        logger.info(f"Retrieved {len(results)} results from Google Scholar using Scholarly")
        return results
        
    except TimeoutError:
        logger.error("Timeout while retrieving results from Google Scholar via Scholarly")
        return []
    except Exception as e:
        logger.error(f"Error retrieving results from Google Scholar via Scholarly: {str(e)}")
        return []


async def get_scholar_results(
    query: str, 
    fields: List[str],
    num_results: int = NUM_RESULTS
) -> List[SearchResult]:
    """
    Get search results from Google Scholar.
    
    Attempts to retrieve results from Google Scholar using direct HTML scraping
    with fallback to the Scholarly library if needed.
    
    Args:
        query: Search query string
        fields: List of fields to include in results
        num_results: Maximum number of results to return
    
    Returns:
        List[SearchResult]: List of search results from Google Scholar
    """
    # Check cache first
    cache_key = get_cache_key("scholar", query, fields, num_results)
    cached_results = load_from_cache(cache_key)
    
    if cached_results is not None:
        logger.info(f"Retrieved {len(cached_results)} Google Scholar results from cache")
        return cached_results
    
    # First try with Scholarly if available
    if SCHOLARLY_AVAILABLE:
        try:
            results = await get_scholar_results_scholarly(query, fields, num_results)
            if results:
                return results
        except Exception as e:
            logger.error(f"Error with Scholarly method: {str(e)}")
    
    # Fall back to direct HTML method
    logger.info("Falling back to direct HTML method for Google Scholar")
    html_content = await get_scholar_direct_html(query, num_results)
    if html_content:
        return await parse_scholar_html(html_content)
    
    return []


async def get_scholar_results_fallback(
    query: str, 
    num_results: int = 10
) -> List[SearchResult]:
    """
    Fallback method for getting Google Scholar results when primary method fails.
    
    This is a simplified method that uses direct HTML scraping with minimal
    fields to minimize the chance of being blocked.
    
    Args:
        query: Search query string
        num_results: Maximum number of results to return
    
    Returns:
        List[SearchResult]: List of search results from Google Scholar
    """
    logger.info(f"Using fallback method for Google Scholar: {query}")
    
    # Check cache first with minimal default fields for fallback method
    minimal_fields = ["title", "authors", "year"]
    cache_key = get_cache_key("scholar_fallback", query, minimal_fields, num_results)
    cached_results = load_from_cache(cache_key)
    
    if cached_results is not None:
        logger.info(f"Retrieved {len(cached_results)} Google Scholar fallback results from cache")
        return cached_results
    
    # Simplify the query to improve chances of success
    simple_query = query.split(" ")[:6]  # Take just the first few terms
    simplified_query = " ".join(simple_query)
    
    # Try to get HTML with the simplified query
    html_content = await get_scholar_direct_html(simplified_query, num_results)
    if not html_content:
        return []
    
    # Parse HTML
    results = await parse_scholar_html(html_content)
    
    # Cache the results if successful
    if results:
        logger.info(f"Fallback method successfully retrieved {len(results)} results from Google Scholar")
        save_to_cache(cache_key, results)
    else:
        logger.warning("Fallback method failed to retrieve any results from Google Scholar")
    
    return results 