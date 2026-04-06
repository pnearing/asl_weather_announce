"""
Unit tests for country_codes module.

These tests cover the CountryCodeNormalizer class and convenience functions
for normalizing various country code formats to 2-letter ISO codes.
"""

import pytest
from asl_weather.get_location.country_codes import (
    CountryCodeNormalizer,
    normalize_country_code,
    is_valid_country_code,
)


class TestCountryCodeNormalizer:
    """Tests for the CountryCodeNormalizer class."""

    @pytest.fixture
    def normalizer(self):
        """Create a fresh normalizer instance for each test."""
        return CountryCodeNormalizer()

    def test_singleton_pattern(self):
        """Test that CountryCodeNormalizer is a singleton."""
        n1 = CountryCodeNormalizer()
        n2 = CountryCodeNormalizer()
        assert n1 is n2

    def test_normalize_2_letter_code(self, normalizer):
        """Test normalization of 2-letter ISO codes."""
        assert normalizer.normalize("US") == "US"
        assert normalizer.normalize("CA") == "CA"
        assert normalizer.normalize("GB") == "GB"
        assert normalizer.normalize("us") == "US"
        assert normalizer.normalize("ca") == "CA"
        assert normalizer.normalize("gb") == "GB"

    def test_normalize_3_letter_code(self, normalizer):
        """Test normalization of 3-letter ISO codes."""
        assert normalizer.normalize("USA") == "US"
        assert normalizer.normalize("CAN") == "CA"
        assert normalizer.normalize("GBR") == "GB"
        assert normalizer.normalize("usa") == "US"
        assert normalizer.normalize("can") == "CA"

    def test_normalize_numeric_code(self, normalizer):
        """Test normalization of numeric country codes."""
        assert normalizer.normalize("840") == "US"
        assert normalizer.normalize("124") == "CA"
        assert normalizer.normalize("826") == "GB"
        # Test without leading zeros
        assert normalizer.normalize("840") == "US"

    def test_normalize_country_name(self, normalizer):
        """Test normalization of full country names."""
        assert normalizer.normalize("United States") == "US"
        assert normalizer.normalize("Canada") == "CA"
        assert normalizer.normalize("United Kingdom") == "GB"
        assert normalizer.normalize("united states") == "US"
        assert normalizer.normalize("canada") == "CA"

    def test_normalize_aliases(self, normalizer):
        """Test normalization of common country aliases."""
        assert normalizer.normalize("USA") == "US"
        assert normalizer.normalize("America") == "US"
        assert normalizer.normalize("UK") == "GB"
        assert normalizer.normalize("United Kingdom") == "GB"
        assert normalizer.normalize("Great Britain") == "GB"
        assert normalizer.normalize("Russia") == "RU"
        assert normalizer.normalize("South Korea") == "KR"
        assert normalizer.normalize("Korea") == "KR"
        assert normalizer.normalize("Taiwan") == "TW"

    def test_normalize_with_whitespace(self, normalizer):
        """Test that whitespace is stripped from input."""
        assert normalizer.normalize("  US  ") == "US"
        assert normalizer.normalize("  Canada  ") == "CA"

    def test_normalize_invalid_codes(self, normalizer):
        """Test that invalid codes return None."""
        assert normalizer.normalize("XX") is None
        assert normalizer.normalize("INVALID") is None
        assert normalizer.normalize("") is None
        assert normalizer.normalize("   ") is None

    def test_normalize_none_and_non_string(self, normalizer):
        """Test that None and non-string inputs return None."""
        assert normalizer.normalize(None) is None
        assert normalizer.normalize(123) is None

    def test_is_valid_with_valid_codes(self, normalizer):
        """Test is_valid with valid country codes."""
        assert normalizer.is_valid("US") is True
        assert normalizer.is_valid("USA") is True
        assert normalizer.is_valid("840") is True
        assert normalizer.is_valid("United States") is True

    def test_is_valid_with_invalid_codes(self, normalizer):
        """Test is_valid with invalid country codes."""
        assert normalizer.is_valid("XX") is False
        assert normalizer.is_valid("INVALID") is False
        assert normalizer.is_valid("") is False
        assert normalizer.is_valid(None) is False


class TestConvenienceFunctions:
    """Tests for the module-level convenience functions."""

    def test_normalize_country_code(self):
        """Test the normalize_country_code convenience function."""
        assert normalize_country_code("US") == "US"
        assert normalize_country_code("USA") == "US"
        assert normalize_country_code("840") == "US"
        assert normalize_country_code("United States") == "US"
        assert normalize_country_code("XX") is None

    def test_is_valid_country_code(self):
        """Test the is_valid_country_code convenience function."""
        assert is_valid_country_code("US") is True
        assert is_valid_country_code("USA") is True
        assert is_valid_country_code("XX") is False
        assert is_valid_country_code(None) is False

    def test_convenience_functions_use_same_normalizer(self):
        """Test that convenience functions share the same normalizer instance."""
        # Both calls should use the same singleton instance
        result1 = normalize_country_code("US")
        result2 = normalize_country_code("US")
        assert result1 == result2 == "US"
