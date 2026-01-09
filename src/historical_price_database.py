"""
Historical Vehicle Price Database & On-Road Calculator
======================================================
This module handles:
1. Historical ex-showroom prices for vehicles (2015-2025)
2. On-road price calculation using year-specific tax rates
3. Market sentiment adjustments

KEY INSIGHT from Droom CEO:
OBV uses ORIGINAL on-road price (when car was purchased), NOT current price.
This represents the actual amount paid by the owner.
"""

from datetime import date
from typing import Dict, Optional, Tuple
from enum import Enum


class MarketSentiment(Enum):
    """Market demand/supply dynamics"""
    HIGH_DEMAND = "High Demand"  # Popular models, holds value
    NORMAL = "Normal Market"
    LOW_DEMAND = "Low Demand"  # Discontinued/unpopular
    DECLINING = "Declining"  # Being phased out


# ==========================================
# HISTORICAL EX-SHOWROOM PRICES DATABASE
# ==========================================
# Format: {model_key: {year: {variant: price}}}
# This is a curated database of popular models
# For production, this should be in a proper database

HISTORICAL_PRICES = {
    # Maruti Swift (2015-2025)
    'maruti_swift': {
        2015: {'lxi': 445000, 'vxi': 525000, 'zxi': 595000},
        2016: {'lxi': 455000, 'vxi': 535000, 'zxi': 605000},
        2017: {'lxi': 465000, 'vxi': 545000, 'zxi': 615000},
        2018: {'lxi': 495000, 'vxi': 575000, 'zxi': 645000},  # New generation
        2019: {'lxi': 510000, 'vxi': 590000, 'zxi': 660000},
        2020: {'lxi': 525000, 'vxi': 605000, 'zxi': 675000},
        2021: {'lxi': 545000, 'vxi': 625000, 'zxi': 695000},
        2022: {'lxi': 570000, 'vxi': 650000, 'zxi': 720000},
        2023: {'lxi': 595000, 'vxi': 675000, 'zxi': 745000},
        2024: {'lxi': 620000, 'vxi': 700000, 'zxi': 770000},
        2025: {'lxi': 640000, 'vxi': 720000, 'zxi': 790000},
    },

    # Hyundai i20 (2015-2025)
    'hyundai_i20': {
        2015: {'magna': 550000, 'sportz': 650000, 'asta': 750000},
        2016: {'magna': 565000, 'sportz': 665000, 'asta': 765000},
        2017: {'magna': 580000, 'sportz': 680000, 'asta': 780000},
        2018: {'magna': 595000, 'sportz': 695000, 'asta': 795000},
        2019: {'magna': 610000, 'sportz': 710000, 'asta': 810000},
        2020: {'magna': 700000, 'sportz': 800000, 'asta': 900000},  # New generation
        2021: {'magna': 720000, 'sportz': 820000, 'asta': 920000},
        2022: {'magna': 745000, 'sportz': 845000, 'asta': 945000},
        2023: {'magna': 770000, 'sportz': 870000, 'asta': 970000},
        2024: {'magna': 795000, 'sportz': 895000, 'asta': 995000},
        2025: {'magna': 820000, 'sportz': 920000, 'asta': 1020000},
    },

    # Hyundai Creta (2015-2025)
    'hyundai_creta': {
        2015: {'e': 925000, 's': 1125000, 'sx': 1325000},
        2016: {'e': 950000, 's': 1150000, 'sx': 1350000},
        2017: {'e': 975000, 's': 1175000, 'sx': 1375000},
        2018: {'e': 1000000, 's': 1200000, 'sx': 1400000},
        2019: {'e': 1025000, 's': 1225000, 'sx': 1425000},
        2020: {'e': 1050000, 's': 1250000, 'sx': 1450000, 'sx(o)': 1550000},  # New gen
        2021: {'e': 1080000, 's': 1280000, 'sx': 1480000, 'sx(o)': 1580000},
        2022: {'e': 1115000, 's': 1315000, 'sx': 1515000, 'sx(o)': 1615000},
        2023: {'e': 1150000, 's': 1350000, 'sx': 1550000, 'sx(o)': 1650000},
        2024: {'e': 1185000, 's': 1385000, 'sx': 1585000, 'sx(o)': 1685000},
        2025: {'e': 1220000, 's': 1420000, 'sx': 1620000, 'sx(o)': 1720000},
    },

    # Maruti Baleno (2015-2025)
    'maruti_baleno': {
        2015: {'sigma': 505000, 'delta': 605000, 'zeta': 685000, 'alpha': 755000},
        2016: {'sigma': 520000, 'delta': 620000, 'zeta': 700000, 'alpha': 770000},
        2017: {'sigma': 535000, 'delta': 635000, 'zeta': 715000, 'alpha': 785000},
        2018: {'sigma': 550000, 'delta': 650000, 'zeta': 730000, 'alpha': 800000},
        2019: {'sigma': 570000, 'delta': 670000, 'zeta': 750000, 'alpha': 820000},
        2020: {'sigma': 590000, 'delta': 690000, 'zeta': 770000, 'alpha': 840000},
        2021: {'sigma': 610000, 'delta': 710000, 'zeta': 790000, 'alpha': 860000},
        2022: {'sigma': 635000, 'delta': 735000, 'zeta': 815000, 'alpha': 885000},
        2023: {'sigma': 660000, 'delta': 760000, 'zeta': 840000, 'alpha': 910000},
        2024: {'sigma': 685000, 'delta': 785000, 'zeta': 865000, 'alpha': 935000},
        2025: {'sigma': 710000, 'delta': 810000, 'zeta': 890000, 'alpha': 960000},
    },

    # Honda City (2015-2025)
    'honda_city': {
        2015: {'s': 845000, 'sv': 945000, 'v': 1045000, 'vx': 1145000},
        2016: {'s': 865000, 'sv': 965000, 'v': 1065000, 'vx': 1165000},
        2017: {'s': 885000, 'sv': 985000, 'v': 1085000, 'vx': 1185000},
        2018: {'s': 905000, 'sv': 1005000, 'v': 1105000, 'vx': 1205000},
        2019: {'s': 925000, 'sv': 1025000, 'v': 1125000, 'vx': 1225000},
        2020: {'s': 945000, 'sv': 1045000, 'v': 1145000, 'vx': 1245000, 'zx': 1345000},  # New gen
        2021: {'s': 1000000, 'sv': 1100000, 'v': 1200000, 'vx': 1300000, 'zx': 1400000},
        2022: {'s': 1030000, 'sv': 1130000, 'v': 1230000, 'vx': 1330000, 'zx': 1430000},
        2023: {'s': 1065000, 'sv': 1165000, 'v': 1265000, 'vx': 1365000, 'zx': 1465000},
        2024: {'s': 1100000, 'sv': 1200000, 'v': 1300000, 'vx': 1400000, 'zx': 1500000},
        2025: {'s': 1135000, 'sv': 1235000, 'v': 1335000, 'vx': 1435000, 'zx': 1535000},
    },

    # Add more models as needed...
}


