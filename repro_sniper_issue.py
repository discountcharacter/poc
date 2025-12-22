
import sys
import os

# Add the project directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.engine_sniper import fetch_closest_match

def test_matching():
    # Simulate user search: 2021 MG Hector Sharp in Hyderabad
    make = "MG"
    model = "Hector"
    year = 2021
    variant = "Sharp"
    km = 45000
    city = "Hyderabad"
    
    # We don't need real API keys for the scraping part we are testing
    price, sources, debug = fetch_closest_match(make, model, year, variant, km, city, None, None)
    
    print(f"Search Query: {year} {make} {model} {variant}")
    print(f"Selected Price: {price}")
    print(f"Debug Log:\n{debug}")
    
    if price == 1850000:
        print("\nFAILURE: Picked 2023 18.5L listing instead of 2021 13.5L listing!")
    elif price == 1350000:
        print("\nSUCCESS: Picked correct 2021 13.5L listing.")
    else:
        print(f"\nPicked: {price}")

    print("\n" + "="*50)
    print("Test Case 2: Broad Variant (Exact Match vs Pro)")
    # If user searches 'Sharp', it should NOT pick 'Sharp Pro' if 'Sharp' is available
    price2, sources2, debug2 = fetch_closest_match(make, model, 2021, "Sharp", km, city, None, None)
    print(f"Search Query: 2021 MG Hector Sharp")
    print(f"Selected Price: {price2}")
    if "Sharp Pro" in debug2.split("Best Match:")[1].split("(")[0]:
        print("FAILURE: Picked 'Sharp Pro' when 'Sharp' was available.")
    else:
        print("SUCCESS: Correctly prioritized 'Sharp' over 'Sharp Pro'.")

if __name__ == "__main__":
    test_matching()
