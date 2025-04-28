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
import re
from typing import Dict, List, Any, Optional, Tuple, Union
from urllib.parse import urljoin

import httpx
from fastapi import HTTPException

from ..api.models import SearchResult
from ..utils.http import safe_api_request

# Setup logging
logger = logging.getLogger(__name__)

# API Constants
QUEPID_API_URL = os.environ.get("QUEPID_API_URL", "https://quepid.herokuapp.com/api/")
QUEPID_API_KEY = os.environ.get("QUEPID_API_KEY", "c707e3d691c5f681f31a05b4c68bb09fc402597f325213a2e6411beebf199405")  # Hardcoded API key
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


class QuepidService:
    """
    Service for interacting with the Quepid API.
    
    This service handles all communication with the Quepid API, including
    retrieving cases, judgments, and evaluating search results.
    """
    
    def __init__(self):
        """
        Initialize the QuepidService with API configuration.
        """
        self.api_url = QUEPID_API_URL  # Use the URL from environment variable
        self.api_key = QUEPID_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def _make_request(self, endpoint: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a request to the Quepid API.
        
        Args:
            endpoint: The API endpoint to call
            method: HTTP method to use (GET, POST, etc.)
            data: Optional data to send with the request
        
        Returns:
            Dict[str, Any]: The JSON response from the API
        
        Raises:
            HTTPException: If the API request fails
        """
        url = urljoin(self.api_url, endpoint.lstrip('/'))  # Use urljoin to handle paths properly
        try:
            logger.info(f"Making request to Quepid API: {url}")
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Quepid API error: {str(e)}")
            raise HTTPException(
                status_code=e.response.status_code if hasattr(e, 'response') else 500,
                detail=f"Quepid API error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error making request to Quepid: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error making request to Quepid: {str(e)}"
            )
    
    async def get_judged_documents(self, case_id: int, query_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get judged documents from a Quepid case.
        
        Args:
            case_id: The ID of the Quepid case
            query_id: Optional ID of a specific query to filter by
        
        Returns:
            List[Dict[str, Any]]: List of judged documents with their metadata
        
        Raises:
            HTTPException: If the API request fails
        """
        try:
            # First get the case data to find the book ID
            case_url = f"cases/{case_id}"
            case_data = await self._make_request(case_url)
            
            if not case_data:
                logger.warning(f"No case data found for case {case_id}")
                return []
            
            book_id = case_data.get('book_id')
            if not book_id:
                logger.warning(f"No book ID found for case {case_id}")
                return []
            
            # Get the book judgments
            book_url = f"books/{book_id}/judgements"
            book_data = await self._make_request(book_url)
            
            if not book_data:
                logger.warning(f"No book data found for book {book_id}")
                return []
            
            # Get the latest snapshot for the case
            snapshot_url = f"cases/{case_id}/snapshots/latest"
            snapshot_data = await self._make_request(snapshot_url)
            
            if not snapshot_data:
                logger.warning(f"No snapshot data found for case {case_id}")
                return []
            
            # Extract documents and their ratings
            documents = []
            for query in snapshot_data.get('queries', []):
                # If query_id is provided, only process that query
                if query_id is not None and query.get('query_id') != query_id:
                    continue
                    
                query_text = query.get('query', '')
                ratings = query.get('ratings', {})
                
                for doc_id, rating in ratings.items():
                    # Get document details from the book judgments
                    doc = next((d for d in book_data.get('judgements', []) if d.get('doc_id') == doc_id), None)
                    if doc:
                        documents.append({
                            'id': doc_id,
                            'title': doc.get('title', ''),
                            'authors': doc.get('authors', []),
                            'year': doc.get('year'),
                            'citation_count': doc.get('citation_count', 0),
                            'doc_type': doc.get('doc_type', ''),
                            'bibcode': doc.get('bibcode', ''),
                            'judgment': rating if isinstance(rating, (int, float)) else rating.get('rating', 0),
                            'query': query_text
                        })
            
            logger.info(f"Found {len(documents)} judged documents for case {case_id}")
            return documents
            
        except Exception as e:
            logger.error(f"Error getting judged documents: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error getting judged documents: {str(e)}"
            )
    
    async def load_case_with_judgments(self, case_id: int) -> Optional[QuepidCase]:
        """Load a case and its judgments from Quepid."""
        return await load_case_with_judgments(case_id)
    
    async def evaluate_search_results(
        self,
        query: str,
        search_results: List[SearchResult],
        case_id: int
    ) -> Dict[str, Any]:
        """Evaluate search results against Quepid judgments."""
        return await evaluate_search_results(query, search_results, case_id)
    
    def find_closest_query(self, query: str, available_queries: List[str]) -> Optional[str]:
        """Find the closest matching query from the available queries."""
        return find_closest_query(query, available_queries)
    
    def calculate_ndcg(self, ratings: List[int], k: int) -> float:
        """Calculate Normalized Discounted Cumulative Gain."""
        return calculate_ndcg(ratings, k)
    
    def extract_doc_id(self, result: Union[str, SearchResult, Dict[str, Any]]) -> Optional[str]:
        """Extract document ID from a search result or URL."""
        return extract_doc_id(result)


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
            
            response = await client.get(
                url,
                headers=headers,
                timeout=TIMEOUT_SECONDS
            )
            
            # Log the response status and headers
            logger.info(f"Quepid API response status: {response.status_code}")
            logger.info(f"Quepid API response headers: {response.headers}")
            
            if response.status_code != 200:
                logger.error(f"Quepid API returned status {response.status_code}: {response.text}")
                return {}
            
            response_data = response.json()
            logger.info(f"Quepid API response data: {response_data}")
            
            if not response_data:
                logger.error("Empty response from Quepid API")
                return {}
            
            return response_data
    
    except httpx.HTTPError as e:
        logger.error(f"HTTP error retrieving judgments for case {case_id} from Quepid: {str(e)}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Quepid API response: {str(e)}")
        return {}
    except Exception as e:
        logger.error(f"Error retrieving judgments for case {case_id} from Quepid: {str(e)}")
        return {}


async def load_case_with_judgments(case_id: int) -> Optional[QuepidCase]:
    """Load a case and its judgments from Quepid."""
    try:
        # Get case details using the cases endpoint
        case_url = urljoin(QUEPID_API_URL, f"cases/{case_id}")
        logger.debug(f"Getting case details from: {case_url}")
        
        headers = {
            "Authorization": f"Bearer {QUEPID_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        async with httpx.AsyncClient() as client:
            # Get case details
            case_response = await client.get(
                case_url,
                headers=headers,
                timeout=TIMEOUT_SECONDS
            )
            case_response.raise_for_status()
            case_data = case_response.json()
            
            if not case_data:
                logger.error(f"No case data found for case {case_id}")
                return None

            # Get judgments using the export endpoint
            export_url = urljoin(QUEPID_API_URL, f"export/ratings/{case_id}")
            logger.debug(f"Getting judgments from export endpoint: {export_url}")
            
            judgments_response = await client.get(
                export_url,
                headers=headers,
                timeout=TIMEOUT_SECONDS
            )
            judgments_response.raise_for_status()
            judgments_data = judgments_response.json()
            
            if judgments_data and 'queries' in judgments_data:
                logger.debug(f"Received judgments data: {judgments_data}")
                
                # Process judgments into the expected format
                processed_judgments = {}
                
                # Handle the new response format
                for query_data in judgments_data['queries']:
                    query = query_data['query']
                    ratings = query_data.get('ratings', {})
                    
                    if query not in processed_judgments:
                        processed_judgments[query] = {}
                    
                    # Add all ratings for this query
                    processed_judgments[query].update(ratings)

                logger.debug(f"Available queries with judgments: {list(processed_judgments.keys())}")
                logger.debug(f"Number of judgments per query: {[(q, len(j)) for q, j in processed_judgments.items()]}")
                
                case = QuepidCase(
                    case_id=case_data["case_id"],
                    name=case_data["case_name"],
                    queries=[try_data.get("args", {}).get("q", [""])[0] for try_data in case_data.get("tries", [])],
                    judgments=processed_judgments
                )
                
                logger.debug(f"Created case object with name: {case.name}")
                logger.debug(f"Case has {len(case.queries)} queries")
                logger.debug(f"Case has judgments for queries: {list(case.judgments.keys())}")
                logger.debug(f"Judgments for 'weak lensing': {case.judgments.get('weak lensing', {})}")
                
                return case

            logger.error(f"No judgments found for case {case_id}")
            return None

    except httpx.HTTPError as e:
        logger.error(f"HTTP error loading case {case_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error loading case {case_id} with judgments: {str(e)}")
        logger.exception("Full traceback:")
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
    
    judgments = case.judgments.get(query, {})
    if not judgments:
        logger.warning(f"No judgments found for query '{query}' in case {case_id}")
        return {"error": f"No judgments found for query '{query}' in case {case_id}"}
    
    # Log all available queries and their judgment counts
    logger.info("=== AVAILABLE QUERIES ===")
    for q in case.queries:
        count = len(case.judgments.get(q, {}))
        logger.info(f"Query: '{q}' - {count} judgments")
    
    # Create judgment dict for lookup by ID and title
    judgment_dict = {}
    title_dict = {}  # Dictionary to store titles by ID
    judged_titles = []  # List to store all judged documents
    
    logger.info("\n=== JUDGED DOCUMENTS ===")
    logger.info(f"Total judged documents: {len(judgments)}")
    for doc_id, judgment_data in judgments.items():
        # Handle both dictionary and direct rating values
        if isinstance(judgment_data, dict):
            rating = judgment_data.get('rating', 0)
            title = judgment_data.get('title', '')
        else:
            rating = float(judgment_data)  # Convert to float in case it's a string
            title = ''
        
        # Store the judgment by its ID
        judgment_dict[doc_id] = rating
        # Store the title
        title_dict[doc_id] = title
        judged_titles.append({
            "id": doc_id,
            "title": title,
            "rating": rating
        })
        logger.info(f"\nJudged document:")
        logger.info(f"ID: '{doc_id}'")
        logger.info(f"Title: '{title}'")
        logger.info(f"Rating: {rating}")
        logger.info("---")
    
    # Process search results
    processed_results = []
    logger.info("\n=== ADS SEARCH RESULTS ===")
    for result in search_results:
        # Extract document ID from the result
        doc_id = extract_doc_id(result)
        logger.info(f"\nADS result:")
        logger.info(f"Title: '{result.title}'")
        logger.info(f"Extracted ID: '{doc_id}'")
        
        # Extract authors safely
        authors = []
        if hasattr(result, 'authors'):
            authors = result.authors
        elif hasattr(result, 'author'):
            authors = result.author
        elif hasattr(result, 'author_list'):
            authors = result.author_list
        
        # Check if this result matches any judgments by ID or title
        rating = judgment_dict.get(doc_id, 0)
        has_judgment = doc_id in judgment_dict
        
        # If no match by ID, try matching by title
        if not has_judgment:
            # Handle both SearchResult objects and dictionaries
            if isinstance(result, dict):
                title = result.get('title', '')
            else:
                title = getattr(result, 'title', '')
            
            # Ensure title is a string
            if isinstance(title, list):
                title = title[0] if title else ''
            
            if title:
                clean_title = str(title).lower().strip()
                logger.info(f"Attempting title match with: '{clean_title}'")
                for j in judged_titles:
                    judged_title = str(j['title']).lower().strip()
                    logger.info(f"Comparing with judged title: '{judged_title}'")
                    if judged_title == clean_title:
                        rating = j['rating']
                        has_judgment = True
                        logger.info(f"MATCH FOUND BY TITLE! Rating: {rating}")
                        logger.info(f"Matched with judged document: '{j['title']}'")
                        break
        
        if has_judgment:
            logger.info(f"MATCH FOUND! Rating: {rating}")
            logger.info(f"Matched with judged document ID: '{doc_id}'")
        else:
            logger.info("No match found in judgments")
            logger.info("Available judgment IDs: " + ", ".join(judgment_dict.keys()))
            logger.info("Available judgment titles: " + ", ".join(title_dict.values()))
        logger.info("---")
        
        # Extract title safely
        if isinstance(result, dict):
            title = result.get('title', '')
        else:
            title = getattr(result, 'title', '')
        
        # Ensure title is a string
        if isinstance(title, list):
            title = title[0] if title else ''
        
        processed_results.append({
            "title": title,
            "authors": authors,
            "year": getattr(result, 'year', ''),
            "citation_count": getattr(result, 'citation_count', 0),
            "doc_type": getattr(result, 'doctype', ''),
            "url": getattr(result, 'url', ''),
            "doc_id": doc_id,
            "rating": rating,
            "has_judgment": has_judgment,
            "judgment": rating
        })
    
    # Calculate metrics
    metrics = {}
    for k in [5, 10, 20]:
        if len(processed_results) >= k:
            # Calculate nDCG
            ratings = [r["rating"] for r in processed_results[:k]]
            metrics[f"ndcg@{k}"] = calculate_ndcg(ratings, k)
            
            # Calculate precision@k (relevant documents / k)
            relevant_at_k = sum(1 for r in processed_results[:k] if r["rating"] > 0)
            metrics[f"p@{k}"] = relevant_at_k / k
    
    # Overall statistics
    total_judged = len(judgments)
    total_relevant = sum(1 for j in judgments.values() if (isinstance(j, dict) and j.get('rating', 0) > 0) or (isinstance(j, (int, float)) and j > 0))
    
    # Count retrieved judged docs
    judged_retrieved = sum(1 for r in processed_results if r["has_judgment"])
    relevant_retrieved = sum(1 for r in processed_results if r["rating"] > 0)
    
    # Calculate recall
    recall = relevant_retrieved / total_relevant if total_relevant > 0 else 0
    
    logger.info("\n=== EVALUATION SUMMARY ===")
    logger.info(f"Total judged documents: {total_judged}")
    logger.info(f"Total relevant documents: {total_relevant}")
    logger.info(f"Judged documents found: {judged_retrieved}")
    logger.info(f"Relevant documents found: {relevant_retrieved}")
    logger.info(f"Recall: {recall}")
    
    return {
        "query": query,
        "case_id": case_id,
        "case_name": case.name,
        "metrics": metrics,
        "recall": recall,
        "judged_retrieved": judged_retrieved,
        "relevant_retrieved": relevant_retrieved,
        "total_judged": total_judged,
        "total_relevant": total_relevant,
        "results_count": len(search_results),
        "judged_titles": judged_titles,  # Include all judged documents
        "source_results": [{
            "source": "ads",
            "metrics": [
                {"name": f"ndcg@{k}", "value": metrics.get(f"ndcg@{k}", 0), 
                 "description": f"Normalized Discounted Cumulative Gain at {k}"}
                for k in [5, 10, 20]
            ] + [
                {"name": f"p@{k}", "value": metrics.get(f"p@{k}", 0),
                 "description": f"Precision at {k}"}
                for k in [5, 10, 20]
            ] + [
                {"name": "recall", "value": recall,
                 "description": "Recall (relevant retrieved / total relevant)"}
            ],
            "judged_retrieved": judged_retrieved,
            "relevant_retrieved": relevant_retrieved,
            "results_count": len(search_results),
            "results": processed_results[:10]  # Include top 10 results
        }]
    }


def find_closest_query(query: str, available_queries: List[str]) -> Optional[str]:
    """
    Find the closest matching query from the available queries.
    
    Args:
        query: The query to match.
        available_queries: List of available queries to match against.
        
    Returns:
        The closest matching query, or None if no match is found.
    """
    # Normalize the input query
    normalized_query = query.lower().strip()
    normalized_available = [q.lower().strip() for q in available_queries]
    
    # Check for exact match after normalization
    if normalized_query in normalized_available:
        idx = normalized_available.index(normalized_query)
        return available_queries[idx]
    
    # Get sets of words from input query and available queries
    query_words = set(normalized_query.split())
    
    # First try to find queries that contain all words from the input query
    matches = []
    for i, available_query in enumerate(normalized_available):
        available_words = set(available_query.split())
        # Check if all words from input query are in available query
        if query_words.issubset(available_words):
            matches.append((i, len(query_words)))
    
    if matches:
        # Sort by number of matching words (descending)
        matches.sort(key=lambda x: x[1], reverse=True)
        return available_queries[matches[0][0]]
    
    # Then try to find queries whose words are a subset of the input query
    matches = []
    for i, available_query in enumerate(normalized_available):
        available_words = set(available_query.split())
        # Check if all words from available query are in input query
        if available_words.issubset(query_words):
            matches.append((i, len(available_words)))
    
    if matches:
        # Sort by number of matching words (descending)
        matches.sort(key=lambda x: x[1], reverse=True)
        return available_queries[matches[0][0]]
    
    # If no matches found, try fuzzy matching
    from difflib import SequenceMatcher
    
    best_match = None
    best_ratio = 0
    
    for i, available_query in enumerate(normalized_available):
        ratio = SequenceMatcher(None, normalized_query, available_query).ratio()
        if ratio > best_ratio and ratio >= 0.8:  # 80% similarity threshold
            best_ratio = ratio
            best_match = available_queries[i]
    
    return best_match


def extract_numeric_id(bibcode: str) -> str:
    """
    Extract numeric ID from a bibcode.
    
    Args:
        bibcode: The bibcode to extract from
        
    Returns:
        str: The numeric ID
    """
    # Extract all digits from the bibcode
    numeric_id = ''.join(filter(str.isdigit, bibcode))
    logger.debug(f"Converted bibcode {bibcode} to numeric ID {numeric_id}")
    return numeric_id


def extract_doc_id(result: Union[str, SearchResult, Dict[str, Any]]) -> Optional[str]:
    """
    Extract document ID from a search result or URL.
    
    Args:
        result: A SearchResult object, dictionary, URL string, or any object containing result data
        
    Returns:
        Optional[str]: The document ID if found, None otherwise
    """
    # Handle string URLs directly
    if isinstance(result, str):
        url = result
    else:
        # Get URL from result object
        url = getattr(result, 'url', None) if hasattr(result, 'url') else result.get('url')
    
    if not url:
        return None
        
    # Match bibcode format: YYYY[Journal..][Vol..].[Page..]
    match = re.search(r'abs/(\d{4}.*?)/abstract', url)
    if not match:
        return None
    
    bibcode = match.group(1)
    # Convert bibcode to numeric ID by extracting all digits
    numeric_id = ''.join(filter(str.isdigit, bibcode))
    logger.debug(f"Converted bibcode {bibcode} to numeric ID {numeric_id}")
    return numeric_id


def calculate_ndcg(ratings: List[int], k: int) -> float:
    """
    Calculate Normalized Discounted Cumulative Gain.
    
    Args:
        ratings: List of relevance ratings
        k: Number of results to consider
    
    Returns:
        float: nDCG score between 0 and 1
    """
    if not ratings:
        return 0.0
    
    # Calculate DCG
    dcg = sum((2**r - 1) / math.log2(i + 2) for i, r in enumerate(ratings[:k]))
    
    # Calculate IDCG (using sorted ratings in descending order)
    ideal_ratings = sorted(ratings, reverse=True)[:k]
    idcg = sum((2**r - 1) / math.log2(i + 2) for i, r in enumerate(ideal_ratings))
    
    # Calculate nDCG
    if idcg == 0:
        return 0.0
    
    return dcg / idcg 


async def get_book_judgments(book_id: int) -> Dict[str, Any]:
    """
    Retrieve all judgments for a specific book from Quepid.
    
    Args:
        book_id: The ID of the book to retrieve judgments for
    
    Returns:
        Dict[str, Any]: Dictionary containing judgment data, or empty dict if error occurs
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
            
            url = urljoin(QUEPID_API_URL, f"books/{book_id}/judgements")
            logger.info(f"Getting judgments for book {book_id} from Quepid: {url}")
            
            response_data = await safe_api_request(
                client,
                "GET",
                url,
                headers=headers,
                timeout=TIMEOUT_SECONDS
            )
            
            return response_data or {}
    
    except Exception as e:
        logger.error(f"Error retrieving judgments for book {book_id} from Quepid: {str(e)}")
        return {} 