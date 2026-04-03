"""
Postal Code Lookup Class

This module provides the main PostalLookup class for performing postal code lookups
using multiple geocoding services with comprehensive error handling.
"""

import logging
import requests
from typing import Optional, Dict, Any

from .exceptions import (
    PostalLookupError,
    NetworkError,
    RateLimitError,
    APIResponseError,
)
from .country_codes import normalize_country_code


class PostalLookup:
    """
    Main class for postal code location lookups.
    
    This class provides methods to look up city, state/province, and coordinates
    from postal codes using multiple geocoding services with comprehensive error handling.
    
    Attributes:
        timeout (float): Default timeout for requests in seconds
        user_agent (str): Default user agent for HTTP requests
        logger (logging.Logger): Logger instance for debugging
        
    Example:
        >>> lookup = PostalLookup()
        >>> result = lookup.lookup("N6A 3K7", "CA")
        >>> print(result['city'])  # 'London'
        >>> print(result['country'])  # 'Canada'
        
    Advanced Usage:
        >>> import logging
        >>> logger = logging.getLogger(__name__)
        >>> lookup = PostalLookup(timeout=15.0, logger=logger)
        >>> result = lookup.lookup("90210", "US")
    """
    
    def __init__(
        self,
        *,
        timeout: float = 10.0,
        user_agent: str = "postal-lookup/1.0 (contact: me@peternearing.ca.)",
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize PostalLookup instance.
        
        Args:
            timeout: Default timeout for requests in seconds (default: 10.0)
            user_agent: Default user agent for HTTP requests
            logger: Optional logger instance for debugging
        """
        self.timeout = timeout
        self.user_agent = user_agent
        self.logger = logger or logging.getLogger(__name__)
        
        # Set up default logging - can be overridden by importing package
        if not self.logger.handlers:
            self.logger.addHandler(logging.NullHandler())
    
    def lookup(
        self,
        postal_code: str,
        country_code: str,
        *,
        timeout: Optional[float] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Look up city and province/state from a postal code + country code.
        
        This method attempts to find location information using multiple API services
        in a fallback chain. It first tries Zippopotam.us (fast, lightweight),
        and if that fails, falls back to Nominatim OpenStreetMap 
        (comprehensive but slower).
        
        The country_code parameter accepts flexible input:
        - 2-letter ISO codes (e.g., "US", "CA")
        - 3-letter ISO codes (e.g., "USA", "CAN")  
        - Numeric codes (e.g., "840", "124")
        - Full country names (e.g., "United States", "Canada")
        
        All country code formats are case-insensitive and will be normalized
        to the standard 2-letter ISO code automatically.
        
        Error Handling Strategy:
        - Network errors, rate limits, and API errors from the primary service
          trigger fallback to the secondary service
        - Only when both services fail or return no results does the method return None
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
            country_code: Country code (2-letter, 3-letter, numeric, or full name)
            timeout: Optional timeout override for this request
            user_agent: Optional user agent override for this request
            
        Returns:
            Dictionary with location data or None if not found
            
        Raises:
            ValueError: If input parameters are invalid
            NetworkError: Network connectivity issues
            RateLimitError: API rate limiting (HTTP 429 or 403)
            APIResponseError: Invalid API responses
            
        Notes:
            - This is best-effort only. Postal codes are not globally uniform.
            - Some postal codes may map to multiple localities.
            - Network and API errors from the primary service trigger fallback attempts
            - Only returns None when both services cannot find the postal code
        """
        # Use instance defaults or method overrides
        request_timeout = timeout if timeout is not None else self.timeout
        request_user_agent = user_agent if user_agent is not None else self.user_agent
        
        self.logger.debug(
            f"Starting postal code lookup for: '{postal_code}', country: '{country_code}'"
        )
        
        # Validate input parameters
        if not postal_code or not isinstance(postal_code, str):
            self.logger.error(f"Invalid postal_code: {postal_code}")
            raise ValueError("postal_code must be a non-empty string")
        if not country_code or not isinstance(country_code, str):
            self.logger.error(f"Invalid country_code: {country_code}")
            raise ValueError("country_code must be a non-empty string")

        # Normalize country code to 2-letter ISO format
        normalized_country = normalize_country_code(country_code)
        if normalized_country is None:
            self.logger.error(f"Invalid country_code: {country_code}")
            raise ValueError(
                f"country_code '{country_code}' is not a valid country code. "
                "Accepts 2-letter (US), 3-letter (USA), numeric (840), or full name (United States)."
            )

        # Normalize postal code
        postal_code = postal_code.strip()
        country_code = normalized_country
        
        self.logger.debug(
            f"Normalized inputs - postal_code: '{postal_code}', country_code: '{country_code}'"
        )

        # Create session for this request
        session = requests.Session()
        session.headers.update({
            "User-Agent": request_user_agent,
            "Accept": "application/json",
        })
        
        self.logger.debug(f"Created session with headers: {session.headers}")

        # 1) Try Zippopotam.us first
        self.logger.debug("Attempting Zippopotam.us lookup...")
        try:
            z_result = self._lookup_zippopotam(session, postal_code, country_code, request_timeout)
            if z_result is not None:
                self.logger.info(f"Zippopotam.us lookup successful: {z_result}")
                return z_result
            else:
                self.logger.debug("Zippopotam.us lookup failed, trying Nominatim...")
        except PostalLookupError:
            # Any error from Zippopotam.us, try Nominatim as fallback
            self.logger.debug("Zippopotam.us lookup failed with error, trying Nominatim...")

        # 2) Fall back to Nominatim
        try:
            n_result = self._lookup_nominatim(session, postal_code, country_code, request_timeout)
            if n_result is not None:
                self.logger.info(f"Nominatim lookup successful: {n_result}")
                return n_result
            else:
                self.logger.debug("Nominatim lookup failed")
        except PostalLookupError:
            # Any error from Nominatim, we're out of options
            self.logger.debug("Nominatim lookup failed with error")

        self.logger.warning(
            f"No location found for postal code '{postal_code}' in country '{country_code}'"
        )
        return None
    
    def _lookup_zippopotam(
        self,
        session: requests.Session,
        postal_code: str,
        country_code: str,
        timeout: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Lookup postal code using Zippopotam.us API.
        
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
            
        Returns:
            Dictionary with location data or None if not found
            
        Raises:
            NetworkError: If network connectivity issues occur
            RateLimitError: If API rate limits are exceeded
            APIResponseError: If API returns invalid responses or server errors
        """
        url = f"https://api.zippopotam.us/{country_code.upper()}/{postal_code[:3]}"
        self.logger.debug(f"Zippopotam.us URL: {url}")

        try:
            self.logger.debug(f"Making GET request to Zippopotam.us with timeout {timeout}s")
            resp = session.get(url, timeout=timeout)
            self.logger.debug(f"Zippopotam.us response status: {resp.status_code}")
            
            if resp.status_code == 404:
                self.logger.debug(f"Zippopotam.us: Postal code '{postal_code}' not found (404)")
                return None
            elif resp.status_code == 429:
                self.logger.error(f"Zippopotam.us: Rate limit exceeded (429)")
                raise RateLimitError(f"Rate limit exceeded for Zippopotam.us API")
            elif resp.status_code == 403:
                self.logger.error(f"Zippopotam.us: Access forbidden (403) - likely rate limiting")
                raise RateLimitError(f"Access forbidden for Zippopotam.us API - likely rate limiting")
            elif resp.status_code >= 500:
                self.logger.error(f"Zippopotam.us: Server error {resp.status_code}")
                raise APIResponseError(f"Zippopotam.us server error: {resp.status_code}")
            
            resp.raise_for_status()
            
            try:
                data = resp.json()
            except ValueError as e:
                self.logger.error(f"Zippopotam.us: Invalid JSON response: {e}")
                raise APIResponseError(f"Invalid JSON response from Zippopotam.us: {e}")
                
            self.logger.debug(f"Zippopotam.us response data: {data}")
        except requests.exceptions.Timeout as e:
            self.logger.error(f"Zippopotam.us: Request timeout after {timeout}s: {e}")
            raise NetworkError(f"Request timeout to Zippopotam.us: {e}")
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Zippopotam.us: Connection error: {e}")
            raise NetworkError(f"Connection error to Zippopotam.us: {e}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Zippopotam.us: Network request failed: {e}")
            raise NetworkError(f"Network error accessing Zippopotam.us: {e}")

        places = data.get("places") or []
        self.logger.debug(f"Found {len(places)} places in Zippopotam.us response")
        
        if not places:
            self.logger.debug("Zippopotam.us: No places found in response")
            return None

        place = places[0]
        self.logger.debug(f"Using first place: {place}")

        # Extract city name from various possible field names
        city = (
            place.get("place name")
            or place.get("place_name")
            or place.get("city")
        )
        self.logger.debug(f"Extracted city: '{city}'")

        # Extract state/province from various possible field names
        state_province = (
            place.get("state")
            or place.get("province")
            or place.get("state name")
            or place.get("state_name")
        )
        self.logger.debug(f"Extracted state_province: '{state_province}'")

        # Convert coordinates to floats safely
        lat = self._safe_float(place.get("latitude"))
        lon = self._safe_float(place.get("longitude"))
        self.logger.debug(f"Extracted coordinates: lat={lat}, lon={lon}")

        result = {
            "postal_code": postal_code,  # Don't override with Zippopotam.us data
            "country_code": (data.get("country abbreviation") or country_code).upper(),
            "country": data.get("country"),
            "city": city,
            "state_province": state_province,
            "latitude": lat,
            "longitude": lon,
            "source": "zippopotam",
        }
        self.logger.debug(f"Zippopotam.us result: {result}")
        return result
    
    def _lookup_nominatim(
        self,
        session: requests.Session,
        postal_code: str,
        country_code: str,
        timeout: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Lookup postal code using Nominatim OpenStreetMap API.
        
        Nominatim is used as a fallback service when Zippopotam.us fails.
        It provides comprehensive global coverage but is rate limited and slower.
        
        This method uses structured search parameters to ensure accurate results
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
            
        Returns:
            Dictionary with location data or None if not found
            
        Raises:
            NetworkError: If network connectivity issues occur
            RateLimitError: If API rate limits are exceeded
            APIResponseError: If API returns invalid responses or server errors
            
        Note:
            Nominatim has a usage policy that recommends no more than 1 request
            per second. This method should be called with appropriate rate limiting
            when used in bulk operations. Nominatim also uses HTTP 403
            Forbidden for rate limiting in addition to HTTP 429.
        """
        # Use structured search so we are not guessing at string parsing
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "postalcode": postal_code,
            "country": country_code,
            "countrycodes": country_code.lower(),
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": 1,
        }
        
        self.logger.debug(f"Nominatim URL: {url}")
        self.logger.debug(f"Nominatim params: {params}")

        try:
            self.logger.debug(f"Making GET request to Nominatim with timeout {timeout}s")
            resp = session.get(url, params=params, timeout=timeout)
            self.logger.debug(f"Nominatim response status: {resp.status_code}")
            
            if resp.status_code == 404:
                self.logger.debug(f"Nominatim: Postal code '{postal_code}' not found (404)")
                return None
            elif resp.status_code == 429:
                self.logger.error(f"Nominatim: Rate limit exceeded (429)")
                raise RateLimitError(f"Rate limit exceeded for Nominatim API")
            elif resp.status_code == 403:
                self.logger.error(f"Nominatim: Access forbidden (403) - likely rate limiting")
                raise RateLimitError(f"Access forbidden for Nominatim API - likely rate limiting")
            elif resp.status_code >= 500:
                self.logger.error(f"Nominatim: Server error {resp.status_code}")
                raise APIResponseError(f"Nominatim server error: {resp.status_code}")
            
            resp.raise_for_status()
            
            try:
                results = resp.json()
            except ValueError as e:
                self.logger.error(f"Nominatim: Invalid JSON response: {e}")
                raise APIResponseError(f"Invalid JSON response from Nominatim: {e}")
                
            self.logger.debug(f"Nominatim response data: {results}")
        except requests.exceptions.Timeout as e:
            self.logger.error(f"Nominatim: Request timeout after {timeout}s: {e}")
            raise NetworkError(f"Request timeout to Nominatim: {e}")
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Nominatim: Connection error: {e}")
            raise NetworkError(f"Connection error to Nominatim: {e}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Nominatim: Network request failed: {e}")
            raise NetworkError(f"Network error accessing Nominatim: {e}")

        if not results:
            self.logger.debug("Nominatim: No results found")
            return None

        result = results[0]
        address = result.get("address", {})
        self.logger.debug(f"Using first result: {result}")
        self.logger.debug(f"Address details: {address}")

        # Extract city name from various possible field names in address hierarchy
        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
            or address.get("hamlet")
            or address.get("county")
        )
        self.logger.debug(f"Extracted city: '{city}'")

        # Extract state/province from various possible field names
        state_province = (
            address.get("state")
            or address.get("province")
            or address.get("region")
            or address.get("state_district")
        )
        self.logger.debug(f"Extracted state_province: '{state_province}'")

        result = {
            "postal_code": address.get("postcode", postal_code),
            "country_code": address.get("country_code", country_code.lower()).upper(),
            "country": address.get("country"),
            "city": city,
            "state_province": state_province,
            "latitude": self._safe_float(result.get("lat")),
            "longitude": self._safe_float(result.get("lon")),
            "source": "nominatim",
        }
        self.logger.debug(f"Nominatim result: {result}")
        return result
    
    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """
        Safely convert value to float, returning None on failure.
        
        This helper method handles the common case of converting coordinate
        strings from API responses to float values. It gracefully handles
        None values, empty strings, and malformed numbers.
        
        Args:
            value: Value to convert (typically string or None)
            
        Returns:
            Float value if conversion succeeds, None otherwise
            
        Examples:
            >>> PostalLookup._safe_float("42.98")
            42.98
            >>> PostalLookup._safe_float("-81.25")
            -81.25
            >>> PostalLookup._safe_float(None)
            None
            >>> PostalLookup._safe_float("invalid")
            None
        """
        try:
            result = float(value)
            return result
        except (TypeError, ValueError):
            return None
