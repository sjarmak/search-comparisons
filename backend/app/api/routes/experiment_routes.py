"""
Experiment API routes for the search-comparisons application.

This module contains route definitions for experiment-related endpoints,
used for testing new features, performing A/B tests, and collecting
performance metrics.
"""
import logging
import time
import random
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from ...api.models import SearchResult, SearchRequest
from ...services.ads_service import get_ads_results
from ...services.search_service import get_results_with_fallback, compare_results

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/experiments",
    tags=["experiments"],
    responses={404: {"description": "Not found"}},
)


class BoostConfig(BaseModel):
    """
    Configuration for a search result boosting experiment.
    
    Attributes:
        query: Original search query
        boost_fields: Fields to use for boosting (e.g., citation_count, year)
        boost_weights: Weight factors for each boost field
        max_boost: Maximum allowed boost factor
    """
    query: str
    boost_fields: List[str]
    boost_weights: Dict[str, float]
    max_boost: float = 2.0


class BoostResult(BaseModel):
    """
    Result of a search result boosting experiment.
    
    Attributes:
        original_results: Search results before boosting
        boosted_results: Search results after boosting
        boost_stats: Statistics about the boosting effects
    """
    original_results: List[SearchResult]
    boosted_results: List[SearchResult]
    boost_stats: Dict[str, Any]


@router.post("/boost")
async def boost_search_results(
    boost_config: BoostConfig
) -> BoostResult:
    """
    Apply experimental boosting to search results.
    
    Retrieves search results and applies boosting based on specified
    fields and weights to experiment with improved ranking.
    
    Args:
        boost_config: Configuration for the boosting experiment
    
    Returns:
        BoostResult: Original and boosted results with statistics
    
    Raises:
        HTTPException: If search or boosting fails
    """
    try:
        # Get original results
        fields = ["title", "authors", "abstract", "doi", "year", "citation_count"]
        original_results = await get_ads_results(boost_config.query, fields)
        
        if not original_results:
            raise HTTPException(status_code=404, detail="No results found for query")
        
        # Apply boosting
        boosted_results = apply_experimental_boost(
            original_results, 
            boost_config.boost_fields, 
            boost_config.boost_weights,
            boost_config.max_boost
        )
        
        # Calculate boost statistics
        stats = calculate_boost_stats(original_results, boosted_results)
        
        return BoostResult(
            original_results=original_results,
            boosted_results=boosted_results,
            boost_stats=stats
        )
        
    except Exception as e:
        logger.error(f"Error in boost experiment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in boost experiment: {str(e)}")


def apply_experimental_boost(
    results: List[SearchResult],
    boost_fields: List[str],
    boost_weights: Dict[str, float],
    max_boost: float
) -> List[SearchResult]:
    """
    Apply experimental boosting to search results.
    
    Applies boosting factors to results based on specified fields and weights,
    creating new boosted results with modified rankings.
    
    Args:
        results: Original search results
        boost_fields: Fields to use for boosting
        boost_weights: Weight factors for each boost field
        max_boost: Maximum allowed boost factor
    
    Returns:
        List[SearchResult]: Boosted search results
    """
    if not results:
        return []
    
    # Create copies of the results for boosting
    boosted_results = []
    
    for result in results:
        # Store original rank information
        original_rank = result.rank
        
        # Initialize boost factors
        boost_factors = {}
        total_boost = 1.0
        
        # Apply boosts for each field
        for field in boost_fields:
            if field in boost_weights:
                field_value = getattr(result, field, None)
                
                if field_value is not None:
                    if field == "citation_count" and isinstance(field_value, int):
                        # Boost by citation count (log scale to avoid extreme values)
                        if field_value > 0:
                            factor = 1.0 + (boost_weights[field] * (1.0 + (1.0 * field_value / 1000.0)))
                            boost_factors[field] = factor
                            total_boost *= factor
                    
                    elif field == "year" and isinstance(field_value, int):
                        # Boost newer publications
                        current_year = time.gmtime().tm_year
                        if 1800 <= field_value <= current_year:
                            age = current_year - field_value
                            factor = 1.0 + (boost_weights[field] * (1.0 - (age / 30.0)))
                            factor = max(1.0, factor)  # Don't penalize, only boost
                            boost_factors[field] = factor
                            total_boost *= factor
        
        # Apply max boost cap
        total_boost = min(total_boost, max_boost)
        
        # Create boosted result
        boosted_result = SearchResult(
            title=result.title,
            authors=result.authors,
            abstract=result.abstract,
            doi=result.doi,
            year=result.year,
            url=result.url,
            source=result.source,
            rank=result.rank,  # Will be re-ranked later
            citation_count=result.citation_count,
            doctype=result.doctype,
            property=result.property,
            # Boost-specific fields
            original_rank=original_rank,
            rank_change=0,  # Will be calculated after re-ranking
            original_score=1.0,
            boosted_score=total_boost,
            boost_factors=boost_factors
        )
        
        boosted_results.append(boosted_result)
    
    # Sort by boosted score
    boosted_results.sort(key=lambda x: x.boosted_score, reverse=True)
    
    # Re-rank and calculate rank changes
    for i, result in enumerate(boosted_results, 1):
        result.rank_change = result.original_rank - i
        result.rank = i
    
    return boosted_results


