#!/usr/bin/env python3
"""
ASL Weather Announce Main Entry Point

This script provides the main entry point for the ASL Weather Announce system.
It combines postal code lookup with weather retrieval to provide current weather
conditions for a specified location.

The script requires root privileges to run (for future ASL integration) and
loads configuration from an INI file, with CLI overrides available.

Usage:
    sudo python main.py
    sudo python main.py --postal-code N6A3K7 --country-code CA
    sudo python main.py --config /path/to/custom.conf

Configuration:
    Default config path: /etc/asl_weather.conf
    
    Example config file:
    [location]
    postal_code = N6A 3K7
    country_code = CA
    
    [asl]
    node_number = 12345
"""

import argparse
import configparser
import os
import sys
from typing import Optional, Dict, Any


def check_root_privileges() -> None:
    """
    Verify the script is running with root or asterisk user privileges.
    
    This is required for ASL (AllStarLink) integration which needs
    root or asterisk user access to interact with the system.
    
    Raises:
        SystemExit: If not running as root or asterisk with an appropriate error message.
    """
    import pwd
    
    current_uid = os.geteuid()
    current_user = pwd.getpwuid(current_uid).pw_name
    
    if current_uid != 0 and current_user != "asterisk":
        print("Error: This script must be run as root or the asterisk user.", file=sys.stderr)
        print("Please run with: sudo python main.py", file=sys.stderr)
        sys.exit(1)


