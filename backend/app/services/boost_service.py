"""
Service module for applying boost factors to search results.

This module provides functionality to apply various boost factors to search results,
including citation count, publication recency, document type, and refereed status boosts.
The boost factors are combined using a weighted sum approach.
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

# Default weights for boost combination
DEFAULT_BOOST_WEIGHTS = {
    'citation': 0.4,
    'recency': 0.3,
    'doctype': 0.2,
    'refereed': 0.1
}

# Document type ranks based on the provided table
DEFAULT_DOCTYPE_RANKS = {
    'article': 1,      # Journal article
    'eprint': 1,       # Article preprinted in arXiv
    'inproceedings': 2,# Article appearing in conference proceedings
    'inbook': 1,       # Article appearing in a book
    'abstract': 5,     # Meeting abstract
    'book': 1,         # Book (monograph)
    'bookreview': 4,   # Published book review
    'catalog': 2,      # Data catalog
    'circular': 3,     # Printed or electronic circular
    'erratum': 6,      # Erratum to a journal article
    'mastersthesis': 3,# Masters thesis
    'newsletter': 5,   # Printed or electronic newsletter
    'obituary': 6,     # Obituary
    'phdthesis': 3,    # PhD thesis
    'pressrelease': 7, # Press release
    'proceedings': 3,  # Conference proceedings book
    'proposal': 4,     # Observing or funding proposal
    'software': 2,     # Software package
    'talk': 4,         # Research talk
    'techreport': 3,   # Technical report
    'misc': 8,         # Anything not in the above list
    'other': 8         # Default for unknown types
}

def calculate_doctype_boost(doctype: str, doctype_ranks: Dict[str, int] = None) -> float:
    """
    Calculate document type boost based on rank using even distribution.
    
    The boost factor is calculated as: 1 - (rank_index / (num_unique_ranks - 1))
    where rank_index is the position of the rank in the sorted list of unique ranks.
    
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
    
    # Get unique ranks and sort them
    unique_ranks = sorted(set(doctype_ranks.values()))
    
    # Calculate boost factor using even distribution
    rank_index = unique_ranks.index(rank)
    num_unique_ranks = len(unique_ranks)
    
    # Avoid division by zero if there's only one rank
    if num_unique_ranks <= 1:
        return 1.0
        
    return 1.0 - (rank_index / (num_unique_ranks - 1))

def calculate_recency_boost(pubdate: str, multiplier: float = 1.0) -> float:
    """
    Calculate recency boost using reciprocal function.
    
    The boost factor is calculated as: 1 / (1 + multiplier * age_months)
    where age_months is the number of months since publication.
    
    Args:
        pubdate: Publication date string (YYYY-MM-DD)
        multiplier: Tuning parameter that controls decay rate
        
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
        
        # Apply reciprocal function
        return 1.0 / (1.0 + multiplier * age_months)
        
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
    weights: Dict[str, float] = None,
    combination_method: str = 'weighted_sum'
) -> float:
    """
    Combine boost factors using the specified combination method.
    
    Args:
        boosts: Dictionary of individual boost factors
        weights: Dictionary of weights for each boost factor. Only used for weighted methods.
        combination_method: Method to use for combining boosts:
            - 'simple_product': Multiply all boosts together
            - 'simple_sum': Add all boosts together
            - 'weighted_geometric_mean': Multiply boosts with weights
            - 'weighted_sum': Add boosts with weights (default)
        
    Returns:
        float: Combined boost factor
    """
    if not boosts:
        return 0.0
        
    # Filter out any None or negative boosts
    valid_boosts = {k: v for k, v in boosts.items() if v is not None and v >= 0}
    
    if not valid_boosts:
        return 0.0
        
    if combination_method == 'simple_product':
        # Multiply all boosts together
        return math.prod(valid_boosts.values())
        
    elif combination_method == 'simple_sum':
        # Add all boosts together
        return sum(valid_boosts.values())
        
    elif combination_method == 'weighted_geometric_mean':
        # Use provided weights or defaults
        weights = weights or DEFAULT_BOOST_WEIGHTS
        
        # Calculate weighted geometric mean
        # For each boost: boost^weight, then multiply all together
        weighted_products = [
            math.pow(valid_boosts.get(boost_type, 0.0), weight)
            for boost_type, weight in weights.items()
            if valid_boosts.get(boost_type, 0.0) > 0
        ]
        
        if not weighted_products:
            return 0.0
            
        return math.prod(weighted_products)
        
    else:  # weighted_sum (default)
        # Use provided weights or defaults
        weights = weights or DEFAULT_BOOST_WEIGHTS
        
        # Calculate weighted sum
        return sum(
            valid_boosts.get(boost_type, 0.0) * weight
            for boost_type, weight in weights.items()
        )

async def apply_all_boosts(
    results: List[SearchResult],
    boost_config: Dict[str, Any],
    citation_distributions: Dict[str, Dict[int, Dict[str, float]]] = None
) -> List[SearchResult]:
    """
    Apply all configured boost factors to search results.
    
    Args:
        results: List of search results to boost
        boost_config: Dictionary containing boost configuration including:
            - citation_boost: Overall strength of citation boost
            - recency_boost: Overall strength of recency boost
            - recency_multiplier: Controls decay rate of recency boost
            - doctype_boosts: Document type boost factors
            - field_boosts: Field-specific boost factors
            - boost_combination_method: Method to combine boosts
            - boost_weights: Weights for weighted combination methods
        citation_distributions: Dictionary of citation distributions by collection and year
        
    Returns:
        List[SearchResult]: List of boosted search results
    """
    if not results:
        return []
        
    try:
        # Create a deep copy of results to avoid modifying originals
        boosted_results = [deepcopy(result) for result in results]
        
        # Get boost configuration
        citation_boost = boost_config.get('citation_boost', 0.0)
        recency_boost = boost_config.get('recency_boost', 0.0)
        recency_multiplier = boost_config.get('recency_multiplier', 1.0)
        doctype_boosts = boost_config.get('doctype_boosts', {})
        field_boosts = boost_config.get('field_boosts', {})
        combination_method = boost_config.get('boost_combination_method', 'weighted_sum')
        boost_weights = boost_config.get('boost_weights', DEFAULT_BOOST_WEIGHTS)

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
            if citation_boost > 0:
                base_boost = calculate_citation_boost(
                    result.citation_count or 0,
                    result.collection or 'general',
                    result.year,
                    citation_distributions or {}
                )
                boosts['citation'] = base_boost * citation_boost
                result.boost_factors['citation'] = boosts['citation']
            
            # Recency boost
            if recency_boost > 0 and result.pubdate:
                base_boost = calculate_recency_boost(
                    result.pubdate,
                    recency_multiplier
                )
                boosts['recency'] = base_boost * recency_boost
                result.boost_factors['recency'] = boosts['recency']
            
            # Document type boost
            if doctype_boosts:
                base_boost = calculate_doctype_boost(
                    result.doctype,
                    doctype_boosts
                )
                boosts['doctype'] = base_boost
                result.boost_factors['doctype'] = boosts['doctype']
            
            # Field boost
            if field_boosts:
                field_boost = 0.0
                for field, weight in field_boosts.items():
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
            
            # Combine boost factors using the specified method
            final_boost = combine_boost_factors(
                boosts, 
                boost_weights,
                combination_method
            )
            
            # Apply final boost to score
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