"""
Script to test ADS Solr connection locally.

This script provides a simple way to test the ADS Solr connection
and verify that search results are being returned correctly.
"""
import asyncio
import os
import sys
from typing import List
import logging
from dotenv import load_dotenv

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.services.ads_service import query_ads_solr, get_ads_results

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_basic_query() -> None:
    """Test a basic query to ADS Solr."""
    query = 'author:"Einstein"'
    fields = ["title", "authors", "year", "abstract"]
    
    logger.info(f"Testing basic query: {query}")
    results = await query_ads_solr(query, fields)
    
    logger.info(f"Found {len(results)} results")
    for i, result in enumerate(results, 1):
        logger.info(f"\nResult {i}:")
        logger.info(f"Title: {result.title}")
        logger.info(f"Authors: {', '.join(result.authors)}")
        logger.info(f"Year: {result.year}")
        logger.info(f"Abstract: {result.abstract[:200]}...")

async def test_combined_query() -> None:
    """Test the combined query method that tries both Solr and API."""
    query = 'author:"Einstein"'
    fields = ["title", "authors", "year", "abstract"]
    
    logger.info(f"Testing combined query method: {query}")
    results = await get_ads_results(query, fields)
    
    logger.info(f"Found {len(results)} results")
    for i, result in enumerate(results, 1):
        logger.info(f"\nResult {i}:")
        logger.info(f"Title: {result.title}")
        logger.info(f"Authors: {', '.join(result.authors)}")
        logger.info(f"Year: {result.year}")
        logger.info(f"Abstract: {result.abstract[:200]}...")

async def main() -> None:
    """Main function to run all tests."""
    # Load environment variables
    load_dotenv()
    
    # Print configuration
    logger.info("Current configuration:")
    logger.info(f"ADS_SOLR_PROXY_URL: {os.environ.get('ADS_SOLR_PROXY_URL')}")
    logger.info(f"ADS_QUERY_METHOD: {os.environ.get('ADS_QUERY_METHOD')}")
    
    # Run tests
    logger.info("\nTesting basic Solr query...")
    await test_basic_query()
    
    logger.info("\nTesting combined query method...")
    await test_combined_query()

if __name__ == "__main__":
    asyncio.run(main()) 