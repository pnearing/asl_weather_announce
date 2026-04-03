from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal, Dict, Any
import requests

from .exceptions import WeatherLookupError


TemperatureUnit = Literal["C", "F"]


@dataclass
class CurrentWeatherResult:
    city: str
    state_province: Optional[str]
    country: Optional[str]
    latitude: float
    longitude: float
    temperature: float
    temperature_unit: TemperatureUnit
    weather_code: Optional[int]
    weather_description: str
    is_day: Optional[bool]
    raw: Dict[str, Any]

    @property
    def location_label(self) -> str:
        parts = [self.city]
        if self.state_province:
            parts.append(self.state_province)
        elif self.country:
            parts.append(self.country)
        return ", ".join(parts)

    def natural_language(self) -> str:
        unit_word = "Celsius" if self.temperature_unit == "C" else "Fahrenheit"
        temp_str = _format_temp(self.temperature)
        return (
            f"Currently in {self.location_label} it is "
            f"{temp_str} degrees {unit_word} and {self.weather_description}."
        )


def get_current_weather(
    *,
    city: str,
    state_province: Optional[str],
    country: Optional[str],
    latitude: float,
    longitude: float,
    temperature_unit: TemperatureUnit = "C",
    timeout: float = 10.0,
    user_agent: str = "weather-module/1.0 (contact: you@example.com)",
) -> CurrentWeatherResult:
    """
    Fetch current weather conditions using latitude/longitude.

    Parameters:
        city: Human-readable city name for output text.
        state_province: State or province name for output text.
        country: Country name for output text fallback.
        latitude: Decimal latitude.
        longitude: Decimal longitude.
        temperature_unit: "C" or "F".
        timeout: HTTP timeout in seconds.
        user_agent: User-Agent header for HTTP requests.

    Returns:
        CurrentWeatherResult

    Raises:
        ValueError: bad arguments
        WeatherLookupError: API/network/parsing issues
    """
    if not city or not isinstance(city, str):
        raise ValueError("city must be a non-empty string")

    if temperature_unit not in ("C", "F"):
        raise ValueError('temperature_unit must be "C" or "F"')

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError) as exc:
        raise ValueError("latitude and longitude must be numeric") from exc

    api_temp_unit = "celsius" if temperature_unit == "C" else "fahrenheit"

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        # Open-Meteo supports current weather variables directly.
        "current": "temperature_2m,weather_code,is_day",
        "temperature_unit": api_temp_unit,
    }

    session = requests.Session()
    session.headers.update({
        "User-Agent": user_agent,
        "Accept": "application/json",
    })

    try:
        response = session.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise WeatherLookupError(f"Failed to fetch weather data: {exc}") from exc
    except ValueError as exc:
        raise WeatherLookupError(f"Weather API returned invalid JSON: {exc}") from exc

    current = data.get("current")
    if not isinstance(current, dict):
        raise WeatherLookupError("Weather API response is missing 'current' data")

    temp = current.get("temperature_2m")
    if temp is None:
        raise WeatherLookupError("Weather API response is missing temperature_2m")

    weather_code = current.get("weather_code")
    is_day_raw = current.get("is_day")
    is_day = bool(is_day_raw) if is_day_raw is not None else None

    description = weather_code_to_description(weather_code, is_day=is_day)

    return CurrentWeatherResult(
        city=city.strip(),
        state_province=(state_province.strip() if state_province else None),
        country=(country.strip() if country else None),
        latitude=latitude,
        longitude=longitude,
        temperature=float(temp),
        temperature_unit=temperature_unit,
        weather_code=int(weather_code) if weather_code is not None else None,
        weather_description=description,
        is_day=is_day,
        raw=data,
    )


def weather_code_to_description(
    weather_code: Optional[int],
    *,
    is_day: Optional[bool] = None,
) -> str:
    """
    Convert Open-Meteo/WMO weather code to a natural-language description.
    """
    if weather_code is None:
        return "conditions unavailable"

    code_map = {
        0: "clear skies" if is_day else "clear skies tonight",
        1: "mostly clear" if is_day else "mostly clear tonight",
        2: "partly cloudy",
        3: "overcast",
        45: "foggy",
        48: "foggy with frost forming",
        51: "light drizzle",
        53: "moderate drizzle",
        55: "dense drizzle",
        56: "light freezing drizzle",
        57: "dense freezing drizzle",
        61: "light rain",
        63: "moderate rain",
        65: "heavy rain",
        66: "light freezing rain",
        67: "heavy freezing rain",
        71: "light snow",
        73: "moderate snow",
        75: "heavy snow",
        77: "snow grains",
        80: "light rain showers",
        81: "moderate rain showers",
        82: "violent rain showers",
        85: "light snow showers",
        86: "heavy snow showers",
        95: "a thunderstorm",
        96: "a thunderstorm with light hail",
        99: "a thunderstorm with heavy hail",
    }

    return code_map.get(int(weather_code), "unrecognized weather conditions")


def _format_temp(value: float) -> str:
    """
    Format temperature cleanly:
    10.0 -> "10"
    10.4 -> "10.4"
    """
    rounded_1 = round(value, 1)
    if rounded_1.is_integer():
        return str(int(rounded_1))
    return str(rounded_1)


if __name__ == "__main__":
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

    print("Testing Miami, Florida... in Fahrenheit")
    result = get_current_weather(
    city="Miami",
    state_province="Florida",
    country="United States",
    latitude=25.7617,
    longitude=-80.1918,
    temperature_unit="F",
    )

    print(result.natural_language())
