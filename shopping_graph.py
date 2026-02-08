"""
Shopping Graph System - PRODUCTION VERSION

**GEOGRAPHIC RESTRICTION:** San Francisco Bay Area (West Bay) only.

This module defines:
1. Core graph objects with geographic validation (Store, RouteSegment/Edge)
2. Price matrix for ingredient pricing across stores
3. Shopping list specification
4. Functions for building shopping graphs with real Google Maps routing

Uses Google Maps Distance Matrix API for real driving times with traffic.
"""

import asyncio
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import pandas as pd

from googlemaps_client import GoogleMapsClient, GeoLocation as GMGeoLocation, WEST_BAY_BOUNDS


# ============================================================================
# STEP 1: DATA STRUCTURES AND CONTAINERS
# ============================================================================

@dataclass
class GeoLocation:
    """
    Geographic coordinates with West Bay validation.

    **PRODUCTION:** All locations must be within San Francisco Bay Area (West Bay).
    """
    latitude: float
    longitude: float

    def is_in_service_area(self) -> bool:
        """Check if location is within West Bay service area."""
        return (
            WEST_BAY_BOUNDS["south"] <= self.latitude <= WEST_BAY_BOUNDS["north"]
            and WEST_BAY_BOUNDS["west"] <= self.longitude <= WEST_BAY_BOUNDS["east"]
        )

    def distance_to(self, other: "GeoLocation") -> float:
        """
        Calculate Haversine distance between two locations in kilometers.

        NOTE: For production routing, use GoogleMapsClient.get_route_info()
        instead of Haversine distance for real traffic-aware routing.
        """
        R = 6371  # Earth's radius in km

        lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
        lat2, lon2 = math.radians(other.latitude), math.radians(other.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))

        return R * c


@dataclass
class Store:
    """
    Represents a store node in the shopping graph.
    
    Attributes:
        name: Store identifier/name
        address: Physical address
        geo_location: GeoLocation object with lat/long
        inventory: Dictionary mapping ingredient names to availability
    """
    name: str
    address: str
    geo_location: GeoLocation
    inventory: Dict[str, bool] = field(default_factory=dict)

    def has_item(self, ingredient: str) -> bool:
        """Check if store has a particular ingredient in inventory."""
        return self.inventory.get(ingredient, False)

    def add_to_inventory(self, ingredient: str, available: bool = True) -> None:
        """Add or update an ingredient in the store's inventory."""
        self.inventory[ingredient] = available


@dataclass
class RouteSegment:
    """
    Represents an edge in the shopping graph (travel path between two locations).
    
    Attributes:
        origin: Starting Store or None for Home
        destination: Ending Store or None for Home
        travel_time_minutes: Time to travel this segment
        travel_cost: Cost of travel (gas, Uber price, etc.)
    """
    origin: Optional[Store]  # None represents Home
    destination: Optional[Store]  # None represents Home
    travel_time_minutes: float
    travel_cost: float

    def __hash__(self) -> int:
        """Make RouteSegment hashable for use in dicts/sets."""
        origin_id = id(self.origin) if self.origin else "HOME"
        dest_id = id(self.destination) if self.destination else "HOME"
        return hash((origin_id, dest_id))


