"""Service module for handling various types of boosts in search results."""
from typing import Dict, List, Optional
from datetime import datetime
from ..api.models import SearchResult


def apply_citation_boost(
    results: List[SearchResult],
    boost_factor: float = 1.0,
    min_citations: int = 0
) -> List[SearchResult]:
    """Apply citation-based boosting to search results.

    Args:
        results: List of search results to boost
        boost_factor: Factor to multiply citation counts by
        min_citations: Minimum number of citations required for boosting

    Returns:
        List[SearchResult]: Results with citation-based boosting applied
    """
    boosted_results = []
    for result in results:
        if result.citation_count is not None and result.citation_count >= min_citations:
            # Store original score if not already stored
            if result.boosted_score is None:
                result.boosted_score = 1.0
                result.original_score = 1.0
            
            # Apply citation boost
            citation_boost = 1.0 + (result.citation_count * boost_factor)
            result.boosted_score *= citation_boost
            
            # Store boost factors
            if result.boost_factors is None:
                result.boost_factors = {}
            result.boost_factors['citations'] = citation_boost
            
        boosted_results.append(result)
    return boosted_results


def apply_recency_boost(
    results: List[SearchResult],
    boost_factor: float = 1.0,
    reference_year: Optional[int] = None
) -> List[SearchResult]:
    """Apply recency-based boosting to search results.

    Args:
        results: List of search results to boost
        boost_factor: Factor to multiply recency boost by
        reference_year: Year to use as reference (defaults to current year)

    Returns:
        List[SearchResult]: Results with recency-based boosting applied
    """
    if reference_year is None:
        reference_year = datetime.now().year

    boosted_results = []
    for result in results:
        if result.year is not None:
            # Store original score if not already stored
            if result.boosted_score is None:
                result.boosted_score = 1.0
                result.original_score = 1.0
            
            # Calculate recency boost (exponential decay)
            years_old = reference_year - result.year
            recency_boost = 1.0 + (boost_factor * (1.0 / (1.0 + years_old)))
            result.boosted_score *= recency_boost
            
            # Store boost factors
            if result.boost_factors is None:
                result.boost_factors = {}
            result.boost_factors['recency'] = recency_boost
            
        boosted_results.append(result)
    return boosted_results


def apply_doctype_boost(
    results: List[SearchResult],
    doctype_boosts: Dict[str, float]
) -> List[SearchResult]:
    """Apply document type-based boosting to search results.

    Args:
        results: List of search results to boost
        doctype_boosts: Dictionary mapping document types to their boost values

    Returns:
        List[SearchResult]: Results with document type-based boosting applied
    """
    boosted_results = []
    for result in results:
        if result.doctype and result.doctype in doctype_boosts:
            # Store original score if not already stored
            if result.boosted_score is None:
                result.boosted_score = 1.0
                result.original_score = 1.0
            
            # Apply document type boost
            doctype_boost = doctype_boosts[result.doctype]
            result.boosted_score *= doctype_boost
            
            # Store boost factors
            if result.boost_factors is None:
                result.boost_factors = {}
            result.boost_factors['doctype'] = doctype_boost
            
        boosted_results.append(result)
    return boosted_results


def apply_all_boosts(
    results: List[SearchResult],
    citation_boost: Optional[float] = None,
    min_citations: Optional[int] = None,
    recency_boost: Optional[float] = None,
    reference_year: Optional[int] = None,
    doctype_boosts: Optional[Dict[str, float]] = None
) -> List[SearchResult]:
    """Apply all types of boosts to search results.

    Args:
        results: List of search results to boost
        citation_boost: Factor to multiply citation counts by
        min_citations: Minimum number of citations required for boosting
        recency_boost: Factor to multiply recency boost by
        reference_year: Year to use as reference for recency
        doctype_boosts: Dictionary mapping document types to their boost values

    Returns:
        List[SearchResult]: Results with all boosts applied
    """
    boosted_results = results.copy()

    # Apply citation boost if configured
    if citation_boost is not None:
        boosted_results = apply_citation_boost(
            boosted_results,
            boost_factor=citation_boost,
            min_citations=min_citations or 0
        )

    # Apply recency boost if configured
    if recency_boost is not None:
        boosted_results = apply_recency_boost(
            boosted_results,
            boost_factor=recency_boost,
            reference_year=reference_year
        )

    # Apply document type boost if configured
    if doctype_boosts:
        boosted_results = apply_doctype_boost(
            boosted_results,
            doctype_boosts
        )

    # Sort results by boosted score
    boosted_results.sort(key=lambda x: x.boosted_score or 0, reverse=True)

    # Update ranks based on boosted scores
    for i, result in enumerate(boosted_results):
        if result.original_rank is None:
            result.original_rank = result.rank
        result.rank = i + 1
        result.rank_change = result.original_rank - result.rank

    return boosted_results 