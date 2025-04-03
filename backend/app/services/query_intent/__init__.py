"""
Query intent service for interpreting and transforming search queries.

This package provides functionality to detect user intent in search queries
and transform them into more effective queries with appropriate search syntax.
"""

from .agent import QueryAgent

__all__ = ['QueryAgent'] 