"""Test query transformation with field boosts.

This module contains tests for transforming queries with field boosts,
handling both single terms and phrases.
"""
from typing import Dict, List, Set, Tuple
from itertools import combinations

import pytest


def transform_query_with_boosts(query: str, field_boosts: Dict[str, float]) -> str:
    """Transform a query by applying field boosts and generating combinations.

    Args:
        query: The input query string to transform
        field_boosts: Dictionary mapping field names to their boost values

    Returns:
        str: The transformed query with field boosts applied
    """
    if not query or not field_boosts:
        return query

    # Split query into terms and phrases
    terms: List[str] = []
    phrases: List[str] = []
    current_term = []
    current_phrase = []
    in_quotes = False

    for char in query:
        if char == '"':
            in_quotes = not in_quotes
            if not in_quotes and current_phrase:
                phrases.append(''.join(current_phrase).strip())
                current_phrase = []
        elif in_quotes:
            current_phrase.append(char)
        elif char == ' ':
            if current_term:
                terms.append(''.join(current_term))
                current_term = []
        else:
            current_term.append(char)

    # Handle any remaining terms or phrases
    if current_term:
        terms.append(''.join(current_term))
    if current_phrase:
        phrases.append(''.join(current_phrase).strip())

    # Sort fields by boost value in descending order
    sorted_fields = sorted(field_boosts.items(), key=lambda x: (-x[1], x[0]))
    
    parts = []
    
    # Process each field in order of boost value
    for field, boost in sorted_fields:
        # First add single terms
        for term in terms:
            parts.append(f'{field}:{term}^{boost}')
            
        # Then add combinations of non-phrase terms
        if len(terms) >= 2:
            # Generate all possible combinations of terms (2 or more terms)
            for r in range(2, len(terms) + 1):
                for combo in combinations(terms, r):
                    parts.append(f'{field}:"{" ".join(combo)}"^{boost}')
                    
        # Then add explicit phrases
        for phrase in phrases:
            parts.append(f'{field}:"{phrase}"^{boost}')
            
        # Finally add combinations of terms with phrases
        for term in terms:
            for phrase in phrases:
                parts.append(f'{field}:"{term} {phrase}"^{boost}')

    return ' OR '.join(parts)


@pytest.mark.parametrize(
    "query,field_boosts,expected",
    [
        # Single term queries
        ("test", {"title": 2.0}, "title:test^2.0"),
        ("test", {"title": 2.0, "abstract": 1.5}, "title:test^2.0 OR abstract:test^1.5"),
        
        # Two term queries
        ("katabatic wind", {"title": 2.0}, 
         'title:katabatic^2.0 OR title:wind^2.0 OR title:"katabatic wind"^2.0'),
        ("katabatic wind", {"title": 2.0, "abstract": 1.5}, 
         'title:katabatic^2.0 OR title:wind^2.0 OR title:"katabatic wind"^2.0 OR '
         'abstract:katabatic^1.5 OR abstract:wind^1.5 OR abstract:"katabatic wind"^1.5'),
        
        # Three term queries
        ("katabatic wind flow", {"title": 2.0},
         'title:katabatic^2.0 OR title:wind^2.0 OR title:flow^2.0 OR '
         'title:"katabatic wind"^2.0 OR title:"katabatic flow"^2.0 OR title:"wind flow"^2.0 OR '
         'title:"katabatic wind flow"^2.0'),
        
        # Quoted phrases (should be treated as single terms)
        ('"katabatic wind"', {"title": 2.0}, 'title:"katabatic wind"^2.0'),
        ('"katabatic wind"', {"title": 2.0, "abstract": 1.5}, 
         'title:"katabatic wind"^2.0 OR abstract:"katabatic wind"^1.5'),
        
        # Mixed terms and phrases
        ('katabatic "wind flow"', {"title": 2.0}, 
         'title:katabatic^2.0 OR title:"wind flow"^2.0 OR title:"katabatic wind flow"^2.0'),
        
        # Empty query
        ("", {"title": 2.0}, ""),
        
        # No field boosts
        ("test query", {}, "test query"),
        
        # Multiple fields with different boosts
        ("climate data", {
            "title": 3.0,
            "abstract": 2.0,
            "keywords": 2.5,
            "author": 1.5,
            "year": 1.0
        }, 'title:climate^3.0 OR title:data^3.0 OR title:"climate data"^3.0 OR '
           'keywords:climate^2.5 OR keywords:data^2.5 OR keywords:"climate data"^2.5 OR '
           'abstract:climate^2.0 OR abstract:data^2.0 OR abstract:"climate data"^2.0 OR '
           'author:climate^1.5 OR author:data^1.5 OR author:"climate data"^1.5 OR '
           'year:climate^1.0 OR year:data^1.0 OR year:"climate data"^1.0'),
    ]
)
def test_query_transformation(query: str, field_boosts: Dict[str, float], expected: str) -> None:
    """Test query transformation with various inputs.
    
    Args:
        query: The input query to transform
        field_boosts: Dictionary of field boosts to apply
        expected: The expected transformed query
    """
    result = transform_query_with_boosts(query, field_boosts)
    assert result == expected


def test_query_transformation_edge_cases() -> None:
    """Test edge cases for query transformation."""
    # Test with unclosed quotes
    result = transform_query_with_boosts('"test', {"title": 2.0})
    assert result == 'title:"test"^2.0'

    # Test with multiple unclosed quotes
    result = transform_query_with_boosts('"test "phrase', {"title": 2.0})
    assert result == 'title:phrase^2.0 OR title:"test"^2.0 OR title:"phrase test"^2.0'

    # Test with empty phrases
    result = transform_query_with_boosts('""', {"title": 2.0})
    assert result == ''

    # Test with only spaces
    result = transform_query_with_boosts('   ', {"title": 2.0})
    assert result == '' 