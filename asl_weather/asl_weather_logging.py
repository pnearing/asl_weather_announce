"""ASL Weather Announce Logging Module

Provides centralized logging setup for the ASL Weather Announce system.
This module handles log file writability checks and falls back to console
logging if the configured log file cannot be written to.

The logging setup uses a simple approach with a constant default log file path.
The package installer sets up proper permissions so both root and asterisk
users can write to the log file.
"""

import logging
import os

from .asl_weather_constants import LOG_LEVEL, DEFAULT_LOG_FILE


def _check_log_writable(log_file: str) -> bool:
    """Check if the log file is writable.

    If the log file exists, checks if it's writable.
    If it doesn't exist, checks if the parent directory is writable.

    Args:
        log_file: Path to the log file.

    Returns:
        True if log file is writable, False otherwise.
    """
    if os.path.exists(log_file):
        return os.access(log_file, os.W_OK)

    log_dir = os.path.dirname(log_file)
    if log_dir and os.path.exists(log_dir):
        return os.access(log_dir, os.W_OK)

    return False


def start_logging(logger_name: str, log_file: str | None = None) -> logging.Logger:
    """Initialize and configure logging for ASL Weather Announce.

    Configures logging to either a file or console based on the provided
    log_file parameter. If the log file is not writable, falls back to
    console logging with a warning.

    Args:
        log_file: Path to the log file. If None, uses console logging.
                  If provided but not writable, falls back to console.

    Returns:
        Configured logger instance for the ASL Weather Announce module.

    Example:
        >>> logger = start_logging("/var/log/asl_weather/asl_weather.log")
        >>> logger.info("Logging initialized")
        >>>
        >>> # For console-only logging
        >>> logger = start_logging()
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

    if log_file and _check_log_writable(log_file):
        logging.basicConfig(
            level=level,
            format=log_format,
            handlers=[logging.FileHandler(log_file)]
        )
    else:
        logging.basicConfig(
            level=level,
            format=log_format
        )
        if log_file:
            # Log a warning that we fell back to console
            temp_logger = logging.getLogger(logger_name)
            temp_logger.warning(
                f"Log file {log_file} is not writable, using console logging"
            )

    return logging.getLogger(logger_name)
