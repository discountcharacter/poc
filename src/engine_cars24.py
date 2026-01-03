"""
Engine F: Cars24 Valuation Engine
Uses Playwright browser automation to get accurate valuations from Cars24.
"""

import os
import json
import re
from pathlib import Path
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except (ImportError, ModuleNotFoundError):
    # This will be handled in main.py, but we define placeholders to avoid name errors
    sync_playwright = None
    PlaywrightTimeout = Exception

# Session file location
SESSION_FILE = Path(__file__).parent.parent / ".cars24_session.json"

# Mapping for common brand names to Cars24 display names
BRAND_MAP = {
    "maruti": "Maruti Suzuki",
    "maruti suzuki": "Maruti Suzuki",
    "hyundai": "Hyundai",
    "honda": "Honda",
    "tata": "Tata",
    "mahindra": "Mahindra",
    "kia": "Kia",
    "toyota": "Toyota",
    "mg": "MG",
    "volkswagen": "Volkswagen",
    "skoda": "Skoda",
    "renault": "Renault",
    "nissan": "Nissan",
    "ford": "Ford",
    "bmw": "BMW",
    "mercedes": "Mercedes-Benz",
    "mercedes-benz": "Mercedes-Benz",
    "audi": "Audi",
    "jeep": "Jeep",
}

# State to RTO prefix mapping (common ones)
STATE_RTO_MAP = {
    "maharashtra": {"state": "Maharashtra", "rto_prefix": "MH"},
    "delhi": {"state": "Delhi", "rto_prefix": "DL"},
    "karnataka": {"state": "Karnataka", "rto_prefix": "KA"},
    "telangana": {"state": "Telangana", "rto_prefix": "TS"},
    "andhra pradesh": {"state": "Andhra Pradesh", "rto_prefix": "AP"},
    "tamil nadu": {"state": "Tamil Nadu", "rto_prefix": "TN"},
    "gujarat": {"state": "Gujarat", "rto_prefix": "GJ"},
    "rajasthan": {"state": "Rajasthan", "rto_prefix": "RJ"},
    "uttar pradesh": {"state": "Uttar Pradesh", "rto_prefix": "UP"},
    "west bengal": {"state": "West Bengal", "rto_prefix": "WB"},
    "kerala": {"state": "Kerala", "rto_prefix": "KL"},
    "punjab": {"state": "Punjab", "rto_prefix": "PB"},
    "haryana": {"state": "Haryana", "rto_prefix": "HR"},
}

# City to State mapping
CITY_STATE_MAP = {
    "mumbai": "maharashtra",
    "pune": "maharashtra",
    "delhi": "delhi",
    "noida": "uttar pradesh",
    "gurgaon": "haryana",
    "gurugram": "haryana",
    "bangalore": "karnataka",
    "bengaluru": "karnataka",
    "hyderabad": "telangana",
    "chennai": "tamil nadu",
    "kolkata": "west bengal",
    "ahmedabad": "gujarat",
    "jaipur": "rajasthan",
    "lucknow": "uttar pradesh",
    "kochi": "kerala",
    "chandigarh": "punjab",
}

def get_km_range(km):
    """Convert exact KM to Cars24 range format."""
    km = int(km)
    if km < 10000:
        return "0 - 10,000 km"
    elif km < 20000:
        return "10,000 - 20,000 km"
    elif km < 30000:
        return "20,000 - 30,000 km"
    elif km < 40000:
        return "30,000 - 40,000 km"
    elif km < 50000:
        return "40,000 - 50,000 km"
    elif km < 60000:
        return "50,000 - 60,000 km"
    elif km < 70000:
        return "60,000 - 70,000 km"
    elif km < 80000:
        return "70,000 - 80,000 km"
    elif km < 90000:
        return "80,000 - 90,000 km"
    elif km < 100000:
        return "90,000 - 1,00,000 km"
    else:
        return "More than 1,00,000 km"

