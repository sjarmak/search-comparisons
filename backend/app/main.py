"""
Main application module for the search-comparisons backend.

This module configures and starts the FastAPI application, including middleware,
exception handlers, and route registration.
"""
import logging
import os
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv
import math
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import search_routes, debug_routes, experiment_routes
from .api.models import ErrorResponse

# Set up platform-specific fixes and environment variables first
# Apply macOS SSL certificate handling fix if needed
if os.name == 'posix' and 'darwin' in os.uname().sysname.lower():
    import ssl
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()

# Load environment variables
load_dotenv()  # First try .env file

# Ensure critical environment variables are set
ADS_API_KEY = os.getenv("ADS_API_KEY", "")
if not ADS_API_KEY:
    # Check if ADS_API_TOKEN is available instead
    ads_api_token = os.getenv("ADS_API_TOKEN", "")
    if ads_api_token:
        print("Found ADS_API_TOKEN instead. Setting as ADS_API_KEY.")
        os.environ["ADS_API_KEY"] = ads_api_token
    else:
        # Set emergency fallback for testing
        print("Setting emergency fallback ADS_API_KEY for testing only")
        os.environ["ADS_API_KEY"] = "F6pHGICMXXy4aiAWBR4gaFL4Ta72xdM8jVhHDOsm"

# Set up logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Log API key status (masked)
ads_api_key = os.environ.get("ADS_API_KEY", "")
if ads_api_key:
    masked_key = f"{ads_api_key[:4]}...{ads_api_key[-4:]}" if len(ads_api_key) > 8 else "[KEY]"
    logger.info(f"ADS_API_KEY found! Length: {len(ads_api_key)}, Value (masked): {masked_key}")

# Service configuration
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

# Create FastAPI app
app = FastAPI(
    title="Academic Search Results Comparator API",
    description="API for comparing search results from multiple academic search engines",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    debug=os.getenv("DEBUG", "True").lower() in ("true", "1", "t", "yes")
)

# Configure CORS with wildcard for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development/testing
    allow_credentials=False,  # Must be False when using wildcard origins
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for all unhandled exceptions.
    
    Args:
        request: The request that caused the exception
        exc: The exception that was raised
    
    Returns:
        JSONResponse: A JSON response with error details
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred",
            details=str(exc) if os.getenv("DEBUG", "True").lower() in ("true", "1", "t", "yes") else None,
        ).model_dump(),
    )


@app.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns:
        Dict[str, Any]: Health status information
    """
    return {
        "status": "ok",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "local"),
    }


# Include routers
app.include_router(search_routes.router)
app.include_router(debug_routes.router)
app.include_router(experiment_routes.router)


@app.on_event("startup")
async def startup_event() -> None:
    """
    Execute startup tasks for the application.
    
    Performs initialization tasks when the application starts.
    """
    logger.info(f"Starting Academic Search Results Comparator API v1.0.0")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'local')}")
    logger.info(f"Debug mode: {os.getenv('DEBUG', 'True')}")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Execute shutdown tasks for the application.
    
    Performs cleanup tasks when the application shuts down.
    """
    logger.info("Shutting down Academic Search Results Comparator API")


