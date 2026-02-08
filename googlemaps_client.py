"""
Google Maps API Client for AI Grocery Agent

Provides:
- Geographic validation for San Francisco Bay Area (West Bay corridor)
- Real driving times via Distance Matrix API
- Address geocoding with service area enforcement
- Store location validation

Region: San Francisco to San Jose corridor only
Bounding Box:
  North: 37.81 (San Francisco)
  South: 37.33 (San Jose)
  West: -122.52 (Pacific Coast)
  East: -121.80 (Bay Front)
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import googlemaps
from googlemaps.exceptions import ApiError

logger = logging.getLogger(__name__)


# Geographic bounds for San Francisco Bay Area (West Bay)
WEST_BAY_BOUNDS = {
    "north": 37.81,  # San Francisco
    "south": 37.33,  # San Jose
    "west": -122.52,  # Pacific Coast
    "east": -121.80,  # Bay Front
}


@dataclass
class GeoLocation:
    """Geographic coordinates with validation"""
    latitude: float
    longitude: float
    address: Optional[str] = None

    def is_in_service_area(self) -> bool:
        """Check if location is within West Bay service area"""
        return (
            WEST_BAY_BOUNDS["south"] <= self.latitude <= WEST_BAY_BOUNDS["north"]
            and WEST_BAY_BOUNDS["west"] <= self.longitude <= WEST_BAY_BOUNDS["east"]
        )


@dataclass
class RouteInfo:
    """Route information from Google Maps"""
    origin: str
    destination: str
    distance_meters: int
    duration_seconds: int
    duration_in_traffic_seconds: Optional[int]

    @property
    def distance_km(self) -> float:
        """Distance in kilometers"""
        return self.distance_meters / 1000.0

    @property
    def duration_minutes(self) -> float:
        """Duration in minutes (uses traffic if available)"""
        seconds = self.duration_in_traffic_seconds or self.duration_seconds
        return seconds / 60.0


class ServiceAreaError(Exception):
    """Raised when location is outside service area"""
    pass


class GoogleMapsClient:
    """Google Maps API client with West Bay geographic filtering"""

    def __init__(self, api_key: str):
        """
        Initialize Google Maps client.

        Args:
            api_key: Google Maps API key

        Raises:
            ValueError: If API key is invalid
        """
        if not api_key:
            raise ValueError("Google Maps API key is required")

        self.client = googlemaps.Client(key=api_key)
        logger.info("Google Maps client initialized")

    def geocode_address(self, address: str) -> GeoLocation:
        """
        Geocode address and validate service area.

        Args:
            address: Street address to geocode

        Returns:
            GeoLocation with validated coordinates

        Raises:
            ServiceAreaError: If address is outside West Bay
            ApiError: If geocoding fails
        """
        try:
            # Bias results to Bay Area
            geocode_result = self.client.geocode(
                address,
                region="us",
                components={"administrative_area": "CA"}
            )

            if not geocode_result:
                raise ValueError(f"Could not geocode address: {address}")

            # Get first result
            result = geocode_result[0]
            location = result["geometry"]["location"]

            geo_loc = GeoLocation(
                latitude=location["lat"],
                longitude=location["lng"],
                address=result["formatted_address"]
            )

            # Validate service area
            if not geo_loc.is_in_service_area():
                raise ServiceAreaError(
                    f"Address '{address}' is outside our service area. "
                    f"We only serve the San Francisco Bay Area (West Bay) "
                    f"corridor between San Francisco and San Jose. "
                    f"Location: ({geo_loc.latitude:.4f}, {geo_loc.longitude:.4f})"
                )

            logger.info(f"Geocoded: {address} -> ({geo_loc.latitude:.4f}, {geo_loc.longitude:.4f})")
            return geo_loc

        except ApiError as e:
            logger.error(f"Google Maps API error: {e}")
            raise

    def validate_store_location(self, latitude: float, longitude: float, store_name: str) -> bool:
        """
        Validate that store location is within service area.

        Args:
            latitude: Store latitude
            longitude: Store longitude
            store_name: Store name for logging

        Returns:
            True if in service area, False otherwise
        """
        geo_loc = GeoLocation(latitude=latitude, longitude=longitude)
        in_area = geo_loc.is_in_service_area()

        if not in_area:
            logger.warning(
                f"Store '{store_name}' at ({latitude:.4f}, {longitude:.4f}) "
                f"is outside West Bay service area"
            )

        return in_area

    def get_distance_matrix(
        self,
        origins: List[str],
        destinations: List[str],
        mode: str = "driving",
        departure_time: str = "now"
    ) -> Dict:
        """
        Get distance matrix with real-time traffic.

        Args:
            origins: List of origin addresses or lat/lng tuples
            destinations: List of destination addresses or lat/lng tuples
            mode: Travel mode (driving, walking, transit, bicycling)
            departure_time: When to depart ("now" or timestamp)

        Returns:
            Distance matrix results

        Raises:
            ApiError: If API call fails
        """
        try:
            result = self.client.distance_matrix(
                origins=origins,
                destinations=destinations,
                mode=mode,
                departure_time=departure_time,
                traffic_model="best_guess",
                units="metric"
            )

            return result

        except ApiError as e:
            logger.error(f"Distance Matrix API error: {e}")
            raise

    def get_route_info(
        self,
        origin: str,
        destination: str,
        departure_time: str = "now"
    ) -> RouteInfo:
        """
        Get detailed route information between two points.

        Args:
            origin: Origin address or lat/lng string
            destination: Destination address or lat/lng string
            departure_time: When to depart ("now" or timestamp)

        Returns:
            RouteInfo with distance and duration

        Raises:
            ApiError: If API call fails
            ValueError: If route not found
        """
        matrix = self.get_distance_matrix(
            origins=[origin],
            destinations=[destination],
            departure_time=departure_time
        )

        # Extract result
        element = matrix["rows"][0]["elements"][0]

        if element["status"] != "OK":
            raise ValueError(
                f"Could not find route from {origin} to {destination}: "
                f"{element.get('status', 'UNKNOWN_ERROR')}"
            )

        # Extract duration in traffic if available
        duration_in_traffic = None
        if "duration_in_traffic" in element:
            duration_in_traffic = element["duration_in_traffic"]["value"]

        return RouteInfo(
            origin=origin,
            destination=destination,
            distance_meters=element["distance"]["value"],
            duration_seconds=element["duration"]["value"],
            duration_in_traffic_seconds=duration_in_traffic
        )

    def get_travel_time_minutes(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float
    ) -> float:
        """
        Get travel time in minutes between coordinates.

        Args:
            origin_lat: Origin latitude
            origin_lng: Origin longitude
            dest_lat: Destination latitude
            dest_lng: Destination longitude

        Returns:
            Travel time in minutes (with traffic)
        """
        origin = f"{origin_lat},{origin_lng}"
        destination = f"{dest_lat},{dest_lng}"

        route = self.get_route_info(origin, destination)
        return route.duration_minutes

    def estimate_travel_cost(self, distance_km: float) -> float:
        """
        Estimate travel cost based on distance.

        Uses IRS standard mileage rate for 2024: $0.67/mile

        Args:
            distance_km: Distance in kilometers

        Returns:
            Estimated cost in USD
        """
        MILES_PER_KM = 0.621371
        COST_PER_MILE = 0.67  # IRS 2024 rate

        miles = distance_km * MILES_PER_KM
        return round(miles * COST_PER_MILE, 2)


if __name__ == "__main__":
    # Example usage
    import os
    from dotenv import load_dotenv

    logging.basicConfig(level=logging.INFO)
    load_dotenv()

    api_key = os.getenv("GOOGLEMAPS_API_KEY")
    if not api_key:
        print("Error: GOOGLEMAPS_API_KEY not set")
        exit(1)

    client = GoogleMapsClient(api_key)

    # Test geocoding
    try:
        loc = client.geocode_address("1 Market St, San Francisco, CA")
        print(f"✓ Geocoded: {loc.address}")
        print(f"  Coordinates: ({loc.latitude}, {loc.longitude})")
        print(f"  In service area: {loc.is_in_service_area()}")
    except ServiceAreaError as e:
        print(f"✗ {e}")

    # Test route
    try:
        route = client.get_route_info(
            "San Francisco, CA",
            "San Jose, CA"
        )
        print(f"\n✓ Route: {route.origin} -> {route.destination}")
        print(f"  Distance: {route.distance_km:.2f} km")
        print(f"  Duration: {route.duration_minutes:.1f} minutes")
        print(f"  Cost: ${client.estimate_travel_cost(route.distance_km):.2f}")
    except Exception as e:
        print(f"✗ Route error: {e}")