def load_session():
    """Load saved session cookies."""
    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def save_session(cookies):
    """Save session cookies for future use."""
    with open(SESSION_FILE, 'w') as f:
        json.dump(cookies, f)
    print(f"Cars24 session saved to {SESSION_FILE}")

def session_exists():
    """Check if a valid session file exists."""
    return SESSION_FILE.exists()

def get_cars24_price(make, model, year, variant, fuel, transmission, km, city):
    """
    Main function to get Cars24 valuation.
    
    Args:
        make: Car brand (e.g., "Maruti", "Hyundai")
        model: Car model (e.g., "Swift", "Creta")
        year: Manufacturing year (e.g., 2020)
        variant: Variant name (e.g., "VXI", "SX")
        fuel: Fuel type ("Petrol", "Diesel", "CNG")
        transmission: "Manual" or "Automatic"
        km: Kilometers driven
        city: City name (e.g., "Mumbai")
    
    Returns:
        tuple: (price, debug_info)
    """
    debug_log = []
    
    # Normalize inputs
    make_normalized = BRAND_MAP.get(make.lower().strip(), make)
    city_lower = city.lower().strip()
    state_key = CITY_STATE_MAP.get(city_lower, "maharashtra")
    state_info = STATE_RTO_MAP.get(state_key, STATE_RTO_MAP["maharashtra"])
    km_range = get_km_range(km)
    
    debug_log.append(f"Searching Cars24 for: {year} {make_normalized} {model} {variant}")
    debug_log.append(f"Location: {city} ({state_info['state']})")
    
    # Check for saved session
    saved_session = load_session()
    if not saved_session:
        debug_log.append("No saved session found. Run setup_cars24_session.py first.")
        return None, "\n".join(debug_log)
    
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-gpu',
                        '--disable-dev-shm-usage',
                        '--disable-setuid-sandbox',
                        '--no-first-run',
                        '--no-zygote',
                        '--single-process'
                    ]
                )
            except Exception as e:
                debug_log.append(f"Playwright Launch Failed: {e}")
                return None, "\n".join(debug_log)
                
            context = browser.new_context()
            
            # Load saved cookies
            context.add_cookies(saved_session)
            debug_log.append("Loaded saved session cookies")
            
            page = context.new_page()
            page.set_default_timeout(15000)  # 15 second timeout
            
            # Navigate to sell page
            page.goto("https://www.cars24.com/sell-used-cars", wait_until="networkidle")
            debug_log.append("Navigated to Cars24")
            
            # Click "Start with your car brand"
            try:
                page.click("text=Start with your car brand", timeout=5000)
            except:
                # Try alternative selector
                page.click("button:has-text('brand')", timeout=5000)
            
            # Step 1: Select Brand
            try:
                page.click(f"text={make_normalized}", timeout=5000)
                debug_log.append(f"Selected brand: {make_normalized}")
            except:
                debug_log.append(f"Could not find brand: {make_normalized}")
                browser.close()
                return None, "\n".join(debug_log)
            
            # Step 2: Select Year
            try:
                # Try to use search box if available
                year_input = page.query_selector("input[placeholder*='year' i], input[placeholder*='search' i]")
                if year_input:
                    year_input.fill(str(year))
                    page.wait_for_timeout(500)
                page.click(f"text={year}", timeout=5000)
                debug_log.append(f"Selected year: {year}")
            except:
                debug_log.append(f"Could not find year: {year}")
                browser.close()
                return None, "\n".join(debug_log)
            
            # Step 3: Select Model
            try:
                page.click(f"text={model}", timeout=5000)
                debug_log.append(f"Selected model: {model}")
            except:
                debug_log.append(f"Could not find model: {model}")
                browser.close()
                return None, "\n".join(debug_log)
            
            # Step 4: Select Fuel Type
            try:
                page.click(f"text={fuel}", timeout=5000)
                debug_log.append(f"Selected fuel: {fuel}")
            except:
                debug_log.append(f"Could not find fuel type: {fuel}")
                browser.close()
                return None, "\n".join(debug_log)
            
            # Step 5: Select Transmission
            try:
                page.click(f"text={transmission}", timeout=5000)
                debug_log.append(f"Selected transmission: {transmission}")
            except:
                debug_log.append(f"Could not find transmission: {transmission}")
                browser.close()
                return None, "\n".join(debug_log)
            
            # Step 6: Select Variant (fuzzy match)
            try:
                # Try exact match first
                variant_btn = page.query_selector(f"button:has-text('{variant}')")
                if variant_btn:
                    variant_btn.click()
                else:
                    # Try partial match - click first available variant
                    page.click("button:visible", timeout=5000)
                debug_log.append(f"Selected variant: {variant}")
            except:
                debug_log.append(f"Could not find variant: {variant}, using first available")
            
            # Step 7: Select State
            try:
                page.click(f"text={state_info['state']}", timeout=5000)
                debug_log.append(f"Selected state: {state_info['state']}")
            except:
                debug_log.append(f"Could not find state: {state_info['state']}")
                browser.close()
                return None, "\n".join(debug_log)
            
            # Step 8: Select RTO (first one for the state)
            try:
                rto_prefix = state_info['rto_prefix']
                page.click(f"text={rto_prefix}-01", timeout=3000)
                debug_log.append(f"Selected RTO: {rto_prefix}-01")
            except:
                # Try clicking first visible RTO button
                try:
                    page.click(f"button:has-text('{rto_prefix}')", timeout=3000)
                except:
                    debug_log.append("Using default RTO")
            
            # Step 9: Select KM Range
            try:
                # Try to find matching range
                page.click(f"text={km_range[:10]}", timeout=5000)  # Match first part
                debug_log.append(f"Selected KM: {km_range}")
            except:
                debug_log.append("Could not select exact KM range")
            
            # Step 10: Select City
            try:
                page.click(f"text={city}", timeout=5000)
                debug_log.append(f"Selected city: {city}")
            except:
                debug_log.append(f"Could not find city: {city}")
            
            # Step 11: Select Intent
            try:
                page.click("text=Just checking price", timeout=5000)
                debug_log.append("Selected intent: Just checking price")
            except:
                pass
            
            # Wait for price to appear
            page.wait_for_timeout(3000)
            
            # Try to extract price from result page
            price = None
            try:
                # Look for price elements
                price_selectors = [
                    ".price-value",
                    "[class*='price']",
                    "text=/₹\s*[\d,]+/",
                    "[data-testid*='price']"
                ]
                
                for selector in price_selectors:
                    try:
                        element = page.query_selector(selector)
                        if element:
                            text = element.text_content()
                            # Extract number from text
                            numbers = re.findall(r"[\d,]+", text)
                            if numbers:
                                price_str = numbers[0].replace(",", "")
                                if len(price_str) >= 5:  # At least 5 digits (10000+)
                                    price = int(price_str)
                                    debug_log.append(f"Found price: ₹{price:,}")
                                    break
                    except:
                        continue
                
                if not price:
                    # Check if we're on login page (session expired)
                    if page.query_selector("input[type='tel']"):
                        debug_log.append("Session expired. Please run setup_cars24_session.py again.")
                    else:
                        debug_log.append("Could not extract price from page")
                        # Take screenshot for debugging
                        page.screenshot(path="/tmp/cars24_debug.png")
                        
            except Exception as e:
                debug_log.append(f"Error extracting price: {str(e)}")
            
            browser.close()
            return price, "\n".join(debug_log)
            
    except PlaywrightTimeout as e:
        debug_log.append(f"Timeout error: {str(e)}")
        return None, "\n".join(debug_log)
    except Exception as e:
        debug_log.append(f"Error: {str(e)}")
        return None, "\n".join(debug_log)


# For testing
if __name__ == "__main__":
    price, debug = get_cars24_price(
        make="Maruti",
        model="Swift",
        year=2020,
        variant="VXI",
        fuel="Petrol",
        transmission="Manual",
        km=50000,
        city="Mumbai"
    )
    print(f"Price: {price}")
    print(f"Debug: {debug}")