# ==========================================
# ON-ROAD PRICE CALCULATION
# ==========================================
# State-specific tax rates (Telangana/Hyderabad)

TELANGANA_TAX_RATES = {
    # Lifetime road tax rates (changed in 2018)
    2015: {'rate': 0.12, 'type': 'lifetime'},  # 12% of vehicle cost
    2016: {'rate': 0.12, 'type': 'lifetime'},
    2017: {'rate': 0.12, 'type': 'lifetime'},
    2018: {'rate': 0.14, 'type': 'lifetime'},  # Increased to 14%
    2019: {'rate': 0.14, 'type': 'lifetime'},
    2020: {'rate': 0.14, 'type': 'lifetime'},
    2021: {'rate': 0.125, 'type': 'lifetime'},  # Reduced during COVID
    2022: {'rate': 0.125, 'type': 'lifetime'},
    2023: {'rate': 0.125, 'type': 'lifetime'},
    2024: {'rate': 0.125, 'type': 'lifetime'},
    2025: {'rate': 0.125, 'type': 'lifetime'},
}

# Fixed charges (year-specific)
REGISTRATION_CHARGES = {
    2015: {'registration': 600, 'smart_card': 300, 'cess': 200, 'other': 500},
    2016: {'registration': 600, 'smart_card': 300, 'cess': 200, 'other': 500},
    2017: {'registration': 800, 'smart_card': 400, 'cess': 300, 'other': 600},
    2018: {'registration': 1000, 'smart_card': 500, 'cess': 300, 'other': 700},
    2019: {'registration': 1000, 'smart_card': 500, 'cess': 300, 'other': 700},
    2020: {'registration': 1200, 'smart_card': 600, 'cess': 400, 'other': 800},
    2021: {'registration': 1200, 'smart_card': 600, 'cess': 400, 'other': 800},
    2022: {'registration': 1500, 'smart_card': 700, 'cess': 500, 'other': 1000},
    2023: {'registration': 1500, 'smart_card': 700, 'cess': 500, 'other': 1000},
    2024: {'registration': 1800, 'smart_card': 800, 'cess': 600, 'other': 1200},
    2025: {'registration': 2000, 'smart_card': 900, 'cess': 700, 'other': 1400},
}

