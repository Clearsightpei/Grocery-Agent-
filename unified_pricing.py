"""
Unified Pricing Engine - Production Version

Orchestrates the complete decision logic:
1. Check database coverage (60% threshold)
2. If < 60%: Fetch from SERPAPI API
3. If SERPAPI fails: Raise error (NO MOCK FALLBACK)

**PRODUCTION:** Requires SERPAPI client for fresh data.
**GEOGRAPHIC RESTRICTION:** San Francisco Bay Area only.

This is the main entry point for getting ingredient prices.
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.orm import Session

from pricing_service import CoverageCheckService, DBCheckResult
from serpapi_client import SERPAPIClient, SERPAPIResult

logger = logging.getLogger(__name__)


@dataclass
class PricingResult:
    """Final pricing result for all ingredients"""
    ingredient_prices: Dict[str, List[Dict]]  # {ingredient: [{"store": name, "price": float}]}
    missing_items: List[str]  # Items that weren't found anywhere
    data_source: str  # 'cache' or 'api'
    coverage_pct: float  # DB coverage percentage
    timestamp: datetime


class PricingEngine:
    """Main pricing engine with smart caching and API fallback"""
    
    def __init__(
        self,
        db_session: Session,
        serpapi_client: Optional[SERPAPIClient] = None
    ):
        """
        Initialize pricing engine.
        
        Args:
            db_session: SQLAlchemy database session
            serpapi_client: SERPAPI client (optional, can be None)
        """
        self.db_session = db_session
        self.serpapi_client = serpapi_client
    
    def get_ingredient_prices(
        self,
        ingredient_list: List[str],
        user_location: str = "San Francisco, CA 94103"
    ) -> PricingResult:
        """
        Production pricing engine: database cache + SERPAPI.

        **PRODUCTION:** Requires SERPAPI client for coverage < 60%.

        Decision Tree:
        1. Check database coverage
           ├─ If >= 60% & cache fresh → Use cached prices
           └─ If < 60% → Fetch from SERPAPI (REQUIRED)
              ├─ If SERPAPI succeeds → Merge with cache, save to DB
              └─ If SERPAPI fails → Raise error (NO FALLBACK)

        Args:
            ingredient_list: Ingredients to get prices for
            user_location: Bay Area location for API search

        Returns:
            PricingResult with prices from database or API

        Raises:
            ValueError: If SERPAPI not configured when needed
            RuntimeError: If SERPAPI fails
        """
        start_time = datetime.utcnow()

        logger.info(f"🔍 Pricing engine: requesting {len(ingredient_list)} ingredients")

        # Step 1: Check database coverage
        db_check = CoverageCheckService.check_database_coverage(
            ingredient_list,
            self.db_session
        )

        logger.info(f"   DB coverage: {db_check.coverage_percentage}%")

        # Step 2: Decide: use cache or fetch API
        if db_check.should_fetch_api:
            # Coverage < 60% → MUST use SERPAPI
            if not self.serpapi_client:
                raise ValueError(
                    f"SERPAPI client required for coverage < 60% "
                    f"(current: {db_check.coverage_percentage}%). "
                    f"Missing items: {db_check.missing_ingredients}"
                )

            logger.info(f"   Coverage < 60%, fetching from SERPAPI...")
            api_result = self.serpapi_client.fetch_prices(
                db_check.missing_ingredients,
                user_location
            )

            if not api_result.success:
                # SERPAPI failed → raise error
                error_msg = f"SERPAPI failed: {'; '.join(api_result.errors)}"
                logger.error(f"   ✗ {error_msg}")
                raise RuntimeError(error_msg)

            # SERPAPI succeeded → merge with DB cache
            logger.info(f"   ✓ SERPAPI succeeded: {len(api_result.prices)} ingredients")

            merged_prices = self._merge_prices(
                db_check.available_ingredients,
                api_result.prices
            )

            # Save to database
            self._save_to_database(api_result.prices)

            return PricingResult(
                ingredient_prices=merged_prices,
                missing_items=[],
                data_source='api',
                coverage_pct=100.0,
                timestamp=start_time
            )
        else:
            # Coverage >= 60% & cache fresh → use cached prices
            logger.info(f"   ✓ Using cached prices (coverage sufficient and fresh)")

            return PricingResult(
                ingredient_prices=db_check.available_ingredients,
                missing_items=db_check.missing_ingredients,
                data_source='cache',
                coverage_pct=db_check.coverage_percentage,
                timestamp=start_time
            )
    
    def _merge_prices(
        self,
        cached: Dict[str, List[Dict]],
        api: Dict[str, List[Dict]]
    ) -> Dict[str, List[Dict]]:
        """
        Merge cached and API prices.

        Priority: API prices first, then cached.

        Args:
            cached: Prices from database cache
            api: Prices from SERPAPI

        Returns:
            Merged price dictionary
        """
        merged = cached.copy()

        for ingredient, prices in api.items():
            if prices:  # Only if API returned data
                merged[ingredient] = prices

        logger.debug(f"Merged {len(api)} API results with {len(cached)} cached results")

        return merged

    def _save_to_database(self, prices: Dict[str, List[Dict]]) -> None:
        """
        Save fetched prices to database.
        
        Args:
            prices: Dict of {ingredient: [{"store": name, "price": float}]}
        """
        try:
            from models import Ingredient, Store, Price, PriceHistory
            
            for ingredient_name, store_prices in prices.items():
                # Find or create ingredient
                ing = self.db_session.query(Ingredient).filter(
                    Ingredient.name == ingredient_name.lower()
                ).first()
                
                if not ing:
                    ing = Ingredient(
                        name=ingredient_name.lower(),
                        category='unknown',
                        unit='each'
                    )
                    self.db_session.add(ing)
                
                # Update prices for each store
                for store_price in store_prices:
                    store = self.db_session.query(Store).filter(
                        Store.name == store_price['store']
                    ).first()
                    
                    if store:
                        # Update or create price
                        price = self.db_session.query(Price).filter(
                            Price.ingredient_id == ing.id,
                            Price.store_id == store.id
                        ).first()
                        
                        if not price:
                            price = Price(
                                ingredient_id=ing.id,
                                store_id=store.id,
                                price=store_price['price'],
                                in_stock=True
                            )
                            self.db_session.add(price)
                        else:
                            price.price = store_price['price']
                        
                        # Record in history
                        history = PriceHistory(
                            ingredient_id=ing.id,
                            store_id=store.id,
                            price=store_price['price'],
                            source='api'
                        )
                        self.db_session.add(history)
            
            self.db_session.commit()
            logger.info(f"✓ Saved prices to database")
        
        except Exception as e:
            logger.error(f"Failed to save prices to database: {e}")
            self.db_session.rollback()


if __name__ == "__main__":
    # Example usage
    import os
    from dotenv import load_dotenv
    
    logging.basicConfig(level=logging.INFO)
    
    load_dotenv()
    
    # Would need actual database connection
    print("PricingEngine requires database connection to run")
    print("See agent_logic.py for integration example")
