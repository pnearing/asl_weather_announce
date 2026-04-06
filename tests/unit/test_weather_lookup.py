"""
Unit tests for weather_lookup module.

These tests cover weather data parsing, API interactions (mocked), and
natural language formatting.
"""

import pytest
from unittest.mock import Mock, patch
import requests

from get_weather.weather_lookup import (
    get_current_weather,
    CurrentWeatherResult,
    weather_code_to_description,
)
from get_weather.exceptions import (
    NetworkError,
    RateLimitError,
    APIResponseError,
    InvalidLocationError,
)


class TestCurrentWeatherResult:
    """Tests for the CurrentWeatherResult dataclass."""

    @pytest.fixture
    def sample_result(self):
        """Create a sample weather result for testing."""
        return CurrentWeatherResult(
            city="London",
            state_province="Ontario",
            country="Canada",
            latitude=42.98,
            longitude=-81.25,
            temperature=15.0,
            temperature_unit="C",
            weather_code=0,
            weather_description="clear skies",
            is_day=True,
            raw={},
        )

    # def test_location_label_with_state(self, sample_result):
    #     """Test location_label property with state."""
    #     assert sample_result.location_label == "London, Ontario"

    # def test_location_label_without_state(self):
    #     """Test location_label property without state."""
    #     result = CurrentWeatherResult(
    #         city="London",
    #         state_province=None,
    #         country="UK",
    #         latitude=51.5,
    #         longitude=-0.1,
    #         temperature=12.0,
    #         temperature_unit="C",
    #         weather_code=1,
    #         weather_description="mostly clear",
    #         is_day=True,
    #         raw={},
    #     )
    #     assert result.location_label == "London"

    # def test_natural_language_celsius(self, sample_result):
    #     """Test natural language output in Celsius."""
    #     text = sample_result.natural_language()
    #     assert "Currently in London, Ontario it is" in text
    #     assert "15 degrees Celsius" in text
    #     assert "clear skies" in text

    # def test_natural_language_fahrenheit(self):
    #     """Test natural language output in Fahrenheit."""
    #     result = CurrentWeatherResult(
    #         city="New York",
    #         state_province="NY",
    #         country="USA",
    #         latitude=40.7,
    #         longitude=-74.0,
    #         temperature=68.5,
    #         temperature_unit="F",
    #         weather_code=2,
    #         weather_description="partly cloudy",
    #         is_day=True,
    #         raw={},
    #     )
    #     text = result.natural_language()
    #     assert "68.5 degrees Fahrenheit" in text

    # def test_natural_language_decimal_removal(self):
    #     """Test that .0 decimals are removed in output."""
    #     result = CurrentWeatherResult(
    #         city="Test",
    #         state_province=None,
    #         country=None,
    #         latitude=0.0,
    #         longitude=0.0,
    #         temperature=20.0,
    #         temperature_unit="C",
    #         weather_code=0,
    #         weather_description="clear skies",
    #         is_day=True,
    #         raw={},
    #     )
    #     # 20.0 should become "20"
    #     text = result.natural_language()
    #     assert "20 degrees Celsius" in text
    #     assert "20.0" not in text


class TestWeatherCodeToDescription:
    """Tests for the weather_code_to_description function."""

    def test_clear_sky(self):
        """Test code 0 (clear sky)."""
        assert weather_code_to_description(0) == "clear skies"

    def test_mostly_clear(self):
        """Test code 1 (mostly clear)."""
        assert weather_code_to_description(1) == "mostly clear"

    def test_partly_cloudy(self):
        """Test code 2 (partly cloudy)."""
        assert weather_code_to_description(2) == "partly cloudy"

    def test_overcast(self):
        """Test code 3 (overcast)."""
        assert weather_code_to_description(3) == "overcast"

    def test_foggy(self):
        """Test code 45 (foggy)."""
        assert weather_code_to_description(45) == "foggy"

    def test_light_rain(self):
        """Test code 61 (light rain)."""
        assert weather_code_to_description(61) == "light rain"

    def test_moderate_rain(self):
        """Test code 63 (moderate rain)."""
        assert weather_code_to_description(63) == "moderate rain"

    def test_thunderstorm(self):
        """Test code 95 (thunderstorm)."""
        assert weather_code_to_description(95) == "thunderstorm"

    def test_light_snow(self):
        """Test code 71 (light snow)."""
        assert weather_code_to_description(71) == "light snow"

    def test_none_code(self):
        """Test None weather code."""
        result = weather_code_to_description(None)
        assert "unavailable" in result

    def test_invalid_code(self):
        """Test invalid weather code."""
        result = weather_code_to_description(999)
        assert "unrecognized" in result

    def test_non_numeric_code(self):
        """Test non-numeric weather code."""
        result = weather_code_to_description("invalid")
        assert "unrecognized" in result


