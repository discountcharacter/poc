"""
Orange Book Value (OBV) Style - Hyderabad-Specific Valuation Engine

This module implements a comprehensive algorithmic vehicle valuation system
based on Orange Book Value methodology, specifically calibrated for the
Hyderabad automotive market.

Key Components:
1. IRDAI-based segmented depreciation with continuous decay
2. Odometer deviation analysis with tiered penalty system
3. 16-point condition scoring algorithm
4. Transaction context pricing (C2C, B2C, C2B, B2B)
5. Ownership factor adjustments
6. Hyderabad-specific location factors
7. GST calculations for dealer transactions

Author: Automotive Valuation Engine
Version: 1.0.0
"""

import math
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import sys
import os

# Import price fetcher with robust path handling
try:
    # Add src directory to path if not already there
    src_dir = os.path.dirname(os.path.abspath(__file__))
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    from price_fetcher import price_fetcher
    PRICE_FETCHER_AVAILABLE = True
except ImportError as e:
    print(f"Price fetcher import failed: {e}")
    PRICE_FETCHER_AVAILABLE = False
except Exception as e:
    print(f"Price fetcher error: {e}")
    PRICE_FETCHER_AVAILABLE = False

# Import historical price database (CRITICAL for accurate OBV)
try:
    from historical_price_database import (
        get_historical_on_road_price,
        get_historical_ex_showroom_price,
        calculate_on_road_price,
        estimate_historical_price,
        get_market_sentiment,
        MarketSentiment,
        SENTIMENT_MULTIPLIERS
    )
    HISTORICAL_PRICES_AVAILABLE = True
    print("✅ Historical price database loaded")
except ImportError as e:
    print(f"⚠️ Historical price database import failed: {e}")
    HISTORICAL_PRICES_AVAILABLE = False
except Exception as e:
    print(f"⚠️ Historical price database error: {e}")
    HISTORICAL_PRICES_AVAILABLE = False

# Import market sentiment analyzer
try:
    from market_sentiment_analyzer import (
        calculate_market_sentiment_multiplier,
        get_brand_resale_multiplier,
        get_fuel_type_sentiment,
        get_segment_sentiment
    )
    MARKET_SENTIMENT_AVAILABLE = True
    print("✅ Market sentiment analyzer loaded")
except ImportError as e:
    print(f"⚠️ Market sentiment analyzer import failed: {e}")
    MARKET_SENTIMENT_AVAILABLE = False
except Exception as e:
    print(f"⚠️ Market sentiment analyzer error: {e}")
    MARKET_SENTIMENT_AVAILABLE = False


class FuelType(Enum):
    """Fuel type enumeration with standard annual mileage"""
    PETROL = "Petrol"
    DIESEL = "Diesel"
    CNG = "CNG"
    ELECTRIC = "Electric"


class ConditionGrade(Enum):
    """Vehicle condition grading"""
    EXCELLENT = "Excellent"
    VERY_GOOD = "Very Good"
    GOOD = "Good"
    FAIR = "Fair"


class TransactionType(Enum):
    """Transaction context types"""
    C2C = "Individual to Individual"  # Fair Market Value
    B2C = "Dealer to Individual"      # Retail Price
    C2B = "Individual to Dealer"      # Trade-in Price (PROCUREMENT)
    B2B = "Dealer to Dealer"          # Wholesale Price


@dataclass
class VehicleInput:
    """Vehicle input data structure"""
    make: str
    model: str
    variant: str
    year: int
    registration_date: date
    fuel_type: FuelType
    odometer: int  # in kilometers
    owners: int
    transmission: str  # "Manual" or "Automatic"
    location: str = "Hyderabad"

    # Condition inspection data
    frame_damage: bool = False
    dents_scratches: str = "Minor"  # "None", "Minor", "Moderate", "Severe"
    repainted: bool = False
    engine_smoke: str = "None"  # "None", "White", "Black"
    tire_tread: int = 75  # Percentage remaining
    ac_working: bool = True
    electrical_issues: bool = False
    service_history: bool = True
    insurance_valid: bool = True
    accident_history: bool = False

    # Additional inspection parameters
    engine_noise: str = "Normal"  # "Normal", "Slight", "Heavy"
    transmission_condition: str = "Smooth"  # "Smooth", "Rough", "Slipping"
    suspension_condition: str = "Good"  # "Excellent", "Good", "Fair", "Poor"
    brake_condition: str = "Good"  # "Excellent", "Good", "Fair", "Poor"
    interior_condition: str = "Good"  # "Excellent", "Good", "Fair", "Poor"
    rust_present: bool = False


@dataclass
class ValuationResult:
    """Comprehensive valuation output"""
    # Core prices
    fair_market_value: float  # C2C price
    retail_price: float  # B2C price (dealer selling)
    trade_in_price: float  # C2B price (PROCUREMENT - what company pays)
    wholesale_price: float  # B2B price

    # Breakdown components
    base_price: float  # Current new vehicle price
    depreciated_value: float  # After depreciation
    usage_adjusted_value: float  # After odometer adjustment
    condition_adjusted_value: float  # After condition scoring

    # Adjustment factors
    depreciation_percentage: float
    usage_factor: float
    condition_score: float
    condition_multiplier: float
    ownership_multiplier: float
    location_multiplier: float

    # Additional insights
    condition_grade: ConditionGrade
    odometer_deviation: int
    expected_odometer: int

    # Price ranges for negotiation
    trade_in_min: float  # Minimum company should pay
    trade_in_max: float  # Maximum company should pay

    # Detailed reasoning
    depreciation_breakdown: Dict[str, float]
    condition_breakdown: Dict[str, float]
    warnings: List[str]
    recommendations: List[str]


