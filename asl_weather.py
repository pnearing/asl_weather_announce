#!/usr/bin/env python3
"""
ASL Weather Announce Main Entry Point

This script provides the main entry point for the ASL Weather Announce system.
It combines postal code lookup with weather retrieval to provide current weather
conditions for a specified location, with optional text-to-speech announcements
through AllStarLink (ASL) nodes.

Features:
    - Location lookup via postal/ZIP code or direct latitude/longitude coordinates
    - Current weather retrieval from Open-Meteo API (no API key required)
    - Natural language weather announcements optimized for TTS
    - Optional date and time announcements with timezone support
    - Configurable TTS voice selection via asl-tts
    - Pre-announcement and post-announcement text options
    - Persistent disk caching for location lookups
    - Comprehensive logging with file or console output
    - Dry-run mode for testing without broadcasting

Usage:
    sudo asl_weather
    sudo asl_weather --postal-code N6A3K7 --country-code CA
    sudo asl_weather --config /path/to/custom.conf
    sudo asl_weather -p N6A3K7 -c CA -n 12345 --say-time --say-date
    sudo asl_weather --dry-run  # Preview announcement text only
    sudo asl_weather --pre-announcement "Attention please" --post-announcement "73"

Configuration:
    Default config path: /etc/asl_weather.conf

    Example config file:
    [asl_weather]
    log_file = /var/log/asl_weather.log
    timezone = America/Toronto
    temperature_unit = C

    [location]
    postal_code = N6A 3K7
    country_code = CA
    # Optional: Use coordinates instead of postal code
    # latitude = 43.6532
    # longitude = -79.3832
    # location_name = Toronto, Ontario

    [asl]
    node_number = 12345

    [asl-tts]
    voice = en_GB-alan-low.onnx
    voice_dir = /var/lib/piper-tts

    [announcements]
    say_weather = true
    say_unit = true
    say_location = true
    say_city = true
    say_state_province = false
    say_country = false
    say_time = true
    say_date = true
    pre_announcement = Attention please
    post_announcement = 73 and good bye

Command Line Options:
    -C, --config PATH                   Path to configuration file (default: /etc/asl_weather.conf)
    -p, --postal-code CODE              Postal/ZIP code to lookup (overrides config)
    -c, --country-code CODE             Country code - accepts 2-letter (CA), 3-letter (CAN),
                                        numeric (124), or full name (Canada). Case-insensitive.
    --latitude LAT                      Latitude coordinate (overrides config)
    --longitude LON                     Longitude coordinate (overrides config)
    -n, --node-number NUM               ASL node number for broadcast (overrides config)
    --temperature-unit UNIT             Temperature unit - C for Celsius, F for Fahrenheit (overrides config)
    -v, --voice VOICE                   TTS voice file (e.g., en_GB-alan-low.onnx, overrides config)
    --log-file PATH                     Path to log file (logs to file instead of terminal)
    -w, --say-weather                   Announce the weather (overrides config)
    -W, --no-say-weather                Do not announce the weather (overrides config)
    -u, --say-unit                      Announce the temperature unit (overrides config)
    -U, --no-say-unit                   Do not announce the temperature unit (overrides config)
    -l, --say-location                  Announce the location name (overrides config)
    -L, --no-say-location               Do not announce the location name (overrides config)
    --say-city                          Announce the city name (overrides config)
    --no-say-city                       Do not announce the city name (overrides config)
    --say-state-province                Announce the state/province name (overrides config)
    --no-say-state-province             Do not announce the state/province name (overrides config)
    --say-country                       Announce the country name (overrides config)
    --no-say-country                    Do not announce the country name (overrides config)
    -t, --say-time                      Announce current time before weather (overrides config)
    -T, --no-say-time                   Do not announce current time (overrides config)
    -d, --say-date                      Announce current date before weather (overrides config)
    -D, --no-say-date                   Do not announce current date (overrides config)
    -b, --pre-announcement TEXT         Text to announce before main content
    -a, --post-announcement TEXT        Text to announce after main content
    -f, --output-file FILE              Output speech to file (passed to asl-tts -f, no extension needed)
    --dry-run                           Print text only, don't broadcast
    --offline                           Offline mode - only announce time/date without weather API calls
    --test-config                       Validate configuration and exit without making API calls or announcements

Location Specification:
    Locations can be specified in two ways:
    1. Postal/ZIP code + country code (traditional method)
       - Uses Zippopotam.us and OpenStreetMap Nominatim for lookup
       - Results are cached to disk for performance
    2. Direct latitude/longitude coordinates (config file only)
       - Specify latitude and longitude in [location] section
       - Optional location_name to skip reverse geocoding
       - Bypasses postal code lookup entirely

Dependencies:
    - Python 3.6+
    - requests (Python module)
    - asl-tts (system binary for TTS/audio playback)
    - Root or asterisk user privileges (for ASL integration)

Notes:
    - The script requires root or asterisk user privileges when not in dry-run mode
    - Weather data is provided by Open-Meteo (free, no API key required)
    - Location lookups are cached to reduce API calls
    - TTS voice files must be installed in the piper-tts voice directory
"""

