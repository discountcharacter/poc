"""
Multi-Source Price Validation Engine
====================================
Fetches ex-showroom prices from multiple sources and validates for accuracy.

This is the GOLD STANDARD for accurate vehicle pricing:
1. Fetches from 8+ sources (official + aggregators)
2. Cross-validates prices across sources
3. Assigns confidence scores based on agreement
4. Returns the most accurate price with metadata

Confidence Levels:
- VERY HIGH: Official website + 2+ aggregators agree (within 3%)
- HIGH: Official website OR 3+ aggregators agree (within 3%)
- MEDIUM: 2 sources agree (within 5%)
- LOW: Only 1 source found
- FAILED: No sources found or sources disagree significantly
"""

import statistics
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum

# Import all scrapers
try:
    from official_manufacturer_scrapers import get_official_price
    OFFICIAL_AVAILABLE = True
except ImportError:
    OFFICIAL_AVAILABLE = False
    print("⚠️ Official manufacturer scrapers not available")

try:
    from simple_price_scraper import scrape_cardekho_simple, scrape_carwale_simple
    SIMPLE_SCRAPERS_AVAILABLE = True
except ImportError:
    SIMPLE_SCRAPERS_AVAILABLE = False
    print("⚠️ Simple scrapers not available")

try:
    from aggregator_scrapers import scrape_zigwheels, scrape_v3cars, scrape_autocar_india, scrape_smartprix
    AGGREGATOR_SCRAPERS_AVAILABLE = True
except ImportError:
    AGGREGATOR_SCRAPERS_AVAILABLE = False
    print("⚠️ Aggregator scrapers not available")


class ConfidenceLevel(Enum):
    """Price confidence levels"""
    VERY_HIGH = "Very High (Official + Multiple Aggregators Agree)"
    HIGH = "High (Official OR Multiple Aggregators Agree)"
    MEDIUM = "Medium (2 Sources Agree)"
    LOW = "Low (Single Source Only)"
    FAILED = "Failed (No Sources OR Significant Disagreement)"


@dataclass
class PriceResult:
    """Validated price result with metadata"""
    price: float
    confidence: ConfidenceLevel
    sources_count: int
    sources_used: List[str]
    price_range: Tuple[float, float]  # (min, max) from all sources
    disagreement_pct: float  # Percentage disagreement between sources
    warnings: List[str]
    source_urls: List[str]


def calculate_agreement(prices: List[float]) -> float:
    """
    Calculate percentage disagreement between prices

    Returns:
        Disagreement percentage (0 = perfect agreement, 100 = extreme disagreement)
    """
    if len(prices) <= 1:
        return 0.0

    mean_price = statistics.mean(prices)
    max_deviation = max(abs(p - mean_price) for p in prices)

    return (max_deviation / mean_price) * 100


def validate_prices(price_data: List[Tuple[float, str, str]]) -> PriceResult:
    """
    Validate prices from multiple sources and determine best price

    Args:
        price_data: List of (price, source_name, source_url) tuples

    Returns:
        PriceResult with validated price and confidence metadata
    """
    if not price_data:
        return PriceResult(
            price=0.0,
            confidence=ConfidenceLevel.FAILED,
            sources_count=0,
            sources_used=[],
            price_range=(0.0, 0.0),
            disagreement_pct=0.0,
            warnings=["❌ No price sources found"],
            source_urls=[]
        )

    prices = [p[0] for p in price_data]
    sources = [p[1] for p in price_data]
    urls = [p[2] for p in price_data]

    # Calculate statistics
    mean_price = statistics.mean(prices)
    median_price = statistics.median(prices)
    min_price = min(prices)
    max_price = max(prices)
    disagreement = calculate_agreement(prices)

    # Check if official source is present
    has_official = any('Official' in s for s in sources)
    num_aggregators = sum(1 for s in sources if 'Official' not in s)

    warnings = []

    # Determine confidence level
    if has_official and num_aggregators >= 2 and disagreement <= 3.0:
        # VERY HIGH: Official + multiple aggregators agree within 3%
        confidence = ConfidenceLevel.VERY_HIGH
        final_price = mean_price  # Use mean when high agreement

    elif has_official and disagreement <= 5.0:
        # HIGH: Official source present with reasonable agreement
        confidence = ConfidenceLevel.HIGH
        # Prefer official price
        official_price = next((p[0] for p in price_data if 'Official' in p[1]), mean_price)
        final_price = official_price

    elif num_aggregators >= 3 and disagreement <= 3.0:
        # HIGH: 3+ aggregators agree within 3%
        confidence = ConfidenceLevel.HIGH
        final_price = median_price  # Use median to avoid outliers

    elif len(prices) >= 2 and disagreement <= 5.0:
        # MEDIUM: 2+ sources agree within 5%
        confidence = ConfidenceLevel.MEDIUM
        final_price = median_price
        warnings.append(f"⚠️ Price based on {len(prices)} sources with {disagreement:.1f}% variance")

    elif len(prices) == 1:
        # LOW: Only single source
        confidence = ConfidenceLevel.LOW
        final_price = prices[0]
        warnings.append("⚠️ Price from single source only - consider manual verification")

    else:
        # FAILED: Significant disagreement
        confidence = ConfidenceLevel.FAILED
        final_price = median_price  # Return median but flag as unreliable
        warnings.append(f"❌ HIGH DISAGREEMENT: {disagreement:.1f}% variance between sources")
        warnings.append(f"   Price range: ₹{min_price:,.0f} - ₹{max_price:,.0f}")
        warnings.append("   ⚠️ MANUAL VERIFICATION REQUIRED")

    # Additional validation warnings
    if disagreement > 10.0:
        warnings.append(f"⚠️ Sources disagree by {disagreement:.1f}% - verify manually")

    if max_price / min_price > 1.15:  # More than 15% difference
        warnings.append(f"⚠️ Wide price range: ₹{min_price:,.0f} to ₹{max_price:,.0f}")

    return PriceResult(
        price=round(final_price, 0),
        confidence=confidence,
        sources_count=len(prices),
        sources_used=sources,
        price_range=(min_price, max_price),
        disagreement_pct=disagreement,
        warnings=warnings,
        source_urls=urls
    )


