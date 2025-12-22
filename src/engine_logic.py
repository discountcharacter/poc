import datetime
import requests
import re

# Brand Categories and Depreciation Rates (Calibrated for Indian Resale Market)
BRAND_CATEGORY = {
    "Maruti": "A+", "Hyundai": "A", "Toyota": "A+", "Honda": "A",
    "Tata": "B", "Mahindra": "B", "Kia": "B", 
    "Volkswagen": "C", "Skoda": "C", "Renault": "C", "Nissan": "C",
    "Mercedes-Benz": "C", "BMW": "C", "Audi": "C"
}

DEPRECIATION_RATES = {
    "A+": 0.08, # 8% (Maruti, Toyota - Ultra High Resale)
    "A": 0.10,  # 10% (Hyundai, Honda)
    "B": 0.14,  # 14% (Tata, Mahindra)
    "C": 0.18   # 18% (Luxury / High Maintenance)
}

# Segment Limits for KM Usage (Expected KM per year)
SEGMENT_KM_LIMIT = {
    "Entry Hatchback": 12000,
    "Compact SUV": 12000,
    "Mid-Size SUV": 15000,
    "Luxury": 10000
}

BASE_PRICES = {
    "Maruti Swift": 850000,
    "Maruti Baleno": 950000,
    "Hyundai Creta": 1600000, 
    "Kia Seltos": 1700000,
    "Toyota Fortuner": 4500000,
    "Honda City": 1500000,
    "Mahindra Thar": 1600000,
    "Tata Nexon": 1300000,
    "BMW 3 Series": 6500000
}

SEGMENT_MAP = {
    "Maruti Swift": "Entry Hatchback",
    "Maruti Baleno": "Entry Hatchback",
    "Hyundai Creta": "Compact SUV",
    "Kia Seltos": "Compact SUV",
    "Toyota Fortuner": "Mid-Size SUV",
    "Honda City": "Entry Hatchback",
    "Mahindra Thar": "Compact SUV",
    "Tata Nexon": "Compact SUV",
    "BMW 3 Series": "Luxury"
}

def get_base_price(make, model, variant):
    key = f"{make} {model}"
    return BASE_PRICES.get(key, 1000000)

def get_segment(make, model):
    key = f"{make} {model}"
    return SEGMENT_MAP.get(key, "Compact SUV")

def get_real_base_price(make, model, variant, year, api_key, cx):
    if not api_key or not cx:
        return None, "No API Key"
        
    queries = [
        f"launch price of {year} {make} {model} {variant} ex-showroom India",
        f"{make} {model} {year} new car price India"
    ]
    
    url = "https://www.googleapis.com/customsearch/v1"
    for q in queries:
        try:
            params = {"key": api_key, "cx": cx, "q": q, "num": 3}
            response = requests.get(url, params=params)
            data = response.json()
            if "items" not in data: continue
                
            price_pattern = re.compile(r"(\d+(\.\d+)?)\s*(?:Lakh|Lakhs|L)", re.IGNORECASE)
            for item in data["items"]:
                snippet = item.get("snippet", "") + " " + item.get("title", "")
                matches = price_pattern.findall(snippet)
                for match in matches:
                    val = float(match[0])
                    # Higher constraint to avoid matching 'used' prices
                    if 4.5 < val < 200.0:
                        return int(val * 100000), f"Found via Search"
        except: continue
    return None, "Search failed"

def calculate_logic_price(make, model, year, variant, km, condition, owners, location, remarks="", api_key=None, cx=None):
    log = []
    current_year = 2024
    age = current_year - year
    if age < 0: age = 0
    
    real_base, _ = get_real_base_price(make, model, variant, year, api_key, cx)
    base_price = real_base if real_base else get_base_price(make, model, variant)
    log.append(f"Base Reference: ₹ {base_price:,}")

    # 2. Depreciation
    category = BRAND_CATEGORY.get(make, "B")
    rate = DEPRECIATION_RATES.get(category, 0.12)
    
    depreciated_value = base_price * ((1 - rate) ** age)
    log.append(f"Depreciation ({age} yrs @ {int(rate*100)}%): - ₹ {int(base_price - depreciated_value):,}")
    
    # Maruti Bonus
    if make.lower() == "maruti":
        depreciated_value *= 1.05
        log.append("Maruti Market Resale Bonus: +5%")

    # 3. Usage Penalty (Less aggressive)
    segment = get_segment(make, model)
    limit = SEGMENT_KM_LIMIT.get(segment, 12000)
    expected_km = limit * age
    if km > expected_km:
        penalty = (km - expected_km) * 1.5
        depreciated_value -= penalty
        log.append(f"Usage Penalty: - ₹ {int(penalty):,}")
    
    # 4. Condition
    condition_map = {"Excellent": 1.05, "Good": 1.00, "Fair": 0.90, "Poor": 0.80}
    c_factor = condition_map.get(condition, 1.0)
    depreciated_value *= c_factor
    
    # 5. Owners
    if owners > 1:
        o_penalty = 0.05 * (owners - 1)
        depreciated_value *= (1 - o_penalty)
        log.append(f"Owner Penalty ({owners} owners): -{int(o_penalty*100)}%")

    final_price = max(int(depreciated_value), 0)
    log.append(f"**Final Logic Estimate**: ₹ {final_price:,}")
    
    return final_price, log
