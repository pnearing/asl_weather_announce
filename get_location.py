"""
Postal Code Location Lookup Module

This module provides functionality to look up city, state/province, and coordinates
from postal codes using multiple geocoding services with comprehensive error handling.

Features:
- Supports postal codes from multiple countries (US, Canada, UK, Germany, etc.)
- Uses Zippopotam.us API as primary source (fast, lightweight)
- Falls back to Nominatim OpenStreetMap API for broader coverage
- Returns structured location data with coordinates
- Comprehensive logging for debugging
- Thread-safe session management
- Detailed exception handling for different error types

Error Handling:
The module provides specific exception types for different error conditions:
- NetworkError: Network connectivity issues (timeouts, connection errors)
- RateLimitError: API rate limiting (HTTP 429 responses)
- APIResponseError: Invalid API responses (server errors, malformed JSON)
- PostalLookupError: Base class for all postal lookup errors

Example Usage:
    >>> from get_location import lookup_city_region_by_postal_code, NetworkError
    >>> try:
    ...     result = lookup_city_region_by_postal_code("N6A 3K7", "CA")
    ...     print(result['city'])  # 'London'
    ...     print(result['country'])  # 'Canada'
    ... except NetworkError as e:
    ...     print(f"Network issue: {e}")

API Services Used:
1. Zippopotam.us (https://api.zippopotam.us/)
   - Fast, lightweight postal code API
   - Limited to first 3 characters for some postal codes
   - No rate limiting

2. Nominatim OpenStreetMap (https://nominatim.openstreetmap.org/)
   - Comprehensive global coverage
   - Rate limited (1 request/second recommended)
   - Full postal code support

Author: Based on work by Peter Nearing
License: See project license
"""

from __future__ import annotations

import requests
import logging
from typing import Optional, Dict, Any


# Set up default logging - can be overridden by importing module
logging.getLogger(__name__).addHandler(logging.NullHandler())


class PostalLookupError(Exception):
    """Base exception class for postal code lookup errors.
    
    This is the base class for all exceptions raised by this module.
    It can be used to catch any postal lookup related error.
    
    Example:
        >>> try:
        ...     lookup_city_region_by_postal_code("invalid", "US")
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
        ...     lookup_city_region_by_postal_code("90210", "US", timeout=0.001)
        ... except NetworkError as e:
        ...     print(f"Network problem: {e}")
    """
    pass


class RateLimitError(PostalLookupError):
    """Raised when API rate limits are exceeded.
    
    This exception is raised when an API service returns HTTP 429
    (Too Many Requests) or similar rate limiting responses.
    
    Example:
        >>> try:
        ...     lookup_city_region_by_postal_code("90210", "US")
        ... except RateLimitError as e:
        ...     time.sleep(1)  # Wait before retry
        ...     # Retry the request
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
        ...     lookup_city_region_by_postal_code("90210", "US")
        ... except APIResponseError as e:
        ...     print(f"API problem: {e}")
    """
    pass


