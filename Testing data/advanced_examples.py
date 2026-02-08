"""
Advanced Usage Examples for the Shopping Graph Solver

Demonstrates various use cases and customizations.
"""

import asyncio
import json
from shopping_graph import (
    Store,
    GeoLocation,
    ShoppingList,
    build_shopping_graph,
)
from solver import solve_best_route, print_solver_result


async def example_1_basic_usage():
    """Simple 3-store scenario."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Basic 3-Store Shopping Optimization")
    print("=" * 80)
    
    home = GeoLocation(latitude=40.7128, longitude=-74.0060)
    
    stores = [
        Store("Whole Foods", "123 Main St", GeoLocation(40.7150, -74.0055)),
        Store("Trader Joe's", "456 Park Ave", GeoLocation(40.7100, -74.0100)),
        Store("Costco", "789 Broadway", GeoLocation(40.7200, -74.0000)),
    ]
    
    shopping_list = ShoppingList(
        ingredients=["Milk", "Eggs", "Cheese", "Butter", "Bread"],
        hourly_time_value=25.0,
        home_location=home
    )
    
    mock_prices = {
        "Whole Foods": {
            "Milk": 4.49, "Eggs": 3.99, "Cheese": 7.99,
            "Butter": 5.49, "Bread": 3.99
        },
        "Trader Joe's": {
            "Milk": 3.99, "Eggs": 2.99, "Cheese": 6.99,
            "Butter": 4.99, "Bread": 2.99
        },
        "Costco": {
            "Milk": 3.49, "Eggs": 2.49, "Cheese": 5.99,
            "Butter": 4.49, "Bread": 2.49
        },
    }
    
    price_matrix, edges = await build_shopping_graph(
        shopping_list, stores, mock_price_data=mock_prices
    )
    
    result = solve_best_route(shopping_list, stores, price_matrix, edges)
    print_solver_result(result, hourly_rate=shopping_list.hourly_time_value)
    
    return result


async def example_2_high_time_value():
    """User with high hourly rate (prioritizes speed over price)."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: High Time Value ($100/hr) - Prioritize Speed")
    print("=" * 80)
    
    home = GeoLocation(latitude=40.7128, longitude=-74.0060)
    
    stores = [
        Store("Quick Stop", "100 5th Ave", GeoLocation(40.7130, -74.0060)),
        Store("Budget Mart", "500 Main St", GeoLocation(40.7080, -74.0100)),
    ]
    
    # High hourly value = prioritize nearby stores
    shopping_list = ShoppingList(
        ingredients=["Milk", "Eggs", "Bread"],
        hourly_time_value=100.0,  # $100/hr (consultant, executive, etc.)
        home_location=home
    )
    
    mock_prices = {
        "Quick Stop": {
            "Milk": 5.99, "Eggs": 4.99, "Bread": 4.99
        },
        "Budget Mart": {
            "Milk": 3.99, "Eggs": 2.99, "Bread": 2.99
        },
    }
    
    price_matrix, edges = await build_shopping_graph(
        shopping_list, stores, mock_price_data=mock_prices
    )
    
    result = solve_best_route(shopping_list, stores, price_matrix, edges)
    print_solver_result(result, hourly_rate=shopping_list.hourly_time_value)
    
    print(f"\n💡 Insight: At $100/hr, even 5 min of travel = $8.33 in time cost!")
    print(f"   Quick Stop (premium, nearby) may beat Budget Mart (cheap, far).")


