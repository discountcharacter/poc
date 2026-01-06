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


# Inline regex price extraction functions (no external module dependency)
def normalize_price_inline(price_str: str) -> Optional[float]:
    """Convert various price formats to float"""
    if not price_str:
        return None

    import re
    price_str = price_str.replace('₹', '').replace('Rs.', '').replace('Rs', '').strip()

    if 'lakh' in price_str.lower() or ' l' in price_str.lower():
        number_match = re.search(r'([\d,\.]+)', price_str)
        if number_match:
            try:
                lakhs = float(number_match.group(1).replace(',', ''))
                return lakhs * 100000
            except:
                return None
    elif 'crore' in price_str.lower() or ' cr' in price_str.lower():
        number_match = re.search(r'([\d,\.]+)', price_str)
        if number_match:
            try:
                crores = float(number_match.group(1).replace(',', ''))
                return crores * 10000000
            except:
                return None

    price_str = price_str.replace(',', '').strip()
    number_match = re.search(r'(\d+)', price_str)
    if number_match:
        try:
            return float(number_match.group(1))
        except:
            return None
    return None


def extract_price_inline(search_results: list, variant: str) -> Optional[Tuple[float, str]]:
    """Extract price for specific variant using regex patterns"""
    import re

    target_variant_normalized = variant.strip().upper()
    all_matches = []
    all_variants_found = []  # Track all variants found (for debugging)

    patterns = [
        r'([A-Za-z]+[A-Za-z0-9]*)\s*(?:\([^)]+\))?\s*[·•-]?\s*(?:Rs\.?|₹)\s*([\d,\.]+(?:\s*(?:Lakh|L|Crore|Cr))?)',
        r'([A-Za-z]+[A-Za-z0-9]*)\s*:\s*(?:Rs\.?|₹)\s*([\d,\.]+(?:\s*(?:Lakh|L|Crore|Cr))?)',
        r'([A-Za-z]+[A-Za-z0-9]*)\s*\|\s*Price.*?(?:Rs\.?|₹)\s*([\d,\.]+(?:\s*(?:Lakh|L|Crore|Cr))?)',
        r'([A-Za-z]+[A-Za-z0-9]*)\s+(?:Rs\.?|₹)\s*([\d,\.]+(?:\s*(?:Lakh|L|Crore|Cr))?)',
    ]

    print(f"🔍 DEBUG: Looking for variant '{target_variant_normalized}'")

    for idx, result in enumerate(search_results):
        text = f"{result.get('title', '')} {result.get('snippet', '')}"
        source_url = result.get('link', '')

        print(f"   Result {idx+1}: {text[:150]}...")

        for pattern_idx, pattern in enumerate(patterns):
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                variant_found = match.group(1).strip().upper()
                price_str = match.group(2).strip()

                # Track all variants found
                all_variants_found.append(variant_found)

                print(f"      Pattern {pattern_idx+1} found: {variant_found} = {price_str}")

                if variant_found == target_variant_normalized:
                    price = normalize_price_inline(price_str)
                    if price and 300000 <= price <= 15000000:
                        print(f"      ✅ MATCH! {variant_found} = ₹{price:,.0f}")
                        all_matches.append({
                            'price': price,
                            'source': source_url,
                            'variant': variant_found
                        })
                    else:
                        print(f"      ❌ Price out of range: ₹{price}")
                elif variant_found:
                    print(f"      ⏭️  Skip: {variant_found} != {target_variant_normalized}")

    # Print summary
    print(f"📊 SUMMARY: Found {len(all_matches)} matches for '{target_variant_normalized}'")
    print(f"   All variants detected: {set(all_variants_found)}")

    if all_matches:
        # Return most common price
        price_counts = {}
        for m in all_matches:
            p_rounded = round(m['price'], -3)
            price_counts[p_rounded] = price_counts.get(p_rounded, 0) + 1

        most_common = max(price_counts, key=price_counts.get)
        print(f"   Most common price: ₹{most_common:,.0f} (appeared {price_counts[most_common]} times)")

        for m in all_matches:
            if round(m['price'], -3) == most_common:
                return (m['price'], m['source'])

    print(f"❌ No valid matches found for variant '{target_variant_normalized}'")
    return None


# Import CarWale scraper (most reliable for variant-specific prices)
try:
    from carwale_scraper import get_variant_price
    CARWALE_SCRAPER_AVAILABLE = True
except ImportError as e:
    CARWALE_SCRAPER_AVAILABLE = False
    print(f"⚠️ CarWale scraper not available: {e}")

# Import direct scraper
try:
    from direct_price_scraper import get_direct_price
    DIRECT_SCRAPER_AVAILABLE = True
except ImportError:
    DIRECT_SCRAPER_AVAILABLE = False

