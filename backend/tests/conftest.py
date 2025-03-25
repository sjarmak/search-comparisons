"""
Pytest configuration file for search-comparisons application.

This module defines fixtures and configuration for pytest tests.
"""
import os
import sys
import logging
from typing import Dict, Any, Generator, TYPE_CHECKING
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app as main_app
from app.api.models import SearchResult

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture
def app() -> FastAPI:
    """
    FastAPI test application.
    
    Returns:
        FastAPI: Application instance for testing
    """
    # Set test environment variables
    os.environ["APP_ENVIRONMENT"] = "test"
    os.environ["DEBUG"] = "true"
    
    # Configure test-specific settings here
    return main_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """
    TestClient fixture.
    
    Provides a FastAPI TestClient for testing API endpoints.
    
    Args:
        app: FastAPI application fixture
        
    Returns:
        TestClient: FastAPI test client
    """
    return TestClient(app)


@pytest.fixture
def mock_settings(monkeypatch: "MonkeyPatch") -> Dict[str, Any]:
    """
    Apply test settings to the application.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
        
    Returns:
        Dict[str, Any]: Dictionary of applied test settings
    """
    test_settings = {
        "DEBUG": True,
        "ENVIRONMENT": "test",
        "LOG_LEVEL": "INFO",
        "CACHE_ENABLED": False,
        "ADS_API_TOKEN": "test_token",
        "SEMANTIC_SCHOLAR_API_KEY": "test_key",
        "WEB_OF_SCIENCE_API_KEY": "test_key",
    }
    
    # Apply settings
    for key, value in test_settings.items():
        monkeypatch.setenv(key, str(value))
        
    return test_settings


@pytest.fixture
def sample_paper_data() -> Dict[str, Any]:
    """
    Provide sample paper data for testing.
    
    Returns:
        Dict[str, Any]: Sample paper data dictionary
    """
    return {
        "title": "Test Paper Title",
        "authors": ["Author One", "Author Two"],
        "abstract": "This is a test abstract for a paper that doesn't exist.",
        "doi": "10.1234/test.12345",
        "year": 2023,
        "url": "https://example.com/paper/12345",
        "source": "test",
        "rank": 1,
        "citation_count": 42,
        "doctype": "article",
        "property": ["refereed"]
    }


@pytest.fixture
def sample_search_result(sample_paper_data: Dict[str, Any]) -> SearchResult:
    """
    Provide a sample SearchResult object for testing.
    
    Args:
        sample_paper_data: Sample paper data dictionary
        
    Returns:
        SearchResult: A populated SearchResult object
    """
    return SearchResult(**sample_paper_data)


@pytest.fixture
def mock_ads_response() -> Dict[str, Any]:
    """
    Provide a mock ADS API response.
    
    Returns:
        Dict[str, Any]: Mocked ADS API response
    """
    return {
        "response": {
            "numFound": 1,
            "start": 0,
            "docs": [
                {
                    "title": ["Test ADS Paper"],
                    "author": ["Smith, J.", "Jones, A."],
                    "abstract": "This is a test abstract from ADS.",
                    "doi": ["10.1234/ads.12345"],
                    "year": 2023,
                    "bibcode": "2023ADS...123..456S",
                    "citation_count": 10,
                    "doctype": "article",
                    "property": ["refereed"]
                }
            ]
        }
    }


@pytest.fixture
def mock_semantic_scholar_response() -> Dict[str, Any]:
    """
    Provide a mock Semantic Scholar API response.
    
    Returns:
        Dict[str, Any]: Mocked Semantic Scholar API response
    """
    return {
        "total": 1,
        "offset": 0,
        "data": [
            {
                "paperId": "12345abcde",
                "title": "Test Semantic Scholar Paper",
                "authors": [
                    {"name": "Smith, John"},
                    {"name": "Jones, Alice"}
                ],
                "abstract": "This is a test abstract from Semantic Scholar.",
                "doi": "10.1234/ss.12345",
                "year": 2023,
                "url": "https://semanticscholar.org/paper/12345abcde",
                "citationCount": 15,
                "publicationTypes": ["JournalArticle"]
            }
        ]
    }


@pytest.fixture
def clean_env(monkeypatch: "MonkeyPatch") -> Generator[None, None, None]:
    """
    Provide a clean environment for tests.
    
    Temporarily unsets environment variables that might interfere with tests.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
        
    Yields:
        None
    """
    # List of environment variables to clean
    env_vars = [
        "ADS_API_TOKEN",
        "SEMANTIC_SCHOLAR_API_KEY",
        "WEB_OF_SCIENCE_API_KEY",
        "CACHE_ENABLED",
        "DEBUG"
    ]
    
    # Store original values
    original_values = {}
    for var in env_vars:
        original_values[var] = os.environ.get(var)
        monkeypatch.delenv(var, raising=False)
    
    yield
    
    # Restore original values
    for var, value in original_values.items():
        if value is not None:
            monkeypatch.setenv(var, value)