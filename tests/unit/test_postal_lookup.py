"""
Unit tests for postal_lookup module.

These tests cover the PostalLookup class including caching, coordinate handling,
and API interactions (mocked).
"""

import json
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import requests

from asl_weather.get_location.postal_lookup import PostalLookup
from asl_weather.get_location.exceptions import NetworkError, RateLimitError, APIResponseError


class TestPostalLookupInitialization:
    """Tests for PostalLookup initialization and configuration."""

    def test_default_initialization(self):
        """Test default initialization values."""
        lookup = PostalLookup()
        assert lookup.timeout == 10.0
        assert "postal-lookup" in lookup.user_agent

    def test_custom_initialization(self):
        """Test initialization with custom values."""
        lookup = PostalLookup(timeout=15.0, user_agent="custom-agent")
        assert lookup.timeout == 15.0
        assert lookup.user_agent == "custom-agent"

    def test_logger_initialization(self):
        """Test that logger is properly initialized."""
        import logging
        custom_logger = logging.getLogger("test_logger")
        lookup = PostalLookup(logger=custom_logger)
        assert lookup.logger is custom_logger


class TestCacheDirectory:
    """Tests for cache directory selection."""

    def test_root_user_cache_dir(self):
        """Test that root user gets system cache directory."""
        with patch('os.geteuid', return_value=0):
            lookup = PostalLookup()
            assert lookup._cache_dir == Path("/var/cache/asl_weather_announce")

    def test_non_root_user_cache_dir(self):
        """Test that non-root user gets home cache directory."""
        with patch('os.geteuid', return_value=1000):
            lookup = PostalLookup()
            expected = Path.home() / ".cache" / "asl_weather_announce"
            assert lookup._cache_dir == expected


class TestCacheOperations:
    """Tests for cache loading and saving operations."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary directory for cache testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_load_nonexistent_cache(self, temp_cache_dir):
        """Test loading cache when file doesn't exist."""
        lookup = PostalLookup()
        lookup._cache_dir = Path(temp_cache_dir)
        lookup._cache_file = Path(temp_cache_dir) / "postal_cache.json"
        lookup._cache = {}
        lookup._load_cache()
        assert lookup._cache == {}

    def test_load_existing_cache(self, temp_cache_dir):
        """Test loading existing cache from disk."""
        cache_file = Path(temp_cache_dir) / "postal_cache.json"
        test_data = {"N6A3K7:CA": {"city": "London", "country": "Canada"}}
        with open(cache_file, "w") as f:
            json.dump(test_data, f)

        lookup = PostalLookup()
        lookup._cache_dir = Path(temp_cache_dir)
        lookup._cache_file = cache_file
        lookup._load_cache()
        assert lookup._cache == test_data

    def test_save_and_load_cache(self, temp_cache_dir):
        """Test saving and then loading cache."""
        lookup = PostalLookup()
        lookup._cache_dir = Path(temp_cache_dir)
        lookup._cache_file = Path(temp_cache_dir) / "postal_cache.json"
        lookup._cache = {"TEST:US": {"city": "Test City"}}
        lookup._save_cache()

        # Create new instance and load
        lookup2 = PostalLookup()
        lookup2._cache_dir = Path(temp_cache_dir)
        lookup2._cache_file = Path(temp_cache_dir) / "postal_cache.json"
        lookup2._load_cache()
        assert lookup2._cache == {"TEST:US": {"city": "Test City"}}


class TestSafeFloat:
    """Tests for the _safe_float static method."""

    def test_valid_float_strings(self):
        """Test conversion of valid float strings."""
        assert PostalLookup._safe_float("42.98") == 42.98
        assert PostalLookup._safe_float("-81.25") == -81.25
        assert PostalLookup._safe_float("0") == 0.0

    def test_numeric_values(self):
        """Test conversion of numeric values."""
        assert PostalLookup._safe_float(42.98) == 42.98
        assert PostalLookup._safe_float(-81) == -81.0

    def test_invalid_values(self):
        """Test that invalid values return None."""
        assert PostalLookup._safe_float(None) is None
        assert PostalLookup._safe_float("invalid") is None
        assert PostalLookup._safe_float("") is None


