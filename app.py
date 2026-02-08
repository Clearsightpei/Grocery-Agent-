"""
Streamlit UI for AI Grocery Agent - PRODUCTION VERSION

**GEOGRAPHIC RESTRICTION:** San Francisco Bay Area (West Bay) only.

- Input: User taste preferences + location
- Generate: 7-day dinner plan using Deepseek AI
- Fetch: Real prices from database + SERPAPI
- Display: Per-store pricing, totals, and recommendations
"""

import os

import streamlit as st
from dotenv import load_dotenv

from agent_logic import (
    generate_meal_plan,
    recommend_store,
    check_grocery_prices_v2,
)

# Load environment variables
load_dotenv()

st.set_page_config(page_title="AI Grocery Agent - Bay Area", layout="wide")

st.title("AI Grocery Agent 🛒🥘")
st.caption("San Francisco Bay Area (West Bay) - SF to San Jose corridor")

st.markdown("""
Tell me your taste preferences and I'll generate a 7-day dinner plan and find the best deals at Bay Area stores.
""")

# ============================================================================
# DATABASE & PRICING ENGINE INITIALIZATION
# ============================================================================


@st.cache_resource
def init_database_and_services():
    """
    Initialize database connection and pricing services.

    **PRODUCTION:** Requires DATABASE_URL and SERPAPI_API_KEY.
    """
    from database import DatabaseManager
    from serpapi_client import SERPAPIClient

    # Get database URL from environment
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError(
            "DATABASE_URL is required for production. "
            "Please set it in your .env file."
        )

    # Initialize database
    db_manager = DatabaseManager(db_url)
    db_manager.init_db()

    # Check database health
    if not db_manager.health_check():
        raise RuntimeError("Database connection failed")

    print(f"✓ Database connected: {db_url.split('@')[-1]}")  # Hide credentials

    # Initialize SERPAPI client (REQUIRED)
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if not serpapi_key:
        st.warning(
            "⚠️ SERPAPI_API_KEY not configured. "
            "Pricing will only work if database cache coverage >= 60%."
        )
        serpapi_client = None
    else:
        serpapi_client = SERPAPIClient(serpapi_key)
        print("✓ SERPAPI client initialized")

    return db_manager, serpapi_client


# Initialize services on app start
try:
    db_manager, serpapi_client = init_database_and_services()
except Exception as e:
    st.error(f"❌ Failed to initialize services: {e}")
    st.stop()

# User inputs
col_input_1, col_input_2 = st.columns([2, 1])

with col_input_1:
    user_taste = st.text_input(
        "Dietary preferences",
        placeholder="e.g., Vegetarian, loves spicy food, no mushrooms",
        help="Describe your dietary preferences, allergies, and favorite cuisines"
    )

with col_input_2:
    user_location = st.text_input(
        "Your Bay Area location",
        value="San Francisco, CA 94103",
        help="Enter a Bay Area address or zip code (SF to San Jose only)"
    )

if 'generated' not in st.session_state:
    st.session_state['generated'] = None

if st.button("🍽️ Generate Plan & Shop", type="primary"):
    if not user_taste.strip():
        st.warning("Please enter your dietary preferences.")
        st.stop()

    try:
        with st.spinner("🤖 Generating personalized meal plan with Deepseek AI..."):
            mp = generate_meal_plan(user_taste)
            st.session_state['generated'] = mp
    except Exception as e:
        st.error(f"❌ Failed to generate meal plan: {e}")
        st.stop()

if st.session_state['generated']:
    mp = st.session_state['generated']

    st.header("7-Day Dinner Plan 🍽️")
    tabs = st.tabs([m.day for m in mp.meals])
    for tab, meal in zip(tabs, mp.meals):
        with tab:
            st.subheader(meal.dish_name)
            st.markdown("**Main Ingredients:**")
            st.write(", ".join(meal.main_ingredients))
            st.markdown("**Recipe:**")
            # Keep recipe faithful to short numbered steps
            st.text(meal.recipe)

    # Consolidate ingredient list (simple flat list)
    all_ingredients = []
    for m in mp.meals:
        for ing in m.main_ingredients:
            if ing not in all_ingredients:
                all_ingredients.append(ing)

    st.header("Shopping & Pricing 🧾")
    st.write(f"Checking prices for {len(all_ingredients)} unique items in Bay Area stores...")

    try:
        with st.spinner("🔍 Fetching real-time prices from database + SERPAPI..."):
            db_session = db_manager.get_session()
            try:
                pricing = check_grocery_prices_v2(
                    all_ingredients,
                    db_session=db_session,
                    serpapi_client=serpapi_client,
                    user_location=user_location
                )
            finally:
                db_session.close()

        # Get store recommendations
        cheapest, least_time = recommend_store(pricing)

    except Exception as e:
        st.error(f"❌ Failed to fetch prices: {e}")
        st.stop()

    # Display per-store breakdowns
    cols = st.columns(2)
    for col, (store_name, data) in zip(cols, pricing.items()):
        with col:
            st.subheader(store_name)
            st.write(f"Estimated total: **${data['total']:.2f}**")
            st.write(f"Availability: **{data['available_pct']}%** of items")
            st.markdown("**Item breakdown:**")
            for item, info in data['items'].items():
                avail_text = "✅" if info['available'] else "❌"
                st.write(f"- {item}: ${info['price']:.2f} {avail_text}")

    st.markdown("---")
    st.subheader("Recommended Strategy ✅")

    col_rec_1, col_rec_2 = st.columns(2)
    with col_rec_1:
        st.metric("💰 Cheapest store", cheapest)
    with col_rec_2:
        st.metric("⚡ Best availability", least_time)

    st.info("💡 Prices are fetched from database cache and SERPAPI. Data is updated in real-time from Bay Area stores.")

else:
    st.write("Enter your dietary preferences and location, then press 'Generate Plan & Shop' to begin.")

# Footer
st.markdown("---")
st.caption(
    "🌉 AI Grocery Agent - Production | "
    "Service Area: San Francisco Bay Area (West Bay) | "
    "Powered by Deepseek AI + SERPAPI + Google Maps"
)