"""ASL Weather Announce package.

This package provides modules for building weather announcements,
configuration management, logging, and resilience patterns.
"""

from .asl_weather_build_annoucement import build_weather, build_date, build_time
from .asl_weather_checks import (
    check_root_privileges,
    check_dependencies,
    validate_coordinates,
    check_voice_exists,
    validate_postal_and_country_codes,
)
from .asl_weather_config import parse_arguments, load_config, resolve_configuration
from .asl_weather_logging import start_logging
from .asl_weather_constants import DEFAULT_LOG_FILE, DEFAULT_CACHE_FILE
from .asl_weather_cache import PersistentLRUCache
from .asl_weather_resilience import CircuitBreaker, APIMetrics, CircuitBreakerConfig

__all__ = [
    "build_weather",
    "build_date",
    "build_time",
    "check_root_privileges",
    "check_dependencies",
    "validate_coordinates",
    "check_voice_exists",
    "validate_postal_and_country_codes",
    "parse_arguments",
    "load_config",
    "resolve_configuration",
    "start_logging",
    "DEFAULT_LOG_FILE",
    "DEFAULT_CACHE_FILE",
    "PersistentLRUCache",
    "CircuitBreaker",
    "APIMetrics",
    "CircuitBreakerConfig",
]
