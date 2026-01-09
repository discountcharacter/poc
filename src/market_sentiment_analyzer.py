"""
Real-Time Market Sentiment Analyzer
===================================
Analyzes market demand/supply dynamics that affect vehicle valuations.

KEY INSIGHT from Droom CEO:
OBV uses real-time market sentiments to adjust pricing beyond simple depreciation.
"""

from typing import Dict, Tuple
from enum import Enum
from datetime import datetime


class FuelTypeTrend(Enum):
    """Fuel type market trends"""
    RISING = "Rising Demand"
    STABLE = "Stable"
    DECLINING = "Declining Demand"


# ==========================================
# FUEL TYPE MARKET DYNAMICS
# ==========================================

FUEL_MARKET_TRENDS = {
    # Post-BS6 (2020+), diesel lost popularity
    'petrol': {
        2015: {'trend': FuelTypeTrend.STABLE, 'multiplier': 1.00},
        2016: {'trend': FuelTypeTrend.STABLE, 'multiplier': 1.00},
        2017: {'trend': FuelTypeTrend.STABLE, 'multiplier': 1.00},
        2018: {'trend': FuelTypeTrend.STABLE, 'multiplier': 1.00},
        2019: {'trend': FuelTypeTrend.STABLE, 'multiplier': 1.00},
        2020: {'trend': FuelTypeTrend.RISING, 'multiplier': 1.03},  # BS6, diesel decline
        2021: {'trend': FuelTypeTrend.RISING, 'multiplier': 1.04},
        2022: {'trend': FuelTypeTrend.RISING, 'multiplier': 1.05},
        2023: {'trend': FuelTypeTrend.RISING, 'multiplier': 1.05},
        2024: {'trend': FuelTypeTrend.STABLE, 'multiplier': 1.03},
        2025: {'trend': FuelTypeTrend.STABLE, 'multiplier': 1.03},
    },

    'diesel': {
        2015: {'trend': FuelTypeTrend.STABLE, 'multiplier': 1.05},  # Diesel premium
        2016: {'trend': FuelTypeTrend.STABLE, 'multiplier': 1.05},
        2017: {'trend': FuelTypeTrend.STABLE, 'multiplier': 1.05},
        2018: {'trend': FuelTypeTrend.STABLE, 'multiplier': 1.04},
        2019: {'trend': FuelTypeTrend.DECLINING, 'multiplier': 1.02},  # BS6 announcement
        2020: {'trend': FuelTypeTrend.DECLINING, 'multiplier': 0.98},  # BS6, price gap narrowed
        2021: {'trend': FuelTypeTrend.DECLINING, 'multiplier': 0.95},
        2022: {'trend': FuelTypeTrend.DECLINING, 'multiplier': 0.93},  # Many brands discontinued diesel
        2023: {'trend': FuelTypeTrend.DECLINING, 'multiplier': 0.92},
        2024: {'trend': FuelTypeTrend.DECLINING, 'multiplier': 0.91},
        2025: {'trend': FuelTypeTrend.DECLINING, 'multiplier': 0.90},
    },

    'cng': {
        2015: {'trend': FuelTypeTrend.STABLE, 'multiplier': 0.98},
        2016: {'trend': FuelTypeTrend.STABLE, 'multiplier': 0.98},
        2017: {'trend': FuelTypeTrend.RISING, 'multiplier': 1.00},
        2018: {'trend': FuelTypeTrend.RISING, 'multiplier': 1.02},
        2019: {'trend': FuelTypeTrend.RISING, 'multiplier': 1.03},
        2020: {'trend': FuelTypeTrend.RISING, 'multiplier': 1.04},  # Fuel price hikes
        2021: {'trend': FuelTypeTrend.RISING, 'multiplier': 1.06},
        2022: {'trend': FuelTypeTrend.RISING, 'multiplier': 1.08},
        2023: {'trend': FuelTypeTrend.RISING, 'multiplier': 1.08},
        2024: {'trend': FuelTypeTrend.STABLE, 'multiplier': 1.07},
        2025: {'trend': FuelTypeTrend.STABLE, 'multiplier': 1.07},
    },

    'electric': {
        2015: {'trend': FuelTypeTrend.STABLE, 'multiplier': 0.85},  # Very niche
        2016: {'trend': FuelTypeTrend.STABLE, 'multiplier': 0.87},
        2017: {'trend': FuelTypeTrend.STABLE, 'multiplier': 0.89},
        2018: {'trend': FuelTypeTrend.RISING, 'multiplier': 0.92},
        2019: {'trend': FuelTypeTrend.RISING, 'multiplier': 0.95},
        2020: {'trend': FuelTypeTrend.RISING, 'multiplier': 1.00},
        2021: {'trend': FuelTypeTrend.RISING, 'multiplier': 1.05},
        2022: {'trend': FuelTypeTrend.RISING, 'multiplier': 1.10},  # EV boom
        2023: {'trend': FuelTypeTrend.RISING, 'multiplier': 1.12},
        2024: {'trend': FuelTypeTrend.RISING, 'multiplier': 1.15},
        2025: {'trend': FuelTypeTrend.RISING, 'multiplier': 1.18},
    },
}


