"""
Simple Price Scraper - Direct string matching on HTML
More reliable than BeautifulSoup parsing
"""

import re
import requests
from typing import Optional, Tuple


def normalize_price(price_str: str) -> Optional[float]:
    """Convert price string like 'Rs.9.15 Lakh' to float"""
    if not price_str:
        return None

    # Remove currency symbols
    price_str = price_str.replace('₹', '').replace('Rs.', '').replace('Rs', '').strip()

    # Handle Lakh
    if 'lakh' in price_str.lower() or ' l' in price_str.lower():
        match = re.search(r'([\d,\.]+)', price_str)
        if match:
            try:
                lakhs = float(match.group(1).replace(',', ''))
                return lakhs * 100000
            except:
                return None

    # Handle Crore
    if 'crore' in price_str.lower() or ' cr' in price_str.lower():
        match = re.search(r'([\d,\.]+)', price_str)
        if match:
            try:
                crores = float(match.group(1).replace(',', ''))
                return crores * 10000000
            except:
                return None

    # Direct number
    try:
        return float(price_str.replace(',', ''))
    except:
        return None


def scrape_cardekho_simple(make: str, model: str, variant: str) -> Optional[Tuple[float, str]]:
    """
    Scrape CarDekho using simple string matching

    Returns:
        Tuple of (ex_showroom_price, source_url) or None
    """
    try:
        # Construct URL
        make_slug = make.lower().replace(' ', '-').replace('maruti suzuki', 'maruti')
        model_slug = model.lower().replace(' ', '-')

        url = f"https://www.cardekho.com/{make_slug}/{model_slug}/price-in-hyderabad"

        print(f"🔍 Simple scraper: Fetching {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        html = response.text

        # Normalize variant for matching
        target_variant = variant.strip().upper()

        print(f"   Looking for variant: {target_variant}")

        # Strategy 1: Look for patterns like "Baleno Zeta Rs.9.15 Lakh"
        # Case-insensitive search
        patterns = [
            # Pattern 1: "Model Variant Rs.X.XX Lakh"
            rf'{model}\s+{variant}\s*(?:,)?\s*Rs\.?\s*([\d,\.]+\s*Lakh)',

            # Pattern 2: "Variant Rs.X.XX Lakh"
            rf'{variant}\s*(?:,)?\s*Rs\.?\s*([\d,\.]+\s*Lakh)',

            # Pattern 3: "Variant(Petrol) Rs.X.XX Lakh"
            rf'{variant}\s*\([^)]*\)\s*Rs\.?\s*([\d,\.]+\s*Lakh)',

            # Pattern 4: In table row format
            rf'>{variant}<.*?Rs\.?\s*([\d,\.]+\s*Lakh)',

            # Pattern 5: Variant with price on same line
            rf'{variant}.*?Rs\.?\s*([\d,\.]+)\s*Lakh',
        ]

        found_prices = []

        for pattern in patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                price_str = match.group(1)
                print(f"   Pattern matched: '{match.group(0)[:100]}...'")
                print(f"   Extracted price string: {price_str}")

                price = normalize_price(price_str + " Lakh" if "Lakh" not in price_str else price_str)

                if price and 300000 <= price <= 15000000:
                    found_prices.append(price)
                    print(f"   Valid price found: ₹{price:,.0f}")

        if found_prices:
            # Use median price if multiple found
            median_price = sorted(found_prices)[len(found_prices) // 2]

            # Convert on-road to ex-showroom (rough estimate: -17%)
            ex_showroom = median_price / 1.17

            print(f"   ✅ Final price: ₹{median_price:,.0f} (on-road) → ₹{ex_showroom:,.0f} (ex-showroom)")

            return (ex_showroom, url)

        print(f"   ❌ No price found for {variant}")
        return None

    except Exception as e:
        print(f"   ❌ CarDekho scraper error: {e}")
        return None


def scrape_carwale_simple(make: str, model: str, variant: str) -> Optional[Tuple[float, str]]:
    """
    Scrape CarWale using simple string matching

    Returns:
        Tuple of (ex_showroom_price, source_url) or None
    """
    try:
        # Construct URL
        make_slug = make.lower().replace(' ', '-')
        model_slug = model.lower().replace(' ', '-')

        url = f"https://www.carwale.com/{make_slug}-cars/{model_slug}/price-in-hyderabad/"

        print(f"🔍 Simple scraper: Fetching {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        html = response.text

        target_variant = variant.strip().upper()
        print(f"   Looking for variant: {target_variant}")

        # Similar patterns as CarDekho
        patterns = [
            rf'{model}\s+{variant}\s*(?:Rs\.?|₹)\s*([\d,\.]+\s*(?:Lakh|L))',
            rf'{variant}\s*(?:Rs\.?|₹)\s*([\d,\.]+\s*(?:Lakh|L))',
            rf'{variant}\s*\([^)]*\).*?(?:Rs\.?|₹)\s*([\d,\.]+\s*(?:Lakh|L))',
            rf'>{variant}<.*?(?:Rs\.?|₹)\s*([\d,\.]+\s*(?:Lakh|L))',
        ]

        found_prices = []

        for pattern in patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                price_str = match.group(1)
                print(f"   Extracted: {price_str}")

                price = normalize_price(price_str)

                if price and 300000 <= price <= 15000000:
                    found_prices.append(price)
                    print(f"   Valid price: ₹{price:,.0f}")

        if found_prices:
            median_price = sorted(found_prices)[len(found_prices) // 2]
            ex_showroom = median_price / 1.17

            print(f"   ✅ Final: ₹{ex_showroom:,.0f} (ex-showroom)")

            return (ex_showroom, url)

        print(f"   ❌ No price found")
        return None

    except Exception as e:
        print(f"   ❌ CarWale scraper error: {e}")
        return None


def get_simple_price(make: str, model: str, variant: str, fuel: str = "Petrol") -> Optional[Tuple[float, str]]:
    """
    Get variant price using simple string matching

    Returns:
        Tuple of (ex_showroom_price, source_url) or None
    """
    print(f"\n🎯 Simple scraper: {make} {model} {variant} ({fuel})")

    # Try CarDekho first (usually more reliable)
    result = scrape_cardekho_simple(make, model, variant)
    if result:
        return result

    # Try CarWale
    result = scrape_carwale_simple(make, model, variant)
    if result:
        return result

    print("❌ Simple scraper failed on all sources")
    return None
