"""
Configuration settings for LLM-based query interpretation.

This module contains configuration settings for integrating lightweight open-source
LLMs for query transformation in the search-comparisons application.
"""
import os
from enum import Enum
from typing import Dict, Any, Optional

# Default model settings
DEFAULT_MODEL = "qwen2:7b"
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS = 1024

# Available LLM models
class LLMModel(str, Enum):
    """Supported LLM models for query transformation."""
    QWEN2_7B = "qwen2:7b"
    LLAMA2_CHAT = "llama2:7b-chat"
    MISTRAL_7B = "mistral:7b-instruct-v0.2"
    GEMMA_2B = "gemma:2b-it"
    
    @staticmethod
    def get_model_info(model_name: str) -> Dict[str, Any]:
        """
        Get model information and parameters for the specified model.
        
        Args:
            model_name: Name of the model to get information for
            
        Returns:
            Dict[str, Any]: Dictionary of model parameters
        """
        model_info = {
            LLMModel.QWEN2_7B: {
                "display_name": "Qwen2 7B",
                "huggingface_repo": "Qwen/Qwen2-7B",
                "ollama_model": "qwen2:7b",
                "context_window": 32768,
                "description": "Efficient model with strong reasoning capabilities"
            },
            LLMModel.LLAMA2_CHAT: {
                "display_name": "Llama 2 Chat (7B)",
                "huggingface_repo": "meta-llama/Llama-2-7b-chat-hf",
                "ollama_model": "llama2:7b-chat",
                "context_window": 4096,
                "description": "Optimized for dialogue and instruction following"
            },
            LLMModel.MISTRAL_7B: {
                "display_name": "Mistral 7B Instruct",
                "huggingface_repo": "mistralai/Mistral-7B-Instruct-v0.2",
                "ollama_model": "mistral:7b-instruct-v0.2",
                "context_window": 8192,
                "description": "Efficient model with good reasoning capabilities"
            },
            LLMModel.GEMMA_2B: {
                "display_name": "Gemma 2B Instruct",
                "huggingface_repo": "google/gemma-2b-it",
                "ollama_model": "gemma:2b-it",
                "context_window": 8192,
                "description": "Lightweight model with good performance"
            }
        }
        return model_info.get(model_name, {})


# LLM configuration
LLM_CONFIG = {
    "model": "qwen2:7b",
    "temperature": DEFAULT_TEMPERATURE,
    "max_tokens": DEFAULT_MAX_TOKENS,
    "provider": "ollama",
    "api_endpoint": "http://localhost:11434/api/generate",
    "prompt_template": None,  # Use default template if None
    "models": {
        "qwen2:7b": {
            "display_name": "Qwen2 7B",
            "huggingface_repo": "Qwen/Qwen2-7B",
            "ollama_model": "qwen2:7b",
            "context_window": 32768,
            "description": "Efficient model with strong reasoning capabilities",
            "default_prompt_template": """You are an expert query understanding assistant for the NASA/ADS (Astrophysics Data System).
Your task is to analyze astronomy search queries and identify the user's intent.
Based on their intent, transform the original query to make it more effective by adding appropriate ADS search syntax.

Respond ONLY with a JSON object containing:
1. "original_query": The user's original query
2. "intent": The identified intent (e.g., recent, highly_cited, author_search, review, etc.)
3. "intent_confidence": Your confidence in the intent (0.0-1.0)
4. "transformed_query": The query with appropriate ADS search syntax
5. "explanation": A brief explanation of how you transformed the query

Available ADS Search Fields and Operators:
- abs:"phrase" - Search across title, abstract, and keywords (preferred over individual fields)
- author:"LastName, FirstName" - Search by author name (use proper format)
- year:YYYY or year:YYYY-YYYY - Filter by publication year
- citation_count:N or citation_count:[N TO M] - Filter by citation count
- property:PROPERTY - Filter by document properties (refereed, openaccess, etc.)
- bibstem:ABBREV - Filter by journal abbreviation (e.g., ApJ, MNRAS)
- aff:"institution" - Search by author affiliation
- orcid:ID - Search by ORCID identifier
- doctype:TYPE - Filter by document type (article, eprint, inproceedings, etc.)

Second-Order Operators:
- reviews(query) - Find papers that cite the most relevant papers on a topic
- trending(query) - Find papers currently being read by users interested in a topic
- useful(query) - Find papers frequently cited by relevant papers on a topic
- similar(query) - Find papers textually similar to the query results
- topn(N, query, sort) - Get top N results sorted by specified criteria

Boolean Operators:
- AND - Requires both terms (default)
- OR - Requires one of the terms
- NOT or - - Excludes documents
- "exact phrase" - Exact phrase matching
- (term1 OR term2) AND term3 - Grouping terms
- "term1 term2"~N - Proximity search
- term^N - Boost term importance
- term* - Wildcard search
- term? - Single character wildcard

Example intents and transformations:
- recent: Use trending() or year filter (e.g., year:2024-2025 or trending(abs:topic))
- highly_cited: Use citation_count filter and sort (e.g., citation_count:[100 TO *] sort:citation_count desc)
- author_search: Format author names properly (e.g., author:"Kurtz, M")
- review: Use reviews() operator (e.g., reviews(abs:topic))
- comparison: Use useful() operator (e.g., useful(abs:topic1 AND topic2))
- definition: Use reviews() with doctype filter (e.g., reviews(abs:term) doctype:(article OR review))

Special Considerations:
1. For topical searches, prefer abs: over individual fields (title:, abstract:, etc.)
2. For recent content, consider using trending() instead of year filters
3. For finding review papers, use reviews() operator instead of doctype:review
4. For finding influential papers, use useful() operator
5. For finding similar papers, use similar() operator
6. For author searches, always use proper format: "LastName, FirstName"
7. For ORCID searches, use full ORCID ID
8. For affiliation searches, use canonical institution names

Keep the transformed query focused on the user's original intent while making it more effective with proper ADS syntax."""
        }
    }
}

