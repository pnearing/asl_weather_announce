"""
Postal Code Location Lookup Package

This package provides functionality to look up city, state/province, and coordinates
from postal codes using multiple geocoding services with comprehensive error handling.

Classes:
    PostalLookup: Main class for postal code lookups

Exceptions:
    PostalLookupError: Base exception for all postal lookup errors
    NetworkError: Network connectivity issues
    RateLimitError: API rate limiting
    APIResponseError: Invalid API responses

Example Usage:
    >>> from get_location import PostalLookup, NetworkError
    >>> lookup = PostalLookup()
    >>> try:
    ...     result = lookup.lookup("N6A 3K7", "CA")
    ...     print(result['city'])  # 'London'
    ... except NetworkError as e:
    ...     print(f"Network issue: {e}")
"""

from .postal_lookup import PostalLookup
from .exceptions import (
    PostalLookupError,
    NetworkError,
    RateLimitError,
    APIResponseError,
)

__all__ = [
    'PostalLookup',           # Main lookup class
    'PostalLookupError',       # Base exception class
    'NetworkError',           # Network connectivity issues
    'RateLimitError',         # API rate limiting
    'APIResponseError',       # Invalid API responses
]