async def example_3_partial_availability():
    """Some stores don't have all items."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Partial Availability - Must Visit Multiple Stores")
    print("=" * 80)
    
    home = GeoLocation(latitude=40.7128, longitude=-74.0060)
    
    stores = [
        Store("Organic Market", "100 Health Ave", GeoLocation(40.7145, -74.0055)),
        Store("Asian Supermarket", "200 Chinatown", GeoLocation(40.7140, -74.0010)),
        Store("General Grocer", "300 Common St", GeoLocation(40.7110, -74.0080)),
    ]
    
    shopping_list = ShoppingList(
        ingredients=["Tofu", "Miso", "Rice", "Soy Sauce", "Kimchi"],
        hourly_time_value=20.0,
        home_location=home
    )
    
    # Asian items scattered across stores
    mock_prices = {
        "Organic Market": {
            "Tofu": 4.99, "Miso": float('inf'), "Rice": 3.99,
            "Soy Sauce": float('inf'), "Kimchi": float('inf')
        },
        "Asian Supermarket": {
            "Tofu": 2.99, "Miso": 5.99, "Rice": 1.99,
            "Soy Sauce": 3.49, "Kimchi": 4.99
        },
        "General Grocer": {
            "Tofu": 3.99, "Miso": float('inf'), "Rice": 2.99,
            "Soy Sauce": 2.99, "Kimchi": float('inf')
        },
    }
    
    price_matrix, edges = await build_shopping_graph(
        shopping_list, stores, mock_price_data=mock_prices
    )
    
    result = solve_best_route(shopping_list, stores, price_matrix, edges)
    print_solver_result(result, hourly_rate=shopping_list.hourly_time_value)
    
    print("\n💡 Insight: The solver finds the best combination when items")
    print("   are only available at specific stores.")


async def example_4_json_export():
    """Export results as structured JSON."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: JSON Export for API Integration")
    print("=" * 80)
    
    home = GeoLocation(latitude=40.7128, longitude=-74.0060)
    
    stores = [
        Store("Store A", "Addr A", GeoLocation(40.7140, -74.0050)),
        Store("Store B", "Addr B", GeoLocation(40.7120, -74.0070)),
    ]
    
    shopping_list = ShoppingList(
        ingredients=["Apple", "Banana", "Orange"],
        hourly_time_value=20.0,
        home_location=home
    )
    
    mock_prices = {
        "Store A": {"Apple": 1.99, "Banana": 0.99, "Orange": 2.49},
        "Store B": {"Apple": 1.79, "Banana": 1.19, "Orange": 2.29},
    }
    
    price_matrix, edges = await build_shopping_graph(
        shopping_list, stores, mock_price_data=mock_prices
    )
    
    result = solve_best_route(shopping_list, stores, price_matrix, edges)
    
    # Export as formatted JSON
    json_str = result.to_json(indent=2)
    print(json_str[:500] + "\n... (truncated)")
    
    # Parse and use the JSON
    result_dict = json.loads(json_str)
    winner = result_dict["winner_route"]
    print(f"\n✅ Exported winner route: {' → '.join(winner['route'])}")
    print(f"   Total cost: ${winner['total_cost']}")


async def example_5_sensitivity_analysis():
    """How time value affects the choice."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Sensitivity Analysis - Time Value Impact")
    print("=" * 80)
    
    home = GeoLocation(latitude=40.7128, longitude=-74.0060)
    
    near_store = Store("Near Store", "100 Close Rd", GeoLocation(40.7130, -74.0060))
    far_store = Store("Far Store", "1000 Distant Rd", GeoLocation(40.6900, -74.0000))
    
    ingredients = ["Milk", "Eggs", "Bread"]
    home_loc = home
    
    mock_prices = {
        "Near Store": {"Milk": 5.99, "Eggs": 4.99, "Bread": 3.99},  # Expensive
        "Far Store": {"Milk": 3.99, "Eggs": 2.99, "Bread": 1.99},   # Cheap
    }
    
    # Test different hourly rates
    hourly_rates = [10, 20, 50, 100]
    
    for hourly_rate in hourly_rates:
        shopping_list = ShoppingList(
            ingredients=ingredients,
            hourly_time_value=hourly_rate,
            home_location=home_loc
        )
        
        price_matrix, edges = await build_shopping_graph(
            shopping_list, [near_store, far_store], mock_price_data=mock_prices
        )
        
        result = solve_best_route(shopping_list, [near_store, far_store], price_matrix, edges)
        winner_name = result.winner_route.route_names[1]  # Middle element
        winner_cost = result.winner_route.total_cost
        
        print(f"\n  Hourly Rate: ${hourly_rate}/hr")
        print(f"    → Winner: {winner_name}")
        print(f"    → Total Cost: ${winner_cost:.2f}")
    
    print("\n💡 Insight: As hourly rate increases, nearby (expensive) store")
    print("   becomes more attractive vs. far (cheap) store.")


async def main():
    """Run all examples."""
    
    # Run each example
    example1_result = await example_1_basic_usage()
    await example_2_high_time_value()
    await example_3_partial_availability()
    await example_4_json_export()
    await example_5_sensitivity_analysis()
    
    print("\n" + "=" * 80)
    print("✅ All examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
