"""
Query transformation cache service.

This module provides caching functionality for transformed queries to avoid unnecessary LLM calls.
"""
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger(__name__)

class QueryCache:
    """
    Cache service for storing transformed queries.
    
    Attributes:
        cache_file: Path to the cache file
        cache: Dictionary storing cached queries
        max_age: Maximum age of cache entries in hours
    """
    
    def __init__(self, cache_file: str = "query_cache.json", max_age: int = 24) -> None:
        """
        Initialize the query cache.
        
        Args:
            cache_file: Path to the cache file
            max_age: Maximum age of cache entries in hours
        """
        self.cache_file = cache_file
        self.max_age = max_age
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Load cache from file if it exists."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded cache with {len(self.cache)} entries")
        except Exception as e:
            logger.error(f"Error loading cache: {str(e)}")
            self.cache = {}
    
    def _save_cache(self) -> None:
        """Save cache to file."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except Exception as e:
            logger.error(f"Error saving cache: {str(e)}")
    
    def _is_valid(self, timestamp: str) -> bool:
        """
        Check if a cache entry is still valid.
        
        Args:
            timestamp: ISO format timestamp string
            
        Returns:
            bool: True if the entry is still valid
        """
        try:
            entry_time = datetime.fromisoformat(timestamp)
            return datetime.now() - entry_time < timedelta(hours=self.max_age)
        except ValueError:
            return False
    
    def get(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Get a cached query transformation.
        
        Args:
            query: Original query string
            
        Returns:
            Optional[Dict[str, Any]]: Cached transformation if found and valid
        """
        if query in self.cache:
            entry = self.cache[query]
            if self._is_valid(entry['timestamp']):
                logger.info(f"Cache hit for query: {query}")
                return entry['result']
            else:
                logger.info(f"Cache entry expired for query: {query}")
                del self.cache[query]
                self._save_cache()
        return None
    
    def set(self, query: str, result: Dict[str, Any]) -> None:
        """
        Cache a query transformation.
        
        Args:
            query: Original query string
            result: Transformation result
        """
        self.cache[query] = {
            'timestamp': datetime.now().isoformat(),
            'result': result
        }
        self._save_cache()
        logger.info(f"Cached transformation for query: {query}")
    
    def clear(self) -> None:
        """Clear the cache."""
        self.cache = {}
        self._save_cache()
        logger.info("Cache cleared") 