# Insurance costs (approximate, varies by vehicle value)
def estimate_insurance_cost(ex_showroom_price: float, year: int) -> float:
    """
    Estimate insurance cost based on vehicle value

    Comprehensive insurance is typically 3-5% of vehicle value for first year
    """
    if ex_showroom_price < 500000:
        rate = 0.04  # 4% for lower value cars
    elif ex_showroom_price < 1000000:
        rate = 0.035  # 3.5% for mid-range
    else:
        rate = 0.03  # 3% for premium cars

    # Adjust for year (insurance has become more expensive)
    year_factor = 1.0 + (year - 2015) * 0.02  # 2% increase per year

    return ex_showroom_price * rate * year_factor


def calculate_on_road_price(ex_showroom: float, year: int, state: str = "telangana") -> Tuple[float, Dict[str, float]]:
    """
    Calculate on-road price from ex-showroom price for a specific year

    Args:
        ex_showroom: Ex-showroom price
        year: Year of purchase
        state: State name (default: telangana)

    Returns:
        Tuple of (on_road_price, breakdown_dict)
    """
    breakdown = {}
    breakdown['ex_showroom'] = ex_showroom

    # Road tax (state-specific)
    if state.lower() == "telangana":
        tax_info = TELANGANA_TAX_RATES.get(year, TELANGANA_TAX_RATES[2025])
        road_tax = ex_showroom * tax_info['rate']
        breakdown['road_tax'] = road_tax
        breakdown['road_tax_rate'] = f"{tax_info['rate']*100}%"
    else:
        # Default to 12% for other states
        road_tax = ex_showroom * 0.12
        breakdown['road_tax'] = road_tax

    # Registration and other charges
    reg_charges = REGISTRATION_CHARGES.get(year, REGISTRATION_CHARGES[2025])
    breakdown['registration'] = reg_charges['registration']
    breakdown['smart_card'] = reg_charges['smart_card']
    breakdown['cess'] = reg_charges['cess']
    breakdown['other_charges'] = reg_charges['other']

    # Insurance
    insurance = estimate_insurance_cost(ex_showroom, year)
    breakdown['insurance'] = insurance

    # Total on-road price
    on_road = (
        ex_showroom +
        road_tax +
        reg_charges['registration'] +
        reg_charges['smart_card'] +
        reg_charges['cess'] +
        reg_charges['other'] +
        insurance
    )

    breakdown['total_on_road'] = on_road

    return on_road, breakdown


# ==========================================
# MARKET SENTIMENT DATABASE
# ==========================================

MARKET_SENTIMENT_DB = {
    # High demand models (retain value better)
    'maruti_swift': MarketSentiment.HIGH_DEMAND,
    'maruti_baleno': MarketSentiment.HIGH_DEMAND,
    'hyundai_creta': MarketSentiment.HIGH_DEMAND,
    'hyundai_i20': MarketSentiment.HIGH_DEMAND,
    'maruti_wagon_r': MarketSentiment.HIGH_DEMAND,
    'maruti_dzire': MarketSentiment.HIGH_DEMAND,
    'honda_city': MarketSentiment.NORMAL,
    'hyundai_venue': MarketSentiment.HIGH_DEMAND,
    'kia_seltos': MarketSentiment.HIGH_DEMAND,
    'tata_nexon': MarketSentiment.HIGH_DEMAND,

    # Discontinued/declining models (lose value faster)
    'ford_ecosport': MarketSentiment.DECLINING,  # Ford exited India
    'chevrolet_beat': MarketSentiment.LOW_DEMAND,  # Chevrolet exited
    'fiat_punto': MarketSentiment.LOW_DEMAND,  # Fiat exited
    'nissan_micra': MarketSentiment.DECLINING,
    'renault_kwid': MarketSentiment.NORMAL,
}

