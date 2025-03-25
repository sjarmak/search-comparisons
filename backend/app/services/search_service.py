"""
Search service module for the search-comparisons application.

This module coordinates search operations across different search engines,
handles fallbacks, and computes similarity metrics between results.
"""
import os
import logging
import asyncio
from typing import Dict, List, Any, Set, Tuple, Optional

from ..api.models import SearchResult
from ..utils.cache import get_cache_key, save_to_cache, load_from_cache
from ..utils.text_processing import preprocess_text
from ..utils.similarity import calculate_jaccard_similarity, calculate_rank_based_overlap, calculate_cosine_similarity

# Import specific search services
from .ads_service import get_ads_results
from .scholar_service import get_scholar_results, get_scholar_results_fallback
from .semantic_scholar_service import get_semantic_scholar_results
from .web_of_science_service import get_web_of_science_results

# Setup logging
logger = logging.getLogger(__name__)

# Service configuration with fallback settings
SERVICE_CONFIG = {
    "ads": {
        "enabled": True,
        "priority": 1,  # Lower number = higher priority
        "timeout": 15,  # seconds
        "min_results": 5,  # Minimum acceptable results
    },
    "scholar": {
        "enabled": True,
        "priority": 2,
        "timeout": 20,
        "min_results": 3,
    },
    "semanticScholar": {
        "enabled": True,
        "priority": 3,
        "timeout": 15,
        "min_results": 5,
    },
    "webOfScience": {
        "enabled": True,
        "priority": 4,
        "timeout": 20,
        "min_results": 3,
    }
}

# Constants
NUM_RESULTS = 20


async def get_results_with_fallback(
    query: str, 
    sources: List[str], 
    fields: List[str], 
    attempts: int = 2
) -> Dict[str, List[SearchResult]]:
    """
    Get search results from multiple sources with fallback mechanisms.
    
    Attempts to retrieve results from each specified source, falling back
    to alternative methods if the primary method fails or returns insufficient
    results. Uses caching to avoid redundant API calls.
    
    Args:
        query: Search query string
        sources: List of search engine sources to query
        fields: List of fields to retrieve
        attempts: Maximum number of retry attempts per source
    
    Returns:
        Dict[str, List[SearchResult]]: Dictionary mapping source names to result lists
    """
    results: Dict[str, List[SearchResult]] = {}
    
    # Check if sources is empty or invalid
    if not sources:
        logger.warning("No sources specified for search")
        return results
    
    # Process each requested source
    for source in sources:
        logger.info(f"Processing source: {source}")
        
        # Skip disabled sources
        if source in SERVICE_CONFIG and not SERVICE_CONFIG[source]["enabled"]:
            logger.info(f"Source {source} is disabled, skipping")
            continue
        
        # Try to get from cache first
        cache_key = get_cache_key(source, query, fields)
        cached_results = load_from_cache(cache_key)
        
        if cached_results:
            logger.info(f"Retrieved {len(cached_results)} results for {source} from cache")
            results[source] = cached_results
            continue
        
        # Not in cache, need to fetch live
        source_results: List[SearchResult] = []
        
        # Track attempts for this source
        attempt_count = 0
        success = False
        
        while attempt_count < attempts and not success:
            attempt_count += 1
            logger.info(f"Attempt {attempt_count} for {source}")
            
            try:
                if source == "ads":
                    source_results = await get_ads_results(query, fields)
                elif source == "scholar":
                    if attempt_count == 1:
                        source_results = await get_scholar_results(query, fields)
                    else:
                        # Fallback method for scholar
                        source_results = await get_scholar_results_fallback(query)
                elif source == "semanticScholar":
                    source_results = await get_semantic_scholar_results(query, fields)
                elif source == "webOfScience":
                    source_results = await get_web_of_science_results(query, fields)
                else:
                    logger.warning(f"Unknown source: {source}")
                    break
                
                # Check if we got enough results
                min_results = SERVICE_CONFIG.get(source, {}).get("min_results", 1)
                if len(source_results) >= min_results:
                    success = True
                    logger.info(f"Successfully retrieved {len(source_results)} results from {source}")
                else:
                    logger.warning(f"Insufficient results from {source}: got {len(source_results)}, need {min_results}")
                    
            except Exception as e:
                logger.error(f"Error getting results from {source} (attempt {attempt_count}): {str(e)}")
                # Wait before retry
                await asyncio.sleep(1.0)
        
        # If we got results, save to cache and add to results dict
        if source_results:
            # Save to cache
            save_to_cache(cache_key, source_results)
            
            # Add to results dictionary
            results[source] = source_results
    
    return results


