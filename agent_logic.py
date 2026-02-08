"""
Agent brain for the AI Grocery Agent - PRODUCTION VERSION

- DeepSeek API for meal planning (REQUIRED - no fallback)
- Real pricing via database + SERPAPI (no mock data)
- San Francisco Bay Area geographic restriction
- PostgreSQL database as source of truth

**GEOGRAPHIC RESTRICTION:**
All operations limited to SF Bay Area (West Bay corridor: SF to San Jose)
"""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from openai import OpenAI
from playwright.async_api import async_playwright

# Load API keys from .env file
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# --------------------- Constants ---------------------

# Store names (for backward compatibility)
TRADER_JOES_NAME = "Trader Joe's"
SAFEWAY_NAME = "Safeway"

# Store URLs (for optional Playwright visits)
TRADER_JOES_URL = "https://www.traderjoes.com/home/products"
SAFEWAY_URL = (
    "https://www.safeway.com/ways-to-shop.html"
    "?CMPID=ps_swy_eas_ecom_goo_20200803_7727860248_81363037156_301138611504"
)

# Days of the week
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# --------------------- Pydantic models ---------------------


class DayMeal(BaseModel):
    day: str
    dish_name: str = Field(..., alias="dish")
    main_ingredients: List[str]
    recipe: str


class MealPlan(BaseModel):
    user_taste_profile: str
    meals: List[DayMeal]


# --------------------- LLM Meal Plan Generation ---------------------

MEAL_PLAN_PROMPT = """You are a helpful chef assistant. Given a user's taste profile, produce a 7-day dinner plan (dinners only).

IMPORTANT: Return ONLY a valid JSON object (no markdown, no extra text). The JSON must be in this exact format:
{
  "user_taste_profile": "the user's taste profile",
  "meals": [
    {
      "day": "Monday",
      "dish": "Dish Name",
      "main_ingredients": ["ingredient1", "ingredient2", "ingredient3"],
      "recipe": "1. Step one\\n2. Step two\\n3. Step three"
    },
    {
      "day": "Tuesday",
      "dish": "Another Dish",
      "main_ingredients": ["ingredient4", "ingredient5"],
      "recipe": "1. Step one\\n2. Step two"
    },
    ... (continue for all 7 days: Monday through Sunday)
  ]
}

Rules:
- Return ONLY the JSON object, nothing else
- Do NOT wrap in markdown code blocks (no ```json ... ```)
- Each meal must have exactly 4 fields: day, dish, main_ingredients, recipe
- main_ingredients must be a list of 3-5 items
- recipe must be numbered steps separated by \\n
- Respect user preferences (if vegetarian, no meat; if allergies, avoid them)
- Make dishes varied and realistic
- Use common grocery store ingredients only
- Focus on ingredients available at major Bay Area grocery stores

User taste profile: {user_taste_profile}"""


# Initialize Deepseek client (REQUIRED - no fallback)
if not DEEPSEEK_API_KEY:
    raise ValueError(
        "DEEPSEEK_API_KEY is required for production. "
        "Please set it in your .env file."
    )

try:
    deepseek_client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )
except Exception as e:
    raise RuntimeError(f"Failed to initialize Deepseek client: {e}")


# --------------------- Playwright Integration (Optional) ---------------------


async def _visit_sites_quick():
    """Open store home pages briefly to demonstrate capability."""
    if async_playwright is None:
        return False
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page1 = await context.new_page()
            await page1.goto(TRADER_JOES_URL, timeout=5000)
            page2 = await context.new_page()
            await page2.goto(SAFEWAY_URL, timeout=5000)
            await browser.close()
    except Exception:
        return False
    return True


# --------------------- Store Recommendation Logic ---------------------


def recommend_store(price_dict: Dict[str, Dict]) -> Tuple[str, str]:
    """Recommend cheapest store and least-time (most availability).

    Returns: (cheapest_store_name, least_time_store_name)
    """
    if not price_dict:
        raise ValueError("No pricing data available for recommendations")

    cheapest = min(price_dict.items(), key=lambda kv: kv[1]["total"])[0]
    least_time = max(price_dict.items(), key=lambda kv: kv[1]["available_pct"])[0]
    return cheapest, least_time


# --------------------- Public API ---------------------


def generate_meal_plan(user_taste_profile: str) -> MealPlan:
    """Generate a 7-day meal plan using Deepseek AI.

    **PRODUCTION:** Requires DEEPSEEK_API_KEY. No fallback.

    Args:
        user_taste_profile: User's dietary preferences and restrictions

    Returns:
        MealPlan with 7 days of dinners

    Raises:
        ValueError: If API key not configured
        RuntimeError: If API call fails
    """
    if not deepseek_client:
        raise ValueError("Deepseek API key not configured")

    try:
        # Format prompt with user input
        formatted_prompt = MEAL_PLAN_PROMPT.format(
            user_taste_profile=user_taste_profile
        )

        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful chef assistant. Return only valid JSON, no markdown formatting or extra text."
                },
                {
                    "role": "user",
                    "content": formatted_prompt
                },
            ],
            temperature=0.7,
            stream=False
        )
        resp = response.choices[0].message.content.strip()

        # Parse JSON output from LLM (handle markdown wrapping)
        json_str = _extract_json_from_response(resp)
        payload = json.loads(json_str)

        # Validate structure
        if "meals" not in payload or not isinstance(payload.get("meals"), list):
            raise ValueError("Missing or invalid 'meals' field")

        if len(payload.get("meals", [])) < 7:
            raise ValueError(f"Expected 7 meals, got {len(payload.get('meals', []))}")

        # Ensure user_taste_profile is set
        if "user_taste_profile" not in payload:
            payload["user_taste_profile"] = user_taste_profile

        mp = MealPlan(**payload)
        print(f"✓ Successfully generated meal plan from Deepseek API")
        return mp

    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse LLM output as JSON: {e}")

    except ValueError as e:
        raise RuntimeError(f"Invalid meal plan structure: {e}")

    except Exception as e:
        raise RuntimeError(f"Deepseek API call failed: {e}")