class PriceMatrix:
    """
    Two-sided price matrix: rows are ingredients, columns are stores.
    
    Values represent the price of an ingredient at a store.
    If an ingredient is not found at a store, the value is float('inf').
    """
    
    def __init__(self, ingredients: List[str], stores: List[Store]):
        """
        Initialize the price matrix with ingredients and stores.
        
        Args:
            ingredients: List of ingredient names
            stores: List of Store objects
        """
        self.ingredients = ingredients
        self.stores = {store.name: store for store in stores}
        self.store_names = [store.name for store in stores]
        
        # Initialize DataFrame with infinity (ingredient not available)
        self.data = pd.DataFrame(
            data=float('inf'),
            index=ingredients,
            columns=self.store_names,
            dtype=float
        )

    def set_price(self, ingredient: str, store_name: str, price: float) -> None:
        """Set the price of an ingredient at a store."""
        if ingredient not in self.data.index:
            raise ValueError(f"Ingredient '{ingredient}' not in price matrix")
        if store_name not in self.data.columns:
            raise ValueError(f"Store '{store_name}' not in price matrix")
        
        self.data.loc[ingredient, store_name] = price

    def get_price(self, ingredient: str, store_name: str) -> float:
        """Get the price of an ingredient at a store (returns inf if not available)."""
        return self.data.loc[ingredient, store_name]

    def get_store_prices(self, store_name: str) -> pd.Series:
        """Get all ingredient prices at a specific store."""
        return self.data[store_name]

    def get_ingredient_prices(self, ingredient: str) -> pd.Series:
        """Get prices of a specific ingredient across all stores."""
        return self.data.loc[ingredient]

    def to_dataframe(self) -> pd.DataFrame:
        """Return the underlying DataFrame."""
        return self.data.copy()


@dataclass
class ShoppingList:
    """
    User's shopping requirements and time valuation.
    
    Attributes:
        ingredients: List of required ingredient names with optional quantities
        hourly_time_value: Hourly rate to calculate cost of time (e.g., $20/hr)
        home_location: GeoLocation of user's home
    """
    ingredients: List[str]
    hourly_time_value: float  # dollars per hour
    home_location: GeoLocation

    def calculate_time_cost(self, minutes: float) -> float:
        """
        Convert travel time into monetary cost based on hourly rate.
        
        Args:
            minutes: Travel time in minutes
            
        Returns:
            Cost in dollars
        """
        hours = minutes / 60
        return hours * self.hourly_time_value


# ============================================================================
# STEP 2: ASYNCHRONOUS DATA FETCHING LAYER
# ============================================================================

async def fetch_prices(
    ingredient_list: List[str],
    stores: List[Store],
    price_matrix: PriceMatrix,
    mock_data: Optional[Dict[str, Dict[str, float]]] = None
) -> PriceMatrix:
    """
    Asynchronously fetch prices for all ingredients at all stores.
    
    This function simulates calling external APIs (e.g., web scraper, store APIs).
    In production, this would use Playwright or requests to scrape/query actual prices.
    
    Args:
        ingredient_list: List of ingredient names to fetch prices for
        stores: List of Store objects representing target stores
        price_matrix: PriceMatrix object to populate
        mock_data: Optional mock data for testing (store_name -> {ingredient -> price})
        
    Returns:
        Populated PriceMatrix
        
    Raises:
        Gracefully handles failures by marking prices as infinity.
    """
    
    async def fetch_for_store(store: Store) -> Tuple[str, Dict[str, float]]:
        """Fetch all ingredient prices for a single store."""
        store_prices = {}
        
        try:
            # If mock data provided, use it
            if mock_data and store.name in mock_data:
                await asyncio.sleep(0.1)  # Simulate network latency
                store_prices = mock_data[store.name]
            else:
                # In production, this would call:
                # - store.api_endpoint with ingredient_list
                # - web scraper (Playwright) for store website
                # - third-party price aggregator API
                
                await asyncio.sleep(0.1)  # Simulate network latency
                
                # Placeholder: randomly populate with mock prices
                for ingredient in ingredient_list:
                    store_prices[ingredient] = float('inf')  # Not found
            
            # Update inventory tracking
            for ingredient in store_prices:
                if store_prices[ingredient] < float('inf'):
                    store.add_to_inventory(ingredient, available=True)
                else:
                    store.add_to_inventory(ingredient, available=False)
            
            return store.name, store_prices
            
        except Exception as e:
            print(f"Error fetching prices for {store.name}: {e}")
            # Mark all items as unavailable (infinity) on error
            return store.name, {ing: float('inf') for ing in ingredient_list}
    
    # Fetch prices for all stores concurrently
    tasks = [fetch_for_store(store) for store in stores]
    results = await asyncio.gather(*tasks)
    
    # Populate the price matrix
    for store_name, prices in results:
        for ingredient, price in prices.items():
            price_matrix.set_price(ingredient, store_name, price)
    
    return price_matrix


