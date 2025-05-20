"""
Service module for applying boost factors to search results.

This module provides functionality to apply various boost factors to search results,
including citation count, publication recency, document type, and refereed status boosts.
The boost factors are combined using a weighted sum approach as specified in the RFC.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from copy import deepcopy
import math
from dateutil.parser import parse

from ..api.models import SearchResult

# Setup logging
logger = logging.getLogger(__name__)

# Default weights for boost combination - these are the original default values
DEFAULT_BOOST_WEIGHTS = {
    'citation': 0.4,
    'recency': 0.3,
    'doctype': 0.2,
    'refereed': 0.1
}

# Default document type ranks (from RFC)
DEFAULT_DOCTYPE_RANKS = {
    'article': 1,      # Journal article
    'book': 2,         # Book
    'inbook': 3,       # Book chapter
    'proceedings': 4,  # Conference proceedings
    'inproceedings': 5,# Conference paper
    'phdthesis': 6,    # PhD thesis
    'mastersthesis': 7,# Masters thesis
    'techreport': 8,   # Technical report
    'preprint': 9,     # Preprint
    'abstract': 10,    # Abstract
    'other': 11        # Other/unknown
}

def calculate_doctype_boost(doctype: str, doctype_ranks: Dict[str, int] = None) -> float:
    """
    Calculate document type boost based on rank.
    
    Args:
        doctype: Document type string
        doctype_ranks: Dictionary mapping doctypes to ranks (lower is better)
        
    Returns:
        float: Boost factor (higher for better ranked doctypes)
    """
    doctype_ranks = doctype_ranks or DEFAULT_DOCTYPE_RANKS
    doctype = doctype.lower() if doctype else 'other'
    
    # Get rank for doctype, default to 'other' if not found
    rank = doctype_ranks.get(doctype, doctype_ranks['other'])
    
    # Calculate boost factor (higher for better ranks)
    # Use inverse of rank to get higher boost for better ranks
    return 1.0 / rank

def calculate_recency_boost(pubdate: str, boost_factor: float = 1.0) -> float:
    """
    Calculate recency boost using exponential decay.
    
    Args:
        pubdate: Publication date string (YYYY-MM-DD)
        boost_factor: Multiplier to control decay rate
        
    Returns:
        float: Boost factor based on recency
    """
    try:
        # Parse publication date
        pub_date = parse(pubdate)
        now = datetime.now()
        
        # Calculate age in months
        age_months = ((now.year - pub_date.year) * 12 + 
                     (now.month - pub_date.month))
        
        # Apply exponential decay: exp(-boost_factor * age_months/12)
        # This gives higher boost for recent papers and decays exponentially
        return math.exp(-boost_factor * age_months / 12)
        
    except (ValueError, TypeError):
        logger.warning(f"Invalid publication date: {pubdate}")
        return 0.0

def calculate_citation_boost(
    citation_count: int,
    collection: str,
    pub_year: int,
    citation_distributions: Dict[str, Dict[int, Dict[str, float]]]
) -> float:
    """
    Calculate citation boost based on citation count.
    
    Args:
        citation_count: Number of citations
        collection: Collection name (e.g. 'astronomy', 'physics')
        pub_year: Publication year
        citation_distributions: Dictionary of citation distributions by collection and year
        
    Returns:
        float: Boost factor based on citation count
    """
    try:
        # Get distribution for collection and year
        dist = citation_distributions.get(collection, {}).get(pub_year, {})
        if not dist:
            logger.warning(f"No citation distribution for {collection} {pub_year}")
            return 0.0
            
        # Get median citations
        median = dist.get('median', 0)
        
        if median == 0:
            return 0.0
            
        # Calculate boost relative to median using log scale
        # This gives diminishing returns for very high citation counts
        return math.log1p(citation_count / median)
            
    except Exception as e:
        logger.error(f"Error calculating citation boost: {str(e)}")
        return 0.0

def calculate_refereed_boost(is_refereed: bool) -> float:
    """
    Calculate boost for refereed papers.
    
    Args:
        is_refereed: Whether the paper is refereed
        
    Returns:
        float: 1.0 for refereed papers, 0.0 for non-refereed
    """
    return 1.0 if is_refereed else 0.0

def combine_boost_factors(
    boosts: Dict[str, float],
    weights: Dict[str, float] = None
) -> float:
    """
    Combine boost factors using weighted sum.
    
    Args:
        boosts: Dictionary of individual boost factors
        weights: Dictionary of weights for each boost factor. If not provided, uses DEFAULT_BOOST_WEIGHTS.
                Weights are used exactly as provided without modification.
        
    Returns:
        float: Combined boost factor
    """
    # Use provided weights or defaults, without any modification
    weights = weights or DEFAULT_BOOST_WEIGHTS
    
    # Calculate weighted sum of boosts using weights exactly as provided
    weighted_sum = sum(
        boosts.get(boost_type, 0.0) * weight
        for boost_type, weight in weights.items()
    )
    
    return weighted_sum

async def apply_all_boosts(
    results: List[SearchResult],
    boost_config: Dict[str, Any],
    citation_distributions: Dict[str, Dict[int, Dict[str, float]]] = None
) -> List[SearchResult]:
    """
    Apply all configured boost factors to search results.
    
    Args:
        results: List of search results to boost
        boost_config: Dictionary containing boost configuration. Weights are used exactly as provided.
        citation_distributions: Dictionary of citation distributions by collection and year
        
    Returns:
        List[SearchResult]: List of boosted search results
    """
    if not results:
        return []
        
    try:
        # Create a deep copy of results to avoid modifying originals
        boosted_results = [deepcopy(result) for result in results]
        
        # Get boost weights from config or use defaults, without modification
        weights = boost_config.get('boost_weights', DEFAULT_BOOST_WEIGHTS)

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
                'refereed': 0.0,
                'field': 0.0
            }
            
            # Store original score and rank
            result.original_score = result._score
            result.original_rank = i + 1
            
            # Calculate individual boost factors
            boosts = {}
            
            # Citation boost
            if boost_config.get('citation_boost', 0.0) > 0:
                base_boost = calculate_citation_boost(
                    result.citation_count or 0,
                    result.collection or 'general',
                    result.year,
                    citation_distributions or {}
                )
                boosts['citation'] = base_boost * boost_config['citation_boost']
                result.boost_factors['citation'] = boosts['citation']
            
            # Recency boost
            if boost_config.get('recency_boost', 0.0) > 0 and result.pubdate:
                base_boost = calculate_recency_boost(
                    result.pubdate,
                    boost_config.get('recency_multiplier', 1.0)
                )
                boosts['recency'] = base_boost * boost_config['recency_boost']
                result.boost_factors['recency'] = boosts['recency']
            
            # Document type boost
            if boost_config.get('doctype_boosts'):
                base_boost = calculate_doctype_boost(
                    result.doctype,
                    boost_config.get('doctype_boosts', {})
                )
                # Apply doctype boost directly without additional multiplier
                boosts['doctype'] = base_boost
                result.boost_factors['doctype'] = boosts['doctype']
            
            # Field boost
            if boost_config.get('field_boosts'):
                field_boost = 0.0
                for field, weight in boost_config['field_boosts'].items():
                    if weight > 0:
                        # Get the field value from the result
                        field_value = getattr(result, field, None)
                        if field_value:
                            # For numeric fields, use the value directly
                            if isinstance(field_value, (int, float)):
                                field_boost += weight * field_value
                            # For string fields, use length as a proxy for relevance
                            elif isinstance(field_value, str):
                                field_boost += weight * len(field_value)
                            # For list fields, use length as a proxy for relevance
                            elif isinstance(field_value, list):
                                field_boost += weight * len(field_value)
                boosts['field'] = field_boost
                result.boost_factors['field'] = boosts['field']
            
            # Refereed boost
            if boost_config.get('refereed_boost', 0.0) > 0:
                boosts['refereed'] = calculate_refereed_boost(
                    result.is_refereed or False
                ) * boost_config['refereed_boost']
                result.boost_factors['refereed'] = boosts['refereed']
            
            # Combine boost factors
            final_boost = combine_boost_factors(boosts, weights)
            
            # Apply final boost to score with more impact
            # Use exponential scaling to make boosts more impactful
            result._score *= math.exp(final_boost)
            result.boosted_score = result._score
        
        # Sort by boosted score and update ranks
        boosted_results.sort(key=lambda x: x._score, reverse=True)
        for i, result in enumerate(boosted_results):
            result.rank = i + 1
            result.rank_change = result.original_rank - result.rank
        
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