class OBVHyderabadEngine:
    """
    Main valuation engine implementing OBV-style algorithmic pricing
    for Hyderabad market
    """

    # Standard annual mileage by fuel type (km/year)
    STANDARD_MILEAGE = {
        FuelType.PETROL: 11000,
        FuelType.DIESEL: 16500,
        FuelType.CNG: 20000,
        FuelType.ELECTRIC: 11000
    }

    # Segmented depreciation rates
    DEPRECIATION_RATES = {
        'year_0_1': 0.17,    # 17% for first year (aggressive drop)
        'year_1_3': 0.11,    # 11% per year for years 1-3
        'year_3_5': 0.09,    # 9% per year for years 3-5
        'year_5_plus': 0.06  # 6% per year for 5+ years
    }

    # IRDAI baseline depreciation schedule (for reference/validation)
    IRDAI_SCHEDULE = {
        0.5: 0.95,   # < 6 months: 95% residual value
        1.0: 0.85,   # < 1 year: 85%
        2.0: 0.80,   # < 2 years: 80%
        3.0: 0.70,   # < 3 years: 70%
        4.0: 0.60,   # < 4 years: 60%
        5.0: 0.50    # < 5 years: 50%
    }

    # Ownership penalty multipliers
    OWNERSHIP_MULTIPLIERS = {
        1: 1.00,   # 1st owner: no penalty
        2: 0.93,   # 2nd owner: -7%
        3: 0.85,   # 3rd owner: -15%
        4: 0.75,   # 4th+ owner: -25%
    }

    # Transaction type margins
    DEALER_MARGIN = 0.12  # 12% dealer margin
    WHOLESALE_DISCOUNT = 0.08  # 8% discount for B2B
    GST_RATE = 0.18  # 18% GST on margin

    # Hyderabad-specific multipliers
    HYDERABAD_FACTORS = {
        'diesel_premium': 1.05,  # Diesel cars retain more value (no ban)
        'tech_hub_premium': 1.03,  # Premium segments in IT corridors
        'default': 1.00
    }

    def __init__(self):
        """Initialize the OBV Hyderabad Engine"""
        self.warnings = []
        self.recommendations = []

    def calculate_vehicle_age(self, registration_date: date) -> float:
        """
        Calculate precise vehicle age in years

        Args:
            registration_date: Date of first registration

        Returns:
            Age in years (fractional)
        """
        today = date.today()
        age_days = (today - registration_date).days
        age_years = age_days / 365.25
        return age_years

    # List of discontinued models that should use HISTORICAL pricing
    DISCONTINUED_MODELS = {
        'beetle', 'volkswagen beetle', 'vw beetle',
        'figo', 'ford figo', 'ecosport', 'ford ecosport',  # Ford exited India
        'chevrolet', 'beat', 'sail', 'cruze',  # Chevrolet exited
        'datsun', 'redi-go', 'go', 'go+',  # Datsun discontinued
        'palio', 'linea', 'punto', 'avventura',  # Fiat mostly discontinued
        'micra', 'sunny', 'terrano',  # Nissan discontinued models
        'storme', 'safari storme',  # Tata discontinued
    }

    def is_discontinued(self, make: str, model: str) -> bool:
        """Check if a model is discontinued"""
        make_model = f"{make} {model}".lower()
        model_lower = model.lower()

        # Check if model or make+model in discontinued list
        return any(disc in make_model or disc in model_lower
                   for disc in self.DISCONTINUED_MODELS)

    def get_current_on_road_price(self, make: str, model: str, variant: str,
                                   fuel_type: FuelType = None, state: str = "telangana") -> float:
        """
        Get CURRENT on-road price (what it would cost to buy NEW today)

        This is THE CORRECT OBV METHOD for CURRENT PRODUCTION cars:
        - Uses CURRENT new vehicle on-road price (today's market price)
        - NOT the historical price from purchase year
        - Shows "what % of current new value" the used car is worth
        - This is why OBV values seem higher - they're compared to current prices!

        Priority:
        1. Live price fetcher (current ex-showroom)
        2. Segment-based current pricing
        3. Fallback estimation

        Args:
            make: Vehicle manufacturer
            model: Model name
            variant: Specific trim/variant
            fuel_type: Fuel type
            state: State of registration (for tax calculation)

        Returns:
            Current new on-road price in INR
        """
        current_year = datetime.now().year
        print(f"🎯 OBV CORRECT METHOD: Getting CURRENT ({current_year}) on-road price for {make} {model} {variant}")

        current_ex_showroom = None

        # PRIORITY 1: Try to fetch CURRENT live price
        if PRICE_FETCHER_AVAILABLE and fuel_type:
            fuel_str = fuel_type.value if isinstance(fuel_type, FuelType) else str(fuel_type)

            try:
                print(f"🔍 Fetching CURRENT market price...")
                price_data = price_fetcher.get_current_price(
                    make=make, model=model, variant=variant, fuel=fuel_str, year=current_year
                )

                if price_data and price_data.get("ex_showroom_price"):
                    current_ex_showroom = price_data.get("ex_showroom_price")

                    if 300000 <= current_ex_showroom <= 15000000:
                        print(f"   ✅ Found current ex-showroom: ₹{current_ex_showroom:,.0f}")
                        self.recommendations.append(
                            f"✅ Current {current_year} ex-showroom price: ₹{current_ex_showroom:,.0f}"
                        )
                    else:
                        current_ex_showroom = None
            except Exception as e:
                print(f"⚠️ Price fetcher error: {e}")

        # PRIORITY 2: Use segment-based current pricing
        if not current_ex_showroom:
            segments = {
                # Entry hatchbacks
                'alto': 450000, 'kwid': 450000, 's-presso': 450000,

                # Budget hatchbacks
                'wagon r': 550000, 'wagonr': 550000, 'santro': 500000,
                'grand i10': 600000, 'ignis': 600000,

                # Premium hatchbacks
                'swift': 650000, 'dzire': 700000, 'baleno': 750000, 'glanza': 700000,
                'i20': 750000, 'altroz': 700000, 'polo': 750000, 'jazz': 800000,
                'fronx': 800000,

                # Compact sedans/SUVs
                'venue': 1200000, 'sonet': 900000, 'nexon': 900000, 'punch': 700000,
                'brezza': 1100000, 'vitara brezza': 1100000, 'ecosport': 1100000,
                'magnite': 700000, 'kiger': 700000,

                # Mid-size sedans
                'city': 1200000, 'verna': 1200000, 'ciaz': 1000000,
                'slavia': 1200000, 'virtus': 1200000,

                # Mid-size SUVs
                'creta': 1500000, 'seltos': 1600000, 'harrier': 2000000,
                'hector': 1600000, 'alcazar': 1800000, 'safari': 1800000,
                'xuv': 1800000, 'xuv700': 2200000, 'scorpio': 1600000,
                'compass': 2500000, 'thar': 1500000,

                # MPVs
                'ertiga': 1000000, 'carens': 1200000, 'marazzo': 1300000,
                'innova': 2500000, 'crysta': 2500000, 'carnival': 3500000,

                # Premium/Luxury
                'fortuner': 3500000, 'endeavour': 3500000, 'tucson': 3000000,
                'kona': 2500000, 'elantra': 2000000, 'octavia': 2800000,
                'superb': 3500000, 'kodiaq': 4000000,

                # Hybrid/Electric
                'hyryder': 1200000, 'urban cruiser': 1100000,
                'nexon ev': 1500000, 'tiago ev': 900000,

                # Commercial
                'eeco': 500000,

                # Special cases
                'celerio': 550000,  # Added for test case
                'aura': 700000,      # Added for test case
                'beetle': 2500000,   # VW Beetle (discontinued, use segment estimate)
            }

            model_lower = model.lower()
            base_price = 800000  # Default fallback

            # Try exact match first
            if model_lower in segments:
                base_price = segments[model_lower]
            else:
                # Try partial match
                for key, price in segments.items():
                    if key in model_lower or model_lower in key:
                        base_price = price
                        break

            current_ex_showroom = base_price
            print(f"   ℹ️ Using segment-based current price: ₹{current_ex_showroom:,.0f}")
            self.recommendations.append(
                f"ℹ️ Current {current_year} ex-showroom (segment estimate): ₹{current_ex_showroom:,.0f}"
            )

        # Calculate CURRENT on-road price
        if HISTORICAL_PRICES_AVAILABLE and current_ex_showroom:
            # Use CURRENT year for on-road calculation
            on_road_price, breakdown = calculate_on_road_price(current_ex_showroom, current_year, state)

            self.recommendations.append(
                f"✅ Current {current_year} on-road price: ₹{on_road_price:,.0f}"
            )
            self.recommendations.append(
                f"   Components: Ex-showroom ₹{breakdown['ex_showroom']:,.0f} + "
                f"Road tax ₹{breakdown['road_tax']:,.0f} + "
                f"Insurance ₹{breakdown['insurance']:,.0f} + "
                f"Registration ₹{breakdown['registration'] + breakdown['smart_card'] + breakdown['cess'] + breakdown['other_charges']:,.0f}"
            )

            print(f"✅ Current on-road price calculated: ₹{on_road_price:,.0f}")
            return on_road_price

        # Last resort: return just the ex-showroom estimate with approximate on-road multiplier
        self.warnings.append(
            "⚠️ On-road calculation unavailable, using ex-showroom estimate + 18% buffer"
        )
        return current_ex_showroom * 1.18 if current_ex_showroom else 800000 * 1.18

    def get_original_on_road_price(self, make: str, model: str, variant: str, year: int,
                                   month: int = 3, fuel_type: FuelType = None, state: str = "telangana") -> float:
        """
        Get ORIGINAL on-road price from the year vehicle was purchased

        This is THE CORRECT OBV METHOD for DISCONTINUED cars:
        - Uses the ACTUAL on-road price paid by the owner (purchase year)
        - NOT a current equivalent (because the model doesn't exist anymore)
        - Represents value loss from original investment

        Priority:
        1. Historical price database (curated data for popular models)
        2. Fetch current price and deflate backwards
        3. Segment-based estimation with deflation

        Args:
            make: Vehicle manufacturer
            model: Model name
            variant: Specific trim/variant
            year: Year of purchase
            month: Month of purchase
            fuel_type: Fuel type
            state: State of registration (for tax calculation)

        Returns:
            Original on-road price in INR
        """
        print(f"🎯 OBV HISTORICAL METHOD: Getting ORIGINAL on-road price for {year} {make} {model} {variant}")

        # PRIORITY 1: Try historical price database (curated accurate data)
        if HISTORICAL_PRICES_AVAILABLE:
            historical_result = get_historical_on_road_price(make, model, variant, year, month, state)

            if historical_result:
                on_road_price, breakdown = historical_result

                self.recommendations.append(
                    f"✅ Historical price database: {year} on-road price ₹{on_road_price:,.0f}"
                )
                self.recommendations.append(
                    f"   Ex-showroom: ₹{breakdown['ex_showroom']:,.0f} + "
                    f"Road tax: ₹{breakdown['road_tax']:,.0f} ({breakdown['road_tax_rate']}) + "
                    f"Insurance: ₹{breakdown['insurance']:,.0f}"
                )

                print(f"✅ Found in historical database: ₹{on_road_price:,.0f}")
                return on_road_price

        # PRIORITY 2: Fetch current ex-showroom price and estimate backwards
        ex_showroom_historical = None

        # Try to get current price and estimate backwards
        if PRICE_FETCHER_AVAILABLE and fuel_type:
            fuel_str = fuel_type.value if isinstance(fuel_type, FuelType) else str(fuel_type)

            try:
                print(f"🔍 Fetching current price to estimate {year} price...")
                price_data = price_fetcher.get_current_price(
                    make=make, model=model, variant=variant, fuel=fuel_str, year=datetime.now().year
                )

                if price_data and price_data.get("ex_showroom_price"):
                    current_ex_showroom = price_data.get("ex_showroom_price")

                    if 300000 <= current_ex_showroom <= 15000000:
                        # Estimate historical price by deflating current price
                        if HISTORICAL_PRICES_AVAILABLE:
                            ex_showroom_historical = estimate_historical_price(
                                current_ex_showroom, datetime.now().year, year
                            )
                            print(f"   Estimated {year} ex-showroom: ₹{ex_showroom_historical:,.0f}")
                            self.recommendations.append(
                                f"✅ Estimated {year} ex-showroom from current price: ₹{ex_showroom_historical:,.0f}"
                            )
            except Exception as e:
                print(f"⚠️ Price fetcher error: {e}")

        # PRIORITY 3: Fallback segment-based estimation with deflation
        if not ex_showroom_historical:
            # Historical segment prices (what these models cost when new)
            historical_segments = {
                # Beetle had different prices depending on variant
                # 1.4 TSI was cheaper than 2.0 TDI
                'beetle': {2016: 2350000, 2017: 2450000, 2018: 2550000, 2019: 2600000},  # Discontinued 2019
                'figo': {2015: 450000, 2016: 470000, 2017: 490000, 2018: 510000, 2019: 530000},
                'ecosport': {2015: 700000, 2016: 750000, 2017: 800000, 2018: 850000, 2019: 900000},
            }

            model_lower = model.lower()

            # Try to get historical price for the specific year
            if model_lower in historical_segments and year in historical_segments[model_lower]:
                ex_showroom_historical = historical_segments[model_lower][year]
                print(f"   Using historical segment price for {year}: ₹{ex_showroom_historical:,.0f}")
                self.recommendations.append(
                    f"✅ Historical segment price ({year}): ₹{ex_showroom_historical:,.0f}"
                )
            else:
                # Use current segment pricing and deflate
                segments = {
                    'alto': 450000, 'kwid': 450000, 'wagon r': 550000, 'wagonr': 550000,
                    'santro': 500000, 'swift': 650000, 'baleno': 750000, 'i20': 750000,
                    'celerio': 550000, 'aura': 700000, 'beetle': 2500000,
                }

                base_price = 800000  # Default
                for key, price in segments.items():
                    if key in model_lower:
                        base_price = price
                        break

                # Deflate to purchase year
                current_year = datetime.now().year
                years_diff = current_year - year

                if years_diff > 0:
                    # Deflate backwards (6% inflation per year)
                    deflation_factor = 1.06 ** years_diff
                    ex_showroom_historical = base_price / deflation_factor
                else:
                    ex_showroom_historical = base_price

                print(f"   Estimated {year} ex-showroom from segment: ₹{ex_showroom_historical:,.0f}")
                self.warnings.append(
                    f"ℹ️ Estimated {year} ex-showroom price (₹{ex_showroom_historical:,.0f}) - "
                    "not in historical database"
                )

        # Calculate on-road price for that year
        if HISTORICAL_PRICES_AVAILABLE and ex_showroom_historical:
            on_road_price, breakdown = calculate_on_road_price(ex_showroom_historical, year, state)

            self.recommendations.append(
                f"✅ Calculated {year} on-road price: ₹{on_road_price:,.0f}"
            )
            self.recommendations.append(
                f"   Components: Ex-showroom ₹{breakdown['ex_showroom']:,.0f} + "
                f"Road tax ₹{breakdown['road_tax']:,.0f} + "
                f"Insurance ₹{breakdown['insurance']:,.0f} + "
                f"Registration ₹{breakdown['registration'] + breakdown['smart_card'] + breakdown['cess'] + breakdown['other_charges']:,.0f}"
            )

            return on_road_price

        # Last resort: return just the ex-showroom estimate
        self.warnings.append(
            "⚠️ On-road calculation unavailable, using ex-showroom estimate"
        )
        return ex_showroom_historical if ex_showroom_historical else 800000

    def calculate_segmented_depreciation(self, age_years: float, base_price: float) -> Tuple[float, Dict[str, float]]:
        """
        Calculate depreciation using segmented rates for different age brackets

        This implements the sophisticated depreciation curve:
        - Year 0-1: Steep drop (17%)
        - Year 1-3: Moderate decline (11% per year)
        - Year 3-5: Slower decline (9% per year)
        - Year 5+: Plateau (6% per year)

        Args:
            age_years: Vehicle age in years
            base_price: Current new vehicle price

        Returns:
            Tuple of (depreciated_value, breakdown_dict)
        """
        breakdown = {}
        remaining_value = base_price

        # Year 0-1 depreciation
        if age_years <= 1:
            depreciation = base_price * self.DEPRECIATION_RATES['year_0_1'] * age_years
            remaining_value = base_price - depreciation
            breakdown['year_0_1'] = depreciation
        else:
            # Apply full first year depreciation
            year_1_dep = base_price * self.DEPRECIATION_RATES['year_0_1']
            remaining_value -= year_1_dep
            breakdown['year_0_1'] = year_1_dep

            # Year 1-3 depreciation
            if age_years <= 3:
                years_in_bracket = age_years - 1
                for i in range(int(years_in_bracket)):
                    year_dep = remaining_value * self.DEPRECIATION_RATES['year_1_3']
                    remaining_value -= year_dep
                    breakdown[f'year_{i+2}'] = year_dep

                # Partial year if any
                partial = years_in_bracket - int(years_in_bracket)
                if partial > 0:
                    year_dep = remaining_value * self.DEPRECIATION_RATES['year_1_3'] * partial
                    remaining_value -= year_dep
                    breakdown[f'year_{int(years_in_bracket)+2}_partial'] = year_dep

            elif age_years <= 5:
                # Apply full years 1-3
                for i in range(2):
                    year_dep = remaining_value * self.DEPRECIATION_RATES['year_1_3']
                    remaining_value -= year_dep
                    breakdown[f'year_{i+2}'] = year_dep

                # Year 3-5 depreciation
                years_in_bracket = age_years - 3
                for i in range(int(years_in_bracket)):
                    year_dep = remaining_value * self.DEPRECIATION_RATES['year_3_5']
                    remaining_value -= year_dep
                    breakdown[f'year_{i+4}'] = year_dep

                # Partial year
                partial = years_in_bracket - int(years_in_bracket)
                if partial > 0:
                    year_dep = remaining_value * self.DEPRECIATION_RATES['year_3_5'] * partial
                    remaining_value -= year_dep
                    breakdown[f'year_{int(years_in_bracket)+4}_partial'] = year_dep

            else:
                # Age > 5 years
                # Apply full years 1-3
                for i in range(2):
                    year_dep = remaining_value * self.DEPRECIATION_RATES['year_1_3']
                    remaining_value -= year_dep
                    breakdown[f'year_{i+2}'] = year_dep

                # Apply full years 3-5
                for i in range(2):
                    year_dep = remaining_value * self.DEPRECIATION_RATES['year_3_5']
                    remaining_value -= year_dep
                    breakdown[f'year_{i+4}'] = year_dep

                # Year 5+ depreciation
                years_in_bracket = age_years - 5
                for i in range(int(years_in_bracket)):
                    year_dep = remaining_value * self.DEPRECIATION_RATES['year_5_plus']
                    remaining_value -= year_dep
                    breakdown[f'year_{i+6}'] = year_dep

                # Partial year
                partial = years_in_bracket - int(years_in_bracket)
                if partial > 0:
                    year_dep = remaining_value * self.DEPRECIATION_RATES['year_5_plus'] * partial
                    remaining_value -= year_dep
                    breakdown[f'year_{int(years_in_bracket)+6}_partial'] = year_dep

        total_depreciation = base_price - remaining_value
        depreciation_percentage = (total_depreciation / base_price) * 100

        return remaining_value, breakdown, depreciation_percentage

    def calculate_odometer_adjustment(self, age_years: float, actual_odometer: int,
                                     fuel_type: FuelType) -> Tuple[float, int, int]:
        """
        Calculate usage factor based on odometer deviation with tiered penalties

        Implements non-linear penalty function:
        - Tier 1 (0-40k km): 2% per 10k km deviation
        - Tier 2 (40-90k km): 4% per 10k km deviation
        - Tier 3 (90-100k km): 8% cliff effect
        - Tier 4 (>100k km): 6% per 10k km deviation

        Args:
            age_years: Vehicle age
            actual_odometer: Actual kilometers driven
            fuel_type: Fuel type (affects standard mileage)

        Returns:
            Tuple of (usage_factor, odometer_deviation, expected_odometer)
        """
        # Calculate expected odometer reading
        standard_annual_km = self.STANDARD_MILEAGE[fuel_type]
        expected_odometer = int(age_years * standard_annual_km)

        # Calculate deviation
        odometer_deviation = actual_odometer - expected_odometer

        # Tampering detection
        if actual_odometer < (age_years * 2000):
            self.warnings.append(
                f"⚠️ Odometer reading ({actual_odometer:,} km) suspiciously low for a "
                f"{age_years:.1f} year old vehicle. Possible tampering."
            )
            # Cap the low mileage premium
            odometer_deviation = max(odometer_deviation, -expected_odometer * 0.3)

        # Calculate tiered penalty/bonus
        penalty_percentage = 0.0

        if odometer_deviation > 0:
            # Car has run MORE than expected - apply penalties
            remaining_deviation = odometer_deviation

            # Tier 1: 0-40k excess
            tier1_threshold = 40000
            if remaining_deviation > 0:
                tier1_km = min(remaining_deviation, tier1_threshold)
                penalty_percentage += (tier1_km / 10000) * 2.0
                remaining_deviation -= tier1_km

            # Tier 2: 40k-90k excess
            tier2_threshold = 50000
            if remaining_deviation > 0:
                tier2_km = min(remaining_deviation, tier2_threshold)
                penalty_percentage += (tier2_km / 10000) * 4.0
                remaining_deviation -= tier2_km

            # Tier 3: 90k-100k (the psychological barrier)
            tier3_threshold = 10000
            if remaining_deviation > 0:
                tier3_km = min(remaining_deviation, tier3_threshold)
                penalty_percentage += 8.0  # Flat 8% for crossing 100k barrier
                remaining_deviation -= tier3_km

                if tier3_km > 0:
                    self.warnings.append(
                        "⚠️ Vehicle has crossed 100,000 km psychological barrier. "
                        "Expect lower market demand and financing difficulty."
                    )

            # Tier 4: >100k excess
            if remaining_deviation > 0:
                penalty_percentage += (remaining_deviation / 10000) * 6.0

        elif odometer_deviation < 0:
            # Car has run LESS than expected - apply premium (capped)
            abs_deviation = abs(odometer_deviation)

            # Premium is less aggressive than penalty (1.5% per 10k km)
            premium_percentage = min((abs_deviation / 10000) * 1.5, 10.0)  # Max 10% premium
            penalty_percentage = -premium_percentage  # Negative penalty = bonus

            self.recommendations.append(
                f"✅ Low mileage vehicle: {actual_odometer:,} km vs expected "
                f"{expected_odometer:,} km. Premium applied."
            )

        # Convert percentage to multiplier
        usage_factor = 1.0 - (penalty_percentage / 100.0)
        usage_factor = max(usage_factor, 0.4)  # Floor at 40% to avoid absurd discounts

        return usage_factor, odometer_deviation, expected_odometer

    def calculate_condition_score(self, vehicle: VehicleInput) -> Tuple[float, ConditionGrade, Dict[str, float]]:
        """
        Calculate comprehensive condition score using 16-point inspection

        Weighted scoring system:
        - Engine/Transmission: 35%
        - Body/Frame: 25%
        - Tires/Suspension: 15%
        - Electrical/Interior: 15%
        - Documentation: 10%

        Args:
            vehicle: Vehicle input data with inspection details

        Returns:
            Tuple of (condition_score_0_100, grade, breakdown_dict)
        """
        breakdown = {}

        # 1. Engine/Transmission (35 points max)
        engine_score = 0

        # Frame damage is critical - auto-fail
        if vehicle.frame_damage:
            breakdown['frame_damage'] = -20
            engine_score -= 20
            self.warnings.append("❌ CRITICAL: Frame damage detected. Vehicle may be unsafe/unsellable.")
        else:
            breakdown['frame_damage'] = 5
            engine_score += 5

        # Engine smoke
        smoke_scores = {"None": 10, "White": 3, "Black": 0}
        smoke_score = smoke_scores.get(vehicle.engine_smoke, 5)
        breakdown['engine_smoke'] = smoke_score
        engine_score += smoke_score

        if vehicle.engine_smoke in ["White", "Black"]:
            self.warnings.append(
                f"⚠️ Engine smoke detected ({vehicle.engine_smoke}). Major engine work may be required."
            )

        # Engine noise
        noise_scores = {"Normal": 10, "Slight": 6, "Heavy": 0}
        noise_score = noise_scores.get(vehicle.engine_noise, 5)
        breakdown['engine_noise'] = noise_score
        engine_score += noise_score

        # Transmission
        trans_scores = {"Smooth": 10, "Rough": 5, "Slipping": 0}
        trans_score = trans_scores.get(vehicle.transmission_condition, 5)
        breakdown['transmission'] = trans_score
        engine_score += trans_score

        # 2. Body/Frame (25 points max)
        body_score = 0

        # Dents and scratches
        dent_scores = {"None": 15, "Minor": 10, "Moderate": 5, "Severe": 0}
        dent_score = dent_scores.get(vehicle.dents_scratches, 7)
        breakdown['dents_scratches'] = dent_score
        body_score += dent_score

        # Repainted (indicates accident or poor maintenance)
        repaint_score = 0 if vehicle.repainted else 5
        breakdown['repainted'] = repaint_score
        body_score += repaint_score

        # Rust
        rust_score = 0 if vehicle.rust_present else 5
        breakdown['rust'] = rust_score
        body_score += rust_score

        # 3. Tires/Suspension (15 points max)
        mechanical_score = 0

        # Tire tread depth
        if vehicle.tire_tread >= 75:
            tire_score = 7
        elif vehicle.tire_tread >= 50:
            tire_score = 5
        elif vehicle.tire_tread >= 30:
            tire_score = 2
        else:
            tire_score = 0
            self.warnings.append("⚠️ Tires critically worn. Immediate replacement required.")

        breakdown['tire_tread'] = tire_score
        mechanical_score += tire_score

        # Suspension
        susp_scores = {"Excellent": 5, "Good": 4, "Fair": 2, "Poor": 0}
        susp_score = susp_scores.get(vehicle.suspension_condition, 2)
        breakdown['suspension'] = susp_score
        mechanical_score += susp_score

        # Brakes
        brake_scores = {"Excellent": 3, "Good": 2, "Fair": 1, "Poor": 0}
        brake_score = brake_scores.get(vehicle.brake_condition, 1)
        breakdown['brakes'] = brake_score
        mechanical_score += brake_score

        # 4. Electrical/Interior (15 points max)
        comfort_score = 0

        # AC
        ac_score = 5 if vehicle.ac_working else 0
        breakdown['ac'] = ac_score
        comfort_score += ac_score

        # Electrical issues
        elec_score = 0 if vehicle.electrical_issues else 5
        breakdown['electrical'] = elec_score
        comfort_score += elec_score

        if vehicle.electrical_issues:
            self.warnings.append("⚠️ Electrical issues reported. Diagnostics recommended.")

        # Interior condition
        int_scores = {"Excellent": 5, "Good": 3, "Fair": 1, "Poor": 0}
        int_score = int_scores.get(vehicle.interior_condition, 2)
        breakdown['interior'] = int_score
        comfort_score += int_score

        # 5. Documentation (10 points max)
        doc_score = 0

        # Service history
        service_score = 5 if vehicle.service_history else 0
        breakdown['service_history'] = service_score
        doc_score += service_score

        # Insurance valid
        ins_score = 3 if vehicle.insurance_valid else 0
        breakdown['insurance'] = ins_score
        doc_score += ins_score

        # Accident history
        accident_score = 0 if vehicle.accident_history else 2
        breakdown['accident_history'] = accident_score
        doc_score += accident_score

        if vehicle.accident_history:
            self.warnings.append("⚠️ Accident history reported. Detailed inspection recommended.")

        # Calculate weighted total (out of 100)
        total_score = (
            (engine_score / 35) * 35 +
            (body_score / 25) * 25 +
            (mechanical_score / 15) * 15 +
            (comfort_score / 15) * 15 +
            (doc_score / 10) * 10
        )

        # Ensure score is within 0-100
        total_score = max(0, min(100, total_score))

        # Map score to grade
        if total_score >= 90:
            grade = ConditionGrade.EXCELLENT
        elif total_score >= 75:
            grade = ConditionGrade.VERY_GOOD
        elif total_score >= 50:
            grade = ConditionGrade.GOOD
        else:
            grade = ConditionGrade.FAIR

        return total_score, grade, breakdown

    def get_condition_multiplier(self, grade: ConditionGrade) -> float:
        """
        Map condition grade to valuation multiplier

        Args:
            grade: Condition grade

        Returns:
            Multiplier for final valuation
        """
        multipliers = {
            ConditionGrade.EXCELLENT: 1.10,  # +10% premium
            ConditionGrade.VERY_GOOD: 1.05,  # +5% premium
            ConditionGrade.GOOD: 1.00,       # Baseline
            ConditionGrade.FAIR: 0.85        # -15% discount
        }
        return multipliers[grade]

    def calculate_ownership_factor(self, owners: int) -> float:
        """Get ownership multiplier"""
        return self.OWNERSHIP_MULTIPLIERS.get(owners, 0.75)

    def calculate_hyderabad_factor(self, make: str, model: str, fuel_type: FuelType,
                                   age_years: float) -> float:
        """
        Calculate Hyderabad-specific location multiplier

        Args:
            make: Vehicle make
            model: Vehicle model
            fuel_type: Fuel type
            age_years: Vehicle age

        Returns:
            Location multiplier
        """
        multiplier = self.HYDERABAD_FACTORS['default']

        # Diesel premium (no ban in Hyderabad unlike Delhi)
        if fuel_type == FuelType.DIESEL and age_years > 5:
            multiplier *= self.HYDERABAD_FACTORS['diesel_premium']
            self.recommendations.append(
                "✅ Diesel vehicle in Hyderabad market: No age-based ban. Premium applied."
            )

        # Tech hub premium for specific segments
        tech_hub_models = ['baleno', 'i20', 'creta', 'venue', 'seltos', 'city', 'verna']
        if any(m in model.lower() for m in tech_hub_models) and 3 <= age_years <= 5:
            multiplier *= self.HYDERABAD_FACTORS['tech_hub_premium']
            self.recommendations.append(
                "✅ High-demand model in Hyderabad IT corridor market. Premium applied."
            )

        return multiplier

    def calculate_transaction_prices(self, fmv: float) -> Dict[str, float]:
        """
        Calculate all four transaction context prices with GST

        Args:
            fmv: Fair Market Value (C2C baseline)

        Returns:
            Dictionary with all four prices
        """
        # C2C - Fair Market Value (baseline)
        c2c_price = fmv

        # C2B - Trade-in price (Individual selling to dealer/company)
        # Company pays LESS than FMV to account for reconditioning and profit margin
        c2b_price = fmv * (1 - self.DEALER_MARGIN)

        # B2C - Retail price (Dealer selling to individual)
        # Dealer charges MORE than FMV
        margin_amount = fmv * self.DEALER_MARGIN
        gst_on_margin = margin_amount * self.GST_RATE
        b2c_price = fmv + margin_amount + gst_on_margin

        # B2B - Wholesale price (Dealer to dealer)
        # Lower than C2B as it's bulk/auction pricing
        b2b_price = fmv * (1 - self.DEALER_MARGIN - self.WHOLESALE_DISCOUNT)

        return {
            'c2c': c2c_price,
            'c2b': c2b_price,  # THIS IS PROCUREMENT PRICE
            'b2c': b2c_price,
            'b2b': b2b_price
        }

    def valuation(self, vehicle: VehicleInput) -> ValuationResult:
        """
        Main valuation function - orchestrates all sub-algorithms

        Args:
            vehicle: Complete vehicle input data

        Returns:
            Comprehensive valuation result
        """
        # Reset warnings and recommendations
        self.warnings = []
        self.recommendations = []

        # 1. Calculate vehicle age
        age_years = self.calculate_vehicle_age(vehicle.registration_date)

        # 2. Get base price using correct methodology
        # HYBRID APPROACH: Current production uses CURRENT prices, discontinued uses HISTORICAL prices
        if self.is_discontinued(vehicle.make, vehicle.model):
            # Discontinued model: Use ORIGINAL purchase price
            month = vehicle.registration_date.month if hasattr(vehicle, 'registration_date') else 3
            base_price = self.get_original_on_road_price(
                vehicle.make, vehicle.model, vehicle.variant, vehicle.year, month, vehicle.fuel_type
            )
            self.recommendations.append(
                f"🔄 Discontinued model detected - using HISTORICAL pricing methodology"
            )
        else:
            # Current production: Use CURRENT new vehicle price
            base_price = self.get_current_on_road_price(
                vehicle.make, vehicle.model, vehicle.variant, vehicle.fuel_type
            )
            self.recommendations.append(
                f"✅ Current production model - using CURRENT pricing methodology"
            )

        # 3. Calculate segmented depreciation
        depreciated_value, dep_breakdown, dep_percentage = self.calculate_segmented_depreciation(
            age_years, base_price
        )

        # 4. Calculate odometer adjustment
        usage_factor, odo_deviation, expected_odo = self.calculate_odometer_adjustment(
            age_years, vehicle.odometer, vehicle.fuel_type
        )
        usage_adjusted_value = depreciated_value * usage_factor

        # 5. Calculate condition score
        condition_score, condition_grade, condition_breakdown = self.calculate_condition_score(vehicle)
        condition_multiplier = self.get_condition_multiplier(condition_grade)
        condition_adjusted_value = usage_adjusted_value * condition_multiplier

        # 6. Apply ownership factor
        ownership_multiplier = self.calculate_ownership_factor(vehicle.owners)
        value_after_ownership = condition_adjusted_value * ownership_multiplier

        # 7. Apply Hyderabad location factor
        location_multiplier = self.calculate_hyderabad_factor(
            vehicle.make, vehicle.model, vehicle.fuel_type, age_years
        )
        value_after_location = value_after_ownership * location_multiplier

        # 8. Apply market sentiment adjustments (OBV KEY FEATURE)
        market_sentiment_multiplier = 1.00
        if MARKET_SENTIMENT_AVAILABLE:
            fuel_str = vehicle.fuel_type.value if isinstance(vehicle.fuel_type, FuelType) else str(vehicle.fuel_type)

            sentiment_mult, sentiment_breakdown = calculate_market_sentiment_multiplier(
                vehicle.make, vehicle.model, fuel_str, vehicle.year
            )

            market_sentiment_multiplier = sentiment_mult

            self.recommendations.append(f"📊 Market Sentiment: {sentiment_breakdown['notes']}")
            self.recommendations.append(f"   Fuel type: {sentiment_breakdown['fuel_type']['reason']}")
            self.recommendations.append(f"   Segment: {sentiment_breakdown['segment']['reason']}")

            # Brand resale value
            brand_mult, brand_reason = get_brand_resale_multiplier(vehicle.make)
            market_sentiment_multiplier *= brand_mult
            self.recommendations.append(f"   Brand: {brand_reason}")

        final_fmv = value_after_location * market_sentiment_multiplier

        # 9. Calculate all transaction context prices
        transaction_prices = self.calculate_transaction_prices(final_fmv)

        # 9. Calculate procurement price range (C2B with buffer)
        # Company should pay between 95% to 100% of calculated C2B
        # This gives negotiation room while staying profitable
        trade_in_min = transaction_prices['c2b'] * 0.95
        trade_in_max = transaction_prices['c2b'] * 1.00

        # 10. Add final recommendations
        if condition_grade == ConditionGrade.EXCELLENT:
            self.recommendations.append(
                "✅ EXCELLENT condition. Can be sold at premium pricing."
            )
        elif condition_grade == ConditionGrade.FAIR:
            self.recommendations.append(
                "⚠️ FAIR condition. Reconditioning required before resale."
            )

        if vehicle.owners >= 3:
            self.warnings.append(
                f"⚠️ {vehicle.owners} owners. Financing may be difficult for buyers."
            )

        # Create result object
        result = ValuationResult(
            # Core prices
            fair_market_value=round(final_fmv, 2),
            retail_price=round(transaction_prices['b2c'], 2),
            trade_in_price=round(transaction_prices['c2b'], 2),
            wholesale_price=round(transaction_prices['b2b'], 2),

            # Breakdown
            base_price=round(base_price, 2),
            depreciated_value=round(depreciated_value, 2),
            usage_adjusted_value=round(usage_adjusted_value, 2),
            condition_adjusted_value=round(condition_adjusted_value, 2),

            # Factors
            depreciation_percentage=round(dep_percentage, 2),
            usage_factor=round(usage_factor, 4),
            condition_score=round(condition_score, 2),
            condition_multiplier=round(condition_multiplier, 2),
            ownership_multiplier=round(ownership_multiplier, 2),
            location_multiplier=round(location_multiplier, 2),

            # Insights
            condition_grade=condition_grade,
            odometer_deviation=odo_deviation,
            expected_odometer=expected_odo,

            # Procurement range
            trade_in_min=round(trade_in_min, 2),
            trade_in_max=round(trade_in_max, 2),

            # Details
            depreciation_breakdown=dep_breakdown,
            condition_breakdown=condition_breakdown,
            warnings=self.warnings,
            recommendations=self.recommendations
        )

        return result


