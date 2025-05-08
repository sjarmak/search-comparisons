"""
Query Intent Service module for interpreting and transforming search queries.

This module provides functionality to interpret user queries and transform them
into effective ADS search queries using LLM-based intent detection.
"""
import logging
from typing import Dict, Any, List, Optional, TypedDict

from .llm_service import LLMService
from .cache_service import CacheService
from app.core.config import settings
from app.services.ads_service import get_ads_results

# Configure logger for this module
logger = logging.getLogger(__name__)

class QueryInterpretation(TypedDict):
    """Type definition for query interpretation results."""
    transformed_query: str
    intent: str
    explanation: str

class SearchResponse(TypedDict):
    """Type definition for search response."""
    original_query: str
    transformed_query: str
    intent: str
    explanation: str
    results: List[Any]

class QueryIntentService:
    """Service for interpreting and transforming search queries."""
    
    def __init__(self, llm_service: Optional[LLMService] = None, cache_service: Optional[CacheService] = None):
        """
        Initialize the QueryIntentService.
        
        Args:
            llm_service: Optional LLM service for query interpretation
            cache_service: Optional cache service for storing query transformations
        """
        # Initialize LLM service if not provided
        self.llm_service = llm_service or LLMService.from_config()
        
        # Initialize cache service if not provided
        self.cache_service = cache_service or CacheService()
        
        logger.info(f"Initialized QueryIntentService with LLM: {settings.LLM_ENABLED}")
    
    async def search(
        self,
        query: str,
        num_results: int = 20,
        use_cache: bool = False
    ) -> SearchResponse:
        """
        Perform a search using the query intent service.
        
        Args:
            query: Search query
            num_results: Maximum number of results to return
            use_cache: Whether to use cached results
        
        Returns:
            SearchResponse: Search results with query interpretation
        """
        try:
            # Check cache first if enabled
            if use_cache:
                cached_results = self.cache_service.get(query)
                if cached_results:
                    logger.info(f"Retrieved cached results for query: {query}")
                    return cached_results
            
            # Transform query using LLM
            transformed_query = await self.llm_service.interpret_query(query)
            
            # Search using ADS API
            results = await get_ads_results(
                query=transformed_query.transformed_query,
                intent=transformed_query.intent,
                num_results=num_results,
                use_cache=use_cache
            )
            
            # Prepare response
            response: SearchResponse = {
                "original_query": query,
                "transformed_query": transformed_query.transformed_query,
                "intent": transformed_query.intent,
                "explanation": transformed_query.explanation,
                "results": results
            }
            
            # Cache results if enabled
            if use_cache and results:
                self.cache_service.set(query, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in search: {str(e)}")
            return {
                "original_query": query,
                "transformed_query": query,  # Fallback to original query
                "intent": "unknown",
                "explanation": f"Error processing query: {str(e)}",
                "results": []
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the query intent service.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            # Check LLM service health
            llm_health = await self.llm_service.health_check()
            
            return {
                "status": "healthy",
                "llm": llm_health
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e)
            } 