# ADS Search Field mappings for query enhancement
ADS_SEARCH_FIELDS = {
    "author": {
        "description": "Author name(s)",
        "syntax": 'author:"LastName, FirstName"',
        "example": 'author:"Kurtz, M"'
    },
    "title": {
        "description": "Words in the title of the paper",
        "syntax": "title:Term",
        "example": "title:gravitational waves"
    },
    "abstract": {
        "description": "Words in the abstract of the paper",
        "syntax": "abstract:Term",
        "example": "abstract:dark matter"
    },
    "year": {
        "description": "Year of publication",
        "syntax": "year:YYYY or year:YYYY-YYYY",
        "example": "year:2020 or year:2018-2022"
    },
    "citation_count": {
        "description": "Number of citations",
        "syntax": "citation_count:N or citation_count:[N TO M]",
        "example": "citation_count:100 or citation_count:[50 TO 100]"
    },
    "bibcode": {
        "description": "ADS Bibliographic Code",
        "syntax": "bibcode:YYYYJJJJJVVVVMPPPPA",
        "example": "bibcode:2019ApJ...886...57K"
    },
    "doi": {
        "description": "Digital Object Identifier",
        "syntax": "doi:DOI",
        "example": "doi:10.3847/1538-4357/ab4a0c"
    },
    "doctype": {
        "description": "Document type",
        "syntax": "doctype:TYPE",
        "example": "doctype:article or doctype:review"
    },
    "property": {
        "description": "Document property",
        "syntax": "property:PROPERTY",
        "example": "property:refereed or property:openaccess"
    },
    "citations": {
        "description": "Citations to a paper",
        "syntax": "citations(PAPER)",
        "example": 'citations(bibcode:2019ApJ...886...57K)'
    },
    "references": {
        "description": "References from a paper",
        "syntax": "references(PAPER)",
        "example": 'references(bibcode:2019ApJ...886...57K)'
    },
    "first_author": {
        "description": "First author of the paper",
        "syntax": 'first_author:"LastName, FirstName"',
        "example": 'first_author:"Kurtz, M"'
    },
    "full": {
        "description": "Full text search",
        "syntax": "full:Term",
        "example": "full:gravitational waves"
    },
    "aff": {
        "description": "Author affiliation",
        "syntax": "aff:Term",
        "example": 'aff:"Harvard"'
    },
    "orcid": {
        "description": "ORCID identifier",
        "syntax": "orcid:ORCID",
        "example": "orcid:0000-0002-4110-3511"
    },
    "bibstem": {
        "description": "Journal abbreviation",
        "syntax": "bibstem:ABBREVIATION",
        "example": "bibstem:ApJ or bibstem:MNRAS"
    },
    "database": {
        "description": "Database",
        "syntax": "database:DATABASE",
        "example": "database:astronomy"
    },
}

