"""
Tests for the Quepid API service module.

This module contains tests for the Quepid API service, which integrates
with Quepid to evaluate search results using relevance judgments.
"""
import json
import math
from typing import Dict, List, Any, Optional, TYPE_CHECKING
import pytest
from unittest.mock import MagicMock, patch, AsyncMock, Mock
from httpx import HTTPError

from app.services.quepid_service import (
    QuepidJudgment,
    QuepidCase,
    calculate_ndcg,
    extract_doc_id,
    find_closest_query,
    evaluate_search_results,
    load_case_with_judgments,
    get_case_judgments
)
from app.api.models import SearchResult

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


@pytest.fixture(autouse=True)
def setup_env(monkeypatch: "MonkeyPatch") -> None:
    """Set up environment variables for testing."""
    monkeypatch.setenv("QUEPID_API_KEY", "test_api_key")
    monkeypatch.setenv("QUEPID_API_URL", "https://test.quepid.com/api/")
    
    # Also patch the QUEPID_API_KEY constant in the module
    monkeypatch.setattr("app.services.quepid_service.QUEPID_API_KEY", "test_api_key")
    monkeypatch.setattr("app.services.quepid_service.QUEPID_API_URL", "https://test.quepid.com/api/")


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock HTTP client for testing.
    
    Returns:
        AsyncMock: A mock HTTP client
    """
    return AsyncMock()


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
            abstract="An abstract about climate change effects",
            year="2020",
            citation_count=10,
            doctype="article",
            url="https://ui.adsabs.harvard.edu/abs/2020ApJ...123..456A/abstract",
            source="ads",
            rank=1
        ),
        SearchResult(
            title="Global Warming Studies",
            authors=["Author Three", "Author Four"],
            abstract="A study about global warming",
            year="2021",
            citation_count=5,
            doctype="article",
            url="https://ui.adsabs.harvard.edu/abs/2021ApJ...234..567B/abstract",
            source="ads",
            rank=2
        ),
        SearchResult(
            title="Unrelated Paper",
            authors=["Author Five", "Author Six"],
            abstract="A paper about something else",
            year="2022",
            citation_count=2,
            doctype="article",
            url="https://ui.adsabs.harvard.edu/abs/2022ApJ...345..678C/abstract",
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

    # Partial match - should match "climate change effects" since it contains all words from "climate change research"
    assert find_closest_query("climate change research", available_queries) == "climate change effects"

    # No match
    assert find_closest_query("unrelated query", available_queries) is None


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


@pytest.fixture
def mock_load_case() -> MagicMock:
    """Create a mock for the load_case_with_judgments function."""
    return MagicMock()


@pytest.mark.asyncio
async def test_evaluate_search_results(
    mock_client: AsyncMock,
    mock_search_results: List[SearchResult]
) -> None:
    """Test evaluating search results against Quepid judgments."""
    # Create mock response for case loading
    mock_response = AsyncMock()
    mock_response.json.side_effect = [
        {
            "case_id": 123,
            "case_name": "Test Case",
            "book_id": 456,
            "tries": [
                {"args": {"q": ["climate change"]}},
                {"args": {"q": ["global warming"]}}
            ]
        },
        {
            "queries": [
                {
                    "query": "climate change",
                    "ratings": {
                        "doc1": 3,
                        "doc2": 2
                    }
                },
                {
                    "query": "global warming",
                    "ratings": {
                        "doc3": 4,
                        "doc4": 1
                    }
                }
            ]
        },
        {
            "query_doc_pairs": [
                {"doc_id": "doc1", "title": "Climate Change Impact"},
                {"doc_id": "doc2", "title": "Global Warming Effects"},
                {"doc_id": "doc3", "title": "Climate Crisis"},
                {"doc_id": "doc4", "title": "Temperature Rise"}
            ]
        }
    ]
    mock_response.raise_for_status = AsyncMock()
    mock_client.get.return_value = mock_response

    # Test evaluating search results
    result = await evaluate_search_results(
        query="climate change",
        search_results=mock_search_results,
        case_id=123
    )

    # Verify results
    assert result is not None
    assert result["query"] == "climate change"
    assert result["case_id"] == 123
    assert result["case_name"] == "Test Case"
    assert "metrics" in result
    assert "ndcg@10" in result["metrics"]
    assert "p@10" in result["metrics"]
    assert "recall" in result
    assert "judged_retrieved" in result
    assert "relevant_retrieved" in result
    assert "total_judged" in result
    assert "total_relevant" in result
    assert "results_count" in result
    assert "judged_titles" in result
    assert "source_results" in result

    # Verify source results
    source_results = result["source_results"][0]
    assert source_results["source"] == "ads"
    assert len(source_results["metrics"]) > 0
    assert len(source_results["results"]) > 0

    # Verify metrics
    assert source_results["metrics"][0]["name"] == "ndcg@5"
    assert source_results["metrics"][1]["name"] == "ndcg@10"
    assert source_results["metrics"][2]["name"] == "ndcg@20"
    assert source_results["metrics"][3]["name"] == "p@5"
    assert source_results["metrics"][4]["name"] == "p@10"
    assert source_results["metrics"][5]["name"] == "p@20"
    assert source_results["metrics"][6]["name"] == "recall"

    # Verify API calls
    assert mock_client.get.call_count == 3
    mock_client.get.assert_any_call(
        "https://api.quepid.com/api/v1/cases/123",
        headers={
            "Authorization": "Bearer test_key",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=30
    )
    mock_client.get.assert_any_call(
        "https://api.quepid.com/api/v1/export/ratings/123",
        headers={
            "Authorization": "Bearer test_key",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=30
    )
    mock_client.get.assert_any_call(
        "https://api.quepid.com/api/v1/books/456/query_doc_pairs",
        headers={
            "Authorization": "Bearer test_key",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=30
    )


@pytest.fixture
def mock_quepid_responses() -> Dict[str, Any]:
    """Create mock responses for Quepid API calls."""
    return {
        "case": {
            "case_id": 8835,
            "case_name": "Test Case",
            "book_id": 172,
            "book_name": "Test Book",
            "tries": [
                {
                    "args": {"q": ["climate change"]}
                },
                {
                    "args": {"q": ["global warming"]}
                }
            ]
        },
        "ratings": {
            "queries": [
                {
                    "query": "climate change",
                    "ratings": {
                        "10.1234/example": 3,
                        "10.5678/another": 1
                    }
                },
                {
                    "query": "global warming",
                    "ratings": {
                        "10.9876/test": 2
                    }
                }
            ]
        },
        "query_doc_pairs": {
            "query_doc_pairs": [
                {
                    "doc_id": "10.1234/example",
                    "title": "Climate Change Effects",
                    "query": "climate change"
                },
                {
                    "doc_id": "10.5678/another",
                    "title": "Global Warming Studies",
                    "query": "climate change"
                },
                {
                    "doc_id": "10.9876/test",
                    "title": "Carbon Emissions Impact",
                    "query": "global warming"
                }
            ]
        },
        "judgements": {
            "judgements": [
                {
                    "doc_id": "10.1234/example",
                    "title": "Climate Change Effects",
                    "rating": 3
                },
                {
                    "doc_id": "10.5678/another",
                    "title": "Global Warming Studies",
                    "rating": 1
                },
                {
                    "doc_id": "10.9876/test",
                    "title": "Carbon Emissions Impact",
                    "rating": 2
                }
            ]
        }
    }


@pytest.fixture
def mock_case() -> QuepidCase:
    """Create a mock case for testing.
    
    Returns:
        QuepidCase: A mock case with test data.
    """
    return QuepidCase(
        case_id=123,
        name="Test Case",
        queries=["climate change", "global warming"],
        judgments={
            "climate change": {
                "doc1": {
                    "rating": 4,
                    "title": "Climate Change Article 1"
                },
                "doc2": {
                    "rating": 3,
                    "title": "Climate Change Article 2"
                }
            },
            "global warming": {
                "doc3": {
                    "rating": 5,
                    "title": "Global Warming Article 1"
                }
            }
        }
    )


def test_quepid_judgment_init() -> None:
    """Test initializing a QuepidJudgment."""
    judgment = QuepidJudgment(
        query_text="test query",
        doc_id="test_doc",
        rating=3,
        metadata={"title": "Test Document"}
    )
    
    assert judgment.query_text == "test query"
    assert judgment.doc_id == "test_doc"
    assert judgment.rating == 3
    assert judgment.metadata == {"title": "Test Document"}


def test_quepid_case_init() -> None:
    """Test initializing a QuepidCase."""
    case = QuepidCase(
        case_id=123,
        name="Test Case",
        queries=["query1", "query2"],
        judgments={
            "query1": {"doc1": {"rating": 3}},
            "query2": {"doc2": {"rating": 2}}
        }
    )
    
    assert case.case_id == 123
    assert case.name == "Test Case"
    assert case.queries == ["query1", "query2"]
    assert case.judgments == {
        "query1": {"doc1": {"rating": 3}},
        "query2": {"doc2": {"rating": 2}}
    }


def test_extract_doc_id() -> None:
    """Test extracting document ID from a URL."""
    url = "https://ui.adsabs.harvard.edu/abs/2020ApJ...123..456A/abstract"
    doc_id = extract_doc_id(url)
    assert doc_id == "2020123456"


def test_find_closest_query() -> None:
    """Test finding the closest matching query."""
    available_queries = ["climate change effects", "global warming impacts", "carbon emissions"]

    # Exact match after normalization
    assert find_closest_query("Climate Change Effects", available_queries) == "climate change effects"

    # Partial match - should match "climate change effects" since it contains all words from "climate change research"
    assert find_closest_query("climate change research", available_queries) == "climate change effects"

    # No match
    assert find_closest_query("unrelated query", available_queries) is None


def test_calculate_ndcg() -> None:
    """Test calculating nDCG."""
    # Test with perfect ordering
    ratings = [3, 2, 1, 0]
    assert calculate_ndcg(ratings, 4) == 1.0
    
    # Test with imperfect ordering
    ratings = [2, 3, 1, 0]
    assert calculate_ndcg(ratings, 4) < 1.0
    
    # Test with empty list
    assert calculate_ndcg([], 4) == 0.0


@pytest.mark.asyncio
async def test_load_case_with_judgments(mock_client: AsyncMock) -> None:
    """Test loading a case with judgments from Quepid."""
    # Create mock response
    mock_response = AsyncMock()
    mock_response.json.side_effect = [
        {
            "case_id": 123,
            "case_name": "Test Case",
            "book_id": 456,
            "tries": [
                {"args": {"q": ["climate change"]}},
                {"args": {"q": ["global warming"]}}
            ]
        },
        {
            "queries": [
                {
                    "query": "climate change",
                    "ratings": {
                        "doc1": 3,
                        "doc2": 2
                    }
                },
                {
                    "query": "global warming",
                    "ratings": {
                        "doc3": 4,
                        "doc4": 1
                    }
                }
            ]
        },
        {
            "query_doc_pairs": [
                {"doc_id": "doc1", "title": "Climate Change Impact"},
                {"doc_id": "doc2", "title": "Global Warming Effects"},
                {"doc_id": "doc3", "title": "Climate Crisis"},
                {"doc_id": "doc4", "title": "Temperature Rise"}
            ]
        }
    ]
    mock_response.raise_for_status = AsyncMock()
    mock_client.get.return_value = mock_response

    # Test loading case
    case = await load_case_with_judgments(123)

    # Verify case was loaded correctly
    assert case is not None
    assert case.case_id == 123
    assert case.name == "Test Case"
    assert len(case.queries) == 2
    assert "climate change" in case.queries
    assert "global warming" in case.queries

    # Verify judgments
    assert "climate change" in case.judgments
    assert "global warming" in case.judgments
    assert len(case.judgments["climate change"]) == 2
    assert len(case.judgments["global warming"]) == 2

    # Verify document ratings and titles
    climate_change_judgments = case.judgments["climate change"]
    assert climate_change_judgments["doc1"]["rating"] == 3
    assert climate_change_judgments["doc1"]["title"] == "Climate Change Impact"
    assert climate_change_judgments["doc2"]["rating"] == 2
    assert climate_change_judgments["doc2"]["title"] == "Global Warming Effects"

    global_warming_judgments = case.judgments["global warming"]
    assert global_warming_judgments["doc3"]["rating"] == 4
    assert global_warming_judgments["doc3"]["title"] == "Climate Crisis"
    assert global_warming_judgments["doc4"]["rating"] == 1
    assert global_warming_judgments["doc4"]["title"] == "Temperature Rise"

    # Verify API calls
    assert mock_client.get.call_count == 3
    mock_client.get.assert_any_call(
        "https://api.quepid.com/api/v1/cases/123",
        headers={
            "Authorization": "Bearer test_key",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=30
    )
    mock_client.get.assert_any_call(
        "https://api.quepid.com/api/v1/export/ratings/123",
        headers={
            "Authorization": "Bearer test_key",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=30
    )
    mock_client.get.assert_any_call(
        "https://api.quepid.com/api/v1/books/456/query_doc_pairs",
        headers={
            "Authorization": "Bearer test_key",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=30
    )


@pytest.mark.asyncio
async def test_load_case_with_judgments_fallback(mock_client: AsyncMock) -> None:
    """Test loading a case with judgments using the fallback endpoint."""
    # Create mock response
    mock_response = AsyncMock()
    mock_response.json.side_effect = [
        {
            "case_id": 123,
            "case_name": "Test Case",
            "book_id": 456,
            "tries": [
                {"args": {"q": ["climate change"]}},
                {"args": {"q": ["global warming"]}}
            ]
        },
        {
            "queries": [
                {
                    "query": "climate change",
                    "ratings": {
                        "doc1": 3,
                        "doc2": 2
                    }
                },
                {
                    "query": "global warming",
                    "ratings": {
                        "doc3": 4,
                        "doc4": 1
                    }
                }
            ]
        },
        HTTPError("Failed to get query_doc_pairs"),  # Simulate failure of first endpoint
        {
            "judgements": [
                {"doc_id": "doc1", "title": "Climate Change Impact"},
                {"doc_id": "doc2", "title": "Global Warming Effects"},
                {"doc_id": "doc3", "title": "Climate Crisis"},
                {"doc_id": "doc4", "title": "Temperature Rise"}
            ]
        }
    ]
    mock_response.raise_for_status = AsyncMock()
    mock_client.get.return_value = mock_response

    # Test loading case
    case = await load_case_with_judgments(123)

    # Verify case was loaded correctly
    assert case is not None
    assert case.case_id == 123
    assert case.name == "Test Case"
    assert len(case.queries) == 2
    assert "climate change" in case.queries
    assert "global warming" in case.queries

    # Verify judgments
    assert "climate change" in case.judgments
    assert "global warming" in case.judgments
    assert len(case.judgments["climate change"]) == 2
    assert len(case.judgments["global warming"]) == 2

    # Verify document ratings and titles
    climate_change_judgments = case.judgments["climate change"]
    assert climate_change_judgments["doc1"]["rating"] == 3
    assert climate_change_judgments["doc1"]["title"] == "Climate Change Impact"
    assert climate_change_judgments["doc2"]["rating"] == 2
    assert climate_change_judgments["doc2"]["title"] == "Global Warming Effects"

    global_warming_judgments = case.judgments["global warming"]
    assert global_warming_judgments["doc3"]["rating"] == 4
    assert global_warming_judgments["doc3"]["title"] == "Climate Crisis"
    assert global_warming_judgments["doc4"]["rating"] == 1
    assert global_warming_judgments["doc4"]["title"] == "Temperature Rise"

    # Verify API calls
    assert mock_client.get.call_count == 4
    mock_client.get.assert_any_call(
        "https://api.quepid.com/api/v1/cases/123",
        headers={
            "Authorization": "Bearer test_key",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=30
    )
    mock_client.get.assert_any_call(
        "https://api.quepid.com/api/v1/export/ratings/123",
        headers={
            "Authorization": "Bearer test_key",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=30
    )
    mock_client.get.assert_any_call(
        "https://api.quepid.com/api/v1/books/456/query_doc_pairs",
        headers={
            "Authorization": "Bearer test_key",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=30
    )
    mock_client.get.assert_any_call(
        "https://api.quepid.com/api/v1/books/456/judgements",
        headers={
            "Authorization": "Bearer test_key",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=30
    )


@pytest.mark.asyncio
async def test_get_document_titles_from_quepid(mock_client: AsyncMock) -> None:
    """
    Test getting document titles from Quepid API.
    
    This test verifies that we can successfully retrieve document titles
    from Quepid's query_doc_pairs endpoint and that they are correctly
    associated with their document IDs.
    """
    # Create mock responses for each API call
    mock_case_response = AsyncMock()
    mock_case_response.json.return_value = {
        "case_id": 123,
        "case_name": "Test Case",
        "book_id": 456,
        "tries": [
            {"args": {"q": ["climate change"]}},
            {"args": {"q": ["global warming"]}}
        ]
    }
    mock_case_response.raise_for_status = AsyncMock()

    mock_ratings_response = AsyncMock()
    mock_ratings_response.json.return_value = {
        "queries": [
            {
                "query": "climate change",
                "ratings": {
                    "2020ApJ...123..456A": 3,
                    "2021ApJ...234..567B": 2
                }
            },
            {
                "query": "global warming",
                "ratings": {
                    "2021ApJ...234..567B": 3,
                    "2020ApJ...123..456A": 2
                }
            }
        ]
    }
    mock_ratings_response.raise_for_status = AsyncMock()

    mock_titles_response = AsyncMock()
    mock_titles_response.json.return_value = {
        "query_doc_pairs": [
            {
                "doc_id": "2020ApJ...123..456A",
                "title": "Climate Change Effects on Global Temperature",
                "query": "climate change"
            },
            {
                "doc_id": "2021ApJ...234..567B",
                "title": "Global Warming Impact on Ecosystems",
                "query": "global warming"
            }
        ]
    }
    mock_titles_response.raise_for_status = AsyncMock()

    # Set up the mock client to return different responses for each call
    mock_client.get.side_effect = [
        mock_case_response,
        mock_ratings_response,
        mock_titles_response
    ]

    # Test loading case with document titles
    case = await load_case_with_judgments(123, client=mock_client)

    # Verify that document titles were retrieved and stored correctly
    assert case is not None
    assert "climate change" in case.judgments
    assert "global warming" in case.judgments

    # Check that titles are present in the judgments
    climate_change_judgments = case.judgments["climate change"]
    assert "2020ApJ...123..456A" in climate_change_judgments
    assert climate_change_judgments["2020ApJ...123..456A"]["title"] == "Climate Change Effects on Global Temperature"

    global_warming_judgments = case.judgments["global warming"]
    assert "2021ApJ...234..567B" in global_warming_judgments
    assert global_warming_judgments["2021ApJ...234..567B"]["title"] == "Global Warming Impact on Ecosystems"

    # Verify the API calls were made correctly
    assert mock_client.get.call_count == 3
    mock_client.get.assert_any_call(
        "https://test.quepid.com/api/cases/123",
        headers={
            "Authorization": "Bearer test_api_key",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=30
    )
    mock_client.get.assert_any_call(
        "https://test.quepid.com/api/export/ratings/123",
        headers={
            "Authorization": "Bearer test_api_key",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=30
    )
    mock_client.get.assert_any_call(
        "https://test.quepid.com/api/books/456/query_doc_pairs",
        headers={
            "Authorization": "Bearer test_api_key",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=30
    )

    # Calculate total relevant documents
    total_relevant = sum(1 for j in case.judgments.values() if 
        (isinstance(j, dict) and j.get('rating', 0) > 0) or 
        (isinstance(j, (int, float)) and j > 0))

    # Get judgment for this document
    judgment = case.judgments.get(doc_id, 0)
    if isinstance(judgment, dict):
        rating = judgment.get('rating', 0)
    else:
        rating = float(judgment)


@pytest.mark.asyncio
async def test_get_case_judgments(mock_client: AsyncMock) -> None:
    """
    Test retrieving judgments for a specific case from Quepid.
    
    Args:
        mock_client: Mocked HTTP client for testing
    """
    # Create mock response data
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "queries": [
            {
                "query": "climate change",
                "ratings": {
                    "doc1": 3,
                    "doc2": 2
                }
            },
            {
                "query": "global warming",
                "ratings": {
                    "doc3": 4,
                    "doc4": 1
                }
            }
        ]
    }
    mock_response.raise_for_status = AsyncMock()
    mock_client.get.return_value = mock_response

    # Test getting judgments
    case_id = 123
    judgments = await get_case_judgments(case_id)

    # Verify the response
    assert judgments is not None
    assert "queries" in judgments
    assert len(judgments["queries"]) == 2
    
    # Verify climate change query
    climate_query = next(q for q in judgments["queries"] if q["query"] == "climate change")
    assert climate_query["ratings"]["doc1"] == 3
    assert climate_query["ratings"]["doc2"] == 2
    
    # Verify global warming query
    warming_query = next(q for q in judgments["queries"] if q["query"] == "global warming")
    assert warming_query["ratings"]["doc3"] == 4
    assert warming_query["ratings"]["doc4"] == 1

    # Verify API call
    mock_client.get.assert_called_once_with(
        "https://test.quepid.com/api/export/ratings/123",
        headers={
            "Authorization": "Bearer test_api_key",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=30
    )


@pytest.mark.asyncio
async def test_get_case_judgments_no_api_key(mock_client: AsyncMock, monkeypatch: MonkeyPatch) -> None:
    """
    Test retrieving judgments when API key is not set.
    
    Args:
        mock_client: Mocked HTTP client for testing
        monkeypatch: pytest's monkeypatch fixture
    """
    # Remove API key
    monkeypatch.delenv("QUEPID_API_KEY", raising=False)
    
    # Test getting judgments
    case_id = 123
    judgments = await get_case_judgments(case_id)
    
    # Verify empty response
    assert judgments == {}
    
    # Verify no API call was made
    mock_client.get.assert_not_called()


@pytest.mark.asyncio
async def test_get_case_judgments_error(mock_client: AsyncMock) -> None:
    """
    Test handling of errors when retrieving judgments.
    
    Args:
        mock_client: Mocked HTTP client for testing
    """
    # Simulate HTTP error
    mock_client.get.side_effect = httpx.HTTPError("API Error")
    
    # Test getting judgments
    case_id = 123
    judgments = await get_case_judgments(case_id)
    
    # Verify empty response on error
    assert judgments == {}
    
    # Verify API call was attempted
    mock_client.get.assert_called_once_with(
        "https://test.quepid.com/api/export/ratings/123",
        headers={
            "Authorization": "Bearer test_api_key",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=30
    ) 