def _extract_json_from_response(response_text: str) -> str:
    """
    Extract JSON from LLM response.

    Handles cases where JSON is wrapped in markdown code blocks or has extra text.

    Args:
        response_text: Raw LLM response

    Returns:
        Valid JSON string
    """
    # Remove leading/trailing whitespace
    text = response_text.strip()

    # Try to extract from markdown code blocks: ```json ... ```
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end > start:
            text = text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        if end > start:
            text = text[start:end].strip()

    # Try to find JSON object: {...}
    if "{" in text and "}" in text:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]

    return text


def compute_shopping_strategy(ingredients: List[str]) -> Dict:
    """Compute pricing and strategy summary for given ingredients.

    **DEPRECATED:** Use check_grocery_prices_v2 directly instead.
    This function exists for backward compatibility only.

    Args:
        ingredients: List of ingredient names

    Returns:
        Dict with pricing and recommendations
    """
    raise NotImplementedError(
        "compute_shopping_strategy is deprecated. "
        "Use check_grocery_prices_v2 with database session instead."
    )


# ============================================================================
# PRODUCTION PRICING WITH DATABASE & SERPAPI
# ============================================================================


def check_grocery_prices_v2(
    ingredients: List[str],
    db_session=None,
    serpapi_client=None,
    user_location: str = "San Francisco, CA 94103"
) -> Dict[str, Dict]:
    """
    Production pricing using database cache + SERPAPI.

    **PRODUCTION:** Requires database session and SERPAPI client.
    Geographic restriction: San Francisco Bay Area only.

    Args:
        ingredients: List of ingredient names to price
        db_session: SQLAlchemy database session (REQUIRED)
        serpapi_client: SERPAPI client (REQUIRED for fresh data)
        user_location: Bay Area location (zip code enforced)

    Returns:
        Pricing dict:
        {
          "Store Name": {
            "items": {ingredient: {"price": float, "available": bool}},
            "total": float,
            "available_pct": float
          }
        }

    Raises:
        ValueError: If required services not provided
    """
    if db_session is None:
        raise ValueError(
            "Database session is required for production. "
            "Initialize DatabaseManager and pass session."
        )

    try:
        from unified_pricing import PricingEngine

        # Initialize pricing engine
        pricing_engine = PricingEngine(db_session, serpapi_client)

        # Get unified prices
        pricing_result = pricing_engine.get_ingredient_prices(
            ingredients,
            user_location=user_location
        )

        # Convert to backward-compatible format
        result = {}

        # Build per-store pricing
        for ingredient, store_prices in pricing_result.ingredient_prices.items():
            for store_info in store_prices:
                store = store_info.get("store", "Unknown")
                price = float(store_info.get("price", 0.0))

                if store not in result:
                    result[store] = {"items": {}, "total": 0.0, "available_count": 0}

                result[store]["items"][ingredient] = {
                    "price": price,
                    "available": price < 9999  # Threshold for "available"
                }
                result[store]["total"] += price
                if price < 9999:
                    result[store]["available_count"] += 1

        # Calculate availability percentages
        for store in result:
            available_pct = round(
                100.0 * result[store]["available_count"] / max(1, len(ingredients)),
                1
            )
            result[store]["available_pct"] = available_pct
            del result[store]["available_count"]
            result[store]["total"] = round(result[store]["total"], 2)

        # Log data source
        print(f"✓ Using pricing from: {pricing_result.data_source}")

        if not result:
            raise ValueError("No pricing data returned from engine")

        return result

    except Exception as e:
        raise RuntimeError(f"Pricing engine failed: {e}")


# Define legacy tool object for backward compatibility
@dataclass
class CheckGroceryPricesTool:
    name: str = "check_grocery_prices_v2"
    description: str = (
        "Production grocery pricing using database + SERPAPI. "
        "Requires database session and SERPAPI client. "
        "Returns real prices from Bay Area stores only."
    )

    def run(self, ingredients: List[str], db_session=None, serpapi_client=None) -> Dict[str, Dict]:
        return check_grocery_prices_v2(
            ingredients,
            db_session=db_session,
            serpapi_client=serpapi_client
        )


check_grocery_prices_tool = CheckGroceryPricesTool()


if __name__ == "__main__":
    # Production test
    print("AI Grocery Agent - Production Mode")
    print("=" * 60)

    # Test meal plan generation
    try:
        mp = generate_meal_plan("Vegetarian, loves spicy food, no mushrooms")
        print(f"✓ Generated {len(mp.meals)} meals")
        for meal in mp.meals[:2]:
            print(f"  - {meal.day}: {meal.dish_name}")
    except Exception as e:
        print(f"✗ Meal generation failed: {e}")

    print("\nNote: Pricing requires database session and SERPAPI client")
    print("Run via app.py for full integration testing")
