# Location Lookup Module

A Python module for postal code to location lookup using multiple geocoding services with comprehensive error handling and fallback mechanisms. Designed for applications that need to convert postal codes to geographic coordinates and location information.

## Features

- **Multiple API Services**: Uses Zippopotam.us (primary) and Nominatim OpenStreetMap (fallback)
- **Global Coverage**: Supports postal codes from many countries worldwide
- **Fallback Mechanism**: Automatic fallback to secondary service if primary fails
- **Comprehensive Error Handling**: Granular exception types for different failure scenarios
- **Coordinate Validation**: Safe conversion and validation of latitude/longitude data
- **Flexible Input**: Handles various postal code formats and country codes
- **Rate Limiting Awareness**: Built-in handling for API rate limits
- **No API Keys Required**: Uses free public APIs

## Installation

This module is part of the AllStarLink ASL Weather Announce package. Ensure you have the required dependencies:

```bash
pip install requests
```

## Quick Start

```python
from get_location import PostalLookup

# Basic usage
lookup = PostalLookup()
result = lookup.lookup("90210", "US")

if result:
    print(f"City: {result['city']}")
    print(f"State: {result['state_province']}")
    print(f"Country: {result['country']}")
    print(f"Coordinates: {result['latitude']}, {result['longitude']}")
    print(f"Source: {result['source']}")
else:
    print("Postal code not found")
```

## API Reference

### Main Class

#### `PostalLookup`

Main class for postal code location lookups with multiple API services and comprehensive error handling.

**Constructor Parameters:**
- `timeout` (float): Default timeout for requests in seconds (default: 10.0)
- `user_agent` (str): Default user agent for HTTP requests
- `logger` (logging.Logger, optional): Logger instance for debugging

**Methods:**

#### `lookup(postal_code, country_code, *, timeout=None, user_agent=None)`

Look up city and province/state from a postal code + 2-letter country code.

**Parameters:**
- `postal_code` (str): Postal code to lookup
- `country_code` (str): 2-letter ISO country code
- `timeout` (float, optional): Timeout override for this request
- `user_agent` (str, optional): User agent override for this request

**Returns:**
- `dict` or `None`: Dictionary with location data or None if not found

**Dictionary Structure:**
```python
{
    "postal_code": "90210",
    "country_code": "US", 
    "country": "United States",
    "city": "Beverly Hills",
    "state_province": "California",
    "latitude": 34.09,
    "longitude": -118.41,
    "source": "zippopotam"  # or "nominatim"
}
```

**Raises:**
- `ValueError`: Invalid input parameters
- `NetworkError`: Network connectivity issues
- `RateLimitError`: API rate limiting
- `APIResponseError`: Invalid API responses
- `PostalLookupError`: General postal lookup issues

#### Static Methods

#### `_safe_float(value)`

Safely convert value to float, returning None on failure.

**Parameters:**
- `value`: Value to convert (typically string or None)

**Returns:**
- `float` or `None`: Float value if conversion succeeds, None otherwise

## Usage Examples

### Basic Postal Code Lookup

```python
from get_location import PostalLookup

lookup = PostalLookup()

# US postal code
result = lookup.lookup("90210", "US")
if result:
    print(f"{result['city']}, {result['state_province']}, {result['country']}")
    print(f"Coordinates: {result['latitude']}, {result['longitude']}")

# Canadian postal code
result = lookup.lookup("N6A 3K7", "CA")
if result:
    print(f"{result['city']}, {result['state_province']}")
    print(f"Coordinates: {result['latitude']}, {result['longitude']}")
```

### Error Handling

```python
from get_location import PostalLookup
from get_location.exceptions import (
    NetworkError,
    RateLimitError, 
    APIResponseError,
    PostalLookupError
)

lookup = PostalLookup()

try:
    result = lookup.lookup("INVALID", "US")
except ValueError as e:
    print(f"Invalid input: {e}")
except NetworkError as e:
    print(f"Network problem: {e}")
except RateLimitError as e:
    print(f"Rate limited: {e}")
except APIResponseError as e:
    print(f"API problem: {e}")
except PostalLookupError as e:
    print(f"Lookup failed: {e}")
```

