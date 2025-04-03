"""
Configuration settings for LLM-based query interpretation.

This module contains configuration settings for integrating lightweight open-source
LLMs for query transformation in the search-comparisons application.
"""
import os
from enum import Enum
from typing import Dict, Any, Optional

# Default model settings
DEFAULT_MODEL = "llama2-chat"
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS = 1024

# Available LLM models
class LLMModel(str, Enum):
    """Supported LLM models for query transformation."""
    LLAMA2_CHAT = "llama2-chat"
    MISTRAL_7B = "mistral-7b-instruct-v0.2"
    GEMMA_2B = "gemma-2b-it"
    
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
                "ollama_model": "gemma:2b-instruct",
                "context_window": 8192,
                "description": "Lightweight model with decent performance"
            }
        }
        
        return model_info.get(model_name, model_info[DEFAULT_MODEL])


# LLM service configuration
LLM_CONFIG = {
    "model": os.getenv("LLM_MODEL", DEFAULT_MODEL),
    "temperature": float(os.getenv("LLM_TEMPERATURE", DEFAULT_TEMPERATURE)),
    "max_tokens": int(os.getenv("LLM_MAX_TOKENS", DEFAULT_MAX_TOKENS)),
    "provider": os.getenv("LLM_PROVIDER", "ollama"),  # ollama, hf, openai, etc.
    "api_endpoint": os.getenv("LLM_API_ENDPOINT", "http://localhost:11434/api/generate"),
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