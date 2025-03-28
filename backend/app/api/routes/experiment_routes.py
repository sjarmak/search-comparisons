"""
Experiment API routes for the search-comparisons application.

This module contains route definitions for experiment-related endpoints,
used for testing new features, performing A/B tests, and collecting
performance metrics.
"""
import logging
import time
import random
import re
import json
from collections import defaultdict, Counter
from typing import Dict, List, Any, Optional, Tuple
import math
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from ...services import search_service
from ...services.ads_service import get_ads_results
from ...services.quepid_service import evaluate_search_results, load_case_with_judgments, get_quepid_cases
from ..models import (
    ErrorResponse, 
    QuepidEvaluationRequest,
    QuepidEvaluationResponse,
    QuepidEvaluationSourceResult,
    MetricResult,
    SearchResult,
    SearchRequest
)

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/experiments",
    tags=["experiments"],
    responses={404: {"description": "Not found"}},
)

# Create a secondary router for backward compatibility with old endpoints
back_compat_router = APIRouter(
    prefix="/api",
    tags=["experiments"],
    responses={404: {"description": "Not found"}},
)


class BoostConfig(BaseModel):
    """
    Configuration for a search result boosting experiment.
    
    Attributes:
        query: Original search query
        transformed_query: Transformed query if available
        enable_cite_boost: Whether to apply citation boost
        cite_boost_weight: Weight for citation boost
        enable_recency_boost: Whether to apply recency boost
        recency_boost_weight: Weight for recency boost
        recency_function: Type of recency decay function
        recency_multiplier: Multiplier for recency decay
        recency_midpoint: Midpoint for sigmoid recency (months)
        enable_doctype_boost: Whether to apply document type boost
        doctype_boost_weight: Weight for document type boost
        enable_refereed_boost: Whether to apply refereed boost
        refereed_boost_weight: Weight for refereed boost
        combination_method: Method to combine boost factors
        max_boost: Maximum allowed boost factor
    """
    query: str
    transformed_query: Optional[str] = None
    enable_cite_boost: bool = True
    cite_boost_weight: float = 1.0
    enable_recency_boost: bool = True
    recency_boost_weight: float = 1.0
    recency_function: str = "exponential"  # exponential, inverse, linear, sigmoid
    recency_multiplier: float = 0.01
    recency_midpoint: int = 36  # 3 years in months
    enable_doctype_boost: bool = True
    doctype_boost_weight: float = 1.0
    enable_refereed_boost: bool = True
    refereed_boost_weight: float = 1.0
    combination_method: str = "sum"  # sum, product, max
    max_boost: float = 5.0


class BoostFactors(BaseModel):
    """
    Boost factors applied to a search result.
    
    Attributes:
        cite_boost: Boost factor from citation count
        recency_boost: Boost factor from publication recency
        doctype_boost: Boost factor from document type
        refereed_boost: Boost factor from refereed status
    """
    cite_boost: float = 0.0
    recency_boost: float = 0.0
    doctype_boost: float = 0.0
    refereed_boost: float = 0.0


class BoostedSearchResult(SearchResult):
    """
    A search result with applied boost factors.
    
    Inherits all fields from SearchResult and adds boost-specific fields.
    
    Attributes:
        boost_factors: Individual boost factors applied
        final_boost: Final combined boost score
        original_rank: Original position in results
        rank_change: Change in position after boosting
    """
    boost_factors: Optional[BoostFactors] = None
    final_boost: float = 0.0
    original_rank: int
    rank_change: int = 0


class BoostResult(BaseModel):
    """
    Result of a search result boosting experiment.
    
    Attributes:
        query: The original search query
        transformed_query: The transformed query if one was used
        original_results: Search results before boosting
        boosted_results: Search results after boosting
        boost_config: The configuration used for boosting
        stats: Statistics about the boosting effects
    """
    query: str
    transformed_query: Optional[str] = None
    original_results: List[SearchResult]
    boosted_results: List[BoostedSearchResult]
    boost_config: BoostConfig
    stats: Dict[str, Any]


