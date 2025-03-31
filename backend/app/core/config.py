"""
Configuration module for the search-comparisons application.

This module defines application settings and environment-specific configurations
using Pydantic for validation and type checking.
"""
import os
import logging
from enum import Enum
from typing import List, Dict, Any, Optional, Set, Union
from pathlib import Path

from pydantic import validator, Field, AnyHttpUrl
from pydantic_settings import BaseSettings


class EnvironmentType(str, Enum):
    """
    Environment types for the application.
    
    Enum for different deployment environments.
    """
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """
    Logging levels supported by the application.
    
    Maps string representations to Python's logging levels.
    """
    DEBUG = "DEBUG"
    INFO = "INFO" 
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Uses Pydantic for validation and provides default values.
    All settings can be overridden with environment variables.
    
    Attributes:
        PROJECT_NAME: Name of the application
        PROJECT_DESCRIPTION: Description of the application
        VERSION: Application version
        ENVIRONMENT: Current environment (local, development, staging, production)
        DEBUG: Debug mode flag
        API_PREFIX: API endpoint prefix
        LOG_LEVEL: Application logging level
        CORS_ORIGINS: Allowed origins for CORS
        CACHE_ENABLED: Flag to enable/disable caching
        CACHE_TTL_SECONDS: Cache time-to-live in seconds
        ADS_API_TOKEN: API token for ADS API
        ADS_ENDPOINT: ADS API endpoint
        ADS_API_KEY: API key for ADS API
        ADS_SOLR_PROXY_URL: URL for ADS Solr proxy
        ADS_SOLR_PASSWORD: Password for ADS Solr proxy
        ADS_QUERY_METHOD: Method to use for ADS queries
        SCHOLAR_USE_PROXY: Flag to use proxy for Google Scholar
        SEMANTIC_SCHOLAR_API_KEY: API key for Semantic Scholar
        SEMANTIC_SCHOLAR_ENDPOINT: Semantic Scholar API endpoint
        WEB_OF_SCIENCE_API_KEY: API key for Web of Science
        WEB_OF_SCIENCE_ENDPOINT: Web of Science API endpoint
        QUEPID_API_KEY: API key for Quepid
        QUEPID_API_URL: Base URL for Quepid API
        CACHE_EXPIRY: Cache expiration time in seconds
        CACHE_DIR: Directory for cache files
        NUM_RESULTS: Default number of results to return
        RATE_LIMIT_DELAY: Delay between API calls in seconds
    """
    # Core application settings
    PROJECT_NAME: str = "Search Engine Comparator"
    PROJECT_DESCRIPTION: str = "API for comparing search engine results across multiple academic sources"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "local"
    DEBUG: bool = False
    API_PREFIX: str = "/api"
    LOG_LEVEL: str = "INFO"
    
    # CORS settings - not used anymore (hardcoded in main.py)
    # Only kept for backward compatibility
    CORS_ORIGINS: str = "*"
    
    # Cache settings
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 3600  # 1 hour
    CACHE_EXPIRY: int = 3600  # 1 hour
    CACHE_DIR: str = "./cache"
    
    # API settings - ADS
    ADS_API_TOKEN: Optional[str] = None
    ADS_API_KEY: Optional[str] = None
    ADS_ENDPOINT: str = "https://api.adsabs.harvard.edu/v1"
    ADS_SOLR_PROXY_URL: Optional[str] = None
    ADS_SOLR_PASSWORD: Optional[str] = None
    ADS_QUERY_METHOD: str = "solr_first"
    
    # API settings - Google Scholar
    SCHOLAR_USE_PROXY: bool = False
    
    # API settings - Semantic Scholar
    SEMANTIC_SCHOLAR_API_KEY: Optional[str] = None
    SEMANTIC_SCHOLAR_ENDPOINT: str = "https://api.semanticscholar.org/v1"
    
    # API settings - Web of Science
    WEB_OF_SCIENCE_API_KEY: Optional[str] = None
    WEB_OF_SCIENCE_ENDPOINT: str = "https://wos-api.clarivate.com/api/woslite/v1"
    
    # API settings - Quepid
    QUEPID_API_KEY: Optional[str] = None
    QUEPID_API_URL: str = "https://app.quepid.com/api/"
    
    # General settings
    NUM_RESULTS: int = 10
    RATE_LIMIT_DELAY: int = 2
    
    class Config:
        """
        Pydantic configuration for the Settings class.
        
        Defines loading behavior, environment variable prefixes, and more.
        """
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"


# Initialize settings
settings = Settings()

# Update DEBUG based on environment if not explicitly set
if os.getenv("DEBUG") is None:
    settings.DEBUG = settings.ENVIRONMENT.lower() in ["local", "development"]

# Set log level in Python's logging module
log_level_map = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

logging.basicConfig(
    level=log_level_map.get(settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
) 