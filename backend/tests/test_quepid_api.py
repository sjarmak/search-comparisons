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

# Specific case and snapshot IDs
CASE_ID = 8862
WEAK_LENSING_QUERY_ID = 231665  # Query ID for "weak lensing"

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

async def get_judged_documents() -> List[Dict[str, Any]]:
    """
    Get documents with their judgments from the latest snapshot.
    
    Returns:
        List[Dict[str, Any]]: List of documents with their judgments
    """
    # Get the latest snapshot data
    snapshot_response = await test_endpoint(f"cases/{CASE_ID}/snapshots/latest")
    if not snapshot_response:
        logger.error("Failed to get snapshot data")
        return []
    
    # Get the weak lensing query
    weak_lensing_query = next(
        (q for q in snapshot_response.get('queries', []) if q.get('query_id') == WEAK_LENSING_QUERY_ID),
        None
    )
    
    if not weak_lensing_query:
        logger.error("Could not find weak lensing query in response")
        return []
    
    # Get the ratings
    ratings = weak_lensing_query.get('ratings', {})
    
    # Get the docs
    docs = snapshot_response.get('docs', {})
    
    # Extract documents with their judgments
    documents = []
    for doc_id, rating in ratings.items():
        # Find the document in the docs
        doc = next(
            (d for d in docs.get(str(WEAK_LENSING_QUERY_ID), []) if str(d.get('id')) == doc_id),
            None
        )
        
        if doc:
            title = doc.get('fields', {}).get('title', '')
            documents.append({
                'title': title,
                'judgment': rating
            })
    
    return documents

async def main():
    """Run tests on various Quepid API endpoints."""
    if not validate_api_key():
        sys.exit(1)
    
    # Get documents with their judgments
    documents = await get_judged_documents()
    
    if documents:
        logger.info("\nTitle | Judgment")
        logger.info("-" * 80)
        for doc in documents:
            logger.info(f"{doc['title']} | {doc['judgment']}")
    else:
        logger.info("No judged documents found in the response")

if __name__ == "__main__":
    asyncio.run(main()) 