# Import robust regex extractor with path handling
try:
    import sys
    import os
    # Ensure src directory is in path
    src_dir = os.path.dirname(os.path.abspath(__file__))
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    from robust_price_extractor import extract_price_for_variant
    REGEX_EXTRACTOR_AVAILABLE = True
    print("✅ Robust regex extractor loaded successfully")
except ImportError as e:
    REGEX_EXTRACTOR_AVAILABLE = False
    print(f"❌ Regex extractor import failed: {e}")
except Exception as e:
    REGEX_EXTRACTOR_AVAILABLE = False
    print(f"❌ Regex extractor error: {e}")


class VehiclePriceFetcher:
    """
    Fetches current vehicle prices using Google Search + Gemini extraction
    """

    # Cache version - increment this to invalidate all old caches
    CACHE_VERSION = "v6_carwale_scraper"  # Added CarWale direct scraping (most reliable)

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
        """Generate cache key with version"""
        return f"{self.CACHE_VERSION}_{make.lower()}_{model.lower()}_{variant.lower()}_{fuel.lower()}"

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

            # Normalize variant for case-insensitive matching
            variant_normalized = variant.strip().upper()

            # Improved prompt with specific examples and stricter instructions
            prompt = f"""You are a vehicle pricing expert. Extract the CURRENT (2025-2026) ex-showroom price for the EXACT variant specified.

Vehicle Details:
- Make: {make}
- Model: {model}
- Variant: {variant} (also matches: {variant.upper()}, {variant.lower()}, {variant.title()})
- Fuel Type: {fuel}
- Location: Hyderabad

Search Results:
{context}

🚨 CRITICAL VARIANT MATCHING RULES:
1. Variant "{variant}" can appear as: "{variant.upper()}", "{variant.lower()}", "{variant.title()}", "VXi", "VXI", "vxi"
2. CASE-INSENSITIVE matching: "VXI" = "VXi" = "vxi"
3. If searching for "VXI" or "VXi":
   - ✅ CORRECT: Extract price for "VXi (Petrol) Rs.6,58,900" → 658900
   - ❌ WRONG: Do NOT extract "LXi" price (₹5.79 Lakh) - this is BASE variant
   - ❌ WRONG: Do NOT extract "ZXi" price - this is TOP variant
4. Look for ex-showroom price in these formats:
   - "₹6.59 Lakh" = 659000
   - "Rs.6,58,900" = 658900
   - "Price: ₹6.59 L" = 659000
5. If on-road price not stated, calculate: on_road = ex_showroom × 1.20 (Hyderabad ~20% taxes)
6. Prefer CarWale, CarDekho, Spinny, ZigWheels sources
7. If table with multiple variants, extract ONLY the row matching "{variant}" (case-insensitive)

VARIANT HIERARCHY (for reference):
- LXi/LXI = Base variant (cheapest)
- VXi/VXI = Mid variant ← If this is requested, ONLY extract this
- ZXi/ZXI = Top variant (most expensive)

EXAMPLES OF CORRECT EXTRACTION:
Input query: variant="VXI"
Result snippet: "LXi: ₹5.79 Lakh | VXi: ₹6.59 Lakh | ZXi: ₹7.50 Lakh"
Output: {{"ex_showroom_price": 659000, "variant_matched": "VXi"}}
Reason: VXI matches VXi (case-insensitive), ignore LXi and ZXi

Input query: variant="VXi"
Result snippet: "VXi (Petrol) · Rs.6,58,900"
Output: {{"ex_showroom_price": 658900, "variant_matched": "VXi"}}

Input query: variant="VXI"
Result snippet: "Swift LXi Rs.5,78,900 | Swift VXi Rs.6,58,900"
Output: {{"ex_showroom_price": 658900, "variant_matched": "VXi"}}
Reason: VXI = VXi, ignore LXi even though it's listed first

Return ONLY valid JSON (no other text):
{{
    "ex_showroom_price": <number>,
    "on_road_price": <number>,
    "variant_matched": "{variant}",
    "source": "CarWale/CarDekho/etc",
    "confidence": "high"
}}

If variant "{variant}" not found, return:
{{"ex_showroom_price": null, "confidence": "low", "notes": "Variant {variant} not found in results"}}
"""

            # Use Gemini 2.0 Flash for extraction
            model_ai = genai.GenerativeModel('gemini-2.0-flash-exp')
            response = model_ai.generate_content(prompt)

            # Parse JSON response
            response_text = response.text.strip()
            print(f"🤖 Gemini raw response: {response_text[:200]}...")

            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()

            price_data = json.loads(response_text)
            print(f"📊 Parsed price data: {price_data}")

            # Validate the response
            ex_showroom = price_data.get("ex_showroom_price")
            on_road = price_data.get("on_road_price")
            confidence = price_data.get("confidence", "low")

            # If on-road not provided, calculate it
            if ex_showroom and not on_road:
                on_road = ex_showroom * 1.20  # Hyderabad taxes ~20%
                print(f"💡 Calculated on-road price: ₹{on_road:,.0f}")

            if ex_showroom and confidence in ["high", "medium"]:
                # Sanity checks
                if 300000 <= ex_showroom <= 15000000:
                    print(f"✅ Gemini extracted price: Ex-showroom: ₹{ex_showroom:,.0f}, "
                          f"On-road: ₹{on_road:,.0f} (Source: {price_data.get('source', 'unknown')})")

                    return (float(ex_showroom), float(on_road))
                else:
                    print(f"❌ Price validation failed: ₹{ex_showroom:,.0f} outside valid range")

            print(f"❌ Extraction failed: ex_showroom={ex_showroom}, confidence={confidence}")
            return None

        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error: {e}")
            print(f"Response was: {response_text[:500]}")
            return None
        except Exception as e:
            print(f"❌ Gemini extraction error: {e}")
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

        # Method 0: Try CarWale/CarDekho direct scraping (MOST RELIABLE for variant prices)
        if CARWALE_SCRAPER_AVAILABLE and variant:
            try:
                print(f"🎯 Method 0: Trying CarWale/CarDekho scraping...")
                scraper_result = get_variant_price(make, model, variant, fuel)

                if scraper_result:
                    ex_showroom, source_url = scraper_result
                    on_road = ex_showroom * 1.20  # Calculate on-road (~20% for Hyderabad)

                    print(f"✅ SCRAPER SUCCESS: ₹{ex_showroom:,.0f} from {source_url}")

                    price_data = {
                        "ex_showroom_price": ex_showroom,
                        "on_road_price": on_road,
                        "source": "carwale_scraper"
                    }

                    # Cache the result
                    self.cache[cache_key] = (price_data, datetime.now())
                    return price_data
                else:
                    print(f"⚠️ CarWale scraper returned no match, trying other methods...")

            except Exception as e:
                print(f"❌ CarWale scraper error: {e}")
                import traceback
                traceback.print_exc()

        # Method 1: Try Google Custom Search + Regex extraction
        search_results = self.search_google(make, model, variant, fuel, year)

        if search_results:
            # Try inline regex extraction first (most reliable)
            print(f"🔍 Trying inline regex extraction for variant '{variant}'...")
            print(f"   Search results count: {len(search_results)}")
            try:
                regex_result = extract_price_inline(search_results, variant)

                if regex_result:
                    ex_showroom, source_url = regex_result
                    on_road = ex_showroom * 1.20  # Calculate on-road

                    print(f"✅ Regex SUCCESS: ₹{ex_showroom:,.0f} for variant '{variant}'")
                    print(f"   Source: {source_url[:80] if source_url else 'unknown'}...")

                    price_data = {
                        "ex_showroom_price": ex_showroom,
                        "on_road_price": on_road,
                        "source": "regex_extraction"
                    }

                    # Cache the result
                    self.cache[cache_key] = (price_data, datetime.now())
                    return price_data
                else:
                    print(f"⚠️ Inline regex extraction returned NO MATCH for variant '{variant}'")
                    print("   Will fallback to Gemini extraction...")

            except Exception as e:
                print(f"❌ Inline regex extraction ERROR: {e}")
                import traceback
                traceback.print_exc()

        # Method 1b: Fallback to Gemini extraction if regex failed
        if search_results:
            print(f"🔍 Regex failed, trying Gemini extraction...")
            price_tuple = self.extract_price_with_gemini(make, model, variant, fuel, search_results)

            if price_tuple:
                ex_showroom, on_road = price_tuple
                price_data = {
                    "ex_showroom_price": ex_showroom,
                    "on_road_price": on_road,
                    "source": "gemini_extraction"
                }

                # Cache the result
                self.cache[cache_key] = (price_data, datetime.now())
                return price_data

        # Method 2: Try direct scraping if Google Search failed
        if DIRECT_SCRAPER_AVAILABLE:
            print(f"🔍 Google Search returned no results. Trying direct scraping...")
            try:
                direct_result = get_direct_price(make, model, variant, fuel)

                if direct_result and direct_result.get("ex_showroom_price"):
                    print(f"✅ Direct scraper found price!")
                    # Cache and return
                    self.cache[cache_key] = (direct_result, datetime.now())
                    return direct_result

            except Exception as e:
                print(f"Direct scraper error: {e}")

        # Method 3: Fallback to lookup table
        print(f"⚠️ All live price methods failed, using fallback estimate for {make} {model}")
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