def _lookup_zippopotam(
    session: requests.Session,
    postal_code: str,
    country_code: str,
    timeout: float,
    logger: logging.Logger,
) -> Optional[Dict[str, Any]]:
    """Lookup postal code using Zippopotam.us API.
    
    Zippopotam.us is a fast, lightweight API that provides basic postal code
    information. It's used as the primary lookup service due to its speed and
    reliability.
    
    Note: Zippopotam.us may only use the first 3 characters of some postal codes
    (like Canadian FSA format), so the returned postal_code field uses the original
    input rather than the API response.
    
    Error Handling:
    - NetworkError: Raised for timeouts, connection errors, and other network issues
    - RateLimitError: Raised when API returns HTTP 429 (rate limiting)
    - APIResponseError: Raised for server errors (HTTP 5xx) or invalid JSON
    
    Args:
        session: Requests session for HTTP calls
        postal_code: Full postal code to lookup
        country_code: 2-letter ISO country code (uppercase)
        timeout: Request timeout in seconds
        logger: Logger instance for debugging
        
    Returns:
        Dictionary with location data or None if not found:
        {
            "postal_code": "original_input",
            "country_code": "CA",
            "country": "Canada",
            "city": "London",
            "state_province": "Ontario",
            "latitude": 42.98,
            "longitude": -81.25,
            "source": "zippopotam"
        }
        
    Raises:
        NetworkError: If network connectivity issues occur
        RateLimitError: If API rate limits are exceeded
        APIResponseError: If API returns invalid responses or server errors
    """
    url = f"https://api.zippopotam.us/{country_code.upper()}/{postal_code[:3]}"
    logger.debug(f"Zippopotam.us URL: {url}")

    try:
        logger.debug(f"Making GET request to Zippopotam.us with timeout {timeout}s")
        resp = session.get(url, timeout=timeout)
        logger.debug(f"Zippopotam.us response status: {resp.status_code}")
        
        if resp.status_code == 404:
            logger.debug(f"Zippopotam.us: Postal code '{postal_code}' not found (404)")
            return None
        elif resp.status_code == 429:
            logger.error(f"Zippopotam.us: Rate limit exceeded (429)")
            raise RateLimitError(f"Rate limit exceeded for Zippopotam.us API")
        elif resp.status_code >= 500:
            logger.error(f"Zippopotam.us: Server error {resp.status_code}")
            raise APIResponseError(f"Zippopotam.us server error: {resp.status_code}")
        
        resp.raise_for_status()
        
        try:
            data = resp.json()
        except ValueError as e:
            logger.error(f"Zippopotam.us: Invalid JSON response: {e}")
            raise APIResponseError(f"Invalid JSON response from Zippopotam.us: {e}")
            
        logger.debug(f"Zippopotam.us response data: {data}")
    except requests.exceptions.Timeout as e:
        logger.error(f"Zippopotam.us: Request timeout after {timeout}s: {e}")
        raise NetworkError(f"Request timeout to Zippopotam.us: {e}")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Zippopotam.us: Connection error: {e}")
        raise NetworkError(f"Connection error to Zippopotam.us: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Zippopotam.us: Network request failed: {e}")
        raise NetworkError(f"Network error accessing Zippopotam.us: {e}")

    places = data.get("places") or []
    logger.debug(f"Found {len(places)} places in Zippopotam.us response")
    
    if not places:
        logger.debug("Zippopotam.us: No places found in response")
        return None

    place = places[0]
    logger.debug(f"Using first place: {place}")

    # Extract city name from various possible field names
    city = (
        place.get("place name")
        or place.get("place_name")
        or place.get("city")
    )
    logger.debug(f"Extracted city: '{city}'")

    # Extract state/province from various possible field names
    state_province = (
        place.get("state")
        or place.get("province")
        or place.get("state name")
        or place.get("state_name")
    )
    logger.debug(f"Extracted state_province: '{state_province}'")

    # Convert coordinates to floats safely
    lat = _safe_float(place.get("latitude"))
    lon = _safe_float(place.get("longitude"))
    logger.debug(f"Extracted coordinates: lat={lat}, lon={lon}")

    result = {
        "postal_code": postal_code,  # Don't override with Zippopotam.us data, because they only return the first 3 characters
        "country_code": (data.get("country abbreviation") or country_code).upper(),
        "country": data.get("country"),
        "city": city,
        "state_province": state_province,
        "latitude": lat,
        "longitude": lon,
        "source": "zippopotam",
    }
    logger.debug(f"Zippopotam.us result: {result}")
    return result


