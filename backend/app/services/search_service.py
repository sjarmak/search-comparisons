"""
Search service module for the search-comparisons application.

This module coordinates search operations across different search engines,
handles fallbacks, and computes similarity metrics between results.
"""
import os
import logging
import asyncio
from typing import Dict, List, Any, Set, Tuple, Optional

from ..api.models import SearchResult
from ..utils.cache import get_cache_key, save_to_cache, load_from_cache
from ..utils.text_processing import preprocess_text
from ..utils.similarity import calculate_jaccard_similarity, calculate_rank_based_overlap, calculate_cosine_similarity

# Import specific search services
from .ads_service import get_ads_results
from .scholar_service import get_scholar_results, get_scholar_results_fallback
from .semantic_scholar_service import get_semantic_scholar_results
from .web_of_science_service import get_web_of_science_results

# Setup logging
logger = logging.getLogger(__name__)


class SearchService:
    """
    Service class for handling search operations across different search engines.
    
    This class provides methods for performing searches, handling fallbacks,
    and computing similarity metrics between results from different sources.
    """
    
    def __init__(self):
        """Initialize the search service with default configuration."""
        self.service_config = SERVICE_CONFIG
        self.default_num_results = DEFAULT_NUM_RESULTS
    
    async def search(
        self,
        query: str,
        sources: List[str],
        fields: List[str],
        max_results: Optional[int] = None,
        attempts: int = 2
    ) -> Dict[str, List[SearchResult]]:
        """
        Perform a search across multiple sources with fallback mechanisms.
        
        Args:
            query: Search query string
            sources: List of search engine sources to query
            fields: List of fields to retrieve
            max_results: Maximum number of results to return per source
            attempts: Maximum number of retry attempts per source
        
        Returns:
            Dict[str, List[SearchResult]]: Dictionary mapping source names to result lists
        """
        return await get_results_with_fallback(
            query=query,
            sources=sources,
            fields=fields,
            max_results=max_results,
            attempts=attempts
        )
    
    def compare(
        self,
        sources_results: Dict[str, List[SearchResult]],
        metrics: List[str],
        fields: List[str]
    ) -> Dict[str, Any]:
        """
        Compare search results from different sources using specified metrics.
        
        Args:
            sources_results: Dictionary mapping source names to result lists
            metrics: List of similarity metrics to compute
            fields: List of fields to use for comparisons
        
        Returns:
            Dict[str, Any]: Dictionary with comparison results
        """
        return compare_results(
            sources_results=sources_results,
            metrics=metrics,
            fields=fields
        )
    
    async def get_paper_details(
        self,
        doi: str,
        sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get detailed information about a paper from multiple sources.
        
        Args:
            doi: Digital Object Identifier of the paper
            sources: Optional list of sources to query
        
        Returns:
            Dict[str, Any]: Dictionary containing paper details from each source
        """
        return await get_paper_details(doi=doi, sources=sources)


# Service configuration with fallback settings
SERVICE_CONFIG = {
    "ads": {
        "enabled": True,
        "priority": 1,  # Lower number = higher priority
        "timeout": 15,  # seconds
        "min_results": 5,  # Minimum acceptable results
    },
    "scholar": {
        "enabled": True,
        "priority": 2,
        "timeout": 20,
        "min_results": 3,
    },
    "semanticScholar": {
        "enabled": True,
        "priority": 3,
        "timeout": 15,
        "min_results": 5,
    },
    "webOfScience": {
        "enabled": True,
        "priority": 4,
        "timeout": 20,
        "min_results": 3,
    }
}

# Default number of results if not specified
DEFAULT_NUM_RESULTS = 20


async def get_results_with_fallback(
    query: str, 
    sources: List[str], 
    fields: List[str], 
    max_results: Optional[int] = None,
    attempts: int = 2,
    use_transformed_query: bool = False,
    original_query: Optional[str] = None,
    qf: Optional[str] = None,  # Query field weights for qf parameter
    field_boosts: Optional[Dict[str, float]] = None  # Field boosts for query transformation
) -> Dict[str, List[SearchResult]]:
    """
    Get search results from multiple sources with fallback mechanisms.
    
    Args:
        query: Search query string
        sources: List of search engine sources to query
        fields: List of fields to retrieve
        max_results: Maximum number of results to return per source
        attempts: Maximum number of retry attempts per source
        use_transformed_query: Whether to use the transformed query
        original_query: The original query before transformation
        qf: Query field weights (e.g., "title^50 author^30")
        field_boosts: Dictionary mapping field names to boost values for query transformation
    
    Returns:
        Dict[str, List[SearchResult]]: Dictionary mapping source names to result lists
    """
    results: Dict[str, List[SearchResult]] = {}
    
    # Convert query to string if it's a list
    if isinstance(query, list):
        query = " ".join(str(item) for item in query)
        logger.warning(f"Query was a list, converted to string: {query}")
    
    # Set number of results
    num_results = max_results or DEFAULT_NUM_RESULTS
    
    # Process each source
    for source in sources:
        if source not in SERVICE_CONFIG or not SERVICE_CONFIG[source]["enabled"]:
            logger.warning(f"Source {source} is not enabled or not configured")
            continue
        
        success = False
        attempt_count = 0
        
        while attempt_count < attempts and not success:
            attempt_count += 1
            logger.info(f"Attempt {attempt_count} for {source}")
            
            try:
                # Determine which query to use based on source and transformation settings
                effective_query = query
                if use_transformed_query:
                    if source == "ads":
                        # For ADS, use the transformed query directly
                        effective_query = query
                        logger.info(f"Using transformed query for ADS: {effective_query}")
                    else:
                        # For other sources, use the original query
                        effective_query = original_query or query
                        logger.info(f"Using original query for {source}: {effective_query}")
                
                # Set timeout based on service config
                timeout = SERVICE_CONFIG[source]["timeout"] if source in SERVICE_CONFIG else 15
                
                # Create a task for the source query with timeout
                async def query_source():
                    if source == "ads":
                        return await get_ads_results(
                            effective_query, 
                            fields, 
                            num_results, 
                            qf=qf,  # Pass qf parameter
                            field_boosts=field_boosts  # Pass field boosts
                        )
                    elif source == "scholar":
                        if attempt_count == 1:
                            return await get_scholar_results(effective_query, fields, num_results)
                        else:
                            return await get_scholar_results_fallback(effective_query, num_results)
                    elif source == "semanticScholar":
                        return await get_semantic_scholar_results(effective_query, fields, num_results)
                    elif source == "webOfScience":
                        return await get_web_of_science_results(effective_query, fields, num_results)
                    else:
                        logger.error(f"Unknown source: {source}")
                        return []
                
                # Execute query with timeout
                try:
                    source_results = await asyncio.wait_for(query_source(), timeout=timeout)
                except asyncio.TimeoutError:
                    logger.error(f"Timeout after {timeout} seconds for {source}")
                    continue
                
                # Check if we got enough results
                min_results = SERVICE_CONFIG[source]["min_results"] if source in SERVICE_CONFIG else 1
                if len(source_results) >= min_results:
                    success = True
                    logger.info(f"Successfully retrieved {len(source_results)} results from {source}")
                else:
                    logger.warning(f"Insufficient results from {source}: {len(source_results)} < {min_results}")
            
            except Exception as e:
                logger.error(f"Error fetching results from {source}: {str(e)}")
                if attempt_count == attempts:
                    logger.error(f"All attempts failed for {source}")
        
        # Save results to cache if successful
        if success and source_results:
            # Generate cache key with all parameters
            cache_key = get_cache_key(
                source=source,
                query=effective_query,  # Use the effective query that was actually used
                fields=fields,
                num_results=num_results,
                qf=qf,
                field_boosts=field_boosts
            )
            save_to_cache(cache_key, source_results)
            results[source] = source_results
    
    return results


def compare_results(
    sources_results: Dict[str, List[SearchResult]], 
    metrics: List[str], 
    fields: List[str]
) -> Dict[str, Any]:
    """
    Compare search results from different sources using specified metrics.
    
    Computes similarity scores between results from different sources based
    on various similarity metrics and fields.
    
    Args:
        sources_results: Dictionary mapping source names to result lists
        metrics: List of similarity metrics to compute
        fields: List of fields to use for comparisons
    
    Returns:
        Dict[str, Any]: Dictionary with comparison results
    """
    comparison_results: Dict[str, Any] = {
        "overlap": {},
        "similarity": {},
        "sources": {}
    }
    
    # Process source data
    for source, results in sources_results.items():
        comparison_results["sources"][source] = {
            "count": len(results),
            "results": results
        }
    
    # If we have fewer than 2 sources with results, we can't compare
    active_sources = [s for s, r in sources_results.items() if r]
    if len(active_sources) < 2:
        logger.warning("Not enough sources with results to compare")
        return comparison_results
    
    # Calculate overlap and similarity for each pair of sources
    for i, source1 in enumerate(active_sources):
        for j, source2 in enumerate(active_sources):
            if i >= j:  # Skip self-comparisons and redundant pairs
                continue
            
            # Get results for both sources
            results1 = sources_results[source1]
            results2 = sources_results[source2]
            
            # Skip if either source has no results
            if not results1 or not results2:
                continue
            
            # Create pair key
            pair_key = f"{source1}_vs_{source2}"
            
            # Calculate overlap
            # Get sets of DOIs or titles for unique identification
            identifiers1: Set[str] = set()
            identifiers2: Set[str] = set()
            
            # Track which results have DOIs
            results1_with_doi = {}
            results2_with_doi = {}
            results1_no_doi = {}
            results2_no_doi = {}
            
            # Categorize results by whether they have DOIs
            for idx, result in enumerate(results1):
                # Handle both SearchResult objects and dictionaries
                if isinstance(result, dict):
                    doi = result.get('doi')
                    title = result.get('title', '')
                else:
                    doi = getattr(result, 'doi', None)
                    title = getattr(result, 'title', '')
                
                # Ensure doi and title are strings
                if isinstance(doi, list):
                    doi = doi[0] if doi else None
                if isinstance(title, list):
                    title = title[0] if title else ''
                
                if doi:
                    identifiers1.add(str(doi).lower())
                    results1_with_doi[str(doi).lower()] = idx
                else:
                    identifiers1.add(f"title:{str(title).lower()}")
                    results1_no_doi[str(title).lower()] = idx
                
                # Always track title for potential title matching
                if title:
                    # Store title with index regardless of DOI status
                    if "titles" not in results1_with_doi:
                        results1_with_doi["titles"] = {}
                    results1_with_doi["titles"][str(title).lower()] = idx
            
            for idx, result in enumerate(results2):
                # Handle both SearchResult objects and dictionaries
                if isinstance(result, dict):
                    doi = result.get('doi')
                    title = result.get('title', '')
                else:
                    doi = getattr(result, 'doi', None)
                    title = getattr(result, 'title', '')
                
                # Ensure doi and title are strings
                if isinstance(doi, list):
                    doi = doi[0] if doi else None
                if isinstance(title, list):
                    title = title[0] if title else ''
                
                if doi:
                    identifiers2.add(str(doi).lower())
                    results2_with_doi[str(doi).lower()] = idx
                else:
                    identifiers2.add(f"title:{str(title).lower()}")
                    results2_no_doi[str(title).lower()] = idx
                
                # Always track title for potential title matching
                if title:
                    # Store title with index regardless of DOI status
                    if "titles" not in results2_with_doi:
                        results2_with_doi["titles"] = {}
                    results2_with_doi["titles"][str(title).lower()] = idx
            
            # First, find overlap by DOI (most precise)
            overlap_doi = set(results1_with_doi.keys()) & set(results2_with_doi.keys())
            if "titles" in overlap_doi:
                overlap_doi.remove("titles")  # Remove the "titles" key from the overlap calculation
            
            # Then find overlap by title, but only for entries without DOIs
            overlap_title_no_doi = set(results1_no_doi.keys()) & set(results2_no_doi.keys())
            
            # Find all title matches regardless of DOI status
            all_title_matches = set()
            if "titles" in results1_with_doi and "titles" in results2_with_doi:
                all_title_matches = set(results1_with_doi["titles"].keys()) & set(results2_with_doi["titles"].keys())
            
            # Find which papers were matched by both DOI and title (to avoid double counting)
            # Papers matched by title that also have DOIs matched
            doi_title_overlap = set()
            for title in all_title_matches:
                # Get corresponding papers for this title
                papers1 = []
                for idx, r in enumerate(results1):
                    if idx in results1_with_doi.get("titles", {}).values():
                        # Handle both SearchResult objects and dictionaries
                        if isinstance(r, dict):
                            r_title = r.get('title', '')
                        else:
                            r_title = getattr(r, 'title', '')
                        
                        # Ensure title is a string
                        if isinstance(r_title, list):
                            r_title = r_title[0] if r_title else ''
                        
                        if str(r_title).lower() == title:
                            papers1.append(r)
                
                papers2 = []
                for idx, r in enumerate(results2):
                    if idx in results2_with_doi.get("titles", {}).values():
                        # Handle both SearchResult objects and dictionaries
                        if isinstance(r, dict):
                            r_title = r.get('title', '')
                        else:
                            r_title = getattr(r, 'title', '')
                        
                        # Ensure title is a string
                        if isinstance(r_title, list):
                            r_title = r_title[0] if r_title else ''
                        
                        if str(r_title).lower() == title:
                            papers2.append(r)
                
                # Check if any of these papers also match by DOI
                for p1 in papers1:
                    for p2 in papers2:
                        # Handle both SearchResult objects and dictionaries
                        if isinstance(p1, dict):
                            p1_doi = p1.get('doi')
                        else:
                            p1_doi = getattr(p1, 'doi', None)
                        
                        if isinstance(p2, dict):
                            p2_doi = p2.get('doi')
                        else:
                            p2_doi = getattr(p2, 'doi', None)
                        
                        # Ensure doi is a string
                        if isinstance(p1_doi, list):
                            p1_doi = p1_doi[0] if p1_doi else None
                        if isinstance(p2_doi, list):
                            p2_doi = p2_doi[0] if p2_doi else None
                        
                        if p1_doi and p2_doi and str(p1_doi).lower() == str(p2_doi).lower():
                            doi_title_overlap.add(title)
                            break
            
            # Calculate total unique matches (DOI matches + title-only matches)
            # Papers matched by DOI plus papers matched only by title (no DOI match)
            unique_title_matches = all_title_matches - doi_title_overlap
            total_overlap = len(overlap_doi) + len(unique_title_matches)
            
            # Store overlap results
            comparison_results["overlap"][pair_key] = {
                "overlap": total_overlap,
                "source1_only": len(identifiers1) - total_overlap,
                "source2_only": len(identifiers2) - total_overlap,
                # Add matching pairs for reference
                "matching_dois": list(overlap_doi),
                "matching_titles": list(overlap_title_no_doi),
                "all_matching_titles": list(all_title_matches),
                "unique_title_matches": list(unique_title_matches)
            }
            
            # Calculate same rank matches
            same_rank_matches = []
            # Check DOI matches first
            for doi in overlap_doi:
                if doi == "titles":  # Skip the titles key
                    continue
                idx1 = results1_with_doi.get(doi)
                idx2 = results2_with_doi.get(doi)
                if idx1 is not None and idx2 is not None:
                    r1 = results1[idx1]
                    r2 = results2[idx2]
                    rank1 = r1.get('rank') if isinstance(r1, dict) else getattr(r1, 'rank', 0)
                    rank2 = r2.get('rank') if isinstance(r2, dict) else getattr(r2, 'rank', 0)
                    if rank1 == rank2:
                        title1 = r1.get('title', '') if isinstance(r1, dict) else getattr(r1, 'title', '')
                        same_rank_matches.append({
                            "doi": doi,
                            "rank": rank1,
                            "title": title1
                        })
            
            # Then check title matches for papers without DOIs
            for title in overlap_title_no_doi:
                idx1 = results1_no_doi.get(title)
                idx2 = results2_no_doi.get(title)
                if idx1 is not None and idx2 is not None:
                    r1 = results1[idx1]
                    r2 = results2[idx2]
                    rank1 = r1.get('rank') if isinstance(r1, dict) else getattr(r1, 'rank', 0)
                    rank2 = r2.get('rank') if isinstance(r2, dict) else getattr(r2, 'rank', 0)
                    if rank1 == rank2:
                        same_rank_matches.append({
                            "title": title,
                            "rank": rank1
                        })
            
            # Add to results
            comparison_results["overlap"][pair_key]["same_rank_matches"] = same_rank_matches
            comparison_results["overlap"][pair_key]["same_rank_count"] = len(same_rank_matches)
            
            # Initialize similarity results for this pair
            if "similarity" not in comparison_results:
                comparison_results["similarity"] = {}
            
            # Initialize metric specific dictionaries if they don't exist
            for metric in metrics:
                if metric not in comparison_results["similarity"]:
                    comparison_results["similarity"][metric] = {}
            
            # Calculate similarity metrics
            for metric in metrics:
                if metric == "jaccard" or metric == "exact_match":
                    # Jaccard similarity is based on overlap in DOIs or titles
                    jaccard_sim = 0.0
                    
                    # Normalize the identifiers for better matching
                    norm_identifiers1 = set()
                    norm_identifiers2 = set()
                    
                    # Log the identifiers for debugging
                    logger.info(f"Calculating jaccard similarity for {source1} vs {source2}")
                    logger.info(f"Source1 ({source1}) has {len(results1)} results")
                    logger.info(f"Source2 ({source2}) has {len(results2)} results")
                    
                    # Prepare normalized identifiers
                    for r in results1:
                        # Handle both SearchResult objects and dictionaries
                        if isinstance(r, dict):
                            doi = r.get('doi')
                            title = r.get('title', '')
                        else:
                            doi = getattr(r, 'doi', None)
                            title = getattr(r, 'title', '')
                        
                        # Ensure doi and title are strings
                        if isinstance(doi, list):
                            doi = doi[0] if doi else None
                        if isinstance(title, list):
                            title = title[0] if title else ''
                        
                        if doi:
                            # Clean and normalize DOI
                            clean_doi = str(doi).lower().strip()
                            norm_identifiers1.add(f"doi:{clean_doi}")
                            logger.debug(f"Source1 DOI: {clean_doi}")
                        if title:
                            # Clean and normalize title
                            clean_title = str(title).lower().strip()
                            norm_identifiers1.add(f"title:{clean_title}")
                            logger.debug(f"Source1 Title: {clean_title}")
                    
                    for r in results2:
                        # Handle both SearchResult objects and dictionaries
                        if isinstance(r, dict):
                            doi = r.get('doi')
                            title = r.get('title', '')
                        else:
                            doi = getattr(r, 'doi', None)
                            title = getattr(r, 'title', '')
                        
                        # Ensure doi and title are strings
                        if isinstance(doi, list):
                            doi = doi[0] if doi else None
                        if isinstance(title, list):
                            title = title[0] if title else ''
                        
                        if doi:
                            # Clean and normalize DOI
                            clean_doi = str(doi).lower().strip()
                            norm_identifiers2.add(f"doi:{clean_doi}")
                            logger.debug(f"Source2 DOI: {clean_doi}")
                        if title:
                            # Clean and normalize title
                            clean_title = str(title).lower().strip()
                            norm_identifiers2.add(f"title:{clean_title}")
                            logger.debug(f"Source2 Title: {clean_title}")
                    
                    # Calculate intersection and union
                    intersection = norm_identifiers1.intersection(norm_identifiers2)
                    union = norm_identifiers1.union(norm_identifiers2)
                    
                    logger.info(f"Found {len(intersection)} matching identifiers out of {len(union)} total identifiers")
                    
                    if union:  # Avoid division by zero
                        jaccard_sim = len(intersection) / len(union)
                    
                    logger.info(f"Jaccard similarity for {source1} vs {source2}: {jaccard_sim}")
                    
                    # Store in both formats for compatibility
                    comparison_results["similarity"]["jaccard"][pair_key] = jaccard_sim
                    
                    # Also calculate field-specific Jaccard similarities
                    for field in fields:
                        # Extract values from results
                        values1 = []
                        for r in results1:
                            # Handle both SearchResult objects and dictionaries
                            if isinstance(r, dict):
                                value = r.get(field, "") or ""
                            else:
                                value = getattr(r, field, "") or ""
                            # Convert list to tuple if necessary (lists are unhashable)
                            if isinstance(value, list):
                                for item in value:
                                    values1.append(str(item).lower().strip())
                            else:
                                values1.append(str(value).lower().strip())
                        values1 = {v for v in values1 if v}
                        
                        values2 = []
                        for r in results2:
                            # Handle both SearchResult objects and dictionaries
                            if isinstance(r, dict):
                                value = r.get(field, "") or ""
                            else:
                                value = getattr(r, field, "") or ""
                            # Convert list to tuple if necessary (lists are unhashable)
                            if isinstance(value, list):
                                for item in value:
                                    values2.append(str(item).lower().strip())
                            else:
                                values2.append(str(value).lower().strip())
                        values2 = {v for v in values2 if v}
                        
                        # Calculate Jaccard similarity for this field
                        field_sim = calculate_jaccard_similarity(values1, values2)
                        
                        # Store result with field name
                        comparison_results["similarity"]["jaccard"][f"{pair_key}_{field}"] = field_sim
                
                elif metric == "rankBiased" or metric == "rank_correlation":
                    # Extract identifiers from each source, matching by DOI first, then title
                    logger.info(f"Calculating rank-biased overlap for {source1} vs {source2}")
                    
                    # Create lists to preserve the ranking order
                    items1 = []
                    items2 = []
                    
                    # Create maps between identifiers and their indices
                    id_to_index1 = {}
                    id_to_index2 = {}
                    
                    # Process results and build ranked lists with both DOI and title identifiers
                    for idx, r in enumerate(results1):
                        # Handle both SearchResult objects and dictionaries
                        if isinstance(r, dict):
                            doi = r.get('doi')
                            title = r.get('title', '')
                        else:
                            doi = getattr(r, 'doi', None)
                            title = getattr(r, 'title', '')
                        
                        # Ensure doi and title are strings
                        if isinstance(doi, list):
                            doi = doi[0] if doi else None
                        if isinstance(title, list):
                            title = title[0] if title else ''
                        
                        identifier = None
                        if doi:
                            clean_doi = str(doi).lower().strip()
                            identifier = f"doi:{clean_doi}"
                        elif title:
                            clean_title = str(title).lower().strip()
                            identifier = f"title:{clean_title}"
                        
                        if identifier:
                            items1.append(identifier)
                            id_to_index1[identifier] = idx
                            
                            # Also add title as alternative identifier if DOI exists
                            if doi and title:
                                alt_id = f"title:{str(title).lower().strip()}"
                                id_to_index1[alt_id] = idx
                    
                    for idx, r in enumerate(results2):
                        # Handle both SearchResult objects and dictionaries
                        if isinstance(r, dict):
                            doi = r.get('doi')
                            title = r.get('title', '')
                        else:
                            doi = getattr(r, 'doi', None)
                            title = getattr(r, 'title', '')
                        
                        # Ensure doi and title are strings
                        if isinstance(doi, list):
                            doi = doi[0] if doi else None
                        if isinstance(title, list):
                            title = title[0] if title else ''
                        
                        identifier = None
                        if doi:
                            clean_doi = str(doi).lower().strip()
                            identifier = f"doi:{clean_doi}"
                        elif title:
                            clean_title = str(title).lower().strip()
                            identifier = f"title:{clean_title}"
                        
                        if identifier:
                            items2.append(identifier)
                            id_to_index2[identifier] = idx
                            
                            # Also add title as alternative identifier if DOI exists
                            if doi and title:
                                alt_id = f"title:{str(title).lower().strip()}"
                                id_to_index2[alt_id] = idx
                    
                    # Log the items for debugging
                    logger.info(f"Source1 ({source1}) ranked list has {len(items1)} items")
                    logger.info(f"Source2 ({source2}) ranked list has {len(items2)} items")
                    
                    # Find overlapping items for debugging
                    overlap_items = set([i for i in items1 if i in items2 or i.replace("doi:", "title:") in items2 or i.replace("title:", "doi:") in items2])
                    logger.info(f"Found {len(overlap_items)} overlapping items in rank lists")
                    
                    # Calculate rank-based overlap
                    rbo_similarity = calculate_rank_based_overlap(items1, items2)
                    logger.info(f"Rank-biased overlap for {source1} vs {source2}: {rbo_similarity}")
                    
                    # Store in both formats for compatibility
                    comparison_results["similarity"]["rankBiased"][pair_key] = rbo_similarity
                
                elif metric == "cosine" or metric == "content_similarity":
                    # Calculate cosine similarity based on text content
                    for field in fields:
                        if field in ["title", "abstract"]:
                            # Extract and preprocess text
                            texts1 = []
                            for r in results1:
                                # Handle both SearchResult objects and dictionaries
                                if isinstance(r, dict):
                                    text = r.get(field, "") or ""
                                else:
                                    text = getattr(r, field, "") or ""
                                texts1.append(preprocess_text(text))
                            texts1 = [t for t in texts1 if t]
                            
                            texts2 = []
                            for r in results2:
                                # Handle both SearchResult objects and dictionaries
                                if isinstance(r, dict):
                                    text = r.get(field, "") or ""
                                else:
                                    text = getattr(r, field, "") or ""
                                texts2.append(preprocess_text(text))
                            texts2 = [t for t in texts2 if t]
                            
                            # Skip if either list is empty
                            if not texts1 or not texts2:
                                continue
                            
                            # Convert to term frequency dictionaries
                            vec1: Dict[str, int] = {}
                            for text in texts1:
                                for term in text.split():
                                    vec1[term] = vec1.get(term, 0) + 1
                            
                            vec2: Dict[str, int] = {}
                            for text in texts2:
                                for term in text.split():
                                    vec2[term] = vec2.get(term, 0) + 1
                            
                            # Calculate cosine similarity
                            cosine_sim = calculate_cosine_similarity(vec1, vec2)
                            
                            # Store result
                            comparison_results["similarity"]["cosine"][f"{pair_key}_{field}"] = cosine_sim
    
    return comparison_results


async def get_paper_details(doi: str, sources: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Get detailed paper information by DOI from multiple sources.
    
    Retrieves detailed metadata for a paper identified by its DOI from
    multiple search engines and combines the results.
    
    Args:
        doi: Digital Object Identifier for the paper
        sources: List of sources to query (if None, query all available)
    
    Returns:
        Dict[str, Any]: Combined paper details from all sources
    """
    if not doi:
        logger.warning("Empty DOI provided to get_paper_details")
        return {}
    
    # Default to all sources if not specified
    if sources is None:
        sources = ["ads", "semanticScholar", "webOfScience"]
    
    # Filter to only enabled sources
    enabled_sources = [
        source for source in sources
        if source in SERVICE_CONFIG and SERVICE_CONFIG[source]["enabled"]
    ]
    
    # Initialize results
    results: Dict[str, Any] = {
        "doi": doi,
        "sources": {}
    }
    
    # Gather tasks for fetching from all sources
    tasks = []
    
    for source in enabled_sources:
        if source == "ads":
            from .ads_service import get_bibcode_from_doi
            tasks.append(get_bibcode_from_doi(doi))
        elif source == "semanticScholar":
            from .semantic_scholar_service import get_paper_details_by_doi
            tasks.append(get_paper_details_by_doi(doi))
        elif source == "webOfScience":
            from .web_of_science_service import get_wos_paper_details
            tasks.append(get_wos_paper_details(doi))
    
    # Run all tasks concurrently
    source_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    for source, source_result in zip(enabled_sources, source_results):
        if isinstance(source_result, Exception):
            logger.error(f"Error getting paper details from {source}: {str(source_result)}")
            results["sources"][source] = {"error": str(source_result)}
        elif source_result:
            results["sources"][source] = source_result
    
    return results 