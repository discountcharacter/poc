import datetime
import requests
import re

# Brand Categories and Depreciation Rates (Assumed/Default values)
# These should be calibrated with the "Excel file" logic when available.
BRAND_CATEGORY = {
    "Maruti": "A", "Hyundai": "A", "Toyota": "A", "Honda": "A",
    "Tata": "B", "Mahindra": "B", "Kia": "B", 
    "Volkswagen": "C", "Skoda": "C", "Renault": "C", "Nissan": "C", "Jeep": "C",
    "Mercedes-Benz": "C", "BMW": "C", "Audi": "C"
}

DEPRECIATION_RATES = {
    "A": 0.10,  # 10% compounding
    "B": 0.12,  # 12% compounding
    "C": 0.15   # 15% compounding
}

# Segment Limits for KM Usage (Expected KM per year)
SEGMENT_KM_LIMIT = {
    "Entry Hatchback": 10000,
    "Compact SUV": 12000,
    "Mid-Size SUV": 15000,
    "Luxury": 10000,
    "Ultra-Luxury": 5000
}

# Base Prices (Approximation database - normally this would come from a DB)
# For POC, we will use a dictionary of base prices for 'New' models of today 
# to calculate depreciation backwards? Or just have a base reference price?
# Better: Assume user might know the "New Car Price" or we estimate it.
# PROMPT REQ: "Bifurcating all Models into Segments"
# Let's create a simple database of base model prices (Average Ex-Showroom)
BASE_PRICES = {
    "Maruti Swift": 900000,
    "Maruti Baleno": 1000000,
    "Hyundai Creta": 1500000, 
    "Kia Seltos": 1600000,
    "Toyota Fortuner": 4000000,
    "Honda City": 1400000,
    "Mahindra Thar": 1600000,
    "Tata Nexon": 1200000,
    "Tata Tigor": 850000,
    "Tata Tiago": 750000,
    "Tata Altroz": 950000,
    "Tata Punch": 900000,
    "BMW 3 Series": 5000000,
    "Mercedes-Benz C-Class": 5500000
}

SEGMENT_MAP = {
    "Maruti Swift": "Entry Hatchback",
    "Maruti Baleno": "Entry Hatchback",
    "Hyundai Creta": "Compact SUV",
    "Kia Seltos": "Compact SUV",
    "Toyota Fortuner": "Luxury",
    "Honda City": "Entry Hatchback",
    "Mahindra Thar": "Compact SUV",
    "Tata Nexon": "Compact SUV",
    "Tata Tigor": "Entry Hatchback",
    "Tata Tiago": "Entry Hatchback",
    "Tata Altroz": "Entry Hatchback",
    "Tata Punch": "Compact SUV",
    "BMW 3 Series": "Luxury",
    "Mercedes-Benz C-Class": "Luxury"
}

def get_base_price(make, model, variant):
    # Simplification: specific logic or DB lookup
    key = f"{make} {model}"
    return BASE_PRICES.get(key, 1000000) # Default fallback 10L

def get_segment(make, model):
    key = f"{make} {model}"
    return SEGMENT_MAP.get(key, "Compact SUV")

