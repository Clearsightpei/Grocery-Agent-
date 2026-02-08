"""
LLM Integration - Convert Shopping Solver Results to Natural Language Plans

This module connects the solver output to DeepSeek API to generate
human-readable shopping instructions based on optimization results.
"""

import json
import os
from typing import Optional, Dict, List
from dataclasses import dataclass
from dotenv import load_dotenv
from solver import SolverResult, ItemAssignment

# Load environment variables from .env file
load_dotenv()


@dataclass
class ShoppingPlan:
    """A natural language shopping plan with structured data."""
    summary: str  # Human-readable plan
    stores_to_visit: List[str]  # Ordered list of stores
    items_by_store: Dict[str, List[Dict]]  # {store: [{item, price}, ...]}
    unavailable_items: List[str]  # Items that can't be bought
    total_cost: float
    travel_time: float
    savings_info: str


def extract_shopping_plan(result: SolverResult) -> ShoppingPlan:
    """
    Extract structured shopping plan from solver results.
    
    Args:
        result: SolverResult from solve_best_route()
        
    Returns:
        ShoppingPlan with organized data
    """
    winner = result.winner_route
    
    MISSING_ITEM_PENALTY = 10.0
    
    # Group items by store
    items_by_store = {}
    unavailable_items = []
    
    for item in winner.item_assignments:
        # If item price equals $10 penalty, it's a missing item
        if item.store_name == "NOT_AVAILABLE" and item.price == MISSING_ITEM_PENALTY:
            unavailable_items.append(item.ingredient)
        else:
            if item.store_name not in items_by_store:
                items_by_store[item.store_name] = []
            items_by_store[item.store_name].append({
                "ingredient": item.ingredient,
                "price": round(item.price, 2)
            })
    
    # Ordered store list
    stores_to_visit = [s.name for s in winner.stores_visited]
    
    # Savings info
    if result.savings_vs_second_best > 0:
        savings_info = f"You save ${result.savings_vs_second_best:.2f} compared to the 2nd best route."
    else:
        savings_info = "This is the optimal route."
    
    return ShoppingPlan(
        summary="",  # Will be filled by LLM
        stores_to_visit=stores_to_visit,
        items_by_store=items_by_store,
        unavailable_items=unavailable_items,
        total_cost=round(winner.total_cost, 2),
        travel_time=round(winner.travel_time_total, 2),
        savings_info=savings_info
    )


def create_shopping_plan_prompt(plan: ShoppingPlan, hourly_rate: float = 20.0) -> str:
    """
    Create a prompt for the LLM to generate a shopping plan.
    
    Args:
        plan: ShoppingPlan with extracted data
        hourly_rate: User's hourly time value
        
    Returns:
        Prompt string for the LLM
    """
    prompt = f"""You are a helpful shopping assistant. Generate a clear, friendly shopping plan based on this optimization result.

SHOPPING PLAN DATA:
Stores to visit (in order): {', '.join(plan.stores_to_visit) if plan.stores_to_visit else 'None found'}
Total estimated cost: ${plan.total_cost}
Travel time: {plan.travel_time} minutes
Hourly time value: ${hourly_rate}/hr

ITEMS TO BUY BY STORE:
"""
    
    if plan.items_by_store:
        for store, items in plan.items_by_store.items():
            prompt += f"\n{store}:\n"
            for item in items:
                prompt += f"  • {item['ingredient']}: ${item['price']}\n"
            total_store = sum(i['price'] for i in items)
            prompt += f"  Subtotal: ${total_store:.2f}\n"
    else:
        prompt += "No items to buy (all unavailable)\n"
    
    if plan.unavailable_items:
        prompt += f"\nITEMS THAT CAN'T BE BOUGHT AT ANY STORE:\n"
        for item in plan.unavailable_items:
            prompt += f"  ✗ {item} - Not available\n"
    
    prompt += f"\n{plan.savings_info}\n"
    
    prompt += """
Please generate a friendly, concise shopping plan that:
1. Explains the recommended route and why it's optimal
2. Lists items to buy at each store in a clear format
3. Mentions any items that can't be bought
4. Provides a brief summary of the total cost and time savings
5. Use a friendly, helpful tone

Format as a clear, actionable plan the user can follow while shopping."""
    
    return prompt


