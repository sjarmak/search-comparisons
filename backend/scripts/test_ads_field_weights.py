"""
Test script for ADS API field weights.

This script makes direct calls to the ADS API to test the effect of field weights
on search results. It compares results with and without field weights.
"""
import os
import asyncio
import logging
from typing import Dict, Any, List
import json
from datetime import datetime
import httpx
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# ADS API Constants
ADS_API_URL = "https://api.adsabs.harvard.edu/v1/search/query"
TIMEOUT_SECONDS = 15

def get_ads_api_key() -> str:
    """Get the ADS API key from environment variables."""
    api_key = os.environ.get("ADS_API_KEY", "")
    if not api_key:
        raise ValueError("ADS_API_KEY not found in environment")
    return api_key

async def search_ads(
    query: str,
    qf: str = None,
    num_results: int = 20
) -> Dict[str, Any]:
    """
    Make a direct search request to the ADS API.
    
    Args:
        query: Search query string
        qf: Query field weights (e.g., "title^50.0")
        num_results: Number of results to return
        
    Returns:
        Dict[str, Any]: Response from ADS API
    """
    api_key = get_ads_api_key()
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    params = {
        "q": query,
        "fl": "bibcode,title,author,year,citation_count,abstract,doctype",
        "rows": num_results,
        "sort": "score desc"
    }
    
    if qf:
        params["qf"] = qf
    
    logger.info(f"Making request to ADS API:")
    logger.info(f"URL: {ADS_API_URL}")
    logger.info(f"Query: {query}")
    logger.info(f"Field weights: {qf if qf else 'None'}")
    logger.info(f"Full parameters: {params}")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            ADS_API_URL,
            headers=headers,
            params=params,
            timeout=TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response.json()

def format_result(doc: Dict[str, Any], rank: int) -> Dict[str, Any]:
    """Format a single search result for display."""
    return {
        "rank": rank,
        "title": doc.get("title", [""])[0] if isinstance(doc.get("title"), list) else doc.get("title", ""),
        "authors": doc.get("author", [])[:3],  # Show first 3 authors
        "year": doc.get("year"),
        "citations": doc.get("citation_count", 0),
        "score": doc.get("score", 0),  # Include score if available
        "bibcode": doc.get("bibcode", "")
    }

def save_results(results: Dict[str, Any], filename: str) -> None:
    """Save results to a JSON file."""
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"Saved results to {filename}")

async def main():
    """Run the field weights test."""
    # Test query
    query = "triton"
    
    # Test cases
    test_cases = [
        {
            "name": "no_weights",
            "qf": None,
            "description": "Search without field weights"
        },
        {
            "name": "title_boost_50",
            "qf": "title^50.0",
            "description": "Search with title boosted by 50x"
        }
    ]
    
    # Create results directory if it doesn't exist
    os.makedirs("test_results", exist_ok=True)
    
    # Run tests
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_results = {}
    
    for test in test_cases:
        logger.info(f"\nRunning test: {test['description']}")
        try:
            response = await search_ads(query, test["qf"])
            
            # Log response details
            logger.info(f"Response status: {response.get('responseHeader', {}).get('status', 'unknown')}")
            logger.info(f"Response time: {response.get('responseHeader', {}).get('QTime', 'unknown')}ms")
            logger.info(f"Response params: {response.get('responseHeader', {}).get('params', {})}")
            
            # Process results
            docs = response.get("response", {}).get("docs", [])
            formatted_results = [format_result(doc, i+1) for i, doc in enumerate(docs)]
            
            # Store results
            test_results = {
                "query": query,
                "field_weights": test["qf"],
                "description": test["description"],
                "response_header": response.get("responseHeader", {}),
                "results": formatted_results
            }
            
            all_results[test["name"]] = test_results
            
            # Save individual test results
            filename = f"test_results/ads_test_{test['name']}_{timestamp}.json"
            save_results(test_results, filename)
            
            # Print summary
            logger.info(f"\nResults for {test['description']}:")
            logger.info(f"Total results: {len(formatted_results)}")
            logger.info("\nTop 5 results:")
            for result in formatted_results[:5]:
                logger.info(f"Rank {result['rank']}: {result['title']}")
                logger.info(f"Authors: {', '.join(result['authors'])}")
                logger.info(f"Year: {result['year']}, Citations: {result['citations']}")
                logger.info(f"Score: {result.get('score', 'N/A')}")
                logger.info("---")
            
        except Exception as e:
            logger.error(f"Error in test {test['name']}: {str(e)}")
    
    # Save combined results
    combined_filename = f"test_results/ads_test_combined_{timestamp}.json"
    save_results(all_results, combined_filename)
    logger.info(f"\nAll test results saved to {combined_filename}")

if __name__ == "__main__":
    asyncio.run(main()) 