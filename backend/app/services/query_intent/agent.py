"""
Query transformation agent for astronomy search.

This module implements an agent that detects user intent in search queries
and transforms them into more effective queries with appropriate search syntax.
"""
import logging
import datetime
import re
import json
from typing import Dict, Any, List, Optional

import requests

# Configure logger for this module
logger = logging.getLogger(__name__)

# Common query indicators for different intents
RECENT_INDICATORS = ["recent", "latest", "new", "current", "last year", "2023", "2022", "2021"]
AUTHOR_INDICATORS = ["authored by", "written by", "papers by", "works by", "articles by", "publications by"]
REVIEW_INDICATORS = ["review", "overview", "survey", "summary", "state of the art", "state-of-the-art"]
CITATION_INDICATORS = ["highly cited", "most cited", "influential", "important", "significant"]


class QueryAgent:
    """
    Agent for transforming user queries based on inferred intent.
    
    This agent coordinates detecting search intent and transforming queries
    with appropriate search syntax, using both rule-based and LLM-based approaches.
    """
    
    def __init__(
        self,
        use_llm: bool = False,
        llm_endpoint: str = "http://localhost:11434/api/generate",
        llm_model: str = "mistral:7b-instruct-v0.2"
    ) -> None:
        """
        Initialize the query agent.
        
        Args:
            use_llm: Whether to use an LLM for query interpretation
            llm_endpoint: API endpoint for the LLM service
            llm_model: Name of the LLM model to use
        """
        self.use_llm = use_llm
        self.llm_endpoint = llm_endpoint
        self.llm_model = llm_model
        logger.info(f"Initialized query agent with use_llm={use_llm}")
    
    def transform_query(self, original_query: str) -> Dict[str, Any]:
        """
        Transform a user query based on detected intent.
        
        Args:
            original_query: User's original search query
            
        Returns:
            Dict[str, Any]: Result containing original query, intent, and transformed query
        """
        if not original_query or original_query.strip() == "":
            return {
                "original_query": original_query,
                "intent": "empty",
                "intent_confidence": 1.0,
                "transformed_query": original_query,
                "explanation": "Empty query provided."
            }
        
        # First, attempt rule-based transformation
        rule_based_result = self._apply_rule_based_transformation(original_query)
        
        # If rule-based transformation was confident, use it
        if rule_based_result:
            logger.info(f"Rule-based transformation applied with intent: {rule_based_result['intent']}")
            return rule_based_result
        
        # If LLM is enabled and no clear rule applies, try using the LLM
        if self.use_llm:
            try:
                llm_result = self._query_llm(original_query)
                if llm_result:
                    logger.info(f"LLM-based transformation applied with intent: {llm_result['intent']}")
                    return llm_result
            except Exception as e:
                logger.error(f"Error using LLM for query transformation: {str(e)}")
        
        # Fallback to the original query if no transformation was applied
        return {
            "original_query": original_query,
            "intent": "unknown",
            "intent_confidence": 0.0,
            "transformed_query": original_query,
            "explanation": "No clear intent detected. Using original query."
        }
    
    def _apply_rule_based_transformation(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Apply rule-based transformations without using an LLM.
        
        Args:
            query: Original user query
            
        Returns:
            Optional[Dict[str, Any]]: Transformation result or None if no clear rule applies
        """
        query_lower = query.lower()
        
        # Check for recent papers intent
        if any(indicator in query_lower for indicator in RECENT_INDICATORS):
            current_year = datetime.datetime.now().year
            year_range = f"{current_year-1}-{current_year}"
            
            # Remove time indicators from query
            clean_query = query
            for indicator in RECENT_INDICATORS:
                clean_query = re.sub(r'\b' + re.escape(indicator) + r'\b', '', clean_query, flags=re.IGNORECASE)
            
            clean_query = clean_query.strip()
            transformed_query = f"{clean_query} year:{year_range}"
            
            return {
                "original_query": query,
                "intent": "recent",
                "intent_confidence": 0.9,
                "transformed_query": transformed_query,
                "explanation": f"Added year:{year_range} to find recent papers on this topic."
            }
        
        # Check for author search intent
        if any(indicator in query_lower for indicator in AUTHOR_INDICATORS):
            for indicator in AUTHOR_INDICATORS:
                if indicator in query_lower:
                    # Try to extract author name after the indicator
                    pattern = re.escape(indicator) + r'\s+([A-Za-z\s,.-]+)'
                    match = re.search(pattern, query, re.IGNORECASE)
                    
                    if match:
                        author_name = match.group(1).strip()
                        # Check if name is in "Lastname, Firstname" format
                        if "," in author_name:
                            transformed_query = f'author:"{author_name}"'
                        else:
                            # Try to convert to ADS format (simple case)
                            name_parts = author_name.split()
                            if len(name_parts) >= 2:
                                lastname = name_parts[-1]
                                firstname = " ".join(name_parts[:-1])
                                transformed_query = f'author:"{lastname}, {firstname}"'
                            else:
                                transformed_query = f'author:"{author_name}"'
                        
                        return {
                            "original_query": query,
                            "intent": "author_search",
                            "intent_confidence": 0.85,
                            "transformed_query": transformed_query,
                            "explanation": f"Formatted author search for {author_name} using ADS syntax."
                        }
        
        # Check for review papers intent
        if any(indicator in query_lower for indicator in REVIEW_INDICATORS):
            # Remove review indicators from query
            clean_query = query
            for indicator in REVIEW_INDICATORS:
                clean_query = re.sub(r'\b' + re.escape(indicator) + r'\b', '', clean_query, flags=re.IGNORECASE)
            
            clean_query = clean_query.strip()
            transformed_query = f"{clean_query} doctype:review"
            
            return {
                "original_query": query,
                "intent": "review",
                "intent_confidence": 0.85,
                "transformed_query": transformed_query,
                "explanation": "Added doctype:review to find review papers on this topic."
            }
        
        # Check for highly cited papers intent
        if any(indicator in query_lower for indicator in CITATION_INDICATORS):
            # Remove citation indicators from query
            clean_query = query
            for indicator in CITATION_INDICATORS:
                clean_query = re.sub(r'\b' + re.escape(indicator) + r'\b', '', clean_query, flags=re.IGNORECASE)
            
            clean_query = clean_query.strip()
            transformed_query = f"{clean_query} citation_count:[100 TO *]"
            
            return {
                "original_query": query,
                "intent": "highly_cited",
                "intent_confidence": 0.85,
                "transformed_query": transformed_query,
                "explanation": "Added citation_count filter to find highly cited papers on this topic."
            }
        
        # No clear rule-based intent detected
        return None
    
    def _query_llm(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Query an LLM to interpret and transform a search query.
        
        Args:
            query: Original user query
            
        Returns:
            Optional[Dict[str, Any]]: LLM-based transformation or None if the LLM query failed
        """
        try:
            # Format the system prompt for intent recognition
            current_date = datetime.datetime.now().strftime("%Y-%m-%d")
            system_prompt = f"""You are an expert astronomy query assistant for the NASA/ADS (Astrophysics Data System).
Your task is to analyze astronomy search queries and identify the user's intent.
Based on their intent, transform the original query to make it more effective by adding appropriate ADS search syntax.
Today's date is {current_date}.

Respond ONLY with a JSON object containing:
1. "original_query": The user's original query
2. "intent": The identified intent (e.g., recent, highly_cited, author_search, review, etc.)
3. "intent_confidence": Your confidence in the intent (0.0-1.0)
4. "transformed_query": The query with appropriate ADS search syntax
5. "explanation": A brief explanation of how you transformed the query

Example intents:
- recent: For finding recent papers (add year filter, sort by date)
- highly_cited: For finding influential papers (add citation_count filter)
- author_search: For finding papers by specific authors (format author names properly)
- review: For finding review papers on a topic (add doctype:review)
- definition: For finding definitions or explanations (focus on reviews and catalog papers)

Keep the transformed query focused on the user's original intent while making it more effective with proper ADS syntax."""
            
            # Format the request for the Ollama API
            request_data = {
                "model": self.llm_model,
                "prompt": query,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 1024
                }
            }
            
            # Send the request to the Ollama API
            response = requests.post(
                self.llm_endpoint,
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            response.raise_for_status()
            response_data = response.json()
            
            # Extract the LLM response
            llm_response = response_data.get("response", "")
            
            # Try to extract JSON from the response
            start_idx = llm_response.find("{")
            end_idx = llm_response.rfind("}") + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = llm_response[start_idx:end_idx]
                structured_response = json.loads(json_str)
                
                # Ensure required fields are present
                return {
                    "original_query": structured_response.get("original_query", query),
                    "intent": structured_response.get("intent", "unknown"),
                    "intent_confidence": structured_response.get("intent_confidence", 0.5),
                    "transformed_query": structured_response.get("transformed_query", query),
                    "explanation": structured_response.get("explanation", "No explanation provided.")
                }
            
            # If JSON extraction failed, return None
            logger.warning("Failed to extract structured data from LLM response")
            return None
            
        except Exception as e:
            logger.error(f"Error querying LLM: {str(e)}")
            return None
    
    def analyze_query_complexity(self, query: str) -> Dict[str, Any]:
        """
        Analyze the complexity of a search query.
        
        Args:
            query: Search query to analyze
            
        Returns:
            Dict[str, Any]: Analysis results including complexity metrics
        """
        # Common search operators
        operators = ["AND", "OR", "NOT", "+", "-", "\"\"", ":", "~", "^", "*", "?", "(", ")"]
        
        # Common field specifiers
        fields = ["author:", "title:", "abstract:", "year:", "citation_count:", "bibcode:", 
                  "doi:", "doctype:", "property:", "citations(", "references(", "first_author:", 
                  "full:", "aff:", "orcid:", "bibstem:", "database:"]
        
        # Count the number of search operators
        operator_count = 0
        field_count = 0
        
        for operator in operators:
            if operator in query:
                operator_count += query.count(operator)
        
        # Count the number of field specifications
        for field in fields:
            if field in query:
                field_count += 1
        
        # Check for advanced syntax features
        has_proximity = "~" in query
        has_ranges = "[" in query and "TO" in query and "]" in query
        has_wildcards = "*" in query or "?" in query
        
        # Calculate complexity score (simple metric)
        complexity_score = (operator_count * 0.5) + field_count
        if has_proximity:
            complexity_score += 1
        if has_ranges:
            complexity_score += 1
        if has_wildcards:
            complexity_score += 0.5
        
        # Determine complexity level
        if complexity_score == 0:
            complexity_level = "basic"
        elif complexity_score <= 2:
            complexity_level = "intermediate"
        else:
            complexity_level = "advanced"
        
        return {
            "query": query,
            "complexity_score": complexity_score,
            "complexity_level": complexity_level,
            "operator_count": operator_count,
            "field_count": field_count,
            "has_proximity_search": has_proximity,
            "has_range_search": has_ranges,
            "has_wildcards": has_wildcards
        }
    
    def suggest_improvements(self, query: str) -> List[Dict[str, str]]:
        """
        Suggest improvements for a search query.
        
        Args:
            query: Current search query
            
        Returns:
            List[Dict[str, str]]: List of suggested improvements
        """
        suggestions = []
        query_lower = query.lower()
        
        # Check for missing quotation marks around phrases
        common_phrases = [
            "black hole", "dark matter", "dark energy", "gravitational wave",
            "neutron star", "binary system", "star formation", "active galactic nuclei"
        ]
        
        for phrase in common_phrases:
            if phrase in query_lower and f'"{phrase}"' not in query_lower:
                suggestions.append({
                    "type": "phrase_quotes",
                    "description": f'Consider using quotes around the phrase "{phrase}" for exact matching'
                })
        
        # Suggest field-specific searches for better precision
        if "title:" not in query and "abstract:" not in query:
            suggestions.append({
                "type": "field_specification",
                "description": "Consider using field specifiers like title: or abstract: for more targeted results"
            })
        
        # Suggest adding year constraint if looking for recent papers
        if "recent" in query_lower and "year:" not in query_lower:
            current_year = datetime.datetime.now().year
            suggestions.append({
                "type": "year_constraint",
                "description": f"Add year:{current_year-3}-{current_year} to find recent papers"
            })
        
        # Suggest property:refereed for peer-reviewed content
        if "property:refereed" not in query_lower and "refereed" not in query_lower:
            suggestions.append({
                "type": "refereed_filter",
                "description": "Add property:refereed to limit results to peer-reviewed papers"
            })
        
        return suggestions 