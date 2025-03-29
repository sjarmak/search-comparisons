"""
Script to test the main search endpoint with ADS Solr integration.

This script tests the /api/search/compare endpoint to verify that
the ADS Solr implementation is working correctly in the main application.
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

async def test_search_endpoint() -> None:
    """Test the search endpoint with ADS Solr."""
    # Load environment variables
    load_dotenv()
    
    # API endpoint
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    endpoint = f"{base_url}/api/search/compare"
    
    # Test query
    search_request = {
        "query": 'author:"Einstein"',
        "sources": ["ads"],  # Only test ADS for now
        "fields": ["title", "authors", "year", "abstract"],
        "metrics": ["jaccard", "rank_overlap"],
        "max_results": 20,
        "useTransformedQuery": False
    }
    
    logger.info(f"Testing search endpoint with request: {json.dumps(search_request, indent=2)}")
    
    try:
        async with httpx.AsyncClient() as client:
            # Make request
            response = await client.post(
                endpoint,
                json=search_request,
                timeout=30.0
            )
            
            # Check response status
            if response.status_code != 200:
                logger.error(f"Error from search endpoint: Status {response.status_code}")
                logger.error(f"Response: {response.text}")
                return
            
            # Parse response
            result = response.json()
            
            # Log results
            logger.info(f"\nSearch completed successfully!")
            logger.info(f"Query: {result['query']}")
            logger.info(f"Sources: {result['sources']}")
            
            # Check ADS results
            if "ads" in result["results"]:
                ads_results = result["results"]["ads"]
                logger.info(f"\nFound {len(ads_results)} results from ADS")
                
                # Log first few results
                for i, result in enumerate(ads_results[:3], 1):
                    logger.info(f"\nResult {i}:")
                    logger.info(f"Title: {result['title']}")
                    logger.info(f"Authors: {', '.join(result['authors'])}")
                    logger.info(f"Year: {result['year']}")
                    logger.info(f"Abstract: {result['abstract'][:200]}...")
            
            # Log comparison metrics if available
            if "comparison" in result:
                logger.info("\nComparison metrics:")
                logger.info(json.dumps(result["comparison"], indent=2))
            
    except Exception as e:
        logger.error(f"Error testing search endpoint: {str(e)}", exc_info=True)

async def main() -> None:
    """Main function to run the test."""
    logger.info("Starting search endpoint test...")
    await test_search_endpoint()
    logger.info("Test completed!")

if __name__ == "__main__":
    asyncio.run(main()) 