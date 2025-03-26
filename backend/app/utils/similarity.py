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
    
    logger.info(f"Calculating Jaccard similarity between sets of size {len(set1)} and {len(set2)}")
    
    # Normalize string elements for better matching
    norm_set1 = set()
    norm_set2 = set()
    
    for item in set1:
        if isinstance(item, str):
            # If it's a DOI or title identifier, handle that specially
            if item.startswith("doi:") or item.startswith("title:"):
                norm_set1.add(item.lower().strip())
            else:
                norm_set1.add(str(item).lower().strip())
        else:
            norm_set1.add(item)
    
    for item in set2:
        if isinstance(item, str):
            # If it's a DOI or title identifier, handle that specially
            if item.startswith("doi:") or item.startswith("title:"):
                norm_set2.add(item.lower().strip())
            else:
                norm_set2.add(str(item).lower().strip())
        else:
            norm_set2.add(item)
    
    intersection = norm_set1.intersection(norm_set2)
    union = norm_set1.union(norm_set2)
    
    logger.info(f"Found intersection of size {len(intersection)} out of union of size {len(union)}")
    
    if len(intersection) > 0:
        logger.debug(f"Sample of intersection: {list(intersection)[:3]}")
    
    if union == 0:
        return 0.0
    
    jaccard = len(intersection) / len(union)
    logger.info(f"Jaccard similarity: {jaccard}")
    
    return jaccard


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
    
    logger.info(f"Calculating RBO for list1 (len={len(list1)}) and list2 (len={len(list2)})")
    logger.debug(f"List1 samples (first 3): {list1[:3]}")
    logger.debug(f"List2 samples (first 3): {list2[:3]}")
    
    # Create normalized versions of lists where we only keep the identifier part
    # and handle both "doi:" and "title:" prefixes for more flexible matching
    norm_list1 = []
    norm_list2 = []
    
    # Create a mapping of normalized item to original position
    norm_to_pos1 = {}
    norm_to_pos2 = {}
    
    for i, item in enumerate(list1):
        if isinstance(item, str):
            # Strip prefixes and whitespace
            norm_item = item.lower().strip()
            if norm_item.startswith("doi:"):
                norm_item = "doi:" + norm_item[4:].strip()
            elif norm_item.startswith("title:"):
                norm_item = "title:" + norm_item[6:].strip()
            
            norm_list1.append(norm_item)
            norm_to_pos1[norm_item] = i
    
    for i, item in enumerate(list2):
        if isinstance(item, str):
            # Strip prefixes and whitespace
            norm_item = item.lower().strip()
            if norm_item.startswith("doi:"):
                norm_item = "doi:" + norm_item[4:].strip()
            elif norm_item.startswith("title:"):
                norm_item = "title:" + norm_item[6:].strip()
            
            norm_list2.append(norm_item)
            norm_to_pos2[norm_item] = i
    
    # Log matching information
    # Find items that match exactly
    exact_matches = set(norm_list1) & set(norm_list2)
    logger.info(f"Found {len(exact_matches)} exact matches out of {len(norm_list1)} and {len(norm_list2)} items")
    
    # Alternate matching for items that may be identified differently
    # (e.g., doi vs title for the same paper)
    doi_to_title1 = {}
    doi_to_title2 = {}
    
    # Extract DOI and title mappings from list1
    for item in list1:
        if isinstance(item, str):
            if item.startswith("doi:"):
                doi = item[4:].lower().strip()
                for t_item in list1:
                    if t_item.startswith("title:"):
                        title = t_item[6:].lower().strip()
                        doi_to_title1[doi] = title
    
    # Extract DOI and title mappings from list2
    for item in list2:
        if isinstance(item, str):
            if item.startswith("doi:"):
                doi = item[4:].lower().strip()
                for t_item in list2:
                    if t_item.startswith("title:"):
                        title = t_item[6:].lower().strip()
                        doi_to_title2[doi] = title
    
    # Check for DOI-title matches
    add_matches = 0
    for doi1, title1 in doi_to_title1.items():
        if doi1 in doi_to_title2:
            continue  # Already counted in exact matches
        for doi2, title2 in doi_to_title2.items():
            if title1 == title2 and doi1 != doi2:
                add_matches += 1
                break
    
    logger.info(f"Found {add_matches} additional matches by cross-referencing DOIs and titles")
    
    try:
        # Convert lists to dictionaries with item: rank
        # Note: RBO package expects rank to start at 1, not 0
        dict1 = {item: i+1 for i, item in enumerate(norm_list1)}
        dict2 = {item: i+1 for i, item in enumerate(norm_list2)}
        
        # Calculate RBO
        result = rbo.RankingSimilarity(dict1, dict2).rbo(p=p)
        logger.info(f"RBO calculation result: {result}")
        return max(result, 0.0)  # Ensure we don't return negative values
    except Exception as e:
        logger.error(f"Error calculating RBO: {str(e)}")
        
        # Fallback to a simpler measure if RBO fails
        logger.warning("Falling back to Jaccard similarity for rank-based overlap")
        set1 = set(norm_list1)
        set2 = set(norm_list2)
        jaccard = calculate_jaccard_similarity(set1, set2)
        logger.info(f"Fallback Jaccard similarity: {jaccard}")
        return jaccard


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