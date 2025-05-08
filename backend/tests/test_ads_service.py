"""
Tests for the ADS service module of the search-comparisons application.

This module tests the functionality of the ADS service for retrieving search results
using the official ADS API.
"""
import os
import json
from typing import Dict, List, Any, Optional, cast
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
import pytest_asyncio
import httpx
from httpx import Response

from app.services.ads_service import (
    get_ads_api_key,
    get_ads_results,
    _get_default_fields,
    _get_sort_parameter,
    _map_fields_to_ads,
    _create_search_result
)
from app.api.models import SearchResult

if TYPE_CHECKING:
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from pytest_mock.plugin import MockerFixture


@pytest.fixture
def mock_ads_api_response() -> Dict[str, Any]:
    """Provide a sample ADS API response."""
    return {
        "responseHeader": {
            "status": 0,
            "QTime": 1933,
            "params": {
                "q": "star formation",
                "fl": "title,abstract,author,year,citation_count,bibcode",
                "rows": "5",
                "wt": "json"
            }
        },
        "response": {
            "numFound": 188889,
            "start": 0,
            "numFoundExact": True,
            "docs": [
                {
                    "bibcode": "2014ARA&A..52..415M",
                    "abstract": "Over the past two decades, an avalanche of new data from multiwavelength imaging...",
                    "author": ["Madau, Piero", "Dickinson, Mark"],
                    "title": ["Cosmic Star-Formation History"],
                    "year": "2014",
                    "citation_count": 3518
                },
                {
                    "bibcode": "2004RvMP...76..125M",
                    "abstract": "Understanding the formation of stars in galaxies is central to modern astrophysics...",
                    "author": ["Mac Low, Mordecai-Mark", "Klessen, Ralf S."],
                    "title": ["Control of star formation by supersonic turbulence"],
                    "year": "2004",
                    "citation_count": 1635
                }
            ]
        }
    }


def test_get_default_fields() -> None:
    """Test getting default fields for ADS API queries."""
    fields = _get_default_fields()
    
    # Check that all required fields are present
    assert "id" in fields
    assert "bibcode" in fields
    assert "title" in fields
    assert "author" in fields
    assert "year" in fields
    assert "citation_count" in fields
    assert "abstract" in fields
    assert "doi" in fields


def test_get_sort_parameter() -> None:
    """Test determining sort parameter based on intent."""
    # Test with explicit sort
    assert _get_sort_parameter(None, "date asc") == "date asc"
    
    # Test with influential intent
    assert _get_sort_parameter("influential", None) == "citation_count desc"
    assert _get_sort_parameter("highly cited", None) == "citation_count desc"
    assert _get_sort_parameter("popular", None) == "citation_count desc"
    
    # Test with recent intent
    assert _get_sort_parameter("recent", None) == "date desc"
    
    # Test with no intent or sort
    assert _get_sort_parameter(None, None) == "score desc"


def test_map_fields_to_ads() -> None:
    """Test mapping fields to ADS API fields."""
    # Test with basic fields
    fields = ["title", "authors", "abstract"]
    mapped = _map_fields_to_ads(fields)
    assert "title" in mapped
    assert "author" in mapped  # Note: authors -> author
    assert "abstract" in mapped
    assert "bibcode" in mapped  # Always included
    assert "id" in mapped  # Always included
    
    # Test with unknown fields
    fields = ["unknown_field"]
    mapped = _map_fields_to_ads(fields)
    assert "unknown_field" not in mapped
    assert "bibcode" in mapped
    assert "id" in mapped


def test_create_search_result() -> None:
    """Test creating a SearchResult from an ADS API document."""
    doc = {
        "bibcode": "2014ARA&A..52..415M",
        "title": ["Test Title"],
        "author": ["Author 1", "Author 2"],
        "abstract": "Test abstract",
        "year": "2014",
        "citation_count": 100
    }
    
    result = _create_search_result(doc, 1)
    
    assert result.title == "Test Title"
    assert result.author == ["Author 1", "Author 2"]
    assert result.abstract == "Test abstract"
    assert result.year == "2014"
    assert result.citation_count == 100
    assert result.rank == 1
    assert result.source == "ads"
    assert result.url == "https://ui.adsabs.harvard.edu/abs/2014ARA&A..52..415M/abstract"