### Custom Timeout and User Agent

```python
lookup = PostalLookup(
    timeout=15.0,
    user_agent="my-app/1.0 (contact: me@example.com)"
)

result = lookup.lookup("SW1A 0AA", "GB")  # Buckingham Palace
if result:
    print(f"Found: {result['city']}, {result['country']}")
```

### Logging Integration

```python
import logging
from get_location import PostalLookup

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

lookup = PostalLookup(logger=logger)
result = lookup.lookup("10001", "US")  # New York City
```

### Batch Processing with Error Handling

```python
import time
from get_location import PostalLookup
from get_location.exceptions import RateLimitError

postal_codes = [
    ("90210", "US"),  # Beverly Hills
    ("10001", "US"),  # New York
    ("60601", "US"),  # Chicago
    ("N6A 3K7", "CA"), # London, Ontario
    ("SW1A 0AA", "GB"), # London, UK
]

lookup = PostalLookup()

for postal_code, country in postal_codes:
    try:
        result = lookup.lookup(postal_code, country)
        if result:
            print(f"{postal_code}: {result['city']}, {result['state_province']}")
        else:
            print(f"{postal_code}: Not found")
    except RateLimitError:
        print(f"Rate limited for {postal_code}, waiting...")
        time.sleep(2)
    except Exception as e:
        print(f"Error with {postal_code}: {e}")
    
    # Be respectful of free APIs
    time.sleep(1)
```

### Integration with Weather Services

```python
from get_location import PostalLookup
from get_weather import get_current_weather

# Get location from postal code, then weather
postal_lookup = PostalLookup()
location = postal_lookup.lookup("90210", "US")

if location:
    weather = get_current_weather(
        city=location["city"],
        state_province=location["state_province"],
        country=location["country"],
        latitude=location["latitude"],
        longitude=location["longitude"],
        temperature_unit="F"
    )
    print(f"Weather for {location['city']}: {weather.natural_language()}")
else:
    print("Location not found")
```

## API Services

### Primary Service: Zippopotam.us

- **Endpoint**: https://api.zippopotam.us
- **Coverage**: US and many other countries
- **Speed**: Fast and lightweight
- **Rate Limits**: None specified
- **Format**: Simple JSON response

**Example Response:**
```json
{
  "post code": "90210",
  "country": "United States", 
  "country abbreviation": "US",
  "places": [
    {
      "place name": "Beverly Hills",
      "longitude": "-118.4065",
      "latitude": "34.0901",
      "state": "California"
    }
  ]
}
```

### Fallback Service: Nominatim OpenStreetMap

- **Endpoint**: https://nominatim.openstreetmap.org
- **Coverage**: Global
- **Speed**: Slower but comprehensive
- **Rate Limits**: ~1 request per second recommended
- **Format**: Detailed JSON with address hierarchy

**Usage Policy**: Nominatim recommends no more than 1 request per second and requires proper User-Agent identification.

## Supported Countries

The module works with many countries, but coverage varies by service:

### Well-Supported Countries
- **United States** (US): Full coverage via Zippopotam.us
- **Canada** (CA): Full coverage via Zippopotam.us  
- **United Kingdom** (GB): Full coverage via Nominatim
- **Germany** (DE): Good coverage via both services
- **France** (FR): Good coverage via both services
- **Australia** (AU): Good coverage via both services
- **Japan** (JP): Good coverage via Nominatim

### Partial Coverage
Many other countries have partial coverage, primarily through Nominatim. The fallback mechanism ensures the best possible results.

## Error Handling Strategy

The module provides granular error handling for different failure scenarios:

1. **NetworkError**: Handle connectivity issues, timeouts, DNS failures
2. **RateLimitError**: Implement backoff/retry logic for rate limiting
3. **APIResponseError**: Handle server errors and malformed responses
4. **PostalLookupError**: Catch-all for postal lookup issues
5. **ValueError**: Invalid input parameters