def check_dependencies() -> None:
    """
    Verify all required dependencies are installed.
    
    Currently checks for:
        - requests: HTTP library for API calls
        - asl-tts: System command for TTS and audio playback
    
    The dependency list is designed to be easily expandable for future
    requirements.
    
    Raises:
        SystemExit: If any required dependency is missing with installation instructions.
    """
    import shutil
    
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
    if not shutil.which("asl-tts"):
        missing_binaries.append("asl-tts")
    
    if missing_modules or missing_binaries:
        print("Error: Missing required dependencies:", file=sys.stderr)
        for package in missing_modules:
            print(f"  - {package} (Python module)", file=sys.stderr)
        for binary in missing_binaries:
            print(f"  - {binary} (system binary)", file=sys.stderr)
        
        if missing_modules:
            print(f"\nInstall Python modules with: pip install {' '.join(missing_modules)}", file=sys.stderr)
        if missing_binaries:
            print(f"\nInstall system binaries with: sudo apt install {' '.join(missing_binaries)}", file=sys.stderr)
        sys.exit(1)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        Namespace object containing parsed CLI arguments.
        
    Arguments:
        -C, --config: Path to configuration file (default: /etc/asl_weather.conf)
        -p, --postal-code: Postal/ZIP code to lookup (overrides config)
        -c, --country-code: 2-letter ISO country code (overrides config)
        -n, --node-number: ASL node number (overrides config)
        -v, --voice: TTS voice to use (e.g., en_GB-alan-low.onnx)
    """
    parser = argparse.ArgumentParser(
        description="ASL Weather Announce - Get current weather for a postal code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sudo python main.py
  sudo python main.py -p N6A3K7 -c CA
  sudo python main.py -C /path/to/custom.conf -n 12345
  sudo python main.py -p N6A3K7 -c CA -v en_GB-alan-low.onnx
        """
    )
    
    parser.add_argument(
        "-C", "--config",
        type=str,
        default="/etc/asl_weather.conf",
        help="Path to configuration file (default: /etc/asl_weather.conf)"
    )
    
    parser.add_argument(
        "-p", "--postal-code",
        type=str,
        help="Postal/ZIP code to lookup (overrides config file)"
    )
    
    parser.add_argument(
        "-c", "--country-code",
        type=str,
        help="2-letter ISO country code (overrides config file)"
    )
    
    parser.add_argument(
        "-n", "--node-number",
        type=str,
        help="ASL node number (overrides config file)"
    )
    
    parser.add_argument(
        "-v", "--voice",
        type=str,
        help="TTS voice to use (e.g., en_GB-alan-low.onnx, overrides config file)"
    )
    
    return parser.parse_args()


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from INI file.
    
    Args:
        config_path: Path to the INI configuration file.
        
    Returns:
        Dictionary containing configuration values with structure:
        {
            "postal_code": str or None,
            "country_code": str or None,
            "node_number": str or None,
            "voice": str or None
        }
        
    Notes:
        - If the config file doesn't exist, returns empty values (all None)
        - Invalid config format will print an error and exit
        - Missing sections/values are returned as None
    """
    config = {
        "postal_code": None,
        "country_code": None,
        "node_number": None,
        "voice": None
    }
    
    if not os.path.exists(config_path):
        return config
    
    parser = configparser.ConfigParser()
    
    try:
        parser.read(config_path)
    except configparser.Error as e:
        print(f"Error: Invalid configuration file format: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Read location section
    if parser.has_section("location"):
        if parser.has_option("location", "postal_code"):
            config["postal_code"] = parser.get("location", "postal_code").strip()
        if parser.has_option("location", "country_code"):
            config["country_code"] = parser.get("location", "country_code").strip()
    
    # Read ASL section
    if parser.has_section("asl"):
        if parser.has_option("asl", "node_number"):
            config["node_number"] = parser.get("asl", "node_number").strip()
    
    # Read asl-tts section
    if parser.has_section("asl-tts"):
        if parser.has_option("asl-tts", "voice"):
            config["voice"] = parser.get("asl-tts", "voice").strip()
    
    return config


def resolve_configuration(cli_args: argparse.Namespace) -> Dict[str, Any]:
    """
    Resolve final configuration by combining CLI arguments and config file.
    
    CLI arguments take precedence over config file values.
    
    Args:
        cli_args: Parsed command line arguments.
        
    Returns:
        Dictionary with final resolved configuration values.
        
    Raises:
        SystemExit: If required values are missing after resolution.
    """
    file_config = load_config(cli_args.config)
    
    # CLI values override file config
    config = {
        "postal_code": cli_args.postal_code or file_config["postal_code"],
        "country_code": cli_args.country_code or file_config["country_code"],
        "node_number": cli_args.node_number or file_config["node_number"],
        "voice": cli_args.voice or file_config["voice"],
    }
    
    # Validate required values
    if not config["postal_code"]:
        print("Error: postal_code is required. Provide via --postal-code(-p) or config file.", file=sys.stderr)
        print(f"\nConfig file location: {cli_args.config}", file=sys.stderr)
        print("\nExample config file format:", file=sys.stderr)
        print("[location]", file=sys.stderr)
        print("postal_code = N6A 3K7", file=sys.stderr)
        print("country_code = CA", file=sys.stderr)
        sys.exit(1)
    
    if not config["country_code"]:
        print("Error: country_code is required. Provide via --country-code(-c) or config file.", file=sys.stderr)
        print(f"\nConfig file location: {cli_args.config}", file=sys.stderr)
        sys.exit(1)
    
    return config


def get_location(postal_code: str, country_code: str) -> Dict[str, Any]:
    """
    Look up location information from postal code and country code.
    
    Uses the get_location package to fetch city, state/province, country,
    and coordinates for the given postal code.
    
    Args:
        postal_code: Postal or ZIP code to lookup.
        country_code: 2-letter ISO country code.
        
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
    from get_location import PostalLookup, PostalLookupError, NetworkError
    
    lookup = PostalLookup()
    
    try:
        result = lookup.lookup(postal_code, country_code)
    except NetworkError as e:
        print(f"Error: Network error during location lookup: {e}", file=sys.stderr)
        sys.exit(1)
    except PostalLookupError as e:
        print(f"Error: Location lookup failed: {e}", file=sys.stderr)
        sys.exit(1)
    
    if result is None:
        print(f"Error: Could not find location for postal code '{postal_code}' in country '{country_code}'", file=sys.stderr)
        sys.exit(1)
    
    return result


def get_weather(location_data: Dict[str, Any], temperature_unit: str = "C") -> Any:
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
    from get_weather import get_current_weather, WeatherLookupError, NetworkError
    
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
        print(f"Error: Network error during weather lookup: {e}", file=sys.stderr)
        sys.exit(1)
    except WeatherLookupError as e:
        print(f"Error: Weather lookup failed: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: Invalid parameters for weather lookup: {e}", file=sys.stderr)
        sys.exit(1)
    
    return result


def main() -> int:
    """
    Main entry point for the ASL Weather Announce script.
    
    Returns:
        Exit code: 0 on success, non-zero on failure.
    """
    # Parse CLI arguments
    cli_args = parse_arguments()
    
    # Check root privileges
    # check_root_privileges()
    
    # Verify dependencies are installed
    # check_dependencies()
    
    # Resolve configuration (CLI overrides config file)
    config = resolve_configuration(cli_args)
    
    # Get location data from postal code
    location_data = get_location(config["postal_code"], config["country_code"])
    
    # Clean up city name for TTS (remove parenthetical content like "(UWO)")
    if location_data.get("city"):
        location_data["city"] = location_data["city"].split("(")[0].strip()
    
    # Get current weather for the location
    weather = get_weather(location_data)
    
    # Output weather information
    print(weather.natural_language())
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
