"""
Postal Code Location Lookup Package

This package provides functionality to look up city, state/province, and coordinates
from postal codes using multiple geocoding services with comprehensive error handling.

Classes:
    PostalLookup: Main class for postal code lookups
    CountryCodeNormalizer: Normalizes various country code formats to 2-letter codes

Functions:
    normalize_country_code: Convenience function to normalize a country code
    is_valid_country_code: Convenience function to validate a country code

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
    
Country Code Examples:
    >>> from get_location import normalize_country_code
    >>> normalize_country_code("USA")  # Returns 'US'
    >>> normalize_country_code("canada")  # Returns 'CA'
    >>> normalize_country_code("840")  # Returns 'US'
    >>> normalize_country_code("United States")  # Returns 'US'
"""

from .postal_lookup import PostalLookup
from .country_codes import (
    CountryCodeNormalizer,
    normalize_country_code,
    is_valid_country_code,
)
from .exceptions import (
    PostalLookupError,
    NetworkError,
    RateLimitError,
    APIResponseError,
)

__all__ = [
    'PostalLookup',           # Main lookup class
    'CountryCodeNormalizer',   # Country code normalizer class
    'normalize_country_code',  # Convenience function
    'is_valid_country_code',   # Validation function
    'PostalLookupError',       # Base exception class
    'NetworkError',           # Network connectivity issues
    'RateLimitError',         # API rate limiting
    'APIResponseError',       # Invalid API responses
]
