import os
from dotenv import load_dotenv
from src.engine_logic import calculate_logic_price
from src.engine_scout import fetch_market_prices
from src.engine_oracle import get_gemini_estimate
from src.utils import calculate_final_price

# Load environment variables
load_dotenv()

def test_all_engines():
    print("--- Starting Engine Verification ---")
    
    # Test Data: 2020 Hyundai Creta SX (Petrol) with 50,000 km
    make = "Hyundai"
    model = "Creta"
    year = 2020
    variant = "SX Petrol"
    km = 50000
    condition = "Good"
    owners = 1
    
    # keys
    api_key_gemini = os.getenv("GOOGLE_API_KEY")
    api_key_search = os.getenv("GOOGLE_SEARCH_API_KEY")
    cx = os.getenv("SEARCH_ENGINE_ID")
    
    if not api_key_gemini: print("❌ Missing GOOGLE_API_KEY")
    if not api_key_search: print("❌ Missing GOOGLE_SEARCH_API_KEY")
    if not cx: print("❌ Missing SEARCH_ENGINE_ID")
    
    print(f"\nTesting Valuation for: {year} {make} {model} {variant}, {km}km\n")

    # 1. Engine A: Logic
    print("1. Testing Engine A (The Accountant)...")
    try:
        price_a = calculate_logic_price(make, model, year, variant, km, condition, owners)
        print(f"   ✅ Success: ₹ {price_a:,}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        price_a = None

    # 2. Engine B: Scout
    print("\n2. Testing Engine B (The Scout)...")
    try:
        price_b = fetch_market_prices(make, model, year, variant, km, api_key_search, cx)
        if price_b:
            print(f"   ✅ Success: ₹ {price_b:,}")
        else:
            print("   ⚠️ No results found (Check API Quota or Search query)")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        price_b = None

    # 3. Engine C: Oracle
    print("\n3. Testing Engine C (The Oracle)...")
    try:
        price_c = get_gemini_estimate(make, model, year, variant, km, condition, api_key_gemini)
        if price_c:
            print(f"   ✅ Success: ₹ {price_c:,}")
        else:
            print("   ⚠️ No response from Gemini (Check API Key)")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        price_c = None

    # 4. Synthesis
    print("\n4. Testing Synthesis...")
    final = calculate_final_price(price_a, price_b, price_c)
    print(f"   ✅ Final Recommended Price: ₹ {final:,}")

if __name__ == "__main__":
    test_all_engines()
