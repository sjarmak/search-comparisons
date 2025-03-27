"""
Tests for the utility modules of the search-comparisons application.

This module contains tests for the utility functions, including HTTP utilities,
text processing, similarity calculations, and caching.
"""
import hashlib
import os
import time
from typing import Set, Dict, Any, List
from unittest.mock import MagicMock, patch, mock_open

import pytest
import httpx
from httpx import Response

from app.utils.text_processing import normalize_text, stem_text, preprocess_text
from app.utils.similarity import (
    calculate_jaccard_similarity,
    calculate_rank_based_overlap,
    calculate_cosine_similarity
)
from app.utils.cache import get_cache_key, save_to_cache, load_from_cache
from app.api.models import SearchResult

# Text Processing Tests


def test_normalize_text() -> None:
    """Test the normalize_text function with various inputs."""
    # Test with regular text with punctuation and capitalization
    text = "Hello, World! This is a TEST string with PUNCTUATION."
    expected = "hello world this is a test string with punctuation"
    
    assert normalize_text(text) == expected
    
    # Test with empty string
    assert normalize_text("") == ""
    
    # Test with None
    assert normalize_text(None) == ""
    
    # Test with multiple spaces and tabs
    text = "   Multiple    spaces\tand\ttabs   "
    expected = "multiple spaces and tabs"
    
    assert normalize_text(text) == expected


def test_stem_text() -> None:
    """Test the stem_text function for stemming functionality."""
    # Test with words that should be stemmed
    text = "running jumps fishing believed studies"
    expected = "run jump fish believ studi"
    
    assert stem_text(text) == expected
    
    # Test with empty string
    assert stem_text("") == ""
    
    # Test with None
    assert stem_text(None) == ""


def test_preprocess_text() -> None:
    """Test the preprocess_text function combining normalization and stemming."""
    # Test with full preprocessing (normalization + stemming)
    text = "Running and Jumping, with CAPITALIZED words!"
    expected = "run and jump with capit word"
    
    assert preprocess_text(text) == expected
    
    # Test without stemming
    expected_no_stemming = "running and jumping with capitalized words"
    assert preprocess_text(text, apply_stemming=False) == expected_no_stemming
    
    # Test with empty string
    assert preprocess_text("") == ""
    
    # Test with None
    assert preprocess_text(None) == ""


# Similarity Tests

def test_jaccard_similarity() -> None:
    """Test the calculate_jaccard_similarity function with different sets."""
    # Test with identical sets
    set1: Set[str] = {"apple", "banana", "cherry"}
    set2: Set[str] = {"apple", "banana", "cherry"}
    assert calculate_jaccard_similarity(set1, set2) == 1.0
    
    # Test with completely different sets
    set3: Set[str] = {"dog", "cat", "bird"}
    assert calculate_jaccard_similarity(set1, set3) == 0.0
    
    # Test with partial overlap
    set4: Set[str] = {"apple", "dog", "cat"}
    # Overlap: 1, Union: 5 -> 1/5 = 0.2
    assert calculate_jaccard_similarity(set1, set4) == 0.2
    
    # Test with empty sets
    empty_set: Set[str] = set()
    # Both empty sets should be 1.0 (identical)
    assert calculate_jaccard_similarity(empty_set, empty_set) == 1.0
    # One empty, one not should be 0.0
    assert calculate_jaccard_similarity(empty_set, set1) == 0.0


def test_rank_based_overlap() -> None:
    """Test the calculate_rank_based_overlap function with different lists."""
    # Test with identical lists
    list1 = ["apple", "banana", "cherry"]
    list2 = ["apple", "banana", "cherry"]
    assert calculate_rank_based_overlap(list1, list2) == 1.0
    
    # Test with completely different lists
    list3 = ["dog", "cat", "bird"]
    assert calculate_rank_based_overlap(list1, list3) < 0.1  # Almost 0
    
    # Test with same items but different order
    list4 = ["cherry", "banana", "apple"]
    # Should be less than 1.0 but greater than 0.0
    similarity = calculate_rank_based_overlap(list1, list4)
    assert 0.0 < similarity < 1.0
    
    # Test with empty lists
    empty_list: List[str] = []
    # Both empty should be 1.0 (identical)
    assert calculate_rank_based_overlap(empty_list, empty_list) == 1.0
    # One empty, one not should be 0.0
    assert calculate_rank_based_overlap(empty_list, list1) == 0.0


