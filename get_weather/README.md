# Weather Lookup Module

A Python module for fetching current weather conditions using the Open-Meteo API, designed specifically for text-to-speech applications with comprehensive error handling and natural language formatting.

## Features

- **Current Weather Data**: Fetch real-time weather conditions using latitude/longitude coordinates
- **Multiple Temperature Units**: Support for both Celsius and Fahrenheit
- **Comprehensive Error Handling**: Granular exception types for different failure scenarios
- **Text-to-Speech Optimized**: Natural language weather descriptions perfect for spoken output
- **WMO Weather Codes**: Translation of standardized weather codes to human-readable descriptions
- **Coordinate Validation**: Built-in validation for latitude/longitude ranges
- **No API Keys Required**: Uses the free Open-Meteo public API

## Installation

This module is part of the AllStarLink ASL Weather Announce package. Ensure you have the required dependencies:

```bash
pip install requests
```

## Quick Start

```python
from get_weather import get_current_weather

# Basic usage
result = get_current_weather(
    city="London",
    state_province="Ontario",
    country="Canada",
    latitude=42.98,
    longitude=-81.25,
    temperature_unit="C"
)

print(result.natural_language())
# Output: "Currently in London, Ontario it is 15 degrees Celsius with clear skies."
```

## API Reference

### Main Function

#### `get_current_weather(...)`

Fetch current weather conditions for a specific location.

**Parameters:**

- `city` (str): Human-readable city name for output text
- `state_province` (str, optional): State or province name for output text
- `country` (str, optional): Country name for output text fallback
- `latitude` (float): Decimal latitude (-90 to 90)
- `longitude` (float): Decimal longitude (-180 to 180)
- `temperature_unit` (str): "C" for Celsius or "F" for Fahrenheit (default: "C")
- `timeout` (float): HTTP timeout in seconds (default: 10.0)
- `user_agent` (str): User-Agent header for HTTP requests

**Returns:**

- `CurrentWeatherResult`: Object containing weather data and formatting methods

**Raises:**

- `ValueError`: Invalid input parameters
- `NetworkError`: Network connectivity issues
- `RateLimitError`: API rate limiting
- `APIResponseError`: Invalid API responses
- `InvalidLocationError`: Invalid coordinates
- `WeatherLookupError`: General weather lookup issues

### Data Classes

#### `CurrentWeatherResult`

Represents current weather conditions for a location.

**Attributes:**

- `city` (str): City name
- `state_province` (str, optional): State or province
- `country` (str, optional): Country name
- `latitude` (float): Latitude coordinate
- `longitude` (float): Longitude coordinate
- `temperature` (float): Current temperature
- `temperature_unit` (str): "C" or "F"
- `weather_code` (int, optional): WMO weather code
- `weather_description` (str): Natural language weather description
- `is_day` (bool, optional): Whether it's currently daytime
- `raw` (dict): Raw API response data

**Methods:**

- `location_label` (property): Formatted location string (e.g., "London, Ontario")
- `natural_language()` (str): Complete weather statement for TTS

### Helper Functions

#### `weather_code_to_description(weather_code, is_day=None)`

Convert WMO weather codes to natural language descriptions.

**Parameters:**

- `weather_code` (int, optional): WMO weather code (0-99)
- `is_day` (bool, optional): Currently unused, reserved for future use

**Returns:**

- `str`: Natural language weather description

## Usage Examples

### Basic Weather Lookup

```python
from get_weather import get_current_weather

# Get weather for a specific location
result = get_current_weather(
    city="New York",
    state_province="New York",
    country="United States",
    latitude=40.71,
    longitude=-74.01,
    temperature_unit="F"
)

print(f"Location: {result.location_label}")
print(f"Temperature: {result.temperature}°{result.temperature_unit}")
print(f"Weather: {result.weather_description}")
print(f"Full statement: {result.natural_language()}")
```

### Error Handling

```python
from get_weather import get_current_weather
from get_weather.exceptions import (
    NetworkError,
    RateLimitError,
    APIResponseError,
    InvalidLocationError,
    WeatherLookupError
)

try:
    result = get_current_weather(
        city="Invalid Location",
        state_province="Nowhere",
        country="Atlantis",
        latitude=999,  # Invalid latitude
        longitude=999,  # Invalid longitude
        temperature_unit="C"
    )
except InvalidLocationError as e:
    print(f"Invalid coordinates: {e}")
except NetworkError as e:
    print(f"Network problem: {e}")
except RateLimitError as e:
    print(f"Rate limited: {e}")
except APIResponseError as e:
    print(f"API problem: {e}")
except WeatherLookupError as e:
    print(f"Weather lookup failed: {e}")
```

### Fahrenheit Temperature

