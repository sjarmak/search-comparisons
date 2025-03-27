"""
Tests for the Quepid API service module.

This module contains tests for the Quepid API service, which integrates
with Quepid to evaluate search results using relevance judgments.
"""
import json
import math
from typing import Dict, List, Any, Optional, TYPE_CHECKING
import pytest
from unittest.mock import MagicMock, patch

from app.services.quepid_service import (
    QuepidJudgment,
    QuepidCase,
    calculate_ndcg,
    extract_doc_id,
    find_closest_query,
    evaluate_search_results,
    load_case_with_judgments
)
from app.api.models import SearchResult

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


@pytest.fixture
def mock_judgment() -> QuepidJudgment:
    """
    Create a mock Quepid judgment for testing.
    
    Returns:
        QuepidJudgment: A mock judgment object
    """
    return QuepidJudgment(
        query_text="climate change",
        doc_id="10.1234/example",
        rating=3,
        metadata={"field1": "value1"}
    )


@pytest.fixture
def mock_case(mock_judgment: QuepidJudgment) -> QuepidCase:
    """
    Create a mock Quepid case with judgments for testing.
    
    Args:
        mock_judgment: A mock judgment to include in the case
    
    Returns:
        QuepidCase: A mock case object
    """
    return QuepidCase(
        case_id=123,
        name="Test Case",
        queries=["climate change", "global warming"],
        judgments={
            "climate change": [
                mock_judgment,
                QuepidJudgment(
                    query_text="climate change",
                    doc_id="10.5678/another",
                    rating=1,
                    metadata={}
                )
            ],
            "global warming": [
                QuepidJudgment(
                    query_text="global warming",
                    doc_id="10.9876/test",
                    rating=2,
                    metadata={}
                )
            ]
        }
    )


@pytest.fixture
def mock_search_results() -> List[SearchResult]:
    """
    Create mock search results for testing.
    
    Returns:
        List[SearchResult]: A list of mock search results
    """
    return [
        SearchResult(
            title="Climate Change Effects",
            authors=["Author One", "Author Two"],
            abstract="An abstract about climate change",
            doi="10.1234/example",
            year=2022,
            url="https://example.com/paper1",
            source="ads",
            rank=1
        ),
        SearchResult(
            title="Global Warming Studies",
            authors=["Author Three"],
            abstract="An abstract about global warming",
            doi="10.5678/another",
            year=2021,
            url="https://example.com/paper2",
            source="ads",
            rank=2
        ),
        SearchResult(
            title="Unrelated Paper",
            authors=["Author Four"],
            abstract="An abstract about something else",
            doi="10.9876/unrelated",
            year=2020,
            url="https://example.com/paper3",
            source="ads",
            rank=3
        )
    ]


def test_quepid_judgment_init(mock_judgment: QuepidJudgment) -> None:
    """
    Test initializing a QuepidJudgment object.
    
    Args:
        mock_judgment: A mock judgment object
    """
    assert mock_judgment.query_text == "climate change"
    assert mock_judgment.doc_id == "10.1234/example"
    assert mock_judgment.rating == 3
    assert mock_judgment.metadata == {"field1": "value1"}


def test_quepid_case_init(mock_case: QuepidCase) -> None:
    """
    Test initializing a QuepidCase object.
    
    Args:
        mock_case: A mock case object
    """
    assert mock_case.case_id == 123
    assert mock_case.name == "Test Case"
    assert len(mock_case.queries) == 2
    assert "climate change" in mock_case.queries
    assert "global warming" in mock_case.queries
    assert len(mock_case.judgments["climate change"]) == 2
    assert len(mock_case.judgments["global warming"]) == 1


def test_extract_doc_id(mock_search_results: List[SearchResult]) -> None:
    """
    Test extracting document IDs from search results.
    
    Args:
        mock_search_results: Mock search results
    """
    # Test DOI extraction
    assert extract_doc_id(mock_search_results[0]) == "10.1234/example"
    
    # Test bibcode extraction from URL
    result_with_bibcode = SearchResult(
        title="Bibcode Paper",
        source="ads",
        rank=4,
        url="https://ui.adsabs.harvard.edu/abs/2020ApJ...900...28L/abstract"
    )
    assert extract_doc_id(result_with_bibcode) == "2020ApJ...900...28L"
    
    # Test fallback to title
    result_without_id = SearchResult(
        title="No ID Paper",
        source="scholar",
        rank=5
    )
    assert extract_doc_id(result_without_id) == "No ID Paper"


def test_find_closest_query() -> None:
    """Test finding the closest matching query."""
    available_queries = ["climate change effects", "global warming impacts", "carbon emissions"]
    
    # Exact match after normalization
    assert find_closest_query("Climate Change Effects", available_queries) == "climate change effects"
    
    # Partial match
    assert find_closest_query("climate change research", available_queries) == "climate change effects"
    
    # No good match
    assert find_closest_query("completely unrelated", available_queries) is None


def test_calculate_ndcg(mock_search_results: List[SearchResult]) -> None:
    """
    Test calculating nDCG for search results.
    
    Args:
        mock_search_results: Mock search results
    """
    # Create judgment dictionary
    judgments = {
        "10.1234/example": 3,  # Highly relevant
        "10.5678/another": 1,  # Somewhat relevant
        "10.9876/test": 2      # Relevant but not in results
    }
    
    # Calculate nDCG
    ndcg = calculate_ndcg(mock_search_results, judgments)
    
    # Expected DCG: (2^3-1)/log2(1+1) + (2^1-1)/log2(2+1) + 0/log2(3+1)
    # Expected DCG: 7/1 + 1/1.585 = 7 + 0.631 = 7.631
    # 
    # Ideal ordering would be: rating 3, rating 2, rating 1
    # Ideal DCG: (2^3-1)/log2(1+1) + (2^2-1)/log2(2+1) + (2^1-1)/log2(3+1)
    # Ideal DCG: 7/1 + 3/1.585 + 1/2 = 7 + 1.893 + 0.5 = 9.393
    # 
    # nDCG = DCG/IDCG = 7.631/9.393 = 0.812
    
    # Allow some floating point tolerance
    assert math.isclose(ndcg, 0.812, abs_tol=0.01)


@patch('app.services.quepid_service.load_case_with_judgments')
@pytest.mark.asyncio
async def test_evaluate_search_results(
    mock_load_case: MagicMock,
    mock_case: QuepidCase,
    mock_search_results: List[SearchResult]
) -> None:
    """
    Test evaluating search results against Quepid judgments.
    
    Args:
        mock_load_case: Mocked function for loading case
        mock_case: Mock case object
        mock_search_results: Mock search results
    """
    # Configure mock
    mock_load_case.return_value = mock_case
    
    # Call function
    result = await evaluate_search_results(
        query="climate change",
        search_results=mock_search_results,
        case_id=123
    )
    
    # Verify results
    assert result["query"] == "climate change"
    assert result["case_id"] == 123
    assert result["case_name"] == "Test Case"
    assert "ndcg" in result
    assert "precision" in result
    assert "recall" in result
    assert "judged_retrieved" in result
    assert "relevant_retrieved" in result
    
    # Verify metrics calculated
    assert "ndcg@5" in result["ndcg"] or "ndcg@10" in result["ndcg"] or "ndcg@20" in result["ndcg"]
    assert result["judged_retrieved"] > 0 