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

        # Normalize variant for matching (preserve original case for display)
        target_variant = variant.strip().upper()

        # Create flexible variant pattern that matches both "VXI" and "VXi" style
        # This handles Maruti's mixed-case naming (LXi, VXi, ZXi, etc.)
        variant_pattern = variant.strip().replace('I', '[Ii]').replace('i', '[Ii]')

        print(f"   Looking for variant: {target_variant} (pattern: {variant_pattern})")

        # Strategy 1: Look for patterns like "Baleno Zeta Rs.9.15 Lakh" or "Swift VXi ₹5 78 900"
        # FLEXIBLE matching - handles both "VXI" and "VXi" style variants
        patterns = [
            # Pattern 1: STRICT - Variant directly followed by price (max 20 chars between)
            # Matches: "VXI Rs.6.59 Lakh" or "VXi, Rs.6.59 Lakh" or "VXi: Rs.6.59 Lakh"
            rf'\b{variant_pattern}\b[,:\s\-|]*(?:Rs\.?|₹)\s*([\d,\.\s]+\s*(?:Lakh|L)?)',

            # Pattern 2: Model + Variant + Price on same line (max 30 chars)
            # Matches: "Swift VXi Rs.6.59 Lakh"
            rf'\b{model}\s+{variant_pattern}\b[,:\s\-|]*(?:Rs\.?|₹)\s*([\d,\.\s]+\s*(?:Lakh|L)?)',

            # Pattern 3: Variant in parentheses with fuel type
            # Matches: "VXi(Petrol) Rs.6.59 Lakh"
            rf'\b{variant_pattern}\s*\([^)]+\)[,:\s\-|]*(?:Rs\.?|₹)\s*([\d,\.\s]+\s*(?:Lakh|L)?)',

            # Pattern 4: Table cell format (variant in one tag, price nearby)
            # Matches: "<td>VXi</td><td>Rs.6.59 Lakh</td>"
            rf'>{variant_pattern}\s*<[^>]*>.*?(?:Rs\.?|₹)\s*([\d,\.\s]+\s*(?:Lakh|L)?)',
        ]

        found_prices = []
        found_variants = []  # Track which variants we found (for debugging)

        # Common variant names to check for cross-contamination
        # Exclude very short variants (E, S, EX) - too generic, cause false positives in HTML
        other_variants = ['LXI', 'VXI', 'ZXI', 'LX', 'VX', 'ZX', 'SIGMA', 'DELTA', 'ZETA', 'ALPHA',
                         'AMBIENTE', 'TREND', 'TITANIUM', 'SX', 'S+', 'SX+']
        other_variants = [v for v in other_variants if v.upper() != target_variant]

        for pattern in patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                matched_text = match.group(0)
                price_str = match.group(1)

                print(f"   Pattern matched: '{matched_text[:100]}'")
                print(f"   Extracted price string: {price_str}")

                # VALIDATION: Check if matched text contains OTHER variant names
                # This prevents matching "LXI ... VXI ... Rs.7.50" where price is for ZXI
                contains_other_variant = False
                for other_var in other_variants:
                    if re.search(rf'\b{other_var}\b', matched_text, re.IGNORECASE):
                        print(f"   ⚠️ REJECTED: Contains other variant '{other_var}' - likely wrong price")
                        contains_other_variant = True
                        break

                if contains_other_variant:
                    continue  # Skip this match

                price = normalize_price(price_str + " Lakh" if "Lakh" not in price_str else price_str)

                if price and 300000 <= price <= 15000000:
                    found_prices.append(price)
                    found_variants.append(target_variant)
                    print(f"   ✅ Valid price found: ₹{price:,.0f}")

        if found_prices:
            # Take MINIMUM price - most likely to be ex-showroom (since ex-showroom < on-road)
            # Aggregator sites often mix both price types, minimum filters correctly
            min_price = min(found_prices)

            print(f"   ✅ Final price: ₹{min_price:,.0f} (using as ex-showroom)")

            return (min_price, url)

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

        # Normalize variant for matching
        target_variant = variant.strip().upper()

        # Create flexible variant pattern (handles "VXI" and "VXi" style)
        variant_pattern = variant.strip().replace('I', '[Ii]').replace('i', '[Ii]')

        print(f"   Looking for variant: {target_variant} (pattern: {variant_pattern})")

        # Generic variant patterns with flexible case matching
        patterns = [
            rf'\b{variant_pattern}\b[,:\s\-|]*(?:Rs\.?|₹)\s*([\d,\.\s]+\s*(?:Lakh|L)?)',
            rf'\b{model}\s+{variant_pattern}\b[,:\s\-|]*(?:Rs\.?|₹)\s*([\d,\.\s]+\s*(?:Lakh|L)?)',
            rf'\b{variant_pattern}\s*\([^)]+\)[,:\s\-|]*(?:Rs\.?|₹)\s*([\d,\.\s]+\s*(?:Lakh|L)?)',
            rf'>{variant_pattern}\s*<[^>]*>.*?(?:Rs\.?|₹)\s*([\d,\.\s]+\s*(?:Lakh|L)?)',
        ]

        found_prices = []

        # Common variant names to check for cross-contamination
        # Exclude very short variants (E, S, EX) - too generic, cause false positives in HTML
        other_variants = ['LXI', 'VXI', 'ZXI', 'LX', 'VX', 'ZX', 'SIGMA', 'DELTA', 'ZETA', 'ALPHA',
                         'AMBIENTE', 'TREND', 'TITANIUM', 'SX', 'S+', 'SX+']
        other_variants = [v for v in other_variants if v.upper() != target_variant]

        for pattern in patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                matched_text = match.group(0)
                price_str = match.group(1)

                print(f"   Matched: '{matched_text[:100]}'")
                print(f"   Price: {price_str}")

                # VALIDATION: Reject if contains other variant names
                contains_other_variant = False
                for other_var in other_variants:
                    if re.search(rf'\b{other_var}\b', matched_text, re.IGNORECASE):
                        print(f"   ⚠️ REJECTED: Contains '{other_var}' - wrong variant")
                        contains_other_variant = True
                        break

                if contains_other_variant:
                    continue

                price = normalize_price(price_str)

                if price and 300000 <= price <= 15000000:
                    found_prices.append(price)
                    print(f"   ✅ Valid: ₹{price:,.0f}")

        if found_prices:
            # Take MINIMUM price - most likely to be ex-showroom (since ex-showroom < on-road)
            # Aggregator sites often mix both price types, minimum filters correctly
            min_price = min(found_prices)

            print(f"   ✅ Final: ₹{min_price:,.0f} (using as ex-showroom)")

            return (min_price, url)

        print(f"   ❌ No price found")
        return None

    except Exception as e:
        print(f"   ❌ CarWale scraper error: {e}")
        return None


