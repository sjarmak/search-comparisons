"""
Similarity calculation utilities for the search-comparisons application.

This module provides functions for calculating similarity between texts
and result sets, including Jaccard similarity, rank-based overlap (RBO),
and cosine similarity.
"""
import math
import logging
import rbo
from typing import Dict, List, Set, Tuple, Any, Union, Optional

# Setup logging
logger = logging.getLogger(__name__)


def calculate_jaccard_similarity(set1: Set[Any], set2: Set[Any]) -> float:
    """
    Calculate Jaccard similarity between two sets.
    
    The Jaccard similarity is the size of the intersection divided by the size
    of the union of the two sets. It ranges from 0 (no overlap) to 1 (identical sets).
    
    Args:
        set1: First set
        set2: Second set
    
    Returns:
        float: Jaccard similarity coefficient in the range [0, 1]
    """
    if not set1 and not set2:
        return 1.0  # Both sets empty => identical
    
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    if union == 0:
        return 0.0
    
    return intersection / union


def calculate_rank_based_overlap(
    list1: List[Any], 
    list2: List[Any], 
    p: float = 0.98
) -> float:
    """
    Calculate Rank-Based Overlap (RBO) between two ranked lists.
    
    RBO is designed for comparing ranked lists when:
    - Not all items may be present in both lists
    - The order of items matters, with higher ranks more important
    - The lists may be of different lengths
    
    Args:
        list1: First ranked list
        list2: Second ranked list
        p: Persistence parameter (default: 0.98) - higher values give
           more weight to agreement at higher ranks
    
    Returns:
        float: RBO similarity in the range [0, 1]
    """
    if not list1 or not list2:
        if not list1 and not list2:
            return 1.0  # Both lists empty => identical
        return 0.0  # One list empty, other not => no overlap
    
    try:
        # Convert lists to dictionaries with item: rank
        # Note: RBO package expects rank to start at 1, not 0
        dict1 = {item: i+1 for i, item in enumerate(list1)}
        dict2 = {item: i+1 for i, item in enumerate(list2)}
        
        # Calculate RBO
        result = rbo.RankingSimilarity(dict1, dict2).rbo(p=p)
        return result
    except Exception as e:
        logger.error(f"Error calculating RBO: {str(e)}")
        
        # Fallback to a simpler measure if RBO fails
        # Calculate proportion of shared elements
        set1 = set(list1)
        set2 = set(list2)
        return calculate_jaccard_similarity(set1, set2)


def calculate_cosine_similarity(
    vec1: Dict[str, int], 
    vec2: Dict[str, int]
) -> float:
    """
    Calculate cosine similarity between two term frequency dictionaries.
    
    Cosine similarity measures the cosine of the angle between two vectors,
    which in this case are term frequency dictionaries. It ranges from 0 (completely
    dissimilar) to 1 (identical).
    
    Args:
        vec1: First term frequency dictionary (term -> count)
        vec2: Second term frequency dictionary (term -> count)
    
    Returns:
        float: Cosine similarity in the range [0, 1]
    """
    if not vec1 or not vec2:
        if not vec1 and not vec2:
            return 1.0  # Both vectors empty => identical
        return 0.0  # One vector empty, other not => no similarity
    
    # Get common terms
    common_terms = set(vec1.keys()) & set(vec2.keys())
    
    # Calculate dot product
    dot_product = sum(vec1[term] * vec2[term] for term in common_terms)
    
    # Calculate magnitudes
    magnitude1 = math.sqrt(sum(vec1[term] ** 2 for term in vec1))
    magnitude2 = math.sqrt(sum(vec2[term] ** 2 for term in vec2))
    
    # Check for zero magnitudes to avoid division by zero
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    # Calculate cosine similarity
    similarity = dot_product / (magnitude1 * magnitude2)
    
    return similarity 