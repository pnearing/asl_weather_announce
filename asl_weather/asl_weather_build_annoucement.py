"""
Build weather announcement message components.

This module provides functions to construct natural language strings
for weather, date, and time announcements that are formatted for
text-to-speech synthesis in the ASL Weather application.
"""
from datetime import datetime
from typing import Dict, Any, Optional
import logging
import os
import json

from asl_weather.get_weather import CurrentWeatherResult

# Load weather code modifier words from JSON file for easy translation/extension
_weather_code_modifier_words: Dict[str, str] = {}
_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_weather_code_modifier_words_file = os.path.join(_data_dir, "modifier_words_en.json")
try:
    with open(_weather_code_modifier_words_file, "r", encoding="utf-8") as _f:
        _weather_code_modifier_words = json.load(_f)
except (FileNotFoundError, json.JSONDecodeError, OSError):
    # Fallback to empty dict; function will handle missing map gracefully
    _weather_code_modifier_words = {}


def _get_modifier_word(weather_code: int) -> str:
    """
    Get the modifier word for a given weather code.
    
    Args:
        weather_code: Weather code from Open-Meteo API
        
    Returns:
        Modifier word for the weather code, or empty string if not found
    """
    return _weather_code_modifier_words.get(str(weather_code), "")


def _format_temp(value: float) -> str:
    """
    Format temperature value for display by removing unnecessary decimal places.
    
    This helper function formats temperature values to be more readable
    for text-to-speech applications by removing trailing zeros after the
    decimal point. This makes "15.0" display as "15" while preserving
    decimal precision when needed (e.g., "15.4" stays as "15.4").
    
    Args:
        value: Temperature value as a float
        
    Returns:
        Formatted temperature string
        
    Examples:
        >>> _format_temp(15.0)
        '15'
        >>> _format_temp(15.4)
        '15.4'
        >>> _format_temp(-5.0)
        '-5'
        >>> _format_temp(-5.7)
        '-5.7'
        >>> _format_temp(0.0)
        '0'
        
    Implementation Details:
        - Rounds to 1 decimal place first to handle floating point precision
        - Checks if the rounded value is an integer
        - If integer, returns as int (no decimal point)
        - If not integer, returns as float with 1 decimal place
        
    Note:
        This formatting is specifically designed for text-to-speech applications
        where "fifteen point zero" is less natural than "fifteen".
    """
    rounded_1 = round(value, 1)
    if rounded_1.is_integer():
        return str(int(rounded_1))
    return str(rounded_1)


def build_weather(
    weather: CurrentWeatherResult,
    config: Dict[str, Any],
    logger: logging.Logger
) -> str:
    """
    Build a weather announcement string from weather data and configuration.

    Constructs a natural language weather announcement based on the provided
    weather result and configuration options. The announcement can include
    city, state/province, and country information based on user preferences.

    Args:
        weather: The current weather result object containing weather data
            and the natural_language() method for formatting.
        config: Configuration dictionary containing speech output options.
            Supported keys:
            - say_city (bool): Include city name in announcement
            - say_state_province (bool): Include state/province in announcement
            - say_country (bool): Include country name in announcement
        logger: Logger instance for debug output.

    Returns:
        A natural language weather announcement string formatted for TTS.

    Example:
        >>> weather = get_weather_data()  # Assume this returns CurrentWeatherResult
        >>> config = {"say_city": True, "say_state_province": False, "say_country": False}
        >>> announcement = build_weather(weather, config, logger)
        >>> print(announcement)
        'In Toronto, it is currently 22 degrees and partly cloudy'
    """
    # Determine which location components to include
    say_location = config.get("say_location", True)
    say_city = config.get("say_city", True)
    say_state_province = config.get("say_state_province", False) and say_city
    say_country = config.get("say_country", False) and (say_state_province or say_city)
    
    # Determine if any location information is provided
    location_provided = say_city or say_state_province or say_country

    logger.debug(f"say_location: {say_location}, say_city: {say_city}, say_state_province: {say_state_province}, say_country: {say_country}, location_provided: {location_provided}")

    # Determine if we should say the unit
    say_unit = config.get("say_unit", True)

    # Build location string
    location_str = ""
    if say_location and location_provided:
        if say_city:
            location_str += f"{weather.city}"
        if say_state_province:
            location_str += f", {weather.state_province}"
        if say_country:
            location_str += f", {weather.country}"
            
    # Build temperature string
    temperature = _format_temp(weather.temperature)
    unit_word = "Celsius" if weather.temperature_unit == "C" else "Fahrenheit"
    temperature_str = f"{temperature} degrees"
    if say_unit:
        temperature_str += f" {unit_word}"
    
    # Determine modifier word
    modifier_word = _get_modifier_word(weather.weather_code)

    # Build the actual weather string
    weather_string = "currently "

    if say_location and location_provided:
        weather_string += f"in {location_str}, "
    
    weather_string += f"it is {temperature_str}"
    weather_string += f", {modifier_word} {weather.weather_description}."
    
    return weather_string


