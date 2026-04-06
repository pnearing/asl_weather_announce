"""
Validation and dependency checking functions for asl_weather.

This module provides functions to validate system requirements,
check dependencies, and validate user input for the ASL Weather
application. These checks ensure proper operation and provide
helpful error messages when requirements are not met.
"""

import os
import pwd
import shutil
import sys
from typing import Any, NoReturn

import logging

from asl_weather.get_location import normalize_country_code


def check_root_privileges(logger: logging.Logger = None) -> bool:
    """
    Verify the script is running with root or asterisk user privileges.

    This check is required for ASL (AllStarLink) integration which needs
    root or asterisk user access to interact with the system, write to
    log files, and execute text-to-speech commands.

    Args:
        logger: Logger instance for error output. If None, uses the
            default "asl_weather" logger.

    Returns:
        True if running as root or asterisk user, False otherwise.

    Example:
        >>> if not check_root_privileges(logger):
        ...     sys.exit(1)
        >>> # Proceed with privileged operations
    """
    if not logger:
        logger = logging.getLogger("asl_weather")

    current_uid = os.geteuid()
    current_user = pwd.getpwuid(current_uid).pw_name

    if current_uid != 0 and current_user != "asterisk":
        logger.error("This script must be run as root or the asterisk user.")
        logger.error("Please run with: sudo asl_weather")
        return False

    return True


def check_dependencies(no_tts: bool = False, logger: logging.Logger = None) -> bool:
    """
    Verify all required dependencies are installed.

    Checks for required Python modules (requests) and system binaries
    (asl-tts). The dependency list is designed to be easily expandable
    for future requirements.

    Args:
        no_tts: If True, skip the asl-tts binary check. Useful for
            testing without full TTS setup.
        logger: Logger instance for error output. If None, uses the
            default "asl_weather" logger.

    Returns:
        True if all dependencies are present, False otherwise.

    Example:
        >>> if not check_dependencies(no_tts=False, logger=logger):
        ...     sys.exit(1)
        >>> # Proceed with operations requiring dependencies
    """
    if not logger:
        logger = logging.getLogger("asl_weather")

    # Check Python modules
    required_modules = [
        ("requests", "requests"),
    ]

    missing_modules = []
    for module_name, package_name in required_modules:
        try:
            __import__(module_name)
        except ImportError:
            missing_modules.append(package_name)

    # Check system binaries
    missing_binaries = []
    if not no_tts and not shutil.which("asl-tts"):
        missing_binaries.append("asl-tts")

    if missing_modules or missing_binaries:
        logger.error("Missing required dependencies:")
        for package in missing_modules:
            logger.error(f"  - {package} (Python module)")
        for binary in missing_binaries:
            logger.error(f"  - {binary} (system binary)")

        if missing_modules:
            logger.error(f"Install Python modules with: pip install {' '.join(missing_modules)}")
        if missing_binaries:
            logger.error(f"Install system binaries with: sudo apt install {' '.join(missing_binaries)}")
        return False

    return True


def check_voice_exists(voice: str, voice_dir: str, logger: logging.Logger = None) -> bool:
    """
    Check if a voice exists and is properly configured.

    Verifies that both the voice data file and its JSON configuration
    file exist in the voice directory. Both files are required for
    successful text-to-speech synthesis.

    Args:
        voice: Voice name to check (e.g., "en_US-amy-medium").
        voice_dir: Directory containing voice files (e.g., "/var/lib/piper-tts").
        logger: Logger instance for warning output. If None, uses the
            default "asl_weather" logger.

    Returns:
        True if both the voice data file and JSON config exist,
        False otherwise. If False is returned, the caller should
        use a default voice.

    Example:
        >>> if not check_voice_exists("en_US-amy-medium", "/var/lib/piper-tts", logger):
        ...     voice = "default"
    """
    if not logger:
        logger = logging.getLogger("asl_weather")

    # Construct voice data file path
    voice_file_path = os.path.join(voice_dir, voice)
    
    # Check if voice data file exists
    if not os.path.exists(voice_file_path):
        logger.warning(f"Voice '{voice}' not found in {voice_dir}, using default voice.")
        return False

    # Check if voice JSON config exists
    if not os.path.exists(f"{voice_file_path}.json"):
        logger.warning(f"Voice '{voice}' JSON config not found in {voice_dir}, using default voice.")
        return False

    return True


