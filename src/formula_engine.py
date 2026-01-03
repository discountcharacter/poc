import os
import requests
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class FormulaEngine:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        self.cx = os.getenv("SEARCH_ENGINE_ID")
        
    def get_base_new_price(self, make, model, variant, year, city):
        """
        Searches for the historical ex-showroom price of the car.
        """
        query = f"{year} {make} {model} {variant} launch price ex-showroom {city}"
        
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.api_key,
                "cx": self.cx,
                "q": query,
                "num": 3
            }
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            # Simple heuristic to extract price from snippets
            # Looking for patterns like "Rs. X.XX Lakh" or "X.XX Lakh"
            items = data.get("items", [])
            for item in items:
                snippet = item.get("snippet", "") + " " + item.get("title", "")
                # Regex for price in Lakhs (e.g. 9.5 Lakh, 9.50 Lakhs, Rs 9.5 Lakh)
                match = re.search(r"(?:Rs\.?|INR|₹)?\s?(\d+\.?\d*)\s?Lakhs?", snippet, re.IGNORECASE)
                if match:
                    price_lakhs = float(match.group(1))
                    if 1.0 < price_lakhs < 100.0: # Sanity check (between 1L and 1Cr)
                        return price_lakhs * 100000
                        
            # Regex for full numbers (e.g. 9,50,000)
            for item in items:
                snippet = item.get("snippet", "")
                match = re.search(r"(?:Rs\.?|INR|₹)\s?(\d{1,2},?\d{2},?\d{3})", snippet)
                if match:
                    price_str = match.group(1).replace(",", "")
                    return float(price_str)
                    
        except Exception as e:
            print(f"Formula Engine Search Error: {e}")
            
        return None

    def calculate_price(self, make, model, variant, year, km, fuel, owners, condition, city):
        """
        Calculates price based on the user's specific formula.
        """
        # 1. Get Base New Price
        base_new_price = self.get_base_new_price(make, model, variant, year, city)
        
        if not base_new_price:
            return {"error": "Could not find base new price for this car."}
            
        # 2. Apply User Formula
        current_year = datetime.now().year
        age = current_year - int(year)
        
        # 1. Age-based depreciation (15% per year for first 5 years, then 8% per year)
        if age <= 5:
            depreciation_factor = 0.85 ** age
        else:
            depreciation_factor = (0.85 ** 5) * (0.92 ** (age - 5))
            
        # 2. KM-based adjustment
        expected_km = age * 12000
        km_diff = km - expected_km
        
        # Avoid division by zero if base_new_price is somehow 0 (sanity check handled above)
        if base_new_price > 0:
            if km_diff > 0:
                # Penalty for excess KM
                km_adjustment = 1 - (km_diff * 2 / base_new_price)
            else:
                # Bonus for low KM
                km_adjustment = 1 + (abs(km_diff) * 1 / base_new_price)
        else:
            km_adjustment = 1.0
            
        km_adjustment = max(0.7, min(1.15, km_adjustment))
        
        # 3. Fuel type adjustment
        fuel_multiplier = {"diesel": 1.10, "petrol": 1.00, "cng": 0.95, "electric": 0.90}
        fuel_factor = fuel_multiplier.get(fuel.lower() if fuel else "petrol", 1.0)
        
        # 4. Ownership penalty
        owner_penalty = {1: 1.00, 2: 0.95, 3: 0.90, 4: 0.85}
        owner_factor = owner_penalty.get(owners if owners else 1, 0.85)
        
        # 5. Condition adjustment
        condition_multiplier = {"excellent": 1.05, "good": 1.00, "fair": 0.92, "poor": 0.80}
        condition_factor = condition_multiplier.get(condition.lower() if condition else "good", 1.0)
        
        # FINAL MARKET RETAIL PRICE
        market_price = int(
            base_new_price * 
            depreciation_factor * 
            km_adjustment * 
            fuel_factor * 
            owner_factor * 
            condition_factor
        )
        
        return {
            "price": market_price,
            "base_new_price": base_new_price,
            "factors": {
                "base_new_price": base_new_price,
                "depreciation_factor": round(depreciation_factor, 3),
                "km_adjustment": round(km_adjustment, 3),
                "fuel_factor": fuel_factor,
                "owner_factor": owner_factor,
                "condition_factor": condition_factor
            }
        }
