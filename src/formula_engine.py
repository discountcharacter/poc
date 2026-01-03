import os
import requests
import re
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class FormulaEngine:
    def __init__(self):
        self.search_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        self.cx = os.getenv("SEARCH_ENGINE_ID")

    def calculate_price(self, make, model, variant, year, km, fuel, owners, condition, location):
        """
        Calculates price using the User's specific formula + Google Search for Base New Price.
        """
        print(f"🤖 Formula Engine: Calculating for {year} {make} {model} {variant} in {location}...")

        # Step 1: Get NEW car price from Google Search with source URLs
        price_data = self._get_base_price_from_google(make, model, year, fuel, variant, location)
        
        base_new_price = price_data['price']
        source_details = price_data.get('source_details', [])
        
        if base_new_price == 0:
            print(f"   ⚠️ Could not find base price, using fallbacks")
            # Minimal fallback or return error? 
            # User's code used 800000. Let's return error if 0 to be safe, or use fallback if desired.
            # Sticking to error for now to prompt user, or maybe user prefers fallback?
            # User's code: base_new_price = 800000
            # I'll enable fallback but mark it
            base_new_price = 800000
            print("   -> Using fallback base price: 8,00,000")
            
        
        # Step 2: FORMULA - Calculate Market Retail Price
        current_year = datetime.now().year
        age = max(0, current_year - int(year))
        
        # 1. Age-based depreciation (15% per year for first 5 years, then 8% per year)
        if age <= 5:
            depreciation_factor = 0.85 ** age
        else:
            depreciation_factor = (0.85 ** 5) * (0.92 ** (age - 5))
        
        # 2. KM-based adjustment
        expected_km = age * 12000
        km_diff = km - expected_km
        
        if base_new_price > 0:
            if km_diff > 0:
                km_adjustment = 1 - (km_diff * 2 / base_new_price)
            else:
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
                "condition_factor": condition_factor,
                "sources_count": len(source_details)
            },
            "source_details": source_details
        }

    def _get_base_price_from_google(self, make, model, year, fuel, variant=None, location=None):
        """
        Fetch NEW car on-road price from Google Search (User provided logic).
        Returns: dict with 'price' and 'sources' (list of URLs)
        """
        try:
            # Search for new car price - INCLUDE VARIANT in search
            current_year = datetime.now().year
            
            # Build specific query with variant and location if available
            query_parts = [f"{current_year}", make, model]
            if variant:
                query_parts.append(variant)
            if fuel:
                query_parts.append(fuel)
            query_parts.extend(["new car on-road price"])
            if location:
                query_parts.append(location)
            query_parts.append("India")
            
            query = " ".join(query_parts)
            
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
                "num": 10  # Get more results to filter better
            }
            
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            if "items" not in data:
                return {'price': 0, 'sources': []}
            
            # Extract price from snippets AND capture source URLs
            prices_with_urls = []  # List of (price, url, title, score) tuples
            
            for item in data["items"]:
                text = item.get("snippet", "") + " " + item.get("title", "")
                source_url = item.get("link", "")
                title = item.get("title", "")
                
                text_lower = text.lower()
                
                # Simplified filtering: Accept if it has a price, prefer location/variant matches
                has_location_match = False
                has_variant_match = False
                
                # Check location match
                if location:
                    if location.lower() in text_lower or location.lower() in source_url.lower():
                        has_location_match = True
                
                # Check variant match (more lenient)
                if variant:
                    # Remove special chars and check if any variant part is in text
                    variant_clean = variant.lower().replace("(", "").replace(")", "").replace("-", " ")
                    if variant_clean in text_lower:
                        has_variant_match = True
                
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
                                # Calculate score for sorting
                                score = 0
                                if has_location_match:
                                    score += 10
                                if has_variant_match:
                                    score += 5
                                
                                prices_with_urls.append((int(price_num), source_url, title, score))
                                
                                match_info = []
                                if has_location_match:
                                    match_info.append("location✓")
                                if has_variant_match:
                                    match_info.append("variant✓")
                                match_str = ", ".join(match_info) if match_info else "general"
                                
                                print(f"      ✓ {title[:50]}... - ₹{int(price_num):,} [{match_str}]")
                                break  # Only take first valid price per URL
                        except:
                            continue
            
            if prices_with_urls:
                # Sort by score (highest first) - location and variant matches appear first
                prices_with_urls.sort(key=lambda x: x[3], reverse=True)
                
                # Get prices and URLs separately
                prices = [p[0] for p in prices_with_urls]
                urls = [p[1] for p in prices_with_urls]
                titles = [p[2] for p in prices_with_urls]
                
                # Return median price AND individual source data
                median_price = int(np.median(prices))
                
                # Build source list with EXACT prices from each link
                source_list = []
                for i, (price, url, title, score) in enumerate(prices_with_urls):  # Fixed: added score
                    source_list.append({
                        'price': price,  # EXACT price from this source
                        'url': url,
                        'title': title,
                        'score': score
                    })
                
                print(f"      ✓ Found {len(prices)} MATCHING prices from {len(urls)} sources")
                print(f"      ✓ Price range: ₹{min(prices):,} - ₹{max(prices):,}")
                print(f"      ✓ Using median: ₹{median_price:,}")
                
                return {
                    'price': median_price,  # For calculation
                    'sources': urls,  # URLs for backward compatibility
                    'source_details': source_list  # Individual price-URL pairs
                }
            
            print(f"      ⚠️ No matching results found for {location} {variant}")
            return {'price': 0, 'sources': []}
            
        except Exception as e:
            print(f"      ✗ Error fetching base price: {e}")
            return {'price': 0, 'sources': []}