def calculate_boost_stats(
    original_results: List[SearchResult],
    boosted_results: List[SearchResult]
) -> Dict[str, Any]:
    """
    Calculate statistics for boosting experiment.
    
    Computes various metrics about the effects of boosting, including
    rank changes, movement statistics, and correlation between
    original and boosted rankings.
    
    Args:
        original_results: Results before boosting
        boosted_results: Results after boosting
    
    Returns:
        Dict[str, Any]: Statistics about the boosting effects
    """
    if not original_results or not boosted_results:
        return {
            "error": "No results to analyze"
        }
    
    # Initialize stats
    stats = {
        "count": len(boosted_results),
        "moved_up": 0,
        "moved_down": 0,
        "unchanged": 0,
        "avg_rank_change": 0,
        "max_rank_increase": 0,
        "max_rank_decrease": 0,
        "correlation": 0
    }
    
    # Calculate movement stats
    total_abs_change = 0
    for result in boosted_results:
        change = result.rank_change
        
        if change > 0:
            stats["moved_up"] += 1
            stats["max_rank_increase"] = max(stats["max_rank_increase"], change)
        elif change < 0:
            stats["moved_down"] += 1
            stats["max_rank_decrease"] = max(stats["max_rank_decrease"], abs(change))
        else:
            stats["unchanged"] += 1
            
        total_abs_change += abs(change)
    
    # Calculate average change
    stats["avg_rank_change"] = total_abs_change / len(boosted_results) if boosted_results else 0
    
    # Calculate correlation between original and new rankings
    if len(original_results) > 1 and len(boosted_results) > 1:
        try:
            import numpy as np
            from scipy.stats import spearmanr
            
            original_ranks = [r.rank for r in original_results]
            boosted_ranks = [r.rank for r in boosted_results]
            
            # Sort boosted results by their original order for correlation calculation
            boosted_ranks_sorted = sorted(boosted_ranks, key=lambda x: original_ranks[boosted_ranks.index(x)])
            
            # Calculate Spearman rank correlation
            correlation, _ = spearmanr(original_ranks, boosted_ranks_sorted)
            stats["correlation"] = correlation
        except ImportError:
            stats["correlation"] = "scipy not available"
        except Exception as e:
            stats["correlation_error"] = str(e)
    
    return stats


@router.post("/ab-test")
async def run_ab_test(
    search_request: SearchRequest,
    variation: str = Query("B", description="Test variation (A=default, B=experimental)")
) -> Dict[str, Any]:
    """
    Run an A/B test of search functionality.
    
    Performs a search with either the default algorithm (A) or an
    experimental algorithm (B) based on the variation parameter.
    
    Args:
        search_request: Standard search request
        variation: Which test variation to use (A or B)
    
    Returns:
        Dict[str, Any]: Search results with A/B test metadata
    
    Raises:
        HTTPException: If the search or experiment fails
    """
    # Record test metadata
    test_id = f"search-ab-{int(time.time())}-{random.randint(1000, 9999)}"
    
    try:
        results = {}
        
        # Get results based on variation
        if variation.upper() == "A":
            # Variation A: Default algorithm
            results = await get_results_with_fallback(
                query=search_request.query,
                sources=search_request.sources,
                fields=search_request.fields
            )
        else:
            # Variation B: Experimental algorithm
            # For demonstration, we'll just use the same algorithm but mark it as experimental
            results = await get_results_with_fallback(
                query=search_request.query,
                sources=search_request.sources,
                fields=search_request.fields
            )
            
            # Apply some experimental modification to variation B
            # (in a real implementation, this would be an actual algorithm change)
            for source, source_results in results.items():
                for result in source_results:
                    # Example: Tag results with experiment info
                    if not result.property:
                        result.property = []
                    result.property.append(f"ab-test:{test_id}")
        
        # Compare results if we have any
        comparison = {}
        if results:
            comparison = compare_results(
                sources_results=results,
                metrics=search_request.metrics,
                fields=search_request.fields
            )
        
        # Return results with test metadata
        return {
            "test_id": test_id,
            "variation": variation.upper(),
            "query": search_request.query,
            "sources": search_request.sources,
            "metrics": search_request.metrics,
            "fields": search_request.fields,
            "results": results,
            "comparison": comparison,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Error in A/B test: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in A/B test: {str(e)}")


@router.get("/log-analysis")
async def analyze_search_logs() -> Dict[str, Any]:
    """
    Analyze search logs for patterns and performance metrics.
    
    Parses search logs to extract insights about query patterns,
    response times, cache hit rates, and other metrics useful for
    improving search performance.
    
    Returns:
        Dict[str, Any]: Log analysis results
    
    Raises:
        HTTPException: If log analysis fails
    """
    # This is a placeholder implementation
    # In a real implementation, this would connect to logs and analyze them
    
    return {
        "message": "Log analysis feature is not yet implemented",
        "metrics": {
            "avg_response_time": "N/A",
            "cache_hit_rate": "N/A",
            "common_queries": [],
            "error_rate": "N/A"
        },
        "timestamp": time.time()
    } 