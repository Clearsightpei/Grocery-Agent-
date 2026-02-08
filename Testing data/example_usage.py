"""
Example usage of the Shopping Graph system.

Demonstrates:
- Creating Store objects
- Initializing the price matrix
- Populating it with async price fetching
- Calculating route segments
- Running the solver to find the optimal route
"""

import asyncio
from shopping_graph import (
    Store,
    GeoLocation,
    ShoppingList,
    PriceMatrix,
    build_shopping_graph,
)
from solver import solve_best_route, print_solver_result


async def main():
    """Example shopping graph setup."""
    
    # Define locations
    home = GeoLocation(latitude=40.7128, longitude=-74.0060)  # NYC
    
    # Create stores
    store_a = Store(
        name="Store A",
        address="123 Main St, NYC",
        geo_location=GeoLocation(latitude=40.7150, longitude=-74.0055)
    )
    
    store_b = Store(
        name="Store B",
        address="456 Park Ave, NYC",
        geo_location=GeoLocation(latitude=40.7100, longitude=-74.0100)
    )
    
    store_c = Store(
        name="Store C",
        address="789 Broadway, NYC",
        geo_location=GeoLocation(latitude=40.7200, longitude=-74.0000)
    )
    
    stores = [store_a, store_b, store_c]
    
    # Create shopping list
    ingredients = ["Milk", "Eggs", "Bread", "Cheese", "Butter"]
    shopping_list = ShoppingList(
        ingredients=ingredients,
        hourly_time_value=20.0,  # $20/hour
        home_location=home
    )
    
    # Mock price data for demonstration
    mock_prices = {
        "Store A": {
            "Milk": 3.99,
            "Eggs": 2.49,
            "Bread": 2.99,
            "Cheese": 5.99,
            "Butter": 4.49,
        },
        "Store B": {
            "Milk": 3.79,
            "Eggs": 2.99,
            "Bread": 3.49,
            "Cheese": 6.49,
            "Butter": float('inf'),  # Not available
        },
        "Store C": {
            "Milk": 4.19,
            "Eggs": 2.39,
            "Bread": float('inf'),  # Not available
            "Cheese": 5.49,
            "Butter": 4.99,
        },
    }
    
    print("Building shopping graph...")
    print("=" * 60)
    
    # Build the entire graph (prices + routes)
    price_matrix, edges = await build_shopping_graph(
        shopping_list,
        stores,
        mock_price_data=mock_prices
    )
    
    print("\n✓ Price Matrix:")
    print("-" * 60)
    print(price_matrix.to_dataframe())
    
    print("\n✓ Route Segments (Home <-> Stores and Store <-> Store):")
    print("-" * 60)
    for edge in edges[:5]:  # Show first 5 for brevity
        origin_name = edge.origin.name if edge.origin else "HOME"
        dest_name = edge.destination.name if edge.destination else "HOME"
        print(
            f"{origin_name:15} -> {dest_name:15} "
            f"| Time: {edge.travel_time_minutes:6.2f} min "
            f"| Cost: ${edge.travel_cost:6.2f}"
        )
    print(f"... and {len(edges) - 5} more routes")
    
    print("\n✓ Store Inventory:")
    print("-" * 60)
    for store in stores:
        available = [ing for ing, avail in store.inventory.items() if avail]
        unavailable = [ing for ing, avail in store.inventory.items() if not avail]
        print(f"{store.name}:")
        print(f"  Available: {', '.join(available)}")
        print(f"  Unavailable: {', '.join(unavailable)}")
    
    print("\n✓ Time Cost Calculations:")
    print("-" * 60)
    test_times = [15, 30, 60]
    for minutes in test_times:
        cost = shopping_list.calculate_time_cost(minutes)
        print(f"  {minutes:2d} minutes of travel = ${cost:6.2f} (at ${shopping_list.hourly_time_value:.0f}/hr)")
    
    # =========================================================================
    # STEP 3: SOLVE FOR THE OPTIMAL ROUTE
    # =========================================================================
    
    print("\n" + "=" * 60)
    print("SOLVING FOR OPTIMAL ROUTE...")
    print("=" * 60)
    
    result = solve_best_route(shopping_list, stores, price_matrix, edges)
    
    # Display results
    print_solver_result(result, hourly_rate=shopping_list.hourly_time_value)
    
    # Also display as JSON
    print("\n✓ JSON Output:")
    print("-" * 60)
    print(result.to_json())


if __name__ == "__main__":
    asyncio.run(main())