def validate_coordinates(
    latitude: Any,
    longitude: Any,
    logger: logging.Logger = None
) -> tuple[float, float] | bool:
    """
    Validate and sanitize latitude and longitude coordinates.

    Accepts string or numeric coordinate values, validates they are
    within valid ranges, and returns them as floats rounded to 6
    decimal places (approximately 0.1m precision at the equator).

    Args:
        latitude: Latitude value (string or numeric, -90 to 90 degrees).
        longitude: Longitude value (string or numeric, -180 to 180 degrees).
        logger: Logger instance for error output. If None, uses the
            default "asl_weather" logger.

    Returns:
        Tuple of (sanitized_latitude, sanitized_longitude) as floats,
        or False if validation fails.

    Example:
        >>> result = validate_coordinates("43.6532", "-79.3832", logger)
        >>> if result:
        ...     lat, lon = result
        ...     print(f"Valid: {lat}, {lon}")
        Valid: 43.6532, -79.3832
    """
    if not logger:
        logger = logging.getLogger("asl_weather")

    try:
        # Convert to float and strip whitespace if string
        if isinstance(latitude, str):
            lat = float(latitude.strip())
        else:
            lat = float(latitude)

        if isinstance(longitude, str):
            lon = float(longitude.strip())
        else:
            lon = float(longitude)
    except (TypeError, ValueError) as e:
        logger.error(f"Invalid coordinates: {e}")
        logger.error("Example format:")
        logger.error("[location]")
        logger.error("latitude = 43.6532")
        logger.error("longitude = -79.3832")
        return False

    # Validate ranges
    if not (-90 <= lat <= 90):
        logger.error(f"latitude must be between -90 and 90 (got {lat})")
        return False
    if not (-180 <= lon <= 180):
        logger.error(f"longitude must be between -180 and 180 (got {lon})")
        return False

    # Round to 6 decimal places for precision (approximately 0.1m at equator)
    lat = round(lat, 6)
    lon = round(lon, 6)

    return lat, lon


def validate_postal_and_country_codes(
    postal_code: str,
    country_code: str,
    logger: logging.Logger = None
) -> tuple[str, str] | bool:
    """
    Validate postal code and country code, normalizing country code to ISO format.

    Ensures that postal_code is provided and country_code is valid and
    can be normalized to a 2-letter ISO country code. Provides helpful
    error messages for configuration issues.

    Note: This function references 'cli_args.config' from the global scope
    for error messages. Ensure this is defined when calling.

    Args:
        postal_code: Postal or ZIP code string (e.g., "N6A 3K7", "90210").
        country_code: Country code in various formats (2-letter: "CA",
            3-letter: "CAN", numeric: "124", or full name: "Canada").
        logger: Logger instance for error output. If None, uses the
            default "asl_weather" logger.

    Returns:
        Tuple of (postal_code, normalized_country_code) where country_code
        is normalized to 2-letter ISO format, or False if validation fails.

    Example:
        >>> result = validate_postal_and_country_codes("N6A 3K7", "Canada", logger)
        >>> if result:
        ...     postal, country = result
        ...     print(f"Valid: {postal}, {country}")
        Valid: N6A 3K7, CA
    """
    if not logger:
        logger = logging.getLogger("asl_weather")

    # Validate required postal_code/country_code since no lat/lon override
    if not postal_code:
        logger.error("postal_code is required. Provide via --postal-code(-p) or config file.")
        logger.error(f"Config file location: {cli_args.config}")
        logger.error("Example config file format:")
        logger.error("[location]")
        logger.error("postal_code = N6A 3K7")
        logger.error("country_code = CA")
        return False

    if not country_code:
        logger.error("country_code is required. Provide via --country-code(-c) or config file.")
        logger.error(f"Config file location: {cli_args.config}")
        return False

    # Normalize country code to 2-letter ISO format
    normalized_country = normalize_country_code(country_code)
    if normalized_country is None:
        logger.error(f"Invalid country_code '{country_code}'.")
        logger.error("Accepts 2-letter (US), 3-letter (USA), numeric (840), or full name (United States).")
        logger.error("Examples: CA, CAN, 124, Canada")
        return False

    return postal_code, normalized_country
