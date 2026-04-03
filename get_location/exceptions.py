"""
Exception classes for postal code lookup module.

This module defines the exception hierarchy used throughout the get_location package.
All exceptions inherit from PostalLookupError for consistent error handling.
"""


class PostalLookupError(Exception):
    """Base exception class for postal code lookup errors.
    
    This is the base class for all exceptions raised by this package.
    It can be used to catch any postal lookup related error.
    
    Example:
        >>> try:
        ...     lookup.lookup("invalid", "US")
        ... except PostalLookupError as e:
        ...     print(f"Lookup failed: {e}")
    """
    pass


class NetworkError(PostalLookupError):
    """Raised when network connectivity issues occur.
    
    This exception is raised for problems such as:
    - Connection timeouts
    - DNS resolution failures
    - Connection refused errors
    - Other network-level issues
    
    Example:
        >>> try:
        ...     lookup.lookup("90210", "US", timeout=0.001)
        ... except NetworkError as e:
        ...     print(f"Network problem: {e}")
    """
    pass


class RateLimitError(PostalLookupError):
    """Raised when API rate limits are exceeded.
    
    This exception is raised when an API service returns HTTP 429
    (Too Many Requests), HTTP 403 (Forbidden), or similar rate limiting responses.
    
    Many APIs use 403 Forbidden as a rate limiting mechanism
    in addition to the more standard 429 Too Many Requests.
    
    Example:
        >>> try:
        ...     lookup_city_region_by_postal_code("90210", "US")
        ... except RateLimitError as e:
        ...     time.sleep(1)  # Wait before retry
        ...     # Retry request
        ...     print(f"Rate limited: {e}")
    """
    pass


class APIResponseError(PostalLookupError):
    """Raised when API services return unexpected or invalid responses.
    
    This exception is raised for problems such as:
    - Server errors (HTTP 5xx)
    - Invalid JSON responses
    - Malformed or incomplete API data
    - Unexpected response formats
    
    Example:
        >>> try:
        ...     lookup.lookup("90210", "US")
        ... except APIResponseError as e:
        ...     print(f"API problem: {e}")
    """
    pass