def test_cosine_similarity() -> None:
    """Test the calculate_cosine_similarity function with term frequency dictionaries."""
    # Test with identical dictionaries
    vec1 = {"apple": 1, "banana": 2, "cherry": 3}
    vec2 = {"apple": 1, "banana": 2, "cherry": 3}
    assert calculate_cosine_similarity(vec1, vec2) == 1.0
    
    # Test with completely different dictionaries
    vec3 = {"dog": 1, "cat": 2, "bird": 3}
    assert calculate_cosine_similarity(vec1, vec3) == 0.0
    
    # Test with partial overlap
    vec4 = {"apple": 1, "dog": 2, "cat": 3}
    # Should be greater than 0.0 but less than 1.0
    similarity = calculate_cosine_similarity(vec1, vec4)
    assert 0.0 < similarity < 1.0
    
    # Test with empty dictionaries
    empty_vec: Dict[str, int] = {}
    # Both empty should be 1.0 (identical)
    assert calculate_cosine_similarity(empty_vec, empty_vec) == 1.0
    # One empty, one not should be 0.0
    assert calculate_cosine_similarity(empty_vec, vec1) == 0.0


# Cache Tests

def test_get_cache_key() -> None:
    """Test the get_cache_key function for consistent hash generation."""
    # Test basic key generation
    source = "ads"
    query = "test query"
    fields = ["title", "abstract"]
    
    # Calculate expected hash
    hash_input = f"{source}:{query}:{':'.join(sorted(fields))}"
    expected = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
    
    assert get_cache_key(source, query, fields) == expected
    
    # Test that field order doesn't matter
    fields_reordered = ["abstract", "title"]
    assert get_cache_key(source, query, fields) == get_cache_key(source, query, fields_reordered)
    
    # Test with num_results parameter
    num_results = 50
    hash_input_with_results = f"{source}:{query}:{':'.join(sorted(fields))}:{num_results}"
    expected_with_results = hashlib.sha256(hash_input_with_results.encode('utf-8')).hexdigest()
    
    assert get_cache_key(source, query, fields, num_results) == expected_with_results
    
    # Test that different num_results produces different keys
    key_with_results_10 = get_cache_key(source, query, fields, 10)
    key_with_results_20 = get_cache_key(source, query, fields, 20)
    assert key_with_results_10 != key_with_results_20
    
    # Test different inputs produce different keys
    key1 = get_cache_key("ads", "query1", ["title"])
    key2 = get_cache_key("scholar", "query1", ["title"])
    key3 = get_cache_key("ads", "query2", ["title"])
    key4 = get_cache_key("ads", "query1", ["abstract"])
    key5 = get_cache_key("ads", "query1", ["title"], 50)
    
    assert len({key1, key2, key3, key4, key5}) == 5  # All keys should be different


@patch('os.makedirs')
@patch('json.dump')
def test_save_to_cache(mock_json_dump: MagicMock, mock_makedirs: MagicMock) -> None:
    """Test the save_to_cache function for storing search results."""
    # Create mock results
    results = [
        SearchResult(title="Test Paper 1", source="ads", rank=1),
        SearchResult(title="Test Paper 2", source="ads", rank=2)
    ]
    
    # Mock open to avoid actual file operations
    with patch('builtins.open', mock_open()) as mock_file:
        # Call the function
        success = save_to_cache("testkey", results)
        
        # Check if directories were created
        mock_makedirs.assert_called_once()
        
        # Check if file was opened
        mock_file.assert_called_once()
        
        # Check if json.dump was called
        mock_json_dump.assert_called_once()
        
        # Check success return value
        assert success is True


@patch('os.path.exists')
@patch('json.load')
def test_load_from_cache_hit(mock_json_load: MagicMock, mock_exists: MagicMock) -> None:
    """Test the load_from_cache function when cache is hit."""
    # Setup mocks
    mock_exists.return_value = True
    mock_json_load.return_value = {
        "timestamp": time.time(),  # Current time
        "expiry": 3600,  # 1 hour
        "results": [
            {"title": "Test Paper 1", "source": "ads", "rank": 1},
            {"title": "Test Paper 2", "source": "ads", "rank": 2}
        ]
    }
    
    # Mock open to avoid actual file operations
    with patch('builtins.open', mock_open()) as mock_file:
        # Call the function
        results = load_from_cache("testkey")
        
        # Check if file existence was checked
        mock_exists.assert_called_once()
        
        # Check if file was opened
        mock_file.assert_called_once()
        
        # Check if json.load was called
        mock_json_load.assert_called_once()
        
        # Check the results
        assert results is not None
        assert len(results) == 2
        assert results[0].title == "Test Paper 1"
        assert results[1].title == "Test Paper 2"


@patch('os.path.exists')
def test_load_from_cache_miss(mock_exists: MagicMock) -> None:
    """Test the load_from_cache function when cache is missed."""
    # Setup mock
    mock_exists.return_value = False
    
    # Call the function
    results = load_from_cache("testkey")
    
    # Check if file existence was checked
    mock_exists.assert_called_once()
    
    # Check the results
    assert results is None 