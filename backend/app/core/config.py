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
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    Application settings.
    
    This class defines all configuration settings for the application,
    loaded from environment variables.
    """
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Academic Search Results Comparator"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Database Configuration
    DATABASE_URL: str = "sqlite:///./search_comparisons.db"
    
    # Cache Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 3600  # 1 hour
    
    # ADS Configuration
    ADS_API_TOKEN: str = "your_ads_api_token"
    ADS_API_URL: str = "https://api.adsabs.harvard.edu/v1/search/query"
    
    # LLM Configuration
    LLM_ENABLED: bool = True
    LLM_MODEL_NAME: str = "qwen2:7b"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 1000
    LLM_PROVIDER: str = "ollama"
    LLM_API_ENDPOINT: str = "http://localhost:11434/api/generate"
    LLM_PROMPT_TEMPLATE: Optional[str] = None
    
    # Query intent settings
    QUERY_INTENT_ENABLED: bool = True
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Rate Limiting
    RATE_LIMIT_DELAY: int = 2
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"  # Allow extra fields in environment variables
    )


# Create settings instance
settings = Settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT
)

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