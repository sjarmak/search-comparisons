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
TIMEOUT_SECONDS = int(os.getenv('SCHOLAR_TIMEOUT_SECONDS', '30'))  # Increased default timeout
MAX_RETRIES = int(os.getenv('SCHOLAR_MAX_RETRIES', '3'))
RETRY_DELAY = int(os.getenv('SCHOLAR_RETRY_DELAY', '5'))
BLOCK_DELAY = int(os.getenv('SCHOLAR_BLOCK_DELAY', '300'))  # 5 minutes delay after being blocked
USER_AGENT = os.getenv('SCHOLAR_USER_AGENT', "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# Track block status
last_block_time = 0
is_blocked = False

def is_currently_blocked() -> bool:
    """
    Check if we're currently blocked by Google Scholar.
    
    Returns:
        bool: True if we're currently blocked, False otherwise
    """
    global is_blocked, last_block_time
    if is_blocked:
        # Check if block period has passed
        if time.time() - last_block_time > BLOCK_DELAY:
            is_blocked = False
            logger.info("Block period has passed, resuming normal operation")
        return is_blocked
    return False

def mark_as_blocked() -> None:
    """
    Mark the service as blocked by Google Scholar.
    """
    global is_blocked, last_block_time
    is_blocked = True
    last_block_time = time.time()
    logger.warning(f"Marked as blocked by Google Scholar. Will retry after {BLOCK_DELAY} seconds")

async def get_scholar_direct_html(
    query: str, 
    num_results: int = NUM_RESULTS
) -> Optional[str]:
    """
    Get Google Scholar search results HTML directly using httpx.
    
    Makes a direct HTTP request to Google Scholar with the search query
    and returns the HTML response for parsing. Includes retry logic and
    block detection.
    
    Args:
        query: Search query string
        num_results: Maximum number of results to retrieve
    
    Returns:
        Optional[str]: HTML content if successful, None otherwise
    """
    if is_currently_blocked():
        logger.warning("Skipping Google Scholar request due to active block")
        return None

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
        "DNT": "1",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                # Add random delay to avoid looking like a bot
                await asyncio.sleep(random.uniform(2.0, 5.0))
                
                # Make request with timeout
                logger.info(f"Making direct HTML request to Google Scholar for: {query} (attempt {attempt + 1}/{MAX_RETRIES})")
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
                elif response.status_code == 429:  # Too Many Requests
                    logger.warning("Rate limited by Google Scholar, waiting before retry...")
                    mark_as_blocked()
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
                    continue
                elif response.status_code == 403:  # Forbidden
                    logger.warning("Access denied by Google Scholar (403)")
                    mark_as_blocked()
                    return None
                else:
                    logger.warning(f"Google Scholar HTML request failed with status code: {response.status_code}")
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    return None
                    
        except httpx.TimeoutException:
            logger.warning(f"Timeout while requesting Google Scholar (attempt {attempt + 1}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
                continue
            return None
        except Exception as e:
            logger.error(f"Error retrieving Google Scholar HTML: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
                continue
            return None
    
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
    with fallback to the Scholarly library if needed. Includes improved error
    handling and block detection.
    
    Args:
        query: Search query string
        fields: List of fields to include in results
        num_results: Maximum number of results to return
    
    Returns:
        List[SearchResult]: List of search results from Google Scholar
    """
    # Check if we're blocked
    if is_currently_blocked():
        logger.warning("Skipping Google Scholar search due to active block")
        return []
    
    # Check cache first
    cache_key = get_cache_key("scholar", query, fields, num_results)
    cached_results = load_from_cache(cache_key)
    
    if cached_results is not None:
        logger.info(f"Retrieved {len(cached_results)} Google Scholar results from cache")
        return cached_results
    
    # Log the environment for debugging
    logger.info(f"Google Scholar search environment: TIMEOUT={TIMEOUT_SECONDS}s, MAX_RETRIES={MAX_RETRIES}, "
                f"SCHOLARLY_AVAILABLE={SCHOLARLY_AVAILABLE}, BLOCKED={is_blocked}")
    
    # First try with Scholarly if available
    if SCHOLARLY_AVAILABLE:
        try:
            results = await get_scholar_results_scholarly(query, fields, num_results)
            if results:
                # Cache successful results
                save_to_cache(cache_key, results)
                return results
        except Exception as e:
            logger.error(f"Error with Scholarly method: {str(e)}")
    
    # Fall back to direct HTML method
    logger.info("Falling back to direct HTML method for Google Scholar")
    html_content = await get_scholar_direct_html(query, num_results)
    if html_content:
        results = await parse_scholar_html(html_content)
        if results:
            # Cache successful results
            save_to_cache(cache_key, results)
        return results
    
    # If both methods fail, try the fallback method
    logger.warning("Both primary methods failed, attempting fallback method")
    fallback_results = await get_scholar_results_fallback(query, num_results)
    if fallback_results:
        # Cache fallback results with a different key
        fallback_cache_key = get_cache_key("scholar_fallback", query, fields, num_results)
        save_to_cache(fallback_cache_key, fallback_results)
    
    return fallback_results


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