__version__ = "1.0.3"
__author__ = "Peter Nearing"
__email__ = "me@peternearing.ca"

import logging
import shutil
import subprocess
import sys
from typing import Dict, Any, Optional

from asl_weather import build_weather, build_date, build_time
from asl_weather import check_root_privileges, check_dependencies, validate_coordinates, check_voice_exists, validate_postal_and_country_codes
from asl_weather import parse_arguments, load_config, resolve_configuration
from asl_weather import start_logging

from asl_weather.get_location import PostalLookup, PostalLookupError, NetworkError
from asl_weather.get_weather import get_current_weather, WeatherLookupError, NetworkError, CurrentWeatherResult


def get_location_postal_country(config: Dict[str, Any], logger: Optional[logging.Logger]) -> Dict[str, Any] | bool:
    """
    Look up location information from postal code and country code.
    
    Uses the get_location package to fetch city, state/province, country,
    and coordinates for the given postal code.
    
    Args:
        postal_code: Postal or ZIP code to lookup.
        country_code: 2-letter ISO country code.
        logger: Optional logger instance.
        cache_size: Maximum number of entries to cache (default: 100).
        
    Returns:
        Dictionary containing location data with keys:
        - city: City name
        - state_province: State or province name
        - country: Full country name
        - latitude: Decimal latitude
        - longitude: Decimal longitude
        
    Raises:
        SystemExit: If location lookup fails.
    """
    
    lookup = PostalLookup(logger=logger, cache_size=config.get("cache_size", 100))
    
    try:
        result = lookup.lookup(config["postal_code"], config["country_code"])
    except NetworkError as e:
        logger.error(f"Network error during location lookup: {e}")
        return False
    except PostalLookupError as e:
        logger.error(f"Location lookup failed: {e}")
        return False
    
    if result is None:
        logger.error(f"Could not find location for postal code '{config['postal_code']}' in country '{config['country_code']}'")
        return False
    # Clean up city name for TTS
    if result.get("city"):
        result["city"] = clean_city_name(result["city"])

    return result


def get_location_lat_lon(config, logger)-> Dict[str, Any]:
    """
    Look up location information from latitude and longitude.
    
    Uses the get_location package to fetch city, state/province, country,
    and coordinates for the given latitude and longitude.
    
    Args:
        config: Configuration dictionary containing latitude and longitude.
        logger: Optional logger instance.
        
    Returns:
        Dictionary containing location data with keys:
        - city: City name
        - state_province: State or province name
        - country: Full country name
        - latitude: Decimal latitude
        - longitude: Decimal longitude
        
    Raises:
        SystemExit: If location lookup fails.
    """
    # Check if location_name is provided (skips reverse lookup)
    if config.get("location_name"):
        # Parse location_name - can be "City, State" or just "City"
        loc_parts = config["location_name"].split(",", 1)
        city = loc_parts[0].strip()
        state_province = loc_parts[1].strip() if len(loc_parts) > 1 else None
        
        location_data = {
            "city": city,
            "state_province": state_province,
            "country": None,
            "latitude": config["latitude"],
            "longitude": config["longitude"],
        }
        logger.debug(f"Using configured location name: {config['location_name']}")
    else:
        # Use configured coordinates and perform reverse lookup to get location name
        lookup = PostalLookup(logger=logger, cache_size=config.get("cache_size", 100))
        try:
            location_data = lookup.reverse_lookup(config["latitude"], config["longitude"])
            if location_data is None:
                logger.warning("Reverse geocoding returned no results, not saying location.")
                location_data = {
                    "city": None,
                    "state_province": None,
                    "country": None,
                    "latitude": config["latitude"],
                    "longitude": config["longitude"],
                }
            else:
                # Ensure coordinates from config are preserved (reverse lookup may have slightly different values)
                location_data["latitude"] = config["latitude"]
                location_data["longitude"] = config["longitude"]
                logger.debug(f"Resolved location from coordinates: {location_data['city']}, {location_data.get('state_province')}")
            
            # Clean up city name for TTS
            if location_data.get("city"):
                location_data["city"] = clean_city_name(location_data["city"])
        except PostalLookupError as e:
            logger.warning(f"Reverse geocoding failed: {e}, not saying location.")
            location_data = {
                "city": None,
                "state_province": None,
                "country": None,
                "latitude": config["latitude"],
                "longitude": config["longitude"],
            }

