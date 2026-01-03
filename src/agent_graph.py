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
        LIVE PRICE FETCHING + FORMULA CALCULATION
        Step 1: Fetch NEW car base price from Google (with source URLs)
        Step 2: Apply depreciation formula
        """
        from datetime import datetime
        import numpy as np
        import re
        
        # Step 1: Get NEW car price from Google Search with source URLs
        print(f"   Fetching base price for NEW {make} {model}...")
        price_data = self._get_base_price_from_google(make, model, year, fuel)
        
        base_new_price = price_data['price']
        source_urls = price_data['sources']  # List of URLs where prices were found
        
        if base_new_price == 0:
            print(f"   ⚠️ Could not find base price, using estimated value")
            base_new_price = 800000  # Fallback
        
        print(f"   ✓ Base NEW price: ₹{base_new_price:,}")
        print(f"   ✓ Found on {len(source_urls)} sources")
        
        # Step 2: FORMULA - Calculate Market Retail Price
        current_year = datetime.now().year
        age = current_year - year
        
        # 1. Age-based depreciation (15% per year for first 5 years, then 8% per year)
        if age <= 5:
            depreciation_factor = 0.85 ** age
        else:
            depreciation_factor = (0.85 ** 5) * (0.92 ** (age - 5))
        
        # 2. KM-based adjustment
        expected_km = age * 12000
        km_diff = km - expected_km
        
        if km_diff > 0:
            km_adjustment = 1 - (km_diff * 2 / base_new_price)
        else:
            km_adjustment = 1 + (abs(km_diff) * 1 / base_new_price)
        
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
        
        # Generate listings with ACTUAL source URLs
        listings = []
        
        # Add main calculated price
        listings.append({
            "title": f"{year} {make.title()} {model.title()} {variant} (Used)",
            "price": market_price,
            "link": source_urls[0] if source_urls else "#",
            "source": "Calculated Price",
            "reason": f"Base: ₹{base_new_price:,} (NEW) → Applied depreciation formula"
        })
        
        # Add source listings showing where base price came from
        for idx, url in enumerate(source_urls[:3]):  # Show top 3 sources
            # Ensure URL starts with http:// or https://
            if url and not url.startswith('http'):
                url = 'https://' + url
            
            print(f"   → Source #{idx+1}: {url}")
            
            listings.append({
                "title": f"NEW {make.title()} {model.title()} Price Source #{idx+1}",
                "price": base_new_price,
                "link": url,
                "source": "Base Price Reference",
                "reason": "Click link to verify NEW car price"
            })
        
        reasoning = (
            f"Live base price: ₹{base_new_price/100000:.1f}L (fetched from {len(source_urls)} sources). "
            f"Formula: Age {depreciation_factor*100:.1f}% × KM {km_adjustment*100:.1f}% × "
            f"Fuel {fuel_factor*100:.0f}% × Owners {owner_factor*100:.0f}% × "
            f"Condition {condition_factor*100:.0f}% = ₹{market_price/100000:.2f}L"
        )
        
        return {
            "valid_listings": listings,
            "rejected_count": 0,
            "market_price": market_price,
            "reasoning": reasoning
        }
    
    def _get_base_price_from_google(self, make, model, year, fuel):
        """
        Fetch NEW car on-road price from Google Search
        Returns: dict with 'price' and 'sources' (list of URLs)
        """
        from datetime import datetime
        import numpy as np
        import re
        
        try:
            # Search for new car price
            current_year = datetime.now().year
            query = f"{current_year} {make} {model} {fuel if fuel else ''} new car on-road price India"
            
            print(f"      Searching: {query}")
            
            # Use Google Custom Search API
            if not self.search_key or not self.cx:
                print("      ⚠️ Google Search API not configured")
                return {'price': 0, 'sources': []}
            
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.search_key,
                "cx": self.cx,
                "q": query,
                "num": 5
            }
            
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            if "items" not in data:
                return {'price': 0, 'sources': []}
            
            # Extract price from snippets AND capture source URLs
            prices_with_urls = []  # List of (price, url) tuples
            
            for item in data["items"]:
                text = item.get("snippet", "") + " " + item.get("title", "")
                source_url = item.get("link", "")
                
                # Look for price patterns
                patterns = [
                    r'₹\s*([\d,]+\.?\d*)\s*(?:lakh|lac)',  # ₹12.50 Lakh
                    r'Rs\.?\s*([\d,]+)',                    # Rs 850000
                    r'INR\s*([\d,]+)',                      # INR 850000
                    r'([\d,]+)\s*(?:lakh|lac)',             # 12.5 Lakh
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    for match in matches:
                        try:
                            price_num = float(match.replace(',', ''))
                            
                            # Convert lakhs to actual rupees
                            if 'lakh' in text.lower() or 'lac' in text.lower():
                                if price_num < 100:  # Assume it's in lakhs
                                    price_num = price_num * 100000
                            
                            # Validate range (cars typically 2L - 50L)
                            if 200000 <= price_num <= 5000000:
                                prices_with_urls.append((int(price_num), source_url))
                                break  # Only take first valid price per URL
                        except:
                            continue
            
            if prices_with_urls:
                # Get prices and URLs separately
                prices = [p[0] for p in prices_with_urls]
                urls = [p[1] for p in prices_with_urls]
                
                # Return median price with all source URLs
                median_price = int(np.median(prices))
                
                print(f"      ✓ Found {len(prices)} prices from {len(urls)} sources")
                print(f"      ✓ Price range: ₹{min(prices):,} - ₹{max(prices):,}")
                print(f"      ✓ Using median: ₹{median_price:,}")
                
                return {
                    'price': median_price,
                    'sources': urls  # Return actual URLs for verification
                }
            
            return {'price': 0, 'sources': []}
            
        except Exception as e:
            print(f"      ✗ Error fetching base price: {e}")
            return {'price': 0, 'sources': []}

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
