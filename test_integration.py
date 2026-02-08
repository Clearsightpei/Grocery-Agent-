#!/usr/bin/env python3
"""
Integration Validation Script
Tests all integration points to ensure the system works end-to-end
"""

import os
import sys
from dotenv import load_dotenv

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_imports():
    """Test all required imports"""
    print_section("TEST 1: Module Imports")
    
    modules = [
        ("agent_logic", ["generate_meal_plan", "check_grocery_prices_v2", "compute_shopping_strategy"]),
        ("database", ["DatabaseManager"]),
        ("models", ["Base", "Store", "Ingredient", "Price"]),
        ("mock_data", ["MockDataManager"]),
        ("unified_pricing", ["PricingEngine"]),
        ("serpapi_client", ["SERPAPIClient"]),
        ("pricing_service", ["CoverageCheckService"]),
    ]
    
    all_passed = True
    for module_name, items in modules:
        try:
            module = __import__(module_name)
            for item in items:
                if not hasattr(module, item):
                    print(f"  ✗ {module_name}.{item} - NOT FOUND")
                    all_passed = False
            print(f"  ✓ {module_name}")
        except ImportError as e:
            print(f"  ✗ {module_name} - {e}")
            all_passed = False
    
    return all_passed

def test_database():
    """Test database initialization"""
    print_section("TEST 2: Database Initialization")
    
    try:
        from database import DatabaseManager
        from models import Store
        
        # Use SQLite in-memory for testing
        db_url = "sqlite:///:memory:"
        db_manager = DatabaseManager(db_url)
        db_manager.init_db()
        print(f"  ✓ Database initialized successfully")
        
        # Verify session works
        session = db_manager.get_session()
        store_count = session.query(Store).count()
        print(f"  ✓ Database session created (0 stores initially)")
        session.close()
        
        return True
    except Exception as e:
        print(f"  ✗ Database test failed: {e}")
        return False

def test_mock_data():
    """Test mock data seeding"""
    print_section("TEST 3: Mock Data Seeding")
    
    try:
        from database import DatabaseManager
        from models import Store
        from mock_data import MockDataManager
        
        # Use SQLite in-memory
        db_url = "sqlite:///:memory:"
        db_manager = DatabaseManager(db_url)
        db_manager.init_db()
        
        session = db_manager.get_session()
        MockDataManager.seed_default_data(session)
        
        store_count = session.query(Store).count()
        print(f"  ✓ Mock data seeded successfully ({store_count} stores)")
        
        session.close()
        return True
    except Exception as e:
        print(f"  ✗ Mock data test failed: {e}")
        return False

def test_pricing_engine():
    """Test pricing engine"""
    print_section("TEST 4: Pricing Engine")
    
    try:
        from database import DatabaseManager
        from models import Store
        from mock_data import MockDataManager
        from unified_pricing import PricingEngine
        
        # Setup database
        db_url = "sqlite:///:memory:"
        db_manager = DatabaseManager(db_url)
        db_manager.init_db()
        
        session = db_manager.get_session()
        MockDataManager.seed_default_data(session)
        
        # Test pricing engine
        engine = PricingEngine(session, serpapi_client=None)
        result = engine.get_ingredient_prices(
            ["Chicken", "Rice", "Tomato"],
            user_location="San Francisco, CA"
        )
        
        print(f"  ✓ Pricing engine works")
        print(f"    Data source: {result.data_source}")
        print(f"    Coverage: {result.coverage_pct}%")
        print(f"    Ingredients priced: {len(result.ingredient_prices)}")
        
        session.close()
        return True
    except Exception as e:
        print(f"  ✗ Pricing engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integrated_pricing():
    """Test check_grocery_prices_v2"""
    print_section("TEST 5: Integrated Pricing (check_grocery_prices_v2)")
    
    try:
        from database import DatabaseManager
        from models import Store
        from mock_data import MockDataManager
        from agent_logic import check_grocery_prices_v2
        
        # Setup database
        db_url = "sqlite:///:memory:"
        db_manager = DatabaseManager(db_url)
        db_manager.init_db()
        
        session = db_manager.get_session()
        MockDataManager.seed_default_data(session)
        
        # Test integrated pricing
        pricing = check_grocery_prices_v2(
            ["Chicken", "Rice", "Tomato"],
            db_session=session,
            serpapi_client=None,
            user_location="San Francisco, CA"
        )
        
        print(f"  ✓ Integrated pricing works")
        print(f"    Stores returned: {len(pricing)}")
        for store, data in pricing.items():
            print(f"    - {store}: ${data['total']:.2f} ({data['available_pct']}% available)")
        
        session.close()
        return True
    except Exception as e:
        print(f"  ✗ Integrated pricing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_meal_plan():
    """Test meal plan generation"""
    print_section("TEST 6: Meal Plan Generation")
    
    try:
        from agent_logic import generate_meal_plan
        
        # Test meal plan generation
        print("  Generating meal plan...")
        mp = generate_meal_plan("Vegetarian, simple")
        
        print(f"  ✓ Meal plan generated")
        print(f"    Days: {len(mp.meals)}")
        print(f"    Sample: {mp.meals[0].day} - {mp.meals[0].dish_name}")
        
        return len(mp.meals) == 7
    except Exception as e:
        print(f"  ✗ Meal plan test failed: {e}")
        return False

def test_strategy():
    """Test shopping strategy"""
    print_section("TEST 7: Shopping Strategy")
    
    try:
        from agent_logic import compute_shopping_strategy
        
        # Test strategy
        strategy = compute_shopping_strategy(["Chicken", "Rice", "Tomato"])
        
        print(f"  ✓ Strategy computed")
        print(f"    Cheapest: {strategy['cheapest']}")
        print(f"    Most available: {strategy['least_time']}")
        
        return True
    except Exception as e:
        print(f"  ✗ Strategy test failed: {e}")
        return False

def main():
    """Run all tests"""
    load_dotenv()
    
    print("\n" + "╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "AI GROCERY AGENT - INTEGRATION TESTS" + " " * 17 + "║")
    print("╚" + "=" * 68 + "╝")
    
    tests = [
        ("Imports", test_imports),
        ("Database", test_database),
        ("Mock Data", test_mock_data),
        ("Pricing Engine", test_pricing_engine),
        ("Integrated Pricing", test_integrated_pricing),
        ("Meal Plan", test_meal_plan),
        ("Strategy", test_strategy),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Unexpected error in {name}: {e}")
            results.append((name, False))
    
    # Summary
    print_section("SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n  🎉 All integration tests passed!")
        print("\n  The system is ready for deployment.")
        return 0
    else:
        print(f"\n  ⚠️  {total - passed} test(s) failed.")
        print("\n  Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
