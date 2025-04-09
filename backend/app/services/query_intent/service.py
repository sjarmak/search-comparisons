"""
Query Intent Service module for interpreting and transforming search queries.

This module provides functionality to interpret user queries and transform them
into effective ADS search queries using LLM-based intent detection.
"""
import logging
import os
from typing import Dict, Any, List, Optional
from .llm_service import LLMService
from .cache_service import CacheService
from app.services.solr_service import SolrService
from app.core.config import settings

# Configure logger for this module
logger = logging.getLogger(__name__)

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
        
        # Initialize Solr service with environment variables
        solr_password = os.environ.get("ADS_SOLR_PASSWORD")
        if not solr_password:
            logger.error("ADS_SOLR_PASSWORD not found in environment variables")
        else:
            logger.info("ADS_SOLR_PASSWORD found in environment variables")
        
        self.solr_service = SolrService()
        
        logger.info(f"Initialized QueryIntentService with LLM: {settings.LLM_ENABLED}")
    
    async def search(
        self,
        query: str,
        num_results: int = 20,
        use_cache: bool = False  # Added parameter to control caching
    ) -> Dict[str, Any]:
        """
        Perform a search using the query intent service.
        
        Args:
            query: Search query
            num_results: Maximum number of results to return
            use_cache: Whether to use cached results
        
        Returns:
            Dict[str, Any]: Search results with query interpretation in format:
                {
                    "original_query": str,
                    "transformed_query": str,
                    "intent": str,
                    "explanation": str,
                    "results": {
                        "numFound": int,
                        "docs": List[Dict]
                    }
                }
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
            
            # Search using Solr service
            results = await self.solr_service.search(
                query=transformed_query.transformed_query,
                intent=transformed_query.intent,
                rows=num_results
            )
            
            # Prepare response
            response = {
                "original_query": query,
                "transformed_query": transformed_query.transformed_query,
                "intent": transformed_query.intent,
                "explanation": transformed_query.explanation,
                "results": results  # Return the full results object
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
                "results": {
                    "numFound": 0,
                    "docs": []
                }
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
            
            # Check Solr service health
            solr_health = await self.solr_service.health_check()
            
            return {
                "status": "healthy",
                "llm": llm_health,
                "solr": solr_health
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e)
            } 