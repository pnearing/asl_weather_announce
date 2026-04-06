"""ASL Weather Announce CLI Module

Handles all command-line interface functionality for the ASL Weather Announce
system, including argument parsing and configuration file loading.
"""

import argparse
import configparser
import logging
import os
import sys
from typing import Dict, Any

from asl_weather_constants import DEFAULT_CONFIG_PATH, DEFAULT_VOICE_DIR, TRUE_WORDS

def _normalize_bool_word(text: str) -> str:
    return " ".join(text.strip().lower().split())

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Namespace object containing parsed CLI arguments.
    """
    parser = argparse.ArgumentParser(
        description="ASL Weather Announce - Get current weather for a postal code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sudo asl_weather
  sudo asl_weather -p N6A3K7 -c CA
  sudo asl_weather -C /path/to/custom.conf -n 12345
  sudo asl_weather -p N6A3K7 -c CA -v en_GB-alan-low.onnx
        """
    )

    parser.add_argument(
        "-C", "--config",
        type=str,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to configuration file (default: {DEFAULT_CONFIG_PATH})"
    )

    parser.add_argument(
        "-p", "--postal-code",
        type=str,
        help="Postal/ZIP code to lookup (overrides config file)"
    )

    parser.add_argument(
        "-c", "--country-code",
        type=str,
        help="Country code - accepts 2-letter (CA), 3-letter (CAN), numeric (124), or full name (Canada). Case-insensitive."
    )

    parser.add_argument(
        "--latitude",
        type=float,
        help="Latitude coordinate (overrides config file)"
    )

    parser.add_argument(
        "--longitude",
        type=float,
        help="Longitude coordinate (overrides config file)"
    )

    parser.add_argument(
        "-n", "--node-number",
        type=int,
        help="ASL node number (overrides config file)"
    )

    parser.add_argument(
        "--temperature-unit",
        type=str,
        choices=["C", "F"],
        help="Temperature unit: C for Celsius, F for Fahrenheit (overrides config file)"
    )

    parser.add_argument(
        "-v", "--voice",
        type=str,
        help="TTS voice to use (e.g., en_GB-alan-low.onnx, overrides config file)"
    )

    parser.add_argument(
        "--log-file",
        type=str,
        help="Path to log file (logs to file instead of terminal)"
    )

    parser.add_argument(
        "-w", "--say-weather",
        action="store_true",
        help="Announce the weather (overrides config file)"
    )

    parser.add_argument(
        "-W", "--no-say-weather",
        action="store_false",
        dest="say_weather",
        help="Do not announce the weather (overrides config file)"
    )
    
    parser.add_argument(
        "-u", "--say-unit",
        action="store_true",
        help="Announce the temperature unit (overrides config file)"
    )

    parser.add_argument(
        "-U", "--no-say-unit",
        action="store_false",
        dest="say_unit",
        help="Do not announce the temperature unit (overrides config file)"
    )

    parser.add_argument(
        "-l", "--say-location",
        action="store_true",
        help="Announce the location name (overrides config file)"
    )

    parser.add_argument(
        "-L", "--no-say-location",
        action="store_false",
        dest="say_location",
        help="Do not announce the location name (overrides config file)"
    )

    parser.add_argument(
        "--say-city",
        action="store_true",
        help="Announce the city name (overrides config file)"
    )

    parser.add_argument(
        "--no-say-city",
        action="store_false",
        dest="say_city",
        help="Do not announce the city name (overrides config file)"
    )

    parser.add_argument(
        "--say-state-province",
        action="store_true",
        help="Announce the state/province name (overrides config file)"
    )

    parser.add_argument(
        "--no-say-state-province",
        action="store_false",
        dest="say_state_province",
        help="Do not announce the state/province name (overrides config file)"
    )

    parser.add_argument(
        "--say-country",
        action="store_true",
        help="Announce the country name (overrides config file)"
    )

    parser.add_argument(
        "--no-say-country",
        action="store_false",
        dest="say_country",
        help="Do not announce the country name (overrides config file)"
    )
    parser.add_argument(
        "-t", "--say-time",
        action="store_true",
        help="Announce the current time before the weather (overrides config file)"
    )

    parser.add_argument(
        "-T", "--no-say-time",
        action="store_false",
        dest="say_time",
        help="Do not announce the current time before the weather (overrides config file)"
    )

    parser.add_argument(
        "-d", "--say-date",
        action="store_true",
        help="Announce the current date before the weather (overrides config file)"
    )

    parser.add_argument(
        "-D", "--no-say-date",
        action="store_false",
        dest="say_date",
        help="Do not announce the current date before the weather (overrides config file)"
    )

    parser.add_argument(
        "-f", "--output-file",
        type=str,
        help="Output speech to file (passed to asl-tts -f option, no extension needed, .ul will be appended automatically)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the announcement text instead of sending it to asl-tts"
    )

    parser.add_argument(
        "--test-config",
        action="store_true",
        help="Validate configuration and exit without making API calls or announcements"
    )

    parser.add_argument(
        "--offline",
        action="store_true",
        dest="offline",
        help="Offline mode - only announce time/date without weather API calls"
    )

    parser.add_argument(
        "-b", "--pre-announcement",
        type=str,
        dest="pre_announcement",
        help="Text to announce before the main announcement (overrides config file)"
    )

    parser.add_argument(
        "-a", "--post-announcement",
        type=str,
        dest="post_announcement",
        help="Text to announce after the main announcement (overrides config file)"
    )

    return parser.parse_args()


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from INI file.

    Args:
        config_path: Path to the INI configuration file.

    Returns:
        Dictionary containing configuration values with all settings.
        Missing values are returned as None or defaults.

    Notes:
        - If the config file doesn't exist, returns empty values (all None)
        - Invalid config format will print an error and exit
        - Missing sections/values are returned as None
    """
    config = {
        "postal_code": None,
        "country_code": None,
        "latitude": None,
        "longitude": None,
        "location_name": None,
        "node_number": None,
        "voice": None,
        "voice_dir": DEFAULT_VOICE_DIR,
        "log_file": None,
        "say_weather": True,
        "say_unit": True,
        "say_time": False,
        "say_date": False,
        "say_location": True,
        "say_city": True,
        "say_state_province": False,
        "say_country": False,
        "timezone": None,
        "temperature_unit": "C",
        "output_file": None,
        "offline": False,
        "cache_size": 100,
        "pre_announcement": None,
        "post_announcement": None,
    }

    if not os.path.exists(config_path):
        return config

    parser = configparser.ConfigParser()

    try:
        parser.read(config_path)
    except configparser.Error as e:
        logging.error(f"Invalid configuration file format: {e}")
        sys.exit(1)

    # Read asl_weather section
    if parser.has_section("asl_weather"):
        if parser.has_option("asl_weather", "log_file"):
            config["log_file"] = parser.get("asl_weather", "log_file").strip()


        if parser.has_option("asl_weather", "timezone"):
            timezone_val = parser.get("asl_weather", "timezone").strip()
            if timezone_val:
                config["timezone"] = timezone_val

        if parser.has_option("asl_weather", "temperature_unit"):
            temp_unit = parser.get("asl_weather", "temperature_unit").strip().upper()
            if temp_unit in ("C", "F"):
                config["temperature_unit"] = temp_unit

        if parser.has_option("asl_weather", "output_file"):
            config["output_file"] = parser.get("asl_weather", "output_file").strip()

        if parser.has_option("asl_weather", "offline"):
            offline_val = _normalize_bool_word(parser.get("asl_weather", "offline"))
            config["offline"] = offline_val in TRUE_WORDS

        if parser.has_option("asl_weather", "cache_size"):
            try:
                config["cache_size"] = int(parser.get("asl_weather", "cache_size").strip())
            except ValueError:
                pass


    # Read the announcements section
    if parser.has_section("announcements"):
        if parser.has_option("announcements", "say_weather"):
            say_weather_val = _normalize_bool_word(parser.get("announcements", "say_weather"))
            config["say_weather"] = say_weather_val in TRUE_WORDS
        
        if parser.has_option("announcements", "say_unit"):
            say_unit_val = _normalize_bool_word(parser.get("announcements", "say_unit"))
            config["say_unit"] = say_unit_val in TRUE_WORDS
        
        if parser.has_option("announcements", "say_location"):
            say_location_val = _normalize_bool_word(parser.get("announcements", "say_location"))
            config["say_location"] = say_location_val in TRUE_WORDS
        
        if parser.has_option("announcements", "say_city"):
            say_city_val = _normalize_bool_word(parser.get("announcements", "say_city"))
            config["say_city"] = say_city_val in TRUE_WORDS

        if parser.has_option("announcements", "say_state_province"):
            say_state_province_val = _normalize_bool_word(parser.get("announcements", "say_state_province"))
            config["say_state_province"] = say_state_province_val in TRUE_WORDS

        if parser.has_option("announcements", "say_country"):
            say_country_val = _normalize_bool_word(parser.get("announcements", "say_country"))
            config["say_country"] = say_country_val in TRUE_WORDS

        if parser.has_option("announcements", "say_time"):
            say_time_val = _normalize_bool_word(parser.get("announcements", "say_time"))
            config["say_time"] = say_time_val in TRUE_WORDS

        if parser.has_option("announcements", "say_date"):
            say_date_val = _normalize_bool_word(parser.get("announcements", "say_date"))
            config["say_date"] = say_date_val in TRUE_WORDS

        if parser.has_option("announcements", "pre_announcement"):
            pre_val = parser.get("announcements", "pre_announcement").strip()
            if pre_val:
                config["pre_announcement"] = pre_val

        if parser.has_option("announcements", "post_announcement"):
            post_val = parser.get("announcements", "post_announcement").strip()
            if post_val:
                config["post_announcement"] = post_val


    # Read location section
    if parser.has_section("location"):
        if parser.has_option("location", "postal_code"):
            config["postal_code"] = parser.get("location", "postal_code").strip()

        if parser.has_option("location", "country_code"):
            config["country_code"] = parser.get("location", "country_code").strip()

        if parser.has_option("location", "latitude"):
            lat_val = parser.get("location", "latitude").strip()
            if lat_val:
                config["latitude"] = lat_val

        if parser.has_option("location", "longitude"):
            lon_val = parser.get("location", "longitude").strip()
            if lon_val:
                config["longitude"] = lon_val
                
        if parser.has_option("location", "location_name"):
            loc_name = parser.get("location", "location_name").strip()
            if loc_name:
                config["location_name"] = loc_name

    # Read ASL section
    if parser.has_section("asl"):
        if parser.has_option("asl", "node_number"):
            try:
                config["node_number"] = int(parser.get("asl", "node_number").strip())
            except ValueError:
                logging.error(f"Invalid node number in config file: {parser.get('asl', 'node_number')}")
                sys.exit(1)

    # Read asl-tts section
    if parser.has_section("asl-tts"):
        if parser.has_option("asl-tts", "voice"):
            config["voice"] = parser.get("asl-tts", "voice").strip()

        if parser.has_option("asl-tts", "voice_dir"):
            config["voice_dir"] = parser.get("asl-tts", "voice_dir").strip()
            if not os.path.isdir(config["voice_dir"]):
                logging.error(f"Voice directory does not exist: {config['voice_dir']}")
                sys.exit(1)

    return config


def resolve_configuration(cli_args: argparse.Namespace) -> Dict[str, Any]:
    """
    Resolve final configuration by combining CLI arguments and config file.
    
    CLI arguments take precedence over config file values.
    
    If latitude and longitude are provided in the config file, they override
    the postal_code/country_code lookup and skip directly to weather lookup.
    
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
        "latitude": cli_args.latitude or file_config["latitude"],
        "longitude": cli_args.longitude or file_config["longitude"],
        "location_name": file_config["location_name"],
        "node_number": cli_args.node_number or file_config["node_number"],
        "voice": cli_args.voice or file_config["voice"],
        "voice_dir": file_config["voice_dir"],
        "log_file": cli_args.log_file or file_config["log_file"],
        "say_weather": cli_args.say_weather or file_config["say_weather"],
        "say_unit": cli_args.say_unit or file_config["say_unit"],
        "say_location": cli_args.say_location or file_config["say_location"],
        "say_city": cli_args.say_city or file_config["say_city"],
        "say_state_province": cli_args.say_state_province or file_config["say_state_province"],
        "say_country": cli_args.say_country or file_config["say_country"],
        "say_time": cli_args.say_time or file_config["say_time"],
        "say_date": cli_args.say_date or file_config["say_date"],
        "timezone": file_config["timezone"],
        "temperature_unit": cli_args.temperature_unit or file_config["temperature_unit"] or "C",
        "output_file": cli_args.output_file or file_config["output_file"],
        "offline": cli_args.offline or file_config["offline"],
        "cache_size": file_config["cache_size"],
        "pre_announcement": cli_args.pre_announcement or file_config["pre_announcement"],
        "post_announcement": cli_args.post_announcement or file_config["post_announcement"],
    }
    
    return config
