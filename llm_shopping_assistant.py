"""
Complete Shopping Assistant Example with DeepSeek LLM Integration

Demonstrates how to use the solver with DeepSeek for natural language output.
"""

import asyncio
import os
from shopping_graph import (
    Store,
    GeoLocation,
    ShoppingList,
    build_shopping_graph,
)
from solver import solve_best_route
from llm_integration import (
    print_shopping_plan,
    LLMShoppingPlanner,
    extract_shopping_plan,
)


async def example_with_structured_output():
    """Example showing structured shopping plan (no LLM needed)."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Structured Shopping Plan (No LLM)")
    print("=" * 80)
    
    # Setup
    home = GeoLocation(latitude=40.7128, longitude=-74.0060)
    
    stores = [
        Store("Whole Foods", "123 Main St", GeoLocation(40.7150, -74.0055)),
        Store("Trader Joe's", "456 Park Ave", GeoLocation(40.7100, -74.0100)),
        Store("Costco", "789 Broadway", GeoLocation(40.7200, -74.0000)),
    ]
    
    shopping_list = ShoppingList(
        ingredients=["Milk", "Eggs", "Cheese", "Bread", "Butter"],
        hourly_time_value=20.0,
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
    
    # Solve
    price_matrix, edges = await build_shopping_graph(
        shopping_list, stores, mock_price_data=mock_prices
    )
    
    result = solve_best_route(shopping_list, stores, price_matrix, edges)
    
    # Display plan (structured, no LLM)
    print_shopping_plan(result, hourly_rate=shopping_list.hourly_time_value, use_llm=False)


async def example_with_unavailable_items():
    """Example showing how unavailable items are handled."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Items That Can't Be Bought")
    print("=" * 80)
    
    home = GeoLocation(latitude=40.7128, longitude=-74.0060)
    
    stores = [
        Store("Local Supermarket", "100 Main St", GeoLocation(40.7140, -74.0050)),
        Store("Health Store", "200 Health Ave", GeoLocation(40.7110, -74.0070)),
    ]
    
    shopping_list = ShoppingList(
        ingredients=["Milk", "Eggs", "Quinoa", "Matcha Tea", "Kombucha"],
        hourly_time_value=20.0,
        home_location=home
    )
    
    # Limited availability
    mock_prices = {
        "Local Supermarket": {
            "Milk": 3.99,
            "Eggs": 2.99,
            "Quinoa": float('inf'),  # Not available
            "Matcha Tea": float('inf'),  # Not available
            "Kombucha": 3.49
        },
        "Health Store": {
            "Milk": 4.49,
            "Eggs": 3.99,
            "Quinoa": 12.99,  # Only here
            "Matcha Tea": 14.99,  # Only here
            "Kombucha": float('inf')  # Not available
        },
    }
    
    price_matrix, edges = await build_shopping_graph(
        shopping_list, stores, mock_price_data=mock_prices
    )
    
    result = solve_best_route(shopping_list, stores, price_matrix, edges)
    
    # Show the plan
    print_shopping_plan(result, hourly_rate=shopping_list.hourly_time_value, use_llm=False)
    
    # Also show the extracted plan data
    plan = extract_shopping_plan(result)
    print("\n📊 PLAN DATA BREAKDOWN:")
    print(f"Stores to visit: {plan.stores_to_visit}")
    print(f"Items by store: {plan.items_by_store}")
    print(f"Unavailable items: {plan.unavailable_items}")
    print(f"Total cost: ${plan.total_cost}")


async def example_json_for_api():
    """Example showing JSON output for API integration."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: JSON Output for API Integration")
    print("=" * 80)
    
    home = GeoLocation(latitude=40.7128, longitude=-74.0060)
    
    stores = [
        Store("Store A", "100 A St", GeoLocation(40.7140, -74.0050)),
        Store("Store B", "200 B Ave", GeoLocation(40.7110, -74.0070)),
    ]
    
    shopping_list = ShoppingList(
        ingredients=["Apple", "Banana", "Orange", "Grapes"],
        hourly_time_value=20.0,
        home_location=home
    )
    
    mock_prices = {
        "Store A": {"Apple": 1.99, "Banana": 0.99, "Orange": 2.49, "Grapes": 4.99},
        "Store B": {"Apple": 1.79, "Banana": 1.19, "Orange": 2.29, "Grapes": 4.49},
    }
    
    price_matrix, edges = await build_shopping_graph(
        shopping_list, stores, mock_price_data=mock_prices
    )
    
    result = solve_best_route(shopping_list, stores, price_matrix, edges)
    
    # Extract plan and show as structured data
    plan = extract_shopping_plan(result)
    
    import json
    plan_dict = {
        "stores_to_visit": plan.stores_to_visit,
        "items_by_store": plan.items_by_store,
        "unavailable_items": plan.unavailable_items,
        "total_cost": plan.total_cost,
        "travel_time_minutes": plan.travel_time,
        "savings_info": plan.savings_info,
    }
    
    print("\n📋 SHOPPING PLAN JSON:")
    print(json.dumps(plan_dict, indent=2))


async def example_mock_llm_output():
    """Example using DeepSeek for natural language output."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Natural Language Output (DeepSeek API)")
    print("=" * 80)
    
    home = GeoLocation(latitude=40.7128, longitude=-74.0060)
    
    stores = [
        Store("Safeway", "123 Main St", GeoLocation(40.7140, -74.0050)),
        Store("Trader Joe's", "456 Park Ave", GeoLocation(40.7110, -74.0070)),
        Store("Whole Foods", "789 Broadway", GeoLocation(40.7200, -74.0000)),
    ]
    
    shopping_list = ShoppingList(
        ingredients=["Milk", "Eggs", "Bread", "Cheese", "Butter"],
        hourly_time_value=25.0,
        home_location=home
    )
    
    mock_prices = {
        "Safeway": {
            "Milk": 3.99, "Eggs": 2.99, "Bread": 2.49,
            "Cheese": 5.99, "Butter": 4.49
        },
        "Trader Joe's": {
            "Milk": 3.79, "Eggs": 2.49, "Bread": 2.99,
            "Cheese": 6.49, "Butter": 4.99
        },
        "Whole Foods": {
            "Milk": 4.49, "Eggs": 3.99, "Bread": 3.99,
            "Cheese": 7.99, "Butter": 5.49
        },
    }
    
    price_matrix, edges = await build_shopping_graph(
        shopping_list, stores, mock_price_data=mock_prices
    )
    
    result = solve_best_route(shopping_list, stores, price_matrix, edges)
    
    # Use DeepSeek to generate natural language plan
    planner = LLMShoppingPlanner(api_key=os.getenv("DEEPSEEK_API_KEY"))
    shopping_plan_text = planner.generate_plan(result, hourly_rate=shopping_list.hourly_time_value)
    print(shopping_plan_text)


