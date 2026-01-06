"""
Simple Price Scraper - Direct string matching on HTML
More reliable than BeautifulSoup parsing
"""

import re
import requests
from typing import Optional, Tuple

# Import official website scrapers for all manufacturers
try:
    from official_website_scrapers import get_official_price
    OFFICIAL_SCRAPERS_AVAILABLE = True
except ImportError:
    OFFICIAL_SCRAPERS_AVAILABLE = False


def normalize_price(price_str: str) -> Optional[float]:
    """Convert price string like 'Rs.9.15 Lakh' or '₹5 78 900' to float"""
    if not price_str:
        return None

    # Remove currency symbols and extra whitespace
    price_str = price_str.replace('₹', '').replace('Rs.', '').replace('Rs', '').strip()

    # Handle Lakh format
    if 'lakh' in price_str.lower() or ' l' in price_str.lower():
        # Extract all digits, commas, dots, and spaces
        match = re.search(r'([\d,\.\s]+)', price_str)
        if match:
            try:
                # Remove all spaces and commas, then convert
                lakhs = float(match.group(1).replace(',', '').replace(' ', ''))
                return lakhs * 100000
            except:
                return None

    # Handle Crore format
    if 'crore' in price_str.lower() or ' cr' in price_str.lower():
        match = re.search(r'([\d,\.\s]+)', price_str)
        if match:
            try:
                crores = float(match.group(1).replace(',', '').replace(' ', ''))
                return crores * 10000000
            except:
                return None

    # Direct number (handles formats like "5 78 900" or "578900")
    try:
        # Remove all spaces and commas
        clean_str = price_str.replace(',', '').replace(' ', '')
        return float(clean_str)
    except:
        return None


def scrape_cardekho_simple(make: str, model: str, variant: str) -> Optional[Tuple[float, str]]:
    """
    Scrape CarDekho using simple string matching (on-road prices - needs conversion)

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

        # Strategy 1: Look for patterns like "Baleno Zeta Rs.9.15 Lakh" or "Swift Lxi ₹5 78 900"
        # Case-insensitive search, handles spaces in numbers
        patterns = [
            # Pattern 0: Official Maruti Suzuki format "Swift Lxi Price in hyderabad. ₹5 78 900.00"
            rf'{model}\s+{variant}\s+Price\s+in\s+\w+\.\s*(?:Rs\.?|₹)\s*([\d,\.\s]+)',

            # Pattern 1: "Model Variant Rs.X.XX Lakh" or "Model Variant ₹X XX XXX"
            rf'{model}\s+{variant}\s*(?:Price[^₹]*)?[,\.\s]*(?:Rs\.?|₹)\s*([\d,\.\s]+(?:\s*Lakh)?)',

            # Pattern 2: "Variant Rs.X.XX Lakh" or "Variant ₹X XX XXX"
            rf'{variant}\s*(?:Price[^₹]*)?[,\.\s]*(?:Rs\.?|₹)\s*([\d,\.\s]+(?:\s*Lakh)?)',

            # Pattern 3: "Variant(Petrol) Rs.X.XX Lakh"
            rf'{variant}\s*\([^)]*\)\s*(?:Rs\.?|₹)\s*([\d,\.\s]+\s*Lakh)',

            # Pattern 4: In table row format
            rf'>{variant}<.*?(?:Rs\.?|₹)\s*([\d,\.\s]+\s*Lakh)',

            # Pattern 5: Variant with price on same line (loose match)
            rf'{variant}[^₹<>]*?(?:Rs\.?|₹)\s*([\d,\.\s]+)(?:\s*Lakh|\s*\.00)?',
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

        # Similar patterns as CarDekho, handles space-separated numbers
        patterns = [
            rf'{model}\s+{variant}\s*(?:Price[^₹]*)?(?:Rs\.?|₹)\s*([\d,\.\s]+\s*(?:Lakh|L)?)',
            rf'{variant}\s*(?:Price[^₹]*)?(?:Rs\.?|₹)\s*([\d,\.\s]+\s*(?:Lakh|L)?)',
            rf'{variant}\s*\([^)]*\).*?(?:Rs\.?|₹)\s*([\d,\.\s]+\s*(?:Lakh|L))',
            rf'>{variant}<.*?(?:Rs\.?|₹)\s*([\d,\.\s]+\s*(?:Lakh|L))',
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

    # Try official manufacturer website first (most accurate ex-showroom prices)
    # Supports: Maruti, Hyundai, Tata, Honda, Toyota, Kia, Mahindra
    if OFFICIAL_SCRAPERS_AVAILABLE:
        print(f"   Trying official {make} website first...")
        result = get_official_price(make, model, variant)
        if result:
            print(f"   ✅ Got price from official {make} website")
            return result
        print(f"   No match on official {make} website, trying aggregators...")

    # Try CarDekho (on-road prices)
    result = scrape_cardekho_simple(make, model, variant)
    if result:
        return result

    # Try CarWale (on-road prices)
    result = scrape_carwale_simple(make, model, variant)
    if result:
        return result

    print("❌ Simple scraper failed on all sources")
    return None
