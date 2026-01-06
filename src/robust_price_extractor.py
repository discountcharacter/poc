"""
Robust Price Extractor - Uses Regex Pattern Matching

Instead of relying on Gemini to filter variants, this uses Python regex
to extract ALL prices with their variants, then filters programmatically.

This is more reliable for variant-specific price extraction.
"""

import re
from typing import Optional, Dict, Tuple, List


def normalize_price(price_str: str) -> Optional[float]:
    """
    Convert various price formats to float

    Examples:
        "₹6.59 Lakh" -> 659000
        "Rs.6,58,900" -> 658900
        "₹ 6.59 L" -> 659000
        "6.59 Lakhs" -> 659000
    """
    if not price_str:
        return None

    # Remove currency symbols and clean up
    price_str = price_str.replace('₹', '').replace('Rs.', '').replace('Rs', '').strip()

    # Check if it's in Lakhs/Crores format
    if 'lakh' in price_str.lower() or ' l' in price_str.lower():
        # Extract the number
        number_match = re.search(r'([\d,\.]+)', price_str)
        if number_match:
            number = number_match.group(1).replace(',', '')
            try:
                lakhs = float(number)
                return lakhs * 100000
            except:
                return None

    elif 'crore' in price_str.lower() or ' cr' in price_str.lower():
        number_match = re.search(r'([\d,\.]+)', price_str)
        if number_match:
            number = number_match.group(1).replace(',', '')
            try:
                crores = float(number)
                return crores * 10000000
            except:
                return None

    # Otherwise assume it's full number format
    price_str = price_str.replace(',', '').strip()
    number_match = re.search(r'(\d+)', price_str)
    if number_match:
        try:
            return float(number_match.group(1))
        except:
            return None

    return None


def extract_variant_prices(text: str, target_variant: str) -> List[Dict]:
    """
    Extract all variant-price pairs from text using regex

    Args:
        text: Search result text containing prices
        target_variant: Variant to look for (e.g., "VXi", "VXI", "vxi")

    Returns:
        List of dicts with variant and price info
    """
    results = []

    # Normalize target variant for comparison
    target_variant_normalized = target_variant.strip().upper()

    # Pattern 1: "VXi (Petrol) · Rs.6,58,900"
    pattern1 = r'([A-Za-z]+[A-Za-z0-9]*)\s*(?:\([^)]+\))?\s*[·•-]?\s*(?:Rs\.?|₹)\s*([\d,\.]+(?:\s*(?:Lakh|L|Crore|Cr))?)'

    # Pattern 2: "VXi: ₹6.59 Lakh"
    pattern2 = r'([A-Za-z]+[A-Za-z0-9]*)\s*:\s*(?:Rs\.?|₹)\s*([\d,\.]+(?:\s*(?:Lakh|L|Crore|Cr))?)'

    # Pattern 3: "Maruti Swift VXi | Price Starts at ₹6.59 Lakh"
    pattern3 = r'([A-Za-z]+[A-Za-z0-9]*)\s*\|\s*Price.*?(?:Rs\.?|₹)\s*([\d,\.]+(?:\s*(?:Lakh|L|Crore|Cr))?)'

    # Pattern 4: Table format "VXi  ₹ 6,58,901 Lakh"
    pattern4 = r'([A-Za-z]+[A-Za-z0-9]*)\s+(?:Rs\.?|₹)\s*([\d,\.]+(?:\s*(?:Lakh|L|Crore|Cr))?)'

    all_patterns = [pattern1, pattern2, pattern3, pattern4]

    for pattern in all_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            variant = match.group(1).strip()
            price_str = match.group(2).strip()

            # Normalize variant for comparison
            variant_normalized = variant.upper()

            # Check if this variant matches our target (case-insensitive)
            if variant_normalized == target_variant_normalized:
                price = normalize_price(price_str)
                if price and 300000 <= price <= 15000000:  # Sanity check
                    results.append({
                        'variant': variant,
                        'variant_normalized': variant_normalized,
                        'price': price,
                        'price_str': price_str,
                        'matched': True
                    })

    return results


def extract_price_for_variant(search_results: list, make: str, model: str,
                              variant: str, fuel: str) -> Optional[Tuple[float, str]]:
    """
    Extract price for specific variant from search results using regex

    Args:
        search_results: List of search result dicts with 'title', 'snippet', 'link'
        make: Vehicle make
        model: Vehicle model
        variant: Target variant (e.g., "VXi", "VXI")
        fuel: Fuel type

    Returns:
        Tuple of (price, source_url) or None
    """
    all_variant_prices = []

    for result in search_results:
        # Combine title and snippet for better coverage
        text = f"{result.get('title', '')} {result.get('snippet', '')}"
        source_url = result.get('link', '')

        # Extract variant-price pairs
        extracted = extract_variant_prices(text, variant)

        for item in extracted:
            item['source'] = source_url
            all_variant_prices.append(item)

    if not all_variant_prices:
        return None

    # Sort by most common price (mode)
    price_counts = {}
    for item in all_variant_prices:
        price_rounded = round(item['price'], -3)  # Round to nearest thousand
        price_counts[price_rounded] = price_counts.get(price_rounded, 0) + 1

    # Get most common price
    if price_counts:
        most_common_price = max(price_counts, key=price_counts.get)

        # Find the first exact match for that price
        for item in all_variant_prices:
            if round(item['price'], -3) == most_common_price:
                return (item['price'], item['source'])

    # Fallback: return first valid price
    return (all_variant_prices[0]['price'], all_variant_prices[0]['source'])


# Test function
if __name__ == "__main__":
    # Test price normalization
    test_cases = [
        ("₹6.59 Lakh", 659000),
        ("Rs.6,58,900", 658900),
        ("₹ 6.59 L", 659000),
        ("6.59 Lakhs", 659000),
        ("₹5.79 Lakh", 579000),
    ]

    print("Testing price normalization:")
    for input_str, expected in test_cases:
        result = normalize_price(input_str)
        status = "✅" if result == expected else "❌"
        print(f"{status} {input_str} -> {result} (expected {expected})")

    # Test variant extraction
    print("\nTesting variant extraction:")
    test_text = """
    Maruti Swift Price in Hyderabad:
    LXi: ₹5.79 Lakh | VXi: ₹6.59 Lakh | ZXi: ₹7.50 Lakh

    VXi (Petrol) · Rs.6,58,900
    """

    results = extract_variant_prices(test_text, "VXI")  # Case-insensitive test
    print(f"Searching for 'VXI' in text:")
    for r in results:
        print(f"  Found: {r['variant']} -> ₹{r['price']:,.0f}")