def compare_results(
    sources_results: Dict[str, List[SearchResult]], 
    metrics: List[str], 
    fields: List[str]
) -> Dict[str, Any]:
    """
    Compare search results from different sources using specified metrics.
    
    Computes similarity scores between results from different sources based
    on various similarity metrics and fields.
    
    Args:
        sources_results: Dictionary mapping source names to result lists
        metrics: List of similarity metrics to compute
        fields: List of fields to use for comparisons
    
    Returns:
        Dict[str, Any]: Dictionary with comparison results
    """
    comparison_results: Dict[str, Any] = {
        "overlap": {},
        "similarity": {},
        "sources": {}
    }
    
    # Process source data
    for source, results in sources_results.items():
        comparison_results["sources"][source] = {
            "count": len(results),
            "results": results
        }
    
    # If we have fewer than 2 sources with results, we can't compare
    active_sources = [s for s, r in sources_results.items() if r]
    if len(active_sources) < 2:
        logger.warning("Not enough sources with results to compare")
        return comparison_results
    
    # Calculate overlap and similarity for each pair of sources
    for i, source1 in enumerate(active_sources):
        for j, source2 in enumerate(active_sources):
            if i >= j:  # Skip self-comparisons and redundant pairs
                continue
            
            # Get results for both sources
            results1 = sources_results[source1]
            results2 = sources_results[source2]
            
            # Skip if either source has no results
            if not results1 or not results2:
                continue
            
            # Create pair key
            pair_key = f"{source1}_vs_{source2}"
            
            # Initialize overlap and similarity results for this pair
            if pair_key not in comparison_results["overlap"]:
                comparison_results["overlap"][pair_key] = {}
            
            if pair_key not in comparison_results["similarity"]:
                comparison_results["similarity"][pair_key] = {}
            
            # Calculate for each metric
            for metric in metrics:
                if metric == "exact_match":
                    # Exact match on specified fields
                    match_sets: Dict[str, Set[str]] = {}
                    
                    for field in fields:
                        # Extract values from results
                        values1 = set(getattr(r, field, "") or "" for r in results1)
                        values1 = {str(v).lower() for v in values1 if v}
                        
                        values2 = set(getattr(r, field, "") or "" for r in results2)
                        values2 = {str(v).lower() for v in values2 if v}
                        
                        # Calculate Jaccard similarity
                        similarity = calculate_jaccard_similarity(values1, values2)
                        
                        # Store result
                        comparison_results["similarity"][pair_key][f"exact_match_{field}"] = similarity
                
                elif metric == "rank_correlation":
                    # Calculate correlation between result rankings
                    # Extract titles from each source
                    titles1 = [r.title.lower() for r in results1 if r.title]
                    titles2 = [r.title.lower() for r in results2 if r.title]
                    
                    # Calculate rank-based overlap
                    rbo_similarity = calculate_rank_based_overlap(titles1, titles2)
                    
                    # Store result
                    comparison_results["similarity"][pair_key]["rank_correlation"] = rbo_similarity
                
                elif metric == "content_similarity":
                    # Calculate similarity based on text content
                    for field in fields:
                        if field in ["title", "abstract"]:
                            # Extract and preprocess text
                            texts1 = [preprocess_text(getattr(r, field, "") or "") for r in results1]
                            texts1 = [t for t in texts1 if t]
                            
                            texts2 = [preprocess_text(getattr(r, field, "") or "") for r in results2]
                            texts2 = [t for t in texts2 if t]
                            
                            # Skip if either list is empty
                            if not texts1 or not texts2:
                                continue
                            
                            # Convert to term frequency dictionaries
                            vec1: Dict[str, int] = {}
                            for text in texts1:
                                for term in text.split():
                                    vec1[term] = vec1.get(term, 0) + 1
                            
                            vec2: Dict[str, int] = {}
                            for text in texts2:
                                for term in text.split():
                                    vec2[term] = vec2.get(term, 0) + 1
                            
                            # Calculate cosine similarity
                            cosine_sim = calculate_cosine_similarity(vec1, vec2)
                            
                            # Store result
                            comparison_results["similarity"][pair_key][f"content_similarity_{field}"] = cosine_sim
    
    return comparison_results


async def get_paper_details(doi: str, sources: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Get detailed paper information by DOI from multiple sources.
    
    Retrieves detailed metadata for a paper identified by its DOI from
    multiple search engines and combines the results.
    
    Args:
        doi: Digital Object Identifier for the paper
        sources: List of sources to query (if None, query all available)
    
    Returns:
        Dict[str, Any]: Combined paper details from all sources
    """
    if not doi:
        logger.warning("Empty DOI provided to get_paper_details")
        return {}
    
    # Default to all sources if not specified
    if sources is None:
        sources = ["ads", "semanticScholar", "webOfScience"]
    
    # Filter to only enabled sources
    enabled_sources = [
        source for source in sources
        if source in SERVICE_CONFIG and SERVICE_CONFIG[source]["enabled"]
    ]
    
    # Initialize results
    results: Dict[str, Any] = {
        "doi": doi,
        "sources": {}
    }
    
    # Gather tasks for fetching from all sources
    tasks = []
    
    for source in enabled_sources:
        if source == "ads":
            from .ads_service import get_bibcode_from_doi
            tasks.append(get_bibcode_from_doi(doi))
        elif source == "semanticScholar":
            from .semantic_scholar_service import get_paper_details_by_doi
            tasks.append(get_paper_details_by_doi(doi))
        elif source == "webOfScience":
            from .web_of_science_service import get_wos_paper_details
            tasks.append(get_wos_paper_details(doi))
    
    # Run all tasks concurrently
    source_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    for source, source_result in zip(enabled_sources, source_results):
        if isinstance(source_result, Exception):
            logger.error(f"Error getting paper details from {source}: {str(source_result)}")
            results["sources"][source] = {"error": str(source_result)}
        elif source_result:
            results["sources"][source] = source_result
    
    return results 