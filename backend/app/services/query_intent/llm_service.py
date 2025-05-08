"""
LLM Service module for query interpretation.

This module provides functionality to interact with lightweight open-source LLMs,
primarily using Ollama as the backend service to run local models.
"""
import json
import logging
from typing import Dict, Any, Optional, List, Union
import datetime
import requests
from requests.exceptions import RequestException
from pydantic import BaseModel
import aiohttp
import re

from .config import LLM_CONFIG, LLMModel, DEFAULT_MODEL, DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS
from ..ads_service import get_ads_results
from .documentation_service import DocumentationService
from app.core.config import settings

# Configure logger for this module
logger = logging.getLogger(__name__)

class QueryIntent(BaseModel):
    """Model for query intent interpretation results."""
    intent: str
    explanation: str
    transformed_query: str
    intent_confidence: Optional[float] = None

class LLMService:
    """
    Service for interacting with lightweight open-source LLMs via Ollama or other providers.
    
    This service handles communication with LLM providers, formatting prompts,
    and processing responses for query intent interpretation.
    """
    
    _instance = None
    _model_loaded = False
    
    def __new__(cls, *args, **kwargs):
        """
        Create a new instance of LLMService or return the existing one.
        
        Returns:
            LLMService: The singleton instance
        """
        if cls._instance is None:
            cls._instance = super(LLMService, cls).__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        model_name: str = "phi:2.7b",  # Changed default to smaller model
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        provider: str = "ollama",
        api_endpoint: Optional[str] = None,
        prompt_template: Optional[str] = None
    ) -> None:
        """
        Initialize the LLM service with configuration parameters.
        
        Args:
            model_name: Name of the LLM model to use
            temperature: Sampling temperature for generation (0.0-1.0)
            max_tokens: Maximum number of tokens to generate
            provider: LLM provider (ollama, huggingface, openai)
            api_endpoint: API endpoint URL for the LLM provider
            prompt_template: Optional custom prompt template for query understanding
        """
        if not hasattr(self, 'initialized'):
            self.model_name = model_name
            self.temperature = temperature
            self.max_tokens = max_tokens
            self.provider = provider
            self.docs_service = DocumentationService()
            self.prompt_template = prompt_template
            self.initialized = True
            
            # Initialize API endpoint based on provider if not specified
            if api_endpoint:
                self.api_endpoint = api_endpoint
            elif provider == "ollama":
                self.api_endpoint = "http://localhost:11434/api/generate"
            elif provider == "huggingface":
                self.api_endpoint = "https://api-inference.huggingface.co/models/"
            elif provider == "openai":
                self.api_endpoint = "https://api.openai.com/v1/chat/completions"
            else:
                raise ValueError(f"Unsupported provider: {provider}")
                
            logger.info(f"Initialized LLM service with {provider} provider using model {model_name}")
    
    @classmethod
    def from_config(cls) -> "LLMService":
        """
        Create an LLM service instance from configuration settings.
        
        Returns:
            LLMService: Configured LLM service instance
        """
        return cls(
            model_name=settings.LLM_MODEL_NAME,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            provider=settings.LLM_PROVIDER,
            api_endpoint=settings.LLM_API_ENDPOINT,
            prompt_template=settings.LLM_PROMPT_TEMPLATE
        )
    
    def format_prompt(self, query: str) -> str:
        """
        Format the prompt template with the query and relevant documentation.
        
        Args:
            query: The search query to format
            
        Returns:
            str: Formatted prompt with documentation
        """
        # Get relevant documentation for the query
        docs = self.docs_service.retrieve_relevant_docs(query)
        if docs:
            documentation = "\n".join(docs)  # docs is already a list of strings
            logger.info(f"Found relevant documentation for query: {query}")
        else:
            documentation = """
            Available search fields:
            - abs: Abstract
            - title: Title
            - author: Author name
            - year: Publication year
            - bibcode: ADS bibcode
            - doctype: Document type
            - property: Paper properties
            - citation_count: Number of citations
            
            Available operators:
            - AND, OR, NOT
            - "quotes" for exact phrases
            - * for wildcards
            - ~ for fuzzy search
            - [x TO y] for ranges
            - trending(): Find trending papers
            - reviews(): Find review papers
            - similar(): Find similar papers
            - related(): Find related papers
            
            CRITICAL RULES FOR QUERY TRANSFORMATION:
            1. For queries with both author and topic:
               - ALWAYS separate author and topic into different fields
               - Use author:"Lastname, Firstname" for the author part
               - Use abs:"topic" for the topic part
               - NEVER put the topic in the author field
               - NEVER put the author in the topic field
               - ALWAYS use AND to combine author and topic parts
               - Example: "papers by Stephen Hawking about black holes" becomes:
                 (author:"Hawking, S" OR author:"Hawking, Stephen") AND abs:"black holes"
            
            2. For author names:
               - ALWAYS use the format author:"Lastname, Firstname"
               - For common names, include both full name and initial:
                 author:"Lastname, Firstname" OR author:"Lastname, F"
               - NEVER put anything else in the author field
            
            3. For topics:
               - ALWAYS use abs:"topic" for the topic part
               - ALWAYS put multi-word topics in quotes
               - NEVER interpret or expand acronyms (e.g., keep "ADS" as "ADS")
               - NEVER add words that weren't in the original query
            
            4. For year specifications:
               - When a specific year is mentioned (e.g., "2020"), use year:2020 for exact match
               - ONLY use year ranges [x TO y] when explicitly requested (e.g., "papers from 2020 to 2023")
               - NEVER use year ranges for single year specifications
               - Example: "Jarmak 2020" becomes:
                 (author:"Jarmak, S" OR author:"Jarmak, Stephanie") AND year:2020
            
            5. For special operators:
               - When "trending" is mentioned, use trending() operator
                 Example: "trending papers on exoplanets" becomes trending(abs:"exoplanets")
               - When "review" or "reviews" is mentioned, use reviews() operator
                 Example: "review papers on exoplanets" becomes reviews(abs:"exoplanets")
               - When "similar" is mentioned, use similar() operator
                 Example: "papers similar to this one" becomes similar(bibcode:"2023ApJ...")
               - When "related" is mentioned, use related() operator
                 Example: "papers related to exoplanets" becomes related(abs:"exoplanets")
               - ALWAYS put the topic/query inside the operator's parentheses
               - NEVER combine multiple operators in the same query
            
            6. For intent modifiers:
               - Words like "popular", "highly cited", "most cited", "recent" are INTENT MODIFIERS
               - DO NOT include these words in the actual query
               - They should only affect the intent classification and sorting
               - DO NOT use property:popular - this is NOT a valid property
               - DO NOT use property:cited - this is NOT a valid property
               - DO NOT use property:influential - this is NOT a valid property
               - DO NOT use property:refereed - this is NOT needed
               - DO NOT use ANY property: conditions unless explicitly requested
               - DO NOT put intent modifiers in the abstract field
               - DO NOT put intent modifiers in the title field
               - DO NOT put intent modifiers in ANY field
            
            7. IMPORTANT: DO NOT add ANY extra conditions to the query unless explicitly requested:
               - NO property:refereed
               - NO property:cited
               - NO property:popular
               - NO property:influential
               - NO year ranges unless explicitly requested
               - NO citation_count filters
               - NO doctype filters
               - NO ANY other conditions not explicitly mentioned in the query
               - The ONLY fields you should use are author:, abs:, and year:
               - The ONLY operators you should use are AND, OR, quotes, and special operators when appropriate
            
            Examples of good transformations:
            Original: "papers about black holes"
            Intent: topic
            Explanation: Looking for research papers about black holes
            Transformed: abs:"black holes"
            
            Original: "papers by Stephanie Jarmak"
            Intent: author
            Explanation: Looking for papers authored by Stephanie Jarmak
            Transformed: author:"Jarmak, S" OR author:"Jarmak, Stephanie"
            
            Original: "Jarmak 2020"
            Intent: author_year
            Explanation: Looking for papers by Stephanie Jarmak from 2020
            Transformed: (author:"Jarmak, S" OR author:"Jarmak, Stephanie") AND year:2020
            
            Original: "papers by Stephen Hawking from 2020 to 2023"
            Intent: author_year_range
            Explanation: Looking for papers by Stephen Hawking between 2020 and 2023
            Transformed: (author:"Hawking, S" OR author:"Hawking, Stephen") AND year:[2020 TO 2023]
            
            Original: "trending papers on exoplanets"
            Intent: topic_trending
            Explanation: Looking for trending papers about exoplanets
            Transformed: trending(abs:"exoplanets")
            
            Original: "review papers on dark matter"
            Intent: topic_review
            Explanation: Looking for review papers about dark matter
            Transformed: reviews(abs:"dark matter")
            
            Original: "papers similar to this one"
            Intent: similar
            Explanation: Looking for papers similar to the specified paper
            Transformed: similar(bibcode:"2023ApJ...")
            
            Original: "papers related to exoplanets"
            Intent: related
            Explanation: Looking for papers related to exoplanets
            Transformed: related(abs:"exoplanets")
            
            Original: "popular papers by Stephen Hawking on black holes"
            Intent: author_topic_influential
            Explanation: Looking for influential papers by Stephen Hawking about black holes
            Transformed: (author:"Hawking, S" OR author:"Hawking, Stephen") AND abs:"black holes"
            
            Original: "papers by Alberto Accomazzi about ADS"
            Intent: author_topic
            Explanation: Looking for papers by Alberto Accomazzi about ADS
            Transformed: (author:"Accomazzi, A" OR author:"Accomazzi, Alberto") AND abs:"ADS"
            
            Original: "popular papers by Stephanie Jarmak about asteroids"
            Intent: author_topic_influential
            Explanation: Looking for influential papers by Stephanie Jarmak about asteroids
            Transformed: (author:"Jarmak, S" OR author:"Jarmak, Stephanie") AND abs:"asteroids"
            
            Now transform this query: {query}
            
            Return your response in this exact format:
            Intent: [one of: topic, author, author_year, author_year_range, topic_trending, topic_review, similar, related, topic_influential, author_topic_influential, or other simple classification]
            Explanation: [brief explanation of the transformation]
            Transformed Query: [the transformed query]
            """
            logger.warning(f"No relevant documentation found for query: {query}")
        
        # Format the prompt with the actual query
        prompt = f"""
        You are an expert at interpreting search queries and transforming them into effective ADS (Astrophysics Data System) queries.
        Your task is to understand the user's intent and transform their query into a precise ADS query using the available fields and operators.
        
        Here is the ADS search syntax documentation:
        {documentation}
        
        CRITICAL RULES FOR QUERY TRANSFORMATION:
        1. For queries with both author and topic:
           - ALWAYS separate author and topic into different fields
           - Use author:"Lastname, Firstname" for the author part
           - Use abs:"topic" for the topic part
           - NEVER put the topic in the author field
           - NEVER put the author in the topic field
           - ALWAYS use AND to combine author and topic parts
           - Example: "papers by Stephen Hawking about black holes" becomes:
             (author:"Hawking, S" OR author:"Hawking, Stephen") AND abs:"black holes"
        
        2. For author names:
           - ALWAYS use the format author:"Lastname, Firstname"
           - For common names, include both full name and initial:
             author:"Lastname, Firstname" OR author:"Lastname, F"
           - NEVER put anything else in the author field
        
        3. For topics:
           - ALWAYS use abs:"topic" for the topic part
           - ALWAYS put multi-word topics in quotes
           - NEVER interpret or expand acronyms (e.g., keep "ADS" as "ADS")
           - NEVER add words that weren't in the original query
        
        4. For year specifications:
           - When a specific year is mentioned (e.g., "2020"), use year:2020 for exact match
           - ONLY use year ranges [x TO y] when explicitly requested (e.g., "papers from 2020 to 2023")
           - NEVER use year ranges for single year specifications
           - Example: "Jarmak 2020" becomes:
             (author:"Jarmak, S" OR author:"Jarmak, Stephanie") AND year:2020
        
        5. For special operators:
           - When "trending" is mentioned, use trending() operator
             Example: "trending papers on exoplanets" becomes trending(abs:"exoplanets")
           - When "review" or "reviews" is mentioned, use reviews() operator
             Example: "review papers on exoplanets" becomes reviews(abs:"exoplanets")
           - When "similar" is mentioned, use similar() operator
             Example: "papers similar to this one" becomes similar(bibcode:"2023ApJ...")
           - When "related" is mentioned, use related() operator
             Example: "papers related to exoplanets" becomes related(abs:"exoplanets")
           - ALWAYS put the topic/query inside the operator's parentheses
           - NEVER combine multiple operators in the same query
        
        6. For intent modifiers:
           - Words like "popular", "highly cited", "most cited", "recent" are INTENT MODIFIERS
           - DO NOT include these words in the actual query
           - They should only affect the intent classification and sorting
           - DO NOT use property:popular - this is NOT a valid property
           - DO NOT use property:cited - this is NOT a valid property
           - DO NOT use property:influential - this is NOT a valid property
           - DO NOT use property:refereed - this is NOT needed
           - DO NOT use ANY property: conditions unless explicitly requested
           - DO NOT put intent modifiers in the abstract field
           - DO NOT put intent modifiers in the title field
           - DO NOT put intent modifiers in ANY field
        
        7. IMPORTANT: DO NOT add ANY extra conditions to the query unless explicitly requested:
           - NO property:refereed
           - NO property:cited
           - NO property:popular
           - NO property:influential
           - NO year ranges unless explicitly requested
           - NO citation_count filters
           - NO doctype filters
           - NO ANY other conditions not explicitly mentioned in the query
           - The ONLY fields you should use are author:, abs:, and year:
           - The ONLY operators you should use are AND, OR, quotes, and special operators when appropriate
        
        Examples of good transformations:
        Original: "papers about black holes"
        Intent: topic
        Explanation: Looking for research papers about black holes
        Transformed: abs:"black holes"
        
        Original: "papers by Stephanie Jarmak"
        Intent: author
        Explanation: Looking for papers authored by Stephanie Jarmak
        Transformed: author:"Jarmak, S" OR author:"Jarmak, Stephanie"
        
        Original: "Jarmak 2020"
        Intent: author_year
        Explanation: Looking for papers by Stephanie Jarmak from 2020
        Transformed: (author:"Jarmak, S" OR author:"Jarmak, Stephanie") AND year:2020
        
        Original: "papers by Stephen Hawking from 2020 to 2023"
        Intent: author_year_range
        Explanation: Looking for papers by Stephen Hawking between 2020 and 2023
        Transformed: (author:"Hawking, S" OR author:"Hawking, Stephen") AND year:[2020 TO 2023]
        
        Original: "trending papers on exoplanets"
        Intent: topic_trending
        Explanation: Looking for trending papers about exoplanets
        Transformed: trending(abs:"exoplanets")
        
        Original: "review papers on dark matter"
        Intent: topic_review
        Explanation: Looking for review papers about dark matter
        Transformed: reviews(abs:"dark matter")
        
        Original: "papers similar to this one"
        Intent: similar
        Explanation: Looking for papers similar to the specified paper
        Transformed: similar(bibcode:"2023ApJ...")
        
        Original: "papers related to exoplanets"
        Intent: related
        Explanation: Looking for papers related to exoplanets
        Transformed: related(abs:"exoplanets")
        
        Original: "popular papers by Stephen Hawking on black holes"
        Intent: author_topic_influential
        Explanation: Looking for influential papers by Stephen Hawking about black holes
        Transformed: (author:"Hawking, S" OR author:"Hawking, Stephen") AND abs:"black holes"
        
        Original: "papers by Alberto Accomazzi about ADS"
        Intent: author_topic
        Explanation: Looking for papers by Alberto Accomazzi about ADS
        Transformed: (author:"Accomazzi, A" OR author:"Accomazzi, Alberto") AND abs:"ADS"
        
        Original: "popular papers by Stephanie Jarmak about asteroids"
        Intent: author_topic_influential
        Explanation: Looking for influential papers by Stephanie Jarmak about asteroids
        Transformed: (author:"Jarmak, S" OR author:"Jarmak, Stephanie") AND abs:"asteroids"
        
        Now transform this query: {query}
        
        Return your response in this exact format:
        Intent: [one of: topic, author, author_year, author_year_range, topic_trending, topic_review, similar, related, topic_influential, author_topic_influential, or other simple classification]
        Explanation: [brief explanation of the transformation]
        Transformed Query: [the transformed query]
        """
        
        logger.info(f"Formatted prompt with query: {query}")
        return prompt
    
    async def _ensure_model_loaded(self) -> None:
        """
        Ensure the model is loaded before making requests.
        This implements lazy loading to reduce memory usage.
        """
        if not self._model_loaded:
            try:
                # For Ollama, we can check if the model is available
                if self.provider == "ollama":
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{self.api_endpoint}/tags") as response:
                            if response.status == 200:
                                models = await response.json()
                                if not any(m['name'] == self.model_name for m in models.get('models', [])):
                                    logger.warning(f"Model {self.model_name} not found, falling back to phi:2.7b")
                                    self.model_name = "phi:2.7b"
                
                self._model_loaded = True
                logger.info(f"Model {self.model_name} is ready for use")
            except Exception as e:
                logger.error(f"Error loading model: {str(e)}")
                raise

    async def query_llm(self, prompt: str) -> Optional[str]:
        """
        Send a query to the LLM provider and get the response.
        
        Args:
            prompt: Formatted prompt for the LLM provider
            
        Returns:
            Optional[str]: LLM response text or None if the request failed
        """
        try:
            await self._ensure_model_loaded()
            
            logger.info(f"Sending request to LLM provider: {self.provider}")
            logger.info(f"Using model: {self.model_name}")
            logger.info(f"Temperature: {self.temperature}")
            logger.info(f"Max tokens: {self.max_tokens}")
            
            # Format the request based on provider
            if self.provider == "ollama":
                request_data = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens
                    }
                }
                logger.info(f"Sending request to Ollama: {request_data}")
            elif self.provider == "openai":
                request_data = {
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens
                }
            else:
                request_data = {"inputs": prompt}
            
            # Make the request using aiohttp
            logger.info(f"Making request to {self.api_endpoint}")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_endpoint,
                    json=request_data,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                ) as response:
                    logger.info(f"Response status code: {response.status}")
                    logger.info(f"Response headers: {response.headers}")
                    
                    response.raise_for_status()
                    response_data = await response.json()
                    logger.info(f"Response data: {response_data}")
                    
                    # Extract response text based on provider format
                    if self.provider == "ollama":
                        response_text = response_data.get("response", "")
                        logger.info(f"Extracted response text: {response_text}")
                        return response_text
                    elif self.provider == "openai":
                        response_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        logger.info(f"Extracted response text: {response_text}")
                        return response_text
                    else:
                        response_text = response_data.get("output", "")
                        logger.info(f"Extracted response text: {response_text}")
                        return response_text
                
        except Exception as e:
            logger.error(f"Error querying LLM: {str(e)}")
            logger.error(f"Request data: {request_data}")
            return None
    
    def extract_structured_response(self, response: str) -> Dict[str, Any]:
        """
        Extract structured data from LLM response.
        
        Args:
            response: LLM response string
            
        Returns:
            Dict[str, Any]: Structured response data
        """
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM response as JSON")
            return None
    
    async def interpret_query(self, query: str) -> QueryIntent:
        """
        Interpret a query using the LLM service.
        
        Args:
            query: The query to interpret
            
        Returns:
            QueryIntent: The interpreted query intent
        """
        await self._ensure_model_loaded()
        
        try:
            # Check if query already has valid field prefixes
            valid_fields = ["author:", "abs:", "title:", "year:", "citation_count:"]
            if any(query.startswith(field) for field in valid_fields):
                logger.info(f"Query already has valid field prefix: {query}")
                return QueryIntent(
                    intent="direct",
                    explanation="Using query as provided with field prefix",
                    transformed_query=query,
                    intent_confidence=1.0
                )
            
            # Format prompt for LLM
            prompt = self.format_prompt(query)
            logger.info(f"Formatted prompt for LLM: {prompt}")
            
            # Query LLM
            response = await self.query_llm(prompt)
            logger.info(f"LLM response: {response}")
            
            # Parse response
            try:
                # Extract intent, explanation, and transformed query
                intent = None
                explanation = None
                transformed_query = None
                
                # Split response into lines
                lines = response.strip().split('\n')
                
                # Find intent line
                for line in lines:
                    if line.startswith("Intent:"):
                        intent = line.replace("Intent:", "").strip()
                        break
                
                # Find explanation line
                for line in lines:
                    if line.startswith("Explanation:"):
                        explanation = line.replace("Explanation:", "").strip()
                        break
                
                # Find transformed query line
                for line in lines:
                    if line.startswith("Transformed Query:"):
                        transformed_query = line.replace("Transformed Query:", "").strip()
                        break
                
                # Validate parsed values
                if not all([intent, explanation, transformed_query]):
                    raise ValueError("Could not parse all required fields from LLM response")
                
                # Clean up the transformed query - remove any property: conditions
                transformed_query = re.sub(r'\s*AND\s*property:[^\s)]+', '', transformed_query)
                transformed_query = re.sub(r'property:[^\s)]+\s*AND\s*', '', transformed_query)
                
                # Ensure the query is properly formatted
                if "author:" in transformed_query and "abs:" in transformed_query:
                    # Make sure author and abs parts are properly separated
                    if not re.search(r'author:[^)]+\)\s*AND\s*abs:', transformed_query):
                        # If not properly formatted, try to fix it
                        author_part = re.search(r'author:[^)]+\)', transformed_query)
                        abs_part = re.search(r'abs:[^)]+\)', transformed_query)
                        if author_part and abs_part:
                            transformed_query = f"{author_part.group(0)} AND {abs_part.group(0)}"
                
                return QueryIntent(
                    intent=intent,
                    explanation=explanation,
                    transformed_query=transformed_query,
                    intent_confidence=0.9  # Default confidence
                )
                
            except Exception as e:
                logger.error(f"Error parsing LLM response: {str(e)}")
                # Fallback to basic query
                return QueryIntent(
                    intent="basic",
                    explanation="Using basic query interpretation",
                    transformed_query=f'abs:"{query}"',
                    intent_confidence=0.5
                )
                
        except Exception as e:
            logger.error(f"Error in interpret_query: {str(e)}")
            # Fallback to basic query
            return QueryIntent(
                intent="error",
                explanation=f"Error interpreting query: {str(e)}",
                transformed_query=query,
                intent_confidence=0.0
            )
            
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the LLM service.
        
        Returns:
            Dict[str, Any]: Health check results
        """
        try:
            # Simple prompt to check if the service is responding
            prompt_data = self.format_prompt("Hello")
            response = self.query_llm(prompt_data)
            
            if response:
                return {
                    "status": "ok",
                    "model": self.model_name,
                    "message": "LLM service is operational"
                }
            else:
                return {
                    "status": "error",
                    "model": self.model_name,
                    "message": "LLM service returned empty response"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "model": self.model_name,
                "message": f"LLM service error: {str(e)}"
            }

    async def search_with_transformed_query(
        self,
        query: str,
        fields: List[str] = None,
        num_results: int = 20,
        use_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Transform a query and search using Solr service.
        
        Args:
            query: Original search query
            fields: List of fields to retrieve
            num_results: Maximum number of results to return
            use_cache: Whether to use caching
            
        Returns:
            Dict[str, Any]: Search results with transformation info
        """
        try:
            # Interpret the query
            intent_result = await self.interpret_query(query)
            transformed_query = intent_result.transformed_query
            
            logger.info(f"Transformed query: {transformed_query}")
            logger.info(f"Query intent: {intent_result.intent}")
            
            # Determine sort parameter based on intent
            sort_param = None
            if "influential" in intent_result.intent or "highly cited" in intent_result.intent or "popular" in intent_result.intent:
                sort_param = "citation_count desc"
                logger.info(f"Sorting by citation count for intent: {intent_result.intent}")
            elif "recent" in intent_result.intent:
                sort_param = "date desc"
                logger.info(f"Sorting by date for intent: {intent_result.intent}")
            
            # Get results from Solr service
            results = await get_solr_results(
                query=transformed_query,
                fields=fields,
                num_results=num_results,
                use_cache=use_cache,
                sort=sort_param  # Pass the sort parameter
            )
            
            # Handle case when no results are returned
            if not results:  # This handles both None and empty list
                logger.warning("No results returned from Solr service")
                return {
                    "original_query": query,
                    "transformed_query": transformed_query,
                    "intent": intent_result.intent,
                    "explanation": intent_result.explanation,
                    "intent_confidence": intent_result.intent_confidence or 1.0,
                    "search_results": {
                        "num_found": 0,
                        "results": []
                    }
                }
            
            # Format results
            formatted_results = []
            for result in results:
                # Format authors as a list of strings
                authors = []
                if 'author' in result:
                    for author in result['author']:
                        # Split author name into parts
                        parts = author.split(',')
                        if len(parts) >= 2:
                            last_name = parts[0].strip()
                            first_name = parts[1].strip()
                            authors.append(f"{first_name} {last_name}")
                        else:
                            authors.append(author)
                
                # Create links
                links = {
                    "ads": f"https://ui.adsabs.harvard.edu/abs/{result['bibcode']}/abstract",
                    "pdf": f"https://ui.adsabs.harvard.edu/link_gateway/{result['bibcode']}/PUB_PDF" if 'property' in result and 'PUB_PDF' in result['property'] else None,
                    "arxiv": f"https://arxiv.org/abs/{result['bibcode']}" if 'property' in result and 'EPRINT_HTML' in result['property'] else None
                }
                
                # Format the result
                formatted_result = {
                    "id": str(result.get('id')),
                    "bibcode": result.get('bibcode'),
                    "title": result.get('title'),
                    "author": authors,
                    "year": int(result.get('year')) if result.get('year') else None,
                    "citation_count": int(result.get('citation_count', 0)),
                    "abstract": result.get('abstract'),
                    "doctype": result.get('doctype'),
                    "property": result.get('property', []),
                    "links": links,
                    "journal": result.get('pub'),
                    "volume": result.get('volume'),
                    "page": result.get('page'),
                    "doi": result.get('doi'),
                    "keywords": result.get('keyword', [])
                }
                formatted_results.append(formatted_result)
            
            return {
                "original_query": query,
                "transformed_query": intent_result.transformed_query,
                "intent": intent_result.intent,
                "explanation": intent_result.explanation,
                "intent_confidence": intent_result.intent_confidence or 1.0,
                "search_results": {
                    "num_found": len(formatted_results),
                    "results": formatted_results
                }
            }
            
        except Exception as e:
            logger.error(f"Error in search_with_transformed_query: {str(e)}")
            return {
                "original_query": query,
                "transformed_query": query,
                "intent": "error",
                "explanation": f"Error processing query: {str(e)}",
                "intent_confidence": 0,
                "search_results": {
                    "num_found": 0,
                    "results": []
                }
            } 