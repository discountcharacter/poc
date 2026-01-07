"""
Live Vehicle Price Fetcher - Gemini API with Google Search Grounding

Uses Gemini 3 Flash with Google Search grounding to fetch accurate
ex-showroom prices for specific vehicle variants.
"""

import os
import json
import re
from typing import Optional, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to import new Google GenAI SDK
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("⚠️ google-genai package not installed. Install with: pip install google-genai")


def normalize_price(price_str: str) -> Optional[float]:
    """
    Convert various price formats to float

    Handles:
    - "5.79 Lakh" -> 579000
    - "₹5,78,900" -> 578900
    - "6.5L" -> 650000
    - "1.2 Crore" -> 12000000
    """
    if not price_str:
        return None

    # Clean up
    price_str = price_str.replace('₹', '').replace('Rs.', '').replace('Rs', '').strip()

    # Lakh format
    if 'lakh' in price_str.lower() or ' l' in price_str.lower():
        match = re.search(r'([\d,\.]+)', price_str)
        if match:
            try:
                lakhs = float(match.group(1).replace(',', ''))
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

    # Plain number with commas: "5,78,900"
    try:
        clean = price_str.replace(',', '').replace(' ', '').strip()
        if clean.replace('.', '').isdigit():
            return float(clean)
    except:
        pass

    return None


def get_car_price_gemini(make: str, model: str, variant: str, year: int,
                         month: int, fuel_type: str, transmission: str,
                         city: str = "Hyderabad") -> Optional[Dict]:
    """
    Fetch car price using Gemini API with Google Search grounding

    Args:
        make: Vehicle manufacturer (e.g., "Maruti Suzuki")
        model: Model name (e.g., "Swift")
        variant: Variant/trim (e.g., "LXI", "VXI")
        year: Manufacturing year (e.g., 2020)
        month: Manufacturing month (1-12)
        fuel_type: Fuel type (e.g., "Petrol", "Diesel")
        transmission: Transmission type (e.g., "Manual", "Automatic")
        city: City name for location-specific pricing

    Returns:
        Dictionary with 'ex_showroom_price' and 'source' or None if failed
    """
    if not GENAI_AVAILABLE:
        raise ImportError("google-genai package not installed. Install with: pip install google-genai")

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "❌ GEMINI_API_KEY or GOOGLE_API_KEY not found in environment variables.\n"
            "   Set your API key in .env file:\n"
            "   GEMINI_API_KEY=your_key_here"
        )

    try:
        client = genai.Client(api_key=api_key)

        # Construct query - emphasize CURRENT ex-showroom price
        prompt_text = (
            f"What is the CURRENT ex-showroom price of "
            f"{make} {model} {variant} {fuel_type} {transmission} "
            f"in {city}? "
            f"Return ONLY the ex-showroom price in Indian Rupees as a JSON object with this format: "
            f'{{ "price": "X.XX Lakh", "year": {year}, "variant": "{variant}" }}. '
            f"Be specific to the {variant} variant, not other variants."
        )

        print(f"🔍 Gemini API: Searching for {make} {model} {variant}...")
        print(f"   Prompt: {prompt_text[:100]}...")

        # IMPORTANT: Use the model name specified by user
        model_name = "gemini-2.0-flash-exp"

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt_text),
                ],
            ),
        ]

        # Enable Google Search grounding
        tools = [
            types.Tool(google_search=types.GoogleSearch()),
        ]

        generate_content_config = types.GenerateContentConfig(
            temperature=0,  # Deterministic output
            tools=tools,
            response_mime_type="application/json",
        )

        response_text = ""

        # Stream response
        try:
            for chunk in client.models.generate_content_stream(
                model=model_name,
                contents=contents,
                config=generate_content_config,
            ):
                if hasattr(chunk, 'text') and chunk.text:
                    response_text += chunk.text
                    print(f"   Chunk received: {chunk.text[:50]}...")
        except Exception as stream_error:
            print(f"   ⚠️ Streaming error: {stream_error}")
            # Try non-streaming as fallback
            print(f"   Trying non-streaming...")
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=generate_content_config,
            )
            response_text = response.text if hasattr(response, 'text') else str(response)

        print(f"   📊 Full response: {response_text[:300]}")

        if not response_text or response_text.strip() == "":
            print(f"   ⚠️ Empty response from Gemini API")
            return None

        # Parse JSON response
        try:
            data = json.loads(response_text)

            # Extract price from various possible keys
            price_str = None
            if 'price' in data:
                price_str = str(data['price'])
            elif 'ex_showroom_price' in data:
                price_str = str(data['ex_showroom_price'])
            elif 'exShowroomPrice' in data:
                price_str = str(data['exShowroomPrice'])

            if price_str:
                # Normalize to float
                price = normalize_price(price_str)

                if price and 300000 <= price <= 15000000:  # Sanity check (3L - 1.5Cr)
                    print(f"   ✅ Extracted price: ₹{price:,.0f}")
                    return {
                        'ex_showroom_price': price,
                        'source': 'gemini_grounded_search'
                    }
                else:
                    print(f"   ⚠️ Price {price} outside valid range (3L-1.5Cr)")
            else:
                print(f"   ⚠️ No price field found in JSON: {data}")

        except json.JSONDecodeError as e:
            print(f"   ⚠️ JSON parse error: {e}")
            # Try to extract price from raw text as fallback
            price_match = re.search(r'(?:Rs\.?|₹)\s*([\d,\.]+)\s*(?:Lakh|L)', response_text, re.IGNORECASE)
            if price_match:
                price = normalize_price(price_match.group(0))
                if price and 300000 <= price <= 15000000:
                    print(f"   ✅ Extracted from text: ₹{price:,.0f}")
                    return {
                        'ex_showroom_price': price,
                        'source': 'gemini_grounded_search'
                    }

    except Exception as e:
        print(f"   ❌ Gemini API error: {e}")
        return None

    return None


