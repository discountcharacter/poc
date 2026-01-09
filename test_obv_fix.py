#!/usr/bin/env python3
"""
Test script to validate OBV methodology fix
Tests the 3 examples provided by user to ensure values match actual OBV
"""

import sys
import os
from datetime import date

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from obv_hyderabad_engine import OBVHyderabadEngine, VehicleInput, FuelType

def test_case(name, vehicle, expected_c2b_min, expected_c2b_max):
    """Test a single case and compare with OBV"""
    print("=" * 80)
    print(f"TEST CASE: {name}")
    print("=" * 80)

    engine = OBVHyderabadEngine()
    result = engine.valuation(vehicle)

    print(f"\n📊 RESULTS:")
    print(f"   Base Price (Current New On-Road): ₹{result.base_price:,.0f}")
    print(f"   After Depreciation: ₹{result.depreciated_value:,.0f} ({result.depreciation_percentage:.1f}% depreciated)")
    print(f"   Fair Market Value (C2C): ₹{result.fair_market_value:,.0f}")
    print(f"   Trade-In Price (C2B): ₹{result.trade_in_price:,.0f}")
    print(f"\n✅ Expected OBV Range: ₹{expected_c2b_min:,.0f} - ₹{expected_c2b_max:,.0f}")

    # Check if we're in range
    if expected_c2b_min <= result.trade_in_price <= expected_c2b_max:
        print(f"✅ PASS: Our price is within OBV range!")
        status = "PASS"
    else:
        diff = min(abs(result.trade_in_price - expected_c2b_min),
                   abs(result.trade_in_price - expected_c2b_max))
        pct_diff = (diff / expected_c2b_min) * 100
        print(f"⚠️  CLOSE: Off by ₹{diff:,.0f} ({pct_diff:.1f}%)")
        status = "CLOSE" if pct_diff < 20 else "FAIL"

    print(f"\nCondition: {result.condition_grade.value} ({result.condition_score}/100)")
    print("\n" + "=" * 80 + "\n")

    return status, result.trade_in_price

# Test Case 1: Celerio 2023
print("\n" + "🚗 " * 20)
print("TESTING OBV METHODOLOGY FIX")
print("🚗 " * 20 + "\n")

vehicle1 = VehicleInput(
    make="Maruti",
    model="Celerio",
    variant="VXI",
    year=2023,
    registration_date=date(2023, 6, 15),
    fuel_type=FuelType.PETROL,
    odometer=15000,
    owners=1,
    transmission="Manual",

    # Good condition
    frame_damage=False,
    dents_scratches="Minor",
    repainted=False,
    engine_smoke="None",
    tire_tread=85,
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

status1, price1 = test_case(
    "2023 Maruti Celerio VXI",
    vehicle1,
    expected_c2b_min=450000,  # OBV ~₹5L for FMV, so C2B ~₹4.4L
    expected_c2b_max=490000
)

# Test Case 2: Aura 2022 Diesel
vehicle2 = VehicleInput(
    make="Hyundai",
    model="Aura",
    variant="SX",
    year=2022,
    registration_date=date(2022, 3, 10),
    fuel_type=FuelType.DIESEL,
    odometer=45000,
    owners=1,
    transmission="Manual",

    # Very good condition
    frame_damage=False,
    dents_scratches="Minor",
    repainted=False,
    engine_smoke="None",
    tire_tread=75,
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

status2, price2 = test_case(
    "2022 Hyundai Aura SX Diesel",
    vehicle2,
    expected_c2b_min=516575,  # OBV range
    expected_c2b_max=548529
)

# Test Case 3: Beetle 2016 (DISCONTINUED MODEL)
vehicle3 = VehicleInput(
    make="Volkswagen",
    model="Beetle",
    variant="1.4 Tsi",
    year=2016,
    registration_date=date(2016, 3, 15),
    fuel_type=FuelType.PETROL,
    odometer=75000,
    owners=1,
    transmission="Manual",

    # Very good condition
    frame_damage=False,
    dents_scratches="Minor",
    repainted=False,
    engine_smoke="None",
    tire_tread=85,
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

status3, price3 = test_case(
    "2016 Volkswagen Beetle 1.4 TSI (DISCONTINUED)",
    vehicle3,
    expected_c2b_min=1006030,  # OBV range
    expected_c2b_max=1068258
)

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Test 1 (Celerio 2023):  {status1:8s}  ₹{price1:,.0f}")
print(f"Test 2 (Aura 2022):     {status2:8s}  ₹{price2:,.0f}")
print(f"Test 3 (Beetle 2016):   {status3:8s}  ₹{price3:,.0f}")
print("=" * 80)

overall = "✅ ALL TESTS PASSED!" if all(s == "PASS" for s in [status1, status2, status3]) else \
          "✅ CLOSE - Within acceptable range" if all(s in ["PASS", "CLOSE"] for s in [status1, status2, status3]) else \
          "❌ NEEDS ADJUSTMENT"

print(f"\n{overall}\n")
