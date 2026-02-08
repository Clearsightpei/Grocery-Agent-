# 🛒 AI Grocery Agent - San Francisco Bay Area

**Smart Meal Planning. Real-Time Pricing. Optimal Shopping Routes.**

The **AI Grocery Agent** is a production-ready intelligent assistant that helps Bay Area residents save money and time on groceries. It combines **LLM-based meal planning** (DeepSeek) with a **real-time pricing engine** (SERPAPI + PostgreSQL Cache) and **Google Maps route optimization** to generate personalized meal plans and the most cost-effective shopping strategy.

**🌉 Service Area:** San Francisco Bay Area (West Bay corridor: SF to San Jose)

---

## 🚀 Key Features

### 🤖 AI Meal Planning
- Generates personalized 7-day dinner plans based on your dietary preferences
- Powered by **DeepSeek AI** with intelligent JSON parsing
- Adapts to restrictions (vegetarian, allergies, cuisine preferences)
- Focuses on ingredients available at major Bay Area grocery stores

### 💰 Smart Pricing Engine
- **Real-Time Data:** Fetches live grocery prices via SERPAPI Google Shopping
- **Intelligent Caching:** PostgreSQL database with 60% coverage threshold
  - If DB coverage ≥ 60% → Use cached prices
  - If DB coverage < 60% → Fetch from SERPAPI and update cache
- **Bay Area Focused:** All price searches restricted to SF Bay Area locations
- **Unit Normalization:** Converts units (gallons ↔ liters, lbs ↔ oz) for fair comparisons

### 🗺️ Route Optimization
- **Google Maps Integration:** Real driving times with live traffic data
- **Distance Matrix API:** Calculates actual travel times between stores
- **Geographic Validation:** Enforces West Bay bounding box:
  - **North:** 37.81° (San Francisco)
  - **South:** 37.33° (San Jose)
  - **West:** -122.52° (Pacific Coast)
  - **East:** -121.80° (Bay Front)
- **Cost Formula:** `Total Cost = (Travel Time × Hourly Rate) + Item Prices`
- **Smart Recommendations:** Suggests cheapest store vs. most consolidated shopping

### 📊 Interactive Dashboard
- **Streamlit Web UI** with real-time updates
- Per-store price breakdowns and availability metrics
- Store recommendations (cheapest vs. fastest)
- Geographic location validation

---

## 🛠️ Tech Stack

### Backend
- **Python 3.11+**
- **SQLAlchemy ORM** with PostgreSQL/SQLite support
- **Asyncio** for concurrent operations
- **Pydantic** for data validation

### AI & APIs
- **DeepSeek V3** - Meal plan generation (deepseek-chat model)
- **SERPAPI** - Real-time grocery pricing from Google Shopping
- **Google Maps Platform:**
  - Distance Matrix API (traffic-aware routing)
  - Geocoding API (address validation)

### Frontend
- **Streamlit** - Interactive web interface
- **Pandas** - Price matrix operations

### Database
- **PostgreSQL** (production) or **SQLite** (development)
- Schema: `grocery.stores`, `grocery.ingredients`, `grocery.prices`, `grocery.price_history`

### Optional
- **Playwright** - Browser automation for store website visits (demonstration)

---

## 🏗️ Architecture

The system follows a strict **3-Layer Production Architecture**:

### Layer 1: Presentation (`app.py`)
- Streamlit web interface
- User input validation (taste preferences, Bay Area location)
- Database service initialization with caching
- Error handling and graceful degradation

### Layer 2: Agent Logic (`agent_logic.py`)
- **Meal Generation:** DeepSeek API integration
- **Pricing Coordinator:** Calls `check_grocery_prices_v2()` with database session
- **Store Recommendations:** Analyzes pricing and availability data

### Layer 3: Data & Optimization
- **Unified Pricing Engine (`unified_pricing.py`):**
  - 60% coverage threshold decision tree
  - SERPAPI integration for missing data
  - Automatic database updates
- **Database Manager (`database.py`):**
  - Connection pooling with `QueuePool`
  - Schema initialization
  - Health checks
- **Shopping Solver (`solver.py` + `shopping_graph.py`):**
  - Graph-based route optimization
  - Google Maps routing integration
  - Basket optimization (cheapest store per item)
