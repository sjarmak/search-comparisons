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
import httpx
import os
from urllib.parse import urljoin

from fastapi import APIRouter, HTTPException, Depends, Query, Request, BackgroundTasks
from pydantic import BaseModel, Field

from ...services import search_service
from ...services.ads_service import get_ads_results
from ...services.quepid_service import (
    evaluate_search_results, 
    load_case_with_judgments, 
    get_quepid_cases,
    get_case_judgments,
    get_book_judgments,
    extract_doc_id,
    calculate_ndcg,
    QUEPID_API_KEY,
    QuepidService
)
from ...core.config import settings
from ..models import (
    ErrorResponse, 
    QuepidEvaluationRequest,
    QuepidEvaluationResponse,
    QuepidEvaluationSourceResult,
    MetricResult,
    SearchResult,
    SearchRequest,
    BoostConfig
)
from ...services.boost_service import apply_all_boosts
from ...services.query_intent.service import QueryIntentService

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

# Initialize QuepidService
quepid_service = QuepidService()

# Initialize QueryIntentService
query_intent_service = QueryIntentService()


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


class ExperimentRequest(BaseModel):
    """Request model for experiment endpoints."""
    query: str
    num_results: int = 20
    use_cache: bool = False
    intent: Optional[str] = None


class ExperimentResponse(BaseModel):
    """Response model for experiment endpoints."""
    query: str
    transformed_query: str
    intent: str
    explanation: str
    results: List[Dict[str, Any]]
    metadata: Dict[str, Any]


def find_closest_query(query: str, available_queries: List[str]) -> Optional[str]:
    """
    Find the closest matching query in a list of available queries.
    
    Args:
        query: The query to match
        available_queries: List of available queries to match against
    
    Returns:
        Optional[str]: The closest matching query, or None if no matches
    """
    if not available_queries:
        return None
    
    # Normalize queries for comparison
    norm_query = query.lower().strip()
    norm_available = [q.lower().strip() for q in available_queries]
    
    # Check for exact match after normalization
    if norm_query in norm_available:
        idx = norm_available.index(norm_query)
        return available_queries[idx]
    
    # Check for queries that contain all words from the input query
    query_words = set(norm_query.split())
    
    matches = []
    for i, q in enumerate(norm_available):
        q_words = set(q.split())
        # Check if all words from the input query are in the available query
        if query_words.issubset(q_words):
            matches.append((i, len(q_words.intersection(query_words))))
        # Also check if the available query is a subset of the input query
        elif q_words.issubset(query_words):
            matches.append((i, len(q_words.intersection(query_words))))
    
    # Sort by number of matching words, descending
    matches.sort(key=lambda x: x[1], reverse=True)
    
    if matches:
        return available_queries[matches[0][0]]
    
    # If no matches found, try fuzzy matching
    from difflib import SequenceMatcher
    best_ratio = 0
    best_query = None
    
    for q in available_queries:
        ratio = SequenceMatcher(None, norm_query, q.lower()).ratio()
        if ratio > best_ratio and ratio > 0.8:  # Only consider matches with >80% similarity
            best_ratio = ratio
            best_query = q
    
    return best_query