@app.post("/api/boost-experiment")
async def boost_experiment(data: dict):
    """
    Apply configurable boost factors to search results using ADS metadata.
    
    This endpoint supports the advanced query transformation approach described in the RFC,
    which breaks down a user query into field-specific boosted components.
    """
    try:
        logger.info("Starting boost experiment with data:")
        logger.info(f"Query: {data.get('query')}")
        logger.info(f"Number of results: {len(data.get('results', []))}")
        logger.info(f"Boost config: {data.get('boostConfig')}")
        
        # Get input data
        query = data.get("query", "")
        transformed_query = data.get("transformedQuery", "")
        original_results = data.get("results", [])
        boost_config = data.get("boostConfig", {})
        
        # Log raw boost config values for debugging
        logger.info(f"CRITICAL DEBUG - Raw boost weights: "
                   f"cite={boost_config.get('citeBoostWeight')}, "
                   f"recency={boost_config.get('recencyBoostWeight')}, "
                   f"doctype={boost_config.get('doctypeBoostWeight')}, "
                   f"refereed={boost_config.get('refereedBoostWeight')}")
        
        if not original_results:
            logger.warning("No results provided for boost experiment")
            return {
                "status": "error",
                "message": "No results to process"
            }
        
        # Log if we're using a transformed query
        if transformed_query:
            logger.info(f"Using transformed query: {transformed_query}")
        
        # Process each result to add boost factors
        boosted_results = []
        current_year = datetime.now().year
        
        for idx, result in enumerate(original_results):
            try:
                # Initialize boost factors
                boost_factors = {
                    "citeBoost": 0.0,
                    "recencyBoost": 0.0,
                    "doctypeBoost": 0.0,
                    "refereedBoost": 0.0
                }
                
                # Log the raw result data for debugging
                logger.info(f"Processing result {idx + 1}:")
                logger.info(f"Citation count: {result.get('citation_count')}")
                logger.info(f"Document type: {result.get('doctype')}")
                logger.info(f"Properties: {result.get('property')}")
                
                # 1. Citation boost (Enhanced per RFC - use logarithmic scaling)
                if boost_config.get("enableCiteBoost"):
                    citation_count = result.get("citation_count", 0)
                    # Handle None citation count
                    if citation_count is None:
                        citation_count = 0
                    
                    # Get the citation boost weight (ensure it's a number)
                    cite_boost_weight = float(boost_config.get("citeBoostWeight", 1.0))
                    logger.info(f"Using citation boost weight: {cite_boost_weight}")
                    
                    # Use logarithmic scaling to handle large variations in citation counts
                    # This is more fair across disciplines and reflects the RFC's recommendation
                    cite_boost = math.log1p(citation_count) * cite_boost_weight
                    boost_factors["citeBoost"] = cite_boost
                    logger.info(f"Applied citation boost: {boost_factors['citeBoost']} for {citation_count} citations with weight {cite_boost_weight}")
                
                # 2. Recency boost (Following RFC recommendations for different decay functions)
                if boost_config.get("enableRecencyBoost"):
                    pub_year = result.get("year")
                    if pub_year:
                        # Calculate age in months (approximate)
                        age_in_years = current_year - pub_year
                        age_in_months = age_in_years * 12
                        
                        recency_boost = 0.0
                        multiplier = boost_config.get("recencyMultiplier", 0.01)
                        recency_function = boost_config.get("recencyFunction", "exponential")
                        
                        # Get the recency boost weight (ensure it's a number)
                        recency_boost_weight = float(boost_config.get("recencyBoostWeight", 1.0))
                        logger.info(f"Using recency boost weight: {recency_boost_weight}")
                        
                        # Apply different decay functions as outlined in the RFC
                        if recency_function == "exponential":
                            # Exponential decay: e^(-m * age_months)
                            recency_boost = math.exp(-multiplier * age_in_months)
                        elif recency_function == "inverse":
                            # Reciprocal/inverse Function: 1/(1 + multiplier * age_months)
                            recency_boost = 1 / (1 + multiplier * age_in_months)
                        elif recency_function == "linear":
                            # Linear Decay: max(1 - m * age_months, 0)
                            recency_boost = max(0, 1 - multiplier * age_in_months)
                        elif recency_function == "sigmoid":
                            # Logistic/Sigmoid: 1/(1 + e^(m * (age_months - midpoint)))
                            midpoint = boost_config.get("recencyMidpoint", 36)  # Default 3 years
                            recency_boost = 1 / (1 + math.exp(multiplier * (age_in_months - midpoint)))
                        
                        boost_factors["recencyBoost"] = recency_boost * recency_boost_weight
                        logger.info(f"Applied recency boost: {boost_factors['recencyBoost']} for year {pub_year} with weight {recency_boost_weight}")
                
                # 3. Document type boost (Following ADS DocType Ranking as in RFC)
                if boost_config.get("enableDoctypeBoost"):
                    doctype = result.get("doctype", "")
                    # Handle None doctype
                    if doctype is None:
                        doctype = ""
                    
                    # Get the doctype boost weight (ensure it's a number)
                    doctype_boost_weight = float(boost_config.get("doctypeBoostWeight", 1.0))
                    logger.info(f"Using doctype boost weight: {doctype_boost_weight}")
                    
                    # Normalize doctype to lowercase string for comparison
                    doctype_str = doctype.lower() if isinstance(doctype, str) else ""
                    
                    # Weights based on ADS document types, ordered by importance as in RFC
                    # The boost factor is evenly distributed from 1 (most important) to 0 (least important)
                    doctype_ranks = {
                        "review": 1,       # Review article (highest rank)
                        "book": 2,         # Book
                        "article": 3,      # Standard article
                        "eprint": 4,       # Preprints
                        "proceedings": 5,  # Conference proceedings
                        "inproceedings": 5,# Conference proceedings (same rank)
                        "thesis": 6,       # Thesis/dissertation
                        "": 7              # Default/unknown (lowest rank)
                    }
                    
                    # Calculate boosting using the rank-to-boost conversion formula from RFC
                    rank = doctype_ranks.get(doctype_str, 7)  # Default to lowest rank if unknown
                    unique_ranks = sorted(set(doctype_ranks.values()))
                    total_ranks = len(unique_ranks)
                    
                    # Apply the formula: 1 - (rank_index / (num_unique_ranks - 1))
                    rank_index = unique_ranks.index(rank)
                    doctype_boost = 1 - (rank_index / (total_ranks - 1)) if total_ranks > 1 else 0
                    
                    boost_factors["doctypeBoost"] = doctype_boost * doctype_boost_weight
                    logger.info(f"Applied doctype boost: {boost_factors['doctypeBoost']} for type {doctype_str} with weight {doctype_boost_weight}")
                
                # 4. Refereed boost (Simple binary boost as suggested in RFC)
                if boost_config.get("enableRefereedBoost"):
                    properties = result.get("property", [])
                    # Handle None properties
                    if properties is None:
                        properties = []
                    elif isinstance(properties, str):
                        properties = [properties]
                    
                    # Get the refereed boost weight (ensure it's a number)
                    refereed_boost_weight = float(boost_config.get("refereedBoostWeight", 1.0))
                    logger.info(f"Using refereed boost weight: {refereed_boost_weight}")
                        
                    is_refereed = "REFEREED" in properties
                    # Simple binary boost: 1 if refereed, 0 if not
                    boost_factors["refereedBoost"] = float(is_refereed) * refereed_boost_weight
                    logger.info(f"Applied refereed boost: {boost_factors['refereedBoost']} (is_refereed: {is_refereed}) with weight {refereed_boost_weight}")
                
                # Calculate final boost based on combination method (as described in RFC)
                combination_method = boost_config.get("combinationMethod", "sum")
                logger.info(f"Using combination method: {combination_method}")
                
                if combination_method == "sum":
                    # Simple sum: citation + recency + doctype + refereed
                    final_boost = sum(boost_factors.values())
                elif combination_method == "product":
                    # Product: (1+citation) * (1+recency) * (1+doctype) * (1+refereed) - 1
                    # This is equivalent to (1 + citation + recency + doctype + refereed + citation*recency + ...)
                    final_boost = math.prod([1 + b for b in boost_factors.values()]) - 1
                elif combination_method == "max":
                    # Maximum: use the highest boost factor
                    final_boost = max(boost_factors.values())
                else:
                    # Default to sum if invalid method
                    final_boost = sum(boost_factors.values())
                
                # Create boosted result
                boosted_result = {
                    **result,  # Keep all original fields
                    "boostFactors": boost_factors,
                    "finalBoost": final_boost,
                    "originalRank": idx + 1
                }
                boosted_results.append(boosted_result)
                
                logger.info(f"Final boost: {final_boost}")
                logger.info(f"Boost factors: {boost_factors}")
                
            except Exception as e:
                logger.error(f"Error processing result {idx}: {str(e)}")
                # Still add this result to the boosted results, but with minimal boosts
                boosted_result = {
                    **result,  # Keep all original fields
                    "boostFactors": {
                        "citeBoost": 0.0,
                        "recencyBoost": 0.0,
                        "doctypeBoost": 0.0,
                        "refereedBoost": 0.0
                    },
                    "finalBoost": 0.0,
                    "originalRank": idx + 1
                }
                boosted_results.append(boosted_result)
                continue
        
        # Sort results by final boost score (descending)
        boosted_results.sort(key=lambda x: x.get("finalBoost", 0), reverse=True)
        
        # Add new ranks and calculate rank changes
        for idx, result in enumerate(boosted_results):
            result["rank"] = idx + 1
            result["rankChange"] = result["originalRank"] - result["rank"]
        
        return {
            "status": "success",
            "query": query,
            "transformedQuery": transformed_query,
            "results": boosted_results,
            "boostConfig": boost_config
        }
        
    except Exception as e:
        logger.exception(f"Error in boost experiment: {str(e)}")
        return {
            "status": "error",
            "message": f"Error processing boost experiment: {str(e)}"
        }