- **External Services:**
  - `serpapi_client.py` - Bay Area price fetching
  - `googlemaps_client.py` - Real routing with geographic validation
  - `pricing_service.py` - Coverage calculation
  - `unit_converter.py` - Unit normalization

---

## ⚙️ Setup & Installation

### 1. Prerequisites

- **Python 3.11+**
- **PostgreSQL** (recommended) or SQLite (development)
- **API Keys:**
  - DeepSeek API key (required)
  - SERPAPI key (required for fresh pricing)
  - Google Maps API key (required for routing)

### 2. Clone & Install

```bash
git clone https://github.com/yourusername/grocery-agent.git
cd grocery-agent

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (optional)
python -m playwright install chromium
```

### 3. Environment Configuration

Create a `.env` file in the root directory. **Do not commit this file.**

```ini
# Required - AI Meal Planning
DEEPSEEK_API_KEY=sk-your-deepseek-key-here

# Required - Database
DATABASE_URL=postgresql://user:password@localhost:5432/grocery_agent
# Or for SQLite (development):
# DATABASE_URL=sqlite:///./grocery_agent.db

# Required - Real-time Pricing
SERPAPI_API_KEY=your-serpapi-key-here

# Required - Route Optimization
GOOGLEMAPS_API_KEY=your-google-maps-key-here
```

### 4. Database Initialization

The database schema is automatically created on first run.

**PostgreSQL Setup:**
```bash
# Create database
createdb grocery_agent

# Initialize schema (automatic on first app.py run)
python -c "from database import DatabaseManager; import os; from dotenv import load_dotenv; load_dotenv(); db = DatabaseManager(os.getenv('DATABASE_URL')); db.init_db()"
```

**SQLite Setup (Development):**
```bash
# Schema auto-created in grocery_agent.db on first run
# No manual setup required
```

---

## 🏃‍♂️ How to Run

### Start the Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

### Usage Flow

1. **Enter dietary preferences** (e.g., "Vegetarian, loves spicy food, no mushrooms")
2. **Enter Bay Area location** (e.g., "San Francisco, CA 94103")
3. **Click "Generate Plan & Shop"**
4. **View 7-day meal plan** with recipes
5. **Review pricing** from Bay Area stores
6. **Get recommendations** for cheapest vs. fastest shopping strategy

---

## 📂 Project Structure

```text
📦 grocery-agent
├── 📄 app.py                      # Streamlit UI (production)
├── 📄 agent_logic.py              # Meal planning + pricing orchestration
├── 📄 solver.py                   # Route optimization algorithms
├── 📄 shopping_graph.py           # Graph data structures
├── 📄 database.py                 # PostgreSQL/SQLite manager
├── 📄 models.py                   # SQLAlchemy ORM models
├── 📄 unified_pricing.py          # Smart pricing engine (cache vs API)
├── 📄 pricing_service.py          # Coverage calculation
├── 📄 serpapi_client.py           # SERPAPI integration (Bay Area)
├── 📄 googlemaps_client.py        # Google Maps routing + validation
├── 📄 unit_converter.py           # Unit normalization logic
├── 📄 requirements.txt            # Python dependencies
├── 📄 .env                        # API keys (gitignored)
├── 📄 CLAUDE.md                   # Development guide for Claude Code
└── 📄 README.md                   # This file

📂 Documentation
├── 📄 SOLVER_README.md            # Detailed solver algorithm docs
├── 📄 INTEGRATION_COMPLETE.md     # Integration architecture
└── 📄 LLM_INTEGRATION.md          # LLM implementation details
```

---

## 🔒 Geographic Restrictions

**All operations are limited to the San Francisco Bay Area (West Bay corridor).**

### Why Geographic Restrictions?

1. **Data Quality:** SERPAPI results filtered to Bay Area zip codes for accurate pricing
2. **Routing Accuracy:** Google Maps routing optimized for local traffic patterns
3. **Store Validation:** Ensures stores are within reasonable driving distance
4. **Service Reliability:** Focused service area improves data consistency

### Bounding Box Validation

All addresses and store locations are validated against:
- **North:** 37.81° (San Francisco)
- **South:** 37.33° (San Jose)
- **West:** -122.52° (Pacific Coast)
- **East:** -121.80° (Bay Front)

