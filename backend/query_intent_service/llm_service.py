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

from .config import LLM_CONFIG, LLMModel, DEFAULT_MODEL, DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS

# Configure logger for this module
logger = logging.getLogger(__name__)

# Default prompt template for query understanding
DEFAULT_PROMPT_TEMPLATE = """You are an expert query understanding assistant.
Your task is to analyze search queries and identify the user's intent.
Based on their intent, transform the original query to make it more effective.

Respond ONLY with a JSON object containing:
1. "original_query": The user's original query
2. "intent": The identified intent (e.g., recent, highly_cited, author_search, review, etc.)
3. "intent_confidence": Your confidence in the intent (0.0-1.0)
4. "transformed_query": The query with appropriate search syntax
5. "explanation": A brief explanation of how you transformed the query

Example intents:
- recent: For finding recent content (add time-based filters)
- highly_cited: For finding influential content (add citation/impact filters)
- author_search: For finding content by specific authors
- review: For finding review/summary content
- comparison: For finding content comparing topics
- definition: For finding definitions or explanations

Keep the transformed query focused on the user's original intent while making it more effective."""

class LLMService:
    """
    Service for interacting with lightweight open-source LLMs via Ollama or other providers.
    
    This service handles communication with LLM providers, formatting prompts,
    and processing responses for query intent interpretation.
    """
    
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
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
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.provider = provider
        
        # Get model-specific prompt template if available
        model_config = LLM_CONFIG.get("models", {}).get(model_name, {})
        model_prompt_template = model_config.get("default_prompt_template")
        
        # Use provided template, model-specific template, or default template
        self.prompt_template = prompt_template or model_prompt_template or DEFAULT_PROMPT_TEMPLATE
        
        # Initialize API endpoint based on provider if not specified
        if api_endpoint:
            self.api_endpoint = api_endpoint
        elif provider == "ollama":
            self.api_endpoint = "http://localhost:11434/api/generate"
        else:
            self.api_endpoint = None
            
        logger.info(f"Initialized LLM service with {provider} provider using model {model_name}")
    
    @classmethod
    def from_config(cls) -> "LLMService":
        """
        Create an LLM service instance from configuration settings.
        
        Returns:
            LLMService: Configured LLM service instance
        """
        return cls(
            model_name=LLM_CONFIG.get("model", DEFAULT_MODEL),
            temperature=LLM_CONFIG.get("temperature", DEFAULT_TEMPERATURE),
            max_tokens=LLM_CONFIG.get("max_tokens", DEFAULT_MAX_TOKENS),
            provider=LLM_CONFIG.get("provider", "ollama"),
            api_endpoint=LLM_CONFIG.get("api_endpoint"),
            prompt_template=LLM_CONFIG.get("prompt_template")
        )
    
    def format_prompt(self, query: str, system_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Format a prompt for the LLM based on the provider and model.
        
        Args:
            query: User query to process
            system_message: Optional system message for instruction-tuned models
            
        Returns:
            Dict[str, Any]: Formatted prompt data
        """
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        if not system_message:
            system_message = self.prompt_template
            
        if self.provider == "ollama":
            # Format for Ollama API
            prompt_data = {
                "model": self.model_name,
                "prompt": query,
                "system": system_message,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens
                }
            }
        elif self.provider == "openai":
            # Format for OpenAI-compatible API
            prompt_data = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": query}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
        else:
            # Default format
            prompt_data = {
                "model": self.model_name,
                "prompt": query,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
        
        return prompt_data
    
    def query_llm(self, prompt_data: Dict[str, Any]) -> Optional[str]:
        """
        Send a query to the LLM provider and get the response.
        
        Args:
            prompt_data: Formatted prompt data for the LLM provider
            
        Returns:
            Optional[str]: LLM response text or None if the request failed
        """
        try:
            logger.debug(f"Sending request to LLM provider: {self.provider}")
            
            response = requests.post(
                self.api_endpoint,
                json=prompt_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            response.raise_for_status()
            response_data = response.json()
            
            # Extract response text based on provider format
            if self.provider == "ollama":
                return response_data.get("response", "")
            elif self.provider == "openai":
                return response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            elif self.provider == "huggingface":
                # Handle Hugging Face API response format
                if isinstance(response_data, list):
                    return response_data[0].get("generated_text", "")
                return response_data.get("generated_text", "")
            else:
                return response_data.get("output", "")
                
        except RequestException as e:
            logger.error(f"Error querying LLM: {str(e)}")
            return None
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM response as JSON")
            return None
    
    def extract_structured_response(self, llm_response: str) -> Optional[Dict[str, Any]]:
        """
        Extract structured data from LLM response text.
        
        Args:
            llm_response: Raw text response from the LLM
            
        Returns:
            Optional[Dict[str, Any]]: Structured response data or None if parsing failed
        """
        # Try to extract JSON from the response text
        try:
            # Find JSON-like content in the text
            start_idx = llm_response.find("{")
            end_idx = llm_response.rfind("}") + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = llm_response[start_idx:end_idx]
                return json.loads(json_str)
            
            # If no JSON found, try to parse the whole response
            return json.loads(llm_response)
            
        except (json.JSONDecodeError, ValueError):
            logger.warning("Failed to extract structured data from LLM response")
            return None
    
    def interpret_query(self, query: str) -> Dict[str, Any]:
        """
        Interpret a search query to identify user intent and transform the query.
        
        Args:
            query: Original user search query
            
        Returns:
            Dict[str, Any]: Result containing original query, intent, and transformed query
        """
        logger.info(f"Interpreting query: {query}")
        
        # Format the prompt and query the LLM
        prompt_data = self.format_prompt(query)
        llm_response = self.query_llm(prompt_data)
        
        if not llm_response:
            # If LLM query failed, return basic response
            return {
                "original_query": query,
                "intent": "unknown",
                "intent_confidence": 0.0,
                "transformed_query": query,
                "explanation": "Failed to interpret query due to LLM service error."
            }
        
        # Extract structured data from response
        structured_response = self.extract_structured_response(llm_response)
        
        if structured_response:
            # Ensure required fields are present
            result = {
                "original_query": structured_response.get("original_query", query),
                "intent": structured_response.get("intent", "unknown"),
                "intent_confidence": structured_response.get("intent_confidence", 0.5),
                "transformed_query": structured_response.get("transformed_query", query),
                "explanation": structured_response.get("explanation", "No explanation provided.")
            }
        else:
            # If parsing failed, return basic response with the raw LLM output
            result = {
                "original_query": query,
                "intent": "unknown",
                "intent_confidence": 0.0,
                "transformed_query": query,
                "explanation": "Failed to parse LLM response. Raw output: " + llm_response[:100] + "..."
            }
        
        logger.info(f"Query interpreted with intent: {result['intent']}")
        return result
            
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
                    "provider": self.provider,
                    "model": self.model_name,
                    "message": "LLM service is operational"
                }
            else:
                return {
                    "status": "error",
                    "provider": self.provider,
                    "model": self.model_name,
                    "message": "LLM service returned empty response"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "provider": self.provider,
                "model": self.model_name,
                "message": f"LLM service error: {str(e)}"
            } 