async def example_real_world_scenario():
    """Real-world scenario: Mixed item availability across stores."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Real-World Scenario - Mixed Availability")
    print("=" * 80)
    
    home = GeoLocation(latitude=40.7128, longitude=-74.0060)
    
    stores = [
        Store("Costco", "100 Warehouse Blvd", GeoLocation(40.7100, -74.0080)),
        Store("Whole Foods Market", "200 Premium St", GeoLocation(40.7150, -74.0050)),
        Store("Local Bodega", "300 Corner Shop", GeoLocation(40.7130, -74.0065)),
    ]
    
    shopping_list = ShoppingList(
        ingredients=[
            "Organic Milk",
            "Free-Range Eggs",
            "Bulk Rice",
            "Greek Yogurt",
            "Almond Butter",
            "Gluten-Free Bread"
        ],
        hourly_time_value=30.0,  # Busy professional
        home_location=home
    )
    
    # Scattered availability
    mock_prices = {
        "Costco": {
            "Organic Milk": 4.99,
            "Free-Range Eggs": 5.99,
            "Bulk Rice": 8.99,
            "Greek Yogurt": 3.99,
            "Almond Butter": float('inf'),  # Not here
            "Gluten-Free Bread": float('inf')  # Not here
        },
        "Whole Foods Market": {
            "Organic Milk": 5.99,
            "Free-Range Eggs": 6.99,
            "Bulk Rice": float('inf'),  # Not here
            "Greek Yogurt": 4.99,
            "Almond Butter": 12.99,
            "Gluten-Free Bread": 7.99
        },
        "Local Bodega": {
            "Organic Milk": 5.49,
            "Free-Range Eggs": 6.49,
            "Bulk Rice": float('inf'),
            "Greek Yogurt": float('inf'),
            "Almond Butter": float('inf'),
            "Gluten-Free Bread": 6.99
        },
    }
    
    price_matrix, edges = await build_shopping_graph(
        shopping_list, stores, mock_price_data=mock_prices
    )
    
    result = solve_best_route(shopping_list, stores, price_matrix, edges)
    
    # Generate both structured and LLM output
    print("\n--- STRUCTURED PLAN ---")
    print_shopping_plan(result, hourly_rate=shopping_list.hourly_time_value, use_llm=False)
    
    print("\n--- NATURAL LANGUAGE PLAN (Mock LLM) ---")
    planner = LLMShoppingPlanner(llm_backend="mock")
    plan_text = planner.generate_plan(result, hourly_rate=shopping_list.hourly_time_value)
    print(plan_text)


async def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("SHOPPING ASSISTANT WITH LLM INTEGRATION")
    print("=" * 80)
    
    await example_with_structured_output()
    await example_with_unavailable_items()
    await example_json_for_api()
    await example_mock_llm_output()
    await example_real_world_scenario()
    
    print("\n" + "=" * 80)
    print("✅ All examples completed!")
    print("=" * 80)
    
    print("""
NEXT STEPS:
1. Replace "mock" backend with real LLM:
   planner = LLMShoppingPlanner(llm_backend="openai", api_key="sk-...")
   planner = LLMShoppingPlanner(llm_backend="anthropic", api_key="sk-ant-...")
   planner = LLMShoppingPlanner(llm_backend="ollama")

2. Set environment variables:
   export OPENAI_API_KEY="sk-..."
   export ANTHROPIC_API_KEY="sk-ant-..."

3. Install required packages:
   pip install openai anthropic ollama
""")


if __name__ == "__main__":
    asyncio.run(main())
