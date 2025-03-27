"""
Tests for the ADS service module of the search-comparisons application.

This module tests the functionality of the ADS service including both
the API and Solr proxy methods for retrieving search results.
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
    get_bibcode_from_doi,
    query_ads_solr,
    query_ads_api,
    get_ads_results
)
from app.api.models import SearchResult


@pytest.fixture
def mock_ads_solr_response() -> Dict[str, Any]:
    """Provide a sample ADS Solr response."""
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


@pytest.fixture
def mock_ads_api_response() -> Dict[str, Any]:
    """Provide a sample ADS API response."""
    return {
        "responseHeader": {
            "status": 0,
            "QTime": 37,
            "params": {
                "q": "star formation",
                "fl": "title,abstract,author,year,citation_count,bibcode,doi",
                "rows": "5"
            }
        },
        "response": {
            "numFound": 188889,
            "start": 0,
            "docs": [
                {
                    "bibcode": "2014ARA&A..52..415M",
                    "doi": ["10.1146/annurev-astro-081811-125615"],
                    "abstract": "Over the past two decades, an avalanche of new data from multiwavelength imaging...",
                    "author": ["Madau, P.", "Dickinson, M."],
                    "title": ["Cosmic Star-Formation History"],
                    "year": "2014",
                    "citation_count": 3518
                },
                {
                    "bibcode": "2004RvMP...76..125M",
                    "doi": ["10.1103/RevModPhys.76.125"],
                    "abstract": "Understanding the formation of stars in galaxies is central to modern astrophysics...",
                    "author": ["Mac Low, M.", "Klessen, R.S."],
                    "title": ["Control of star formation by supersonic turbulence"],
                    "year": "2004",
                    "citation_count": 1635
                }
            ]
        }
    }


@pytest.mark.asyncio
async def test_get_ads_api_key() -> None:
    """Test retrieving the ADS API key from environment variables."""
    # Test with no environment variables set
    with patch.dict(os.environ, {}, clear=True):
        assert get_ads_api_key() == ""
    
    # Test with ADS_API_KEY set
    with patch.dict(os.environ, {"ADS_API_KEY": "test_key"}, clear=True):
        assert get_ads_api_key() == "test_key"
    
    # Test with ADS_API_TOKEN set (fallback)
    with patch.dict(os.environ, {"ADS_API_TOKEN": "test_token"}, clear=True):
        assert get_ads_api_key() == "test_token"
    
    # Test precedence (ADS_API_KEY has priority)
    with patch.dict(os.environ, {
        "ADS_API_KEY": "primary_key", 
        "ADS_API_TOKEN": "fallback_token"
    }, clear=True):
        assert get_ads_api_key() == "primary_key"


@pytest.mark.asyncio
async def test_get_bibcode_from_doi() -> None:
    """Test retrieving a bibcode from a DOI."""
    # Test with empty DOI
    assert await get_bibcode_from_doi("") is None
    
    # Test with valid DOI but missing API key
    with patch("app.services.ads_service.get_ads_api_key", return_value=""):
        assert await get_bibcode_from_doi("10.1146/annurev-astro-081811-125615") is None
    
    # Test with valid DOI and API key but failed request
    with patch("app.services.ads_service.get_ads_api_key", return_value="test_key"):
        with patch("app.services.ads_service.safe_api_request", side_effect=Exception("API error")):
            assert await get_bibcode_from_doi("10.1146/annurev-astro-081811-125615") is None
    
    # Test with valid DOI, API key, and successful request but no results
    with patch("app.services.ads_service.get_ads_api_key", return_value="test_key"):
        with patch("app.services.ads_service.safe_api_request", return_value={"response": {"docs": []}}):
            assert await get_bibcode_from_doi("10.1146/nonexistent") is None
    
    # Test with valid DOI, API key, and successful request with results
    with patch("app.services.ads_service.get_ads_api_key", return_value="test_key"):
        mock_response = {"response": {"docs": [{"bibcode": "2014ARA&A..52..415M"}]}}
        with patch("app.services.ads_service.safe_api_request", return_value=mock_response):
            assert await get_bibcode_from_doi("10.1146/annurev-astro-081811-125615") == "2014ARA&A..52..415M"


@pytest.mark.asyncio
async def test_query_ads_solr(mock_ads_solr_response: Dict[str, Any]) -> None:
    """Test querying the ADS Solr instance directly."""
    query = "star formation"
    fields = ["title", "abstract", "authors", "year", "citation_count"]
    num_results = 5
    
    # Test with successful response
    with patch("app.services.ads_service.load_from_cache", return_value=None):
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value = Response(
                status_code=200,
                content=json.dumps(mock_ads_solr_response).encode()
            )
            
            with patch("app.services.ads_service.save_to_cache"):
                results = await query_ads_solr(query, fields, num_results)
                
                # Verify the results
                assert len(results) == 2
                assert results[0].title == "Cosmic Star-Formation History"
                assert results[0].source == "ads"
                assert results[0].year == 2014
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
            
            results = await query_ads_solr(query, fields, num_results)
            assert results == []
    
    # Test with exception
    with patch("app.services.ads_service.load_from_cache", return_value=None):
        with patch("httpx.AsyncClient.get", side_effect=Exception("Connection error")):
            results = await query_ads_solr(query, fields, num_results)
            assert results == []
    
    # Test with cache hit
    cached_results = [
        SearchResult(title="Cached Result", source="ads", rank=1)
    ]
    with patch("app.services.ads_service.load_from_cache", return_value=cached_results):
        results = await query_ads_solr(query, fields, num_results)
        assert results == cached_results


@pytest.mark.asyncio
async def test_query_ads_api(mock_ads_api_response: Dict[str, Any]) -> None:
    """Test querying the ADS API."""
    query = "star formation"
    fields = ["title", "abstract", "authors", "year", "citation_count"]
    num_results = 5
    
    # Test with no API key
    with patch("app.services.ads_service.get_ads_api_key", return_value=""):
        results = await query_ads_api(query, fields, num_results)
        assert results == []
    
    # Test with API key and successful response
    with patch("app.services.ads_service.get_ads_api_key", return_value="test_key"):
        with patch("app.services.ads_service.load_from_cache", return_value=None):
            with patch("app.services.ads_service.safe_api_request", return_value=mock_ads_api_response):
                with patch("app.services.ads_service.save_to_cache"):
                    results = await query_ads_api(query, fields, num_results)
                    
                    # Verify the results
                    assert len(results) == 2
                    assert results[0].title == "Cosmic Star-Formation History"
                    assert results[0].source == "ads"
                    assert results[0].year == 2014
                    assert results[0].citation_count == 3518
                    assert results[0].doi == "10.1146/annurev-astro-081811-125615"
    
    # Test with API key but failed request
    with patch("app.services.ads_service.get_ads_api_key", return_value="test_key"):
        with patch("app.services.ads_service.load_from_cache", return_value=None):
            with patch("app.services.ads_service.safe_api_request", side_effect=Exception("API error")):
                results = await query_ads_api(query, fields, num_results)
                assert results == []
    
    # Test with API key and successful request but no results
    with patch("app.services.ads_service.get_ads_api_key", return_value="test_key"):
        with patch("app.services.ads_service.load_from_cache", return_value=None):
            empty_response = {"response": {"docs": []}}
            with patch("app.services.ads_service.safe_api_request", return_value=empty_response):
                results = await query_ads_api(query, fields, num_results)
                assert results == []
    
    # Test with cache hit
    cached_results = [
        SearchResult(title="Cached API Result", source="ads", rank=1)
    ]
    with patch("app.services.ads_service.get_ads_api_key", return_value="test_key"):
        with patch("app.services.ads_service.load_from_cache", return_value=cached_results):
            results = await query_ads_api(query, fields, num_results)
            assert results == cached_results


@pytest.mark.asyncio
async def test_get_ads_results() -> None:
    """Test the main get_ads_results function with different query methods."""
    query = "star formation"
    fields = ["title", "abstract", "authors", "year", "citation_count"]
    num_results = 5
    
    solr_results = [SearchResult(title="Solr Result", source="ads", rank=1)]
    api_results = [SearchResult(title="API Result", source="ads", rank=1)]
    
    # Test solr_only mode
    with patch.dict(os.environ, {"ADS_QUERY_METHOD": "solr_only"}):
        with patch("app.services.ads_service.ADS_QUERY_METHOD", "solr_only"):
            with patch("app.services.ads_service.query_ads_solr", return_value=solr_results) as mock_solr:
                with patch("app.services.ads_service.query_ads_api") as mock_api:
                    results = await get_ads_results(query, fields, num_results)
                    assert results == solr_results
                    mock_api.assert_not_called()
                    mock_solr.assert_called_once()
    
    # Test api_only mode
    with patch.dict(os.environ, {"ADS_QUERY_METHOD": "api_only"}):
        with patch("app.services.ads_service.ADS_QUERY_METHOD", "api_only"):
            with patch("app.services.ads_service.query_ads_api", return_value=api_results) as mock_api:
                with patch("app.services.ads_service.query_ads_solr") as mock_solr:
                    results = await get_ads_results(query, fields, num_results)
                    assert results == api_results
                    mock_solr.assert_not_called()
                    mock_api.assert_called_once()
    
    # Test solr_first mode (successful Solr query)
    with patch.dict(os.environ, {"ADS_QUERY_METHOD": "solr_first"}):
        with patch("app.services.ads_service.ADS_QUERY_METHOD", "solr_first"):
            with patch("app.services.ads_service.query_ads_solr", return_value=solr_results) as mock_solr:
                with patch("app.services.ads_service.query_ads_api") as mock_api:
                    results = await get_ads_results(query, fields, num_results)
                    assert results == solr_results
                    mock_api.assert_not_called()
                    mock_solr.assert_called_once()
    
    # Test solr_first mode (failed Solr query, fallback to API)
    with patch.dict(os.environ, {"ADS_QUERY_METHOD": "solr_first"}):
        with patch("app.services.ads_service.ADS_QUERY_METHOD", "solr_first"):
            with patch("app.services.ads_service.query_ads_solr", return_value=[]) as mock_solr:
                with patch("app.services.ads_service.query_ads_api", return_value=api_results) as mock_api:
                    results = await get_ads_results(query, fields, num_results)
                    assert results == api_results
                    mock_solr.assert_called_once()
                    mock_api.assert_called_once()
    
    # Test solr_first mode (exception in Solr query, fallback to API)
    with patch.dict(os.environ, {"ADS_QUERY_METHOD": "solr_first"}):
        with patch("app.services.ads_service.ADS_QUERY_METHOD", "solr_first"):
            with patch("app.services.ads_service.query_ads_solr", side_effect=Exception("Solr error")) as mock_solr:
                with patch("app.services.ads_service.query_ads_api", return_value=api_results) as mock_api:
                    results = await get_ads_results(query, fields, num_results)
                    assert results == api_results
                    mock_solr.assert_called_once()
                    mock_api.assert_called_once() 