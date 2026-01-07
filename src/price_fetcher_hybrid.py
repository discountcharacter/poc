"""
Hybrid Price Fetcher - Google Search + Direct Scraping

Uses Google Custom Search API to find sources, then scrapes HTML directly
for accurate, variant-specific ex-showroom prices.

This is MORE RELIABLE than Gemini's JSON output which has parsing issues.
"""

import os
import json
import re
import requests
from typing import Optional, Dict, Tuple
from dotenv import load_dotenv

load_dotenv()


def normalize_price(price_str: str) -> Optional[float]:
    """
    Convert various price formats to float

    Handles:
    - "5.79 Lakh" -> 579000
    - "₹5,78,900" -> 578900
    - "6.5L" -> 650000
    """
    if not price_str:
        return None

    # Clean up
    price_str = price_str.replace('₹', '').replace('Rs.', '').replace('Rs', '').strip()

    # Lakh format
    if 'lakh' in price_str.lower() or ' l' in price_str.lower():
        match = re.search(r'([\d,\.\s]+)', price_str)
        if match:
            try:
                clean = match.group(1).replace(',', '').replace(' ', '')
                lakhs = float(clean)
                return lakhs * 100000
            except:
                return None

    # Crore format
    elif 'crore' in price_str.lower() or ' cr' in price_str.lower():
        match = re.search(r'([\d,\.]+)', price_str)
        if match:
            try:
                crores = float(match.group(1).replace(',', ''))
                return crores * 10000000
            except:
                return None

    # Plain number with commas: "5,78,900" or spaces "5 78 900"
    try:
        clean = price_str.replace(',', '').replace(' ', '').strip()
        if clean.replace('.', '').isdigit():
            return float(clean)
    except:
        pass

    return None


def search_google_custom(make: str, model: str, variant: str, fuel: str, city: str = "Hyderabad") -> list:
    """
    Use Google Custom Search API to find relevant pricing pages

    Returns list of search results with URLs
    """
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    search_engine_id = os.getenv("SEARCH_ENGINE_ID")

    if not api_key or not search_engine_id:
        print("   ⚠️ Google Custom Search API not configured")
        return []

    # Construct search query
    query = f"{make} {model} {variant} {fuel} ex-showroom price {city}"

    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': search_engine_id,
            'q': query,
            'num': 5  # Get top 5 results
        }

        print(f"🔍 Google Search: {query}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        results = []

        if 'items' in data:
            for item in data['items']:
                results.append({
                    'title': item.get('title', ''),
                    'link': item.get('link', ''),
                    'snippet': item.get('snippet', '')
                })
                print(f"   📄 Found: {item.get('title', '')[:60]}...")

        return results

    except Exception as e:
        print(f"   ❌ Search error: {e}")
        return []


def scrape_price_from_html(html: str, variant: str, model: str) -> Optional[float]:
    """
    Extract price from HTML using robust regex patterns

    Returns ex-showroom price (the minimum price found, which is typically ex-showroom)
    """
    target_variant = variant.strip().upper()

    # Pattern 1: Ex-Showroom Price labeled in table
    ex_showroom_pattern = r'Ex-Showroom\s+Price.*?(?:Rs\.?|₹)\s*([\d,\.\s]+)'
    ex_matches = re.finditer(ex_showroom_pattern, html, re.IGNORECASE | re.DOTALL)

    for match in ex_matches:
        if len(match.group(0)) < 200:  # Within reasonable distance
            price_str = match.group(1)
            price = normalize_price(price_str)
            if price and 300000 <= price <= 15000000:
                print(f"   ✅ Found ex-showroom label: ₹{price:,.0f}")
                return price

    # Pattern 2: Variant-specific price extraction
    patterns = [
        # Direct variant + price
        rf'\b{variant}\b[,:\s\-|]*(?:Rs\.?|₹)\s*([\d,\.\s]+\s*(?:Lakh|L)?)',
        # Model + variant + price
        rf'\b{model}\s+{variant}\b[,:\s\-|]*(?:Rs\.?|₹)\s*([\d,\.\s]+\s*(?:Lakh|L)?)',
        # Variant in table cell
        rf'>{variant}\s*<[^>]*>.*?(?:Rs\.?|₹)\s*([\d,\.\s]+)',
    ]

    found_prices = []

    # Exclude generic short variants from validation
    other_variants = ['LXI', 'VXI', 'ZXI', 'LX', 'VX', 'ZX', 'SIGMA', 'DELTA', 'ZETA', 'ALPHA',
                     'AMBIENTE', 'TREND', 'TITANIUM', 'SX', 'S+', 'SX+']
    other_variants = [v for v in other_variants if v.upper() != target_variant]

    for pattern in patterns:
        matches = re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)
        for match in matches:
            matched_text = match.group(0)
            price_str = match.group(1)

            # Validate: reject if contains other variant names
            contains_other = False
            for other_var in other_variants:
                if re.search(rf'\b{other_var}\b', matched_text, re.IGNORECASE):
                    contains_other = True
                    break

            if contains_other:
                continue

            price = normalize_price(price_str)
            if price and 300000 <= price <= 15000000:
                found_prices.append(price)

    if found_prices:
        # Return minimum price (ex-showroom < on-road)
        min_price = min(found_prices)
        print(f"   ✅ Extracted from HTML: ₹{min_price:,.0f}")
        return min_price

    return None


