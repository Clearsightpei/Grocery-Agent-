"""
INTEGRATION GUIDE: Using UnitNormalizer in agent_logic.py Scraping Loop

This shows the exact code pattern to normalize prices before storing in database.
"""

# ============================================================================
# STEP 1: ADD THIS IMPORT AT THE TOP OF agent_logic.py
# ============================================================================

# Add to imports section:
from unit_converter import UnitNormalizer

# ============================================================================
# STEP 2: NORMALIZE PRICES IN YOUR SCRAPING LOOP
# ============================================================================

# Pattern A: Single Item Normalization
def process_single_scraped_item(scraped_item):
    """
    Process a single item from scraper.
    
    Args:
        scraped_item: Dict with 'title', 'price', 'store_name'
    
    Returns:
        Dict ready for database insertion with normalized price
    """
    raw_price = scraped_item['price']
    product_title = scraped_item['title']
    store_name = scraped_item['store_name']
    
    # Normalize the price
    normalized_price, base_unit, extracted_unit = UnitNormalizer.normalize_price(
        raw_price=raw_price,
        raw_title=product_title,
        target_base_unit=None  # Auto-detect (liter, lb, or each)
    )
    
    # Return with both raw and normalized prices
    return {
        'store_name': store_name,
        'product_title': product_title,
        'raw_price': raw_price,
        'normalized_price': normalized_price,  # ← Store THIS in database
        'base_unit': base_unit,  # ← Store THIS too (for comparisons)
        'extracted_unit': extracted_unit,
        'in_stock': True,
        'last_verified': datetime.now()
    }


# ============================================================================
# Pattern B: Batch Normalization (Recommended for Scraper Loops)
# ============================================================================

def normalize_scraped_batch(scraped_items):
    """
    Normalize a batch of scraped prices before database insertion.
    
    Args:
        scraped_items: List of dicts from scraper
    
    Returns:
        List ready for batch database insert
    """
    # Extract prices and titles for normalization
    prices_for_norm = [
        {
            'title': item['product_title'],
            'price': item['raw_price'],
            'store': item['store_name']
        }
        for item in scraped_items
    ]
    
    # Batch normalize
    normalized = UnitNormalizer.batch_normalize(
        prices_for_norm,
        price_field='price',
        title_field='title'
    )
    
    # Prepare for database insertion
    db_items = []
    for item in normalized:
        db_item = {
            'store_name': item['store'],
            'product_title': item['title'],
            'raw_price': item['price'],
            'normalized_price': item['normalized_price'],  # ← USE THIS
            'base_unit': item['base_unit'],               # ← USE THIS
            'extracted_unit': item['extracted_unit'],
            'in_stock': True,
            'last_verified': datetime.now()
        }
        db_items.append(db_item)
    
    return db_items


# ============================================================================
# STEP 3: EXAMPLE - INTEGRATE INTO EXISTING SCRAPING FUNCTION
# ============================================================================

async def check_grocery_prices_with_normalization(ingredients: List[str]) -> Dict[str, Dict]:
    """
    Enhanced version that normalizes prices before comparison.
    
    This replaces the old check_grocery_prices() function.
    Now prices are normalized for fair comparison across units.
    """
    # Your existing scraper code...
    scraped_prices = []
    
    for store in ['Trader Joe\'s', 'Safeway', 'Whole Foods']:
        for ingredient in ingredients:
            # Your scraping logic here...
            scraped_item = {
                'title': f'Some Product 1 Gallon',  # Product title from scraper
                'price': 4.29,  # Raw price from scraper
                'store_name': store
            }
            
            # NORMALIZE BEFORE PROCESSING
            normalized_item = process_single_scraped_item(scraped_item)
            scraped_prices.append(normalized_item)
    
    # Now build your price matrix with normalized prices
    results = {}
    for store_name in ['Trader Joe\'s', 'Safeway', 'Whole Foods']:
        store_items = [p for p in scraped_prices if p['store_name'] == store_name]
        
        items_dict = {}
        total = 0.0
        available_count = 0
        
        for item in store_items:
            # USE NORMALIZED PRICE HERE
            price = item['normalized_price']
            items_dict[item['product_title']] = {
                'price': price,
                'available': True,
                'base_unit': item['base_unit']  # Track the unit
            }
            total += price
            available_count += 1
        
        results[store_name] = {
            'items': items_dict,
            'total': round(total, 2),
            'available_pct': round(100.0 * available_count / max(1, len(ingredients)), 1)
        }
    
    return results


# ============================================================================
# STEP 4: STORE IN DATABASE WITH NORMALIZATION
# ============================================================================

def store_normalized_prices_to_db(scraped_items, db_session):
    """
    Store normalized prices in database.
    
    Args:
        scraped_items: Raw scraped prices
        db_session: SQLAlchemy session
    """
    from models import Ingredient, Store, Price
    from datetime import datetime, timedelta
    
    # Normalize all items
    normalized = normalize_scraped_batch(scraped_items)
    
    # Store in database
    for item in normalized:
        # Get or create ingredient
        ingredient = db_session.query(Ingredient).filter_by(
            name=item['product_title'].lower()
        ).first()
        
        if not ingredient:
            ingredient = Ingredient(
                name=item['product_title'].lower(),
                category='unknown',
                unit=item['base_unit']  # Use normalized unit
            )
            db_session.add(ingredient)
            db_session.flush()
        
        # Get store
        store = db_session.query(Store).filter_by(
            name=item['store_name']
        ).first()
        
        if store:
            # Create or update price record with NORMALIZED price
            price_record = Price(
                ingredient_id=ingredient.id,
                store_id=store.id,
                price=item['normalized_price'],  # ← STORE NORMALIZED PRICE
                in_stock=item['in_stock'],
                expires_at=datetime.now() + timedelta(hours=24)
            )
            
            db_session.merge(price_record)
    
    db_session.commit()


# ============================================================================
# QUICK REFERENCE: WHAT TO CHANGE IN agent_logic.py
# ============================================================================

"""
1. ADD IMPORT:
   from unit_converter import UnitNormalizer

2. IN YOUR SCRAPING LOOP, NORMALIZE PRICES:
   
   Before:
   -------
   price_matrix.set_price(ingredient, store.name, raw_price)
   
   After:
   ------
   normalized_price, base_unit, _ = UnitNormalizer.normalize_price(
       raw_price, product_title
   )
   price_matrix.set_price(ingredient, store.name, normalized_price)

3. WHEN STORING TO DATABASE:
   
   Before:
   -------
   db_price = Price(
       ingredient_id=ing.id,
       store_id=store.id,
       price=raw_price  # ← Raw, unfair comparison
   )
   
   After:
   ------
   db_price = Price(
       ingredient_id=ing.id,
       store_id=store.id,
       price=normalized_price,  # ← Normalized, fair comparison
       unit=base_unit  # ← Track the unit
   )

4. WHEN COMPARING PRICES:
   
   Now all prices in database are per unit:
   - Milk: $1.13 per liter (not $4.29 per gallon)
   - Spinach: $3.12 per lb (not $4.99 per 16oz)
   - Eggs: $0.33 per egg (not $3.99 per dozen)
"""
