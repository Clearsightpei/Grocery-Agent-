"""
Unit Converter for Grocery Pricing Normalization

Handles conversion of various unit measurements to standardized base units:
- Volume: all → liter
- Weight: all → lb (pound)
- Count: all → each

This enables fair price comparison across different package sizes and units.
"""

import re
from typing import Tuple, Optional


class UnitNormalizer:
    """
    Normalizes grocery product quantities and prices to standard base units.
    
    Base Units:
    - Volume: liter (L)
    - Weight: pound (lb)
    - Count: each (unit)
    """
    
    # =========================================================================
    # CONVERSION FACTORS TO BASE UNITS
    # =========================================================================
    
    # Volume conversions: X unit → 1 liter
    VOLUME_TO_LITER = {
        # Liters
        'liter': 1.0,
        'litre': 1.0,
        'l': 1.0,
        
        # Milliliters
        'milliliter': 0.001,
        'millilitre': 0.001,
        'ml': 0.001,
        
        # Gallons (US)
        'gallon': 3.78541,
        'gal': 3.78541,
        'gallons': 3.78541,
        
        # Quarts (US)
        'quart': 0.946353,
        'qt': 0.946353,
        'quarts': 0.946353,
        
        # Pints (US)
        'pint': 0.473176,
        'pt': 0.473176,
        'pints': 0.473176,
        
        # Fluid ounces (US)
        'fluid ounce': 0.0295735,
        'fl oz': 0.0295735,
        'fl oz.': 0.0295735,
        'floz': 0.0295735,
        'fluid ounces': 0.0295735,
        
        # Cups (US)
        'cup': 0.236588,
        'cups': 0.236588,
        'c': 0.236588,
    }
    
    # Weight conversions: X unit → 1 pound
    WEIGHT_TO_LB = {
        # Pounds
        'pound': 1.0,
        'lb': 1.0,
        'lbs': 1.0,
        'lb.': 1.0,
        'pounds': 1.0,
        '#': 1.0,
        
        # Ounces
        'ounce': 1/16,
        'oz': 1/16,
        'oz.': 1/16,
        'ounces': 1/16,
        
        # Kilograms
        'kilogram': 2.20462,
        'kg': 2.20462,
        'kilograms': 2.20462,
        
        # Grams
        'gram': 0.00220462,
        'g': 0.00220462,
        'grams': 0.00220462,
        
        # Milligrams
        'milligram': 0.00000220462,
        'mg': 0.00000220462,
        'milligrams': 0.00000220462,
    }
    
    # Count (units) - no conversion needed
    COUNT_UNITS = {
        'each': 1.0,
        'count': 1.0,
        'piece': 1.0,
        'unit': 1.0,
        'item': 1.0,
        'bunch': 1.0,
        'pack': 1.0,
        'box': 1.0,
        'bottle': 1.0,
        'can': 1.0,
        'jar': 1.0,
        'bag': 1.0,
    }
    
    # Base units mapping
    BASE_UNITS = {
        'volume': 'liter',
        'weight': 'lb',
        'count': 'each',
    }
    
    @staticmethod
    def extract_quantity(text: str) -> Optional[Tuple[float, str]]:
        """
        Extract quantity and unit from product text using regex.
        
        Examples:
        - "Organic Milk 1 Gallon" → (1.0, 'gallon')
        - "Spinach 16oz" → (16.0, 'oz')
        - "12 pack eggs" → (12.0, 'pack')
        - "Chicken Breast 2 lb" → (2.0, 'lb')
        
        Args:
            text: Product name or description string
        
        Returns:
            Tuple of (quantity: float, unit: str) or None if no match found
        """
        if not text:
            return None
        
        # Pattern: number (int or decimal) followed by optional space and unit
        pattern = r'(\d+(?:\.\d+)?(?:/\d+)?)\s*([a-z\.#/]+)'
        
        matches = re.findall(pattern, text.lower())
        
        if matches:
            # Return the first match (most likely the package size)
            quantity_str, unit_str = matches[0]
            
            # Handle fractions like "1/2"
            if '/' in quantity_str:
                parts = quantity_str.split('/')
                quantity = float(parts[0]) / float(parts[1])
            else:
                quantity = float(quantity_str)
            
            # Clean up unit
            unit = unit_str.strip().rstrip('.')
            
            return (quantity, unit)
        
        return None
    
    @staticmethod
    def identify_unit_type(unit: str) -> Optional[str]:
        """
        Identify if a unit is for volume, weight, or count.
        
        Args:
            unit: Unit string (e.g., 'gallon', 'oz', 'lb', 'pack')
        
        Returns:
            'volume', 'weight', 'count', or None if unknown
        """
        unit_lower = unit.lower().strip().rstrip('.')
        
        if unit_lower in UnitNormalizer.VOLUME_TO_LITER:
            return 'volume'
        elif unit_lower in UnitNormalizer.WEIGHT_TO_LB:
            return 'weight'
        elif unit_lower in UnitNormalizer.COUNT_UNITS:
            return 'count'
        
        return None
    
    @staticmethod
    def normalize_price(
        raw_price: float,
        raw_title: str,
        target_base_unit: str = None
    ) -> Tuple[float, str, str]:
        """
        Calculate normalized price per base unit.
        
        Converts raw price to price-per-base-unit by extracting quantity
        from product title and converting to target unit.
        
        Args:
            raw_price: Original price (e.g., 4.29)
            raw_title: Product name/description (e.g., "Organic Milk 1 Gallon")
            target_base_unit: Target unit ('liter', 'lb', 'each'). 
                            If None, auto-detect from unit type.
        
        Returns:
            Tuple of:
            - normalized_price: Price per base unit (e.g., 1.13)
            - base_unit: The base unit used (e.g., 'liter')
            - extracted_unit: The original unit found (e.g., 'gallon')
        
        Example:
            >>> normalized, base, extracted = UnitNormalizer.normalize_price(
            ...     4.29, "Milk 1 Gallon", "liter"
            ... )
            >>> print(f"${normalized:.2f} per {base}")
            $1.13 per liter
        """
        # Extract quantity and unit from title
        result = UnitNormalizer.extract_quantity(raw_title)
        
        if not result:
            # No quantity found, return raw price as-is
            return (raw_price, 'each', 'unknown')
        
        quantity, extracted_unit = result
        
        # Identify unit type
        unit_type = UnitNormalizer.identify_unit_type(extracted_unit)
        
        if not unit_type:
            # Unknown unit, return raw price
            return (raw_price, 'each', extracted_unit)
        
        # Determine target base unit if not provided
        if target_base_unit is None:
            target_base_unit = UnitNormalizer.BASE_UNITS[unit_type]
        
        # Get conversion factor
        if unit_type == 'volume':
            conversion_factor = UnitNormalizer.VOLUME_TO_LITER.get(
                extracted_unit.lower().rstrip('.'), 1.0
            )
        elif unit_type == 'weight':
            conversion_factor = UnitNormalizer.WEIGHT_TO_LB.get(
                extracted_unit.lower().rstrip('.'), 1.0
            )
        else:  # count
            conversion_factor = 1.0
        
        # Calculate normalized price
        total_base_units = quantity * conversion_factor
        
        if total_base_units > 0:
            normalized_price = raw_price / total_base_units
        else:
            normalized_price = raw_price
        
        return (normalized_price, target_base_unit, extracted_unit)
    
    @staticmethod
    def batch_normalize(
        prices_list: list,
        price_field: str = 'price',
        title_field: str = 'title'
    ) -> list:
        """
        Normalize a batch of prices (useful for processing scraped data).
        
        Args:
            prices_list: List of price dicts, each with price/title
            price_field: Key name for price in each dict
            title_field: Key name for title in each dict
        
        Returns:
            List of dicts with added 'normalized_price' and 'base_unit' fields
        """
        normalized_list = []
        
        for item in prices_list:
            price = item.get(price_field, 0)
            title = item.get(title_field, '')
            
            norm_price, base_unit, extracted_unit = UnitNormalizer.normalize_price(price, title)
            
            item['normalized_price'] = round(norm_price, 2)
            item['base_unit'] = base_unit
            item['extracted_unit'] = extracted_unit
            
            normalized_list.append(item)
        
        return normalized_list