class PriceFetcherGemini:
    """
    Price fetcher using Gemini API with Google Search grounding

    ONLY uses Gemini API - no fallbacks, no web scraping
    """

    def __init__(self):
        """Initialize Gemini-based price fetcher"""
        # No cache - always fetch fresh prices
        pass

    def get_current_price(self, make: str, model: str, variant: str = "",
                         fuel: str = "Petrol", year: int = None,
                         month: int = 3, transmission: str = "Manual") -> Dict:
        """
        Get current vehicle price using Gemini API - NO FALLBACKS

        Args:
            make: Vehicle manufacturer
            model: Model name
            variant: Variant/trim
            fuel: Fuel type
            year: Manufacturing year
            month: Manufacturing month (1-12)
            transmission: Transmission type

        Returns:
            Dictionary with ex_showroom_price and source

        Raises:
            ValueError: If API key not found
            ImportError: If google-genai not installed
        """
        from datetime import datetime

        if year is None:
            year = datetime.now().year

        print(f"🔍 Fetching live price using Gemini API for {make} {model} {variant} {fuel}...")

        # Use ONLY Gemini API - no fallbacks
        result = get_car_price_gemini(
            make=make,
            model=model,
            variant=variant,
            year=year,
            month=month,
            fuel_type=fuel,
            transmission=transmission,
            city="Hyderabad"
        )

        if result:
            return result

        # If Gemini returns None, return None (OBV engine will handle error)
        print("   ❌ Gemini API returned no valid price")
        raise ValueError(
            f"Failed to fetch price for {make} {model} {variant}. "
            "Gemini API did not return a valid price."
        )


# Create singleton instance
price_fetcher = PriceFetcherGemini()


# CLI test function
def test_price_fetcher():
    """Test the Gemini price fetcher interactively"""
    print("--- Gemini Price Fetcher Test ---\n")

    make = input("Make (e.g., Maruti Suzuki): ") or "Maruti Suzuki"
    model = input("Model (e.g., Swift): ") or "Swift"
    variant = input("Variant (e.g., LXI): ") or "LXI"
    year = int(input("Year (e.g., 2020): ") or "2020")
    month = int(input("Month (e.g., 3): ") or "3")
    fuel = input("Fuel Type (e.g., Petrol): ") or "Petrol"
    transmission = input("Transmission (e.g., Manual): ") or "Manual"

    print(f"\n{'='*60}")
    result = price_fetcher.get_current_price(
        make=make,
        model=model,
        variant=variant,
        fuel=fuel,
        year=year,
        month=month,
        transmission=transmission
    )

    print(f"{'='*60}\n")
    if result and result.get('ex_showroom_price'):
        price = result['ex_showroom_price']
        print(f"✅ Price Found: ₹{price:,.2f} ({price/100000:.2f} Lakhs)")
        print(f"   Source: {result['source']}")
    else:
        print("❌ No price found")


if __name__ == "__main__":
    test_price_fetcher()