@router.post("/boost", response_model=BoostResult)
async def boost_search_results(
    request: Request,
    boost_config: BoostConfig
) -> BoostResult:
    """
    Apply advanced boosting to search results.
    
    This endpoint implements the advanced boosting approach which applies
    multiple configurable boost factors to search results based on metadata
    such as citation count, publication year, document type, and refereed status.
    
    Args:
        request: The FastAPI request object
        boost_config: Configuration for the boosting experiment
    
    Returns:
        BoostResult: Original and boosted results with statistics
    
    Raises:
        HTTPException: If search or boosting fails
    """
    try:
        # Extract query and transformed query from request body
        data = await request.json()
        query = data.get("query", "")
        transformed_query = data.get("transformed_query", query)
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        logger.info(f"Starting boost experiment with query: {query}")
        
        # Get original results
        fields = ["title", "authors", "abstract", "doi", "year", "citation_count", "doctype", "property", "url"]
        original_results = await get_ads_results(query, fields)
        
        if not original_results:
            logger.warning(f"No results found for query: {query}")
            raise HTTPException(status_code=404, detail="No results found for query")
        
        logger.info(f"Retrieved {len(original_results)} results for boosting")
        
        # Process each result to add boost factors
        boosted_results = []
        current_year = datetime.now().year
        
        for idx, result in enumerate(original_results):
            try:
                # Initialize boost factors
                boost_factors = BoostFactors()
                
                # Apply citation boost if configured
                if boost_config.citation_boost > 0:
                    citation_count = getattr(result, "citation_count", 0)
                    if citation_count > 0:
                        cite_boost = boost_config.citation_boost * math.log1p(citation_count)
                        boost_factors.cite_boost = cite_boost
                        logger.debug(f"Applied citation boost: {cite_boost} (citation count: {citation_count})")
                
                # Apply recency boost if configured
                if boost_config.recency_boost > 0:
                    pub_year = getattr(result, "year", None)
                    if pub_year:
                        # Calculate age in months (assuming publication in January of the year)
                        current_year = datetime.now().year
                        current_month = datetime.now().month
                        age_months = (current_year - pub_year) * 12 + current_month
                        
                        if age_months > 0:
                            recency_boost = boost_config.recency_boost / age_months
                            boost_factors.recency_boost = recency_boost
                            logger.debug(f"Applied recency boost: {recency_boost} for {age_months} months old paper")
                
                # Apply document type boosts if configured
                doctype = getattr(result, "doctype", "") or ""
                doctype_str = doctype.lower() if isinstance(doctype, str) else ""
                
                if doctype_str in boost_config.doctype_boosts and boost_config.doctype_boosts[doctype_str] > 0:
                    doctype_boost = boost_config.doctype_boosts[doctype_str]
                    boost_factors.doctype_boost = doctype_boost
                    logger.debug(f"Applied doctype boost: {doctype_boost} for type {doctype_str}")
                
                # Calculate final boost as sum of individual boosts
                final_boost = (
                    boost_factors.cite_boost +
                    boost_factors.recency_boost +
                    boost_factors.doctype_boost +
                    boost_factors.refereed_boost
                )
                
                # Only sort by boost if any boosts were applied
                if final_boost > 0:
                    logger.debug(f"Result {idx+1}: Final boost={final_boost}")
                else:
                    logger.debug(f"Result {idx+1}: No boosts applied")
                
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
                except Exception as e:
                    logger.error(f"Error creating BoostedSearchResult: {str(e)}", exc_info=True)
                    # If all else fails, add a minimal result
                    boosted_result = BoostedSearchResult(
                        title=getattr(result, "title", "Unknown"),
                        url=getattr(result, "url", ""),
                        abstract=getattr(result, "abstract", ""),
                        authors=getattr(result, "authors", []),
                        source=getattr(result, "source", "ads"),
                        rank=idx + 1,
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
                        source=getattr(result, "source", "ads"),
                        rank=idx + 1,
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
                        source=getattr(result, "source", "ads"),
                        rank=idx + 1,
                        boost_factors=BoostFactors(),
                        final_boost=0.0,
                        original_rank=idx + 1,
                        rank_change=0
                    )
                    boosted_results.append(boosted_result)
        
        # Only sort by boost score if any boosts were applied
        has_boosts = any(r.final_boost > 0 for r in boosted_results)
        if has_boosts:
            boosted_results.sort(key=lambda x: x.final_boost, reverse=True)
            logger.info("Results sorted by boost score")
        else:
            logger.info("No boosts applied, maintaining original order")
        
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
            query=query,
            transformed_query=transformed_query,
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


