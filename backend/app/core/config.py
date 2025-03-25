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

from pydantic import BaseSettings, validator, Field, AnyHttpUrl


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
        SCHOLAR_USE_PROXY: Flag to use proxy for Google Scholar
        SEMANTIC_SCHOLAR_API_KEY: API key for Semantic Scholar
        SEMANTIC_SCHOLAR_ENDPOINT: Semantic Scholar API endpoint
        WEB_OF_SCIENCE_API_KEY: API key for Web of Science
        WEB_OF_SCIENCE_ENDPOINT: Web of Science API endpoint
    """
    # Core application settings
    PROJECT_NAME: str = "Search Engine Comparator"
    PROJECT_DESCRIPTION: str = "API for comparing search engine results across multiple academic sources"
    VERSION: str = "1.0.0"
    ENVIRONMENT: EnvironmentType = EnvironmentType.LOCAL
    DEBUG: bool = False
    API_PREFIX: str = "/api"
    LOG_LEVEL: str = LogLevel.INFO
    
    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
    ]
    
    # Cache settings
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 3600  # 1 hour
    
    # API settings - ADS
    ADS_API_TOKEN: Optional[str] = None
    ADS_ENDPOINT: str = "https://api.adsabs.harvard.edu/v1"
    
    # API settings - Google Scholar
    SCHOLAR_USE_PROXY: bool = False
    
    # API settings - Semantic Scholar
    SEMANTIC_SCHOLAR_API_KEY: Optional[str] = None
    SEMANTIC_SCHOLAR_ENDPOINT: str = "https://api.semanticscholar.org/v1"
    
    # API settings - Web of Science
    WEB_OF_SCIENCE_API_KEY: Optional[str] = None
    WEB_OF_SCIENCE_ENDPOINT: str = "https://wos-api.clarivate.com/api/woslite/v1"
    
    @validator("ENVIRONMENT", pre=True)
    def validate_environment(cls, v: str) -> str:
        """
        Validate and normalize the environment string.
        
        Args:
            v: Environment string from environment variable
            
        Returns:
            str: Normalized environment string
            
        Raises:
            ValueError: If the environment is not valid
        """
        if isinstance(v, str):
            normalized = v.lower()
            if normalized in [e.value for e in EnvironmentType]:
                return normalized
            raise ValueError(f"Invalid environment: {v}")
        return v
    
    @validator("LOG_LEVEL", pre=True)
    def validate_log_level(cls, v: str) -> str:
        """
        Validate and normalize the log level string.
        
        Args:
            v: Log level string from environment variable
            
        Returns:
            str: Normalized log level string
            
        Raises:
            ValueError: If the log level is not valid
        """
        if isinstance(v, str):
            normalized = v.upper()
            if normalized in [level.value for level in LogLevel]:
                return normalized
            raise ValueError(f"Invalid log level: {v}")
        return v
    
    @validator("CORS_ORIGINS", pre=True)
    def validate_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """
        Parse CORS origins from string or list.
        
        Args:
            v: CORS origins as comma-separated string or list
            
        Returns:
            List[str]: List of validated origins
        """
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
        
    class Config:
        """
        Pydantic configuration for the Settings class.
        
        Defines loading behavior, environment variable prefixes, and more.
        """
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = ""  # No prefix for environment variables


# Determine which .env file to load based on environment
ENV = os.getenv("APP_ENVIRONMENT", "local").lower()
env_files = {
    "local": ".env.local",
    "development": ".env.dev",
    "staging": ".env.staging",
    "production": ".env.prod",
}

# Set environment-specific .env file if it exists
if ENV in env_files and Path(env_files[ENV]).exists():
    Settings.Config.env_file = env_files[ENV]

# Initialize settings
settings = Settings()

# Update DEBUG based on environment if not explicitly set
if os.getenv("DEBUG") is None:
    settings.DEBUG = settings.ENVIRONMENT in [EnvironmentType.LOCAL, EnvironmentType.DEVELOPMENT]

# Add production domains to CORS if in production
if settings.ENVIRONMENT == EnvironmentType.PRODUCTION:
    production_domains = [
        "https://search-comparisons.onrender.com",
        "https://search.sjarmak.ai"
    ]
    
    for domain in production_domains:
        if domain not in settings.CORS_ORIGINS:
            settings.CORS_ORIGINS.append(domain)

# Set log level in Python's logging module
log_level_map = {
    LogLevel.DEBUG.value: logging.DEBUG,
    LogLevel.INFO.value: logging.INFO,
    LogLevel.WARNING.value: logging.WARNING,
    LogLevel.ERROR.value: logging.ERROR,
    LogLevel.CRITICAL.value: logging.CRITICAL,
}

logging.basicConfig(
    level=log_level_map.get(settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
) 