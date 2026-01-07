"""
Simple test script for Gemini-based price fetcher
Run with: python test_gemini_price.py
"""

import os
import sys
sys.path.insert(0, '/home/user/poc')

from src.price_fetcher_gemini import price_fetcher

def main():
    print("="*60)
    print("Testing Gemini Price Fetcher with Google Search Grounding")
    print("="*60)

    # Test 1: Swift LXI
    print("\n[Test 1] Maruti Suzuki Swift LXI Petrol 2020")
    result = price_fetcher.get_current_price(
        make="Maruti Suzuki",
        model="Swift",
        variant="LXI",
        fuel="Petrol",
        year=2020,
        month=3,
        transmission="Manual"
    )

    if result and result.get('ex_showroom_price'):
        price = result['ex_showroom_price']
        print(f"✅ Price: ₹{price:,.0f} ({price/100000:.2f} Lakhs)")
        print(f"   Source: {result['source']}")
        print(f"   Expected: ~₹5.78 Lakhs")
    else:
        print("❌ No price found")

    print("\n" + "="*60)

if __name__ == "__main__":
    main()