def get_simple_price(make: str, model: str, variant: str, fuel: str = "Petrol") -> Optional[Tuple[float, str]]:
    """
    Get variant price using simple string matching

    Priority order optimized for coverage and reliability:
    1. CarDekho/CarWale (most comprehensive, covers ALL manufacturers)
    2. Official websites (for additional validation when available)

    Returns:
        Tuple of (ex_showroom_price, source_url) or None
    """
    print(f"\n🎯 Simple scraper: {make} {model} {variant} ({fuel})")

    # Priority 1: CarDekho - Most comprehensive coverage
    # Covers ALL manufacturers including discontinued (Ford, Chevrolet, Fiat)
    result = scrape_cardekho_simple(make, model, variant)
    if result:
        return result

    # Priority 2: CarWale - Alternative aggregator
    result = scrape_carwale_simple(make, model, variant)
    if result:
        return result

    # Priority 3: Official manufacturer website (as fallback)
    # Only for active brands: Maruti, Hyundai, Tata, Honda, Toyota, Kia, Mahindra
    # May miss discontinued brands or specific variants
    if OFFICIAL_SCRAPERS_AVAILABLE:
        print(f"   Aggregators didn't find it, trying official {make} website...")
        result = get_official_price(make, model, variant)
        if result:
            print(f"   ✅ Got price from official {make} website")
            return result

    print("❌ Simple scraper failed on all sources")
    return None