# ============================================================================
# EXAMPLE USAGE IN YOUR SCRAPING LOOP
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("UNIT NORMALIZER EXAMPLES")
    print("=" * 70)
    
    # Example 1: Milk gallon vs liter
    print("\n1. MILK PRICE COMPARISON (Volume):")
    price1, unit1, extracted1 = UnitNormalizer.normalize_price(4.29, "Organic Milk 1 Gallon")
    print(f"   Safeway: ${4.29} for 1 Gallon")
    print(f"   → Normalized: ${price1:.2f} per {unit1}")
    
    price2, unit2, extracted2 = UnitNormalizer.normalize_price(3.99, "Store Brand Milk 1 Liter")
    print(f"   \n   Trader Joe's: ${3.99} for 1 Liter")
    print(f"   → Normalized: ${price2:.2f} per {unit2}")
    
    print(f"\n   ✓ FAIR COMPARISON: ${price1:.2f}/L vs ${price2:.2f}/L")
    cheaper = "Trader Joe's" if price2 < price1 else "Safeway"
    print(f"   Winner: {cheaper} saves ${abs(price1-price2):.2f}/liter")
    
    # Example 2: Spinach by weight
    print("\n\n2. SPINACH PRICE COMPARISON (Weight):")
    price3, unit3, extracted3 = UnitNormalizer.normalize_price(4.99, "Fresh Spinach 16oz")
    print(f"   Store A: ${4.99} for 16oz")
    print(f"   → Normalized: ${price3:.2f} per {unit3}")
    
    price4, unit4, extracted4 = UnitNormalizer.normalize_price(5.99, "Organic Spinach 1lb")
    print(f"   \n   Store B: ${5.99} for 1lb")
    print(f"   → Normalized: ${price4:.2f} per {unit4}")
    
    print(f"\n   ✓ FAIR COMPARISON: ${price3:.2f}/lb vs ${price4:.2f}/lb")
    cheaper = "Store A" if price3 < price4 else "Store B"
    print(f"   Winner: {cheaper} saves ${abs(price3-price4):.2f}/lb")
    
    # Example 3: Eggs (count-based)
    print("\n\n3. EGGS PRICE COMPARISON (Count):")
    price5, unit5, extracted5 = UnitNormalizer.normalize_price(3.99, "Brown Eggs 12 pack")
    print(f"   Store A: ${3.99} for 12 pack")
    print(f"   → Normalized: ${price5:.2f} per {unit5}")
    
    price6, unit6, extracted6 = UnitNormalizer.normalize_price(5.49, "Free Range Eggs 18 count")
    print(f"   \n   Store B: ${5.49} for 18 count")
    print(f"   → Normalized: ${price6:.2f} per {unit6}")
    
    print(f"\n   ✓ FAIR COMPARISON: ${price5:.2f}/egg vs ${price6:.2f}/egg")
    cheaper = "Store A" if price5 < price6 else "Store B"
    print(f"   Winner: {cheaper} saves ${abs(price5-price6):.2f}/egg")
    
    # Example 4: Batch processing (simulating scraper loop)
    print("\n\n4. BATCH PROCESSING (Like in scraping loop):")
    scraped_prices = [
        {'title': 'Organic Milk 1 Gallon', 'price': 5.49, 'store': 'Whole Foods'},
        {'title': 'Store Brand Milk 2 Liters', 'price': 4.29, 'store': 'Safeway'},
        {'title': 'Chicken Breast 1.5 lb', 'price': 8.99, 'store': 'Trader Joe\'s'},
        {'title': 'Chicken Thighs 3 lb', 'price': 10.99, 'store': 'Safeway'},
        {'title': 'Eggs 12 count', 'price': 3.99, 'store': 'Local Market'},
        {'title': 'Orange Juice 1 Gallon', 'price': 6.99, 'store': 'Whole Foods'},
    ]
    
    print("\n   Before normalization:")
    for item in scraped_prices[:3]:
        print(f"   - {item['title']:35} @ {item['store']:20} ${item['price']:6.2f}")
    
    normalized = UnitNormalizer.batch_normalize(scraped_prices)
    
    print("\n   After normalization:")
    print(f"\n   {'Product':<30} {'Store':<20} {'Raw Price':<12} {'Norm Price':<12} {'Unit'}")
    print("   " + "-" * 85)
    for item in normalized:
        print(f"   {item['title']:<30} {item['store']:<20} "
              f"${item['price']:<11.2f} ${item['normalized_price']:<11.2f} {item['base_unit']}")
#     formatted_price = normalizer.format_normalized_price(normalized_price)
#     database.store({
#         'product': item['name'],
#         'normalized_price': normalized_price,
#         'formatted_price': formatted_price
#     })