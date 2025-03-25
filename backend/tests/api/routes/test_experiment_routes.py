"""
Tests for experiment routes.

This module contains tests for the experiment-related API endpoints.
"""
import json
from typing import Dict, Any, List, Optional, TYPE_CHECKING
import pytest
from fastapi.testclient import TestClient

from app.api.models import SearchResult, SearchRequest
from app.api.routes.experiment_routes import (
    apply_experimental_boost,
    calculate_boost_stats,
    BoostConfig,
    BoostResult
)

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


@pytest.fixture
def sample_search_results() -> List[SearchResult]:
    """
    Create sample search results for testing.
    
    Returns:
        List[SearchResult]: A list of mock search results
    """
    return [
        SearchResult(
            title="First Paper",
            authors=["Smith, J.", "Jones, A."],
            abstract="This is an abstract for the first paper",
            doi="10.1234/abc123",
            year=2020,
            url="https://example.com/paper1",
            source="ads",
            rank=1,
            citation_count=25,
            doctype="article",
            property=["refereed"]
        ),
        SearchResult(
            title="Second Paper",
            authors=["Brown, K.", "Lee, M."],
            abstract="This is an abstract for the second paper",
            doi="10.1234/def456",
            year=2018,
            url="https://example.com/paper2",
            source="ads",
            rank=2,
            citation_count=50,
            doctype="article",
            property=["refereed"]
        ),
        SearchResult(
            title="Third Paper",
            authors=["Wilson, T.", "Davis, C."],
            abstract="This is an abstract for the third paper",
            doi="10.1234/ghi789",
            year=2022,
            url="https://example.com/paper3",
            source="ads",
            rank=3,
            citation_count=10,
            doctype="article",
            property=["refereed"]
        ),
    ]


def test_apply_experimental_boost(sample_search_results: List[SearchResult]) -> None:
    """
    Test the application of experimental boosting to search results.
    
    Tests that boost factors are correctly applied to search results 
    and that rankings are appropriately modified.
    
    Args:
        sample_search_results: Fixture providing sample search results
    """
    # Define boost fields and weights for testing
    boost_fields = ["citation_count", "year"]
    boost_weights = {"citation_count": 0.2, "year": 0.5}
    max_boost = 2.0
    
    # Apply boosting
    boosted_results = apply_experimental_boost(
        sample_search_results,
        boost_fields,
        boost_weights,
        max_boost
    )
    
    # Verify boosted results are properly formed
    assert len(boosted_results) == len(sample_search_results)
    
    # Verify all results have been boosted
    for result in boosted_results:
        assert hasattr(result, "boosted_score")
        assert hasattr(result, "boost_factors")
        assert hasattr(result, "original_rank")
        assert hasattr(result, "rank_change")
    
    # Verify ordering has changed based on boosting
    # Paper with rank 2 should now be ranked higher due to citation count
    assert any(r.original_rank != r.rank for r in boosted_results)
    
    # Find paper with high citation count
    high_citation_paper = next(r for r in boosted_results if r.original_rank == 2)
    
    # It should have moved up in ranking due to high citation count
    assert high_citation_paper.rank < high_citation_paper.original_rank


def test_calculate_boost_stats(sample_search_results: List[SearchResult]) -> None:
    """
    Test the calculation of boosting statistics.
    
    Tests that boost statistics are correctly computed from original
    and boosted search results.
    
    Args:
        sample_search_results: Fixture providing sample search results
    """
    # Create a copy of results to simulate boosting effects
    boosted_results = [
        SearchResult(
            title=r.title,
            authors=r.authors,
            abstract=r.abstract,
            doi=r.doi,
            year=r.year,
            url=r.url,
            source=r.source,
            rank=3 if r.rank == 1 else (1 if r.rank == 2 else 2),  # Swap ranks
            citation_count=r.citation_count,
            doctype=r.doctype,
            property=r.property,
            # Add boost-specific fields
            original_rank=r.rank,
            rank_change=r.rank - (3 if r.rank == 1 else (1 if r.rank == 2 else 2)),
            original_score=1.0,
            boosted_score=1.5,
            boost_factors={"citation_count": 1.2, "year": 1.3}
        )
        for r in sample_search_results
    ]
    
    # Calculate stats
    stats = calculate_boost_stats(sample_search_results, boosted_results)
    
    # Verify stats have expected keys
    expected_keys = [
        "count", "moved_up", "moved_down", "unchanged", 
        "avg_rank_change", "max_rank_increase", "max_rank_decrease"
    ]
    for key in expected_keys:
        assert key in stats
    
    # Verify values make sense for our test data
    assert stats["count"] == 3
    assert stats["moved_up"] > 0  # At least one result moved up
    assert stats["moved_down"] > 0  # At least one result moved down
    assert stats["avg_rank_change"] > 0  # There should be movement