def calculate_edges_with_google_maps(
    home_location: GeoLocation,
    stores: List[Store],
    gmaps_client: GoogleMapsClient
) -> List[RouteSegment]:
    """
    Calculate travel times and costs using Google Maps Distance Matrix API.

    **PRODUCTION:** Uses real driving times with traffic from Google Maps.

    Creates edges for:
    - Home <-> each Store
    - Store <-> Store (for multi-stop optimization)

    Args:
        home_location: GeoLocation of user's home
        stores: List of Store objects (must be in West Bay)
        gmaps_client: Initialized GoogleMapsClient

    Returns:
        List of RouteSegment objects with real travel times and costs

    Raises:
        ValueError: If any store is outside service area
    """
    # Validate all stores are in service area
    for store in stores:
        if not store.geo_location.is_in_service_area():
            raise ValueError(
                f"Store '{store.name}' at ({store.geo_location.latitude}, "
                f"{store.geo_location.longitude}) is outside West Bay service area"
            )

    # Validate home is in service area
    if not home_location.is_in_service_area():
        raise ValueError(
            f"Home location ({home_location.latitude}, {home_location.longitude}) "
            f"is outside West Bay service area"
        )

    edges = []

    # Helper to calculate segment
    def calculate_segment(origin: Optional[Store], dest: Optional[Store]) -> RouteSegment:
        """Calculate edge using Google Maps."""
        try:
            # Get origin and destination coordinates
            if origin is None:
                origin_coords = f"{home_location.latitude},{home_location.longitude}"
            else:
                origin_coords = f"{origin.geo_location.latitude},{origin.geo_location.longitude}"

            if dest is None:
                dest_coords = f"{home_location.latitude},{home_location.longitude}"
            else:
                dest_coords = f"{dest.geo_location.latitude},{dest.geo_location.longitude}"

            # Get route info from Google Maps
            route = gmaps_client.get_route_info(origin_coords, dest_coords)

            # Calculate travel cost
            travel_cost = gmaps_client.estimate_travel_cost(route.distance_km)

            return RouteSegment(
                origin=origin,
                destination=dest,
                travel_time_minutes=route.duration_minutes,
                travel_cost=travel_cost
            )

        except Exception as e:
            print(f"Error calculating edge: {e}")
            # Return high-cost segment on error
            return RouteSegment(
                origin=origin,
                destination=dest,
                travel_time_minutes=float('inf'),
                travel_cost=float('inf')
            )
    
    # Create edges for Home -> each Store
    for store in stores:
        edges.append(calculate_segment(None, store))

    # Create edges for Store -> Home (return trips)
    for store in stores:
        edges.append(calculate_segment(store, None))

    # Create edges for Store -> Store (for multi-stop routes)
    for i in range(len(stores)):
        for j in range(len(stores)):
            if i != j:
                edges.append(calculate_segment(stores[i], stores[j]))

    return edges


async def build_shopping_graph(
    shopping_list: ShoppingList,
    stores: List[Store],
    mock_price_data: Optional[Dict[str, Dict[str, float]]] = None
) -> Tuple[PriceMatrix, List[RouteSegment]]:
    """
    Convenience function to build the entire shopping graph.
    
    Concurrently fetches prices and calculates all edges.
    
    Args:
        shopping_list: ShoppingList object
        stores: List of Store objects
        mock_price_data: Optional mock price data for testing
        
    Returns:
        Tuple of (populated PriceMatrix, list of RouteSegments)
    """
    # Initialize price matrix
    price_matrix = PriceMatrix(shopping_list.ingredients, stores)
    
    # Fetch prices and calculate edges concurrently
    price_matrix_task = fetch_prices(
        shopping_list.ingredients,
        stores,
        price_matrix,
        mock_data=mock_price_data
    )
    edges_task = calculate_edges(shopping_list.home_location, stores)
    
    populated_matrix, edges = await asyncio.gather(price_matrix_task, edges_task)
    
    return populated_matrix, edges
