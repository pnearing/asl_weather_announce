#!/usr/bin/env python3
"""
Example usage of the get_weather package.

This script demonstrates how to use the weather lookup functionality
to fetch current weather conditions for different locations.
"""

from get_weather import get_current_weather, CurrentWeatherResult

def main():
    print("Testing London, Ontario... in Celsius")
    result = get_current_weather(
        city="London",
        state_province="Ontario",
        country="Canada",
        latitude=42.9834,
        longitude=-81.233,
        temperature_unit="C",
    )

    print(result.natural_language())
    print(result.temperature)
    print(result.weather_description)

    print("\nTesting Miami, Florida... in Fahrenheit")
    result = get_current_weather(
        city="Miami",
        state_province="Florida",
        country="United States",
        latitude=25.7617,
        longitude=-80.1918,
        temperature_unit="F",
    )

    print(result.natural_language())

if __name__ == "__main__":
    main()