def build_time(
    timezone_str: Optional[str],
    logger: logging.Logger
) -> str:
    """
    Build a time announcement string.

    Creates a natural language time string in the format "H MM AM/PM" or
    just "H AM/PM" when minutes are zero. Handles timezone conversion and
    falls back to local time if the timezone is invalid.

    Args:
        timezone_str: IANA timezone name (e.g., "America/Toronto") or None
            to use the system local time.
        logger: Logger instance for debug and warning output.

    Returns:
        A formatted time string for TTS (e.g., "10 30 AM" or "10 AM").

    Example:
        >>> time_str = build_time("America/New_York", logger)
        >>> print(time_str)
        '10 30 AM'
        >>> time_str = build_time(None, logger)  # Uses local time
        >>> print(time_str)
        '3 PM'
    """
    # Use timezone if provided, otherwise use local time
    if timezone_str:
        try:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo(timezone_str))
        except Exception:
            # Fallback to local time if timezone is invalid
            logger.warning(f"Invalid timezone '{timezone_str}', using local time")
            now = datetime.now()
    else:
        now = datetime.now()

    time_str = now.strftime("%I:%M").lstrip("0").replace(":", " ")

    # Format time so if exactly on the hour, it just says the hour (e.g., "10" instead of "10 00")
    if time_str.endswith("00"):
        time_str = time_str.replace("00", "")

    # Add AM/PM
    time_str += " " + now.strftime("%p")

    logger.debug(f"time_str: '{time_str}'")

    return time_str


def build_date(
    say_year: bool,
    timezone_str: Optional[str],
    logger: logging.Logger
) -> str:
    """
    Build a date announcement string.

    Creates a natural language date string (e.g., "April 4, 2026" or "April 4").
    Removes leading zeros from day numbers for better TTS pronunciation.
    Handles timezone conversion and falls back to local time if invalid.

    Args:
        say_year: Whether to include the year in the date string.
        timezone_str: IANA timezone name (e.g., "America/Toronto") or None
            to use the system local time.
        logger: Logger instance for debug output.

    Returns:
        A formatted date string for TTS (e.g., "April 4, 2026" or "April 4").

    Example:
        >>> date_str = build_date(True, "America/Toronto", logger)
        >>> print(date_str)
        'April 6, 2026'
        >>> date_str = build_date(False, None, logger)  # No year, local time
        >>> print(date_str)
        'April 6'
    """
    # Use timezone if provided, otherwise use local time
    if timezone_str:
        try:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo(timezone_str))
        except Exception:
            # Fallback to local time if timezone is invalid
            logger.warning(f"Invalid timezone '{timezone_str}', using local time")
            now = datetime.now()
    else:
        now = datetime.now()

    # Format date in natural language (e.g., "April 4, 2026")
    if say_year:
        date_str = now.strftime("%B %d, %Y")
    else:
        date_str = now.strftime("%B %d")

    # Remove leading zero from day (e.g., "April 04" -> "April 4")
    date_str = date_str.replace(" 0", " ")

    logger.debug(f"date_str: '{date_str}'")

    return date_str