def _lookup_nominatim(
    session: requests.Session,
    postal_code: str,
    country_code: str,
    timeout: float,
    logger: logging.Logger,
) -> Optional[Dict[str, Any]]:
    """Lookup postal code using Nominatim OpenStreetMap API.
    
    Nominatim is used as a fallback service when Zippopotam.us fails.
    It provides comprehensive global coverage but is rate limited and slower.
    
    This function uses structured search parameters to ensure accurate results
    and avoid ambiguity in postal code parsing.
    
    Error Handling:
    - NetworkError: Raised for timeouts, connection errors, and other network issues
    - RateLimitError: Raised when API returns HTTP 429 (rate limiting)
    - APIResponseError: Raised for server errors (HTTP 5xx) or invalid JSON
    
    Args:
        session: Requests session for HTTP calls
        postal_code: Full postal code to lookup
        country_code: 2-letter ISO country code (uppercase)
        timeout: Request timeout in seconds
        logger: Logger instance for debugging
        
    Returns:
        Dictionary with location data or None if not found:
        {
            "postal_code": "N6A 3K7",
            "country_code": "CA",
            "country": "Canada",
            "city": "London",
            "state_province": "Ontario",
            "latitude": 42.98,
            "longitude": -81.25,
            "source": "nominatim"
        }
        
    Raises:
        NetworkError: If network connectivity issues occur
        RateLimitError: If API rate limits are exceeded
        APIResponseError: If API returns invalid responses or server errors
        
    Note:
        Nominatim has a usage policy that recommends no more than 1 request
        per second. This function should be called with appropriate rate limiting
        when used in bulk operations.
    """
    # Use structured search so we are not guessing at string parsing.
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "postalcode": postal_code,
        "country": country_code,
        "countrycodes": country_code.lower(),
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": 1,
    }
    
    logger.debug(f"Nominatim URL: {url}")
    logger.debug(f"Nominatim params: {params}")

    try:
        logger.debug(f"Making GET request to Nominatim with timeout {timeout}s")
        resp = session.get(url, params=params, timeout=timeout)
        logger.debug(f"Nominatim response status: {resp.status_code}")
        
        if resp.status_code == 404:
            logger.debug(f"Nominatim: Postal code '{postal_code}' not found (404)")
            return None
        elif resp.status_code == 429:
            logger.error(f"Nominatim: Rate limit exceeded (429)")
            raise RateLimitError(f"Rate limit exceeded for Nominatim API")
        elif resp.status_code >= 500:
            logger.error(f"Nominatim: Server error {resp.status_code}")
            raise APIResponseError(f"Nominatim server error: {resp.status_code}")
        
        resp.raise_for_status()
        
        try:
            results = resp.json()
        except ValueError as e:
            logger.error(f"Nominatim: Invalid JSON response: {e}")
            raise APIResponseError(f"Invalid JSON response from Nominatim: {e}")
            
        logger.debug(f"Nominatim response data: {results}")
    except requests.exceptions.Timeout as e:
        logger.error(f"Nominatim: Request timeout after {timeout}s: {e}")
        raise NetworkError(f"Request timeout to Nominatim: {e}")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Nominatim: Connection error: {e}")
        raise NetworkError(f"Connection error to Nominatim: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Nominatim: Network request failed: {e}")
        raise NetworkError(f"Network error accessing Nominatim: {e}")

    if not results:
        logger.debug("Nominatim: No results found")
        return None

    result = results[0]
    address = result.get("address", {})
    logger.debug(f"Using first result: {result}")
    logger.debug(f"Address details: {address}")

    # Extract city name from various possible field names in address hierarchy
    city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("municipality")
        or address.get("hamlet")
        or address.get("county")
    )
    logger.debug(f"Extracted city: '{city}'")

    # Extract state/province from various possible field names
    state_province = (
        address.get("state")
        or address.get("province")
        or address.get("region")
        or address.get("state_district")
    )
    logger.debug(f"Extracted state_province: '{state_province}'")

    result = {
        "postal_code": address.get("postcode", postal_code),
        "country_code": address.get("country_code", country_code.lower()).upper(),
        "country": address.get("country"),
        "city": city,
        "state_province": state_province,
        "latitude": _safe_float(result.get("lat")),
        "longitude": _safe_float(result.get("lon")),
        "source": "nominatim",
    }
    logger.debug(f"Nominatim result: {result}")
    return result


def _safe_float(value: Any) -> Optional[float]:
    """Safely convert value to float, returning None on failure.
    
    This helper function handles the common case of converting coordinate
    strings from API responses to float values. It gracefully handles
    None values, empty strings, and malformed numbers.
    
    Args:
        value: Value to convert (typically string or None)
        
    Returns:
        Float value if conversion succeeds, None otherwise
        
    Examples:
        >>> _safe_float("42.98")
        42.98
        >>> _safe_float("-81.25")
        -81.25
        >>> _safe_float(None)
        None
        >>> _safe_float("invalid")
        None
    """
    try:
        result = float(value)
        return result
    except (TypeError, ValueError):
        return None


