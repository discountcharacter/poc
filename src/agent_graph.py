import os
import time
import requests
import json
import re

from dotenv import load_dotenv

load_dotenv()

class ValuationAgent:
    """
    Rescue-v2.0: Automated Market Analysis
    Browses live markets via Custom Search and uses LLM (Gemini REST API) to verify data.
    """
    def __init__(self, gemini_key, search_key=None, cx=None):
        self.gemini_key = gemini_key or os.getenv("GOOGLE_API_KEY")
        self.search_key = search_key or os.getenv("GOOGLE_SEARCH_API_KEY")
        self.cx = cx or os.getenv("SEARCH_ENGINE_ID")

    def search_market(self, make, model, year, variant, location, km=None, fuel=None, owners=None, condition=None, remarks=None):
        """
        Orchestrates the market valuation using FORMULA-BASED calculation.
        NO EXTERNAL API CALLS - Completely deterministic.
        """
        print(f"🤖 Agent: Calculating price for {year} {make} {model} {variant}...")
        print(f"   Using FORMULA (No Google Search, No AI)")
        
        # Direct formula calculation - no browsing needed
        analysis = self._filter_with_llm([], make, model, year, variant, location, km, fuel, owners, condition, remarks)
        
        print(f"✅ Agent: Market Retail Price = ₹{analysis.get('market_price', 0):,}")
        
        return analysis

    def _filter_with_llm(self, raw_data, make, model, year, variant, location, km, fuel, owners, condition, remarks):
        """
        FORMULA-BASED MARKET PRICE CALCULATION (Deterministic - No AI/API calls)
        This ensures the same car details always return the same price.
        """
        from datetime import datetime
        import numpy as np
        
        # Base price lookup table (retail market prices in INR)
        # This can be expanded as needed - formula will still work for unlisted cars
        base_prices = {
            # Maruti
            ("maruti", "alto"): 280000,
            ("maruti", "swift"): 550000,
            ("maruti", "baleno"): 650000,
            ("maruti", "wagon r"): 400000,
            ("maruti", "dzire"): 600000,
            ("maruti", "swift dzire"): 600000,
            ("maruti", "vitara"): 850000,
            ("maruti", "brezza"): 900000,
            ("maruti", "ertiga"): 900000,
            ("maruti", "ciaz"): 750000,
            
            # Hyundai
            ("hyundai", "i10"): 400000,
            ("hyundai", "grand"): 500000,
            ("hyundai", "i20"): 700000,
            ("hyundai", "venue"): 1000000,
            ("hyundai", "creta"): 1400000,
            ("hyundai", "verna"): 1100000,
            
            # Honda
            ("honda", "city"): 1200000,
            ("honda", "amaze"): 750000,
            ("honda", "jazz"): 750000,
            ("honda", "wr-v"): 900000,
            
            # Tata
            ("tata", "tiago"): 500000,
            ("tata", "tigor"): 650000,
            ("tata", "nexon"): 1000000,
            ("tata", "harrier"): 1800000,
            
            # Mahindra
            ("mahindra", "xuv500"): 1600000,
            ("mahindra", "xuv700"): 2000000,
            ("mahindra", "scorpio"): 1400000,
            ("mahindra", "thar"): 1400000,
            ("mahindra", "bolero"): 900000,
            
            # Toyota
            ("toyota", "innova"): 1800000,
            ("toyota", "fortuner"): 3500000,
            
            # Ford
            ("ford", "ecosport"): 900000,
            ("ford", "figo"): 550000,
        }
        
        # Get base price (new car retail price)
        key = (make.lower(), model.lower())
        base_new_price = base_prices.get(key, 800000)  # Default for unlisted models
        
        # FORMULA: Calculate Market Retail Price
        current_year = datetime.now().year
        age = current_year - year
        
        # 1. Age-based depreciation (15% per year for first 5 years, then 8% per year)
        if age <= 5:
            depreciation_factor = 0.85 ** age
        else:
            depreciation_factor = (0.85 ** 5) * (0.92 ** (age - 5))
        
        # 2. KM-based adjustment
        # Expected KM: 12,000 per year
        expected_km = age * 12000
        km_diff = km - expected_km
        
        if km_diff > 0:
            # Excess KM penalty: Rs 2 per extra km
            km_adjustment = 1 - (km_diff * 2 / base_new_price)
        else:
            # Low KM bonus: Rs 1 per saved km
            km_adjustment = 1 + (abs(km_diff) * 1 / base_new_price)
        
        km_adjustment = max(0.7, min(1.15, km_adjustment))  # Cap between 70% and 115%
        
        # 3. Fuel type adjustment
        fuel_multiplier = {
            "diesel": 1.10,  # Diesel cars retain higher value
            "petrol": 1.00,
            "cng": 0.95,
            "electric": 0.90  # Higher depreciation due to battery concerns
        }
        fuel_factor = fuel_multiplier.get(fuel.lower() if fuel else "petrol", 1.0)
        
        # 4. Ownership penalty
        owner_penalty = {
            1: 1.00,
            2: 0.95,
            3: 0.90,
            4: 0.85
        }
        owner_factor = owner_penalty.get(owners if owners else 1, 0.85)
        
        # 5. Condition adjustment
        condition_multiplier = {
            "excellent": 1.05,
            "good": 1.00,
            "fair": 0.92,
            "poor": 0.80
        }
        condition_factor = condition_multiplier.get(condition.lower() if condition else "good", 1.0)
        
        # FINAL MARKET RETAIL PRICE FORMULA
        market_price = int(
            base_new_price * 
            depreciation_factor * 
            km_adjustment * 
            fuel_factor * 
            owner_factor * 
            condition_factor
        )
        
        # Generate mock listings for display (deterministic)
        listings = [
            {
                "title": f"{year} {make.title()} {model.title()} {variant}",
                "price": market_price,
                "link": "#formula-based",
                "source": "Formula Calculation",
                "reason": f"Base: ₹{base_new_price:,}, Age: {age}y, KM: {km:,}"
            }
        ]
        
        reasoning = (
            f"Formula-based calculation (100% deterministic). "
            f"Base new price: ₹{base_new_price/100000:.1f}L. "
            f"Age depreciation: {depreciation_factor*100:.1f}%. "
            f"KM adjustment: {km_adjustment*100:.1f}%. "
            f"Fuel ({fuel}): {fuel_factor*100:.0f}%. "
            f"Owners ({owners}): {owner_factor*100:.0f}%. "
            f"Condition ({condition}): {condition_factor*100:.0f}%. "
            f"Final Market Retail: ₹{market_price/100000:.2f}L"
        )
        
        return {
            "valid_listings": listings,
            "rejected_count": 0,
            "market_price": market_price,
            "reasoning": reasoning
        }

    def _call_gemini_rest(self, prompt):
        """
        Raw REST API call to Gemini Pro with Retry logic.
        """
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-latest:generateContent?key={self.gemini_key}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        for attempt in range(3):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    # Check if candidates exist (Safety filters can block response)
                    if not data.get('candidates'):
                        print(f"Gemini Safety/Block Error: {data}")
                        return f"Error: Model blocked response. Safety/Other reason. Raw: {json.dumps(data)}"
                    return data['candidates'][0]['content']['parts'][0]['text']
                else:
                    print(f"Gemini API Error {response.status_code}: {response.text}")
                    if response.status_code >= 500:
                        time.sleep(1) # Retry on server error
                        continue
                    return f"Error: API {response.status_code} - {response.text}"
            except Exception as e:
                print(f"Gemini REST Exception: {e}")
                time.sleep(1)
        
        return "Error: Failed after 3 attempts."

def raw_listings_str(listings):
    return "\n---\n".join([f"Item {i+1}: {t.replace(chr(10), ' ')}" for i, t in enumerate(listings)])

if __name__ == "__main__":
    # Test
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_SEARCH_API_KEY") # Try both
    # Load from main.py env if possible
    if not key:
        print("Set GOOGLE_API_KEY to run test.")
        exit()
        
    agent = ValuationAgent(key)
    res = agent.search_market("Hyundai", "Creta", 2020, "SX Petrol", "Hyderabad")
    print(json.dumps(res, indent=2))
