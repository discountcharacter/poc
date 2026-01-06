"""
Official Website Scrapers for All Major Car Manufacturers
Gets accurate ex-showroom prices directly from manufacturer websites
"""

import re
import requests
from typing import Optional, Tuple


def normalize_price(price_str: str) -> Optional[float]:
    """Convert price string to float (handles spaces, commas, lakhs, crores)"""
    if not price_str:
        return None

    # Remove currency symbols
    price_str = price_str.replace('₹', '').replace('Rs.', '').replace('Rs', '').strip()

    # Handle Lakh format
    if 'lakh' in price_str.lower() or ' l' in price_str.lower():
        match = re.search(r'([\d,\.\s]+)', price_str)
        if match:
            try:
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

    # Direct number
    try:
        clean_str = price_str.replace(',', '').replace(' ', '')
        return float(clean_str)
    except:
        return None


def scrape_maruti_official(model: str, variant: str) -> Optional[Tuple[float, str]]:
    """Scrape Maruti Suzuki official website"""
    try:
        model_slug = model.lower().replace(' ', '-')
        url = f"https://www.marutisuzuki.com/price-list/{model_slug}-price-in-hyderabad-in-telangana"

        print(f"   Trying official Maruti: {url}")

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        html = response.text

        # Pattern: "Swift Lxi Price in hyderabad. ₹5 78 900.00"
        pattern = rf'{model}\s+{variant}\s+Price\s+in\s+\w+\.\s*(?:Rs\.?|₹)\s*([\d,\.\s]+)'

        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            price = normalize_price(match.group(1))
            if price and 300000 <= price <= 15000000:
                print(f"   ✅ Maruti official: ₹{price:,.0f}")
                return (price, url)

        return None
    except Exception as e:
        print(f"   ❌ Maruti scraper error: {e}")
        return None