class TestInputValidation:
    """Tests for input parameter validation."""

    @patch.object(PostalLookup, '_load_cache')
    def test_invalid_postal_code(self, mock_load):
        """Test validation of invalid postal code."""
        lookup = PostalLookup()
        with pytest.raises(ValueError, match="postal_code must be a non-empty string"):
            lookup.lookup("", "US")
        with pytest.raises(ValueError, match="postal_code must be a non-empty string"):
            lookup.lookup(None, "US")

    @patch.object(PostalLookup, '_load_cache')
    def test_invalid_country_code(self, mock_load):
        """Test validation of invalid country code."""
        lookup = PostalLookup()
        with pytest.raises(ValueError, match="country_code must be a non-empty string"):
            lookup.lookup("12345", "")
        with pytest.raises(ValueError, match="country_code must be a non-empty string"):
            lookup.lookup("12345", None)

    @patch.object(PostalLookup, '_load_cache')
    def test_unnormalizable_country_code(self, mock_load):
        """Test handling of country codes that can't be normalized."""
        lookup = PostalLookup()
        with pytest.raises(ValueError, match="is not a valid country code"):
            lookup.lookup("12345", "INVALID")


class TestCacheLookup:
    """Tests for cache hit behavior."""

    def test_cache_hit_returns_cached_data(self):
        """Test that cache hits return cached data without API call."""
        lookup = PostalLookup()
        cached_data = {
            "city": "London",
            "state_province": "Ontario",
            "country": "Canada",
            "latitude": 42.98,
            "longitude": -81.25,
        }
        lookup._cache = {"N6A3K7:CA": cached_data}

        with patch.object(lookup, '_lookup_zippopotam') as mock_zip:
            result = lookup.lookup("N6A3K7", "CA")
            mock_zip.assert_not_called()  # Should not make API call
            assert result == cached_data

    def test_cache_miss_calls_api(self):
        """Test that cache misses trigger API calls."""
        lookup = PostalLookup()
        lookup._cache = {}

        mock_result = {
            "city": "London",
            "state_province": "Ontario",
            "country": "Canada",
            "latitude": 42.98,
            "longitude": -81.25,
            "source": "zippopotam",
        }

        with patch.object(lookup, '_lookup_zippopotam', return_value=mock_result):
            with patch.object(lookup, '_save_cache'):
                result = lookup.lookup("N6A3K7", "CA")
                assert result["city"] == "London"


class TestZippopotamLookup:
    """Tests for the Zippopotam.us API lookup."""

    def test_successful_zippopotam_lookup(self):
        """Test successful lookup via Zippopotam.us."""
        lookup = PostalLookup()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "country": "Canada",
            "country abbreviation": "CA",
            "places": [{
                "place name": "London",
                "state": "Ontario",
                "latitude": "42.9834",
                "longitude": "-81.2330",
            }]
        }

        mock_session = Mock()
        mock_session.get.return_value = mock_response

        result = lookup._lookup_zippopotam(mock_session, "N6A3K7", "CA", 10.0)

        assert result["city"] == "London"
        assert result["state_province"] == "Ontario"
        assert result["latitude"] == 42.9834
        assert result["source"] == "zippopotam"

    def test_zippopotam_404_returns_none(self):
        """Test that 404 response returns None."""
        lookup = PostalLookup()

        mock_response = Mock()
        mock_response.status_code = 404

        mock_session = Mock()
        mock_session.get.return_value = mock_response

        result = lookup._lookup_zippopotam(mock_session, "INVALID", "US", 10.0)
        assert result is None

    def test_zippopotam_rate_limit(self):
        """Test that 429 raises RateLimitError."""
        lookup = PostalLookup()

        mock_response = Mock()
        mock_response.status_code = 429

        mock_session = Mock()
        mock_session.get.return_value = mock_response

        with pytest.raises(RateLimitError):
            lookup._lookup_zippopotam(mock_session, "12345", "US", 10.0)

    def test_zippopotam_server_error(self):
        """Test that 5xx raises APIResponseError."""
        lookup = PostalLookup()

        mock_response = Mock()
        mock_response.status_code = 500

        mock_session = Mock()
        mock_session.get.return_value = mock_response

        with pytest.raises(APIResponseError):
            lookup._lookup_zippopotam(mock_session, "12345", "US", 10.0)

    def test_zippopotam_network_timeout(self):
        """Test that timeout raises NetworkError."""
        lookup = PostalLookup()

        mock_session = Mock()
        mock_session.get.side_effect = requests.exceptions.Timeout("Request timed out")

        with pytest.raises(NetworkError, match="Request timeout"):
            lookup._lookup_zippopotam(mock_session, "12345", "US", 10.0)

    def test_zippopotam_connection_error(self):
        """Test that connection error raises NetworkError."""
        lookup = PostalLookup()

        mock_session = Mock()
        mock_session.get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        with pytest.raises(NetworkError, match="Connection error"):
            lookup._lookup_zippopotam(mock_session, "12345", "US", 10.0)

    def test_zippopotam_invalid_json(self):
        """Test that invalid JSON raises APIResponseError."""
        lookup = PostalLookup()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        mock_session = Mock()
        mock_session.get.return_value = mock_response

        with pytest.raises(APIResponseError, match="Invalid JSON"):
            lookup._lookup_zippopotam(mock_session, "12345", "US", 10.0)

    def test_zippopotam_empty_places(self):
        """Test that empty places list returns None."""
        lookup = PostalLookup()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"places": []}

        mock_session = Mock()
        mock_session.get.return_value = mock_response

        result = lookup._lookup_zippopotam(mock_session, "12345", "US", 10.0)
        assert result is None