class LLMShoppingPlanner:
    """
    Shopping plan generator using DeepSeek API.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the DeepSeek LLM planner.
        
        Args:
            api_key: DeepSeek API key (or uses DeepSeek_API_Key from .env)
        """
        self.api_key = api_key or os.getenv("DeepSeek_API_Key") or os.getenv("DEEPSEEK_API_KEY")
        
        if not self.api_key:
            raise ValueError("DeepSeek API key not provided. Set DEEPSEEK_API_KEY env var or pass api_key parameter")
        
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )
        except ImportError:
            raise ImportError("Install openai: pip install openai")
    
    def generate_plan(
        self,
        result: SolverResult,
        hourly_rate: float = 20.0,
        model: Optional[str] = None
    ) -> str:
        """
        Generate a natural language shopping plan from solver results using DeepSeek.
        
        Args:
            result: SolverResult from solve_best_route()
            hourly_rate: User's hourly time value
            model: DeepSeek model (default: "deepseek-chat")
            
        Returns:
            Natural language shopping plan
        """
        # Extract structured plan
        plan = extract_shopping_plan(result)
        
        # Create prompt for LLM
        prompt = create_shopping_plan_prompt(plan, hourly_rate)
        
        # Generate response using DeepSeek
        try:
            response = self.client.chat.completions.create(
                model=model or "deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a helpful shopping assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"DeepSeek API error: {e}")


def print_shopping_plan(result: SolverResult, hourly_rate: float = 20.0, use_llm: bool = False, api_key: Optional[str] = None) -> None:
    """
    Print a shopping plan from solver results.
    
    Args:
        result: SolverResult from solve_best_route()
        hourly_rate: User's hourly time value
        use_llm: If True, use DeepSeek LLM to generate plan
        api_key: DeepSeek API key (optional, uses env var if not provided)
    """
    if use_llm:
        try:
            planner = LLMShoppingPlanner(api_key=api_key)
            plan_text = planner.generate_plan(result, hourly_rate)
            print(plan_text)
        except Exception as e:
            print(f"Error generating LLM plan: {e}")
            print("Falling back to structured plan...\n")
            _print_structured_plan(result, hourly_rate)
    else:
        _print_structured_plan(result, hourly_rate)


def _print_structured_plan(result: SolverResult, hourly_rate: float) -> None:
    """Print a structured shopping plan without LLM."""
    plan = extract_shopping_plan(result)
    
    print("\n" + "=" * 70)
    print("🛍️  YOUR OPTIMIZED SHOPPING PLAN")
    print("=" * 70)
    
    if plan.stores_to_visit:
        print(f"\n📍 ROUTE: {' → '.join(plan.stores_to_visit)}")
    else:
        print("\n📍 ROUTE: No stores have all items")
    
    print(f"\n⏱️  TRAVEL TIME: {plan.travel_time} minutes")
    print(f"💰 TOTAL COST: ${plan.total_cost}")
    
    if plan.items_by_store:
        print(f"\n🛒 SHOPPING LIST BY STORE:")
        print("-" * 70)
        for store in plan.stores_to_visit:
            if store in plan.items_by_store:
                print(f"\n  {store}:")
                for item in plan.items_by_store[store]:
                    print(f"    • {item['ingredient']:25} ${item['price']:7.2f}")
                subtotal = sum(i['price'] for i in plan.items_by_store[store])
                print(f"    {'─' * 35}")
                print(f"    Subtotal: ${subtotal:7.2f}")
    
    if plan.unavailable_items:
        print(f"\n❌ CAN'T BE BOUGHT (Not available at any store):")
        print("-" * 70)
        for item in plan.unavailable_items:
            print(f"  ✗ {item}")
    
    print(f"\n✨ {plan.savings_info}")
    print("=" * 70)