# class TestFormatTemp:
#     """Tests for the _format_temp helper function."""

#     def test_integer_temperature(self):
#         """Test that whole numbers lose the decimal."""
#         assert _format_temp(15.0) == "15"
#         assert _format_temp(-5.0) == "-5"
#         assert _format_temp(0.0) == "0"

#     def test_decimal_temperature(self):
#         """Test that decimals are preserved."""
#         assert _format_temp(15.5) == "15.5"
#         assert _format_temp(-5.7) == "-5.7"
#         assert _format_temp(0.1) == "0.1"

#     def test_rounding(self):
#         """Test that values are rounded to 1 decimal place."""
#         assert _format_temp(15.04) == "15"  # Rounds to 15.0
#         assert _format_temp(15.06) == "15.1"  # Rounds to 15.1


class TestGetCurrentWeatherInputValidation:
    """Tests for input validation in get_current_weather."""

    def test_invalid_city(self):
        """Test that invalid city raises ValueError."""
        with pytest.raises(ValueError, match="city must be a non-empty string"):
            get_current_weather(
                city="",
                state_province="Ontario",
                country="Canada",
                latitude=42.98,
                longitude=-81.25,
            )

    def test_invalid_temperature_unit(self):
        """Test that invalid temperature unit raises ValueError."""
        with pytest.raises(ValueError, match='temperature_unit must be "C" or "F"'):
            get_current_weather(
                city="London",
                state_province="Ontario",
                country="Canada",
                latitude=42.98,
                longitude=-81.25,
                temperature_unit="K",
            )

    def test_non_numeric_latitude(self):
        """Test that non-numeric latitude raises InvalidLocationError."""
        with pytest.raises(InvalidLocationError):
            get_current_weather(
                city="London",
                state_province="Ontario",
                country="Canada",
                latitude="invalid",
                longitude=-81.25,
            )

    def test_latitude_out_of_range(self):
        """Test that out-of-range latitude raises InvalidLocationError."""
        with pytest.raises(InvalidLocationError, match="latitude.*out of valid range"):
            get_current_weather(
                city="London",
                state_province="Ontario",
                country="Canada",
                latitude=91,
                longitude=-81.25,
            )
        with pytest.raises(InvalidLocationError, match="latitude.*out of valid range"):
            get_current_weather(
                city="London",
                state_province="Ontario",
                country="Canada",
                latitude=-91,
                longitude=-81.25,
            )

    def test_longitude_out_of_range(self):
        """Test that out-of-range longitude raises InvalidLocationError."""
        with pytest.raises(InvalidLocationError, match="longitude.*out of valid range"):
            get_current_weather(
                city="London",
                state_province="Ontario",
                country="Canada",
                latitude=42.98,
                longitude=181,
            )