def get_real_base_price(make, model, variant, year, api_key, cx):
    """
    Attempts to find the original launch price/ex-showroom price of the specific model-year.
    Returns: (price: int|None, debug_info: str)
    """
    if not api_key or not cx:
        return None, "No API Key"
        
    queries = [
        f"launch price of {year} {make} {model} {variant} in India ex-showroom",
        f"{make} {model} {variant} {year} price new ex-showroom",
        f"{make} {model} {year} price India"
    ]
    
    debug_log = []
    
    url = "https://www.googleapis.com/customsearch/v1"
    
    for q in queries:
        params = {
            "key": api_key,
            "cx": cx,
            "q": q,
            "num": 3
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if "items" not in data:
                debug_log.append(f"Query '{q[:20]}...' returned 0 items.")
                continue
                
            price_pattern = re.compile(r"(\d+(\.\d+)?)\s*(?:Lakh|Lakhs|L)", re.IGNORECASE)
            
            for item in data["items"]:
                snippet = item.get("snippet", "") + " " + item.get("title", "")
                matches = price_pattern.findall(snippet)
                for match in matches:
                    try:
                        val = float(match[0])
                        # Launch prices usually 4L to 150L
                        # For 2024/2025 cars, we want the most recent higher price
                        if 4.0 < val < 150.0:
                            if year >= 2024 and val < 6.0: continue # Likely old base model price
                            return int(val * 100000), f"Found via query: '{q}'"
                    except:
                        continue
        except Exception as e:
            debug_log.append(f"API Error: {str(e)}")
            
    return None, "; ".join(debug_log) if debug_log else "Search yielded no valid price pattern."

def calculate_logic_price(make, model, year, variant, km, condition, owners, location, remarks="", api_key=None, cx=None):
    """
    Engine A: The Accountant
    Formula: Real Base Price (if found) -> Depreciation -> Usage Penalty -> Location/Owner/Condition -> Remarks -> Final
    Returns: (price, log_data)
    """
    log = []
    current_year = datetime.datetime.now().year
    age = current_year - year
    if age < 0: age = 0
    
    # 1. Base Price (Real vs Static)
    real_base, base_debug = get_real_base_price(make, model, variant, year, api_key, cx)
    
    if real_base:
        base_price = real_base
        log.append(f"**Real Base Price Found**: ₹ {base_price:,} ({base_debug})")
    else:
        base_price = get_base_price(make, model, variant)
        log.append(f"Base Price (Static Database): ₹ {base_price:,} (Real Search Failed: {base_debug})")
    
    # 2. Depreciation
    category = BRAND_CATEGORY.get(make, "B")
    rate = DEPRECIATION_RATES.get(category, 0.12)
    
    # Special Handling for Brand New Cars (2024/2025)
    if age == 0:
        depreciated_value = base_price * 0.95 # Only 5% drop if virtually new
        log.append(f"Near-New Car Bonus (2025): Only 5% initial drop: - ₹ {int(base_price - depreciated_value):,}")
    else:
        depreciated_value = base_price * ((1 - rate) ** age)
        log.append(f"Depreciation ({age} yrs @ {int(rate*100)}%): - ₹ {int(base_price - depreciated_value):,}")
    
    # 3. Usage Penalty
    segment = get_segment(make, model)
    limit_per_year = SEGMENT_KM_LIMIT.get(segment, 12000)
    expected_km = limit_per_year * age
    
    if km > expected_km:
        excess_km = km - expected_km
        penalty = excess_km * 2.0
        depreciated_value -= penalty
        log.append(f"High Mileage Penalty ({excess_km} km excess): - ₹ {int(penalty):,}")
    else:
        log.append(f"Mileage within limits ({km} km), no penalty.")
    
    # 4. Location Adjustment (Simple heuristic)
    loc_lower = location.lower()
    loc_factor = 1.0
    if any(c in loc_lower for c in ["bangalore", "bengaluru", "hyderabad", "chennai", "telangana", "karnataka"]):
        loc_factor = 1.05
        log.append(f"Location Premium ({location}): +5%")
    elif any(c in loc_lower for c in ["delhi", "ncr", "ht", "haryana"]):
        loc_factor = 0.95
        log.append(f"Location Discount ({location}): -5% (NCR Rules)")
    
    depreciated_value *= loc_factor
    
    # 5. Owner & Condition
    if owners == 2:
        depreciated_value *= 0.96
        log.append("2nd Owner Deduction: -4%")
    elif owners >= 3:
        depreciated_value *= 0.92
        log.append(f"{owners} Owners Deduction: -8%")
        
    condition_map = {"Excellent": 1.05, "Good": 1.00, "Fair": 0.90, "Poor": 0.80}
    c_factor = condition_map.get(condition, 1.0)
    depreciated_value *= c_factor
    if c_factor != 1.0:
        log.append(f"Condition Adjustment ({condition}): {int((c_factor-1)*100)}%")
        
    # 6. Remarks Analysis (Heuristic)
    remarks_lower = remarks.lower() if remarks else ""
    if remarks_lower:
        # Positive Attributes
        if "sunroof" in remarks_lower:
            depreciated_value *= 1.03
            log.append("Remark Bonus (Sunroof): +3%")
        if "alloy" in remarks_lower or "alloys" in remarks_lower:
            depreciated_value *= 1.02
            log.append("Remark Bonus (Alloy Wheels): +2%")
        if "service history" in remarks_lower or "records" in remarks_lower:
            depreciated_value *= 1.04
            log.append("Remark Bonus (Service Records): +4%")
        if "insurance" in remarks_lower and "valid" in remarks_lower:
            depreciated_value *= 1.01
            log.append("Remark Bonus (Valid Insurance): +1%")
            
        # Negative Attributes
        if "accident" in remarks_lower or "damage" in remarks_lower:
            depreciated_value *= 0.80
            log.append("Remark Penalty (Accident/Damage): -20%")
        if "rust" in remarks_lower:
            depreciated_value *= 0.90
            log.append("Remark Penalty (Rust): -10%")
        if "scratch" in remarks_lower or "dent" in remarks_lower:
            depreciated_value *= 0.97
            log.append("Remark Penalty (Scratches/Dents): -3%")
    
    final_price = max(int(depreciated_value), 0)
    log.append(f"**Final Logic Price**: ₹ {final_price:,}")
    
    return final_price, log
