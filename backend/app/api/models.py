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


class BoostConfig(BaseModel):
    """
    Model representing boost configuration for search results.
    
    Attributes:
        name: Name of the boost configuration (optional)
        citation_boost: Boost factor for citation count
        min_citations: Minimum citation count for boosting (optional)
        recency_boost: Boost factor for publication recency
        reference_year: Reference year for recency calculations (optional)
        doctype_boosts: Dictionary mapping document types to boost factors
    """
    name: Optional[str] = "Default Boost Config"
    citation_boost: float = Field(default=0.0, ge=0.0)
    min_citations: Optional[int] = Field(default=1, ge=0)
    recency_boost: float = Field(default=0.0, ge=0.0)
    reference_year: Optional[int] = None
    doctype_boosts: Dict[str, float] = Field(default_factory=dict)


class BoostFactors(BaseModel):
    """Factors used to boost search results.
    
    Attributes:
        cite_boost: Boost from citation count
        recency_boost: Boost from publication year
        doctype_boost: Boost from document type
        refereed_boost: Boost from refereed status
    """
    cite_boost: float = 0.0
    recency_boost: float = 0.0
    doctype_boost: float = 0.0
    refereed_boost: float = 0.0


class BoostResult(BaseModel):
    """
    Model representing the boost factors and final boost score for a result.
    
    Attributes:
        boost_factors: Dictionary of individual boost factors applied
        final_boost: The final combined boost score
    """
    boost_factors: Dict[str, float]
    final_boost: float


class SearchRequestWithBoosts(SearchRequest):
    """
    Extended search request model that includes boost configuration.
    
    Attributes:
        boost_config: Configuration for various boost factors
    """
    boost_config: Optional[BoostConfig] = None


class SearchResult(BaseModel):
    """
    Model representing a single search result.
    
    Attributes:
        title: Title of the paper
        authors: List of authors
        abstract: Abstract text
        doi: Digital Object Identifier
        year: Publication year
        url: URL to the paper
        source: Source of the result
        rank: Rank in search results
        citation_count: Number of citations
        doctype: Document type
        property: List of properties
        boosted_score: Score after applying boosts
        original_score: Original score before boosts
        original_rank: Original rank before boosts
        rank_change: Change in rank after boosts
        boost_factors: Dictionary of applied boost factors
    """
    title: str
    authors: List[str]
    abstract: Optional[str] = None
    doi: Optional[str] = None
    year: Optional[int] = None
    url: Optional[str] = None
    source: str
    rank: int
    citation_count: Optional[int] = None
    doctype: Optional[str] = None
    property: Optional[List[str]] = None
    boosted_score: Optional[float] = None
    original_score: Optional[float] = None
    original_rank: Optional[int] = None
    rank_change: Optional[int] = None
    boost_factors: Optional[Dict[str, float]] = None


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


class SearchResponse(BaseModel):
    """
    Model representing the complete search response from the API.
    
    Attributes:
        query: The search query string
        results: List of search results from each source
        metrics: List of metric results for each source
        total_results: Total number of results returned
        transformed_query: The transformed query with field boosts (optional)
    """
    query: str
    results: List[SearchResult]
    metrics: Optional[List[MetricResult]] = None
    total_results: int
    transformed_query: Optional[str] = None


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
    Request model for Quepid evaluation.
    
    Attributes:
        query: The search query to evaluate
        case_id: The Quepid case ID to use for evaluation
        query_id: Optional ID of a specific query to filter by
        sources: List of search sources to evaluate
    """
    query: str
    case_id: int = Field(default=8862, description="The Quepid case ID to use for evaluation")
    query_id: Optional[int] = Field(default=None, description="Optional ID of a specific query to filter by")
    sources: List[str] = Field(default=["ads"], description="List of search sources to evaluate")


class QuepidEvaluationSourceResult(BaseModel):
    """
    Model representing evaluation results for a single source.
    
    Attributes:
        source: The search source name
        metrics: List of evaluation metrics
        judged_retrieved: Number of judged documents found in results
        relevant_retrieved: Number of relevant documents found in results
        results_count: Total number of results
        results: List of search results
        config: Boost configuration used
        judged_titles: List of judged documents with their titles
    """
    source: str
    metrics: List[MetricResult]
    judged_retrieved: int
    relevant_retrieved: int
    results_count: int
    results: List[SearchResult]
    config: BoostConfig
    judged_titles: List[Dict[str, Any]] = Field(default_factory=list)


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


class BoostedSearchResult(SearchResult):
    """Search result with boost information.
    
    Attributes:
        boost_factors: Individual boost factors applied
        final_boost: Combined boost score
        original_rank: Rank before boosting
        rank_change: Change in rank after boosting
    """
    boost_factors: BoostFactors
    final_boost: float
    original_rank: int
    rank_change: int
    source: str = "ads"
    rank: int = 1 