@pytest.mark.asyncio
async def test_boost_search_results_endpoint(
    client: TestClient,
    mocker: "MockerFixture"
) -> None:
    """
    Test the boost search results endpoint.
    
    Tests that the /api/experiments/boost endpoint correctly processes
    boost requests and returns the expected response.
    
    Args:
        client: TestClient fixture
        mocker: Pytest mocker fixture
    """
    # Create sample results for mocking
    sample_results = [
        SearchResult(
            title="Paper Title",
            authors=["Author One", "Author Two"],
            abstract="Sample abstract",
            doi="10.1234/sample",
            year=2021,
            url="https://example.com/sample",
            source="ads",
            rank=1,
            citation_count=30,
            doctype="article",
            property=["refereed"]
        )
    ]
    
    # Mock ADS results
    mocker.patch(
        "app.services.ads_service.get_ads_results", 
        return_value=sample_results
    )
    
    # Define test request
    request_data = {
        "query": "quantum mechanics",
        "boost_fields": ["citation_count", "year"],
        "boost_weights": {"citation_count": 0.2, "year": 0.4},
        "max_boost": 1.8
    }
    
    # Make request to endpoint
    response = client.post("/api/experiments/boost", json=request_data)
    
    # Check response
    assert response.status_code == 200
    
    result = response.json()
    assert "original_results" in result
    assert "boosted_results" in result
    assert "boost_stats" in result
    
    # Verify the original results match what we mocked
    assert len(result["original_results"]) == len(sample_results)
    assert result["original_results"][0]["title"] == sample_results[0].title
    
    # Verify the boosted results contain expected fields
    assert "boosted_score" in result["boosted_results"][0]
    assert "original_rank" in result["boosted_results"][0]
    assert "rank_change" in result["boosted_results"][0]


@pytest.mark.asyncio
async def test_ab_test_endpoint(
    client: TestClient,
    mocker: "MockerFixture"
) -> None:
    """
    Test the A/B test endpoint.
    
    Tests that the /api/experiments/ab-test endpoint correctly processes
    A/B test requests for different variations.
    
    Args:
        client: TestClient fixture
        mocker: Pytest mocker fixture
    """
    # Mock search results
    mock_results = {
        "ads": [
            SearchResult(
                title="Paper Title",
                authors=["Author One", "Author Two"],
                abstract="Sample abstract",
                doi="10.1234/sample",
                year=2021,
                url="https://example.com/sample",
                source="ads",
                rank=1,
                citation_count=30,
                doctype="article",
                property=["refereed"]
            )
        ]
    }
    
    # Mock get_results_with_fallback function
    mocker.patch(
        "app.services.search_service.get_results_with_fallback", 
        return_value=mock_results
    )
    
    # Mock compare_results function
    mock_comparison = {
        "similarity": {
            "title": 0.85,
            "abstract": 0.75
        }
    }
    mocker.patch(
        "app.services.search_service.compare_results", 
        return_value=mock_comparison
    )
    
    # Define test request
    request_data = {
        "query": "quantum mechanics",
        "sources": ["ads", "semanticscholar"],
        "fields": ["title", "abstract", "authors", "doi"],
        "metrics": ["similarity", "coverage"]
    }
    
    # Test variation A
    response_a = client.post(
        "/api/experiments/ab-test?variation=A", 
        json=request_data
    )
    
    # Test variation B
    response_b = client.post(
        "/api/experiments/ab-test?variation=B", 
        json=request_data
    )
    
    # Check responses
    assert response_a.status_code == 200
    assert response_b.status_code == 200
    
    result_a = response_a.json()
    result_b = response_b.json()
    
    # Verify response contains expected fields
    for result in [result_a, result_b]:
        assert "test_id" in result
        assert "variation" in result
        assert "query" in result
        assert "results" in result
        assert "comparison" in result
    
    # Verify variations are correctly labeled
    assert result_a["variation"] == "A"
    assert result_b["variation"] == "B"
    
    # Verify results are included
    assert "ads" in result_a["results"]
    assert "ads" in result_b["results"]
    
    # B variation should have test property added to results
    b_result = result_b["results"]["ads"][0]
    if isinstance(b_result["property"], list):
        assert any("ab-test:" in prop for prop in b_result["property"])


@pytest.mark.asyncio
async def test_log_analysis_endpoint(client: TestClient) -> None:
    """
    Test the log analysis endpoint.
    
    Tests that the /api/experiments/log-analysis endpoint returns
    the expected placeholder response structure.
    
    Args:
        client: TestClient fixture
    """
    # Make request to endpoint
    response = client.get("/api/experiments/log-analysis")
    
    # Check response
    assert response.status_code == 200
    
    result = response.json()
    assert "message" in result
    assert "metrics" in result
    assert "timestamp" in result
    
    # Verify metrics fields in the placeholder response
    assert "avg_response_time" in result["metrics"]
    assert "cache_hit_rate" in result["metrics"]
    assert "common_queries" in result["metrics"]
    assert "error_rate" in result["metrics"] 