class TestNominatimLookup:
    """Tests for the Nominatim API lookup."""

    def test_successful_nominatim_lookup(self):
        """Test successful lookup via Nominatim."""
        lookup = PostalLookup()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{
            "lat": "42.9834",
            "lon": "-81.2330",
            "address": {
                "city": "London",
                "state": "Ontario",
                "country": "Canada",
                "country_code": "ca",
                "postcode": "N6A3K7",
            }
        }]

        mock_session = Mock()
        mock_session.get.return_value = mock_response

        result = lookup._lookup_nominatim(mock_session, "N6A3K7", "CA", 10.0)

        assert result["city"] == "London"
        assert result["state_province"] == "Ontario"
        assert result["latitude"] == 42.9834
        assert result["source"] == "nominatim"

    def test_nominatim_empty_results(self):
        """Test that empty results return None."""
        lookup = PostalLookup()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        mock_session = Mock()
        mock_session.get.return_value = mock_response

        result = lookup._lookup_nominatim(mock_session, "INVALID", "US", 10.0)
        assert result is None

    def test_nominatim_rate_limit(self):
        """Test that 429 raises RateLimitError."""
        lookup = PostalLookup()

        mock_response = Mock()
        mock_response.status_code = 429

        mock_session = Mock()
        mock_session.get.return_value = mock_response

        with pytest.raises(RateLimitError):
            lookup._lookup_nominatim(mock_session, "12345", "US", 10.0)


class TestReverseLookup:
    """Tests for reverse geocoding functionality."""

    def test_successful_reverse_lookup(self):
        """Test successful reverse geocoding."""
        lookup = PostalLookup()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "address": {
                "city": "Toronto",
                "state": "Ontario",
                "country": "Canada",
                "country_code": "ca",
            }
        }

        with patch('requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session.get.return_value = mock_response
            mock_session_class.return_value = mock_session

            with patch.object(lookup, '_save_cache'):
                result = lookup.reverse_lookup(43.6532, -79.3832)

        assert result["city"] == "Toronto"
        assert result["state_province"] == "Ontario"

    def test_reverse_lookup_invalid_latitude(self):
        """Test that invalid latitude raises ValueError."""
        lookup = PostalLookup()
        with pytest.raises(ValueError, match="latitude must be between"):
            lookup.reverse_lookup(999, -79.3832)

    def test_reverse_lookup_invalid_longitude(self):
        """Test that invalid longitude raises ValueError."""
        lookup = PostalLookup()
        with pytest.raises(ValueError, match="longitude must be between"):
            lookup.reverse_lookup(43.6532, 999)

    def test_reverse_lookup_non_numeric_coords(self):
        """Test that non-numeric coordinates raise ValueError."""
        lookup = PostalLookup()
        with pytest.raises(ValueError, match="must be numeric"):
            lookup.reverse_lookup("invalid", -79.3832)


class TestFallbackBehavior:
    """Tests for fallback between APIs."""

    def test_zippopotam_fails_fallback_to_nominatim(self):
        """Test that Zippopotam failure falls back to Nominatim."""
        lookup = PostalLookup()

        # Clear any cached data from disk
        lookup._cache = {}

        mock_zip_result = None  # Zippopotam fails
        mock_nominatim_result = {
            "city": "London",
            "state_province": "Ontario",
            "source": "nominatim",
        }

        with patch.object(lookup, '_lookup_zippopotam', return_value=mock_zip_result):
            with patch.object(lookup, '_lookup_nominatim', return_value=mock_nominatim_result):
                with patch.object(lookup, '_save_cache'):
                    result = lookup.lookup("N6A3K7", "CA")
                    assert result["source"] == "nominatim"

    def test_both_services_fail_returns_none(self):
        """Test that when both services fail, None is returned."""
        lookup = PostalLookup()

        with patch.object(lookup, '_lookup_zippopotam', return_value=None):
            with patch.object(lookup, '_lookup_nominatim', return_value=None):
                with patch.object(lookup, '_save_cache'):
                    result = lookup.lookup("INVALID", "US")
                    assert result is None
