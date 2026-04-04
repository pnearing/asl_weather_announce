from .exceptions import (
    WeatherLookupError,
    NetworkError,
    RateLimitError,
    APIResponseError,
    InvalidLocationError,
)
from .weather_lookup import (
    get_current_weather,
    CurrentWeatherResult,
    weather_code_to_description,
)

__all__ = [
    "WeatherLookupError",
    "NetworkError",
    "RateLimitError",
    "APIResponseError",
    "InvalidLocationError",
    "get_current_weather",
    "CurrentWeatherResult",
    "weather_code_to_description",
]

__version__ = "1.0.0"
__author__ = "Peter Nearing"
__email__ = "me@peternearing.ca"

