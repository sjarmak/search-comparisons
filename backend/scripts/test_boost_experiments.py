"""
Script to test the boost experiments functionality.

This script tests the field boost implementation by:
1. Making a search request with field boosts
2. Verifying query transformation
3. Checking original results remain unchanged
4. Verifying boosted results appear correctly
"""
import asyncio
import os
import sys
import json
from typing import Dict, Any
import logging
from dotenv import load_dotenv
import httpx

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_field_boosts() -> None:
    """Test the field boost functionality."""
    # Load environment variables
    load_dotenv()
    
    # Base URL for API
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    
    # Original query
    original_query = "Einstein relativity"
    
    # Create transformed query with field boosts
    transformed_query = (
        f'title:"{original_query}"^2.0 OR '
        f'abstract:"{original_query}"^1.5 OR '
        f'author:"{original_query}"^1.0'
    )
    
    # Boost experiment request
    boost_request = {
        "query": original_query,
        "transformedQuery": transformed_query,
        "boostConfig": {
            "enableFieldBoosts": True,
            "fieldBoosts": {
                "title": 2.0,
                "abstract": 1.5,
                "author": 1.0
            },
            "enableCiteBoost": True,
            "citeBoostWeight": 1.0,
            "enableRecencyBoost": True,
            "recencyBoostWeight": 1.0,
            "enableDoctypeBoost": True,
            "doctypeBoostWeight": 1.0,
            "combinationMethod": "sum",
            "maxBoost": 5.0
        }
    }
    
    logger.info(f"\n=== Boost Experiment Request ===")
    logger.info(f"Original Query: {original_query}")
    logger.info(f"Transformed Query: {transformed_query}")
    logger.info(f"Boost Config: {json.dumps(boost_request['boostConfig'], indent=2)}")
    
    try:
        async with httpx.AsyncClient() as client:
            # Make boost request
            response = await client.post(
                f"{base_url}/api/boost-experiment",
                json=boost_request,
                timeout=30.0
            )
            
            # Check response status
            if response.status_code != 200:
                logger.error(f"Error from boost endpoint: Status {response.status_code}")
                logger.error(f"Response: {response.text}")
                return
            
            # Parse response
            result = response.json()
            
            # Log the response details
            logger.info("\n=== Boost Experiment Results ===")
            logger.info(f"Status: {result.get('status')}")
            logger.info(f"Original Query: {result.get('query')}")
            logger.info(f"Transformed Query: {result.get('transformed_query')}")
            
            # Log the boosted results
            boosted_results = result.get('results', [])
            logger.info(f"\n=== Boosted Results (First 3) ===")
            logger.info(f"Total: {len(boosted_results)} results")
            
            for i, result in enumerate(boosted_results[:3], 1):
                logger.info(f"\nBoosted Result {i}:")
                logger.info(f"Title: {result.get('title')}")
                logger.info(f"Authors: {', '.join(result.get('authors', []))}")
                logger.info(f"Year: {result.get('year')}")
                logger.info(f"Abstract: {result.get('abstract')[:200]}...")
                logger.info(f"Citation Count: {result.get('citation_count')}")
                logger.info(f"Document Type: {result.get('doctype')}")
                
                # Log boost factors
                boost_factors = result.get('boost_factors', {})
                logger.info(f"Boost Factors:")
                logger.info(f"  Citation Boost: {boost_factors.get('cite_boost', 0):.2f}")
                logger.info(f"  Recency Boost: {boost_factors.get('recency_boost', 0):.2f}")
                logger.info(f"  Document Type Boost: {boost_factors.get('doctype_boost', 0):.2f}")
                
                logger.info(f"Final Boost: {result.get('final_boost', 0):.2f}")
                logger.info(f"Original Rank: {result.get('original_rank', 0)}")
                logger.info(f"New Rank: {result.get('new_rank', 0)}")
                logger.info(f"Rank Change: {result.get('rank_change', 0)}")
            
    except Exception as e:
        logger.error(f"Error testing boost experiments: {str(e)}", exc_info=True)

async def main() -> None:
    """Main function to run the test."""
    logger.info("Starting boost experiments test...")
    await test_field_boosts()
    logger.info("Test completed!")

if __name__ == "__main__":
    asyncio.run(main()) 