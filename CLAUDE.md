# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Grocery Agent - An intelligent meal planning and grocery shopping optimization system that generates personalized 7-day dinner plans and finds the most cost-effective shopping routes across multiple stores.

**Key Capabilities:**
- LLM-powered meal planning using Deepseek API (with deterministic fallback)
- Smart pricing with 3-tier data sourcing (database cache → SERPAPI → mock)
- Multi-store route optimization that balances time vs money
- Graph-based shopping solver using Haversine distances
- Streamlit web interface with database caching

## Setup & Running

### Environment Setup
```bash
# Create virtual environment (Python 3.11+)
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (required for store visits)
python -m playwright install chromium
```

### Environment Variables
Create `.env` file with:
```bash
# Required for AI meal generation
DEEPSEEK_API_KEY=sk_...

# Optional for real pricing data (otherwise uses mock data)
SERPAPI_API_KEY=...

# Optional for PostgreSQL (defaults to SQLite)
DATABASE_URL=postgresql://user:pass@localhost/grocery
```

### Running the Application
```bash
# Start Streamlit web UI
streamlit run app.py

# Test integration end-to-end
python test_integration.py
```

### Running Tests
```bash
# Run integration validation
python test_integration.py

# Test specific module
python -c "from agent_logic import generate_meal_plan; print(generate_meal_plan('vegetarian'))"
```

## Architecture Overview

### 3-Layer System Design

**Layer 1: Streamlit UI (app.py)**
- User input for taste preferences
- Database/service initialization with `@st.cache_resource`
- Display meal plans, pricing, and recommendations
- Handles graceful fallbacks if services unavailable

**Layer 2: Agent Logic (agent_logic.py)**
- `generate_meal_plan()`: Deepseek LLM integration with deterministic fallback
- `check_grocery_prices_v2()`: New unified pricing with database + SERPAPI
- `check_grocery_prices()`: Legacy mocked pricing (backward compatible)
- `compute_shopping_strategy()`: Store recommendations

**Layer 3: Data & Optimization**
- **Unified Pricing Engine** (`unified_pricing.py`): Smart cache vs API decision tree
- **Database Layer** (`database.py`, `models.py`): SQLAlchemy ORM with PostgreSQL/SQLite
- **Shopping Solver** (`solver.py`, `shopping_graph.py`): Route optimization algorithm
- **External APIs** (`serpapi_client.py`): Real-time grocery price fetching

### Pricing Engine Decision Tree

The pricing engine follows this logic:

```
1. Check database coverage
   ├─ If >= 60% & fresh → Use cached prices
   └─ If < 60% → Try SERPAPI
      ├─ Success → Merge API + cache, save to DB
      └─ Fail → Use deterministic mock data
```

**Key Files:**
- `unified_pricing.py`: Main PricingEngine class
- `pricing_service.py`: CoverageCheckService for DB coverage calculation
- `serpapi_client.py`: External API client
- `mock_data.py`: Deterministic seeded fallback (SHA256-based)

### Database Schema

**Tables (in `grocery` schema):**
- `stores`: Physical locations with lat/long
- `ingredients`: Normalized ingredient names with categories
- `prices`: Current prices (unique per ingredient+store)
- `price_history`: Time-series pricing data
- `cache_metadata`: Cache expiration tracking

**ORM Models:** All defined in `models.py` using SQLAlchemy

### Shopping Solver Algorithm

**Files:** `solver.py` + `shopping_graph.py`

**Cost Formula:**
```
Total Cost = (Travel Time × Hourly Rate / 60) + Sum of Item Prices
```

**Algorithm:**
1. Generate all single-store and two-store route permutations
2. For each route:
   - Calculate travel time & cost (Haversine distance)
   - Optimize basket: Pick cheapest store for each item in route
   - Compute total = travel_value + basket_cost
3. Return route with minimum total cost

**Key Classes:**
- `ShoppingList`: User preferences + time valuation
- `PriceMatrix`: Pandas DataFrame of ingredient prices
- `RouteSegment`: Graph edges with time/cost
- `SolverResult`: Winner route + all analyzed options

## Important Implementation Details

### LLM Meal Plan Generation

**Function:** `generate_meal_plan(user_taste_profile: str) -> MealPlan`

**Behavior:**
1. Tries Deepseek API first (JSON-only output, no markdown)
2. Extracts JSON from response using `_extract_json_from_response()`
3. Validates structure (7 meals, required fields)
4. Falls back to `_mock_generate_meal_plan()` if API fails

**Mock Fallback:** Uses precreated dishes from `_SIMPLE_DISHES` dict (vegetarian vs default)

### Price Determinism