class TestGetCurrentWeatherAPIMocking:
    """Tests for get_current_weather with mocked API responses."""

    @pytest.fixture
    def mock_success_response(self):
        """Create a mock successful API response."""
        mock = Mock()
        mock.status_code = 200
        mock.json.return_value = {
            "current": {
                "temperature_2m": 15.5,
                "weather_code": 1,
                "is_day": 1,
            }
        }
        return mock

    def test_successful_weather_fetch(self, mock_success_response):
        """Test successful weather fetch."""
        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session.get.return_value = mock_success_response
            mock_session_class.return_value = mock_session

            result = get_current_weather(
                city="London",
                state_province="Ontario",
                country="Canada",
                latitude=42.98,
                longitude=-81.25,
                temperature_unit="C",
            )

        assert result.city == "London"
        assert result.temperature == 15.5
        assert result.weather_code == 1
        assert result.is_day is True

    def test_celsius_temperature_unit(self, mock_success_response):
        """Test that Celsius temperature unit is passed correctly."""
        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session.get.return_value = mock_success_response
            mock_session_class.return_value = mock_session

            get_current_weather(
                city="London",
                state_province="Ontario",
                country="Canada",
                latitude=42.98,
                longitude=-81.25,
                temperature_unit="C",
            )

            # Check that celsius was passed to API
            call_args = mock_session.get.call_args
            assert call_args[1]["params"]["temperature_unit"] == "celsius"

    def test_fahrenheit_temperature_unit(self, mock_success_response):
        """Test that Fahrenheit temperature unit is passed correctly."""
        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session.get.return_value = mock_success_response
            mock_session_class.return_value = mock_session

            get_current_weather(
                city="London",
                state_province="Ontario",
                country="Canada",
                latitude=42.98,
                longitude=-81.25,
                temperature_unit="F",
            )

            # Check that fahrenheit was passed to API
            call_args = mock_session.get.call_args
            assert call_args[1]["params"]["temperature_unit"] == "fahrenheit"

    def test_missing_current_data(self):
        """Test that missing 'current' data raises APIResponseError."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # Missing 'current' key

        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session.get.return_value = mock_response
            mock_session_class.return_value = mock_session

            with pytest.raises(APIResponseError, match="missing 'current' data"):
                get_current_weather(
                    city="London",
                    state_province="Ontario",
                    country="Canada",
                    latitude=42.98,
                    longitude=-81.25,
                )

    def test_missing_temperature_data(self):
        """Test that missing temperature raises APIResponseError."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "current": {
                "weather_code": 0,
                # Missing temperature_2m
            }
        }

        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session.get.return_value = mock_response
            mock_session_class.return_value = mock_session

            with pytest.raises(APIResponseError, match="missing temperature_2m"):
                get_current_weather(
                    city="London",
                    state_province="Ontario",
                    country="Canada",
                    latitude=42.98,
                    longitude=-81.25,
                )

    def test_none_weather_code(self):
        """Test handling of None weather code."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "current": {
                "temperature_2m": 15.0,
                "weather_code": None,
                "is_day": 1,
            }
        }

        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session.get.return_value = mock_response
            mock_session_class.return_value = mock_session

            result = get_current_weather(
                city="London",
                state_province="Ontario",
                country="Canada",
                latitude=42.98,
                longitude=-81.25,
            )

        assert result.weather_code is None


class TestGetCurrentWeatherNetworkErrors:
    """Tests for network error handling."""

    def test_timeout_error(self):
        """Test that timeout raises NetworkError."""
        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session.get.side_effect = requests.exceptions.Timeout("Request timed out")
            mock_session_class.return_value = mock_session

            with pytest.raises(NetworkError, match="timeout"):
                get_current_weather(
                    city="London",
                    state_province="Ontario",
                    country="Canada",
                    latitude=42.98,
                    longitude=-81.25,
                    timeout=0.001,
                )

    def test_connection_error(self):
        """Test that connection error raises NetworkError."""
        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session.get.side_effect = requests.exceptions.ConnectionError("Connection failed")
            mock_session_class.return_value = mock_session

            with pytest.raises(NetworkError, match="connection error"):
                get_current_weather(
                    city="London",
                    state_province="Ontario",
                    country="Canada",
                    latitude=42.98,
                    longitude=-81.25,
                )

    def test_rate_limit_error(self):
        """Test that 429 status raises RateLimitError."""
        mock_response = Mock()
        mock_response.status_code = 429
        # raise_for_status raises HTTPError which triggers the RequestException handler
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )

        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session.get.return_value = mock_response
            mock_session_class.return_value = mock_session

            with pytest.raises(RateLimitError):
                get_current_weather(
                    city="London",
                    state_province="Ontario",
                    country="Canada",
                    latitude=42.98,
                    longitude=-81.25,
                )

    def test_forbidden_error(self):
        """Test that 403 status raises RateLimitError."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )

        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session.get.return_value = mock_response
            mock_session_class.return_value = mock_session

            with pytest.raises(RateLimitError, match="access forbidden"):
                get_current_weather(
                    city="London",
                    state_province="Ontario",
                    country="Canada",
                    latitude=42.98,
                    longitude=-81.25,
                )

    def test_server_error(self):
        """Test that 5xx status raises APIResponseError."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )

        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session.get.return_value = mock_response
            mock_session_class.return_value = mock_session

            with pytest.raises(APIResponseError, match="server error"):
                get_current_weather(
                    city="London",
                    state_province="Ontario",
                    country="Canada",
                    latitude=42.98,
                    longitude=-81.25,
                )

    def test_invalid_json_response(self):
        """Test that invalid JSON raises APIResponseError."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session.get.return_value = mock_response
            mock_session_class.return_value = mock_session

            with pytest.raises(APIResponseError, match="Invalid JSON"):
                get_current_weather(
                    city="London",
                    state_province="Ontario",
                    country="Canada",
                    latitude=42.98,
                    longitude=-81.25,
                )


class TestRawDataPreservation:
    """Tests that raw API data is preserved in the result."""

    def test_raw_data_included(self):
        """Test that raw API response is included in result."""
        raw_response = {
            "current": {
                "temperature_2m": 20.0,
                "weather_code": 0,
                "is_day": 1,
            },
            "extra_field": "preserved",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = raw_response

        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session.get.return_value = mock_response
            mock_session_class.return_value = mock_session

            result = get_current_weather(
                city="London",
                state_province="Ontario",
                country="Canada",
                latitude=42.98,
                longitude=-81.25,
            )

        assert result.raw == raw_response
        assert result.raw["extra_field"] == "preserved"
