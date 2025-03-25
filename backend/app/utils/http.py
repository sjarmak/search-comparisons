"""
HTTP utility functions for the search-comparisons application.

This module provides utilities for making HTTP requests, including
a timeout context manager and a safe API request function with proper
error handling and retry logic.
"""
import signal
import time
import logging
import random
from contextlib import contextmanager
from typing import Any, Dict, Optional, Union, Callable, TypeVar, cast

import httpx

# Setup logging
logger = logging.getLogger(__name__)

# Define a generic type variable for the return type
T = TypeVar('T')


class timeout:
    """
    Context manager for timeouts, using SIGALRM signal.
    
    Allows setting a maximum time for operations that might hang indefinitely.
    Raises a TimeoutError if the operation doesn't complete within the specified time.
    
    Attributes:
        seconds: Number of seconds before timing out
        timeout_message: Custom message for the timeout error
    """
    def __init__(self, seconds: int, *, timeout_message: str = 'Operation timed out'):
        """
        Initialize the timeout context manager.
        
        Args:
            seconds: Number of seconds before timeout
            timeout_message: Custom message for the timeout error
        """
        self.seconds = seconds
        self.timeout_message = timeout_message
    
    def __enter__(self) -> 'timeout':
        """
        Start the timer when entering the context.
        
        Returns:
            self: The timeout instance
        """
        self.old_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, self._timeout_handler)
        signal.alarm(self.seconds)
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Cancel the timer when exiting the context and restore the old signal handler.
        
        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        signal.alarm(0)
        signal.signal(signal.SIGALRM, self.old_handler)
    
    def _timeout_handler(self, signum: int, frame: Any) -> None:
        """
        Handle the timeout signal by raising a TimeoutError.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        
        Raises:
            TimeoutError: Always raised when the timeout handler is called
        """
        raise TimeoutError(self.timeout_message)


async def safe_api_request(
    client: httpx.AsyncClient, 
    method: str, 
    url: str, 
    max_retries: int = 3,
    retry_delay: float = 1.5,
    **kwargs: Any
) -> Dict[str, Any]:
    """
    Make a safe API request with retries and error handling.
    
    Attempts to make the request multiple times before giving up, with
    exponential backoff between retries. Handles common HTTP errors and
    timeouts appropriately.
    
    Args:
        client: The HTTPX client to use for the request
        method: HTTP method (GET, POST, etc.)
        url: URL to request
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries (with exponential backoff)
        **kwargs: Additional arguments to pass to the client request method
    
    Returns:
        Dict[str, Any]: Response data as a dictionary
    
    Raises:
        httpx.HTTPError: If the request fails after all retries
    """
    attempt = 0
    last_error = None
    
    while attempt < max_retries:
        try:
            # Add jitter to avoid thundering herd issues
            if attempt > 0:
                delay = retry_delay * (2 ** (attempt - 1)) * (0.5 + random.random())
                logger.info(f"Retry attempt {attempt} for {url}. Waiting {delay:.2f}s")
                await client.timeout(delay)
            
            # Make the request
            logger.debug(f"Making {method} request to {url}")
            request_method = getattr(client, method.lower())
            response = await request_method(url, **kwargs)
            response.raise_for_status()
            
            # Return successful response as dictionary
            return response.json()
            
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            logger.warning(f"HTTP error {status_code} for {url}: {e}")
            
            # Handle specific status codes differently
            if status_code == 429 or (500 <= status_code < 600):
                # These are retryable errors
                last_error = e
                attempt += 1
            else:
                # Client errors are not retryable
                raise
                
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
            logger.warning(f"Connection/timeout error for {url}: {e}")
            last_error = e
            attempt += 1
            
        except Exception as e:
            logger.error(f"Unexpected error during API request to {url}: {e}")
            last_error = e
            raise
    
    # If we've exhausted retries, raise the last error
    logger.error(f"Failed after {max_retries} attempts to {url}")
    if last_error:
        raise last_error
    
    # This should never happen, but just in case
    raise httpx.RequestError("Request failed for unknown reasons") 