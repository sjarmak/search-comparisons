"""
API data models for the search-comparisons application.

This module contains Pydantic models for request and response data structures.
These models define the structure of incoming requests and outgoing responses
for the API endpoints.
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """
    Model representing a search request submitted to the API.
    
    Attributes:
        query: The search query string
        sources: List of search engines to query
        metrics: List of metrics to use for result comparison
        fields: List of fields to include in the search
        max_results: Maximum number of results to return (optional)
        originalQuery: Original query before transformation (optional)
        useTransformedQuery: Flag indicating if the query is transformed (optional)
    """
    query: str
    sources: List[str]
    metrics: List[str]
    fields: List[str]
    max_results: Optional[int] = Field(default=20, ge=1, le=1000)
    originalQuery: Optional[str] = None
    useTransformedQuery: Optional[bool] = False


class SearchResult(BaseModel):
    """
    Model representing a single search result from any search engine.
    
    Attributes:
        title: Title of the result
        authors: List of authors (optional)
        abstract: Abstract or summary (optional)
        doi: Digital Object Identifier (optional)
        year: Publication year (optional)
        url: URL to the result (optional)
        source: Search engine that provided this result
        rank: Position in the results from the source
        citation_count: Number of citations (optional)
        doctype: Document type (optional)
        property: List of properties (optional)
        original_rank: Original rank before any boosting (optional)
        rank_change: Change in rank after boosting (optional)
        original_score: Original score before boosting (optional)
        boosted_score: Score after boosting (optional)
        boost_factors: Factors applied during boosting (optional)
    """
    title: str
    authors: Optional[List[str]] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    year: Optional[int] = None
    url: Optional[str] = None
    source: str
    rank: int
    citation_count: Optional[int] = None
    doctype: Optional[str] = None
    property: Optional[List[str]] = None
    
    # Fields for boost experiment
    original_rank: Optional[int] = None
    rank_change: Optional[int] = None
    original_score: Optional[float] = None
    boosted_score: Optional[float] = None
    boost_factors: Optional[Dict[str, float]] = None


class ErrorResponse(BaseModel):
    """
    Model representing an error response from the API.
    
    Attributes:
        status_code: HTTP status code
        message: Human-readable error message
        details: Additional error details (optional)
    """
    status_code: int
    message: str
    details: Optional[Any] = None


class QuepidJudgmentEntry(BaseModel):
    """
    Model representing a single judgment entry from Quepid.
    
    Attributes:
        doc_id: Document identifier (DOI, bibcode, etc.)
        rating: Relevance rating (typically 0-3)
        metadata: Additional metadata about the judgment (optional)
    """
    doc_id: str
    rating: int = Field(ge=0)
    metadata: Optional[Dict[str, Any]] = None


class QuepidEvaluationRequest(BaseModel):
    """
    Model representing a request to evaluate search results against Quepid judgments.
    
    Attributes:
        query: The search query string
        sources: List of search engines to query
        case_id: The Quepid case ID containing judgments
        fields: List of fields to include in the search (optional)
        max_results: Maximum number of results to return (optional)
    """
    query: str
    sources: List[str]
    case_id: int = Field(gt=0)
    fields: Optional[List[str]] = None
    max_results: Optional[int] = Field(default=20, ge=1, le=1000)


class MetricResult(BaseModel):
    """
    Model representing a single metric result.
    
    Attributes:
        name: The name of the metric (e.g., ndcg@10)
        value: The metric value
        description: A brief description of the metric (optional)
    """
    name: str
    value: float
    description: Optional[str] = None


class QuepidEvaluationSourceResult(BaseModel):
    """
    Model representing evaluation results for a single source.
    
    Attributes:
        source: The search engine source name
        metrics: List of metric results
        judged_retrieved: Number of judged documents retrieved
        relevant_retrieved: Number of relevant documents retrieved
        results_count: Total number of results returned
    """
    source: str
    metrics: List[MetricResult]
    judged_retrieved: int
    relevant_retrieved: int
    results_count: int


class QuepidEvaluationResponse(BaseModel):
    """
    Model representing the complete evaluation response.
    
    Attributes:
        query: The search query string
        case_id: The Quepid case ID
        case_name: The name of the Quepid case
        source_results: Results for each source
        total_judged: Total number of judged documents for the query
        total_relevant: Total number of relevant documents for the query
        available_queries: Other queries available in the case (optional)
    """
    query: str
    case_id: int
    case_name: str
    source_results: List[QuepidEvaluationSourceResult]
    total_judged: int
    total_relevant: int
    available_queries: Optional[List[str]] = None 