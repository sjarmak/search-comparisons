"""
API data models for the search-comparisons application.

This module contains Pydantic models for request and response data structures.
These models define the structure of incoming requests and outgoing responses
for the API endpoints.
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel


class SearchRequest(BaseModel):
    """
    Model representing a search request submitted to the API.
    
    Attributes:
        query: The search query string
        sources: List of search engines to query
        metrics: List of metrics to use for result comparison
        fields: List of fields to include in the search
    """
    query: str
    sources: List[str]
    metrics: List[str]
    fields: List[str]


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