```python
result = get_current_weather(
    city="Miami",
    state_province="Florida",
    country="United States",
    latitude=25.76,
    longitude=-80.19,
    temperature_unit="F"
)

print(result.natural_language())
# Output: "Currently in Miami, Florida it is 85 degrees Fahrenheit with clear skies."
```

### Accessing Raw Data

```python
result = get_current_weather(
    city="Tokyo",
    state_province=None,
    country="Japan",
    latitude=35.68,
    longitude=139.69,
    temperature_unit="C"
)

# Access raw API response for advanced usage
raw_data = result.raw
print(f"Raw API keys: {list(raw_data.keys())}")
print(f"Current data: {raw_data.get('current', {})}")
```

## WMO Weather Codes

The module uses World Meteorological Organization (WMO) weather codes:

| Code Range | Description |
|------------|-------------|
| 0-3 | Cloud cover (clear to overcast) |
| 45, 48 | Fog |
| 51-55 | Drizzle (light to dense) |
| 56, 57 | Freezing drizzle |
| 61-65 | Rain (light to heavy) |
| 66, 67 | Freezing rain |
| 71-75 | Snow (light to heavy) |
| 77 | Snow grains |
| 80-82 | Rain showers (light to violent) |
| 85, 86 | Snow showers (light to heavy) |
| 95-99 | Thunderstorm (with/without hail) |

```python
from get_weather import weather_code_to_description

# Convert specific weather codes
print(weather_code_to_description(0))   # "with clear skies"
print(weather_code_to_description(63))  # "with moderate rain"
print(weather_code_to_description(95))  # "with a thunderstorm"
```

## API Information

- **Service**: Open-Meteo Weather API
- **Endpoint**: https://api.open-meteo.com/v1/forecast
- **Authentication**: None (free public API)
- **Rate Limits**: None specified (reasonable usage expected)
- **Data Source**: European Centre for Medium-Range Weather Forecasts (ECMWF)
- **Coverage**: Global weather data

## Dependencies

- `requests`: HTTP client library for API calls
- `dataclasses`: Data structure definitions (Python 3.7+)
- `typing`: Type hints (Python 3.5+)

## Error Handling Strategy

The module provides granular error handling to help you handle different failure scenarios appropriately:

1. **NetworkError**: Handle connectivity issues, timeouts, DNS failures
2. **RateLimitError**: Implement backoff/retry logic for rate limiting
3. **APIResponseError**: Handle server errors and malformed responses
4. **InvalidLocationError**: Validate user input coordinates
5. **WeatherLookupError**: Catch-all for weather-related issues

## Text-to-Speech Optimization

This module is specifically designed for text-to-speech applications:

- Natural language phrasing that flows well when spoken
- Temperature formatting removes unnecessary decimal points ("15" instead of "15.0")
- Weather descriptions use appropriate conjunctions ("with", "and")
- Concise location labels for clear speech output

## Integration Examples

### Integration with Location Services

```python
from get_location import PostalLookup
from get_weather import get_current_weather

# First get location from postal code
location_lookup = PostalLookup()
location = location_lookup.lookup("90210", "US")

if location:
    # Then get weather for that location
    weather = get_current_weather(
        city=location["city"],
        state_province=location["state_province"],
        country=location["country"],
        latitude=location["latitude"],
        longitude=location["longitude"],
        temperature_unit="F"
    )
    print(weather.natural_language())
```

### Batch Processing with Error Handling

```python
import time
from get_weather import get_current_weather
from get_weather.exceptions import RateLimitError

locations = [
    {"city": "New York", "lat": 40.71, "lon": -74.01},
    {"city": "London", "lat": 51.51, "lon": -0.13},
    {"city": "Tokyo", "lat": 35.68, "lon": 139.69},
]

for location in locations:
    try:
        weather = get_current_weather(
            city=location["city"],
            state_province=None,
            country=None,
            latitude=location["lat"],
            longitude=location["lon"],
            temperature_unit="C"
        )
        print(f"{location['city']}: {weather.natural_language()}")
    except RateLimitError:
        print(f"Rate limited for {location['city']}, waiting...")
        time.sleep(1)
    except Exception as e:
        print(f"Error getting weather for {location['city']}: {e}")
    
    # Be respectful of the free API
    time.sleep(0.5)
```

## Contributing

This module is part of the AllStarLink ASL Weather Announce project. For bug reports, feature requests, or contributions, please refer to the main project repository.

## License

This project is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License (CC BY-NC-SA 4.0).

This means you are free to:

- **Share** — copy and redistribute the material in any medium or format
- **Adapt** — remix, transform, and build upon the material

Under the following terms:

- **Attribution** — You must give appropriate credit, provide a link to the license, and indicate if changes were made.
- **NonCommercial** — You may not use the material for commercial purposes.
- **ShareAlike** — If you remix, transform, or build upon the material, you must distribute your contributions under the same license as the original.

See the [LICENSE](../LICENSE) file for the full license text.
