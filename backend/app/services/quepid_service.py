"""
Quepid API service module for the search-comparisons application.

This module handles interactions with the Quepid API, including retrieving
judgments, query document pairs, and other relevance assessment data for
search algorithm evaluation.
"""
import os
import logging
import json
import math
from typing import Dict, List, Any, Optional, Tuple, Union
from urllib.parse import urljoin

import httpx

from ..api.models import SearchResult
from ..utils.http import safe_api_request

# Setup logging
logger = logging.getLogger(__name__)

# API Constants
QUEPID_API_URL = os.environ.get("QUEPID_API_URL", "https://app.quepid.com/api/")
QUEPID_API_KEY = os.environ.get("QUEPID_API_KEY", "")
TIMEOUT_SECONDS = 30


class QuepidJudgment:
    """
    Represents a judgment from Quepid.
    
    Attributes:
        query_text: The search query text
        doc_id: The document ID
        rating: The relevance rating (typically 0-3 where 3 is most relevant)
        metadata: Additional metadata about the judgment
    """
    def __init__(
        self, 
        query_text: str, 
        doc_id: str, 
        rating: int,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.query_text = query_text
        self.doc_id = doc_id
        self.rating = rating
        self.metadata = metadata or {}


class QuepidCase:
    """
    Represents a case from Quepid containing multiple judged queries.
    
    Attributes:
        case_id: The Quepid case ID
        name: The name of the case
        queries: List of query texts in this case
        judgments: Dictionary mapping query text to list of judgments
    """
    def __init__(
        self, 
        case_id: int,
        name: str,
        queries: Optional[List[str]] = None,
        judgments: Optional[Dict[str, List[QuepidJudgment]]] = None
    ):
        self.case_id = case_id
        self.name = name
        self.queries = queries or []
        self.judgments = judgments or {}


async def get_quepid_cases() -> List[Dict[str, Any]]:
    """
    Retrieve a list of Quepid cases accessible to the current API key.
    
    Returns:
        List[Dict[str, Any]]: List of case data from Quepid
    """
    if not QUEPID_API_KEY:
        logger.error("QUEPID_API_KEY not found in environment")
        return []
    
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {QUEPID_API_KEY}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            url = urljoin(QUEPID_API_URL, "cases")
            logger.info(f"Getting cases from Quepid: {url}")
            
            response_data = await safe_api_request(
                client,
                "GET",
                url,
                headers=headers,
                timeout=TIMEOUT_SECONDS
            )
            
            return response_data
    
    except Exception as e:
        logger.error(f"Error retrieving cases from Quepid: {str(e)}")
        return []


async def get_case_judgments(case_id: int) -> Dict[str, Any]:
    """
    Retrieve judgments for a specific Quepid case.
    
    Args:
        case_id: The Quepid case ID to retrieve judgments for
    
    Returns:
        Dict[str, Any]: Judgment data from Quepid
    """
    if not QUEPID_API_KEY:
        logger.error("QUEPID_API_KEY not found in environment")
        return {}
    
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {QUEPID_API_KEY}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            url = urljoin(QUEPID_API_URL, f"export/ratings/{case_id}")
            logger.info(f"Getting judgments for case {case_id} from Quepid: {url}")
            
            response_data = await safe_api_request(
                client,
                "GET",
                url,
                headers=headers,
                timeout=TIMEOUT_SECONDS
            )
            
            return response_data
    
    except Exception as e:
        logger.error(f"Error retrieving judgments for case {case_id} from Quepid: {str(e)}")
        return {}


async def load_case_with_judgments(case_id: int) -> Optional[QuepidCase]:
    """
    Load a Quepid case with its judgments.
    
    Args:
        case_id: The ID of the Quepid case to load
    
    Returns:
        Optional[QuepidCase]: The loaded case with judgments, or None if not found
    """
    try:
        # Get case details
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{QUEPID_API_URL}cases/{case_id}",
                headers={"Authorization": f"Bearer {QUEPID_API_KEY}"}
            )
            response.raise_for_status()
            case_data = response.json()
            
            # Get judgments using the export endpoint
            judgments_response = await client.get(
                f"{QUEPID_API_URL}export/ratings/{case_id}",
                headers={"Authorization": f"Bearer {QUEPID_API_KEY}"}
            )
            judgments_response.raise_for_status()
            judgments_data = judgments_response.json()
            
            # Log available queries
            queries = set()
            for query_data in judgments_data.get('queries', []):
                queries.add(query_data['query'])
            logger.info(f"Available queries in case {case_id}: {sorted(list(queries))}")
            
            # Create case object with case_id as name if name not available
            case = QuepidCase(
                case_id=case_id,
                name=case_data.get("case_name", f"Case {case_id}"),
                queries=[]
            )
            
            # Process judgments
            for query_data in judgments_data.get('queries', []):
                query = query_data['query']
                if query not in case.queries:
                    case.queries.append(query)
                
                if query not in case.judgments:
                    case.judgments[query] = []
                
                # Process ratings for this query
                for doc_id, rating in query_data.get('ratings', {}).items():
                    case.judgments[query].append(QuepidJudgment(
                        query_text=query,
                        doc_id=doc_id,
                        rating=rating
                    ))
            
            return case
            
    except Exception as e:
        logger.error(f"Error loading Quepid case {case_id}: {str(e)}", exc_info=True)
        return None


