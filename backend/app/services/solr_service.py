"""
Solr Service module for handling search operations.

This module provides functionality to interact with the ADS Solr proxy for searching papers.
"""
import os
import logging
from typing import Dict, Any, Optional, List
import aiohttp
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from app.services.query_intent.llm_service import LLMService

# Configure logger for this module
logger = logging.getLogger(__name__)

# Load environment variables from backend/.env
backend_dir = Path(__file__).parent.parent.parent
env_path = backend_dir / '.env'
load_dotenv(dotenv_path=env_path)

# API Constants
ADS_SOLR_PROXY_URL = os.environ.get("ADS_SOLR_PROXY_URL", "https://adsabs.harvard.edu/solr/collection1/select")
ADS_SOLR_USERNAME = os.environ.get("ADS_SOLR_USERNAME", "ads")
ADS_SOLR_PASSWORD = os.environ.get("ADS_SOLR_PASSWORD", "")
DEFAULT_ROWS = 20
TIMEOUT_SECONDS = 15

class SolrService:
    """Service for interacting with the ADS Solr proxy."""
    
    def __init__(self):
        """Initialize the Solr service with configuration."""
        self.api_url = ADS_SOLR_PROXY_URL
        self.solr_username = ADS_SOLR_USERNAME
        self.solr_password = ADS_SOLR_PASSWORD
        if not self.solr_password:
            logger.warning("ADS Solr password not found in environment variables")
        else:
            logger.info("ADS Solr password found in environment variables")
            logger.info(f"Using Solr proxy URL: {self.api_url}")
    
    async def search(self, query: str, intent: str = None, rows: int = DEFAULT_ROWS) -> Dict[str, Any]:
        """
        Search for papers using the ADS Solr proxy.
        
        Args:
            query: Pre-transformed search query
            intent: Optional query intent (not used in this implementation)
            rows: Number of results to return
            
        Returns:
            Dict[str, Any]: Search results in format:
                {
                    "numFound": int,
                    "docs": List[Dict]
                }
        """
        try:
            if not self.solr_password:
                logger.error("ADS Solr password not configured")
                return self._get_mock_results(query)
            
            # Set up query parameters
            params = {
                "q": query,
                "rows": rows,
                "wt": "json",
                "fl": "id,bibcode,title,author,year,citation_count,abstract"  # Specify fields to return
            }
            
            # Add sort parameter based on intent
            if intent:
                if "influential" in intent or "highly cited" in intent or "popular" in intent:
                    params["sort"] = "citation_count desc"
                    logger.info(f"Sorting by citation count for intent: {intent}")
                elif "recent" in intent:
                    params["sort"] = "date desc"
                    logger.info(f"Sorting by date for intent: {intent}")
            
            logger.info(f"Making request to Solr proxy with URL: {self.api_url}")
            logger.info(f"Query parameters: {params}")
            
            # Make request to Solr proxy
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.api_url,
                    params=params,
                    auth=aiohttp.BasicAuth(self.solr_username, self.solr_password),
                    timeout=TIMEOUT_SECONDS,
                    allow_redirects=True  # Allow redirects
                ) as response:
                    response_text = await response.text()
                    logger.info(f"Solr proxy response status: {response.status}")
                    logger.info(f"Solr proxy response headers: {response.headers}")
                    
                    if response.status != 200:
                        logger.error(f"Error from Solr proxy: Status {response.status}")
                        logger.error(f"Response text: {response_text}")
                        return self._get_mock_results(query)
                    
                    # Parse the response
                    try:
                        result = await response.json()
                        logger.info("Successfully parsed Solr response")
                        # Process the results before returning
                        return self._process_results(result)
                    except Exception as e:
                        logger.error(f"Error parsing Solr response: {str(e)}")
                        logger.error(f"Response text: {response_text}")
                        return self._get_mock_results(query)
                    
        except Exception as e:
            logger.error(f"Error searching Solr proxy: {str(e)}")
            return self._get_mock_results(query)
    
    async def _transform_query(self, query: str) -> str:
        """
        Transform natural language query to structured ADS query using LLM.
        
        Args:
            query: Natural language query
            
        Returns:
            str: Structured ADS query
        """
        try:
            logger.info(f"Transforming natural language query: {query}")
            
            # Format the prompt with the query
            prompt = self.llm_service.format_prompt(query)
            logger.debug(f"Formatted prompt: {prompt}")
            
            # Get transformed query from LLM
            transformed_query = await self.llm_service.query_llm(prompt)
            if not transformed_query:
                logger.error("LLM failed to transform query - no response received")
                return self._create_basic_query(query)
            
            logger.debug(f"Raw LLM response: {transformed_query}")
            
            # Try to parse the response as JSON first
            try:
                import json
                response_dict = json.loads(transformed_query)
                if isinstance(response_dict, dict) and "transformed_query" in response_dict:
                    structured_query = response_dict["transformed_query"]
                    logger.info(f"Successfully extracted structured query from JSON: {structured_query}")
                    return structured_query
            except json.JSONDecodeError:
                pass  # Not JSON, continue with text parsing
            
            # Parse the response as text
            lines = transformed_query.strip().split('\n')
            for line in lines:
                # Look for the transformed query in various formats
                if line.startswith('Transformed Query:'):
                    structured_query = line.split('Transformed Query:')[1].strip()
                    logger.info(f"Successfully extracted structured query from text: {structured_query}")
                    return structured_query
                elif 'transformed_query' in line.lower():
                    # Handle JSON-like format in text
                    parts = line.split('transformed_query', 1)
                    if len(parts) > 1:
                        structured_query = parts[1].strip().strip('":,')
                        logger.info(f"Successfully extracted structured query from JSON-like text: {structured_query}")
                        return structured_query
            
            # If we couldn't find the transformed query in the expected format,
            # try to extract any ADS query syntax from the response
            for line in lines:
                # Look for valid ADS query syntax
                if any(field in line.lower() for field in ['title:', 'author:', 'year:', 'abs:', 'bibcode:', 'doctype:', 'property:']):
                    # Clean up the line to get just the query part
                    query_part = line.strip().strip('":,')
                    if any(field in query_part.lower() for field in ['title:', 'author:', 'year:', 'abs:', 'bibcode:', 'doctype:', 'property:']):
                        logger.info(f"Found potential ADS query syntax in response: {query_part}")
                        return query_part
            
            # If all else fails, create a basic query
            logger.warning("Could not find structured query in LLM response, creating basic query")
            return self._create_basic_query(query)
            
        except Exception as e:
            logger.error(f"Error transforming query: {str(e)}", exc_info=True)
            return self._create_basic_query(query)
    
    def _clean_and_validate_query(self, query: str) -> str:
        """
        Clean and validate a Solr query to ensure it's valid.
        
        Args:
            query: Raw query string
            
        Returns:
            str: Cleaned and validated query
        """
        try:
            # Remove invalid functions and operators
            invalid_patterns = [
                'trending(', 'sort:', 'boost:', 'fq:', 'facet.', 'stats.',
                'group.', 'spellcheck.', 'hl.', 'fl:', 'rows:', 'start:',
                'wt:', 'json', 'xml', 'csv', 'python', 'indent:'
            ]
            
            cleaned_query = query
            for pattern in invalid_patterns:
                cleaned_query = cleaned_query.replace(pattern, '')
            
            # Remove any trailing commas or semicolons
            cleaned_query = cleaned_query.strip().rstrip(',;')
            
            # Fix parentheses issues
            # Remove any unmatched parentheses
            open_count = cleaned_query.count('(')
            close_count = cleaned_query.count(')')
            if open_count > close_count:
                cleaned_query = cleaned_query.rstrip('(')
            elif close_count > open_count:
                cleaned_query = cleaned_query.rstrip(')')
            
            # Remove any trailing operators
            cleaned_query = cleaned_query.rstrip(' AND').rstrip(' OR').rstrip(' NOT')
            
            # If the query is empty after cleaning, create a basic query
            if not cleaned_query.strip():
                logger.warning("Query is empty after cleaning")
                return self._create_basic_query(query)
            
            # Check for duplicate field prefixes
            valid_fields = ['title:', 'author:', 'year:', 'abs:', 'bibcode:', 'doctype:', 'property:']
            
            # Find the first valid field in the query
            first_field = None
            first_field_index = float('inf')
            for field in valid_fields:
                index = cleaned_query.lower().find(field)
                if index != -1 and index < first_field_index:
                    first_field = field
                    first_field_index = index
            
            if first_field:
                # Extract the value after the first field
                value = cleaned_query[first_field_index + len(first_field):].strip()
                
                # Remove any other field prefixes from the value
                for field in valid_fields:
                    value = value.replace(field, '')
                
                # Create a clean query with just the first field and its value
                cleaned_query = first_field + value
            
            # Validate that the query contains at least one valid field
            if not any(field in cleaned_query.lower() for field in valid_fields):
                logger.warning("Query does not contain any valid fields after cleaning")
                return self._create_basic_query(query)
            
            # Ensure proper field syntax
            for field in valid_fields:
                if cleaned_query.lower().startswith(field):
                    # Get the value after the field
                    value = cleaned_query[len(field):].strip()
                    
                    # If the field has no value after it, use the original query terms
                    if not value:
                        terms = query.split()
                        # Remove common words like "papers", "on", "about", etc.
                        topic_words = [word for word in terms if word.lower() not in ["papers", "on", "about", "the", "a", "an"]]
                        if topic_words:
                            cleaned_query = field + ' '.join(topic_words)
                        else:
                            cleaned_query = field + ' '.join(terms)
                    
                    # If the field has only a wildcard after it, use the original query terms
                    elif value == "*":
                        terms = query.split()
                        # Remove common words like "papers", "on", "about", etc.
                        topic_words = [word for word in terms if word.lower() not in ["papers", "on", "about", "the", "a", "an"]]
                        if topic_words:
                            cleaned_query = field + ' '.join(topic_words)
                        else:
                            cleaned_query = field + ' '.join(terms)
                    
                    # If the field has a wildcard at the start of the value, remove it
                    elif value.startswith("*"):
                        cleaned_query = field + value.lstrip("*")
            
            logger.info(f"Cleaned and validated query: {cleaned_query}")
            return cleaned_query
            
        except Exception as e:
            logger.error(f"Error cleaning query: {str(e)}")
            return self._create_basic_query(query)
    
    def _create_basic_query(self, query: str) -> str:
        """
        Create a basic ADS query from the original terms.
        
        Args:
            query: Original search query
            
        Returns:
            str: Basic ADS query
        """
        terms = query.split()
        basic_query = f"(title:{' AND title:'.join(terms)}) OR (abs:{' AND abs:'.join(terms)})"
        logger.info(f"Created basic query: {basic_query}")
        return basic_query
    
    def _process_results(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw Solr results into standardized format.
        
        Args:
            data: Raw Solr response data
            
        Returns:
            Dict[str, Any]: Processed results in format:
                {
                    "numFound": int,
                    "docs": List[Dict]
                }
        """
        try:
            docs = data.get("response", {}).get("docs", [])
            return {
                "numFound": data.get("response", {}).get("numFound", 0),
                "docs": docs
            }
        except Exception as e:
            logger.error(f"Error processing Solr results: {str(e)}")
            return self._get_mock_results("")
    
    def _get_mock_results(self, query: str) -> Dict[str, Any]:
        """
        Generate mock results for testing or fallback.
        
        Args:
            query: Original search query
            
        Returns:
            Dict[str, Any]: Mock search results in format:
                {
                    "numFound": int,
                    "docs": List[Dict]
                }
        """
        logger.warning(f"Using mock results for query: {query}")
        return {
            "numFound": 0,
            "docs": []
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the Solr service.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            if not self.solr_password:
                return {
                    "status": "unhealthy",
                    "error": "ADS Solr password not configured"
                }
            
            # Make a simple query to check connectivity
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.api_url,
                    params={"q": "*:*", "rows": 1},
                    auth=aiohttp.BasicAuth(self.solr_username, self.solr_password),
                    timeout=TIMEOUT_SECONDS,
                    allow_redirects=True  # Allow redirects
                ) as response:
                    if response.status == 200:
                        return {
                            "status": "healthy",
                            "url": self.api_url
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "error": f"Solr proxy returned status {response.status}"
                        }
                    
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def get_solr_results(
        self,
        query: str,
        fields: List[str] = None,
        num_results: int = 20,
        use_cache: bool = False,
        sort: str = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get search results from Solr.
        
        Args:
            query: Search query
            fields: List of fields to retrieve
            num_results: Maximum number of results to return
            use_cache: Whether to use caching
            sort: Sort parameter (e.g., "citation_count desc")
            
        Returns:
            Optional[List[Dict[str, Any]]]: List of search results or None if error
        """
        try:
            # Prepare query parameters
            params = {
                "q": query,
                "rows": num_results,
                "fl": ",".join(fields) if fields else "*",
                "wt": "json"
            }
            
            # Add sort parameter as a separate parameter
            if sort:
                params["sort"] = sort
                logger.info(f"Adding sort parameter: {sort}")
            
            # Log the request
            logger.info(f"Making Solr request with params: {params}")
            
            # Make request to Solr
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.api_url,
                    params=params,
                    auth=aiohttp.BasicAuth(self.solr_username, self.solr_password),
                    timeout=TIMEOUT_SECONDS,
                    allow_redirects=True  # Allow redirects
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Extract results
                    if "response" in data and "docs" in data["response"]:
                        return data["response"]["docs"]
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting Solr results: {str(e)}")
            return None 