def scrape_hyundai_official(model: str, variant: str) -> Optional[Tuple[float, str]]:
    """Scrape Hyundai official website"""
    try:
        model_slug = model.lower().replace(' ', '-')
        url = f"https://www.hyundai.com/in/en/find-a-car/{model_slug}/price"

        print(f"   Trying official Hyundai: {url}")

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        html = response.text

        # Multiple patterns for Hyundai format
        patterns = [
            rf'{variant}\s*(?:Petrol|Diesel|CNG)?\s*(?:Rs\.?|₹)\s*([\d,\.\s]+\s*(?:Lakh)?)',
            rf'{variant}.*?(?:Rs\.?|₹)\s*([\d,\.\s]+)\s*(?:Lakh|\.00)',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                price = normalize_price(match.group(1) + " Lakh" if "Lakh" not in match.group(1) else match.group(1))
                if price and 300000 <= price <= 15000000:
                    print(f"   ✅ Hyundai official: ₹{price:,.0f}")
                    return (price, url)

        return None
    except Exception as e:
        print(f"   ❌ Hyundai scraper error: {e}")
        return None


def scrape_tata_official(model: str, variant: str) -> Optional[Tuple[float, str]]:
    """Scrape Tata Motors official website"""
    try:
        model_slug = model.lower().replace(' ', '-')
        url = f"https://www.tatamotors.com/cars/{model_slug}/price"

        print(f"   Trying official Tata: {url}")

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        html = response.text

        patterns = [
            rf'{variant}\s*(?:Rs\.?|₹)\s*([\d,\.\s]+\s*(?:Lakh)?)',
            rf'{variant}.*?(?:Rs\.?|₹)\s*([\d,\.\s]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                price = normalize_price(match.group(1) + " Lakh" if "Lakh" not in match.group(1) else match.group(1))
                if price and 300000 <= price <= 15000000:
                    print(f"   ✅ Tata official: ₹{price:,.0f}")
                    return (price, url)

        return None
    except Exception as e:
        print(f"   ❌ Tata scraper error: {e}")
        return None


def scrape_honda_official(model: str, variant: str) -> Optional[Tuple[float, str]]:
    """Scrape Honda official website"""
    try:
        model_slug = model.lower().replace(' ', '-')
        url = f"https://www.hondacarindia.com/honda-{model_slug}-price"

        print(f"   Trying official Honda: {url}")

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        html = response.text

        patterns = [
            rf'{variant}\s*(?:Rs\.?|₹)\s*([\d,\.\s]+\s*(?:Lakh)?)',
            rf'{variant}.*?(?:Rs\.?|₹)\s*([\d,\.\s]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                price = normalize_price(match.group(1) + " Lakh" if "Lakh" not in match.group(1) else match.group(1))
                if price and 300000 <= price <= 15000000:
                    print(f"   ✅ Honda official: ₹{price:,.0f}")
                    return (price, url)

        return None
    except Exception as e:
        print(f"   ❌ Honda scraper error: {e}")
        return None


def scrape_toyota_official(model: str, variant: str) -> Optional[Tuple[float, str]]:
    """Scrape Toyota official website"""
    try:
        model_slug = model.lower().replace(' ', '-')
        url = f"https://www.toyotabharat.com/showroom/{model_slug}/price.html"

        print(f"   Trying official Toyota: {url}")

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        html = response.text

        patterns = [
            rf'{variant}\s*(?:Rs\.?|₹)\s*([\d,\.\s]+\s*(?:Lakh)?)',
            rf'{variant}.*?(?:Rs\.?|₹)\s*([\d,\.\s]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                price = normalize_price(match.group(1) + " Lakh" if "Lakh" not in match.group(1) else match.group(1))
                if price and 300000 <= price <= 15000000:
                    print(f"   ✅ Toyota official: ₹{price:,.0f}")
                    return (price, url)

        return None
    except Exception as e:
        print(f"   ❌ Toyota scraper error: {e}")
        return None


def scrape_kia_official(model: str, variant: str) -> Optional[Tuple[float, str]]:
    """Scrape Kia official website"""
    try:
        model_slug = model.lower().replace(' ', '-')
        url = f"https://www.kia.com/in/discover-kia/{model_slug}/price.html"

        print(f"   Trying official Kia: {url}")

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        html = response.text

        patterns = [
            rf'{variant}\s*(?:Rs\.?|₹)\s*([\d,\.\s]+\s*(?:Lakh)?)',
            rf'{variant}.*?(?:Rs\.?|₹)\s*([\d,\.\s]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                price = normalize_price(match.group(1) + " Lakh" if "Lakh" not in match.group(1) else match.group(1))
                if price and 300000 <= price <= 15000000:
                    print(f"   ✅ Kia official: ₹{price:,.0f}")
                    return (price, url)

        return None
    except Exception as e:
        print(f"   ❌ Kia scraper error: {e}")
        return None


def scrape_mahindra_official(model: str, variant: str) -> Optional[Tuple[float, str]]:
    """Scrape Mahindra official website"""
    try:
        model_slug = model.lower().replace(' ', '-')
        url = f"https://www.mahindra.com/cars/{model_slug}/price"

        print(f"   Trying official Mahindra: {url}")

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        html = response.text

        patterns = [
            rf'{variant}\s*(?:Rs\.?|₹)\s*([\d,\.\s]+\s*(?:Lakh)?)',
            rf'{variant}.*?(?:Rs\.?|₹)\s*([\d,\.\s]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                price = normalize_price(match.group(1) + " Lakh" if "Lakh" not in match.group(1) else match.group(1))
                if price and 300000 <= price <= 15000000:
                    print(f"   ✅ Mahindra official: ₹{price:,.0f}")
                    return (price, url)

        return None
    except Exception as e:
        print(f"   ❌ Mahindra scraper error: {e}")
        return None


# Manufacturer scraper registry
OFFICIAL_SCRAPERS = {
    'maruti suzuki': scrape_maruti_official,
    'maruti': scrape_maruti_official,
    'hyundai': scrape_hyundai_official,
    'tata': scrape_tata_official,
    'tata motors': scrape_tata_official,
    'honda': scrape_honda_official,
    'toyota': scrape_toyota_official,
    'kia': scrape_kia_official,
    'mahindra': scrape_mahindra_official,
}


def get_official_price(make: str, model: str, variant: str) -> Optional[Tuple[float, str]]:
    """
    Try to get price from official manufacturer website

    Returns:
        Tuple of (ex_showroom_price, source_url) or None
    """
    make_lower = make.lower().strip()

    # Try exact match first
    if make_lower in OFFICIAL_SCRAPERS:
        scraper = OFFICIAL_SCRAPERS[make_lower]
        result = scraper(model, variant)
        if result:
            return result

    # Try partial match (e.g., "Maruti Suzuki" matches "maruti")
    for key, scraper in OFFICIAL_SCRAPERS.items():
        if key in make_lower or make_lower in key:
            result = scraper(model, variant)
            if result:
                return result

    return None