# ==========================================
# SEGMENT-WISE MARKET DYNAMICS
# ==========================================

SEGMENT_TRENDS = {
    # Hatchbacks
    'hatchback': {
        'base_multiplier': 1.00,
        'trend': 'Stable demand, entry-level buyers',
        'notes': 'Smaller depreciation, high liquidity'
    },

    # Compact SUVs (hottest segment)
    'compact_suv': {
        'base_multiplier': 1.08,  # +8% premium
        'trend': 'Very high demand post-2020',
        'notes': 'Best value retention, highest liquidity'
    },

    # Mid-size SUVs
    'suv': {
        'base_multiplier': 1.05,
        'trend': 'Growing demand',
        'notes': 'Good value retention'
    },

    # Sedans (declining segment)
    'sedan': {
        'base_multiplier': 0.95,  # -5% penalty
        'trend': 'Declining popularity, SUV preference',
        'notes': 'Slower depreciation but lower demand'
    },

    # MPVs
    'mpv': {
        'base_multiplier': 0.98,
        'trend': 'Niche segment',
        'notes': 'Specific buyer base, moderate demand'
    },

    # Luxury
    'luxury': {
        'base_multiplier': 0.85,  # -15% penalty
        'trend': 'Steep depreciation',
        'notes': 'High depreciation, limited buyers'
    },
}


# Model to segment mapping
MODEL_SEGMENT_MAP = {
    # Hatchbacks
    'alto': 'hatchback',
    'kwid': 'hatchback',
    'wagon r': 'hatchback',
    'swift': 'hatchback',
    'baleno': 'hatchback',
    'i20': 'hatchback',
    'polo': 'hatchback',
    'jazz': 'hatchback',
    'altroz': 'hatchback',
    'glanza': 'hatchback',

    # Compact SUVs (hottest segment!)
    'venue': 'compact_suv',
    'sonet': 'compact_suv',
    'nexon': 'compact_suv',
    'brezza': 'compact_suv',
    'ecosport': 'compact_suv',
    'xuv300': 'compact_suv',
    'magnite': 'compact_suv',
    'kiger': 'compact_suv',
    'punch': 'compact_suv',

    # Mid-size SUVs
    'creta': 'suv',
    'seltos': 'suv',
    'harrier': 'suv',
    'hector': 'suv',
    'xuv700': 'suv',
    'compass': 'suv',
    'alcazar': 'suv',
    'safari': 'suv',
    'scorpio': 'suv',

    # Sedans
    'dzire': 'sedan',
    'amaze': 'sedan',
    'aura': 'sedan',
    'city': 'sedan',
    'verna': 'sedan',
    'ciaz': 'sedan',
    'slavia': 'sedan',
    'virtus': 'sedan',

    # MPVs
    'ertiga': 'mpv',
    'marazzo': 'mpv',
    'carens': 'mpv',
    'innova': 'mpv',
    'carnival': 'mpv',
}


# ==========================================
# ECONOMIC FACTORS
# ==========================================

ECONOMIC_EVENTS = {
    2020: {
        'event': 'COVID-19 Pandemic',
        'impact': -0.10,  # -10% impact on valuations
        'notes': 'Market crash, uncertainty, production halted'
    },
    2021: {
        'event': 'Chip Shortage + COVID Recovery',
        'impact': +0.05,  # Used car prices rose due to new car shortage
        'notes': 'High demand, limited new car supply'
    },
    2022: {
        'event': 'Chip Shortage Continues',
        'impact': +0.08,  # Used cars commanded premium
        'notes': 'New car waiting periods extended'
    },
    2023: {
        'event': 'Market Normalization',
        'impact': 0.00,  # Back to normal
        'notes': 'Supply chains recovered'
    },
    2024: {
        'event': 'Stable Market',
        'impact': 0.00,
        'notes': 'Normal market conditions'
    },
    2025: {
        'event': 'Stable Market',
        'impact': 0.00,
        'notes': 'Normal market conditions'
    },
}


# ==========================================
# MARKET SENTIMENT CALCULATOR
# ==========================================

def get_fuel_type_sentiment(fuel_type: str, current_year: int = None) -> Tuple[float, str]:
    """
    Get current market sentiment for fuel type

    Args:
        fuel_type: Fuel type (Petrol, Diesel, CNG, Electric)
        current_year: Current year (defaults to current)

    Returns:
        Tuple of (multiplier, reason)
    """
    if current_year is None:
        current_year = datetime.now().year

    fuel_lower = fuel_type.lower()
    if fuel_lower not in FUEL_MARKET_TRENDS:
        return 1.00, "Unknown fuel type, using baseline"

    trend_data = FUEL_MARKET_TRENDS[fuel_lower].get(current_year, {'multiplier': 1.00, 'trend': FuelTypeTrend.STABLE})

    multiplier = trend_data['multiplier']
    trend = trend_data['trend']

    reason = f"{fuel_type.capitalize()} market: {trend.value}"

    return multiplier, reason


