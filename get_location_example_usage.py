#!/usr/bin/env python3
"""
Example script demonstrating how to use the get_location module.
"""

import logging
from get_location import (
    lookup_city_region_by_postal_code, 
    PostalLookupError, 
    NetworkError, 
    RateLimitError, 
    APIResponseError
)

def main():
    # Set up logging for this script
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Example postal codes to test
    test_cases = [
        ("N6A 3K7", "CA"),  # London, Ontario, Canada
        ("90210", "US"),    # Beverly Hills, CA, USA
        ("M5H 2N2", "CA"),  # Toronto, Ontario, Canada
        ("10001", "US"),    # New York, NY, USA
        ("N5Z 0B3", "CA"),  # London, Ontario, Canada
    ]
    
    for postal_code, country_code in test_cases:
        logger.info(f"Looking up: {postal_code}, {country_code}")
        
        try:
            result = lookup_city_region_by_postal_code(
                postal_code=postal_code,
                country_code=country_code,
                logger=logger  # Pass our logger for verbose output
            )
            
            if result:
                print(f"✓ {postal_code} ({country_code}): {result['city']}, {result['state_province']}, {result['country']}")
                print(f"  Coordinates: {result['latitude']}, {result['longitude']}")
                print(f"  Source: {result['source']}")
                print()
            else:
                print(f"✗ {postal_code} ({country_code}): Not found")
                print()
                
        except NetworkError as e:
            logger.error(f"Network error for {postal_code}: {e}")
            print(f"✗ {postal_code} ({country_code}): Network Error - {e}")
            print()
        except RateLimitError as e:
            logger.error(f"Rate limit error for {postal_code}: {e}")
            print(f"✗ {postal_code} ({country_code}): Rate Limit Error - {e}")
            print()
        except APIResponseError as e:
            logger.error(f"API response error for {postal_code}: {e}")
            print(f"✗ {postal_code} ({country_code}): API Response Error - {e}")
            print()
        except ValueError as e:
            logger.error(f"Invalid input for {postal_code}: {e}")
            print(f"✗ {postal_code} ({country_code}): Invalid input - {e}")
            print()
        except PostalLookupError as e:
            logger.error(f"Postal lookup error for {postal_code}: {e}")
            print(f"✗ {postal_code} ({country_code}): Lookup Error - {e}")
            print()
        except Exception as e:
            logger.error(f"Unexpected error looking up {postal_code}: {e}")
            print(f"✗ {postal_code} ({country_code}): Unexpected Error - {e}")
            print()

if __name__ == "__main__":
    main()