@router.post("/boost", response_model=BoostResult)
async def boost_search_results(
    boost_config: BoostConfig
) -> BoostResult:
    """
    Apply advanced boosting to search results.
    
    This endpoint implements the advanced boosting approach which applies
    multiple configurable boost factors to search results based on metadata
    such as citation count, publication year, document type, and refereed status.
    
    Args:
        boost_config: Configuration for the boosting experiment
    
    Returns:
        BoostResult: Original and boosted results with statistics
    
    Raises:
        HTTPException: If search or boosting fails
    """
    try:
        logger.info(f"Starting boost experiment with query: {boost_config.query}")
        
        # Get original results
        fields = ["title", "authors", "abstract", "doi", "year", "citation_count", "doctype", "property", "url"]
        original_results = await get_ads_results(boost_config.query, fields)
        
        if not original_results:
            logger.warning(f"No results found for query: {boost_config.query}")
            raise HTTPException(status_code=404, detail="No results found for query")
        
        logger.info(f"Retrieved {len(original_results)} results for boosting")
        
        # Process each result to add boost factors
        boosted_results = []
        current_year = datetime.now().year
        
        for idx, result in enumerate(original_results):
            try:
                # Initialize boost factors
                boost_factors = BoostFactors()
                
                # 1. Citation boost (Enhanced version - use logarithmic scaling)
                if boost_config.enable_cite_boost:
                    citation_count = getattr(result, "citation_count", 0) or 0
                    
                    # Use logarithmic scaling to handle large variations in citation counts
                    cite_boost = math.log1p(citation_count) * boost_config.cite_boost_weight
                    boost_factors.cite_boost = cite_boost
                    logger.debug(f"Applied citation boost: {cite_boost} for {citation_count} citations")
                
                # 2. Recency boost (with different decay functions)
                if boost_config.enable_recency_boost:
                    pub_year = getattr(result, "year", None)
                    if pub_year:
                        # Calculate age in months (approximate)
                        age_in_years = current_year - pub_year
                        age_in_months = age_in_years * 12
                        
                        recency_boost = 0.0
                        
                        # Apply different decay functions
                        if boost_config.recency_function == "exponential":
                            # Exponential decay: e^(-m * age_months)
                            recency_boost = math.exp(-boost_config.recency_multiplier * age_in_months)
                        elif boost_config.recency_function == "inverse":
                            # Reciprocal/inverse Function: 1/(1 + multiplier * age_months)
                            recency_boost = 1 / (1 + boost_config.recency_multiplier * age_in_months)
                        elif boost_config.recency_function == "linear":
                            # Linear Decay: max(1 - m * age_months, 0)
                            recency_boost = max(0, 1 - boost_config.recency_multiplier * age_in_months)
                        elif boost_config.recency_function == "sigmoid":
                            # Logistic/Sigmoid: 1/(1 + e^(m * (age_months - midpoint)))
                            recency_boost = 1 / (1 + math.exp(boost_config.recency_multiplier * 
                                                            (age_in_months - boost_config.recency_midpoint)))
                        
                        boost_factors.recency_boost = recency_boost * boost_config.recency_boost_weight
                        logger.debug(f"Applied recency boost: {boost_factors.recency_boost} for year {pub_year}")
                
                # 3. Document type boost
                if boost_config.enable_doctype_boost:
                    doctype = getattr(result, "doctype", "") or ""
                    
                    # Normalize doctype to lowercase string for comparison
                    doctype_str = doctype.lower() if isinstance(doctype, str) else ""
                    
                    # Weights based on ADS document types, ordered by importance
                    doctype_ranks = {
                        "review": 1,       # Review article (highest rank)
                        "book": 2,         # Book
                        "article": 3,      # Standard article
                        "eprint": 4,       # Preprints
                        "proceedings": 5,  # Conference proceedings
                        "inproceedings": 5,# Conference proceedings (same rank)
                        "thesis": 6,       # Thesis/dissertation
                        "": 7              # Default/unknown (lowest rank)
                    }
                    
                    # Calculate boosting using the rank-to-boost conversion formula
                    rank = doctype_ranks.get(doctype_str, 7)  # Default to lowest rank if unknown
                    unique_ranks = sorted(set(doctype_ranks.values()))
                    total_ranks = len(unique_ranks)
                    
                    # Apply the formula: 1 - (rank_index / (num_unique_ranks - 1))
                    rank_index = unique_ranks.index(rank)
                    doctype_boost = 1 - (rank_index / (total_ranks - 1)) if total_ranks > 1 else 0
                    
                    boost_factors.doctype_boost = doctype_boost * boost_config.doctype_boost_weight
                    logger.debug(f"Applied doctype boost: {boost_factors.doctype_boost} for type {doctype_str}")
                
                # 4. Refereed boost (Simple binary boost)
                if boost_config.enable_refereed_boost:
                    properties = getattr(result, "property", []) or []
                    if isinstance(properties, str):
                        properties = [properties]
                    
                    is_refereed = "REFEREED" in properties
                    # Simple binary boost: 1 if refereed, 0 if not
                    boost_factors.refereed_boost = float(is_refereed) * boost_config.refereed_boost_weight
                    logger.debug(f"Applied refereed boost: {boost_factors.refereed_boost} (is_refereed: {is_refereed})")
                
                # Calculate final boost based on combination method
                if boost_config.combination_method == "sum":
                    # Simple sum: citation + recency + doctype + refereed
                    final_boost = (boost_factors.cite_boost + boost_factors.recency_boost + 
                                boost_factors.doctype_boost + boost_factors.refereed_boost)
                elif boost_config.combination_method == "product":
                    # Product: (1+citation) * (1+recency) * (1+doctype) * (1+refereed) - 1
                    final_boost = (
                        (1 + boost_factors.cite_boost) * 
                        (1 + boost_factors.recency_boost) * 
                        (1 + boost_factors.doctype_boost) * 
                        (1 + boost_factors.refereed_boost)
                    ) - 1
                elif boost_config.combination_method == "max":
                    # Maximum: use the highest boost factor
                    final_boost = max(
                        boost_factors.cite_boost,
                        boost_factors.recency_boost,
                        boost_factors.doctype_boost,
                        boost_factors.refereed_boost
                    )
                else:
                    # Default to sum if invalid method
                    final_boost = (boost_factors.cite_boost + boost_factors.recency_boost + 
                                boost_factors.doctype_boost + boost_factors.refereed_boost)
                
                # Cap the final boost if needed
                final_boost = min(final_boost, boost_config.max_boost)
                
                # Create boosted result
                try:
                    # Get all fields from the original result
                    result_dict = result.model_dump()
                    
                    # Remove any existing boost_factors to avoid conflict
                    if 'boost_factors' in result_dict:
                        del result_dict['boost_factors']
                    
                    # Create the boosted result with our new boost factors
                    boosted_result = BoostedSearchResult(
                        **result_dict,
                        boost_factors=boost_factors,
                        final_boost=final_boost,
                        original_rank=idx + 1,
                        rank_change=0  # Will be calculated after sorting
                    )
                    
                    boosted_results.append(boosted_result)
                    logger.debug(f"Result {idx+1}: Final boost={final_boost}")
                except Exception as e:
                    logger.error(f"Error creating BoostedSearchResult: {str(e)}", exc_info=True)
                    # Try an alternative approach if the first attempt fails
                    try:
                        # Create a dictionary with all the necessary fields
                        boosted_dict = {**result_dict}
                        boosted_dict['boost_factors'] = boost_factors
                        boosted_dict['final_boost'] = final_boost
                        boosted_dict['original_rank'] = idx + 1
                        boosted_dict['rank_change'] = 0
                        
                        # Create the result from this dictionary
                        boosted_result = BoostedSearchResult.model_validate(boosted_dict)
                        boosted_results.append(boosted_result)
                    except Exception as inner_e:
                        logger.error(f"Alternative approach also failed: {str(inner_e)}", exc_info=True)
                        # If all else fails, add a minimal result
                        boosted_result = BoostedSearchResult(
                            title=getattr(result, "title", "Unknown"),
                            url=getattr(result, "url", ""),
                            abstract=getattr(result, "abstract", ""),
                            authors=getattr(result, "authors", []),
                            boost_factors=boost_factors,
                            final_boost=final_boost,
                            original_rank=idx + 1,
                            rank_change=0
                        )
                        boosted_results.append(boosted_result)
                
            except Exception as e:
                logger.error(f"Error processing result {idx}: {str(e)}", exc_info=True)
                # Still add the result, but with no boost
                try:
                    # Get all fields from the original result
                    result_dict = result.model_dump()
                    
                    # Remove any existing boost_factors to avoid conflict
                    if 'boost_factors' in result_dict:
                        del result_dict['boost_factors']
                    
                    boosted_result = BoostedSearchResult(
                        **result_dict,
                        boost_factors=BoostFactors(),
                        final_boost=0.0,
                        original_rank=idx + 1,
                        rank_change=0
                    )
                    boosted_results.append(boosted_result)
                except Exception as inner_e:
                    logger.error(f"Failed to create minimal boosted result: {str(inner_e)}", exc_info=True)
                    # If everything fails, at least add something with the title
                    boosted_result = BoostedSearchResult(
                        title=getattr(result, "title", "Unknown"),
                        url=getattr(result, "url", ""),
                        abstract=getattr(result, "abstract", ""),
                        authors=getattr(result, "authors", []),
                        boost_factors=BoostFactors(),
                        final_boost=0.0,
                        original_rank=idx + 1,
                        rank_change=0
                    )
                    boosted_results.append(boosted_result)
        
        # Sort results by final boost score (descending)
        boosted_results.sort(key=lambda x: x.final_boost, reverse=True)
        
        # Re-rank and calculate rank changes
        for idx, result in enumerate(boosted_results, 1):
            original_rank = result.original_rank
            new_rank = idx
            result.rank = new_rank
            result.rank_change = original_rank - new_rank
        
        # Calculate boost statistics
        stats = calculate_boost_stats(original_results, boosted_results)
        
        # Add additional statistics
        stats.update({
            "boost_factors": {
                "cite": [r.boost_factors.cite_boost for r in boosted_results],
                "recency": [r.boost_factors.recency_boost for r in boosted_results],
                "doctype": [r.boost_factors.doctype_boost for r in boosted_results],
                "refereed": [r.boost_factors.refereed_boost for r in boosted_results]
            },
            "final_boosts": [r.final_boost for r in boosted_results],
            "highest_boosted": max([r.final_boost for r in boosted_results], default=0),
            "average_boost": sum([r.final_boost for r in boosted_results]) / len(boosted_results) if boosted_results else 0
        })
        
        return BoostResult(
            query=boost_config.query,
            transformed_query=boost_config.transformed_query,
            original_results=original_results,
            boosted_results=boosted_results,
            boost_config=boost_config,
            stats=stats
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error in boost experiment: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error in boost experiment: {str(e)}")


def calculate_boost_stats(
    original_results: List[SearchResult],
    boosted_results: List[BoostedSearchResult]
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
            
            # Calculate Spearman rank correlation
            correlation, _ = spearmanr(original_ranks, boosted_ranks)
            stats["correlation"] = correlation
        except ImportError:
            stats["correlation"] = "scipy not available"
        except Exception as e:
            stats["correlation_error"] = str(e)
    
    # Add boost distribution info
    if boosted_results:
        boost_values = [r.final_boost for r in boosted_results]
        stats["boost_distribution"] = {
            "min": min(boost_values),
            "max": max(boost_values),
            "avg": sum(boost_values) / len(boost_values),
            "median": sorted(boost_values)[len(boost_values) // 2]
        }
        
        # Categorize boost levels
        low_boosts = sum(1 for b in boost_values if b < 0.5)
        medium_boosts = sum(1 for b in boost_values if 0.5 <= b < 1.5)
        high_boosts = sum(1 for b in boost_values if b >= 1.5)
        
        stats["boost_categories"] = {
            "low": low_boosts,
            "medium": medium_boosts,
            "high": high_boosts
        }
    
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
            results = await search_service.get_results_with_fallback(
                source=None,
                query=search_request.query,
                sources=search_request.sources,
                fields=search_request.fields
            )
        else:
            # Variation B: Experimental algorithm
            # For demonstration, we'll just use the same algorithm but mark it as experimental
            results = await search_service.get_results_with_fallback(
                source=None,
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
            comparison = search_service.compare_results(
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


@router.post(
    "/quepid-evaluation", 
    response_model=QuepidEvaluationResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def evaluate_search_with_quepid(request: QuepidEvaluationRequest) -> QuepidEvaluationResponse:
    """
    Evaluate search results against Quepid judgments.
    
    This endpoint executes a search query against multiple sources and
    evaluates the results using relevance judgments from Quepid,
    calculating metrics such as nDCG@10.
    
    Args:
        request: The evaluation request parameters
    
    Returns:
        QuepidEvaluationResponse: The evaluation results for each source
    
    Raises:
        HTTPException: If there's an error processing the request
    """
    logger.info(f"Quepid evaluation request: {request.dict()}")
    
    start_time = time.time()
    
    try:
        # Validate the case exists and contains judgments
        case = await load_case_with_judgments(request.case_id)
        if not case:
            raise HTTPException(
                status_code=404,
                detail=f"Quepid case {request.case_id} not found or contains no judgments"
            )
        
        # Use default fields if none provided
        fields = request.fields or ["title", "abstract", "authors", "year", "doi", "url"]
        
        # Find closest matching query if exact match not found
        query_to_use = request.query
        available_queries = case.queries
        
        if request.query not in case.judgments:
            closest_query = None
            # Find query with most overlapping terms
            query_terms = set(request.query.lower().split())
            
            max_overlap = 0
            for q in case.queries:
                q_terms = set(q.lower().split())
                overlap = len(query_terms & q_terms)
                if overlap > max_overlap:
                    max_overlap = overlap
                    closest_query = q
            
            if closest_query:
                logger.info(f"Using closest query match: '{closest_query}' instead of '{request.query}'")
                query_to_use = closest_query
            else:
                error_msg = f"No matching query found for '{request.query}' in case {request.case_id}"
                logger.warning(error_msg)
                return QuepidEvaluationResponse(
                    query=request.query,
                    case_id=request.case_id,
                    case_name=case.name,
                    source_results=[],
                    total_judged=0,
                    total_relevant=0,
                    available_queries=case.queries
                )
        
        # Get judgments for the query
        judgments = case.judgments.get(query_to_use, [])
        if not judgments:
            error_msg = f"No judgments found for query '{query_to_use}' in case {request.case_id}"
            logger.warning(error_msg)
            return QuepidEvaluationResponse(
                query=request.query,
                case_id=request.case_id,
                case_name=case.name,
                source_results=[],
                total_judged=0,
                total_relevant=0,
                available_queries=case.queries
            )
        
        # Count total judged and relevant documents
        total_judged = len(judgments)
        total_relevant = sum(1 for j in judgments if j.rating > 0)
        
        # Get search results for each source
        source_results = []
        for source in request.sources:
            try:
                # Get results from the source
                results = await search_service.get_results_with_fallback(
                    source=source,
                    query=query_to_use,
                    fields=fields,
                    num_results=request.max_results
                )
                
                # Evaluate results against judgments
                eval_result = await evaluate_search_results(
                    query=query_to_use,
                    search_results=results,
                    case_id=request.case_id
                )
                
                # Format metrics for response
                metrics = []
                for name, value in eval_result.get("ndcg", {}).items():
                    metrics.append(MetricResult(
                        name=name,
                        value=value,
                        description=f"Normalized Discounted Cumulative Gain at {name.split('@')[1]}"
                    ))
                
                for name, value in eval_result.get("precision", {}).items():
                    metrics.append(MetricResult(
                        name=name,
                        value=value,
                        description=f"Precision at {name.split('@')[1]}"
                    ))
                
                metrics.append(MetricResult(
                    name="recall",
                    value=eval_result.get("recall", 0.0),
                    description="Recall (relevant retrieved / total relevant)"
                ))
                
                # Add to source results
                source_results.append(QuepidEvaluationSourceResult(
                    source=source,
                    metrics=metrics,
                    judged_retrieved=eval_result.get("judged_retrieved", 0),
                    relevant_retrieved=eval_result.get("relevant_retrieved", 0),
                    results_count=eval_result.get("results_count", 0)
                ))
                
            except Exception as e:
                logger.error(f"Error evaluating {source} results: {str(e)}", exc_info=True)
                # Continue with other sources
        
        # Create response
        response = QuepidEvaluationResponse(
            query=request.query,
            case_id=request.case_id,
            case_name=case.name,
            source_results=source_results,
            total_judged=total_judged,
            total_relevant=total_relevant,
            available_queries=case.queries if query_to_use != request.query else None
        )
        
        # Log timing
        end_time = time.time()
        logger.info(f"Quepid evaluation completed in {end_time - start_time:.2f}s")
        
        return response
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(f"Quepid evaluation error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error evaluating results: {str(e)}"
        )


@router.get(
    "/quepid-cases", 
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def get_available_quepid_cases() -> List[Dict[str, Any]]:
    """
    Get a list of available Quepid cases.
    
    This endpoint retrieves a list of cases from Quepid that are
    available for use in evaluations.
    
    Returns:
        List[Dict[str, Any]]: List of Quepid cases
    
    Raises:
        HTTPException: If there's an error retrieving the cases
    """
    try:
        cases = await get_quepid_cases()
        
        if isinstance(cases, dict) and cases.get('error'):
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving Quepid cases: {cases.get('message', 'Unknown error')}"
            )
        
        return cases
    
    except Exception as e:
        logger.error(f"Error getting Quepid cases: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving Quepid cases: {str(e)}"
        )


@back_compat_router.post("/boost-experiment")
async def boost_experiment_legacy(
    data: dict
) -> Dict[str, Any]:
    """
    Legacy endpoint for backward compatibility with the old boost-experiment API.
    
    This endpoint converts the request format from the old API to the new API format
    and delegates to the boost_search_results function.
    
    Args:
        data: Dictionary containing the boost experiment request data
        
    Returns:
        Dict[str, Any]: Results with status and boosted results
    """
    try:
        query = data.get("query", "")
        logger.info(f"Received legacy boost experiment request with query: {query}")
        
        # IMPORTANT: Log that field boosts in this experiment don't affect the main search query
        logger.info("IMPORTANT: Boost experiment only applies boost locally and doesn't affect the Web of Science API query")
        
        # Extract the query and boost config
        transformed_query = data.get("transformedQuery", None)
        boost_config_data = data.get("boostConfig", {})
        
        # Process the input results if they are provided
        input_results = data.get("results", [])
        logger.info(f"Received {len(input_results)} results to process with the legacy endpoint")
        
        # Check if input data is reasonable
        if not query:
            logger.warning("No query provided in the request")
            return {
                "status": "error",
                "message": "No query provided"
            }
            
        if not input_results:
            logger.warning("No results provided in the request")
            return {
                "status": "error",
                "message": "No results to process"
            }
        
        # Create a BoostConfig object with the data from the request
        boost_config = BoostConfig(
            query=query,
            transformed_query=transformed_query,
            enable_cite_boost=boost_config_data.get("enableCiteBoost", True),
            cite_boost_weight=boost_config_data.get("citeBoostWeight", 1.0),
            enable_recency_boost=boost_config_data.get("enableRecencyBoost", True),
            recency_boost_weight=boost_config_data.get("recencyBoostWeight", 1.0),
            recency_function=boost_config_data.get("recencyFunction", "exponential"),
            recency_multiplier=boost_config_data.get("recencyMultiplier", 0.01),
            recency_midpoint=boost_config_data.get("recencyMidpoint", 36),
            enable_doctype_boost=boost_config_data.get("enableDoctypeBoost", True),
            doctype_boost_weight=boost_config_data.get("doctypeBoostWeight", 1.0),
            enable_refereed_boost=boost_config_data.get("enableRefereedBoost", True),
            refereed_boost_weight=boost_config_data.get("refereedBoostWeight", 1.0),
            combination_method=boost_config_data.get("combinationMethod", "sum"),
            max_boost=boost_config_data.get("maxBoost", 5.0)
        )
        
        # Log the boost weights being applied
        logger.info(f"Applying boost weights: cite={boost_config.cite_boost_weight}, " +
                   f"recency={boost_config.recency_boost_weight}, " +
                   f"doctype={boost_config.doctype_boost_weight}, " +
                   f"refereed={boost_config.refereed_boost_weight}")
        
        # Process each of the input results directly instead of using boost_search_results
        boosted_results = []
        current_year = datetime.now().year
        
        for idx, result_data in enumerate(input_results):
            try:
                # Convert the input result to a SearchResult object
                search_result = SearchResult(
                    title=result_data.get("title", ""),
                    authors=result_data.get("authors", []),
                    abstract=result_data.get("abstract", ""),
                    url=result_data.get("url", ""),
                    source="input",
                    rank=idx + 1,
                    score=1.0,
                    citation_count=result_data.get("citation_count", 0),
                    year=result_data.get("year", None),
                    doctype=result_data.get("doctype", ""),
                    doi=result_data.get("doi", ""),
                    property=result_data.get("property", [])
                )
                
                # Initialize boost factors
                boost_factors = BoostFactors()
                
                # 1. Citation boost (Enhanced version - use logarithmic scaling)
                if boost_config.enable_cite_boost:
                    citation_count = result_data.get("citation_count", 0) or 0
                    
                    # Use logarithmic scaling to handle large variations in citation counts
                    cite_boost = math.log1p(citation_count) * boost_config.cite_boost_weight
                    boost_factors.cite_boost = cite_boost
                    logger.debug(f"Applied citation boost: {cite_boost} for {citation_count} citations")
                
                # 2. Recency boost (with different decay functions)
                if boost_config.enable_recency_boost:
                    pub_year = result_data.get("year")
                    if pub_year:
                        # Calculate age in months (approximate)
                        age_in_years = current_year - pub_year
                        age_in_months = age_in_years * 12
                        
                        recency_boost = 0.0
                        
                        # Apply different decay functions
                        if boost_config.recency_function == "exponential":
                            # Exponential decay: e^(-m * age_months)
                            recency_boost = math.exp(-boost_config.recency_multiplier * age_in_months)
                        elif boost_config.recency_function == "inverse":
                            # Reciprocal/inverse Function: 1/(1 + multiplier * age_months)
                            recency_boost = 1 / (1 + boost_config.recency_multiplier * age_in_months)
                        elif boost_config.recency_function == "linear":
                            # Linear Decay: max(1 - m * age_months, 0)
                            recency_boost = max(0, 1 - boost_config.recency_multiplier * age_in_months)
                        elif boost_config.recency_function == "sigmoid":
                            # Logistic/Sigmoid: 1/(1 + e^(m * (age_months - midpoint)))
                            recency_boost = 1 / (1 + math.exp(boost_config.recency_multiplier * 
                                                            (age_in_months - boost_config.recency_midpoint)))
                        
                        boost_factors.recency_boost = recency_boost * boost_config.recency_boost_weight
                        logger.debug(f"Applied recency boost: {boost_factors.recency_boost} for year {pub_year}")
                
                # 3. Document type boost
                if boost_config.enable_doctype_boost:
                    doctype = result_data.get("doctype", "") or ""
                    
                    # Normalize doctype to lowercase string for comparison
                    doctype_str = doctype.lower() if isinstance(doctype, str) else ""
                    
                    # Weights based on ADS document types, ordered by importance
                    doctype_ranks = {
                        "review": 1,       # Review article (highest rank)
                        "book": 2,         # Book
                        "article": 3,      # Standard article
                        "eprint": 4,       # Preprints
                        "proceedings": 5,  # Conference proceedings
                        "inproceedings": 5,# Conference proceedings (same rank)
                        "thesis": 6,       # Thesis/dissertation
                        "": 7              # Default/unknown (lowest rank)
                    }
                    
                    # Calculate boosting using the rank-to-boost conversion formula
                    rank = doctype_ranks.get(doctype_str, 7)  # Default to lowest rank if unknown
                    unique_ranks = sorted(set(doctype_ranks.values()))
                    total_ranks = len(unique_ranks)
                    
                    # Apply the formula: 1 - (rank_index / (num_unique_ranks - 1))
                    rank_index = unique_ranks.index(rank)
                    doctype_boost = 1 - (rank_index / (total_ranks - 1)) if total_ranks > 1 else 0
                    
                    boost_factors.doctype_boost = doctype_boost * boost_config.doctype_boost_weight
                    logger.debug(f"Applied doctype boost: {boost_factors.doctype_boost} for type {doctype_str}")
                
                # 4. Refereed boost (Simple binary boost)
                if boost_config.enable_refereed_boost:
                    properties = result_data.get("property", []) or []
                    if isinstance(properties, str):
                        properties = [properties]
                    
                    is_refereed = "REFEREED" in properties
                    # Simple binary boost: 1 if refereed, 0 if not
                    boost_factors.refereed_boost = float(is_refereed) * boost_config.refereed_boost_weight
                    logger.debug(f"Applied refereed boost: {boost_factors.refereed_boost} (is_refereed: {is_refereed})")
                
                # Calculate final boost based on combination method
                if boost_config.combination_method == "sum":
                    # Simple sum: citation + recency + doctype + refereed
                    final_boost = (boost_factors.cite_boost + boost_factors.recency_boost + 
                                boost_factors.doctype_boost + boost_factors.refereed_boost)
                elif boost_config.combination_method == "product":
                    # Product: (1+citation) * (1+recency) * (1+doctype) * (1+refereed) - 1
                    final_boost = (
                        (1 + boost_factors.cite_boost) * 
                        (1 + boost_factors.recency_boost) * 
                        (1 + boost_factors.doctype_boost) * 
                        (1 + boost_factors.refereed_boost)
                    ) - 1
                elif boost_config.combination_method == "max":
                    # Maximum: use the highest boost factor
                    final_boost = max(
                        boost_factors.cite_boost,
                        boost_factors.recency_boost,
                        boost_factors.doctype_boost,
                        boost_factors.refereed_boost
                    )
                else:
                    # Default to sum if invalid method
                    final_boost = (boost_factors.cite_boost + boost_factors.recency_boost + 
                                boost_factors.doctype_boost + boost_factors.refereed_boost)
                
                # Cap the final boost if needed
                final_boost = min(final_boost, boost_config.max_boost)
                
                # Create boosted result 
                boosted_result = {
                    # Keep all original fields
                    **result_data,
                    # Add boost-specific fields
                    "boostFactors": boost_factors.model_dump(),
                    "finalBoost": final_boost,
                    "originalRank": idx + 1,
                    "rank": idx + 1,  # Will be re-ranked later
                    "rankChange": 0  # Will be calculated after sorting
                }
                
                boosted_results.append(boosted_result)
                logger.debug(f"Legacy result {idx+1}: Final boost={final_boost}")
                
            except Exception as e:
                logger.error(f"Error processing legacy result {idx}: {str(e)}", exc_info=True)
                # Still add the result, but with no boost
                boosted_result = {
                    **result_data,
                    "boostFactors": {
                        "cite_boost": 0.0,
                        "recency_boost": 0.0,
                        "doctype_boost": 0.0,
                        "refereed_boost": 0.0
                    },
                    "finalBoost": 0.0,
                    "originalRank": idx + 1,
                    "rank": idx + 1,
                    "rankChange": 0
                }
                boosted_results.append(boosted_result)
        
        # Sort results by final boost score (descending)
        boosted_results.sort(key=lambda x: x.get("finalBoost", 0), reverse=True)
        
        # Re-rank and calculate rank changes
        for idx, result in enumerate(boosted_results, 1):
            original_rank = result["originalRank"]
            new_rank = idx
            result["rank"] = new_rank
            result["rankChange"] = original_rank - new_rank
        
        # Return the results
        return {
            "status": "success",
            "results": boosted_results
        }
        
    except Exception as e:
        logger.exception(f"Error in legacy boost experiment endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing boost experiment: {str(e)}") 