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


async def apply_all_boosts(results: List[SearchResult], boost_config: Dict[str, Any]) -> List[SearchResult]:
    """
    Apply all configured boost factors to search results.
    
    Args:
        results: List of search results to boost
        boost_config: Dictionary containing boost configuration
        
    Returns:
        List[SearchResult]: List of boosted search results
    """
    if not results:
        return []
        
    try:
        # Create a deep copy of results to avoid modifying originals
        boosted_results = [deepcopy(result) for result in results]
        
        # Initialize scores and source_id for each result
        for i, result in enumerate(boosted_results):
            # Initialize _score based on rank (higher rank = higher score)
            result._score = 1.0 / (i + 1)  # Inverse of rank for initial score
            result.source_id = 'boosted'  # Mark as boosted result
            
            # Initialize boost factors
            result.boost_factors = {
                'citation': 0.0,
                'recency': 0.0,
                'doctype': 0.0,
                'field': 0.0
            }
            
            # Store original score and rank
            result.original_score = result._score
            result.original_rank = i + 1
        
        # Apply citation boost if configured
        if boost_config.get('citation_boost', 0.0) > 0:
            min_citations = boost_config.get('min_citations', 1)
            for result in boosted_results:
                if result.citation_count and result.citation_count >= min_citations:
                    boost_factor = min(result.citation_count / 100, 1.0) * boost_config['citation_boost']
                    result._score *= (1.0 + boost_factor)
                    result.boost_factors['citation'] = boost_factor
        
        # Apply recency boost if configured
        if boost_config.get('recency_boost', 0.0) > 0:
            reference_year = boost_config.get('reference_year', datetime.now().year)
            for result in boosted_results:
                if result.year:
                    years_diff = reference_year - result.year
                    if years_diff >= 0:
                        boost_factor = (1.0 / (years_diff + 1)) * boost_config['recency_boost']
                        result._score *= (1.0 + boost_factor)
                        result.boost_factors['recency'] = boost_factor
        
        # Apply document type boost if configured
        if boost_config.get('doctype_boosts'):
            for result in boosted_results:
                if result.doctype in boost_config['doctype_boosts']:
                    boost_factor = boost_config['doctype_boosts'][result.doctype]
                    if boost_factor > 0:
                        result._score *= (1.0 + boost_factor)
                        result.boost_factors['doctype'] = boost_factor
        
        # Apply field boosts if configured
        if boost_config.get('field_boosts'):
            for result in boosted_results:
                field_boost_sum = 0.0
                for field, boost in boost_config['field_boosts'].items():
                    if boost > 0:
                        field_boost_sum += boost
                if field_boost_sum > 0:
                    result._score *= (1.0 + field_boost_sum)
                    result.boost_factors['field'] = field_boost_sum
        
        # Sort by boosted score and update ranks
        boosted_results.sort(key=lambda x: x._score, reverse=True)
        for i, result in enumerate(boosted_results):
            result.rank = i + 1
            result.rank_change = result.original_rank - result.rank
            result.boosted_score = result._score
        
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


def apply_field_boosts(
    results: List[SearchResult],
    field_boosts: Dict[str, float]
) -> List[SearchResult]:
    """
    Apply field-specific boosts to search results.
    
    Args:
        results: List of search results
        field_boosts: Dictionary mapping field names to boost factors
        
    Returns:
        List[SearchResult]: Results with field boosts applied
    """
    for result in results:
        for field, boost in field_boosts.items():
            if boost > 0:
                # Get the field value
                field_value = getattr(result, field, None)
                if field_value:
                    # Make sure _score exists
                    if not hasattr(result, '_score') or result._score is None:
                        result._score = 1.0
                    
                    # Apply boost based on field value
                    if isinstance(field_value, str):
                        # For text fields, boost based on length
                        result._score *= (1 + (boost * len(field_value) / 100))
                    elif isinstance(field_value, (int, float)):
                        # For numeric fields, apply direct boost
                        result._score *= (1 + boost)
                    elif isinstance(field_value, list):
                        # For list fields (like authors), boost based on length
                        result._score *= (1 + (boost * len(field_value) / 10))
    
    return results 