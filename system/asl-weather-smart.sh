#!/bin/bash
# Smart ASL Weather wrapper - announces date+time during the 08 hour,
# time only at other hours

HOUR="$(date +%H)" # Current hour (00-23)
LOG_FILE="/var/log/asl_weather.log" # Log file path
ASL_WEATHER_PATH="${ASL_WEATHER_PATH:-$(command -v asl_weather 2>/dev/null || true)}" # Path to asl_weather executable, overridden by environment variable
DATE_ANNOUNCE_HOUR="08" # Hour to announce date and time

# Require root or asterisk
if [[ "$EUID" -ne 0 && "$(id -un)" != "asterisk" ]]; then
    echo "Error: this script must be run as root or asterisk." >&2
    exit 1
fi

# Make sure asl_weather exists
if [[ -z "$ASL_WEATHER_PATH" ]]; then
    echo "Error: asl_weather not found in PATH." >&2
    exit 1
fi

# Make sure it is executable
if [[ ! -x "$ASL_WEATHER_PATH" ]]; then
    echo "Error: $ASL_WEATHER_PATH is not executable." >&2
    exit 1
fi

if [[ "$HOUR" == "$DATE_ANNOUNCE_HOUR" ]]; then
    # 08:00-08:59 - Full announcement with date, time, and weather
    exec "$ASL_WEATHER_PATH" --say-date --say-time --log-file "$LOG_FILE"
else
    # Other hours - Time and weather only
    exec "$ASL_WEATHER_PATH" --say-time --log-file "$LOG_FILE"
fi