# ADS Search Operators
ADS_SEARCH_OPERATORS = {
    "AND": {
        "description": "Requires both terms to be present",
        "syntax": "term1 AND term2",
        "example": "exoplanets AND \"habitable zone\""
    },
    "OR": {
        "description": "Requires one of the terms to be present",
        "syntax": "term1 OR term2",
        "example": "Mars OR Venus"
    },
    "NOT": {
        "description": "Excludes documents containing the term",
        "syntax": "term1 NOT term2",
        "example": "galaxies NOT dwarf"
    },
    "+": {
        "description": "Requires term to be present",
        "syntax": "+term",
        "example": "+gravitational +waves"
    },
    "-": {
        "description": "Excludes documents containing the term",
        "syntax": "-term",
        "example": "black holes -hawking"
    },
    "\"\"": {
        "description": "Exact phrase search",
        "syntax": "\"exact phrase\"",
        "example": "\"dark energy\""
    },
    "( )": {
        "description": "Grouping terms together",
        "syntax": "(term1 OR term2) AND term3",
        "example": "(Mars OR Venus) AND atmosphere"
    },
    "~": {
        "description": "Proximity search",
        "syntax": "\"term1 term2\"~N",
        "example": "\"star planet\"~5"
    },
    "^": {
        "description": "Boosting term importance",
        "syntax": "term^N",
        "example": "title:star^2 abstract:star"
    },
    "*": {
        "description": "Wildcard search",
        "syntax": "term*",
        "example": "galax*"
    },
    "?": {
        "description": "Single character wildcard",
        "syntax": "term?",
        "example": "m?on"
    },
}

# Common astronomical/scientific terms and their variations
# Used to help the LLM recognize domain-specific terminology
ASTRONOMY_TERMS = {
    "galaxy": ["galaxies", "galactic", "intergalactic"],
    "star": ["stars", "stellar", "interstellar"],
    "planet": ["planets", "planetary", "exoplanet", "exoplanets"],
    "black hole": ["black holes", "supermassive black hole"],
    "nebula": ["nebulae", "nebular"],
    "supernova": ["supernovae", "supernova remnant"],
    "quasar": ["quasars", "quasi-stellar object"],
    "pulsar": ["pulsars", "pulsar timing"],
    "asteroid": ["asteroids", "near-earth object", "NEO"],
    "comet": ["comets", "Kuiper belt object"],
    "dwarf planet": ["dwarf planets", "Pluto", "Eris"],
    "moon": ["moons", "lunar", "satellite"],
    "meteorite": ["meteorites", "meteor", "meteors", "meteoroid"],
    "cosmology": ["cosmological", "early universe"],
    "dark matter": ["dark energy", "dark sector"],
    "gravitational wave": ["gravitational waves", "LIGO"],
    "redshift": ["redshifts", "blueshift", "Doppler shift"],
    "spectroscopy": ["spectroscopic", "spectrum", "spectra"],
    "photometry": ["photometric", "lightcurve", "lightcurves"],
    "interferometry": ["interferometric", "VLBI"],
}

# Query intent mappings
QUERY_INTENTS = {
    "recent": {
        "description": "Finding recent papers on a topic",
        "indicators": ["recent", "latest", "new", "current", "last year", "2023", "2022", "2021"],
        "transformations": [
            {"type": "add_field", "field": "year", "value": "{current_year-1}-{current_year}"},
            {"type": "add_operator", "operator": "sort", "value": "date desc"}
        ]
    },
    "highly_cited": {
        "description": "Finding influential/highly cited papers",
        "indicators": ["influential", "important", "significant", "highly cited", "most cited", "high impact"],
        "transformations": [
            {"type": "add_field", "field": "citation_count", "value": "[100 TO *]"},
            {"type": "add_operator", "operator": "sort", "value": "citation_count desc"}
        ]
    },
    "author_search": {
        "description": "Finding papers by specific authors",
        "indicators": ["authored by", "written by", "papers by", "works by", "articles by", "publications by"],
        "transformations": [
            {"type": "convert_to_author_search", "format": 'author:"{lastname}, {firstname}"'}
        ]
    },
    "review": {
        "description": "Finding review papers on a topic",
        "indicators": ["review", "overview", "survey", "summary", "state of the art", "state-of-the-art"],
        "transformations": [
            {"type": "add_field", "field": "doctype", "value": "review"}
        ]
    },
    "comparison": {
        "description": "Finding papers comparing topics",
        "indicators": ["comparing", "comparison", "versus", "vs", "difference between", "contrast"],
        "transformations": [
            {"type": "add_field", "field": "property", "value": "refereed"},
            {"type": "add_field", "field": "references", "value": "100"}
        ]
    },
    "definition": {
        "description": "Finding definitions or explanations",
        "indicators": ["what is", "what are", "definition of", "meaning of", "explain", "definition"],
        "transformations": [
            {"type": "add_field", "field": "doctype", "value": "(review OR catalog)"},
            {"type": "add_operator", "operator": "sort", "value": "citation_count desc"}
        ]
    }
} 