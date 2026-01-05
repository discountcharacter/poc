"""
Live Vehicle Price Fetcher

Fetches current ex-showroom and on-road prices for vehicles using:
1. Google Custom Search API to find pricing pages
2. Gemini API to extract and validate prices from search results
3. Caching to avoid repeated API calls

This ensures the OBV valuation engine has accurate base prices.
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure APIs
GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)


class VehiclePriceFetcher:
    """
    Fetches current vehicle prices using Google Search + Gemini extraction
    """

    def __init__(self, cache_duration_hours: int = 24):
        """
        Initialize price fetcher with caching

        Args:
            cache_duration_hours: How long to cache prices (default 24 hours)
        """
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.cache = {}  # In-memory cache: {search_key: (price, timestamp)}

        # Fallback prices (same as OBV engine)
        self.fallback_prices = {
            'alto': 450000,
            'kwid': 450000,
            'wagon r': 550000,
            'wagonr': 550000,
            'santro': 500000,
            'swift': 650000,
            'baleno': 750000,
            'i20': 750000,
            'polo': 750000,
            'jazz': 800000,
            'city': 1200000,
            'verna': 1200000,
            'ciaz': 1000000,
            'creta': 1500000,
            'seltos': 1600000,
            'venue': 1200000,
            'brezza': 1100000,
            'vitara brezza': 1100000,
            'ecosport': 1100000,
            'compass': 2500000,
            'harrier': 2000000,
            'fortuner': 3500000,
            'innova': 2500000,
            'crysta': 2500000,
            'ertiga': 1000000,
            'xuv': 1800000,
            'thar': 1500000,
            'nexon': 900000,
            'punch': 700000,
            'altroz': 700000,
            'safari': 1800000,
            'scorpio': 1600000,
            'grand i10': 600000,
            'elantra': 2000000,
            'tucson': 3000000,
            'kona': 2500000,
            'alcazar': 1800000,
            'sonet': 900000,
            'carens': 1200000,
            'carnival': 3500000,
            'glanza': 700000,
            'urban cruiser': 1100000,
            'hyryder': 1200000,
            'fronx': 800000,
            'jimny': 1300000,
            'ignis': 600000,
            'ciaz': 1000000,
            'dzire': 700000,
            's-presso': 450000,
            'eeco': 500000,
        }

    def get_cache_key(self, make: str, model: str, variant: str, fuel: str) -> str:
        """Generate cache key"""
        return f"{make.lower()}_{model.lower()}_{variant.lower()}_{fuel.lower()}"

    def is_cache_valid(self, timestamp: datetime) -> bool:
        """Check if cached data is still valid"""
        return datetime.now() - timestamp < self.cache_duration

    def search_google(self, make: str, model: str, variant: str, fuel: str, year: int) -> list:
        """
        Search Google for vehicle pricing pages

        Args:
            make: Vehicle manufacturer
            model: Model name
            variant: Variant/trim
            fuel: Fuel type
            year: Current year for latest model

        Returns:
            List of search result snippets
        """
        if not GOOGLE_SEARCH_API_KEY or not SEARCH_ENGINE_ID:
            return []

        # Construct search query optimized for finding Hyderabad prices
        current_year = datetime.now().year
        query = f"{make} {model} {variant} {fuel} {current_year} ex-showroom price Hyderabad on-road price"

        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": GOOGLE_SEARCH_API_KEY,
                "cx": SEARCH_ENGINE_ID,
                "q": query,
                "num": 5  # Get top 5 results
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            results = []
            if "items" in data:
                for item in data["items"]:
                    results.append({
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "link": item.get("link", "")
                    })

            return results

        except Exception as e:
            print(f"Google Search error: {e}")
            return []

    def extract_price_with_gemini(self, make: str, model: str, variant: str,
                                  fuel: str, search_results: list) -> Optional[Tuple[float, float]]:
        """
        Use Gemini to extract and validate prices from search results

        Args:
            make: Vehicle manufacturer
            model: Model name
            variant: Variant/trim
            fuel: Fuel type
            search_results: Google search results

        Returns:
            Tuple of (ex_showroom_price, on_road_price) or None
        """
        if not GOOGLE_API_KEY or not search_results:
            return None

        try:
            # Prepare context from search results
            context = "\n\n".join([
                f"Source: {r['title']}\nURL: {r['link']}\nContent: {r['snippet']}"
                for r in search_results
            ])

            # Prompt for Gemini
            prompt = f"""You are a vehicle pricing expert. Extract the CURRENT (2025-2026) ex-showroom and on-road prices for the following vehicle in Hyderabad, India.

Vehicle Details:
- Make: {make}
- Model: {model}
- Variant: {variant}
- Fuel Type: {fuel}

Search Results:
{context}

Task:
1. Find the most recent and reliable ex-showroom price and on-road price for this vehicle in Hyderabad
2. If the exact variant is not found, use the closest variant with the same fuel type
3. Prices should be in INR (Indian Rupees)
4. Ignore used car prices - only look for NEW car prices
5. On-road price should be higher than ex-showroom (includes road tax, insurance, registration)

