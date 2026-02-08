"""
Shopping Graph Solver - Optimal Route and Basket Optimization

This module implements the "Brain" that finds the cheapest combination of Time + Money.

Specifications:
- Cost Formula: Total Score = (Travel Time * User Hourly Value) + (Sum of Item Prices)
- Logic: Brute force permutations for routes of length 1 and 2
- Basket Optimization: Pick lowest price for each item across stores in the route
- Output: JSON summary with winner route, savings, and item assignments
"""

import json
from itertools import permutations
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from shopping_graph import (
    Store,
    ShoppingList,
    PriceMatrix,
    RouteSegment,
)


@dataclass
class ItemAssignment:
    """Assignment of an item to a specific store in the route."""
    ingredient: str
    store_name: str
    price: float


@dataclass
class RouteOption:
    """A complete route option with optimized basket and total cost."""
    route: List[Optional[Store]]  # e.g., [None, Store A, Store B, None] or [None, Store A, None]
    route_names: List[str]  # Human-readable route names
    stores_visited: List[Store]  # The actual stores in this route (excluding Home)
    
    travel_cost_total: float
    travel_time_total: float
    travel_time_value_cost: float
    
    item_assignments: List[ItemAssignment]
    basket_cost: float
    
    total_cost: float  # travel_time_value_cost + basket_cost
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "route": self.route_names,
            "stores_visited": [s.name for s in self.stores_visited],
            "travel": {
                "time_minutes": round(self.travel_time_total, 2),
                "cost_dollars": round(self.travel_cost_total, 2),
                "time_value_cost": round(self.travel_time_value_cost, 2),
            },
            "basket": {
                "items": [
                    {
                        "ingredient": item.ingredient,
                        "store": item.store_name,
                        "price": round(item.price, 2),
                    }
                    for item in self.item_assignments
                ],
                "total_cost": round(self.basket_cost, 2),
            },
            "total_cost": round(self.total_cost, 2),
        }


