"""
Test suite for analyzing Quepid API metadata and search results.
"""
from typing import Dict, Any, List, Optional
import os
import pytest
import httpx
import json
import logging
import sys
from urllib.parse import urljoin
from datetime import datetime

# Setup logging to output to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# API Constants
QUEPID_API_URL = os.environ.get("QUEPID_API_URL", "https://quepid.herokuapp.com/api/")
QUEPID_API_KEY = os.environ.get("QUEPID_API_KEY", "c707e3d691c5f681f31a05b4c68bb09fc402597f325213a2e6411beebf199405")
TIMEOUT_SECONDS = 30

# Test Constants
CASE_ID = 8914
QUERY_TEXT = "triton"

@pytest.fixture(scope="session")
def event_loop():
    """
    Create an instance of the default event loop for the test session.
    """
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def snapshot_data() -> Dict[str, Any]:
    """
    Fixture to fetch snapshot data from Quepid API.
    
    Returns:
        Dict[str, Any]: The snapshot data from the API response.
    """
    url = urljoin(QUEPID_API_URL, f"cases/{CASE_ID}/snapshots/latest")
    headers = {
        "Authorization": f"Bearer {QUEPID_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        response = await client.get(url, headers=headers)
        assert response.status_code == 200, f"Failed to fetch data: {response.text}"
        return response.json()

@pytest.mark.asyncio
async def test_snapshot_basic_structure(snapshot_data: Dict[str, Any]) -> None:
    """
    Test the basic structure of the snapshot data.
    
    Args:
        snapshot_data: The snapshot data from the API.
    """
    data = await snapshot_data
    # Test basic snapshot metadata
    assert "id" in data
    assert "name" in data
    assert "time" in data
    assert "scorer" in data
    assert "try" in data
    assert "docs" in data
    assert "queries" in data
    assert "scores" in data

@pytest.mark.asyncio
async def test_scorer_metadata(snapshot_data: Dict[str, Any]) -> None:
    """
    Test the scorer metadata structure.
    
    Args:
        snapshot_data: The snapshot data from the API.
    """
    data = await snapshot_data
    scorer = data["scorer"]
    assert "scorer_id" in scorer
    assert "code" in scorer
    assert "name" in scorer
    assert "scale" in scorer
    assert "scale_with_labels" in scorer
    
    # Test scale labels
    scale_labels = scorer["scale_with_labels"]
    assert isinstance(scale_labels, dict)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in scale_labels.items())

@pytest.mark.asyncio
async def test_search_endpoint_metadata(snapshot_data: Dict[str, Any]) -> None:
    """
    Test the search endpoint metadata structure.
    
    Args:
        snapshot_data: The snapshot data from the API.
    """
    data = await snapshot_data
    try_data = data["try"]
    assert "search_endpoint" in try_data
    
    endpoint = try_data["search_endpoint"]
    assert "name" in endpoint
    assert "search_endpoint_id" in endpoint
    assert "endpoint_url" in endpoint
    assert "search_engine" in endpoint
    assert "api_method" in endpoint

@pytest.mark.asyncio
async def test_document_metadata(snapshot_data: Dict[str, Any]) -> None:
    """
    Test the document metadata structure.
    
    Args:
        snapshot_data: The snapshot data from the API.
    """
    data = await snapshot_data
    docs = data["docs"]
    assert isinstance(docs, dict)
    
    # Get first document
    first_doc_id = next(iter(docs.keys()))
    first_doc = docs[first_doc_id][0]  # Documents are in a list
    
    # Test document structure
    assert "id" in first_doc
    assert "explain" in first_doc
    assert "rated_only" in first_doc
    
    # Test explain structure
    explain = first_doc["explain"]
    assert "match" in explain
    assert "value" in explain
    assert "description" in explain
    assert "details" in explain

