"""
Exception classes for weather lookup module.

This module defines the exception hierarchy used throughout the get_weather package.
All exceptions inherit from WeatherLookupError for consistent error handling.
"""
__version__ = "1.0.0"
__author__ = "Peter Nearing"
__email__ = "me@peternearing.ca"


class WeatherLookupError(Exception):
    """Base exception class for weather lookup errors.
    
    This is the base class for all exceptions raised by this package.
    It can be used to catch any weather lookup related error.
    
    Example:
        >>> try:
        ...     get_current_weather(...)
        ... except WeatherLookupError as e:
        ...     print(f"Weather lookup failed: {e}")
    """
    pass


class NetworkError(WeatherLookupError):
    """Raised when network connectivity issues occur.
    
    This exception is raised for problems such as:
    - Connection timeouts
    - DNS resolution failures
    - Connection refused errors
    - Other network-level issues
    
    Example:
        >>> try:
        ...     get_current_weather(..., timeout=0.001)
        ... except NetworkError as e:
        ...     print(f"Network problem: {e}")
    """
    pass


class RateLimitError(WeatherLookupError):
    """Raised when API rate limits are exceeded.
    
    This exception is raised when an API service returns HTTP 429
    (Too Many Requests), HTTP 403 (Forbidden), or similar rate limiting responses.
    
    Many APIs use 403 Forbidden as a rate limiting mechanism
    in addition to the more standard 429 Too Many Requests.
    
    Example:
        >>> try:
        ...     get_current_weather(...)
        ... except RateLimitError as e:
        ...     time.sleep(1)  # Wait before retry
        ...     # Retry request
        ...     print(f"Rate limited: {e}")
    """
    pass


class APIResponseError(WeatherLookupError):
    """Raised when API services return unexpected or invalid responses.
    
    This exception is raised for problems such as:
    - Server errors (HTTP 5xx)
    - Invalid JSON responses
    - Malformed or incomplete API data
    - Unexpected response formats
    
    Example:
        >>> try:
        ...     get_current_weather(...)
        ... except APIResponseError as e:
        ...     print(f"API problem: {e}")
    """
    pass


class InvalidLocationError(WeatherLookupError):
    """Raised when location coordinates are invalid or out of range.
    
    This exception is raised for problems such as:
    - Invalid latitude/longitude values
    - Coordinates outside valid ranges
    - Missing coordinate data
    
    Example:
        >>> try:
        ...     get_current_weather(..., latitude=999, longitude=999)
        ... except InvalidLocationError as e:
        ...     print(f"Invalid location: {e}")
    """
    pass