**Supported Cities:** San Francisco, Daly City, San Mateo, Palo Alto, Mountain View, Sunnyvale, San Jose

---

## 🧪 Testing

### Integration Test
```bash
python test_integration.py
```

### Test Individual Components
```bash
# Test meal plan generation
python -c "from agent_logic import generate_meal_plan; print(generate_meal_plan('vegetarian'))"

# Test database connection
python database.py

# Test Google Maps client
python googlemaps_client.py
```

---

## 🚨 Troubleshooting

### "DEEPSEEK_API_KEY is required"
- Ensure `.env` file exists with `DEEPSEEK_API_KEY=sk-...`
- Verify API key is active at https://platform.deepseek.com

### "DATABASE_URL is required"
- Set `DATABASE_URL` in `.env` file
- For SQLite: `DATABASE_URL=sqlite:///./grocery_agent.db`
- For PostgreSQL: `DATABASE_URL=postgresql://user:pass@host:5432/dbname`

### "Address is outside service area"
- Enter a valid Bay Area address (SF to San Jose corridor)
- Use specific zip codes: 94103, 94301, 94086, 95113, etc.

### "SERPAPI failed"
- Check `SERPAPI_API_KEY` in `.env`
- Verify API quota at https://serpapi.com/dashboard
- System requires ≥60% database coverage or working SERPAPI

### Playwright not installed
```bash
python -m playwright install chromium
```

---

## 🔮 Future Roadmap

### Phase 1: Enhanced Optimization
- [ ] **Weekly Coupon Integration:** Automatically fetch and incorporate weekly deals from Safeway, Trader Joe's, Whole Foods, and other Bay Area stores into route optimization
  - Parse digital circulars and mobile app promotions
  - Calculate effective prices after discounts
  - Prioritize stores with best coupon stacks
  - Alert users to limited-time offers (e.g., "2-for-1 this week only")
  - Consider minimum purchase requirements for coupon eligibility
  - Track historical coupon patterns to predict future deals

### Phase 2: User Experience
- [ ] **User Accounts:** Multi-user support with saved preferences
- [ ] **Pantry Tracking:** "What's in my fridge?" feature to avoid duplicate purchases
- [ ] **Meal History:** Track past meals and avoid repetition
- [ ] **Shopping List Export:** Email or SMS shopping lists

### Phase 3: Advanced Features
- [ ] **Mobile App:** Native iOS/Android app with GPS routing
- [ ] **Price Alerts:** Notifications when favorite items drop in price
- [ ] **Recipe Customization:** Adjust serving sizes and substitute ingredients
- [ ] **Nutritional Analysis:** Calorie and macro tracking

### Phase 4: Geographic Expansion
- [ ] **East Bay Support:** Oakland, Berkeley, Alameda
- [ ] **South Bay Expansion:** Santa Clara, Milpitas, Fremont
- [ ] **North Bay:** Marin County, Napa Valley

### Phase 5: Advanced AI
- [ ] **Image Recognition:** Snap photos of receipts to auto-update prices
- [ ] **Voice Interface:** "Alexa, add eggs to my shopping list"
- [ ] **Predictive Analytics:** Learn shopping patterns and suggest lists

---

## 📊 API Rate Limits & Costs

### DeepSeek API
- **Cost:** ~$0.14 per 1M input tokens, ~$0.28 per 1M output tokens
- **Usage:** ~1 request per meal plan (~1000 tokens)
- **Estimate:** < $0.01 per user session

### SERPAPI
- **Free Tier:** 100 searches/month
- **Paid:** $50/month for 5,000 searches
- **Usage:** ~10-20 searches per ingredient list (depends on DB coverage)
- **Database caching reduces API calls by 60%+**

### Google Maps
- **Free Tier:** $200 monthly credit (~28,000 Distance Matrix calls)
- **Cost:** $0.005 per element (origin-destination pair)
- **Usage:** ~5-10 API calls per route optimization
- **Estimate:** < $0.05 per user session

---

## 📝 License

MIT License - See LICENSE file for details

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📧 Support

For issues, questions, or feedback:
- Open an issue on GitHub
- Check CLAUDE.md for development guidelines
- Review documentation in `docs/` folder

---

**Built with ❤️ for the San Francisco Bay Area community**
