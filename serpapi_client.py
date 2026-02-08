"""
SERPAPI Integration for Real Price Fetching

Fetches live grocery prices from Google Shopping via SERPAPI.

**GEOGRAPHIC RESTRICTION:**
All searches are limited to San Francisco Bay Area (West Bay corridor)
from San Francisco to San Jose.

Features:
- Batch processing (5-10 ingredients per request)
- Rate limit handling (429)
- Timeout fallback (>10s)
- Graceful degradation (returns partial results)
- Bay Area location enforcement
"""

import requests
import logging
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


# San Francisco Bay Area zip codes (West Bay corridor: SF to San Jose)
BAY_AREA_LOCATIONS = [
    "San Francisco, CA 94103",  # SF Downtown
    "Daly City, CA 94014",      # Northern Peninsula
    "San Mateo, CA 94401",      # Mid Peninsula
    "Palo Alto, CA 94301",      # South Peninsula
    "Mountain View, CA 94041",   # South Bay
    "Sunnyvale, CA 94086",      # South Bay
    "San Jose, CA 95113",       # San Jose Downtown
]


@dataclass
class SERPAPIResult:
    """Result from SERPAPI price fetch"""
    success: bool  # True if fetched successfully
    prices: Dict[str, List[Dict]]  # {ingredient: [{"store": name, "price": float}]}
    errors: List[str]  # List of error messages
    retry_after: int  # Seconds to wait before retrying (if rate limited)


