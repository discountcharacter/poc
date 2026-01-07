"""
Official Manufacturer Website Scrapers
=======================================
Scrapes ex-showroom prices directly from official manufacturer websites.
These are THE most accurate sources for current vehicle pricing.

Supported Manufacturers:
- Maruti Suzuki (marutisuzuki.com)
- Hyundai (hyundai.com/in)
- Tata Motors (tatamotors.com)
- Kia (kia.com/in)
- Toyota (toyotabharat.com)
- Honda (hondacarindia.com)
- Mahindra (mahindra.com)
- MG Motor (mgmotor.co.in)
- Renault (renault.co.in)
- Nissan (nissan.in)
"""

import re
import requests
from typing import Optional, Tuple
from urllib.parse import quote


def normalize_price(price_str: str) -> Optional[float]:
    """Convert price string to float (handles Lakh, Crore, numeric formats)"""
    if not price_str:
        return None

    price_str = price_str.replace('₹', '').replace('Rs.', '').replace('Rs', '').replace(',', '').strip()

    # Handle Lakh format
    if 'lakh' in price_str.lower() or ' l' in price_str.lower():
        match = re.search(r'([\d\.]+)', price_str)
        if match:
            try:
                return float(match.group(1)) * 100000
            except:
                return None

    # Handle Crore format
    if 'crore' in price_str.lower() or ' cr' in price_str.lower():
        match = re.search(r'([\d\.]+)', price_str)
        if match:
            try:
                return float(match.group(1)) * 10000000
            except:
                return None

    # Direct number
    try:
        return float(price_str.replace(' ', ''))
    except:
        return None