def get_segment_sentiment(model: str) -> Tuple[float, str]:
    """
    Get market sentiment for vehicle segment

    Args:
        model: Model name

    Returns:
        Tuple of (multiplier, reason)
    """
    model_lower = model.lower().replace(' ', '_')

    # Find segment
    segment = None
    for model_key, seg in MODEL_SEGMENT_MAP.items():
        if model_key in model_lower:
            segment = seg
            break

    if not segment:
        return 1.00, "Unknown segment, using baseline"

    segment_data = SEGMENT_TRENDS[segment]
    multiplier = segment_data['base_multiplier']
    reason = f"{segment.replace('_', ' ').title()} segment: {segment_data['trend']}"

    return multiplier, reason


def get_economic_factor(valuation_year: int) -> Tuple[float, str]:
    """
    Get economic factor for specific year

    Args:
        valuation_year: Year being valued

    Returns:
        Tuple of (adjustment_factor, reason)
    """
    if valuation_year in ECONOMIC_EVENTS:
        event_data = ECONOMIC_EVENTS[valuation_year]
        return 1.0 + event_data['impact'], f"{event_data['event']}: {event_data['notes']}"

    return 1.00, "No significant economic events"


def calculate_market_sentiment_multiplier(make: str, model: str, fuel_type: str,
                                         purchase_year: int, valuation_year: int = None) -> Tuple[float, Dict]:
    """
    Calculate comprehensive market sentiment multiplier

    This combines:
    1. Fuel type trends
    2. Segment dynamics
    3. Brand sentiment
    4. Economic factors

    Args:
        make: Manufacturer
        model: Model name
        fuel_type: Fuel type
        purchase_year: Year vehicle was purchased
        valuation_year: Current valuation year

    Returns:
        Tuple of (total_multiplier, breakdown_dict)
    """
    if valuation_year is None:
        valuation_year = datetime.now().year

    breakdown = {}

    # 1. Fuel type sentiment
    fuel_mult, fuel_reason = get_fuel_type_sentiment(fuel_type, valuation_year)
    breakdown['fuel_type'] = {
        'multiplier': fuel_mult,
        'reason': fuel_reason
    }

    # 2. Segment sentiment
    segment_mult, segment_reason = get_segment_sentiment(model)
    breakdown['segment'] = {
        'multiplier': segment_mult,
        'reason': segment_reason
    }

    # 3. Economic factors (for the purchase year)
    econ_mult, econ_reason = get_economic_factor(purchase_year)
    breakdown['economic'] = {
        'multiplier': econ_mult,
        'reason': econ_reason
    }

    # Combined multiplier
    total_multiplier = fuel_mult * segment_mult * econ_mult

    breakdown['total_multiplier'] = total_multiplier
    breakdown['notes'] = f"Market sentiment adjustment: {(total_multiplier - 1.0) * 100:+.1f}%"

    return total_multiplier, breakdown


# ==========================================
# BRAND RESALE VALUE INDEX
# ==========================================

BRAND_RESALE_INDEX = {
    # Japanese brands (excellent resale)
    'maruti suzuki': 1.08,  # +8% - Best resale in India
    'maruti': 1.08,
    'honda': 1.05,  # +5% - Strong resale
    'toyota': 1.06,  # +6% - Very reliable

    # Korean brands (good resale)
    'hyundai': 1.04,  # +4% - Popular brand
    'kia': 1.02,  # +2% - Newer but gaining trust

    # Indian brands (improving)
    'tata': 1.00,  # Baseline - Much improved quality
    'mahindra': 1.01,  # +1% - Strong in SUV segment

    # European brands (premium but faster depreciation)
    'volkswagen': 0.95,  # -5% - Higher maintenance costs
    'skoda': 0.94,  # -6% - Similar to VW
    'renault': 0.92,  # -8% - Lower brand equity
    'nissan': 0.93,  # -7% - Declining presence

    # Exited brands (poor resale)
    'ford': 0.80,  # -20% - Exited India
    'chevrolet': 0.75,  # -25% - Exited, service concerns
    'fiat': 0.70,  # -30% - Exited, parts availability issues
}


def get_brand_resale_multiplier(make: str) -> Tuple[float, str]:
    """
    Get brand-specific resale value multiplier

    Args:
        make: Manufacturer name

    Returns:
        Tuple of (multiplier, reason)
    """
    make_lower = make.lower()

    if make_lower in BRAND_RESALE_INDEX:
        multiplier = BRAND_RESALE_INDEX[make_lower]

        if multiplier > 1.0:
            reason = f"{make} has excellent resale value (+{(multiplier-1)*100:.0f}%)"
        elif multiplier < 1.0:
            reason = f"{make} has lower resale value ({(multiplier-1)*100:.0f}%)"
        else:
            reason = f"{make} has standard resale value"

        return multiplier, reason

    return 1.00, f"{make} - standard resale value"
