"""
Smart Database Coverage Check

Determines whether to fetch prices from SERPAPI API or use cached prices.

Decision Logic:
- Check database: Do we have >= 60% of required ingredients already cached?
- If YES (>= 60%) → Use cached prices (fast & cheap)
- If NO (< 60%) → Fetch fresh prices from SERPAPI (expensive but more accurate)
"""

import logging
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Configuration
COVERAGE_THRESHOLD = 0.60  # 60% threshold
CACHE_TTL = timedelta(hours=4)  # Cache validity period


@dataclass
class DBCheckResult:
    """Result of database coverage check"""
    coverage_percentage: float  # % of ingredients found in DB
    available_ingredients: Dict[str, List[Dict]]  # {ingredient: [{"store": name, "price": float}]}
    missing_ingredients: List[str]  # Ingredients NOT in DB
    should_fetch_api: bool  # True if coverage < 60% → activate SERPAPI
    cache_freshness: Dict[str, bool]  # {store: is_fresh}
    timestamp: datetime


class CoverageCheckService:
    """Service to check database coverage and determine API activation"""
    
    @staticmethod
    def check_database_coverage(
        ingredient_list: List[str],
        session: Session
    ) -> DBCheckResult:
        """
        Smart coverage check: determine if we should fetch from SERPAPI or use cache.
        
        Algorithm:
        1. Normalize ingredient names (lowercase, trim)
        2. Query database for each ingredient across all stores
        3. Calculate coverage % = (ingredients found) / (total ingredients)
        4. Check cache freshness (are existing prices fresh? < 4 hours old?)
        5. Decision: coverage < 60% OR cache stale → should_fetch_api = True
        
        Args:
            ingredient_list: List of ingredients needed (e.g., from meal plan)
            session: SQLAlchemy database session
        
        Returns:
            DBCheckResult with coverage info and decision flag
        
        Raises:
            Exception: If database query fails
        """
        start_time = datetime.utcnow()
        
        try:
            from models import Ingredient, Price, Store, CacheMetadata
            
            # Step 1: Normalize ingredient names
            ingredients_normalized = [
                ing.lower().strip() 
                for ing in ingredient_list
            ]
            
            logger.info(f"Coverage check: {len(ingredients_normalized)} ingredients requested")
            
            # Step 2: Query database for existing ingredients
            db_ingredients = session.query(Ingredient).filter(
                Ingredient.name.in_(ingredients_normalized)
            ).all()
            
            found_count = len(db_ingredients)
            coverage = found_count / len(ingredients_normalized) if ingredients_normalized else 0
            
            logger.info(f"Database coverage: {found_count}/{len(ingredients_normalized)} = {coverage*100:.1f}%")
            
            # Step 3: Get available prices for found ingredients
            available_ingredients = {}
            for ingredient in db_ingredients:
                prices_for_ing = session.query(Price).filter(
                    Price.ingredient_id == ingredient.id,
                    Price.in_stock == True  # Only in-stock items
                ).all()
                
                available_ingredients[ingredient.name] = [
                    {
                        "store": p.store.name,
                        "price": float(p.price)
                    }
                    for p in prices_for_ing
                ]
            
            # Step 4: Identify missing ingredients
            found_names = {ing.name for ing in db_ingredients}
            missing_ingredients = [
                ing for ing in ingredients_normalized
                if ing not in found_names
            ]
            
            logger.info(f"Missing ingredients: {len(missing_ingredients)} - {missing_ingredients[:5]}...")
            
            # Step 5: Check cache freshness for all stores
            all_stores = session.query(Store).all()
            cache_freshness = {}
            
            for store in all_stores:
                cache = session.query(CacheMetadata).filter(
                    CacheMetadata.store_id == store.id
                ).first()
                
                # Cache is fresh if:
                # - metadata exists AND
                # - last_fetch_time is recent (< 4 hours ago)
                is_fresh = (
                    cache is not None and
                    cache.last_fetch_time is not None and
                    (datetime.utcnow() - cache.last_fetch_time) < CACHE_TTL
                )
                
                cache_freshness[store.name] = is_fresh
                logger.debug(f"  {store.name}: {'fresh' if is_fresh else 'stale'}")
            
            # Step 6: Make decision
            # Fetch from API if:
            # - Coverage < 60% (we're missing critical items)
            # - OR cache is stale across all stores
            any_fresh = any(cache_freshness.values())
            should_fetch = (coverage < COVERAGE_THRESHOLD) or not any_fresh
            
            if should_fetch:
                reason = "coverage < 60%" if coverage < COVERAGE_THRESHOLD else "cache stale"
                logger.info(f"✓ Should fetch API: {reason}")
            else:
                logger.info(f"✓ Using cached prices: coverage sufficient and fresh")
            
            return DBCheckResult(
                coverage_percentage=round(coverage * 100, 2),
                available_ingredients=available_ingredients,
                missing_ingredients=missing_ingredients,
                should_fetch_api=should_fetch,
                cache_freshness=cache_freshness,
                timestamp=start_time
            )
        
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            # If DB fails, assume we need to fetch from API
            logger.warning("Database unavailable, defaulting to API fetch")
            return DBCheckResult(
                coverage_percentage=0,
                available_ingredients={},
                missing_ingredients=ingredient_list,
                should_fetch_api=True,  # Fail-safe: fetch from API
                cache_freshness={},
                timestamp=start_time
            )
    
    @staticmethod
    def update_cache_metadata(
        session: Session,
        store_id: int,
        coverage_percentage: int,
        data_source: str,
        ttl_hours: int = 4
    ) -> None:
        """
        Update cache metadata after fetching prices.
        
        Args:
            session: SQLAlchemy session
            store_id: Store to update
            coverage_percentage: % of ingredients in stock
            data_source: 'api', 'mock', 'cache'
            ttl_hours: Hours until cache expires (default 4)
        """
        try:
            from models import CacheMetadata
            
            cache = session.query(CacheMetadata).filter(
                CacheMetadata.store_id == store_id
            ).first()
            
            now = datetime.utcnow()
            next_refresh = now + timedelta(hours=ttl_hours)
            
            if cache:
                cache.last_fetch_time = now
                cache.coverage_percentage = coverage_percentage
                cache.data_source = data_source
                cache.next_refresh_at = next_refresh
            else:
                cache = CacheMetadata(
                    store_id=store_id,
                    last_fetch_time=now,
                    coverage_percentage=coverage_percentage,
                    data_source=data_source,
                    next_refresh_at=next_refresh
                )
                session.add(cache)
            
            session.commit()
            logger.info(f"✓ Updated cache metadata for store {store_id}")
        
        except Exception as e:
            logger.error(f"Failed to update cache metadata: {e}")
            session.rollback()


if __name__ == "__main__":
    # Example usage (requires database to be deployed)
    import logging
    from database import DatabaseManager
    import os
    from dotenv import load_dotenv
    
    logging.basicConfig(level=logging.INFO)
    
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    
    if db_url:
        db = DatabaseManager(db_url)
        
        # Initialize database
        # db.init_db()
        # db.seed_mock_data()
        
        with db.session_scope() as session:
            # Test coverage check
            ingredients = ["chicken breast", "broccoli", "rice", "milk", "unknown_item"]
            
            result = CoverageCheckService.check_database_coverage(ingredients, session)
            
            print(f"\nCoverage Check Results:")
            print(f"  Coverage: {result.coverage_percentage}%")
            print(f"  Missing: {result.missing_ingredients}")
            print(f"  Should fetch API: {result.should_fetch_api}")
            print(f"  Available ingredients: {len(result.available_ingredients)}")
        
        db.close()
    else:
        print("DATABASE_URL not set")
