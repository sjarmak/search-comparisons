"""Service module for query transformation with field boosts."""
from typing import Dict, List
from itertools import combinations


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