def get_weather(location_data: Dict[str, Any], temperature_unit: str = "C", logger: Optional[logging.Logger] = None) -> CurrentWeatherResult | bool:
    """
    Fetch current weather for the given location.
    
    Uses the get_weather package to retrieve current weather conditions
    based on the latitude and longitude from the location data.
    
    Args:
        location_data: Dictionary containing location data with keys:
            - city: City name
            - state_province: State or province name
            - country: Full country name
            - latitude: Decimal latitude
            - longitude: Decimal longitude
        temperature_unit: Temperature unit, "C" or "F" (default: "C")
        
    Returns:
        CurrentWeatherResult object with weather information.
        
    Raises:
        SystemExit: If weather lookup fails.
    """
    try:
        result = get_current_weather(
            city=location_data["city"],
            state_province=location_data.get("state_province"),
            country=location_data.get("country"),
            latitude=location_data["latitude"],
            longitude=location_data["longitude"],
            temperature_unit=temperature_unit
        )
    except NetworkError as e:
        logger.error(f"Network error during weather lookup: {e}")
        return False
    except WeatherLookupError as e:
        logger.error(f"Weather lookup failed: {e}")
        return False
    except ValueError as e:
        logger.error(f"Invalid parameters for weather lookup: {e}")
        return False
    
    return result


def print_config_info(config_file_path: str, config: Dict[str, Any]) -> None:
    """
    Print configuration information and exit.
    
    Args:
        config_file_path: Path to the configuration file.
        config: Dictionary containing configuration data.
    """
    print("Configuration validation mode - no API calls will be made.")
    print()
    print("Configuration Summary:")
    print(f"  Config file: {config_file_path}")
    print(f"  Log file: {config.get('log_file') or 'console (default)'}")
    print()
    print("  Location:")
    if config.get('latitude') is not None and config.get('longitude') is not None:
        print(f"    Mode: Coordinates (lat={config['latitude']}, lon={config['longitude']})")
        if config.get('location_name'):
            print(f"    Location name: {config['location_name']}")
    else:
        print(f"    Postal code: {config['postal_code']}")
        print(f"    Country code: {config['country_code']}")
    print()
    print("  ASL Settings:")
    print(f"    Node number: {config['node_number']}")
    print()
    print("  'asl-tts' Settings:")
    print(f"    Voice: {config.get('voice') or 'default'}")
    print(f"    Voice directory: {config['voice_dir']}")
    print()
    print("  Announcement Options:")
    print(f"    Temperature unit: {config['temperature_unit']}")
    print(f"    Say time: {'enabled' if config.get('say_time') else 'disabled'}")
    print(f"    Say date: {'enabled' if config.get('say_date') else 'disabled'}")
    print(f"    Timezone: {config.get('timezone') or 'local (default)'}")
    print(f"    Pre-announcement: {config.get('pre_announcement') or 'none (default)'}")
    print(f"    Post-announcement: {config.get('post_announcement') or 'none (default)'}")
    print(f"  Output file: {config.get('output_file') or 'none (broadcast to node) (default)'}")
    print()
    print(f"    Offline mode: {'enabled' if config.get('offline') else 'disabled'}")
    print()
    print("Configuration is valid.")


def clean_city_name(city_name: str) -> str:
    """
    Clean up city name for TTS by removing parenthetical content.
    
    Args:
        city_name: The city name to clean
        
    Returns:
        The cleaned city name
    """
    # Clean up city name for TTS (remove parenthetical content like "(UWO)" from "London North (UWO)")
    if city_name:
        city_name = city_name.split("(")[0].strip()
    return city_name