async def evaluate_search_results(
    query: str,
    search_results: List[SearchResult],
    case_id: int
) -> Dict[str, Any]:
    """
    Evaluate search results against Quepid judgments.
    
    Args:
        query: The search query
        search_results: The list of search results to evaluate
        case_id: The Quepid case ID containing relevance judgments
    
    Returns:
        Dict[str, Any]: Evaluation metrics including nDCG, precision, etc.
    """
    # Load case with judgments
    case = await load_case_with_judgments(case_id)
    
    if not case:
        logger.error(f"Failed to load case {case_id}")
        return {"error": f"Failed to load case {case_id}"}
    
    # Find closest matching query if exact match not found
    if query not in case.judgments:
        closest_query = find_closest_query(query, case.queries)
        if not closest_query:
            logger.warning(f"No matching query found for '{query}' in case {case_id}")
            return {
                "error": f"No matching query found for '{query}' in case {case_id}",
                "available_queries": case.queries
            }
        
        logger.info(f"Using '{closest_query}' instead of '{query}'")
        query = closest_query
    
    judgments = case.judgments.get(query, [])
    if not judgments:
        logger.warning(f"No judgments found for query '{query}' in case {case_id}")
        return {"error": f"No judgments found for query '{query}' in case {case_id}"}
    
    # Create judgment dict for lookup
    judgment_dict = {j.doc_id: j.rating for j in judgments}
    max_rating = max(j.rating for j in judgments) if judgments else 3
    
    # Calculate metrics
    ndcg_values = {}
    precision_values = {}
    relevant_retrieved = 0
    
    for k in [5, 10, 20]:
        if len(search_results) >= k:
            ndcg_values[f"ndcg@{k}"] = calculate_ndcg(search_results[:k], judgment_dict, max_rating)
            
            # Calculate precision@k (relevant documents / k)
            relevant_at_k = sum(1 for r in search_results[:k] if extract_doc_id(r) in judgment_dict 
                               and judgment_dict[extract_doc_id(r)] > 0)
            precision_values[f"p@{k}"] = relevant_at_k / k
    
    # Overall statistics
    total_judged = len(judgments)
    total_relevant = sum(1 for j in judgments if j.rating > 0)
    
    # Count retrieved judged docs
    judged_retrieved = sum(1 for r in search_results if extract_doc_id(r) in judgment_dict)
    relevant_retrieved = sum(1 for r in search_results 
                           if extract_doc_id(r) in judgment_dict and judgment_dict[extract_doc_id(r)] > 0)
    
    # Calculate recall
    recall = relevant_retrieved / total_relevant if total_relevant > 0 else 0
    
    return {
        "query": query,
        "case_id": case_id,
        "case_name": case.name,
        "ndcg": ndcg_values,
        "precision": precision_values,
        "recall": recall,
        "judged_retrieved": judged_retrieved,
        "relevant_retrieved": relevant_retrieved,
        "total_judged": total_judged,
        "total_relevant": total_relevant,
        "results_count": len(search_results)
    }


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
        if query_words.issubset(q_words) or q_words.issubset(query_words):
            matches.append((i, len(q_words.intersection(query_words))))
    
    # Sort by number of matching words, descending
    matches.sort(key=lambda x: x[1], reverse=True)
    
    if matches:
        return available_queries[matches[0][0]]
    
    return None


def extract_doc_id(result: SearchResult) -> str:
    """
    Extract a document ID from a search result.
    
    Args:
        result: The search result
    
    Returns:
        str: The document ID
    """
    # Try DOI first, as it's the most precise identifier
    if result.doi:
        return result.doi
    
    # Next try bibcode if it's in the URL
    if result.url and "abs/" in result.url:
        parts = result.url.split("abs/")
        if len(parts) > 1:
            bibcode = parts[1].split("/")[0]
            return bibcode
    
    # Fall back to title as ID
    return result.title


def calculate_ndcg(
    results: List[SearchResult], 
    judgments: Dict[str, int], 
    max_rating: int = 3,
    use_exp: bool = True
) -> float:
    """
    Calculate Normalized Discounted Cumulative Gain (nDCG) for search results.
    
    Args:
        results: List of search results
        judgments: Dictionary mapping document IDs to relevance judgments
        max_rating: Maximum possible relevance judgment
        use_exp: Whether to use exponential gain (2^rel - 1) or linear gain
    
    Returns:
        float: nDCG score in range [0, 1]
    """
    if not results:
        return 0.0
    
    # Extract document IDs from results
    doc_ids = [extract_doc_id(r) for r in results]
    
    # Get relevance scores for each result
    rel_scores = []
    for doc_id in doc_ids:
        # Default score is 0 if not judged
        score = judgments.get(doc_id, 0)
        rel_scores.append(score)
    
    # Calculate DCG
    dcg = 0.0
    for i, score in enumerate(rel_scores):
        # Position is 0-indexed but formula uses 1-indexed
        pos = i + 1
        
        # Calculate gain: either 2^rel - 1 (exponential) or just rel (linear)
        gain = (2 ** score - 1) if use_exp else score
        
        # Apply discount factor: 1/log_2(pos + 1)
        discount = math.log2(pos + 1)
        dcg += gain / discount
    
    # Calculate ideal DCG (IDCG)
    # For this, we need to sort the judgments by score, descending
    ideal_scores = sorted([score for _, score in judgments.items()], reverse=True)
    
    # Truncate to same length as results list
    ideal_scores = ideal_scores[:len(results)]
    
    # Calculate IDCG
    idcg = 0.0
    for i, score in enumerate(ideal_scores):
        pos = i + 1
        gain = (2 ** score - 1) if use_exp else score
        discount = math.log2(pos + 1)
        idcg += gain / discount
    
    # Calculate nDCG
    if idcg == 0:
        return 0.0  # Avoid division by zero
    
    ndcg = dcg / idcg
    return ndcg 