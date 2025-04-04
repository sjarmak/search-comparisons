"""
Query transformation agent for astronomy search.

This module implements an agent that orchestrates the process of transforming
user queries into more effective astronomy search queries using LLM-based intent recognition.
"""
import logging
import datetime
import re
from typing import Dict, Any, List, Optional, Tuple

from .llm_service import LLMService
from .config import ADS_SEARCH_FIELDS, ADS_SEARCH_OPERATORS, ASTRONOMY_TERMS, QUERY_INTENTS

# Configure logger for this module
logger = logging.getLogger(__name__)


class QueryAgent:
    """
    Agent for transforming user queries based on inferred intent.
    
    This agent coordinates the process of:
    1. Analyzing the user's original query
    2. Detecting search intent using an LLM
    3. Transforming the query with appropriate field operators
    4. Explaining the transformation process
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None) -> None:
        """
        Initialize the query agent with an LLM service.
        
        Args:
            llm_service: LLM service for query interpretation
        """
        self.llm_service = llm_service or LLMService.from_config()
        logger.info("Initialized query transformation agent")
    
    def transform_query(self, original_query: str) -> Dict[str, Any]:
        """
        Transform a user query based on the detected intent.
        
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
        if rule_based_result and rule_based_result.get("intent_confidence", 0) > 0.8:
            logger.info(f"Rule-based transformation applied with intent: {rule_based_result['intent']}")
            return rule_based_result
        
        # Otherwise, use LLM for intent detection and transformation
        llm_result = self.llm_service.interpret_query(original_query)
        
        # Enhance the LLM result with any additional information
        enhanced_result = self._enhance_llm_result(llm_result)
        
        # Record and return the final transformation
        logger.info(f"Query transformed: '{original_query}' -> '{enhanced_result['transformed_query']}'")
        return enhanced_result
    
    def _apply_rule_based_transformation(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Apply rule-based transformations without using the LLM.
        
        Args:
            query: Original user query
            
        Returns:
            Optional[Dict[str, Any]]: Transformation result or None if no clear rule applies
        """
        query_lower = query.lower()
        
        # Check for recent papers intent
        if any(indicator in query_lower for indicator in QUERY_INTENTS["recent"]["indicators"]):
            current_year = datetime.datetime.now().year
            year_range = f"{current_year-1}-{current_year}"
            
            # Remove time indicators from query
            clean_query = query
            for indicator in QUERY_INTENTS["recent"]["indicators"]:
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
        author_indicators = QUERY_INTENTS["author_search"]["indicators"]
        if any(indicator in query_lower for indicator in author_indicators):
            for indicator in author_indicators:
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
        
        # No clear rule-based intent detected
        return None
    
    def _enhance_llm_result(self, llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance the LLM transformation result with additional processing.
        
        Args:
            llm_result: Result from LLM interpretation
            
        Returns:
            Dict[str, Any]: Enhanced transformation result
        """
        # Get the identified intent and the transformed query
        intent = llm_result.get("intent", "unknown")
        transformed_query = llm_result.get("transformed_query", "")
        
        # Apply additional enhancements based on intent
        if intent == "recent" and "year:" not in transformed_query:
            # Ensure year constraint is included for recent intent
            current_year = datetime.datetime.now().year
            transformed_query += f" year:{current_year-1}-{current_year}"
            llm_result["explanation"] += f" Added year filter for recent papers."
        
        elif intent == "highly_cited" and "citation_count:" not in transformed_query:
            # Ensure citation count for highly cited papers
            transformed_query += " citation_count:[100 TO *]"
            llm_result["explanation"] += f" Added citation count filter for influential papers."
        
        # Update the transformed query in the result
        llm_result["transformed_query"] = transformed_query.strip()
        
        return llm_result
    
    def analyze_query_complexity(self, query: str) -> Dict[str, Any]:
        """
        Analyze the complexity of a search query.
        
        Args:
            query: Search query to analyze
            
        Returns:
            Dict[str, Any]: Analysis results including complexity metrics
        """
        # Count the number of search operators
        operator_count = 0
        field_count = 0
        
        for operator in ADS_SEARCH_OPERATORS:
            if operator in query:
                operator_count += query.count(operator)
        
        # Count the number of field specifications
        for field in ADS_SEARCH_FIELDS:
            if f"{field}:" in query:
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