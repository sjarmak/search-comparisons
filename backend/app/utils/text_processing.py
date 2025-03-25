"""
Text processing utilities for the search-comparisons application.

This module provides functions for normalizing and processing text,
including normalization, stemming, and preprocessing for similarity
calculations.
"""
import re
import logging
from typing import List, Set, Dict, Optional

import nltk
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize

# Setup logging
logger = logging.getLogger(__name__)

# Initialize stemmer
stemmer = PorterStemmer()

# Ensure NLTK resources are available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)


def normalize_text(text: str) -> str:
    """
    Normalize text by removing special characters and extra whitespace.
    
    Converts text to lowercase, removes special characters, and normalizes
    whitespace to single spaces.
    
    Args:
        text: Text string to normalize
    
    Returns:
        str: Normalized text string
    """
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove special characters, keeping letters, numbers, and spaces
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Trim leading/trailing whitespace
    text = text.strip()
    
    return text


def stem_text(text: str) -> str:
    """
    Apply stemming to normalize word forms.
    
    Tokenizes text and applies Porter stemming to reduce words to their stems,
    which helps with matching similar words (e.g., "running" and "runs" both
    stem to "run").
    
    Args:
        text: Text string to stem
    
    Returns:
        str: Space-separated string of stemmed words
    """
    if not text:
        return ""
    
    # Tokenize the text
    tokens = word_tokenize(text)
    
    # Apply stemming to each token
    stemmed_tokens = [stemmer.stem(token) for token in tokens]
    
    # Join stemmed tokens back into a string
    return " ".join(stemmed_tokens)


def preprocess_text(text: str, apply_stemming: bool = True) -> str:
    """
    Preprocess text for comparison by normalizing and optionally stemming.
    
    Combines normalization and stemming into a single preprocessing step,
    making text ready for similarity comparisons.
    
    Args:
        text: Text string to preprocess
        apply_stemming: Whether to apply stemming (default: True)
    
    Returns:
        str: Preprocessed text string
    """
    if not text:
        return ""
    
    # Normalize the text first
    normalized = normalize_text(text)
    
    # Apply stemming if requested
    if apply_stemming:
        return stem_text(normalized)
    
    return normalized 