"""
Direct Price Scraper - More Reliable Alternative to Google Search

Directly fetches prices from CarWale and other sources without needing
Google Custom Search results. Uses intelligent URL construction and
Gemini for extraction.
"""

import os
import json
import requests
from datetime import datetime
from typing import Optional, Dict
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)


def get_carwale_price(make: str, model: str, variant: str, fuel: str) -> Optional[Dict]:
    """
    Fetch price directly from CarWale using constructed URL

    Args:
        make: Vehicle manufacturer
        model: Model name
        variant: Variant/trim
        fuel: Fuel type

    Returns:
        Dictionary with price data or None
    """
    if not GOOGLE_API_KEY:
        return None

    try:
        # Construct CarWale URL (they have predictable URL structure)
        make_lower = make.lower().replace(" ", "-")
        model_lower = model.lower().replace(" ", "-")

        # Try multiple URL patterns
        urls = [
            f"https://www.carwale.com/{make_lower}-cars/{model_lower}/",
            f"https://www.carwale.com/new/{make_lower}-cars/{model_lower}/price-in-hyderabad/",
            f"https://www.carwale.com/{make_lower}-cars/{model_lower}-price-in-hyderabad/",
        ]

        for url in urls:
            try:
                print(f"🔍 Trying CarWale URL: {url}")

                # Fetch page content
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=10)

                if response.status_code == 200:
                    # Use Gemini to extract price from HTML
                    content_preview = response.text[:5000]  # First 5000 chars

                    prompt = f"""Extract the ex-showroom price for the EXACT variant from this CarWale page.

Vehicle:
- Make: {make}
- Model: {model}
- Variant: {variant} ← CRITICAL: Extract price for THIS variant ONLY
- Fuel: {fuel}
- Location: Hyderabad

Page Content (HTML):
{content_preview}

INSTRUCTIONS:
1. Look for variant "{variant}" specifically - ignore LXi, ZXi if searching for VXi
2. Find ex-showroom price in formats:
   - "₹6.59 Lakh" = 659000
   - "Rs. 6,58,900" = 658900
   - "Starts at ₹6.59 L" = 659000
3. If table with multiple variants, extract row matching "{variant}"
4. Ignore on-road/total prices (we only need ex-showroom)

EXAMPLES:
"VXi (Petrol) Rs.6,58,900" → {{"ex_showroom_price": 658900}}
"Swift VXi | Price Starts at ₹6.59 Lakh" → {{"ex_showroom_price": 659000}}

Return ONLY JSON (no other text):
{{
    "ex_showroom_price": <number>,
    "variant_found": "{variant}",
    "confidence": "high"
}}

If variant not found:
{{"ex_showroom_price": null, "variant_found": null, "confidence": "low"}}
"""

                    model_ai = genai.GenerativeModel('gemini-2.0-flash-exp')
                    result = model_ai.generate_content(prompt)

                    # Parse response
                    response_text = result.text.strip()
                    if response_text.startswith("```json"):
                        response_text = response_text.replace("```json", "").replace("```", "").strip()
                    elif response_text.startswith("```"):
                        response_text = response_text.replace("```", "").strip()

                    data = json.loads(response_text)

                    if data.get("ex_showroom_price") and data.get("confidence") in ["high", "medium"]:
                        price = float(data["ex_showroom_price"])

                        # Validation
                        if 300000 <= price <= 15000000:
                            print(f"✅ CarWale price found: ₹{price:,.0f}")
                            return {
                                "ex_showroom_price": price,
                                "on_road_price": price * 1.15,  # Estimate
                                "source": "carwale_direct",
                                "url": url
                            }

            except Exception as e:
                print(f"CarWale URL failed: {e}")
                continue

        return None

    except Exception as e:
        print(f"CarWale scraper error: {e}")
        return None


def get_direct_price(make: str, model: str, variant: str, fuel: str) -> Optional[Dict]:
    """
    Try multiple direct sources in order of reliability

    Args:
        make: Vehicle manufacturer
        model: Model name
        variant: Variant/trim
        fuel: Fuel type

    Returns:
        Dictionary with price data or None
    """
    # Try CarWale first
    carwale_result = get_carwale_price(make, model, variant, fuel)
    if carwale_result:
        return carwale_result

    # Could add more sources here (CardEkho, manufacturer sites, etc.)

    return None


# Export for easy import
if __name__ == "__main__":
    # Test
    result = get_direct_price("Hyundai", "Creta", "SX", "Diesel")
    if result:
        print(f"Price: ₹{result['ex_showroom_price']:,.0f}")
        print(f"Source: {result['source']}")
    else:
        print("No price found")
