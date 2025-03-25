"""
Environment configuration module for search-comparisons.

This module handles the loading of environment variables from .env files and
applies platform-specific fixes for SSL certificates and other issues.
"""
import os
import logging
import platform
import ssl
import certifi
from typing import List, Optional
from pathlib import Path

# Initialize logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_environment() -> bool:
    """
    Initialize environment variables with multiple fallback mechanisms.
    
    Attempts to load environment variables from .env files in several possible
    locations. Sets fallback values for critical variables if they are not found.
    
    Returns:
        bool: True if environment variables were successfully loaded, False otherwise.
    """
    logger.info("Initializing environment variables")
    
    # Try multiple possible locations for .env file
    possible_paths: List[str] = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env'),  # backend/.env
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), '.env'),  # .env in root directory
        '.env'  # Relative to current working directory
    ]
    
    env_loaded: bool = False
    for path in possible_paths:
        logger.info(f"Checking for .env file at: {path}")
        if os.path.exists(path):
            logger.info(f"Found .env file at: {path}")
            try:
                # Try loading with python-dotenv
                from dotenv import load_dotenv
                load_dotenv(dotenv_path=path)
                logger.info("Loaded .env file with python-dotenv")
                
                # Also try direct loading as a backup
                with open(path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip().strip('"\'')
                            logger.info(f"Directly set environment variable: {key.strip()}")
                
                env_loaded = True
                break
            except Exception as e:
                logger.error(f"Error loading .env file from {path}: {str(e)}")
    
    if not env_loaded:
        logger.warning("No .env file was successfully loaded")
    
    # Check for critical environment variables
    ads_api_key: Optional[str] = os.environ.get("ADS_API_KEY", "")
    if ads_api_key:
        # Mask key for logging
        masked_key = f"{ads_api_key[:4]}...{ads_api_key[-4:]}" if len(ads_api_key) > 8 else "[KEY]"
        logger.info(f"ADS_API_KEY found! Length: {len(ads_api_key)}, Value (masked): {masked_key}")
    else:
        logger.error("ADS_API_KEY not found in environment!")
        # Hard-code emergency fallback for testing
        logger.warning("Setting emergency fallback ADS_API_KEY for testing only")
        os.environ["ADS_API_KEY"] = "F6pHGICMXXy4aiAWBR4gaFL4Ta72xdM8jVhHDOsm"
        logger.info("Emergency ADS_API_KEY set")
    
    return env_loaded


def apply_platform_specific_fixes() -> None:
    """
    Apply fixes specific to the operating system platform.
    
    Currently handles SSL certificate issues on macOS by setting the appropriate
    certificate paths and environment variables.
    """
    system: str = platform.system()
    logger.info(f"Detected platform: {system}")
    
    if system == "Darwin":  # macOS
        # Fix for macOS SSL certificate verification issues
        try:
            # Override SSL default context with certifi's certificate bundle
            ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
            
            # Set environment variables for requests/urllib3
            os.environ['SSL_CERT_FILE'] = certifi.where()
            os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
            
            logger.info(f"SSL certificate path set to: {certifi.where()}")
            logger.info("Successfully applied macOS-specific SSL fixes")
        except Exception as e:
            logger.error(f"Failed to apply macOS-specific SSL fixes: {str(e)}") 