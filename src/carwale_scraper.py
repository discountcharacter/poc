"""
CarWale Price Scraper
Directly scrapes variant-specific prices from CarWale pricing pages
"""

import re
import requests
from typing import Optional, Tuple
from bs4 import BeautifulSoup


def normalize_variant_name(variant: str) -> str:
    """Normalize variant name for matching (case-insensitive, remove spaces)"""
    return variant.strip().upper().replace(" ", "")


def extract_price_from_text(text: str) -> Optional[float]:
    """Extract numeric price from text like 'Rs. 7.95 Lakh' or '₹6.59 L'"""
    if not text:
        return None

    # Remove currency symbols and common text
    text = text.replace('₹', '').replace('Rs.', '').replace('Rs', '').strip()

    # Handle Lakh format
    if 'lakh' in text.lower() or ' l' in text.lower():
        match = re.search(r'([\d,\.]+)', text)
        if match:
            try:
                lakhs = float(match.group(1).replace(',', ''))
                return lakhs * 100000
            except:
                return None

    # Handle Crore format
    if 'crore' in text.lower() or ' cr' in text.lower():
        match = re.search(r'([\d,\.]+)', text)
        if match:
            try:
                crores = float(match.group(1).replace(',', ''))
                return crores * 10000000
            except:
                return None

    # Try direct number extraction
    text = text.replace(',', '').strip()
    match = re.search(r'(\d+)', text)
    if match:
        try:
            return float(match.group(1))
        except:
            return None

    return None


def scrape_carwale(make: str, model: str, variant: str, fuel: str) -> Optional[Tuple[float, str]]:
    """
    Scrape variant price from CarWale

    Returns:
        Tuple of (ex_showroom_price, source_url) or None
    """
    try:
        # Construct CarWale URL
        make_slug = make.lower().replace(' ', '-')
        model_slug = model.lower().replace(' ', '-')

        url = f"https://www.carwale.com/{make_slug}-cars/{model_slug}/price-in-hyderabad/"

        print(f"🔍 Scraping CarWale: {url}")

        # Fetch page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Normalize target variant
        target_variant = normalize_variant_name(variant)
        target_fuel = fuel.strip().upper()

        print(f"   Looking for variant: {target_variant} ({target_fuel})")

        # Strategy 1: Look for tables with variant listings
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')

            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    # First cell typically has variant name
                    variant_cell = cells[0].get_text(strip=True)

                    # Extract variant name from text like "Swift VXi" or "VXi (Petrol)"
                    variant_match = re.search(r'(LXi|VXi|ZXi|LX|VX|ZX|LXI|VXI|ZXI)', variant_cell, re.IGNORECASE)
                    if variant_match:
                        found_variant = normalize_variant_name(variant_match.group(1))

                        # Check if fuel type matches (if specified in cell)
                        fuel_match = found_variant if target_fuel in variant_cell.upper() or '(' not in variant_cell else None

                        if found_variant == target_variant:
                            # Look for price in subsequent cells
                            for cell in cells[1:]:
                                price_text = cell.get_text(strip=True)
                                price = extract_price_from_text(price_text)

                                if price and 300000 <= price <= 15000000:
                                    print(f"   ✅ Found {variant_cell}: ₹{price:,.0f}")
                                    # Convert on-road to ex-showroom (rough estimate: -17%)
                                    ex_showroom = price / 1.17
                                    return (ex_showroom, url)

        # Strategy 2: Look for div/span structures with variant info
        variant_divs = soup.find_all(['div', 'span', 'li'], class_=re.compile(r'variant|price|model', re.I))

        for div in variant_divs:
            text = div.get_text(strip=True)

            # Look for pattern like "VXi - Rs. 7.95 Lakh"
            variant_price_match = re.search(
                r'(LXi|VXi|ZXi|LX|VX|ZX|LXI|VXI|ZXI)[\s\-:•|]*(?:Rs\.?|₹)?\s*([\d,\.]+\s*(?:Lakh|L|Crore|Cr)?)',
                text,
                re.IGNORECASE
            )

            if variant_price_match:
                found_variant = normalize_variant_name(variant_price_match.group(1))
                price_text = variant_price_match.group(2)

                if found_variant == target_variant:
                    price = extract_price_from_text(price_text)
                    if price and 300000 <= price <= 15000000:
                        print(f"   ✅ Found {text}: ₹{price:,.0f}")
                        ex_showroom = price / 1.17  # Convert to ex-showroom
                        return (ex_showroom, url)

        print(f"   ❌ Variant {variant} not found on CarWale")
        return None

    except Exception as e:
        print(f"   ❌ CarWale scraping error: {e}")
        return None


def scrape_cardekho(make: str, model: str, variant: str, fuel: str) -> Optional[Tuple[float, str]]:
    """
    Scrape variant price from CarDekho

    Returns:
        Tuple of (ex_showroom_price, source_url) or None
    """
    try:
        # Construct CarDekho URL
        make_slug = make.lower().replace(' ', '-')
        model_slug = model.lower().replace(' ', '-')

        url = f"https://www.cardekho.com/{make_slug}/{model_slug}/price-in-hyderabad"

        print(f"🔍 Scraping CarDekho: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        target_variant = normalize_variant_name(variant)
        print(f"   Looking for variant: {target_variant}")

        # Look for variant listings (similar strategies as CarWale)
        # CarDekho typically uses divs with variant data
        variant_elements = soup.find_all(['div', 'li', 'tr'], class_=re.compile(r'variant|model', re.I))

        for elem in variant_elements:
            text = elem.get_text(strip=True)

            variant_match = re.search(r'(LXi|VXi|ZXi|LX|VX|ZX|LXI|VXI|ZXI)', text, re.IGNORECASE)
            if variant_match:
                found_variant = normalize_variant_name(variant_match.group(1))

                if found_variant == target_variant:
                    # Look for price in same element or nearby
                    price_match = re.search(r'(?:Rs\.?|₹)\s*([\d,\.]+\s*(?:Lakh|L)?)', text, re.IGNORECASE)
                    if price_match:
                        price = extract_price_from_text(price_match.group(0))
                        if price and 300000 <= price <= 15000000:
                            print(f"   ✅ Found: ₹{price:,.0f}")
                            ex_showroom = price / 1.17
                            return (ex_showroom, url)

        print(f"   ❌ Variant {variant} not found on CarDekho")
        return None

    except Exception as e:
        print(f"   ❌ CarDekho scraping error: {e}")
        return None


def get_variant_price(make: str, model: str, variant: str, fuel: str = "Petrol") -> Optional[Tuple[float, str]]:
    """
    Get variant-specific price by scraping CarWale and CarDekho

    Returns:
        Tuple of (ex_showroom_price, source_url) or None
    """
    print(f"\n🔍 Scraping variant price for {make} {model} {variant} ({fuel})")

    # Try CarWale first (usually more reliable)
    result = scrape_carwale(make, model, variant, fuel)
    if result:
        return result

    # Fallback to CarDekho
    result = scrape_cardekho(make, model, variant, fuel)
    if result:
        return result

    print(f"❌ Could not scrape price from any source")
    return None
