"""
Cache Service module for query intent service.

This module provides functionality to cache query transformations and their results
using an LRU (Least Recently Used) eviction policy with TTL (Time To Live) support.
"""
import logging
import time
from collections import OrderedDict
from typing import Dict, Any, Optional

# Configure logger for this module
logger = logging.getLogger(__name__)

class CacheService:
    """
    Service for caching query transformations and their results.
    
    Attributes:
        max_size: Maximum number of items to store in the cache
        ttl: Time to live for cache entries in seconds
        cache: OrderedDict storing the cache entries
    """
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600) -> None:
        """
        Initialize the cache service.
        
        Args:
            max_size: Maximum number of items to store in the cache
            ttl: Time to live for cache entries in seconds
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        logger.info(f"Initialized CacheService with max_size={max_size}, ttl={ttl}")
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get a value from the cache.
        
        Args:
            key: The cache key to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: The cached value if found and not expired, None otherwise
        """
        if key not in self.cache:
            return None
            
        value, timestamp = self.cache[key]
        
        # Check if the entry has expired
        if time.time() - timestamp > self.ttl:
            logger.debug(f"Cache entry expired for key: {key}")
            del self.cache[key]
            return None
            
        # Move the entry to the end (most recently used)
        self.cache.move_to_end(key)
        return value
    
    def set(self, key: str, value: Dict[str, Any]) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: The cache key to set
            value: The value to cache
        """
        # Remove the key if it exists to update its position
        if key in self.cache:
            del self.cache[key]
        # Remove the oldest item if the cache is full
        elif len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            logger.debug(f"Cache full, removing oldest key: {oldest_key}")
            del self.cache[oldest_key]
            
        # Add the new entry with current timestamp
        self.cache[key] = (value, time.time())
        logger.debug(f"Cached entry for key: {key}")
    
    def clear(self) -> None:
        """Clear all entries from the cache."""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def size(self) -> int:
        """
        Get the current number of entries in the cache.
        
        Returns:
            int: Number of entries in the cache
        """
        return len(self.cache) 