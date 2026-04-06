"""
Weather Lookup Module

This module provides functionality to fetch current weather conditions using the Open-Meteo API.
It includes comprehensive error handling, coordinate validation, and natural language formatting
for weather data suitable for text-to-speech applications.

The module uses the Open-Meteo weather API (https://api.open-meteo.com) which provides
free, unlimited access to current weather data without requiring API keys.

Key Features:
- Current weather conditions by latitude/longitude
- Support for both Celsius and Fahrenheit temperature units
- Comprehensive error handling with specific exception types
- Natural language weather descriptions optimized for TTS
- WMO weather code translation to human-readable descriptions

Example Usage:
    >>> from get_weather import get_current_weather
    >>> result = get_current_weather(
    ...     city="London",
    ...     state_province="Ontario", 
    ...     country="Canada",
    ...     latitude=42.98,
    ...     longitude=-81.25,
    ...     temperature_unit="C"
    ... )
    >>> print(result.natural_language())
    "Currently in London, Ontario it is 15 degrees Celsius with clear skies."

Error Handling:
    The module provides granular error handling with specific exception types:
    - NetworkError: Network connectivity issues
    - RateLimitError: API rate limiting
    - APIResponseError: Invalid API responses
    - InvalidLocationError: Invalid coordinates
    - WeatherLookupError: General weather lookup issues

Dependencies:
    - requests: HTTP client library
    - dataclasses: Data structure definitions
    - typing: Type hints

API Information:
    - Service: Open-Meteo Weather API
    - Endpoint: https://api.open-meteo.com/v1/forecast
    - Authentication: None (free public API)
    - Rate Limits: None specified (reasonable usage expected)
    - Data Source: European Centre for Medium-Range Weather Forecasts (ECMWF)
"""

from __future__ import annotations

__version__ = "1.0.2"
__author__ = "Peter Nearing"
__email__ = "me@peternearing.ca"

from dataclasses import dataclass
from typing import Optional, Literal, Dict, Any
import json
import os
import requests

# Import resilience patterns
try:
    from asl_weather_resilience import CircuitBreaker, APIMetrics, CircuitBreakerConfig
    HAS_RESILIENCE = True
except ImportError:
    HAS_RESILIENCE = False

try:
    from .exceptions import (
        NetworkError,
        RateLimitError,
        APIResponseError,
        InvalidLocationError,
    )
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from get_weather.exceptions import (
        NetworkError,
        RateLimitError,
        APIResponseError,
        InvalidLocationError,
    )

# Load weather code map from JSON file for easy translation/extension
_weather_code_map: Dict[str, str] = {}
_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_weather_code_file = os.path.join(_data_dir, "weather_code_map_en.json")
try:
    with open(_weather_code_file, "r", encoding="utf-8") as _f:
        _weather_code_map = json.load(_f)
except (FileNotFoundError, json.JSONDecodeError, OSError):
    # Fallback to empty dict; function will handle missing map gracefully
    _weather_code_map = {}


TemperatureUnit = Literal["C", "F"]


@dataclass
class CurrentWeatherResult:
    """
    Data class representing current weather conditions for a location.
    
    This class encapsulates all weather information returned by the Open-Meteo API
    and provides convenient methods for formatting the data for display or text-to-speech.
    
    Attributes:
        city: Human-readable city name for display purposes
        state_province: State or province name (optional)
        country: Country name (optional, used as fallback)
        latitude: Decimal latitude coordinate
        longitude: Decimal longitude coordinate
        temperature: Current temperature in the specified unit
        temperature_unit: Temperature unit ("C" for Celsius, "F" for Fahrenheit)
        weather_code: WMO weather code (optional, None if unavailable)
        weather_description: Natural language description of weather conditions
        is_day: Whether it's currently daytime (True/False/None if unknown)
        raw: Raw API response data for advanced usage
        
    Example:
        >>> result = CurrentWeatherResult(
        ...     city="London",
        ...     state_province="Ontario",
        ...     country="Canada",
        ...     latitude=42.98,
        ...     longitude=-81.25,
        ...     temperature=15.0,
        ...     temperature_unit="C",
        ...     weather_code=0,
        ...     weather_description="with clear skies",
        ...     is_day=True,
        ...     raw={}
        ... )
    """
    city: str
    state_province: Optional[str]
    country: Optional[str]
    latitude: float
    longitude: float
    temperature: float
    temperature_unit: TemperatureUnit
    weather_code: Optional[int]
    weather_description: str
    is_day: Optional[bool]
    raw: Dict[str, Any]