Return ONLY a JSON object in this exact format (no other text):
{{
    "ex_showroom_price": <price_in_rupees_as_number>,
    "on_road_price": <price_in_rupees_as_number>,
    "source": "<which website/source this came from>",
    "confidence": "<high/medium/low>",
    "notes": "<any relevant notes about the price>"
}}

If you cannot find reliable pricing information, return:
{{
    "ex_showroom_price": null,
    "on_road_price": null,
    "source": "not_found",
    "confidence": "low",
    "notes": "No reliable pricing data found"
}}
"""

            # Use Gemini 2.0 Flash for extraction
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            response = model.generate_content(prompt)

            # Parse JSON response
            response_text = response.text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()

            price_data = json.loads(response_text)

            # Validate the response
            ex_showroom = price_data.get("ex_showroom_price")
            on_road = price_data.get("on_road_price")
            confidence = price_data.get("confidence", "low")

            if ex_showroom and on_road and confidence in ["high", "medium"]:
                # Sanity checks
                if (300000 <= ex_showroom <= 15000000 and  # Between 3L and 1.5Cr
                    on_road > ex_showroom and  # On-road should be higher
                    on_road <= ex_showroom * 1.5):  # But not more than 150%

                    print(f"✅ Gemini extracted price: Ex-showroom: ₹{ex_showroom:,.0f}, "
                          f"On-road: ₹{on_road:,.0f} (Source: {price_data.get('source')})")

                    return (float(ex_showroom), float(on_road))

            return None

        except Exception as e:
            print(f"Gemini extraction error: {e}")
            return None

    def get_fallback_price(self, make: str, model: str, year: int) -> float:
        """
        Get fallback price from lookup table with inflation adjustment

        Args:
            make: Vehicle manufacturer
            model: Model name
            year: Manufacturing year

        Returns:
            Estimated ex-showroom price
        """
        model_lower = model.lower()
        base_price = 800000  # Default fallback

        # Try to find matching model
        for key, price in self.fallback_prices.items():
            if key in model_lower:
                base_price = price
                break

        # Adjust for inflation (6% per year from current year)
        current_year = datetime.now().year
        years_diff = current_year - year

        if years_diff > 0:
            inflation_factor = 1.06 ** years_diff
            base_price = base_price * inflation_factor

        return base_price

    def get_current_price(self, make: str, model: str, variant: str = "",
                         fuel: str = "Petrol", year: int = None) -> Dict[str, float]:
        """
        Get current vehicle price with caching

        Args:
            make: Vehicle manufacturer
            model: Model name
            variant: Variant/trim (optional)
            fuel: Fuel type
            year: Manufacturing year (for fallback inflation adjustment)

        Returns:
            Dictionary with ex_showroom_price, on_road_price, and source
        """
        if year is None:
            year = datetime.now().year

        # Check cache first
        cache_key = self.get_cache_key(make, model, variant, fuel)
        if cache_key in self.cache:
            price_data, timestamp = self.cache[cache_key]
            if self.is_cache_valid(timestamp):
                print(f"📦 Using cached price for {make} {model}")
                return price_data

        # Try to fetch live price
        print(f"🔍 Fetching live price for {make} {model} {variant} {fuel}...")

        search_results = self.search_google(make, model, variant, fuel, year)

        if search_results:
            price_tuple = self.extract_price_with_gemini(make, model, variant, fuel, search_results)

            if price_tuple:
                ex_showroom, on_road = price_tuple
                price_data = {
                    "ex_showroom_price": ex_showroom,
                    "on_road_price": on_road,
                    "source": "live_search"
                }

                # Cache the result
                self.cache[cache_key] = (price_data, datetime.now())
                return price_data

        # Fallback to lookup table
        print(f"⚠️ Live price not found, using fallback estimate for {make} {model}")
        fallback_price = self.get_fallback_price(make, model, year)

        price_data = {
            "ex_showroom_price": fallback_price,
            "on_road_price": fallback_price * 1.15,  # Rough estimate: +15% for taxes/registration
            "source": "fallback_estimate"
        }

        # Cache fallback (but with shorter duration in real implementation)
        self.cache[cache_key] = (price_data, datetime.now())
        return price_data


# Global instance for easy import
price_fetcher = VehiclePriceFetcher()


# Example usage
if __name__ == "__main__":
    fetcher = VehiclePriceFetcher()

    # Test cases
    test_vehicles = [
        ("Hyundai", "Creta", "SX", "Diesel", 2019),
        ("Maruti", "Swift", "VXi", "Petrol", 2020),
        ("Honda", "City", "VX", "Petrol", 2021),
    ]

    for make, model, variant, fuel, year in test_vehicles:
        print(f"\n{'='*80}")
        print(f"Testing: {year} {make} {model} {variant} {fuel}")
        print('='*80)

        price_data = fetcher.get_current_price(make, model, variant, fuel, year)

        print(f"Ex-Showroom Price: ₹{price_data['ex_showroom_price']:,.0f}")
        print(f"On-Road Price (Hyderabad): ₹{price_data['on_road_price']:,.0f}")
        print(f"Source: {price_data['source']}")
