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
    # Environment Configuration
    ENVIRONMENT: EnvironmentType = EnvironmentType.DEVELOPMENT
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Academic Search Results Comparator"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./search_comparisons.db")
    
    # If using PostgreSQL on Render, convert the URL if needed
    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            # If it's a Render PostgreSQL URL, ensure it's properly formatted
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql://", 1)
            return v
        return v
    
    # Cache Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 3600  # 1 hour
    
    # ADS Configuration
    ADS_API_TOKEN: str = "your_ads_api_token"
    ADS_API_URL: str = "https://api.adsabs.harvard.edu/v1/search/query"
    
    # LLM Configuration
    LLM_ENABLED: bool = os.getenv("LLM_ENABLED", "true").lower() == "true"
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "qwen2:7b")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1000"))
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")
    LLM_API_ENDPOINT: str = os.getenv("LLM_API_ENDPOINT", "http://localhost:11434/api/generate")
    LLM_PROMPT_TEMPLATE: Optional[str] = os.getenv("LLM_PROMPT_TEMPLATE")
    
    # Local LLM Configuration
    LOCAL_LLM_ENABLED: bool = os.getenv("LOCAL_LLM_ENABLED", "false").lower() == "true"
    LOCAL_LLM_HOST: str = os.getenv("LOCAL_LLM_HOST", "localhost")
    LOCAL_LLM_PORT: int = int(os.getenv("LOCAL_LLM_PORT", "11434"))
    LOCAL_LLM_TIMEOUT: int = int(os.getenv("LOCAL_LLM_TIMEOUT", "120"))
    
    # Query intent settings
    QUERY_INTENT_ENABLED: bool = True
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Rate Limiting
    RATE_LIMIT_DELAY: int = 2
    
    # Session settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")  # Change this in production
    
    # Search settings
    MAX_SEARCH_RESULTS: int = 100
    DEFAULT_SEARCH_RESULTS: int = 20
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"  # Allow extra fields in environment variables
    )


# Create settings instance
settings = Settings()

# Update DEBUG based on environment if not explicitly set
if os.getenv("DEBUG") is None:
    settings.DEBUG = settings.ENVIRONMENT in [EnvironmentType.LOCAL, EnvironmentType.DEVELOPMENT]

# Set log level in Python's logging module
log_level_map = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# Get logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(settings.LOG_LEVEL, logging.INFO)) 