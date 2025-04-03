"""
Service module for applying boost factors to search results.

This module provides functionality to apply various boost factors to search results,
including citation count, publication recency, and document type boosts.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from copy import deepcopy
import math

from ..api.models import SearchResult

# Setup logging
logger = logging.getLogger(__name__)


async def apply_all_boosts(
    results: List[SearchResult],
    boost_config: Dict[str, Any]
) -> List[SearchResult]:
    """
    Apply all configured boost factors to search results.
    
    Args:
        results: List of search results to boost
        boost_config: Dictionary containing boost configuration:
            citation_boost: Factor to boost citation counts
            min_citations: Minimum number of citations to apply boost (optional)
            recency_boost: Factor to boost recent publications
            reference_year: Reference year for calculating recency (optional)
            doctype_boosts: Dictionary mapping document types to boost factors
        
    Returns:
        List[SearchResult]: Boosted search results
    """
    if not results:
        return []
    
    # Create a deep copy to avoid modifying originals
    boosted_results = deepcopy(results)
    
    try:
        # Apply citation boost
        if boost_config.get("citation_boost", 0.0) > 0:
            min_citations = boost_config.get("min_citations", 0)
            boosted_results = apply_citation_boost(
                boosted_results,
                boost_config["citation_boost"],
                min_citations=min_citations
            )
        
        # Apply recency boost
        if boost_config.get("recency_boost", 0.0) > 0:
            reference_year = boost_config.get("reference_year")
            boosted_results = apply_recency_boost(
                boosted_results,
                boost_config["recency_boost"],
                reference_year=reference_year
            )
        
        # Apply document type boosts
        doctype_boosts = boost_config.get("doctype_boosts", {})
        if doctype_boosts:
            boosted_results = apply_doctype_boosts(
                boosted_results,
                doctype_boosts
            )
        
        # Sort results by boosted score
        for i, result in enumerate(boosted_results):
            # Make sure each result has a _score attribute
            if not hasattr(result, '_score') or result._score is None:
                # If no score exists, use 1.0 as default and adjust based on rank
                result._score = 1.0 - (i / len(boosted_results))
                
        # Sort results by boosted score
        boosted_results.sort(key=lambda x: x._score, reverse=True)
        
        return boosted_results
        
    except Exception as e:
        logger.error(f"Error applying boosts: {str(e)}", exc_info=True)
        return results


def apply_citation_boost(
    results: List[SearchResult],
    boost_factor: float,
    min_citations: int = 0
) -> List[SearchResult]:
    """
    Apply citation count boost to search results.
    
    Args:
        results: List of search results
        boost_factor: Factor to boost citation counts by
        min_citations: Minimum citations to apply boost
        
    Returns:
        List[SearchResult]: Results with citation boost applied
    """
    for result in results:
        citation_count = getattr(result, 'citation_count', 0) or 0
        if citation_count >= min_citations:
            # Make sure _score exists
            if not hasattr(result, '_score') or result._score is None:
                result._score = 1.0
                
            # Apply logarithmic boost to avoid extreme values
            boost = 1 + (boost_factor * (1 + math.log2(1 + citation_count)))
            result._score *= boost
    
    return results


def apply_recency_boost(
    results: List[SearchResult],
    boost_factor: float,
    reference_year: Optional[int] = None
) -> List[SearchResult]:
    """
    Apply publication recency boost to search results.
    
    Args:
        results: List of search results
        boost_factor: Factor to boost recent publications by
        reference_year: Year to use as reference point (defaults to current year)
        
    Returns:
        List[SearchResult]: Results with recency boost applied
    """
    # Use current year if reference_year is not provided
    current_year = reference_year or datetime.now().year
    
    for result in results:
        year = getattr(result, 'year', None)
        if year and isinstance(year, (int, str)):
            try:
                year = int(year)
                if 1900 <= year <= current_year:
                    # Make sure _score exists
                    if not hasattr(result, '_score') or result._score is None:
                        result._score = 1.0
                        
                    # Calculate years since publication
                    years_old = current_year - year
                    # Apply exponential decay boost
                    boost = 1 + (boost_factor * math.exp(-years_old / 10))
                    result._score *= boost
            except (ValueError, TypeError):
                continue
    
    return results


def apply_doctype_boosts(
    results: List[SearchResult],
    doctype_boosts: Dict[str, float]
) -> List[SearchResult]:
    """
    Apply document type boosts to search results.
    
    Args:
        results: List of search results
        doctype_boosts: Dictionary mapping document types to boost factors
        
    Returns:
        List[SearchResult]: Results with document type boosts applied
    """
    for result in results:
        doctype = getattr(result, 'doctype', '').lower()
        if doctype in doctype_boosts:
            # Make sure _score exists
            if not hasattr(result, '_score') or result._score is None:
                result._score = 1.0
                
            boost = 1 + doctype_boosts[doctype]
            result._score *= boost
    
    return results 