# Example usage
if __name__ == "__main__":
    # Test case: 2019 Hyundai Creta
    test_vehicle = VehicleInput(
        make="Hyundai",
        model="Creta",
        variant="SX Diesel",
        year=2019,
        registration_date=date(2019, 3, 15),
        fuel_type=FuelType.DIESEL,
        odometer=75000,
        owners=1,
        transmission="Manual",

        # Condition inspection
        frame_damage=False,
        dents_scratches="Minor",
        repainted=False,
        engine_smoke="None",
        tire_tread=60,
        ac_working=True,
        electrical_issues=False,
        service_history=True,
        insurance_valid=True,
        accident_history=False,

        engine_noise="Normal",
        transmission_condition="Smooth",
        suspension_condition="Good",
        brake_condition="Good",
        interior_condition="Good",
        rust_present=False
    )

    # Run valuation
    engine = OBVHyderabadEngine()
    result = engine.valuation(test_vehicle)

    # Print results
    print("=" * 80)
    print("OBV HYDERABAD VALUATION REPORT")
    print("=" * 80)
    print(f"\nVehicle: {test_vehicle.year} {test_vehicle.make} {test_vehicle.model} {test_vehicle.variant}")
    print(f"Odometer: {test_vehicle.odometer:,} km")
    print(f"Condition Grade: {result.condition_grade.value}")
    print(f"\n{'TRANSACTION PRICES':^80}")
    print("-" * 80)
    print(f"Fair Market Value (C2C):     ₹{result.fair_market_value:,.2f}")
    print(f"Retail Price (B2C):          ₹{result.retail_price:,.2f}")
    print(f"TRADE-IN PRICE (C2B):        ₹{result.trade_in_price:,.2f} ⭐ PROCUREMENT")
    print(f"Wholesale Price (B2B):       ₹{result.wholesale_price:,.2f}")
    print(f"\n{'PROCUREMENT RANGE':^80}")
    print("-" * 80)
    print(f"Minimum Offer:               ₹{result.trade_in_min:,.2f}")
    print(f"Maximum Offer:               ₹{result.trade_in_max:,.2f}")
    print("\n" + "=" * 80)