@router.post("/quepid-evaluation", response_model=QuepidEvaluationResponse)
async def evaluate_search_with_quepid(
    request: QuepidEvaluationRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Evaluate search results against Quepid judgments.
    
    Args:
        request: The evaluation request containing query, case ID, and other parameters
        background_tasks: FastAPI background tasks handler
    
    Returns:
        Dict[str, Any]: Evaluation results including metrics and judged documents
    """
    try:
        logger.info(f"Quepid evaluation request: {request.dict()}")
        
        if not QUEPID_API_KEY:
            raise HTTPException(
                status_code=500,
                detail="Quepid API key not configured. Please set QUEPID_API_KEY environment variable."
            )
        
        # Get judged documents from Quepid
        judged_documents = await quepid_service.get_judged_documents(
            case_id=request.case_id, 
            query_id=request.query_id
        )
        
        # Get case data from Quepid
        case_data = await get_case_judgments(request.case_id)
        if not case_data:
            raise HTTPException(
                status_code=404,
                detail=f"Case {request.case_id} not found or no data returned from Quepid"
            )
        
        # Get judgments for the query
        judgments = {}
        for query_data in case_data.get('queries', []):
            if query_data['query'] == request.query:
                judgments = query_data.get('ratings', {})
                break
        
        if not judgments:
            available_queries = [q['query'] for q in case_data.get('queries', [])]
            raise HTTPException(
                status_code=404,
                detail=f"No judgments found for query '{request.query}' in case {request.case_id}. Available queries: {', '.join(available_queries)}"
            )
        
        # Format response
        source_result = QuepidEvaluationSourceResult(
            source="quepid",
            metrics=[],
            judged_retrieved=0,
            relevant_retrieved=0,
            results_count=0,
            results=[],
            config=BoostConfig(
                name="Base Results",
                citation_boost=0.0,
                recency_boost=0.0,
                doctype_boosts={}
            ),
            judged_titles=[]
        )

        return QuepidEvaluationResponse(
            query=request.query,
            case_id=request.case_id,
            case_name=case_data.get('case_name', f'Case {request.case_id}'),
            source_results=[source_result],
            total_judged=len(judgments),
            total_relevant=sum(1 for j in judgments.values() if 
                (isinstance(j, dict) and j.get('rating', 0) > 0) or 
                (isinstance(j, (int, float)) and j > 0)),
            available_queries=[q['query'] for q in case_data.get('queries', [])],
            judged_documents=judged_documents  # Add judged documents to response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Quepid evaluation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error evaluating search results: {str(e)}"
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


@back_compat_router.post("/boost-experiment-legacy")
async def boost_experiment_legacy(
    request: Request,
    boost_config: BoostConfig
):
    """
    Maintain backward compatibility with old boost-experiment API.
    This endpoint applies various boost factors to search results.
    """
    try:
        # Extract query and transformed query from request body
        data = await request.json()
        query = data.get("query", "")
        transformed_query = data.get("transformed_query", query)  # Use transformed query if provided
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Get field boosts and convert string values to float
        field_boosts = {}
        if boost_config.enable_field_boosts and boost_config.field_boosts:
            for field, weight in boost_config.field_boosts.items():
                if weight and weight != "":  # Only add if weight is not empty
                    try:
                        field_boosts[field] = float(weight)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid boost weight for field {field}: {weight}")
                        continue
        
        logger.info(f"Original query: {query}")
        logger.info(f"Transformed query: {transformed_query}")
        logger.info(f"Field boosts: {field_boosts}")
        
        # Get initial search results from ADS Solr
        search_url = "https://playground.adsabs.harvard.edu/dev/solr/collection1/select"
        params = {
            "q": transformed_query,  # Use the transformed query here
            "fl": "bibcode,title,author,year,abstract,citation_count,doctype",
            "rows": 1000,
            "wt": "json"
        }
        
        # Add authentication
        solr_password = os.environ.get("ADS_SOLR_PASSWORD", "")
        if not solr_password:
            raise HTTPException(status_code=500, detail="ADS_SOLR_PASSWORD not configured")
        
        logger.info(f"Making request to {search_url} with params: {params}")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    search_url, 
                    params=params, 
                    auth=httpx.BasicAuth('ads', solr_password)
                )
                response.raise_for_status()
                search_data = response.json()
            except httpx.HTTPError as e:
                logger.error(f"HTTP error occurred: {str(e)}")
                logger.error(f"Response status: {e.response.status_code if hasattr(e, 'response') else 'No response'}")
                logger.error(f"Response body: {e.response.text if hasattr(e, 'response') else 'No response'}")
                raise HTTPException(status_code=500, detail=f"Error fetching results: {str(e)}")
            except Exception as e:
                logger.error(f"Error making request: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error making request: {str(e)}")
            
        if not search_data.get("response", {}).get("docs"):
            return {
                "boosted_results": [],
                "metadata": {
                    "query": query,
                    "transformed_query": transformed_query,
                    "field_boosts": field_boosts,
                    "citation_boost": boost_config.cite_boost_weight if boost_config.enable_cite_boost else None,
                    "recency_boost": boost_config.recency_boost_weight if boost_config.enable_recency_boost else None,
                    "doctype_boost": boost_config.doctype_boost_weight if boost_config.enable_doctype_boost else None,
                    "combination_method": boost_config.combination_method
                }
            }
            
        # Process results with boosts
        boosted_results = []
        for doc in search_data["response"]["docs"]:
            boost_factors = {}
            
            # Apply citation boost if configured
            if boost_config.enable_cite_boost and boost_config.cite_boost_weight is not None:
                cite_count = doc.get("citation_count", 0)
                if cite_count > 0:
                    cite_boost = boost_config.cite_boost_weight * math.log1p(cite_count)
                    boost_factors['cite_boost'] = cite_boost
                    final_boost = cite_boost
                    logger.debug(f"Applied citation boost: {cite_boost} (citation count: {cite_count})")
            
            # Apply recency boost if configured
            if boost_config.enable_recency_boost and boost_config.recency_boost_weight is not None:
                year = doc.get("year")
                if year:
                    current_year = datetime.now().year
                    age = current_year - int(year)
                    if age >= 0:
                        recency_boost = boost_config.recency_boost_weight * (1 / (1 + age))
                        boost_factors['recency_boost'] = recency_boost
                        final_boost += recency_boost
                        logger.debug(f"Applied recency boost: {recency_boost} (age: {age})")
            
            # Apply document type boosts if configured
            for doctype, boost in boost_config.doctype_boosts.items():
                if boost > 0:
                    property_value = doc.get('property', [])
                    if isinstance(property_value, list) and doctype in property_value:
                        boost_factors[f'doctype_boost_{doctype}'] = boost
                        final_boost += boost
                        logger.debug(f"Applied {doctype} boost: {boost}")
            
            # Only sort by boost score if any boosts were applied
            if final_boost > 0:
                boosted_results.append({
                    "bibcode": doc["bibcode"],
                    "title": doc.get("title", ""),
                    "authors": doc.get("author", []),
                    "year": doc.get("year"),
                    "abstract": doc.get("abstract", ""),
                    "citation_count": doc.get("citation_count", 0),
                    "doctype": doc.get("doctype", ""),
                    "boost_score": final_boost,
                    "boost_factors": boost_factors
                })
        
        # Sort by boost score and return top 10
        boosted_results.sort(key=lambda x: x["boost_score"], reverse=True)
        
        return {
            "boosted_results": boosted_results[:10],
            "metadata": {
                "query": query,
                "transformed_query": transformed_query,
                "field_boosts": field_boosts,
                "citation_boost": boost_config.cite_boost_weight if boost_config.enable_cite_boost else None,
                "recency_boost": boost_config.recency_boost_weight if boost_config.enable_recency_boost else None,
                "doctype_boost": boost_config.doctype_boost_weight if boost_config.enable_doctype_boost else None,
                "combination_method": boost_config.combination_method
            }
        }
        
    except Exception as e:
        logger.error(f"Error in boost experiment: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=ExperimentResponse)
async def run_experiment(request: ExperimentRequest) -> Dict[str, Any]:
    """
    Run a search experiment using the query intent service.
    
    Args:
        request: Experiment request parameters
        
    Returns:
        Dict[str, Any]: Search results with metadata
    """
    try:
        # Transform query using LLM
        transformed_query = await query_intent_service.llm_service.interpret_query(request.query)
        
        # Search using ADS API
        results = await get_ads_results(
            query=transformed_query.transformed_query,
            intent=transformed_query.intent,
            num_results=request.num_results,
            use_cache=request.use_cache
        )
        
        # Prepare response
        response = {
            "query": request.query,
            "transformed_query": transformed_query.transformed_query,
            "intent": transformed_query.intent,
            "explanation": transformed_query.explanation,
            "results": [result.dict() for result in results],
            "metadata": {
                "num_results": len(results),
                "service": "ads",
                "cache_used": request.use_cache
            }
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error in experiment search: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error running experiment: {str(e)}"
        )


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Check the health of the experiment service.
    
    Returns:
        Dict[str, Any]: Health status information
    """
    try:
        # Check query intent service health
        health = await query_intent_service.health_check()
        
        return {
            "status": "healthy",
            "services": {
                "query_intent": health
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        } 