class SERPAPIClient:
    """Client for fetching prices from SERPAPI Google Shopping API"""
    
    BASE_URL = "https://serpapi.com/search"
    TIMEOUT = 10  # seconds
    MAX_RETRIES = 3
    BATCH_SIZE = 5
    
    def __init__(self, api_key: str):
        """
        Initialize SERPAPI client.
        
        Args:
            api_key: SERPAPI API key from environment
        """
        self.api_key = api_key
        logger.info("SERPAPIClient initialized")
    
    def fetch_prices(
        self,
        ingredient_list: List[str],
        location: str = "San Francisco, CA 94103"
    ) -> SERPAPIResult:
        """
        Fetch prices for multiple ingredients from Bay Area stores.

        **IMPORTANT:** Location is restricted to San Francisco Bay Area
        (West Bay corridor: SF to San Jose). Invalid locations will be
        overridden to default Bay Area location.

        Algorithm:
        1. Validate location is within Bay Area
        2. Batch ingredients into groups of 5
        3. For each batch, call SERPAPI Google Shopping API
        4. Parse prices and stores from response
        5. Handle errors gracefully (timeouts, rate limits, invalid responses)
        6. Return all results even if some failed

        Args:
            ingredient_list: List of ingredients to fetch
            location: Geographic location (must be in Bay Area)

        Returns:
            SERPAPIResult with prices and error list
        """
        # Enforce Bay Area location
        if not self._is_valid_bay_area_location(location):
            logger.warning(
                f"Location '{location}' is not in Bay Area. "
                f"Using default: San Francisco, CA 94103"
            )
            location = "San Francisco, CA 94103"

        prices = {}
        errors = []
        retry_after = 0

        logger.info(f"Fetching prices for {len(ingredient_list)} ingredients from {location}")
        
        # Batch ingredients to stay within API limits
        batches = [
            ingredient_list[i:i + self.BATCH_SIZE]
            for i in range(0, len(ingredient_list), self.BATCH_SIZE)
        ]
        
        logger.info(f"Processing {len(batches)} batches (batch size: {self.BATCH_SIZE})")
        
        for batch_idx, batch in enumerate(batches):
            for ingredient in batch:
                try:
                    logger.debug(f"Fetching prices for: {ingredient}")
                    result = self._fetch_single_ingredient(ingredient, location)
                    prices[ingredient] = result
                    
                    # Small delay between requests to avoid rate limiting
                    time.sleep(0.5)
                    
                except requests.exceptions.Timeout:
                    msg = f"Timeout fetching {ingredient}"
                    logger.warning(msg)
                    errors.append(msg)
                    
                except requests.exceptions.HTTPError as e:
                    # Handle specific HTTP errors
                    if e.response.status_code == 429:  # Rate limit
                        retry_after = int(e.response.headers.get('Retry-After', 60))
                        msg = f"Rate limited (429). Retry after {retry_after}s"
                        logger.error(msg)
                        errors.append(msg)
                        
                        return SERPAPIResult(
                            success=False,
                            prices=prices,  # Return partial results
                            errors=errors,
                            retry_after=retry_after
                        )
                    
                    elif e.response.status_code == 401:  # Invalid API key
                        msg = "Invalid SERPAPI key (401)"
                        logger.error(msg)
                        errors.append(msg)
                        # Continue trying other ingredients
                    
                    else:
                        msg = f"HTTP {e.response.status_code}: {ingredient}"
                        logger.error(msg)
                        errors.append(msg)
                    
                except ValueError as e:  # JSON parse error
                    msg = f"Invalid JSON response for {ingredient}: {str(e)}"
                    logger.error(msg)
                    errors.append(msg)
                    
                except Exception as e:
                    msg = f"Unexpected error fetching {ingredient}: {str(e)}"
                    logger.error(msg)
                    errors.append(msg)
        
        # Log results
        logger.info(f"✓ Fetched {len(prices)}/{len(ingredient_list)} ingredients")
        if errors:
            logger.warning(f"⚠ Errors: {len(errors)}")
        
        return SERPAPIResult(
            success=len(errors) == 0,
            prices=prices,
            errors=errors,
            retry_after=retry_after
        )
    
    def _is_valid_bay_area_location(self, location: str) -> bool:
        """
        Check if location is a valid Bay Area location.

        Args:
            location: Location string to validate

        Returns:
            True if location contains Bay Area indicators
        """
        bay_area_indicators = [
            "94",  # SF Bay Area zip prefix
            "san francisco",
            "san mateo",
            "palo alto",
            "mountain view",
            "sunnyvale",
            "san jose",
            "daly city",
            "bay area",
        ]

        location_lower = location.lower()
        return any(indicator in location_lower for indicator in bay_area_indicators)

    def _fetch_single_ingredient(
        self,
        ingredient: str,
        location: str
    ) -> List[Dict]:
        """
        Fetch prices for a single ingredient from SERPAPI.

        Args:
            ingredient: Ingredient name
            location: Bay Area location for search

        Returns:
            List of [{"store": name, "price": float}, ...]

        Raises:
            requests.exceptions.RequestException: On network/API errors
            ValueError: On JSON parse errors
        """
        params = {
            "q": f"{ingredient} grocery store",
            "api_key": self.api_key,
            "engine": "google_shopping",
            "google_domain": "google.com",
            "hl": "en",  # English
            "gl": "us",  # United States
            "location": location,  # Enforce Bay Area location
        }
        
        logger.debug(f"SERPAPI request: {ingredient} in {location}")
        
        response = requests.get(
            self.BASE_URL,
            params=params,
            timeout=self.TIMEOUT
        )
        
        # Raise exception for bad status codes
        response.raise_for_status()
        
        data = response.json()
        
        # Parse shopping results
        results = []
        
        for result in data.get('shopping_results', []):
            try:
                store_name = result.get('source')
                price_str = result.get('price', '0')
                
                # Parse price (might be "$10.99" or "10.99")
                price_float = float(price_str.replace('$', '').strip())
                
                results.append({
                    "store": store_name,
                    "price": price_float
                })
            
            except (ValueError, AttributeError, KeyError) as e:
                logger.debug(f"Failed to parse shopping result: {result}")
                continue
        
        if not results:
            logger.debug(f"No shopping results found for {ingredient}")
        else:
            logger.debug(f"Found {len(results)} results for {ingredient}")
        
        return results


if __name__ == "__main__":
    # Example usage
    import os
    from dotenv import load_dotenv
    
    logging.basicConfig(level=logging.INFO)
    
    load_dotenv()
    api_key = os.getenv("SERPAPI_API_KEY")
    
    if api_key:
        client = SERPAPIClient(api_key)
        
        # Test with a few ingredients
        ingredients = ["chicken breast", "broccoli", "rice"]
        result = client.fetch_prices(ingredients)
        
        print(f"\nSERPAPI Results:")
        print(f"  Success: {result.success}")
        print(f"  Prices fetched: {len(result.prices)}")
        print(f"  Errors: {len(result.errors)}")
        
        if result.prices:
            for ing, prices in list(result.prices.items())[:2]:
                print(f"\n  {ing}:")
                for p in prices[:3]:
                    print(f"    - {p['store']}: ${p['price']}")
    else:
        print("SERPAPI_API_KEY not set in environment")