def fetch_price_hybrid(make: str, model: str, variant: str, fuel: str,
                       year: int, city: str = "Hyderabad") -> Optional[Dict]:
    """
    HYBRID APPROACH: Google Search + Direct HTML Scraping

    1. Use Google Custom Search to find relevant pages
    2. Fetch HTML from top results
    3. Extract price using proven regex patterns

    This is more reliable than Gemini's inconsistent JSON output.
    """
    print(f"🔍 Hybrid Search: {make} {model} {variant} {fuel}")

    # Step 1: Search Google for relevant pages
    search_results = search_google_custom(make, model, variant, fuel, city)

    if not search_results:
        print("   ⚠️ No search results found")
        return None

    # Step 2: Try each result URL
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    for result in search_results:
        url = result['link']

        # Prioritize known good sources
        if 'cardekho.com' not in url and 'carwale.com' not in url and 'zigwheels.com' not in url:
            continue

        try:
            print(f"   📥 Fetching: {url[:60]}...")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            html = response.text

            # Step 3: Extract price from HTML
            price = scrape_price_from_html(html, variant, model)

            if price:
                return {
                    'ex_showroom_price': price,
                    'source': 'hybrid_search_scrape',
                    'source_url': url
                }

        except Exception as e:
            print(f"   ⚠️ Scrape error: {e}")
            continue

    print("   ❌ No valid price found in search results")
    return None


class PriceFetcherHybrid:
    """
    Hybrid price fetcher: Google Search + HTML Scraping

    More reliable than Gemini API's inconsistent JSON output
    """

    def __init__(self):
        """Initialize hybrid price fetcher"""
        pass

    def get_current_price(self, make: str, model: str, variant: str = "",
                         fuel: str = "Petrol", year: int = None,
                         month: int = 3, transmission: str = "Manual") -> Dict:
        """
        Get current vehicle price using hybrid approach

        Args:
            make: Vehicle manufacturer
            model: Model name
            variant: Variant/trim
            fuel: Fuel type
            year: Manufacturing year
            month: Manufacturing month
            transmission: Transmission type

        Returns:
            Dictionary with ex_showroom_price and source

        Raises:
            ValueError: If price cannot be fetched
        """
        from datetime import datetime

        if year is None:
            year = datetime.now().year

        # Use hybrid search + scrape
        result = fetch_price_hybrid(
            make=make,
            model=model,
            variant=variant,
            fuel=fuel,
            year=year,
            city="Hyderabad"
        )

        if result:
            return result

        # If hybrid fails, raise error
        raise ValueError(
            f"Failed to fetch price for {make} {model} {variant}. "
            "No valid price found in search results."
        )


# Create singleton instance
price_fetcher = PriceFetcherHybrid()


# Test function
def test_price_fetcher():
    """Test the hybrid price fetcher"""
    print("="*60)
    print("Testing Hybrid Price Fetcher (Google Search + Scraping)")
    print("="*60)

    print("\n[Test 1] Maruti Suzuki Swift VXI Petrol")
    result = price_fetcher.get_current_price(
        make="Maruti Suzuki",
        model="Swift",
        variant="VXI",
        fuel="Petrol",
        year=2020
    )

    if result and result.get('ex_showroom_price'):
        price = result['ex_showroom_price']
        print(f"✅ Price: ₹{price:,.0f} ({price/100000:.2f} Lakhs)")
        print(f"   Source: {result['source']}")
        print(f"   URL: {result.get('source_url', 'N/A')[:60]}...")
    else:
        print("❌ No price found")

    print("\n" + "="*60)


if __name__ == "__main__":
    test_price_fetcher()
