"""
Test script for exploring Quepid API endpoints.

This script helps test and understand the Quepid API responses for different endpoints.
"""
import os
import asyncio
import logging
import sys
import json
from typing import Dict, Any, Optional, List
import httpx
from urllib.parse import urljoin

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Constants
QUEPID_API_URL = os.environ.get("QUEPID_API_URL", "https://quepid.herokuapp.com/api/")
QUEPID_API_KEY = 'c707e3d691c5f681f31a05b4c68bb09fc402597f325213a2e6411beebf199405' # os.environ.get("QUEPID_API_KEY", "")
TIMEOUT_SECONDS = 30

# User input: set these for your test
CASE_ID = 8914  # Change as needed
QUERY_TEXT = "triton"  # Change as needed

def validate_api_key() -> bool:
    """
    Validate that the API key is set and not empty.
    
    Returns:
        bool: True if API key is valid, False otherwise
    """
    if not QUEPID_API_KEY:
        logger.error("QUEPID_API_KEY environment variable is not set or is empty.")
        logger.error("Please set your API key using:")
        logger.error("export QUEPID_API_KEY='your_api_key_here'")
        return False
    return True

async def test_endpoint(endpoint: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Test a Quepid API endpoint and log the response.
    
    Args:
        endpoint: The API endpoint to test
        method: HTTP method to use (GET, POST, etc.)
        data: Optional data to send with the request
        
    Returns:
        Optional[Dict[str, Any]]: The JSON response if successful, None otherwise
    """
    try:
        url = urljoin(QUEPID_API_URL, endpoint)
        headers = {
            "Authorization": f"Bearer {QUEPID_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        logger.info(f"\nTesting endpoint: {url}")
        logger.info(f"Method: {method}")
        
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers, json=data)
            else:
                logger.error(f"Unsupported method: {method}")
                return None
            
            logger.info(f"Status code: {response.status_code}")
            
            try:
                response_data = response.json()
                return response_data
            except Exception as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                logger.info(f"Raw response: {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Error testing endpoint {endpoint}: {str(e)}")
        return None

async def get_case_queries(case_id: int) -> List[Dict[str, Any]]:
    """Fetch all queries for a given case using the ratings export endpoint."""
    url = urljoin(QUEPID_API_URL, f"export/ratings/{case_id}")
    headers = {
        "Authorization": f"Bearer {QUEPID_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    return data.get("queries", [])

def find_query_entry(queries: List[Dict[str, Any]], query_text: str) -> Optional[Dict[str, Any]]:
    """Find the query entry for a given query string."""
    for q in queries:
        if q.get("query", "").strip().lower() == query_text.strip().lower():
            return q
    return None

async def get_judged_documents_by_text(case_id: int, query_text: str) -> List[Dict[str, Any]]:
    """
    Get judged documents (title and judgment) for a given case and query text.
    """
    snapshot_url = urljoin(QUEPID_API_URL, f"cases/{case_id}/snapshots/latest")
    headers = {
        "Authorization": f"Bearer {QUEPID_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        resp = await client.get(snapshot_url, headers=headers)
        resp.raise_for_status()
        snapshot = resp.json()

    # Find the query in the snapshot by query text
    ratings = None
    for q in snapshot.get("queries", []):
        if q.get("query_text", "").strip().lower() == query_text.strip().lower():
            ratings = q.get("ratings", {})
            break
    if ratings is None:
        logger.warning("No ratings found for this query in the snapshot.")
        logger.info("Available queries in snapshot:")
        for q in snapshot.get("queries", []):
            logger.info(f"  - {q.get('query')}")
        return []

    # Create doc_map from the docs dictionary
    doc_map = {}
    for doc_id, doc_list in snapshot.get("docs", {}).items():
        # Each doc_list contains all documents for this query
        for doc in doc_list:
            # Use the document's own ID as the key
            doc_map[doc["id"]] = doc

    # Debug: Print what we found in doc_map
    logger.info("Documents found in doc_map:")
    for doc_id in doc_map:
        logger.info(f"  - {doc_id}")

    results = []
    for doc_id, score in ratings.items():
        doc = doc_map.get(doc_id, {})
        title = None
        if "fields" in doc:
            title = doc["fields"].get("title")
        if title is None:
            logger.warning(f"Missing title for doc_id={doc_id}")
        results.append({
            "title": title or "Unknown Title",
            "score": score
        })
    return results

async def main():
    if not validate_api_key():
        sys.exit(1)

    # Step 1: Get all queries for the case (for debug/info)
    queries = await get_case_queries(CASE_ID)
    logger.info("Available queries in this case (from ratings export):")
    for q in queries:
        logger.info(f"  - {q.get('query')} (query_id={q.get('query_id')})")

    # Step 2: Get judged documents for this query (by text)
    judged_docs = await get_judged_documents_by_text(CASE_ID, QUERY_TEXT)
    if judged_docs:
        logger.info("\nTitle | Judgment")
        logger.info("-" * 80)
        for doc in judged_docs:
            logger.info(f"{doc['title']} | {doc['score']}")
    else:
        logger.info("No judged documents found for the given query.")

if __name__ == "__main__":
    asyncio.run(main()) 