def scrape_maruti_official(model: str, variant: str) -> Optional[Tuple[float, str]]:
    """
    Scrape Maruti Suzuki official website
    URL format: https://www.marutisuzuki.com/{model}
    """
    try:
        model_slug = model.lower().replace(' ', '-')
        url = f"https://www.marutisuzuki.com/{model_slug}"

        print(f"🏢 Maruti Official: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

        response = requests.get(url, headers=headers, timeout=15, verify=True)
        response.raise_for_status()

        html = response.text

        # Look for variant-specific pricing
        # Patterns: "VXi Rs. 6.59 Lakh*" or similar (handles mixed case)
        target_variant = variant.strip().upper()

        # Create flexible variant pattern (handles "VXI" and "VXi" style)
        variant_pattern = variant.strip().replace('I', '[Ii]').replace('i', '[Ii]')

        patterns = [
            rf'{variant_pattern}[^<]*?(?:Rs\.?|₹)\s*([\d,\.]+)\s*(?:Lakh|L)',
            rf'>{variant_pattern}<[^>]*>.*?(?:Rs\.?|₹)\s*([\d,\.]+)\s*(?:Lakh|L)',
            rf'data-variant=["\']?{variant_pattern}["\']?[^>]*>.*?(?:Rs\.?|₹)\s*([\d,\.]+)\s*(?:Lakh|L)',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                price_str = match.group(1)
                price = normalize_price(price_str + " Lakh")

                if price and 300000 <= price <= 15000000:
                    print(f"   ✅ Maruti Official: ₹{price:,.0f}")
                    return (price, url)

        print("   ❌ Maruti: Variant not found")
        return None

    except Exception as e:
        print(f"   ❌ Maruti error: {e}")
        return None


def scrape_hyundai_official(model: str, variant: str, city: str = "hyderabad") -> Optional[Tuple[float, str]]:
    """
    Scrape Hyundai official website
    URL format: https://www.hyundai.com/in/en/find-a-car/{model}/price
    """
    try:
        model_slug = model.lower().replace(' ', '-')
        url = f"https://www.hyundai.com/in/en/find-a-car/{model_slug}/price"

        print(f"🏢 Hyundai Official: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        html = response.text

        target_variant = variant.strip().upper()

        # Create flexible variant pattern (handles "VXI" and "VXi" style)
        variant_pattern = variant.strip().replace('I', '[Ii]').replace('i', '[Ii]')

        # Hyundai uses variant codes like "SX", "SX(O)", "N Line"
        patterns = [
            rf'{variant_pattern}[^<]*?₹\s*([\d,]+)',
            rf'>{variant_pattern}<[^>]*>.*?₹\s*([\d,]+)',
            rf'{variant_pattern}.*?Ex-showroom.*?₹\s*([\d,]+)',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                price_str = match.group(1)
                price = normalize_price(price_str)

                if price and 300000 <= price <= 15000000:
                    print(f"   ✅ Hyundai Official: ₹{price:,.0f}")
                    return (price, url)

        print("   ❌ Hyundai: Variant not found")
        return None

    except Exception as e:
        print(f"   ❌ Hyundai error: {e}")
        return None


def scrape_tata_official(model: str, variant: str) -> Optional[Tuple[float, str]]:
    """
    Scrape Tata Motors official website
    URL format: https://cars.tatamotors.com/{model}
    """
    try:
        model_slug = model.lower().replace(' ', '-')
        url = f"https://cars.tatamotors.com/{model_slug}"

        print(f"🏢 Tata Official: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        html = response.text

        target_variant = variant.strip().upper()

        # Create flexible variant pattern (handles "VXI" and "VXi" style)
        variant_pattern = variant.strip().replace('I', '[Ii]').replace('i', '[Ii]')

        patterns = [
            rf'{variant_pattern}[^<]*?(?:Rs\.?|₹)\s*([\d,\.]+)\s*(?:Lakh|L)',
            rf'>{variant_pattern}<[^>]*>.*?(?:Rs\.?|₹)\s*([\d,\.]+)\s*(?:Lakh|L)',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                price_str = match.group(1)
                price = normalize_price(price_str + " Lakh")

                if price and 300000 <= price <= 15000000:
                    print(f"   ✅ Tata Official: ₹{price:,.0f}")
                    return (price, url)

        print("   ❌ Tata: Variant not found")
        return None

    except Exception as e:
        print(f"   ❌ Tata error: {e}")
        return None


def scrape_kia_official(model: str, variant: str) -> Optional[Tuple[float, str]]:
    """Scrape Kia India official website"""
    try:
        model_slug = model.lower().replace(' ', '-')
        url = f"https://www.kia.com/in/buy-a-car/{model_slug}"

        print(f"🏢 Kia Official: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        html = response.text
        target_variant = variant.strip().upper()

        patterns = [
            rf'{variant}[^<]*?₹\s*([\d,\.]+)\s*(?:Lakh|L)',
            rf'>{variant}<[^>]*>.*?₹\s*([\d,\.]+)\s*(?:Lakh|L)',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                price_str = match.group(1)
                price = normalize_price(price_str + " Lakh")

                if price and 300000 <= price <= 15000000:
                    print(f"   ✅ Kia Official: ₹{price:,.0f}")
                    return (price, url)

        return None

    except Exception as e:
        print(f"   ❌ Kia error: {e}")
        return None


def scrape_toyota_official(model: str, variant: str) -> Optional[Tuple[float, str]]:
    """Scrape Toyota Bharat official website"""
    try:
        model_slug = model.lower().replace(' ', '-')
        url = f"https://www.toyotabharat.com/showroom/{model_slug}"

        print(f"🏢 Toyota Official: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        html = response.text
        target_variant = variant.strip().upper()

        patterns = [
            rf'{variant}[^<]*?₹\s*([\d,\.]+)\s*(?:Lakh|L)',
            rf'>{variant}<[^>]*>.*?₹\s*([\d,\.]+)\s*(?:Lakh|L)',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                price_str = match.group(1)
                price = normalize_price(price_str + " Lakh")

                if price and 300000 <= price <= 15000000:
                    print(f"   ✅ Toyota Official: ₹{price:,.0f}")
                    return (price, url)

        return None

    except Exception as e:
        print(f"   ❌ Toyota error: {e}")
        return None


def scrape_honda_official(model: str, variant: str) -> Optional[Tuple[float, str]]:
    """Scrape Honda Car India official website"""
    try:
        model_slug = model.lower().replace(' ', '-')
        url = f"https://www.hondacarindia.com/our-range/{model_slug}/price"

        print(f"🏢 Honda Official: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        html = response.text
        target_variant = variant.strip().upper()

        patterns = [
            rf'{variant}[^<]*?₹\s*([\d,\.]+)\s*(?:Lakh|L)',
            rf'>{variant}<[^>]*>.*?₹\s*([\d,\.]+)\s*(?:Lakh|L)',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                price_str = match.group(1)
                price = normalize_price(price_str + " Lakh")

                if price and 300000 <= price <= 15000000:
                    print(f"   ✅ Honda Official: ₹{price:,.0f}")
                    return (price, url)

        return None

    except Exception as e:
        print(f"   ❌ Honda error: {e}")
        return None


def scrape_mahindra_official(model: str, variant: str) -> Optional[Tuple[float, str]]:
    """Scrape Mahindra official website"""
    try:
        model_slug = model.lower().replace(' ', '-')
        url = f"https://www.mahindra.com/passenger-vehicles/{model_slug}"

        print(f"🏢 Mahindra Official: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        html = response.text
        target_variant = variant.strip().upper()

        patterns = [
            rf'{variant}[^<]*?₹\s*([\d,\.]+)\s*(?:Lakh|L)',
            rf'>{variant}<[^>]*>.*?₹\s*([\d,\.]+)\s*(?:Lakh|L)',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                price_str = match.group(1)
                price = normalize_price(price_str + " Lakh")

                if price and 300000 <= price <= 15000000:
                    print(f"   ✅ Mahindra Official: ₹{price:,.0f}")
                    return (price, url)

        return None

    except Exception as e:
        print(f"   ❌ Mahindra error: {e}")
        return None


# Manufacturer routing
OFFICIAL_SCRAPERS = {
    'maruti': scrape_maruti_official,
    'maruti suzuki': scrape_maruti_official,
    'hyundai': scrape_hyundai_official,
    'tata': scrape_tata_official,
    'tata motors': scrape_tata_official,
    'kia': scrape_kia_official,
    'toyota': scrape_toyota_official,
    'honda': scrape_honda_official,
    'mahindra': scrape_mahindra_official,
}


def get_official_price(make: str, model: str, variant: str, city: str = "hyderabad") -> Optional[Tuple[float, str]]:
    """
    Get price from official manufacturer website

    Returns:
        Tuple of (ex_showroom_price, source_url) or None
    """
    make_lower = make.lower().strip()

    scraper_func = OFFICIAL_SCRAPERS.get(make_lower)

    if not scraper_func:
        print(f"   ⚠️ No official scraper for {make}")
        return None

    try:
        # Call the appropriate scraper
        if make_lower == 'hyundai':
            return scraper_func(model, variant, city)
        else:
            return scraper_func(model, variant)
    except Exception as e:
        print(f"   ❌ Official scraper error for {make}: {e}")
        return None