@pytest.mark.asyncio
async def test_query_metadata(snapshot_data: Dict[str, Any]) -> None:
    """
    Test the query metadata structure.
    
    Args:
        snapshot_data: The snapshot data from the API.
    """
    data = await snapshot_data
    queries = data["queries"]
    assert isinstance(queries, list)
    assert len(queries) > 0
    
    query = queries[0]
    assert "query_id" in query
    assert "query_text" in query
    assert "ratings" in query
    assert "modified_at" in query
    
    # Test ratings
    ratings = query["ratings"]
    assert isinstance(ratings, dict)
    assert all(isinstance(k, str) and isinstance(v, (int, float)) for k, v in ratings.items())

@pytest.mark.asyncio
async def test_score_metadata(snapshot_data: Dict[str, Any]) -> None:
    """
    Test the score metadata structure.
    
    Args:
        snapshot_data: The snapshot data from the API.
    """
    data = await snapshot_data
    scores = data["scores"]
    assert isinstance(scores, list)
    assert len(scores) > 0
    
    score = scores[0]
    assert "query_id" in score
    assert "score" in score
    assert "all_rated" in score
    assert "number_of_results" in score

@pytest.mark.asyncio
async def test_field_specification(snapshot_data: Dict[str, Any]) -> None:
    """
    Test the field specification metadata.
    
    Args:
        snapshot_data: The snapshot data from the API.
    """
    data = await snapshot_data
    try_data = data["try"]
    assert "field_spec" in try_data
    
    field_spec = try_data["field_spec"]
    logger.info(f"Field specification: {field_spec}")
    
    # Parse field spec
    fields = [f.strip() for f in field_spec.split(",")]
    logger.info(f"Parsed fields: {fields}")
    
    # Test common fields
    expected_fields = ["id", "title", "abstract"]
    for field in expected_fields:
        assert any(field in f for f in fields), f"Expected field {field} not found in field_spec"

@pytest.mark.asyncio
async def test_document_fields(snapshot_data: Dict[str, Any]) -> None:
    """
    Test the actual document fields in the response.
    
    Args:
        snapshot_data: The snapshot data from the API.
    """
    data = await snapshot_data
    
    # First, check the field specification
    try_data = data["try"]
    field_spec = try_data["field_spec"]
    print("\n=== Field Specification ===")
    print(f"Raw field spec: {field_spec}")
    
    # Parse and log each field
    fields = [f.strip() for f in field_spec.split(",")]
    print("\nParsed fields:")
    for field in fields:
        print(f"- {field}")
    
    # Now check the actual documents
    docs = data["docs"]
    print("\n=== Document Analysis ===")
    
    # Get first document
    first_doc_id = next(iter(docs.keys()))
    first_doc = docs[first_doc_id][0]  # Documents are in a list
    
    print(f"\nDocument ID: {first_doc_id}")
    print(f"Document structure: {json.dumps(first_doc, indent=2)}")
    
    # Check explain section for field information
    if "explain" in first_doc:
        explain = first_doc["explain"]
        print("\nExplain section details:")
        for detail in explain.get("details", []):
            if "description" in detail:
                desc = detail["description"]
                print(f"\nDescription: {desc}")
                # Look for field mentions in description
                if "title:" in desc.lower():
                    print("Found title field in description")
                if "abstract:" in desc.lower():
                    print("Found abstract field in description")
                if "keyword:" in desc.lower():
                    print("Found keyword field in description")
    
    # Check if fields are present
    if "fields" in first_doc:
        print(f"\nFields present: {json.dumps(first_doc['fields'], indent=2)}")
    else:
        print("\nNo fields section found in document")
        
    # Check queries section for ratings
    queries = data["queries"]
    if queries:
        query = queries[0]
        print("\n=== Query Information ===")
        print(f"Query text: {query.get('query_text')}")
        if "ratings" in query:
            print(f"Number of rated documents: {len(query['ratings'])}")
            print(f"Ratings: {json.dumps(query['ratings'], indent=2)}")