def get_validated_price(make: str, model: str, variant: str, fuel: str = "Petrol",
                       city: str = "hyderabad") -> PriceResult:
    """
    Get validated ex-showroom price from multiple sources

    Fetching Strategy:
    1. Official manufacturer website (HIGHEST PRIORITY)
    2. CarDekho (comprehensive coverage)
    3. CarWale (alternative aggregator)
    4. ZigWheels (additional validation)
    5. V3Cars (additional validation)
    6. AutocarIndia (additional validation)
    7. Smartprix (additional validation)

    Args:
        make: Vehicle manufacturer (e.g., "Maruti Suzuki")
        model: Model name (e.g., "Swift")
        variant: Specific variant (e.g., "VXI")
        fuel: Fuel type (e.g., "Petrol")
        city: City for pricing (default: "hyderabad")

    Returns:
        PriceResult with validated price and confidence metadata
    """
    print(f"\n{'='*60}")
    print(f"🎯 MULTI-SOURCE PRICE VALIDATION")
    print(f"   Vehicle: {make} {model} {variant} ({fuel})")
    print(f"   Location: {city}")
    print(f"{'='*60}\n")

    price_data = []

    # TIER 1: Official Manufacturer Website (MOST ACCURATE)
    print("🏢 TIER 1: Official Manufacturer Website")
    print("-" * 60)
    if OFFICIAL_AVAILABLE:
        official_result = get_official_price(make, model, variant, city)
        if official_result:
            price, url = official_result
            price_data.append((price, f"{make} Official", url))
            print(f"✅ Official: ₹{price:,.0f} from {make}")
        else:
            print(f"❌ Official: Not found for {make}")
    else:
        print("⚠️ Official scrapers not available")

    print()

    # TIER 2: Primary Aggregators (COMPREHENSIVE COVERAGE)
    print("🔍 TIER 2: Primary Aggregators")
    print("-" * 60)

    if SIMPLE_SCRAPERS_AVAILABLE:
        # CarDekho
        cardekho_result = scrape_cardekho_simple(make, model, variant)
        if cardekho_result:
            price, url = cardekho_result
            price_data.append((price, "CarDekho", url))

        # CarWale
        carwale_result = scrape_carwale_simple(make, model, variant)
        if carwale_result:
            price, url = carwale_result
            price_data.append((price, "CarWale", url))
    else:
        print("⚠️ Simple scrapers not available")

    print()

    # TIER 3: Additional Aggregators (VALIDATION)
    print("📊 TIER 3: Additional Aggregators (Validation)")
    print("-" * 60)

    if AGGREGATOR_SCRAPERS_AVAILABLE:
        # ZigWheels
        zigwheels_result = scrape_zigwheels(make, model, variant)
        if zigwheels_result:
            price, url = zigwheels_result
            price_data.append((price, "ZigWheels", url))

        # V3Cars
        v3cars_result = scrape_v3cars(make, model, variant)
        if v3cars_result:
            price, url = v3cars_result
            price_data.append((price, "V3Cars", url))

        # AutocarIndia
        autocar_result = scrape_autocar_india(make, model, variant)
        if autocar_result:
            price, url = autocar_result
            price_data.append((price, "AutocarIndia", url))

        # Smartprix
        smartprix_result = scrape_smartprix(make, model, variant)
        if smartprix_result:
            price, url = smartprix_result
            price_data.append((price, "Smartprix", url))
    else:
        print("⚠️ Aggregator scrapers not available")

    print()
    print("=" * 60)
    print("📊 VALIDATION RESULTS")
    print("=" * 60)

    # Validate and return result
    result = validate_prices(price_data)

    # Print summary
    print(f"\n✅ Final Price: ₹{result.price:,.0f}")
    print(f"🎯 Confidence: {result.confidence.value}")
    print(f"📊 Sources: {result.sources_count} ({', '.join(result.sources_used)})")
    print(f"📈 Price Range: ₹{result.price_range[0]:,.0f} - ₹{result.price_range[1]:,.0f}")
    print(f"📉 Disagreement: {result.disagreement_pct:.1f}%")

    if result.warnings:
        print(f"\n⚠️ Warnings:")
        for warning in result.warnings:
            print(f"   {warning}")

    print("=" * 60)

    return result


# Convenience function for OBV engine integration
def get_accurate_price(make: str, model: str, variant: str, fuel: str = "Petrol",
                      city: str = "hyderabad") -> Tuple[Optional[float], str, List[str]]:
    """
    Get accurate price for OBV engine integration

    Returns:
        Tuple of (price, confidence_level, warnings)
    """
    result = get_validated_price(make, model, variant, fuel, city)

    if result.confidence == ConfidenceLevel.FAILED:
        return (None, result.confidence.value, result.warnings)

    return (result.price, result.confidence.value, result.warnings)
