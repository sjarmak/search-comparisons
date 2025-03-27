"""
Service modules for the search-comparisons application.

This package contains service modules that handle interactions with
external APIs and data sources, including search engines and other
academic data providers.
"""

# Import and expose all service modules for convenience
from . import (
    search_service,
    ads_service,
    scholar_service,
    semantic_scholar_service,
    web_of_science_service,
    quepid_service
) 