# Market sentiment multipliers for valuation
SENTIMENT_MULTIPLIERS = {
    MarketSentiment.HIGH_DEMAND: 1.05,  # +5% premium
    MarketSentiment.NORMAL: 1.00,  # Baseline
    MarketSentiment.LOW_DEMAND: 0.92,  # -8% penalty
    MarketSentiment.DECLINING: 0.85,  # -15% penalty
}


def get_market_sentiment(make: str, model: str) -> Tuple[MarketSentiment, float]:
    """
    Get market sentiment for a vehicle and its multiplier

    Args:
        make: Manufacturer
        model: Model name

    Returns:
        Tuple of (sentiment, multiplier)
    """
    model_key = f"{make.lower().replace(' ', '_')}_{model.lower().replace(' ', '_')}"
    sentiment = MARKET_SENTIMENT_DB.get(model_key, MarketSentiment.NORMAL)
    multiplier = SENTIMENT_MULTIPLIERS[sentiment]

    return sentiment, multiplier


# ==========================================
# HISTORICAL PRICE LOOKUP
# ==========================================

def get_historical_ex_showroom_price(make: str, model: str, variant: str, year: int) -> Optional[float]:
    """
    Get historical ex-showroom price for a specific vehicle and year

    Args:
        make: Manufacturer
        model: Model name
        variant: Variant name
        year: Year of purchase

    Returns:
        Ex-showroom price or None if not found
    """
    model_key = f"{make.lower().replace(' ', '_')}_{model.lower().replace(' ', '_')}"
    variant_key = variant.lower().strip()

    # Handle variant name variations (LXi, LXI, lxi all match)
    variant_key = variant_key.replace('i', '').replace('I', '').lower()

    if model_key in HISTORICAL_PRICES:
        year_data = HISTORICAL_PRICES[model_key].get(year)
        if year_data:
            # Try exact match first
            for var_name, price in year_data.items():
                if variant_key in var_name.lower():
                    return price

    return None


def get_historical_on_road_price(make: str, model: str, variant: str, year: int,
                                 month: int = 3, state: str = "telangana") -> Optional[Tuple[float, Dict]]:
    """
    Get complete historical on-road price with breakdown

    This is the KEY function for OBV - get the ORIGINAL price paid by owner

    Args:
        make: Manufacturer
        model: Model name
        variant: Variant name
        year: Year of purchase
        month: Month of purchase (for future enhancement)
        state: State of registration

    Returns:
        Tuple of (on_road_price, breakdown_dict) or None
    """
    # Get historical ex-showroom price
    ex_showroom = get_historical_ex_showroom_price(make, model, variant, year)

    if not ex_showroom:
        return None

    # Calculate on-road price using year-specific rates
    on_road, breakdown = calculate_on_road_price(ex_showroom, year, state)

    return on_road, breakdown


# ==========================================
# FALLBACK: ESTIMATE HISTORICAL PRICE
# ==========================================

def estimate_historical_price(current_ex_showroom: float, current_year: int, target_year: int) -> float:
    """
    Estimate historical price by deflating current price

    Uses average car price inflation rate (reverse calculation)

    Args:
        current_ex_showroom: Current ex-showroom price
        current_year: Current year
        target_year: Target year to estimate

    Returns:
        Estimated historical ex-showroom price
    """
    years_diff = current_year - target_year

    # Car prices typically increase 5-8% per year
    # We'll use 6% as average
    inflation_rate = 0.06

    # Deflate price backwards
    deflation_factor = (1 + inflation_rate) ** years_diff
    historical_price = current_ex_showroom / deflation_factor

    return historical_price