# Module-level convenience functions
def lookup_postal_code(postal_code: str, country_code: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Convenience wrapper for lookup_city_region_by_postal_code.
    
    This function provides a shorter, more memorable name for the main
    lookup function. It passes all arguments through unchanged.
    
    The same error handling applies as the main function - specific
    exceptions are raised for different error conditions.
    
    Args:
        postal_code: Postal code to lookup
        country_code: 2-letter ISO country code
        **kwargs: Additional arguments passed to lookup_city_region_by_postal_code
        
    Returns:
        Same as lookup_city_region_by_postal_code
        
    Raises:
        NetworkError: Network connectivity issues
        RateLimitError: API rate limiting
        APIResponseError: Invalid API responses
        ValueError: Invalid input parameters
        
    Example:
        >>> from get_location import lookup_postal_code, NetworkError
        >>> try:
        ...     result = lookup_postal_code("90210", "US")
        ...     print(result['city'])
        ... except NetworkError as e:
        ...     print(f"Network issue: {e}")
    """
    return lookup_city_region_by_postal_code(postal_code, country_code, **kwargs)


# Exported symbols - defines the public API of this module
__all__ = [
    'lookup_city_region_by_postal_code',  # Main lookup function with fallback logic
    'lookup_postal_code',                 # Convenience wrapper function
    'PostalLookupError',                  # Base exception class for all lookup errors
    'NetworkError',                       # Network connectivity issues (timeouts, etc.)
    'RateLimitError',                     # API rate limiting (HTTP 429)
    'APIResponseError',                   # Invalid API responses (server errors, JSON)
]


def lookup_city_region_by_postal_code(
    postal_code: str,
    country_code: str,
    *,
    timeout: float = 10.0,
    user_agent: str = "postal-lookup/1.0 (contact: me@peternearing.ca.)",
    logger: Optional[logging.Logger] = None,
) -> Optional[Dict[str, Any]]:
    """Look up city and province/state from a postal code + 2-letter country code.

    This function attempts to find location information using multiple API services
    in a fallback chain. It first tries Zippopotam.us (fast, lightweight), and if
    that fails, falls back to Nominatim OpenStreetMap (comprehensive but slower).

    Error Handling Strategy:
    - Network errors, rate limits, and API errors from the primary service
      trigger fallback to the secondary service
    - Only when both services fail or return no results does the function return None
    - Specific exception types allow for granular error handling

    Returns a dict like:
    {
        "postal_code": "N6A 3K7",
        "country_code": "CA",
        "country": "Canada",
        "city": "London",
        "state_province": "Ontario",
        "latitude": 42.98,
        "longitude": -81.25,
        "source": "zippopotam"
    }

    Returns None if no match is found from either service.

    Args:
        postal_code: Postal code to lookup
        country_code: 2-letter ISO country code
        timeout: Request timeout in seconds (default: 10.0)
        user_agent: User agent string for HTTP requests
        logger: Optional logger instance for debugging

    Returns:
        Dictionary with location data or None if not found

    Raises:
        ValueError: If input parameters are invalid
        
    Notes:
        - This is best-effort only. Postal codes are not globally uniform.
        - Some postal codes may map to multiple localities.
        - Network and API errors from the primary service trigger fallback attempts
        - Only returns None when both services cannot find the postal code
    """
    
    # Use provided logger or create module logger
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.debug(f"Starting postal code lookup for: '{postal_code}', country: '{country_code}'")
    
    if not postal_code or not isinstance(postal_code, str):
        logger.error(f"Invalid postal_code: {postal_code}")
        raise ValueError("postal_code must be a non-empty string")
    if not country_code or not isinstance(country_code, str) or len(country_code.strip()) != 2:
        logger.error(f"Invalid country_code: {country_code}")
        raise ValueError("country_code must be a 2-letter ISO country code")

    postal_code = postal_code.strip()
    country_code = country_code.strip().upper()
    
    logger.debug(f"Normalized inputs - postal_code: '{postal_code}', country_code: '{country_code}'")

    session = requests.Session()
    session.headers.update({
        "User-Agent": user_agent,
        "Accept": "application/json",
    })
    
    logger.debug(f"Created session with headers: {session.headers}")

    # 1) Try Zippopotam.us first
    logger.debug("Attempting Zippopotam.us lookup...")
    try:
        z_result = _lookup_zippopotam(session, postal_code, country_code, timeout, logger)
        if z_result is not None:
            logger.info(f"Zippopotam.us lookup successful: {z_result}")
            return z_result
        else:
            logger.debug("Zippopotam.us lookup failed, trying Nominatim...")
    except PostalLookupError:
        # Any error from Zippopotam.us, try Nominatim as fallback
        logger.debug("Zippopotam.us lookup failed with error, trying Nominatim...")

    # 2) Fall back to Nominatim
    try:
        n_result = _lookup_nominatim(session, postal_code, country_code, timeout, logger)
        if n_result is not None:
            logger.info(f"Nominatim lookup successful: {n_result}")
            return n_result
        else:
            logger.debug("Nominatim lookup failed")
    except PostalLookupError:
        # Any error from Nominatim, we're out of options
        logger.debug("Nominatim lookup failed with error")

    logger.warning(f"No location found for postal code '{postal_code}' in country '{country_code}'")
    return None


if __name__ == "__main__":
    """Standalone execution for testing and demonstration.
    
    When this module is run directly, it performs a test lookup using
    a Canadian postal code and displays the results. This is useful for:
    
    - Quick testing of the module functionality
    - Verification that API services are accessible
    - Demonstration of expected output format
    
    The test uses verbose logging to show the lookup process step-by-step.
    """
    # Set up logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting get_location.py test with postal code 'N6A 3K7', country 'CA'")
    
    try:
        result = lookup_city_region_by_postal_code("N6A 3K7", "CA")
        logger.info(f"Final result: {result}")
        print(result)
    except NetworkError as e:
        logger.error(f"Network error during test: {e}")
        print(f"Network Error: {e}")
    except RateLimitError as e:
        logger.error(f"Rate limit error during test: {e}")
        print(f"Rate Limit Error: {e}")
    except APIResponseError as e:
        logger.error(f"API response error during test: {e}")
        print(f"API Response Error: {e}")
    except PostalLookupError as e:
        logger.error(f"Postal lookup error during test: {e}")
        print(f"Postal Lookup Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during test: {e}")
        print(f"Unexpected Error: {e}")