def get_current_weather(
    *,
    city: str,
    state_province: Optional[str],
    country: Optional[str],
    latitude: float,
    longitude: float,
    temperature_unit: TemperatureUnit = "C",
    timeout: float = 10.0,
    user_agent: str = f"weather-module/{__version__} (contact: {__author__} [<{__email__}>])",
    use_resilience: bool = True,
    logger: Optional[Any] = None,
) -> CurrentWeatherResult:
    """
    Fetch current weather conditions using latitude/longitude.

    Parameters:
        city: Human-readable city name for output text.
        state_province: State or province name for output text.
        country: Country name for output text fallback.
        latitude: Decimal latitude.
        longitude: Decimal longitude.
        temperature_unit: "C" or "F".
        timeout: HTTP timeout in seconds.
        user_agent: User-Agent header for HTTP requests.
        use_resilience: Whether to enable circuit breaker, caching, and metrics.
        logger: Optional logger instance.

    Returns:
        CurrentWeatherResult

    Raises:
        ValueError: bad arguments
        NetworkError: network connectivity issues
        RateLimitError: API rate limiting
        APIResponseError: invalid API responses
        InvalidLocationError: invalid coordinates
        WeatherLookupError: general weather lookup issues
    """
    if not city or not isinstance(city, str):
        raise ValueError("city must be a non-empty string")

    if temperature_unit not in ("C", "F"):
        raise ValueError('temperature_unit must be "C" or "F"')

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError) as exc:
        raise InvalidLocationError("latitude and longitude must be numeric") from exc
    
    # Validate coordinate ranges
    if not (-90 <= latitude <= 90):
        raise InvalidLocationError(f"latitude {latitude} is out of valid range [-90, 90]")
    if not (-180 <= longitude <= 180):
        raise InvalidLocationError(f"longitude {longitude} is out of valid range [-180, 180]")

    # Initialize resilience components if enabled
    circuit_breaker = None
    metrics = None
    if use_resilience and HAS_RESILIENCE:
        circuit_breaker = CircuitBreaker(
            name="open-meteo",
            config=CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60),
            logger_instance=logger,
        )
        metrics = APIMetrics()

    api_temp_unit = "celsius" if temperature_unit == "C" else "fahrenheit"

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        # Open-Meteo supports current weather variables directly.
        "current": "temperature_2m,weather_code,is_day",
        "temperature_unit": api_temp_unit,
    }

    session = requests.Session()
    session.headers.update({
        "User-Agent": user_agent,
        "Accept": "application/json",
    })

    def _fetch_weather():
        try:
            response = session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.Timeout as exc:
            raise NetworkError(f"Weather API request timeout after {timeout}s: {exc}") from exc
        except requests.exceptions.ConnectionError as exc:
            raise NetworkError(f"Weather API connection error: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            if hasattr(exc, 'response') and exc.response is not None:
                if exc.response.status_code == 429:
                    raise RateLimitError(f"Weather API rate limit exceeded: {exc}") from exc
                elif exc.response.status_code == 403:
                    raise RateLimitError(f"Weather API access forbidden - likely rate limiting: {exc}") from exc
                elif exc.response.status_code >= 500:
                    raise APIResponseError(f"Weather API server error {exc.response.status_code}: {exc}") from exc
            raise NetworkError(f"Weather API request failed: {exc}") from exc
        except ValueError as exc:
            raise APIResponseError(f"Weather API returned invalid JSON: {exc}") from exc

        current = data.get("current")
        if not isinstance(current, dict):
            raise APIResponseError("Weather API response is missing 'current' data")

        temp = current.get("temperature_2m")
        if temp is None:
            raise APIResponseError("Weather API response is missing temperature_2m")

        weather_code = current.get("weather_code")
        is_day_raw = current.get("is_day")
        is_day = bool(is_day_raw) if is_day_raw is not None else None

        description = weather_code_to_description(weather_code, is_day=is_day)

        return CurrentWeatherResult(
            city=city.strip(),
            state_province=(state_province.strip() if state_province else None),
            country=(country.strip() if country else None),
            latitude=latitude,
            longitude=longitude,
            temperature=float(temp),
            temperature_unit=temperature_unit,
            weather_code=int(weather_code) if weather_code is not None else None,
            weather_description=description,
            is_day=is_day,
            raw=data,
        )

    # Execute with circuit breaker and metrics if enabled
    try:
        if circuit_breaker and metrics:
            with metrics.measure("open-meteo", "forecast"):
                return circuit_breaker.call(_fetch_weather)
        else:
            return _fetch_weather()
    except Exception:
        # Re-raise all exceptions (circuit breaker open, network errors, etc.)
        raise


def weather_code_to_description(
    weather_code: Optional[int],
    *,
    is_day: Optional[bool] = None,
) -> str:
    """
    Convert Open-Meteo/WMO weather code to a natural-language description.
    
    Translates World Meteorological Organization (WMO) weather codes into
    human-readable weather descriptions optimized for text-to-speech applications.
    The descriptions are loaded from a JSON file to enable easy translation
    and extension for different locales.
    
    The WMO weather code system is a standardized way to represent weather
    conditions used by meteorological services worldwide. The codes range
    from 0-99 and cover various precipitation types, cloud cover, and
    atmospheric conditions.
    
    Args:
        weather_code: WMO weather code (0-99) or None if unavailable
        is_day: Whether it's currently daytime (not currently used, but
               reserved for future day/night-specific descriptions)
               
    Returns:
        Natural language weather description string
        
    Examples:
        >>> weather_code_to_description(0)
        'clear skies'
        >>> weather_code_to_description(63)
        'moderate rain'
        >>> weather_code_to_description(95)
        'thunderstorm'
        >>> weather_code_to_description(None)
        'weather conditions are unavailable'
        >>> weather_code_to_description(999)  # Invalid code
        'weather conditions are unrecognized'
        
    WMO Code Categories:
        0-3: Cloud cover (clear to overcast)
        45, 48: Fog
        51-55: Drizzle (light to dense)
        56, 57: Freezing drizzle
        61-65: Rain (light to heavy)
        66, 67: Freezing rain
        71-75: Snow (light to heavy)
        77: Snow grains
        80-82: Rain showers (light to violent)
        85, 86: Snow showers (light to heavy)
        95-99: Thunderstorm (with/without hail)
        
    Note:
        The is_day parameter is currently unused but maintained for compatibility
        with the Open-Meteo API which provides this information. Future versions
        may use this to provide day/night-specific descriptions.
        
        Weather descriptions are loaded from weather_code_map.json to allow
        for easy translation and customization without code changes.
    """
    if weather_code is None:
        return _weather_code_map.get("-1", "weather conditions are unavailable")

    try:
        code_key = str(int(weather_code))
        return _weather_code_map.get(code_key, _weather_code_map.get("-2", "weather conditions are unrecognized"))
    except (ValueError, TypeError):
        return _weather_code_map.get("-2", "weather conditions are unrecognized")