All mock prices are **deterministic** based on SHA256 hash of `{ingredient}::{store}`:
- Range: $3.00 - $10.00 per item
- Availability: ~92-96% (store-dependent)
- Consistent across runs for same inputs

**Functions:**
- `_seeded_price(ingredient, store)` → float
- `_seeded_availability(ingredient, store)` → bool

### Playwright Integration

**Purpose:** Demonstrates browser automation capability (lightweight in MVP)

**Usage:** `_visit_sites_quick()` in `agent_logic.py`
- Opens Trader Joe's and Safeway homepages (headless)
- Best-effort (tolerates failures)
- Does NOT scrape prices in current MVP
- Future: Can be extended for real price extraction

### Database Initialization

**Automatic on first run:**
```python
@st.cache_resource
def init_database_and_services():
    db_manager = DatabaseManager("sqlite:///./grocery_agent.db")
    db_manager.init_db()  # Creates schema
    # Seeds mock data if empty
    if store_count == 0:
        MockDataManager.seed_default_data(session)
```

**Database Options:**
- Default: SQLite (`grocery_agent.db`) - zero configuration
- Production: PostgreSQL via `DATABASE_URL` env var

## Development Patterns

### Adding New Stores

**In mock data** (`mock_data.py`):
```python
MockDataManager.seed_default_data(session)  # Adds 5 default stores
```

**For solver** (`shopping_graph.py`):
```python
Store(name="...", address="...", geo_location=GeoLocation(lat, lon))
```

### Adding New Ingredients

Ingredients auto-created on first price lookup. Manual add:
```python
ingredient = Ingredient(name="tomato", category="produce", unit="lb")
session.add(ingredient)
session.commit()
```

### Extending Route Optimization

Current: 1-2 store routes only. To add 3+ stores:

**In `solver.py`:**
```python
# Currently:
route_lengths = [1, 2]
# Change to:
route_lengths = [1, 2, 3]
```

**Warning:** Complexity grows as O(n!) for n stores

## API Keys & External Services

### Deepseek API
- **Purpose:** AI meal plan generation
- **Required:** Yes (but has fallback)
- **Rate limits:** Standard Deepseek limits
- **Model:** `deepseek-chat`

### SERPAPI
- **Purpose:** Real grocery price fetching
- **Required:** No (uses mock if missing)
- **Fallback:** Deterministic mock data
- **Coverage threshold:** 60% (configurable in `unified_pricing.py`)

### Playwright
- **Purpose:** Browser automation for store visits
- **Required:** Yes (install with `python -m playwright install`)
- **Usage:** Demonstration only in MVP (no scraping yet)

## File Organization

**Entry Points:**
- `app.py` - Streamlit web UI (main entry)
- `test_integration.py` - End-to-end validation

**Core Logic:**
- `agent_logic.py` - LLM integration + pricing wrapper
- `unified_pricing.py` - Smart pricing engine
- `solver.py` - Route optimization algorithm
- `shopping_graph.py` - Graph data structures

**Data Layer:**
- `database.py` - DatabaseManager with connection pooling
- `models.py` - SQLAlchemy ORM models
- `mock_data.py` - Deterministic seeded data

**External Services:**
- `serpapi_client.py` - SERPAPI integration
- `pricing_service.py` - Coverage calculation
- `unit_converter.py` - Unit normalization (lb, oz, etc.)

**Documentation:**
- `README.md` - User-facing setup guide
- `SOLVER_README.md` - Detailed solver algorithm docs
- `INTEGRATION_COMPLETE.md` - Integration architecture
- `LLM_INTEGRATION.md` - LLM implementation details

**Test Data:**
- `Testing data/` - Example usage scripts
- `grocery_agent.db` - SQLite database (auto-generated)

## Common Troubleshoots

### Playwright Not Installed
```bash
python -m playwright install chromium
```

### Database Schema Missing
Automatic on first `streamlit run app.py`, or manually:
```python
from database import DatabaseManager
db = DatabaseManager("sqlite:///./grocery_agent.db")
db.init_db()
```

### LLM Returns Invalid JSON
The `_extract_json_from_response()` function handles markdown wrapping, but if it still fails, check:
- Deepseek API response format changes
- Temperature too high (currently 0.7)
- Falls back to mock automatically

### SERPAPI Rate Limits
Pricing engine automatically falls back to cached prices or mock data. No manual intervention needed.

## Backward Compatibility

The codebase maintains dual pricing systems:

**Legacy (original MVP):**
- `check_grocery_prices()` - Mocked prices only
- `check_grocery_prices_tool` - LangChain tool wrapper

**New (integrated):**
- `check_grocery_prices_v2()` - Database + SERPAPI + mock fallback

Both APIs return same format for seamless switching.