@dataclass
class SolverResult:
    """Final result from the solver."""
    winner_route: RouteOption
    all_routes: List[RouteOption]
    savings_vs_second_best: float
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to formatted JSON string."""
        result_dict = {
            "winner_route": self.winner_route.to_dict(),
            "total_routes_analyzed": len(self.all_routes),
            "savings_vs_second_best": round(self.savings_vs_second_best, 2),
            "all_routes": [route.to_dict() for route in self.all_routes],
        }
        return json.dumps(result_dict, indent=indent)


def get_route_edges(
    home_stores_route: List[Optional[Store]],
    all_edges: List[RouteSegment],
) -> Tuple[float, float]:
    """
    Calculate total travel time and cost for a given route.
    
    Args:
        home_stores_route: List like [None, Store A, Store B, None]
        all_edges: All RouteSegment objects
        
    Returns:
        Tuple of (total_travel_time_minutes, total_travel_cost)
    """
    total_time = 0.0
    total_cost = 0.0
    
    # Traverse the route: Home -> A -> B -> ... -> Home
    for i in range(len(home_stores_route) - 1):
        origin = home_stores_route[i]
        destination = home_stores_route[i + 1]
        
        # Find the edge connecting origin to destination
        # Match by name (origin None = Home)
        origin_name = None if origin is None else origin.name
        dest_name = None if destination is None else destination.name
        
        matching_edge = None
        for edge in all_edges:
            edge_origin_name = None if edge.origin is None else edge.origin.name
            edge_dest_name = None if edge.destination is None else edge.destination.name
            
            if edge_origin_name == origin_name and edge_dest_name == dest_name:
                matching_edge = edge
                break
        
        if matching_edge:
            total_time += matching_edge.travel_time_minutes
            total_cost += matching_edge.travel_cost
        else:
            # Edge not found - should not happen with proper graph
            print(f"Warning: Edge not found for {origin_name} -> {dest_name}")
            return float('inf'), float('inf')
    
    return total_time, total_cost


def optimize_basket(
    stores_in_route: List[Store],
    ingredient_list: List[str],
    price_matrix: PriceMatrix,
) -> Tuple[List[ItemAssignment], float]:
    """
    Optimize the shopping basket for a given route.
    
    For each ingredient, pick the cheapest store among those in the route.
    If ingredient is unavailable, add $10 penalty (prevents bad routes from being chosen).
    
    Args:
        stores_in_route: List of Store objects in the route
        ingredient_list: List of ingredients to buy
        price_matrix: PriceMatrix object
        
    Returns:
        Tuple of (item_assignments, total_basket_cost)
    """
    MISSING_ITEM_PENALTY = 10.0  # $10 penalty for each missing item
    
    item_assignments = []
    total_cost = 0.0
    
    for ingredient in ingredient_list:
        # Get prices for this ingredient across all stores in route
        best_price = float('inf')
        best_store_name = None
        
        for store in stores_in_route:
            price = price_matrix.get_price(ingredient, store.name)
            if price < best_price:
                best_price = price
                best_store_name = store.name
        
        # If available at a store, add actual price; otherwise add $10 penalty
        if best_price < float('inf'):
            item_assignments.append(
                ItemAssignment(
                    ingredient=ingredient,
                    store_name=best_store_name,
                    price=best_price,
                )
            )
            total_cost += best_price
        else:
            # Ingredient not available at any store in route → add $10 penalty
            item_assignments.append(
                ItemAssignment(
                    ingredient=ingredient,
                    store_name="NOT_AVAILABLE",
                    price=MISSING_ITEM_PENALTY,
                )
            )
            total_cost += MISSING_ITEM_PENALTY
    
    return item_assignments, total_cost


def evaluate_route(
    home_stores_route: List[Optional[Store]],
    stores_visited: List[Store],
    shopping_list: ShoppingList,
    price_matrix: PriceMatrix,
    all_edges: List[RouteSegment],
) -> RouteOption:
    """
    Evaluate a single route option and optimize its basket.
    
    Args:
        home_stores_route: Full route including Home [None, Store A, ..., None]
        stores_visited: Just the stores (no Home)
        shopping_list: ShoppingList object
        price_matrix: PriceMatrix object
        all_edges: All RouteSegment objects
        
    Returns:
        RouteOption with calculated costs
    """
    # Calculate travel costs
    travel_time, travel_cost = get_route_edges(home_stores_route, all_edges)
    travel_time_value_cost = travel_time * (shopping_list.hourly_time_value / 60)
    
    # Optimize basket
    item_assignments, basket_cost = optimize_basket(
        stores_visited,
        shopping_list.ingredients,
        price_matrix,
    )
    
    # Total cost
    total_cost = travel_time_value_cost + basket_cost
    
    # Route names for display
    route_names = ["HOME"]
    for store in stores_visited:
        route_names.append(store.name)
    route_names.append("HOME")
    
    return RouteOption(
        route=home_stores_route,
        route_names=route_names,
        stores_visited=stores_visited,
        travel_cost_total=travel_cost,
        travel_time_total=travel_time,
        travel_time_value_cost=travel_time_value_cost,
        item_assignments=item_assignments,
        basket_cost=basket_cost,
        total_cost=total_cost,
    )


def solve_best_route(
    shopping_list: ShoppingList,
    stores: List[Store],
    price_matrix: PriceMatrix,
    edges: List[RouteSegment],
) -> SolverResult:
    """
    Find the optimal route that minimizes Total Cost = (Time Cost) + (Item Prices).
    
    Generates all possible routes:
    - Length 1: Home -> A -> Home
    - Length 2: Home -> A -> B -> Home
    
    For each route, optimizes the basket by picking the lowest price for each item
    among the stores in that route.
    
    Args:
        shopping_list: ShoppingList object
        stores: List of Store objects
        price_matrix: PriceMatrix with prices
        edges: List of RouteSegment objects with travel costs/times
        
    Returns:
        SolverResult with winner route and all evaluated options
    """
    evaluated_routes = []
    
    # Generate routes: length 1 and length 2
    # Length 1: single store visits
    for store in stores:
        home_store_route = [None, store, None]
        route_option = evaluate_route(
            home_store_route,
            [store],
            shopping_list,
            price_matrix,
            edges,
        )
        evaluated_routes.append(route_option)
    
    # Length 2: two store visits
    for perm in permutations(stores, 2):
        store_a, store_b = perm
        home_store_route = [None, store_a, store_b, None]
        route_option = evaluate_route(
            home_store_route,
            [store_a, store_b],
            shopping_list,
            price_matrix,
            edges,
        )
        evaluated_routes.append(route_option)
    
    # Sort by total cost
    evaluated_routes.sort(key=lambda r: r.total_cost)
    
    # Winner is the cheapest route
    winner_route = evaluated_routes[0]
    
    # Calculate savings vs second best
    if len(evaluated_routes) > 1:
        savings = evaluated_routes[1].total_cost - winner_route.total_cost
    else:
        savings = 0.0
    
    return SolverResult(
        winner_route=winner_route,
        all_routes=evaluated_routes,
        savings_vs_second_best=savings,
    )


# ============================================================================
# UTILITY FUNCTION: Display results in a human-readable format
# ============================================================================

def print_solver_result(result: SolverResult, hourly_rate: float = 20.0) -> None:
    """Pretty-print the solver result.
    
    Args:
        result: SolverResult object
        hourly_rate: Hourly time value for display (default $20/hr)
    """
    print("\n" + "=" * 80)
    print("🏆 OPTIMAL SHOPPING ROUTE")
    print("=" * 80)
    
    winner = result.winner_route
    print(f"\n📍 Route: {' → '.join(winner.route_names)}")
    print(f"\n⏱️  Travel Time: {winner.travel_time_total:.2f} minutes")
    print(f"💰 Travel Cost: ${winner.travel_cost_total:.2f}")
    print(f"📊 Time Value (at ${hourly_rate:.0f}/hr): ${winner.travel_time_value_cost:.2f}")
    
    print(f"\n🛒 Shopping List:")
    print("-" * 80)
    for item in winner.item_assignments:
        if item.price < float('inf'):
            print(f"  • {item.ingredient:20} @ {item.store_name:15} = ${item.price:7.2f}")
        else:
            print(f"  • {item.ingredient:20} @ {'NOT_AVAILABLE':15} = {'UNAVAILABLE':>7}")
    
    print(f"\n💵 Basket Total: ${winner.basket_cost:.2f}")
    print(f"{'─' * 80}")
    print(f"🎯 TOTAL COST: ${winner.total_cost:.2f}")
    
    if result.savings_vs_second_best > 0:
        print(f"✨ Savings vs 2nd best route: ${result.savings_vs_second_best:.2f}")
    
    print(f"\nTotal routes analyzed: {len(result.all_routes)}")
    print("=" * 80)
