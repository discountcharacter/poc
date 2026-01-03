from src.engine_research import get_market_estimate
import json

def test_engine():
    print("🚀 Starting Local Engine Test...")
    
    # Test Case: 2020 Maruti Swift in Hyderabad
    make = "Maruti"
    model = "Swift"
    year = 2020
    city = "hyderabad"
    
    print(f"🧪 Testing for: {year} {make} {model} in {city}")
    
    try:
        result = get_market_estimate(make, model, year, city)
        
        if result['success']:
            print("\n✅ TEST SUCCESSFUL")
            print(f"💰 Median Price: ₹{result['median_price']:.2f} Lakh")
            print(f"📊 Valid Listings Found: {result['count']}")
            print(f"📉 Price Range: {result['price_range']}")
            print("\n📌 Top Listings Sample:")
            for l in result['listings'][:3]:
                print(f"   - {l['year']} {l['title']} -> ₹{l['price']}L ({l['source']})")
        else:
            print("\n⚠️ TEST COMPLETED (No Data)")
            print(f"❌ Message: {result['message']}")
            if 'raw_results' in result:
                print(f"🔍 First few raw results: {result['raw_results'][:2]}")
                
    except Exception as e:
        print(f"\n❌ TEST CRASHED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_engine()
