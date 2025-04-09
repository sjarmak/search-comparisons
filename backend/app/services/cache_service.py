"""
Cache service for storing and retrieving query transformations.

This module provides functionality to cache query transformations and their results
to improve performance and reduce redundant processing.
"""
from typing import Dict, Any, Optional
import logging
import time
from collections import OrderedDict

logger = logging.getLogger(__name__)

class CacheService:
    """
    Service for caching query transformations and results.
    
    Attributes:
        cache: OrderedDict storing cached items
        max_size: Maximum number of items to cache
        ttl: Time-to-live for cached items in seconds
    """
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600) -> None:
        """
        Initialize the cache service.
        
        Args:
            max_size: Maximum number of items to cache
            ttl: Time-to-live for cached items in seconds
        """
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl
        logger.info(f"Initialized CacheService with max_size={max_size}, ttl={ttl}")
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a value from the cache.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Cached value if found and not expired, None otherwise
        """
        if key not in self.cache:
            return None
            
        item = self.cache[key]
        if time.time() - item['timestamp'] > self.ttl:
            logger.debug(f"Cache entry expired for key: {key}")
            del self.cache[key]
            return None
            
        # Move to end of OrderedDict to mark as recently used
        self.cache.move_to_end(key)
        return item['value']
    
    def set(self, key: str, value: Dict[str, Any]) -> None:
        """
        Store a value in the cache.
        
        Args:
            key: Cache key to store
            value: Value to cache
        """
        # Remove oldest item if cache is full
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)
            
        self.cache[key] = {
            'value': value,
            'timestamp': time.time()
        }
        logger.debug(f"Cached value for key: {key}")
    
    def clear(self) -> None:
        """
        Clear all items from the cache.
        """
        self.cache.clear()
        logger.info("Cache cleared")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health status of the cache service.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        return {
            'status': 'ok',
            'size': len(self.cache),
            'max_size': self.max_size,
            'ttl': self.ttl
        } 