@pytest.mark.asyncio
async def test_get_ads_results(mock_ads_api_response: Dict[str, Any]) -> None:
    """Test getting results from the ADS API."""
    query = "star formation"
    fields = ["title", "abstract", "authors", "year", "citation_count"]
    num_results = 5
    
    # Test with successful response
    with patch("app.services.ads_service.load_from_cache", return_value=None):
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value = Response(
                status_code=200,
                content=json.dumps(mock_ads_api_response).encode()
            )
            
            with patch("app.services.ads_service.save_to_cache"):
                results = await get_ads_results(query, fields, num_results)
                
                # Verify the results
                assert len(results) == 2
                assert results[0].title == "Cosmic Star-Formation History"
                assert results[0].source == "ads"
                assert results[0].year == "2014"
                assert results[0].citation_count == 3518
                
                # Verify the request was made correctly
                mock_get.assert_called_once()
                call_args = mock_get.call_args[1]
                assert "params" in call_args
                assert call_args["params"]["q"] == query
                assert "author" in call_args["params"]["fl"]
                assert call_args["params"]["rows"] == num_results
    
    # Test with failed response
    with patch("app.services.ads_service.load_from_cache", return_value=None):
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value = Response(status_code=400, content=b'{"error": "Bad Request"}')
            
            results = await get_ads_results(query, fields, num_results)
            assert results == []


@pytest.mark.asyncio
async def test_get_ads_results_with_intent(mock_ads_api_response: Dict[str, Any]) -> None:
    """Test getting results from the ADS API with different intents."""
    query = "star formation"
    fields = ["title", "abstract", "authors", "year", "citation_count"]
    num_results = 5
    
    # Test with influential intent
    with patch("app.services.ads_service.load_from_cache", return_value=None):
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value = Response(
                status_code=200,
                content=json.dumps(mock_ads_api_response).encode()
            )
            
            results = await get_ads_results(query, fields, num_results, intent="influential")
            
            # Verify sort parameter
            mock_get.assert_called_once()
            call_args = mock_get.call_args[1]
            assert call_args["params"]["sort"] == "citation_count desc"
    
    # Test with recent intent
    with patch("app.services.ads_service.load_from_cache", return_value=None):
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value = Response(
                status_code=200,
                content=json.dumps(mock_ads_api_response).encode()
            )
            
            results = await get_ads_results(query, fields, num_results, intent="recent")
            
            # Verify sort parameter
            mock_get.assert_called_once()
            call_args = mock_get.call_args[1]
            assert call_args["params"]["sort"] == "date desc"


@pytest.mark.asyncio
async def test_get_ads_results_with_cache(mock_ads_api_response: Dict[str, Any]) -> None:
    """Test getting results from the ADS API with caching."""
    query = "star formation"
    fields = ["title", "abstract", "authors", "year", "citation_count"]
    num_results = 5
    
    # Test with cached results
    cached_results = [
        SearchResult(
            title="Cached Result",
            author=["Test Author"],
            abstract="Test abstract",
            source="ads",
            rank=1
        )
    ]
    
    with patch("app.services.ads_service.load_from_cache", return_value=cached_results):
        with patch("httpx.AsyncClient.get") as mock_get:
            results = await get_ads_results(query, fields, num_results, use_cache=True)
            
            # Verify we got cached results
            assert results == cached_results
            mock_get.assert_not_called()


@pytest.mark.asyncio
async def test_get_ads_results_error_handling(
    mock_httpx_client: None,
    caplog: "LogCaptureFixture"
) -> None:
    """
    Test error handling for ADS API queries.
    
    This test verifies that the service handles various error cases
    gracefully and returns appropriate results.
    """
    # Test with invalid query
    query = "invalid:field:value"
    fields = ["title"]
    
    # Query ADS API
    results = await get_ads_results(query, fields)
    
    # Should return empty list for invalid query
    assert isinstance(results, list)
    assert len(results) == 0
    
    # Check logs for error message
    assert any("error" in record.levelname.lower() for record in caplog.records) 