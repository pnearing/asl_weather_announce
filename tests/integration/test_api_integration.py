"""
Integration tests with mocked APIs.

These tests verify the end-to-end flow of the application with mocked external APIs.
They test the integration between location lookup and weather retrieval.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from asl_weather.get_location import PostalLookup
from asl_weather.get_location.exceptions import NetworkError, RateLimitError
from asl_weather.get_weather import get_current_weather
from asl_weather.get_weather.exceptions import WeatherLookupError

class TestLocationToWeatherFlow:
    """Integration tests for the complete location → weather flow."""

    @pytest.fixture
    def mock_zippopotam_response(self):
        """Mock successful Zippopotam response."""
        return {
            "country": "Canada",
            "country abbreviation": "CA",
            "places": [{
                "place name": "London",
                "state": "Ontario",
                "latitude": "42.9834",
                "longitude": "-81.2330",
            }]
        }

    @pytest.fixture
    def mock_open_meteo_response(self):
        """Mock successful Open-Meteo response."""
        return {
            "current": {
                "temperature_2m": 15.5,
                "weather_code": 1,
                "is_day": 1,
            }
        }

    def test_complete_flow_postal_to_weather(
        self, mock_zippopotam_response, mock_open_meteo_response
    ):
        """Test complete flow from postal code to weather announcement."""
        lookup = PostalLookup()

        # Mock Zippopotam response
        mock_zip_response = Mock()
        mock_zip_response.status_code = 200
        mock_zip_response.json.return_value = mock_zippopotam_response

        # Mock Open-Meteo response
        mock_weather_response = Mock()
        mock_weather_response.status_code = 200
        mock_weather_response.json.return_value = mock_open_meteo_response

        with patch('asl_weather.get_location.postal_lookup.requests.Session') as mock_session_class:
            mock_session = MagicMock()
            # Return different responses for different URLs
            def side_effect(*args, **kwargs):
                url = args[0] if args else kwargs.get('url', '')
                if 'zippopotam' in url:
                    return mock_zip_response
                elif 'open-meteo' in url:
                    return mock_weather_response
                return Mock()

            mock_session.get.side_effect = side_effect
            mock_session_class.return_value = mock_session

            # Step 1: Get location from postal code
            location = lookup.lookup("N6A3K7", "CA")
            assert location is not None
            assert location["city"] == "London"
            assert location["state_province"] == "Ontario"

            # Step 2: Get weather from location coordinates
            weather = get_current_weather(
                city=location["city"],
                state_province=location["state_province"],
                country=location["country"],
                latitude=location["latitude"],
                longitude=location["longitude"],
                temperature_unit="C",
            )

            # Step 3: Verify weather result
            assert weather.city == "London"
            assert weather.temperature == 15.5
            assert weather.weather_code == 1

            # # Step 4: Verify natural language output
            # announcement = weather.natural_language()
            # assert "London, Ontario" in announcement
            # assert "15.5 degrees Celsius" in announcement

    def test_flow_with_nominatim_fallback(
        self, mock_zippopotam_response, mock_open_meteo_response
    ):
        """Test flow when Zippopotam fails and Nominatim is used."""
        lookup = PostalLookup()
        lookup._cache = {}  # Clear any cached data from disk

        # Zippopotam fails (404)
        mock_zip_response = Mock()
        mock_zip_response.status_code = 404

        # Nominatim succeeds
        mock_nominatim_response = Mock()
        mock_nominatim_response.status_code = 200
        mock_nominatim_response.json.return_value = [{
            "lat": "42.9834",
            "lon": "-81.2330",
            "address": {
                "city": "London",
                "state": "Ontario",
                "country": "Canada",
                "country_code": "ca",
            }
        }]

        # Weather succeeds
        mock_weather_response = Mock()
        mock_weather_response.status_code = 200
        mock_weather_response.json.return_value = mock_open_meteo_response

        with patch('asl_weather.get_location.postal_lookup.requests.Session') as mock_session_class:
            mock_session = MagicMock()

            def side_effect(*args, **kwargs):
                url = args[0] if args else kwargs.get('url', '')
                if 'zippopotam' in url:
                    return mock_zip_response
                elif 'nominatim' in url and 'reverse' not in url:
                    return mock_nominatim_response
                elif 'open-meteo' in url:
                    return mock_weather_response
                return Mock()

            mock_session.get.side_effect = side_effect
            mock_session_class.return_value = mock_session

            # Location lookup should fallback to Nominatim
            location = lookup.lookup("N6A3K7", "CA")
            assert location is not None
            assert location["source"] == "nominatim"

            # Weather should work normally
            weather = get_current_weather(
                city=location["city"],
                state_province=location["state_province"],
                country=location["country"],
                latitude=location["latitude"],
                longitude=location["longitude"],
            )

            assert weather.city == "London"

    def test_flow_both_location_services_fail(self):
        """Test flow when both location services fail."""
        lookup = PostalLookup()

        # Both services fail
        mock_fail_response = Mock()
        mock_fail_response.status_code = 500

        with patch('asl_weather.get_location.postal_lookup.requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session.get.return_value = mock_fail_response
            mock_session_class.return_value = mock_session

            # Location lookup should return None
            location = lookup.lookup("INVALID", "XX")
            assert location is None


class TestReverseGeocodingFlow:
    """Integration tests for reverse geocoding flow."""

    def test_reverse_lookup_then_weather(self):
        """Test reverse geocoding followed by weather lookup."""
        lookup = PostalLookup()

        # Nominatim reverse geocoding response
        mock_reverse_response = Mock()
        mock_reverse_response.status_code = 200
        mock_reverse_response.json.return_value = {
            "address": {
                "city": "Toronto",
                "state": "Ontario",
                "country": "Canada",
                "country_code": "ca",
            }
        }

        # Weather response
        mock_weather_response = Mock()
        mock_weather_response.status_code = 200
        mock_weather_response.json.return_value = {
            "current": {
                "temperature_2m": 22.0,
                "weather_code": 0,
                "is_day": 1,
            }
        }

        with patch('asl_weather.get_location.postal_lookup.requests.Session') as mock_session_class:
            mock_session = MagicMock()

            def side_effect(*args, **kwargs):
                url = args[0] if args else kwargs.get('url', '')
                if 'reverse' in url:
                    return mock_reverse_response
                elif 'open-meteo' in url:
                    return mock_weather_response
                return Mock()

            mock_session.get.side_effect = side_effect
            mock_session_class.return_value = mock_session

            # Reverse geocode coordinates
            location = lookup.reverse_lookup(43.6532, -79.3832)
            assert location["city"] == "Toronto"

            # Get weather for the location
            weather = get_current_weather(
                city=location["city"],
                state_province=location["state_province"],
                country=location["country"],
                latitude=location["latitude"],
                longitude=location["longitude"],
            )

            assert weather.city == "Toronto"
            assert weather.temperature == 22.0


class TestErrorHandlingIntegration:
    """Integration tests for error handling across modules."""

    def test_network_error_propagation(self):
        """Test that network errors are properly propagated."""
        lookup = PostalLookup()
        lookup._cache = {}  # Clear any cached data from disk

        with patch('asl_weather.get_location.postal_lookup.requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session.get.side_effect = requests.exceptions.ConnectionError("No connection")
            mock_session_class.return_value = mock_session

            # Both modules should raise NetworkError
            with pytest.raises(NetworkError):
                lookup.lookup("N6A3K7", "CA")

    def test_rate_limit_handling(self):
        """Test that rate limits are handled across services."""
        lookup = PostalLookup()
        lookup._cache = {}  # Clear any cached data from disk

        mock_rate_limit_response = Mock()
        mock_rate_limit_response.status_code = 429

        with patch('asl_weather.get_location.postal_lookup.requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session.get.return_value = mock_rate_limit_response
            mock_session_class.return_value = mock_session

            # Should raise RateLimitError from both location services
            with pytest.raises(RateLimitError):
                lookup.lookup("N6A3K7", "CA")


class TestCachingIntegration:
    """Integration tests for caching behavior."""

    def test_cached_location_avoids_api_calls(self):
        """Test that cached locations don't trigger API calls."""
        lookup = PostalLookup()

        # Pre-populate cache
        cached_data = {
            "city": "London",
            "state_province": "Ontario",
            "country": "Canada",
            "latitude": 42.98,
            "longitude": -81.25,
        }
        lookup._cache = {"N6A3K7:CA": cached_data}

        # Mock to verify no API calls are made
        with patch('asl_weather.get_location.postal_lookup.requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            # Should return cached data without API calls
            result = lookup.lookup("N6A3K7", "CA")
            assert result == cached_data
            mock_session.get.assert_not_called()

    def test_weather_no_caching(self):
        """Test that weather API always makes requests (no caching)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "current": {
                "temperature_2m": 15.0,
                "weather_code": 0,
                "is_day": 1,
            }
        }

        with patch('asl_weather.get_location.postal_lookup.requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session.get.return_value = mock_response
            mock_session_class.return_value = mock_session

            # Make multiple calls
            get_current_weather(
                city="London", state_province="Ontario", country="Canada",
                latitude=42.98, longitude=-81.25,
            )
            get_current_weather(
                city="London", state_province="Ontario", country="Canada",
                latitude=42.98, longitude=-81.25,
            )

            # Should have made 2 API calls
            assert mock_session.get.call_count == 2


class TestUSLocations:
    """Integration tests for US locations."""

    def test_us_zip_code_flow(self):
        """Test complete flow with US ZIP code."""
        lookup = PostalLookup()

        mock_zip_response = Mock()
        mock_zip_response.status_code = 200
        mock_zip_response.json.return_value = {
            "country": "United States",
            "country abbreviation": "US",
            "places": [{
                "place name": "Beverly Hills",
                "state": "California",
                "latitude": "34.0901",
                "longitude": "-118.4065",
            }]
        }

        mock_weather_response = Mock()
        mock_weather_response.status_code = 200
        mock_weather_response.json.return_value = {
            "current": {
                "temperature_2m": 72.0,
                "weather_code": 0,
                "is_day": 1,
            }
        }

        with patch('asl_weather.get_location.postal_lookup.requests.Session') as mock_session_class:
            mock_session = MagicMock()

            def side_effect(*args, **kwargs):
                url = args[0] if args else kwargs.get('url', '')
                if 'zippopotam' in url:
                    return mock_zip_response
                elif 'open-meteo' in url:
                    return mock_weather_response
                return Mock()

            mock_session.get.side_effect = side_effect
            mock_session_class.return_value = mock_session

            location = lookup.lookup("90210", "US")
            assert location["city"] == "Beverly Hills"
            assert location["state_province"] == "California"

            weather = get_current_weather(
                city=location["city"],
                state_province=location["state_province"],
                country=location["country"],
                latitude=location["latitude"],
                longitude=location["longitude"],
                temperature_unit="F",
            )

            assert weather.city == "Beverly Hills"


class TestEuropeanLocations:
    """Integration tests for European locations."""

    def test_uk_postal_code_flow(self):
        """Test complete flow with UK postal code."""
        lookup = PostalLookup()

        mock_zip_response = Mock()
        mock_zip_response.status_code = 200
        mock_zip_response.json.return_value = {
            "country": "United Kingdom",
            "country abbreviation": "GB",
            "places": [{
                "place name": "London",
                "state": "England",
                "latitude": "51.5074",
                "longitude": "-0.1278",
            }]
        }

        mock_weather_response = Mock()
        mock_weather_response.status_code = 200
        mock_weather_response.json.return_value = {
            "current": {
                "temperature_2m": 12.5,
                "weather_code": 3,
                "is_day": 1,
            }
        }

        with patch('asl_weather.get_location.postal_lookup.requests.Session') as mock_session_class:
            mock_session = MagicMock()

            def side_effect(*args, **kwargs):
                url = args[0] if args else kwargs.get('url', '')
                if 'zippopotam' in url:
                    return mock_zip_response
                elif 'open-meteo' in url:
                    return mock_weather_response
                return Mock()

            mock_session.get.side_effect = side_effect
            mock_session_class.return_value = mock_session

            location = lookup.lookup("SW1A 1AA", "GB")
            assert location["city"] == "London"

            weather = get_current_weather(
                city=location["city"],
                state_province=location["state_province"],
                country=location["country"],
                latitude=location["latitude"],
                longitude=location["longitude"],
            )

            assert weather.weather_code == 3  # Overcast
