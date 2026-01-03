import re
from datetime import datetime

class ProcurementAlgo:
    """
    Implements the Actuarial Depreciation Logic for Vehicle Procurement.
    Based on User-Provided Tables for Depreciation, KM Limits, and Condition Penalties.
    """
    
    # Segment Definitions & Limits (Expected KM/Year, Depreciation ₹/km)
    SEGMENTS = {
        "Entry Hatchback": {"km_limit": 12500, "km_dep": 1.75}, # Alto, Kwid, Eon
        "Premium Hatchback": {"km_limit": 12500, "km_dep": 2.00}, # Swift, Baleno, i20
        "Sedan": {"km_limit": 12500, "km_dep": 2.25}, # City, Verna, Ciaz
        "Compact SUV": {"km_limit": 10000, "km_dep": 2.75}, # Brezza, Venue, Nexon
        "Mid-Size SUV": {"km_limit": 10000, "km_dep": 3.00}, # Creta, Seltos
        "Full-Size SUV": {"km_limit": 10000, "km_dep": 3.25}, # Harrier, XUV700, Hector
        "Luxury": {"km_limit": 8000, "km_dep": 4.00}, # Merc, BMW
        "Ultra-Luxury": {"km_limit": 6000, "km_dep": 5.50}
    }

    # Manual Mapping of Models to Segments
    MODEL_MAP = {
        "alto": "Entry Hatchback", "kwid": "Entry Hatchback", "eon": "Entry Hatchback", "santro": "Entry Hatchback", 
        "celerio": "Entry Hatchback", "wagon r": "Entry Hatchback", "tiago": "Entry Hatchback", "ignis": "Entry Hatchback",
        "swift": "Premium Hatchback", "baleno": "Premium Hatchback", "i20": "Premium Hatchback", "altroz": "Premium Hatchback", 
        "polo": "Premium Hatchback", "glanza": "Premium Hatchback", "micra": "Premium Hatchback", "grand i10": "Premium Hatchback", "i10": "Premium Hatchback",
        "city": "Sedan", "verna": "Sedan", "ciaz": "Sedan", "rapid": "Sedan", "vento": "Sedan", "amaze": "Sedan", "dzire": "Sedan", "etios": "Sedan", "aura": "Sedan", "tigore": "Sedan", 
        "brezza": "Compact SUV", "venue": "Compact SUV", "nexon": "Compact SUV", "sonet": "Compact SUV", "xuv300": "Compact SUV", "magnite": "Compact SUV", "kiger": "Compact SUV", "ecosport": "Compact SUV", "wr-v": "Compact SUV", "punch": "Compact SUV", "exter": "Compact SUV",
        "creta": "Mid-Size SUV", "seltos": "Mid-Size SUV", "astor": "Mid-Size SUV", "kushaq": "Mid-Size SUV", "taigun": "Mid-Size SUV", "grand vitara": "Mid-Size SUV", "hyryder": "Mid-Size SUV", "thar": "Mid-Size SUV", "scorpio": "Mid-Size SUV", "duster": "Mid-Size SUV",
        "harrier": "Full-Size SUV", "safari": "Full-Size SUV", "hector": "Full-Size SUV", "xuv700": "Full-Size SUV", "innova": "Full-Size SUV", "fortuner": "Full-Size SUV", "gloster": "Full-Size SUV", "compass": "Full-Size SUV", "tuv 300": "Full-Size SUV",
        "mercedes": "Luxury", "bmw": "Luxury", "audi": "Luxury"
    }

    @staticmethod
    def get_segment(model_name):
        model_lower = model_name.lower().strip()
        for key, segment in ProcurementAlgo.MODEL_MAP.items():
            if key in model_lower:
                return segment
        # Default fallback
        if "suv" in model_lower: return "Mid-Size SUV"
        return "Premium Hatchback" # Safe default

    @staticmethod
    def calculate_procurement_price(market_price, make, model, year, km, owners, condition):
        """
        Calculates the Procurement Price (Buying Price) from the Market Retail Price.
        Logic:
        1. Base Procurement Price = Market Price * Margin (0.80 for Trade, 0.70 for Buy)
        2. Apply Excess KM Penalty
        3. Apply Owner Penalty
        4. Apply Condition Penalty
        """
        segment_name = ProcurementAlgo.get_segment(model)
        segment_data = ProcurementAlgo.SEGMENTS.get(segment_name, ProcurementAlgo.SEGMENTS["Premium Hatchback"])
        
        # 1. Base Margin Integration (Dynamic based on Age)
        # New cars (0-2 yrs) retain high % of retail value (80%).
        # Mid-age cars (3-5 yrs) retain moderate % (70%).
        # Old cars (6+ yrs) follow standard depreciation (65%).
        current_year = datetime.now().year
        age = max(1, current_year - int(year))
        
        if age <= 2:
            base_factor = 0.80
        elif age <= 5:
            base_factor = 0.70
        else:
            base_factor = 0.65
            
        base_procurement = market_price * base_factor
        
        # 2. Age & KM Calculations
        # re-use age variable
        
        expected_km = age * segment_data["km_limit"]
        actual_km = int(km) if km else expected_km
        
        # Excess KM Penalty
        extra_km = max(0, actual_km - expected_km)
        km_penalty = extra_km * segment_data["km_dep"]
        
        # Low KM Appreciation (Bonus)
        # If car has run LESS than expected, dealers pay a premium.
        # We apply a conservative bonus: 30% of the depreciation rate for every saved km.
        saved_km = max(0, expected_km - actual_km)
        km_bonus = saved_km * (segment_data["km_dep"] * 0.30)
        
        # 3. Ownership Depreciation
        # 2nd Owner: -2% of Base
        # 3rd Owner: -4% of Base
        owner_count = int(owners) if owners else 1
        owner_penalty_pct = 0
        if owner_count == 2: owner_penalty_pct = 0.02
        elif owner_count >= 3: owner_penalty_pct = 0.04
        
        owner_penalty = base_procurement * owner_penalty_pct
        
        # 4. Condition Price Impact
        # Good: -1.5%, Fair: -3%, Poor: -6%
        cond_map = {"Excellent": 0, "Good": 0.015, "Fair": 0.03, "Poor": 0.06}
        cond_penalty_pct = cond_map.get(condition, 0)
        
        cond_penalty = base_procurement * cond_penalty_pct
        
        # Final Calculation
        # Base - Penalties + Bonus
        final_price = base_procurement + km_bonus - km_penalty - owner_penalty - cond_penalty
        
        km_msg = ""
        if extra_km > 0:
            km_msg += f"Extra KM: {extra_km} @ ₹{segment_data['km_dep']}/km"
        if saved_km > 0:
            if km_msg: km_msg += " | "
            km_msg += f"Low KM Bonus: {saved_km} km (Credit ₹{int(km_bonus)})"
        
        # Floor price at Scrap Value (approx 25k) to prevent negative results
        final_price = max(25000, final_price)
        
        return {
            "market_price": market_price,
            "base_procurement": int(base_procurement),
            "segment": segment_name,
            "penalties": {
                "km_penalty": int(km_penalty),
                "owner_penalty": int(owner_penalty),
                "cond_penalty": int(cond_penalty),
                "km_bonus": int(km_bonus)
            },
            "final_procurement_price": int(final_price),
            "details": f"Segment: {segment_name} | Expected KM: {expected_km} | {km_msg}"
        }

if __name__ == "__main__":
    # Test Case: Wagon R 2019 (User Example)
    # Market: ~5.35L. User Paid: 3.45L. KM: 18k.
    res = ProcurementAlgo.calculate_procurement_price(535000, "Maruti", "Wagon R", 2019, 18537, 1, "Good")
    print(res)