def main() -> int:
    """
    Main entry point for the ASL Weather Announce script.
    
    Returns:
        Exit code: 0 on success, non-zero on failure.
    """
    # Parse CLI arguments first
    cli_args = parse_arguments()

    # Load config file early to check for log_file setting
    file_config = load_config(cli_args.config)

    # Determine effective log file: CLI arg > config file > None (console logging)
    effective_log_file = cli_args.log_file or file_config["log_file"]

    # Initialize logging and get logger
    logger = start_logging(__name__, effective_log_file)
    
    # Check root privileges, unless running in dry run mode
    if not cli_args.dry_run:
        if not check_root_privileges(logger):
            return 1
        
    
    # Verify dependencies are installed
    if cli_args.dry_run:
        # In dry run mode, we only need python dependencies, not the tts engine.
        if not check_dependencies(no_tts=True, logger=logger):
            return 2
    else:
        if not check_dependencies(logger=logger):
            return 2
    
    # Resolve configuration (CLI overrides config file)
    config = resolve_configuration(cli_args)

    # Check if latitude/longitude override is provided
    lat_lon_override = config["latitude"] is not None and config["longitude"] is not None
    
    if lat_lon_override:
        # Validate and sanitize coordinates
        return_value = validate_coordinates(config["latitude"], config["longitude"])
        if return_value is False:
            return 3
        lat, lon = return_value
        config["latitude"] = lat
        config["longitude"] = lon
        logger.debug(f"Using configured coordinates: latitude={lat}, longitude={lon}")
    else:
        # Validate postal code and country code
        return_value = validate_postal_and_country_codes(config["postal_code"], config["country_code"], logger)
        if return_value is False:
            return 4
        postal_code, country_code = return_value
        config["postal_code"] = postal_code
        config["country_code"] = country_code
        logger.debug(f"Using configured postal code and country code: postal_code={postal_code}, country_code={country_code}")
    
    # Validate node number
    if not config["node_number"]:
        logger.error("node_number is required. Provide via --node-number(-n) or config file.")
        logger.error(f"Config file location: {cli_args.config}")
        return 5

    # Handle --test-config mode: validate config and exit without API calls
    if cli_args.test_config:
        print_config_info(cli_args.config, config)
        return 0

    # Check if the voice exists, if not, use the default voice
    if config['voice']:
        if not check_voice_exists(config['voice'], config['voice_dir'], logger):
            config['voice'] = None

    # Determine if we're using lat/lon override
    use_lat_lon_override = config.get("latitude") is not None and config.get("longitude") is not None

    # If in 'offline' mode, we don't get location data
    if config.get("offline"):
        logger.info("Offline mode enabled - skipping location lookup")
        location_data = {
            "city": None,
            "state_province": None,
            "country": None,
            "latitude": config["latitude"],
            "longitude": config["longitude"],
        }
    
    elif use_lat_lon_override:
        # Get location data from lat/lon (unless in offline mode)
        location_data = get_location_lat_lon(config, logger=logger)
        if location_data is False:
            logger.error("Failed to get location from latitude and longitude")
            return 6
    else:
        # Get location data from postal code (unless in offline mode)
        location_data = get_location_postal_country(config, logger=logger)
        if location_data is False:
            logger.error("Failed to get location from postal code and country code")
            return 7

    # Get current weather for the location (unless in offline mode)
    if not config.get("offline"):
        weather = get_weather(location_data, temperature_unit=config.get("temperature_unit", "C"), logger=logger)
        if weather is False:
            logger.error("Failed to get weather data")
            return 8
    else:
        logger.info("Offline mode enabled - skipping weather lookup")
        weather = None
    
    # Build weather announcement
    if weather is not None:
        weather_announcement = build_weather(weather, config, logger)
    else:
        weather_announcement = ""
    
    # Build date announcement
    if config.get("say_date"):
        date_announcement = build_date(config.get("say_year", True), config.get("timezone", None), logger=logger)
    else:
        date_announcement = ""
    
    # Build time announcement
    if config.get("say_time"):
        time_announcement = build_time(config.get("timezone", None), logger=logger)
    else:
        time_announcement = ""

    # Get pre-announcement if configured
    if config.get("pre_announcement"):
        pre_announcement = f"{config['pre_announcement']}. "
    else:
        pre_announcement = ""
    
    # Get post-announcement if configured
    if config.get("post_announcement"):
        post_announcement = f". {config['post_announcement']}"
    else:
        post_announcement = ""
    
    # Build final announcement with pre and post announcements
    announcement = f"{pre_announcement} {time_announcement} {date_announcement} {weather_announcement} {post_announcement}"
    
    # Build asl-tts command line:
    asl_tts_cmd = []
    asl_tts_cmd.append(shutil.which("asl-tts"))
    asl_tts_cmd.append(f"-n {config['node_number']}")
    asl_tts_cmd.append(f"-t {announcement}")
    if config['voice']:
        asl_tts_cmd.append(f"-v {config['voice']}")
    
    if config['output_file']:
        asl_tts_cmd.append(f"-f {config['output_file']}")
    
    # Output weather information to stdout if in dry run mode
    if cli_args.dry_run:
        print(announcement)
        return 0
    
    # Send announcement to asl-tts, if an annoucement exists
    try:
        if announcement:
            subprocess.check_call(asl_tts_cmd)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to send announcement to asl-tts: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
