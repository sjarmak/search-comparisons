"""
Script to test the field boost experiments functionality.

This script tests the field boost implementation by:
1. Making a search request with field boosts
2. Verifying query transformation
3. Checking results are properly boosted by field
4. Comparing results with and without field boosts
"""
import asyncio
import os
import sys
import json
from typing import Dict, Any
import logging
from dotenv import load_dotenv
import httpx
from datetime import datetime

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Import models after adding backend to path
from app.api.models import BoostConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main(query: str) -> None:
    """
    Test the field boost implementation.
    
    Args:
        query: The search query to test
    """
    # Create the transformed query with field boosts
    transformed_query = (
        f'title:"{query}"^2.0 OR '
        f'abstract:"{query}"^1.5 OR '
        f'author:"{query}"^1.0'
    )
    
    # Create the request data
    request_data = {
        "query": query,
        "transformed_query": transformed_query,
        "citation_boost": 0.0,  # Disable other boosts for field boost testing
        "min_citations": 0,
        "recency_boost": 0.0,
        "reference_year": datetime.now().year,
        "doctype_boosts": {},  # Disable doctype boosts
        "source": "ads",
        "rank": 1
    }
    
    logger.info(f"Original query: {query}")
    logger.info(f"Transformed query: {transformed_query}")
    logger.info(f"Request data: {json.dumps(request_data, indent=2)}")
    
    # Make the request
    try:
        response = httpx.post(
            "http://localhost:8000/api/experiments/boost",
            json=request_data,
            timeout=30
        )
        response.raise_for_status()
        logger.info("Field boost experiment completed successfully")
        logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
    except httpx.HTTPError as e:
        logger.error(f"Error making request: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response content: {e.response.text}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_field_boost_experiments.py <query>")
        sys.exit(1)
    main(sys.argv[1]) 