### Fallback Behavior

- **Primary service failures** automatically trigger fallback to secondary service
- **Network errors, rate limits, and API errors** from primary service cause fallback
- **Only when both services fail** does the method raise an exception
- **When both services succeed but find no results**, the method returns None

## Performance Considerations

### Response Times
- **Zippopotam.us**: Typically 100-300ms
- **Nominatim**: Typically 500-2000ms (slower but more comprehensive)

### Rate Limiting
- **Zippopotam.us**: No explicit rate limits
- **Nominatim**: Recommend 1 request/second maximum
- **Batch operations**: Include delays between requests

### Caching
For production use, consider implementing caching to reduce API calls:
```python
import functools
import time

@functools.lru_cache(maxsize=1000)
def cached_lookup(postal_code, country):
    lookup = PostalLookup()
    return lookup.lookup(postal_code, country)
```

## Advanced Usage

### Custom User Agent

```python
lookup = PostalLookup(
    user_agent="my-company-app/2.0 (contact: support@mycompany.com)"
)
```

### Extended Timeout for Slow Networks

```python
lookup = PostalLookup(timeout=30.0)  # 30 second timeout
```

### Debug Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
lookup = PostalLookup()
```

### Handling Invalid Coordinates

```python
result = lookup.lookup("12345", "US")
if result:
    lat = result.get('latitude')
    lon = result.get('longitude')
    
    # Coordinates might be None if conversion failed
    if lat is not None and lon is not None:
        print(f"Valid coordinates: {lat}, {lon}")
    else:
        print("Invalid coordinates in response")
```

## Dependencies

- `requests`: HTTP client library for API calls
- `logging`: Python's logging framework (built-in)
- `typing`: Type hints (Python 3.5+)

## Integration Examples

### Flask Web Service

```python
from flask import Flask, request, jsonify
from get_location import PostalLookup
from get_location.exceptions import PostalLookupError

app = Flask(__name__)
lookup = PostalLookup()

@app.route('/api/lookup')
def lookup_postal():
    postal_code = request.args.get('postal_code')
    country = request.args.get('country_code')
    
    try:
        result = lookup.lookup(postal_code, country)
        if result:
            return jsonify(result)
        else:
            return jsonify({"error": "Postal code not found"}), 404
    except PostalLookupError as e:
        return jsonify({"error": str(e)}), 500
```

### Command Line Tool

```python
#!/usr/bin/env python3
import sys
from get_location import PostalLookup
from get_location.exceptions import PostalLookupError

def main():
    if len(sys.argv) != 3:
        print("Usage: python lookup.py <postal_code> <country_code>")
        sys.exit(1)
    
    postal_code, country = sys.argv[1], sys.argv[2]
    lookup = PostalLookup()
    
    try:
        result = lookup.lookup(postal_code, country)
        if result:
            print(f"Location: {result['city']}, {result['state_province']}")
            print(f"Country: {result['country']}")
            print(f"Coordinates: {result['latitude']}, {result['longitude']}")
            print(f"Source: {result['source']}")
        else:
            print(f"Postal code {postal_code} in {country} not found")
    except PostalLookupError as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Data Quality Notes

### Postal Code Formats
Different countries use different postal code formats:
- **US**: 5 digits (90210) or 9 digits with hyphen (90210-1234)
- **Canada**: 6 characters with space (N6A 3K7)
- **UK**: Variable length with space (SW1A 0AA)
- **Germany**: 5 digits (10115)

### Coordinate Precision
- **Zippopotam.us**: Typically 2-4 decimal places
- **Nominatim**: Typically 5-7 decimal places (more precise)

### Address Hierarchy
Nominatim provides detailed address hierarchy while Zippopotam.us provides basic city/state information.

## Contributing

This module is part of the AllStarLink ASL Weather Announce project. For bug reports, feature requests, or contributions, please refer to the main project repository.

## License

This module is released under the same license as the AllStarLink ASL Weather Announce project.
