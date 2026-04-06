"""
Country Code Normalization Module

This module provides functionality to normalize country codes from various
formats (2-letter, 3-letter, numeric code, or full country name) to the
standard 2-letter ISO 3166-1 alpha-2 code.

All lookups are case-insensitive. Supports fuzzy matching for country names.
"""
__version__ = "1.0.0"
__author__ = "Peter Nearing"
__email__ = "me@peternearing.ca"

import json
import os
from typing import Optional
from difflib import get_close_matches


class CountryCodeNormalizer:
    """
    Normalizes various country code formats to 2-letter ISO codes.
    
    Accepts:
        - 2-letter ISO codes (e.g., "US", "ca")
        - 3-letter ISO codes (e.g., "USA", "can")
        - Numeric codes (e.g., "840", 840)
        - Full country names (e.g., "United States", "canada")
    
    All inputs are case-insensitive.
    
    Example:
        >>> normalizer = CountryCodeNormalizer()
        >>> normalizer.normalize("USA")
        'US'
        >>> normalizer.normalize("canada")
        'CA'
        >>> normalizer.normalize("840")
        'US'
    """
    
    _instance = None
    _data_loaded = False
    
    # Lookup dictionaries
    _alpha2_map: dict = {}
    _alpha3_map: dict = {}
    _numeric_map: dict = {}
    _name_map: dict = {}
    _alias_map: dict = {}
    _all_names: list = []
    
    def __new__(cls):
        """Singleton pattern to ensure data is loaded only once."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._data_loaded:
            self._load_country_data()
            CountryCodeNormalizer._data_loaded = True
    
    def _load_country_data(self) -> None:
        """
        Load country data from JSON file and build lookup maps.
        
        The JSON file is expected to contain country data with fields:
        - name: Full country name
        - alpha-2: 2-letter ISO code
        - alpha-3: 3-letter ISO code  
        - country-code: Numeric code (as string with leading zeros)
        """
        # Find the data file relative to this module
        # The data file is at data/country_codes.json relative to this file
        module_dir = os.path.dirname(os.path.abspath(__file__))
        data_file = os.path.join(module_dir, "data", "country_codes.json")
        
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                countries = json.load(f)
        except FileNotFoundError:
            raise RuntimeError(f"Country codes data file not found: {data_file}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in country codes file: {e}")
        
        # Build lookup maps (all keys are stored lowercase for case-insensitive lookup)
        for country in countries:
            alpha2 = country.get("alpha-2", "").strip().upper()
            alpha3 = country.get("alpha-3", "").strip().upper()
            numeric = country.get("country-code", "").strip()
            name = country.get("name", "").strip()
            
            if alpha2:
                self._alpha2_map[alpha2.lower()] = alpha2
                
                # Also map the name to alpha-2
                if name:
                    name_lower = name.lower()
                    self._name_map[name_lower] = alpha2
                    self._all_names.append(name_lower)
                
                # Map alpha-3 to alpha-2
                if alpha3:
                    self._alpha3_map[alpha3.lower()] = alpha2
                
                # Map numeric code to alpha-2 (strip leading zeros for flexible matching)
                if numeric:
                    self._numeric_map[numeric.lower()] = alpha2
                    # Also map without leading zeros
                    self._numeric_map[numeric.lstrip("0") or "0"] = alpha2
        
        # Add common aliases for fuzzy matching
        self._add_common_aliases()
    
    def normalize(self, country_code: str) -> Optional[str]:
        """
        Normalize a country code input to a 2-letter ISO code.
        
        Accepts 2-letter codes, 3-letter codes, numeric codes, or full country names.
        All comparisons are case-insensitive.
        
        Args:
            country_code: The country code or name to normalize (e.g., "US", "USA", 
                         "840", "United States")
        
        Returns:
            The 2-letter ISO country code (uppercase) if found, None otherwise.
        
        Examples:
            >>> normalizer = CountryCodeNormalizer()
            >>> normalizer.normalize("USA")
            'US'
            >>> normalizer.normalize("us")
            'US'
            >>> normalizer.normalize("840")
            'US'
            >>> normalizer.normalize("United States")
            'US'
            >>> normalizer.normalize("CAN")
            'CA'
            >>> normalizer.normalize("124")
            'CA'
            >>> normalizer.normalize("canada")
            'CA'
            >>> normalizer.normalize("INVALID") is None
            True
        """
        if not country_code or not isinstance(country_code, str):
            return None
        
        code = country_code.strip()
        if not code:
            return None
        
        # Convert to lowercase for case-insensitive lookup
        code_lower = code.lower()
        
        # Try 2-letter code first
        if code_lower in self._alpha2_map:
            return self._alpha2_map[code_lower]
        
        # Try 3-letter code
        if code_lower in self._alpha3_map:
            return self._alpha3_map[code_lower]
        
        # Try numeric code (with or without leading zeros)
        # Strip any leading zeros for comparison, but handle "0" case
        numeric_key = code_lower.lstrip("0") or "0"
        if numeric_key in self._numeric_map:
            return self._numeric_map[numeric_key]
        
        # Try full country name (exact match first)
        if code_lower in self._name_map:
            return self._name_map[code_lower]
        
        # Try common aliases
        if code_lower in self._alias_map:
            return self._alias_map[code_lower]
        
        # Try fuzzy matching for country names (if input is at least 3 characters)
        if len(code_lower) >= 3:
            # First try alias fuzzy match (high confidence required)
            alias_matches = get_close_matches(code_lower, self._alias_map.keys(), n=1, cutoff=0.8)
            if alias_matches:
                return self._alias_map[alias_matches[0]]
            
            # Then try full name fuzzy match (very high cutoff to avoid false matches)
            # Only match if input is at least 4 chars and has reasonable similarity
            if len(code_lower) >= 4:
                name_matches = get_close_matches(code_lower, self._all_names, n=1, cutoff=0.7)
                if name_matches:
                    return self._name_map[name_matches[0]]
        
        return None
    
    def is_valid(self, country_code: str) -> bool:
        """
        Check if a country code input is valid.
        
        Args:
            country_code: The country code or name to validate
        
        Returns:
            True if the input can be normalized to a valid 2-letter code,
            False otherwise.
        
        Example:
            >>> normalizer = CountryCodeNormalizer()
            >>> normalizer.is_valid("US")
            True
            >>> normalizer.is_valid("usa")
            True
            >>> normalizer.is_valid("United States")
            True
            >>> normalizer.is_valid("XX")
            False
        """
        return self.normalize(country_code) is not None
    
    def _add_common_aliases(self) -> None:
        """Add common aliases and short forms for fuzzy matching."""
        aliases = {
            # Common short forms
            "uk": "GB",  # United Kingdom
            "united kingdom": "GB",
            "great britain": "GB",
            "britain": "GB",
            "england": "GB",  # Not strictly correct but commonly used
            "scotland": "GB",
            "wales": "GB",
            "northern ireland": "GB",
            "usa": "US",
            "america": "US",
            "united states": "US",
            "russia": "RU",  # Russian Federation
            "russian federation": "RU",
            "south korea": "KR",
            "north korea": "KP",
            "korea": "KR",  # Default to South Korea
            "republic of korea": "KR",
            "taiwan": "TW",  # Taiwan, Province of China
            "iran": "IR",  # Iran (Islamic Republic of)
            "syria": "SY",  # Syrian Arab Republic
            "macedonia": "MK",  # North Macedonia
            "north macedonia": "MK",
            "moldova": "MD",  # Republic of Moldova
            "bolivia": "BO",  # Bolivia (Plurinational State of)
            "venezuela": "VE",  # Venezuela (Bolivarian Republic of)
            "tanzania": "TZ",  # Tanzania, United Republic of
            "vietnam": "VN",  # Viet Nam
            "ivory coast": "CI",  # Côte d'Ivoire
            "cape verde": "CV",  # Cabo Verde
            "myanmar": "MM",  # Myanmar (Burma)
            "burma": "MM",
            "laos": "LA",  # Lao People's Democratic Republic
            "brunei": "BN",  # Brunei Darussalam
            "vatican": "VA",  # Vatican City / Holy See
            "vatican city": "VA",
            "palestine": "PS",  # Palestine, State of
            "palestinian": "PS",
            "kosovo": "XK",
        }
        
        for alias, alpha2 in aliases.items():
            # Only add alias if the target country exists in our data
            if alpha2.lower() in self._alpha2_map:
                self._alias_map[alias] = alpha2
                # Also add without spaces and with common variations
                self._alias_map[alias.replace(" ", "")] = alpha2
                self._alias_map[alias.replace("-", "")] = alpha2


# Module-level convenience function
_normalizer = None

def normalize_country_code(country_code: str) -> Optional[str]:
    """
    Normalize a country code to a 2-letter ISO code.
    
    This is a convenience function that uses the CountryCodeNormalizer singleton.
    
    Args:
        country_code: The country code or name to normalize
    
    Returns:
        The 2-letter ISO country code (uppercase) if found, None otherwise.
    
    Examples:
        >>> normalize_country_code("USA")
        'US'
        >>> normalize_country_code("canada")
        'CA'
        >>> normalize_country_code("840")
        'US'
        >>> normalize_country_code("United States of America")
        'US'
    """
    global _normalizer
    if _normalizer is None:
        _normalizer = CountryCodeNormalizer()
    return _normalizer.normalize(country_code)


def is_valid_country_code(country_code: str) -> bool:
    """
    Check if a country code is valid.
    
    This is a convenience function that uses the CountryCodeNormalizer singleton.
    
    Args:
        country_code: The country code or name to validate
    
    Returns:
        True if valid, False otherwise.
    
    Examples:
        >>> is_valid_country_code("US")
        True
        >>> is_valid_country_code("XX")
        False
    """
    global _normalizer
    if _normalizer is None:
        _normalizer = CountryCodeNormalizer()
    return _normalizer.is_valid(country_code)
