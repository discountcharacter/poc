"""
Automotive Aggregator Website Scrapers
======================================
Scrapes from premium automotive aggregator websites for cross-validation.

Supported Aggregators:
- ZigWheels (zigwheels.com)
- V3Cars (v3cars.com)
- AutocarIndia (autocarindia.com)
- Smartprix (smartprix.com)
"""

import re
import requests
from typing import Optional, Tuple


def normalize_price(price_str: str) -> Optional[float]:
    """Convert price string to float"""
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


def scrape_zigwheels(make: str, model: str, variant: str) -> Optional[Tuple[float, str]]:
    """
    Scrape ZigWheels for variant price
    URL format: https://www.zigwheels.com/{make}-{model}/price-in-hyderabad
    """
    try:
        make_slug = make.lower().replace(' ', '-').replace('maruti suzuki', 'maruti')
        model_slug = model.lower().replace(' ', '-')

        url = f"https://www.zigwheels.com/{make_slug}-{model_slug}/price-in-hyderabad"

        print(f"🔍 ZigWheels: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        html = response.text
        target_variant = variant.strip().upper()

        # ZigWheels patterns
        patterns = [
            rf'{variant}[^<]*?(?:Rs\.?|₹)\s*([\d,\.]+)\s*(?:Lakh|L)',
            rf'>{variant}<[^>]*>.*?(?:Rs\.?|₹)\s*([\d,\.]+)\s*(?:Lakh|L)',
            rf'{variant}.*?Ex-showroom.*?(?:Rs\.?|₹)\s*([\d,\.]+)\s*(?:Lakh|L)',
        ]

        # Cross-variant validation
        other_variants = ['LXI', 'VXI', 'ZXI', 'LX', 'VX', 'ZX', 'SIGMA', 'DELTA', 'ZETA', 'ALPHA']
        other_variants = [v for v in other_variants if v.upper() != target_variant]

        found_prices = []

        for pattern in patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                matched_text = match.group(0)
                price_str = match.group(1)

                # Reject if contains other variant names
                contains_other = any(re.search(rf'\b{v}\b', matched_text, re.IGNORECASE)
                                   for v in other_variants)
                if contains_other:
                    continue

                price = normalize_price(price_str + " Lakh")

                if price and 300000 <= price <= 15000000:
                    found_prices.append(price)

        if found_prices:
            min_price = min(found_prices)
            print(f"   ✅ ZigWheels: ₹{min_price:,.0f}")
            return (min_price, url)

        print("   ❌ ZigWheels: Not found")
        return None

    except Exception as e:
        print(f"   ❌ ZigWheels error: {e}")
        return None


def scrape_v3cars(make: str, model: str, variant: str) -> Optional[Tuple[float, str]]:
    """
    Scrape V3Cars for variant price
    URL format: https://www.v3cars.com/{make}-{model}-price-in-india
    """
    try:
        make_slug = make.lower().replace(' ', '-')
        model_slug = model.lower().replace(' ', '-')

        url = f"https://www.v3cars.com/{make_slug}-{model_slug}-price-in-india"

        print(f"🔍 V3Cars: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        html = response.text
        target_variant = variant.strip().upper()

        patterns = [
            rf'{variant}[^<]*?(?:Rs\.?|₹)\s*([\d,\.]+)\s*(?:Lakh|L)',
            rf'>{variant}<[^>]*>.*?(?:Rs\.?|₹)\s*([\d,\.]+)\s*(?:Lakh|L)',
        ]

        other_variants = ['LXI', 'VXI', 'ZXI', 'LX', 'VX', 'ZX', 'SIGMA', 'DELTA', 'ZETA', 'ALPHA']
        other_variants = [v for v in other_variants if v.upper() != target_variant]

        found_prices = []

        for pattern in patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                matched_text = match.group(0)
                price_str = match.group(1)

                contains_other = any(re.search(rf'\b{v}\b', matched_text, re.IGNORECASE)
                                   for v in other_variants)
                if contains_other:
                    continue

                price = normalize_price(price_str + " Lakh")

                if price and 300000 <= price <= 15000000:
                    found_prices.append(price)

        if found_prices:
            min_price = min(found_prices)
            print(f"   ✅ V3Cars: ₹{min_price:,.0f}")
            return (min_price, url)

        print("   ❌ V3Cars: Not found")
        return None

    except Exception as e:
        print(f"   ❌ V3Cars error: {e}")
        return None


def scrape_autocar_india(make: str, model: str, variant: str) -> Optional[Tuple[float, str]]:
    """
    Scrape AutocarIndia for variant price
    URL format: https://www.autocarindia.com/cars/{make}/{model}
    """
    try:
        make_slug = make.lower().replace(' ', '-')
        model_slug = model.lower().replace(' ', '-')

        url = f"https://www.autocarindia.com/cars/{make_slug}/{model_slug}"

        print(f"🔍 AutocarIndia: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        html = response.text
        target_variant = variant.strip().upper()

        patterns = [
            rf'{variant}[^<]*?(?:Rs\.?|₹)\s*([\d,\.]+)\s*(?:Lakh|L)',
            rf'>{variant}<[^>]*>.*?(?:Rs\.?|₹)\s*([\d,\.]+)\s*(?:Lakh|L)',
        ]

        other_variants = ['LXI', 'VXI', 'ZXI', 'LX', 'VX', 'ZX', 'SIGMA', 'DELTA', 'ZETA', 'ALPHA']
        other_variants = [v for v in other_variants if v.upper() != target_variant]

        found_prices = []

        for pattern in patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                matched_text = match.group(0)
                price_str = match.group(1)

                contains_other = any(re.search(rf'\b{v}\b', matched_text, re.IGNORECASE)
                                   for v in other_variants)
                if contains_other:
                    continue

                price = normalize_price(price_str + " Lakh")

                if price and 300000 <= price <= 15000000:
                    found_prices.append(price)

        if found_prices:
            min_price = min(found_prices)
            print(f"   ✅ AutocarIndia: ₹{min_price:,.0f}")
            return (min_price, url)

        print("   ❌ AutocarIndia: Not found")
        return None

    except Exception as e:
        print(f"   ❌ AutocarIndia error: {e}")
        return None


def scrape_smartprix(make: str, model: str, variant: str) -> Optional[Tuple[float, str]]:
    """
    Scrape Smartprix for variant price
    URL format: https://www.smartprix.com/cars/{make}-{model}-price-in-india
    """
    try:
        make_slug = make.lower().replace(' ', '-')
        model_slug = model.lower().replace(' ', '-')

        url = f"https://www.smartprix.com/cars/{make_slug}-{model_slug}-price-in-india"

        print(f"🔍 Smartprix: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        html = response.text
        target_variant = variant.strip().upper()

        patterns = [
            rf'{variant}[^<]*?(?:Rs\.?|₹)\s*([\d,\.]+)\s*(?:Lakh|L)',
            rf'>{variant}<[^>]*>.*?(?:Rs\.?|₹)\s*([\d,\.]+)\s*(?:Lakh|L)',
        ]

        other_variants = ['LXI', 'VXI', 'ZXI', 'LX', 'VX', 'ZX', 'SIGMA', 'DELTA', 'ZETA', 'ALPHA']
        other_variants = [v for v in other_variants if v.upper() != target_variant]

        found_prices = []

        for pattern in patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                matched_text = match.group(0)
                price_str = match.group(1)

                contains_other = any(re.search(rf'\b{v}\b', matched_text, re.IGNORECASE)
                                   for v in other_variants)
                if contains_other:
                    continue

                price = normalize_price(price_str + " Lakh")

                if price and 300000 <= price <= 15000000:
                    found_prices.append(price)

        if found_prices:
            min_price = min(found_prices)
            print(f"   ✅ Smartprix: ₹{min_price:,.0f}")
            return (min_price, url)

        print("   ❌ Smartprix: Not found")
        return None

    except Exception as e:
        print(f"   ❌ Smartprix error: {e}")
        return None
