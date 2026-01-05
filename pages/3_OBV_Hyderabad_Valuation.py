"""
OBV Hyderabad Valuation Portal

Orange Book Value (OBV) style algorithmic vehicle valuation system
specifically calibrated for the Hyderabad automotive market.

This is the 4th valuation URL/system alongside:
1. Main Agent Portal
2. Legacy Dashboard
3. Cars24 Valuation

Key Features:
- IRDAI-based segmented depreciation
- Tiered odometer penalty system
- 16-point condition scoring
- Transaction context pricing (C2C, B2C, C2B, B2B)
- Hyderabad-specific market factors
- Procurement-focused (C2B pricing for company buying vehicles)
"""

import streamlit as st
from datetime import date, datetime
import pandas as pd
import plotly.graph_objects as go
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from obv_hyderabad_engine import (
    OBVHyderabadEngine,
    VehicleInput,
    FuelType,
    ConditionGrade,
    TransactionType
)

# Page configuration
st.set_page_config(
    page_title="OBV Hyderabad Valuation",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    /* Main title styling */
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }

    .subtitle {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }

    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Procurement card - special styling */
    .procurement-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        border: 3px solid #fff;
    }

    /* Warning/Recommendation boxes */
    .warning-box {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 4px;
    }

    .recommendation-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 4px;
    }

    /* Section headers */
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        margin: 2rem 0 1rem 0;
        color: #333;
        border-bottom: 2px solid #667eea;
        padding-bottom: 0.5rem;
    }

    /* Condition badge */
    .condition-excellent {
        background-color: #28a745;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }

    .condition-very-good {
        background-color: #17a2b8;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }

    .condition-good {
        background-color: #ffc107;
        color: #333;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }

    .condition-fair {
        background-color: #dc3545;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }

    /* Info cards */
    .info-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }

    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem;
        color: #666;
        font-size: 0.9rem;
        margin-top: 3rem;
        border-top: 1px solid #eee;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-title">🏆 OBV Hyderabad Valuation Engine</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle">Orange Book Value Style Algorithmic Pricing • Hyderabad Market Calibrated • '
    'Procurement Optimized</p>',
    unsafe_allow_html=True
)

# Info banner
st.info(
    "**🎯 Purpose:** This system provides accurate vehicle valuations for procurement (trade-in). "
    "The **C2B Trade-In Price** is what your company should offer to purchase the vehicle from individuals. "
    "It accounts for reconditioning costs and ensures profitable resale margins."
)

# Sidebar - Input Form
with st.sidebar:
    st.markdown("### 📋 Vehicle Details")

    # Basic Information
    st.markdown("#### Basic Information")
    make = st.text_input("Make", value="Hyundai", help="e.g., Maruti, Hyundai, Honda")
    model = st.text_input("Model", value="Creta", help="e.g., Swift, City, Creta")
    variant = st.text_input("Variant", value="SX Diesel", help="e.g., VXi, SX, ZX+")

    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox(
            "Year",
            options=list(range(datetime.now().year, 1989, -1)),
            index=5,  # Default to 5 years old
            help="Manufacturing year"
        )
    with col2:
        month = st.selectbox(
            "Month",
            options=list(range(1, 13)),
            index=2,  # Default March
            help="Registration month"
        )

    # Calculate registration date
    try:
        reg_date = date(year, month, 15)  # Use 15th as default day
    except:
        reg_date = date(year, 1, 15)

    # Fuel and Transmission
    col1, col2 = st.columns(2)
    with col1:
        fuel_type_str = st.selectbox(
            "Fuel Type",
            options=["Petrol", "Diesel", "CNG", "Electric"],
            index=1,  # Default Diesel
            help="Fuel type affects standard mileage expectations"
        )
    with col2:
        transmission = st.selectbox(
            "Transmission",
            options=["Manual", "Automatic"],
            index=0
        )

    # Convert fuel type string to enum
    fuel_type = FuelType[fuel_type_str.upper()]

    # Usage Information
    st.markdown("#### Usage Information")
    col1, col2 = st.columns(2)
    with col1:
        odometer = st.number_input(
            "Odometer (km)",
            min_value=0,
            max_value=500000,
            value=75000,
            step=1000,
            help="Total kilometers driven"
        )
    with col2:
        owners = st.selectbox(
            "Number of Owners",
            options=[1, 2, 3, 4],
            index=0,
            help="Number of previous owners"
        )

    location = st.text_input("Location", value="Hyderabad", help="City/Region")

    # Condition Inspection
    st.markdown("#### 🔍 Condition Inspection (16-Point)")

    with st.expander("🚗 Body & Exterior", expanded=False):
        frame_damage = st.checkbox("Frame Damage", value=False, help="Critical structural damage")
        dents_scratches = st.select_slider(
            "Dents & Scratches",
            options=["None", "Minor", "Moderate", "Severe"],
            value="Minor"
        )
        repainted = st.checkbox("Repainted", value=False, help="Any panels repainted")
        rust_present = st.checkbox("Rust Present", value=False)

    with st.expander("🔧 Engine & Transmission", expanded=False):
        engine_smoke = st.selectbox(
            "Engine Smoke",
            options=["None", "White", "Black"],
            index=0,
            help="Smoke from exhaust"
        )
        engine_noise = st.selectbox(
            "Engine Noise",
            options=["Normal", "Slight", "Heavy"],
            index=0
        )
        transmission_condition = st.selectbox(
            "Transmission Condition",
            options=["Smooth", "Rough", "Slipping"],
            index=0
        )

    with st.expander("⚙️ Mechanical Components", expanded=False):
        tire_tread = st.slider(
            "Tire Tread Remaining (%)",
            min_value=0,
            max_value=100,
            value=60,
            step=5
        )
        suspension_condition = st.selectbox(
            "Suspension",
            options=["Excellent", "Good", "Fair", "Poor"],
            index=1
        )
        brake_condition = st.selectbox(
            "Brakes",
            options=["Excellent", "Good", "Fair", "Poor"],
            index=1
        )

    with st.expander("⚡ Electrical & Comfort", expanded=False):
        ac_working = st.checkbox("AC Working", value=True)
        electrical_issues = st.checkbox("Electrical Issues", value=False)
        interior_condition = st.selectbox(
            "Interior Condition",
            options=["Excellent", "Good", "Fair", "Poor"],
            index=1
        )

    with st.expander("📄 Documentation", expanded=False):
        service_history = st.checkbox("Service History Available", value=True)
        insurance_valid = st.checkbox("Insurance Valid", value=True)
        accident_history = st.checkbox("Accident History", value=False)

    # Calculate button
    st.markdown("---")
    calculate_btn = st.button("🚀 Calculate Valuation", type="primary", use_container_width=True)

# Main content area
if calculate_btn:
    # Create vehicle input
    vehicle = VehicleInput(
        make=make,
        model=model,
        variant=variant,
        year=year,
        registration_date=reg_date,
        fuel_type=fuel_type,
        odometer=odometer,
        owners=owners,
        transmission=transmission,
        location=location,

        # Condition data
        frame_damage=frame_damage,
        dents_scratches=dents_scratches,
        repainted=repainted,
        engine_smoke=engine_smoke,
        tire_tread=tire_tread,
        ac_working=ac_working,
        electrical_issues=electrical_issues,
        service_history=service_history,
        insurance_valid=insurance_valid,
        accident_history=accident_history,

        engine_noise=engine_noise,
        transmission_condition=transmission_condition,
        suspension_condition=suspension_condition,
        brake_condition=brake_condition,
        interior_condition=interior_condition,
        rust_present=rust_present
    )

    # Run valuation
    with st.spinner("🔄 Running OBV Algorithm..."):
        engine = OBVHyderabadEngine()
        result = engine.valuation(vehicle)

    st.success("✅ Valuation Complete!")

    # Vehicle Summary
    st.markdown('<div class="section-header">📊 Vehicle Summary</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Vehicle", f"{year} {make} {model}")
    with col2:
        st.metric("Odometer", f"{odometer:,} km")
    with col3:
        # Condition badge
        condition_class = result.condition_grade.value.lower().replace(" ", "-")
        st.markdown(
            f'<div class="condition-{condition_class}">{result.condition_grade.value}</div>',
            unsafe_allow_html=True
        )
        st.caption(f"Condition Score: {result.condition_score}/100")
    with col4:
        age = (date.today() - reg_date).days / 365.25
        st.metric("Age", f"{age:.1f} years")

    # PROCUREMENT PRICING - HERO SECTION
    st.markdown('<div class="section-header">💰 Procurement Pricing (C2B - Company Buying)</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="procurement-card">
        <div class="metric-label">⭐ RECOMMENDED TRADE-IN OFFER</div>
        <div class="metric-value">₹{result.trade_in_price:,.0f}</div>
        <div style="margin-top: 1rem; font-size: 1rem;">
            <strong>Negotiation Range:</strong><br>
            Minimum: ₹{result.trade_in_min:,.0f} | Maximum: ₹{result.trade_in_max:,.0f}
        </div>
        <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9rem;">
            This is the price your company should offer to purchase this vehicle from the owner.
            It accounts for reconditioning costs, resale margin, and market positioning.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Transaction Context Prices
    st.markdown('<div class="section-header">💵 All Transaction Prices</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">Fair Market Value</div>
            <div class="metric-value">₹{:,.0f}</div>
            <div style="font-size: 0.8rem; margin-top: 0.5rem;">C2C • Individual to Individual</div>
        </div>
        """.format(result.fair_market_value), unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <div class="metric-label">⭐ Trade-In Price</div>
            <div class="metric-value">₹{:,.0f}</div>
            <div style="font-size: 0.8rem; margin-top: 0.5rem;">C2B • Company Procurement</div>
        </div>
        """.format(result.trade_in_price), unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="metric-card" style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);">
            <div class="metric-label">Retail Price</div>
            <div class="metric-value" style="color: #333;">₹{:,.0f}</div>
            <div style="font-size: 0.8rem; margin-top: 0.5rem; color: #555;">B2C • Dealer to Individual</div>
        </div>
        """.format(result.retail_price), unsafe_allow_html=True)

    with col4:
        st.markdown("""
        <div class="metric-card" style="background: linear-gradient(135deg, #d299c2 0%, #fef9d7 100%);">
            <div class="metric-label">Wholesale Price</div>
            <div class="metric-value" style="color: #333;">₹{:,.0f}</div>
            <div style="font-size: 0.8rem; margin-top: 0.5rem; color: #555;">B2B • Dealer to Dealer</div>
        </div>
        """.format(result.wholesale_price), unsafe_allow_html=True)

    # Price Breakdown Waterfall
    st.markdown('<div class="section-header">📈 Price Calculation Breakdown</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        # Create waterfall chart
        fig = go.Figure(go.Waterfall(
            name="Valuation",
            orientation="v",
            measure=["absolute", "relative", "relative", "relative", "relative", "relative", "total"],
            x=["Base Price", "Depreciation", "Odometer Adj", "Condition Adj", "Ownership", "Location", "Fair Market Value"],
            textposition="outside",
            text=[
                f"₹{result.base_price:,.0f}",
                f"₹{result.depreciated_value - result.base_price:,.0f}",
                f"₹{result.usage_adjusted_value - result.depreciated_value:,.0f}",
                f"₹{result.condition_adjusted_value - result.usage_adjusted_value:,.0f}",
                f"₹{result.condition_adjusted_value * (result.ownership_multiplier - 1):,.0f}",
                f"₹{result.fair_market_value - result.condition_adjusted_value * result.ownership_multiplier:,.0f}",
                f"₹{result.fair_market_value:,.0f}"
            ],
            y=[
                result.base_price,
                result.depreciated_value - result.base_price,
                result.usage_adjusted_value - result.depreciated_value,
                result.condition_adjusted_value - result.usage_adjusted_value,
                result.condition_adjusted_value * (result.ownership_multiplier - 1),
                result.fair_market_value - result.condition_adjusted_value * result.ownership_multiplier,
                result.fair_market_value
            ],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
        ))

        fig.update_layout(
            title="Price Waterfall: Base Price → Fair Market Value",
            showlegend=False,
            height=400,
            yaxis_title="Price (INR)"
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown("**📊 Adjustment Factors**")
        st.markdown(f"- **Depreciation:** {result.depreciation_percentage:.1f}%")
        st.markdown(f"- **Usage Factor:** {result.usage_factor:.4f}x")
        st.markdown(f"- **Condition Multiplier:** {result.condition_multiplier:.2f}x")
        st.markdown(f"- **Ownership Multiplier:** {result.ownership_multiplier:.2f}x")
        st.markdown(f"- **Location Multiplier:** {result.location_multiplier:.2f}x")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown("**🚗 Odometer Analysis**")
        st.markdown(f"- **Actual:** {odometer:,} km")
        st.markdown(f"- **Expected:** {result.expected_odometer:,} km")
        deviation_sign = "+" if result.odometer_deviation > 0 else ""
        st.markdown(f"- **Deviation:** {deviation_sign}{result.odometer_deviation:,} km")
        st.markdown('</div>', unsafe_allow_html=True)

    # Warnings and Recommendations
    if result.warnings or result.recommendations:
        st.markdown('<div class="section-header">⚠️ Insights & Recommendations</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            if result.warnings:
                st.markdown("**⚠️ Warnings**")
                for warning in result.warnings:
                    st.markdown(f'<div class="warning-box">{warning}</div>', unsafe_allow_html=True)

        with col2:
            if result.recommendations:
                st.markdown("**✅ Recommendations**")
                for rec in result.recommendations:
                    st.markdown(f'<div class="recommendation-box">{rec}</div>', unsafe_allow_html=True)

    # Detailed Breakdown (Expandable)
    with st.expander("🔍 Detailed Technical Breakdown"):
        tab1, tab2, tab3 = st.tabs(["Depreciation", "Condition Scoring", "Transaction Analysis"])

        with tab1:
            st.markdown("### Depreciation Breakdown")

            # Create DataFrame from depreciation breakdown
            if result.depreciation_breakdown:
                dep_df = pd.DataFrame([
                    {"Year": k, "Depreciation Amount": f"₹{v:,.0f}"}
                    for k, v in result.depreciation_breakdown.items()
                ])
                st.dataframe(dep_df, use_container_width=True, hide_index=True)

            st.markdown(f"""
            **Total Depreciation:** {result.depreciation_percentage:.2f}%

            **Base Price (Current New):** ₹{result.base_price:,.0f}

            **Depreciated Value:** ₹{result.depreciated_value:,.0f}

            **Method:** Segmented exponential decay
            - Year 0-1: 17% aggressive drop (new car premium loss)
            - Year 1-3: 11% per year moderate decline
            - Year 3-5: 9% per year slower decline
            - Year 5+: 6% per year plateau
            """)

        with tab2:
            st.markdown("### 16-Point Condition Scoring")

            # Create DataFrame from condition breakdown
            if result.condition_breakdown:
                cond_df = pd.DataFrame([
                    {"Component": k.replace("_", " ").title(), "Score": v}
                    for k, v in result.condition_breakdown.items()
                ])
                st.dataframe(cond_df, use_container_width=True, hide_index=True)

            st.markdown(f"""
            **Overall Condition Score:** {result.condition_score:.2f}/100

            **Condition Grade:** {result.condition_grade.value}

            **Valuation Impact:** {result.condition_multiplier:.2f}x

            **Scoring Weights:**
            - Engine/Transmission: 35%
            - Body/Frame: 25%
            - Tires/Suspension: 15%
            - Electrical/Interior: 15%
            - Documentation: 10%
            """)

        with tab3:
            st.markdown("### Transaction Context Analysis")

            st.markdown(f"""
            **Fair Market Value (C2C):** ₹{result.fair_market_value:,.0f}
            - Baseline price for individual-to-individual transaction
            - No dealer margins or GST

            **Trade-In Price (C2B - PROCUREMENT):** ₹{result.trade_in_price:,.0f}
            - Company purchasing from individual
            - Includes 12% dealer margin discount
            - Accounts for reconditioning costs
            - **Negotiation Range:** ₹{result.trade_in_min:,.0f} - ₹{result.trade_in_max:,.0f}

            **Retail Price (B2C):** ₹{result.retail_price:,.0f}
            - Company/Dealer selling to individual
            - Includes 12% dealer margin
            - Includes 18% GST on margin
            - Formula: FMV + Margin + (Margin × 18% GST)

            **Wholesale Price (B2B):** ₹{result.wholesale_price:,.0f}
            - Dealer-to-dealer auction price
            - Additional 8% discount for bulk/auction
            - Used for inter-dealer transfers

            **Hyderabad Market Factor:** {result.location_multiplier:.2f}x
            - Diesel premium: No age-based ban unlike Delhi
            - Tech hub premium: High demand for premium segments
            - Local road tax considerations
            """)

    # Methodology
    with st.expander("📚 Valuation Methodology"):
        st.markdown("""
        ### OBV-Style Algorithmic Valuation

        This engine implements a comprehensive multi-factor valuation model based on Orange Book Value (OBV)
        methodology, specifically calibrated for the Hyderabad automotive market.

        #### Core Algorithm Components:

        1. **IRDAI-Based Segmented Depreciation**
           - Follows Insurance Regulatory guidelines as baseline
           - Uses continuous decay function instead of step functions
           - Segmented rates: 17% → 11% → 9% → 6% by age brackets
           - Links to current new vehicle price, not historical invoice

        2. **Odometer Deviation Analysis**
           - Calculates expected mileage based on fuel type
           - Standard annual mileage: Petrol (11k), Diesel (16.5k), CNG (20k), Electric (11k)
           - Non-linear penalty tiers: 2% → 4% → 8% → 6%
           - Psychological barriers at 50k, 100k km
           - Tampering detection safeguards

        3. **16-Point Condition Scoring**
           - Weighted inspection across 5 categories
           - Engine/Transmission (35%), Body/Frame (25%), Mechanical (15%), Comfort (15%), Documentation (10%)
           - Maps to 4 grades: Excellent, Very Good, Good, Fair
           - Grade multipliers: 1.10x, 1.05x, 1.00x, 0.85x

        4. **Transaction Context Pricing**
           - C2C: Fair Market Value (baseline)
           - C2B: Trade-in (FMV - 12% margin) ← **PROCUREMENT FOCUS**
           - B2C: Retail (FMV + 12% margin + 18% GST on margin)
           - B2B: Wholesale (FMV - 20%)

        5. **Ownership Factor**
           - 1st owner: 1.00x (no penalty)
           - 2nd owner: 0.93x (-7%)
           - 3rd owner: 0.85x (-15%)
           - 4th+ owner: 0.75x (-25%)

        6. **Hyderabad Location Factor**
           - Diesel premium: 1.05x (no age ban)
           - Tech hub premium: 1.03x (high demand segments)
           - Road tax adjustments for out-of-state registrations

        #### Data Sources:
        - Vehicle master database (make/model/variant pricing)
        - IRDAI depreciation schedule (regulatory baseline)
        - Market research (Hyderabad-specific demand coefficients)
        - Historical transaction data (calibration)

        #### Accuracy & Validation:
        - Segmented depreciation ensures realistic curves
        - Condition scoring eliminates subjective bias
        - Transaction context provides actionable prices
        - Hyderabad calibration accounts for local market dynamics

        #### For Procurement Use:
        - Focus on **C2B Trade-In Price**
        - Conservative estimates to protect profit margins
        - Built-in reconditioning cost buffer
        - Negotiation range (95%-100% of calculated C2B)
        - Warnings flag high-risk vehicles
        """)

else:
    # Landing state - show info
    st.markdown('<div class="section-header">🎯 How It Works</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="info-card">
            <h3>1️⃣ Enter Vehicle Details</h3>
            <p>Fill in the basic vehicle information: Make, Model, Year, Odometer, etc.</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="info-card">
            <h3>2️⃣ Complete Inspection</h3>
            <p>Provide detailed 16-point condition assessment for accurate valuation.</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="info-card">
            <h3>3️⃣ Get Valuation</h3>
            <p>Receive comprehensive pricing across all transaction contexts with detailed breakdown.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">✨ Key Features</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### 🔬 Advanced Algorithms
        - **IRDAI-based segmented depreciation** with continuous decay
        - **Tiered odometer penalties** (non-linear impact)
        - **16-point condition scoring** with weighted components
        - **Hyderabad-specific market calibration**

        ### 💼 Procurement Optimized
        - **C2B Trade-In Pricing** for company purchases
        - **Conservative estimates** to ensure profitability
        - **Negotiation ranges** for flexibility
        - **Risk warnings** for problematic vehicles
        """)

    with col2:
        st.markdown("""
        ### 📊 Comprehensive Insights
        - **4 transaction prices** (C2C, B2C, C2B, B2B)
        - **Detailed breakdowns** of all adjustments
        - **Visual waterfall chart** showing calculation flow
        - **Warnings & recommendations** for decision support

        ### 🏆 Market Accuracy
        - **Current new prices** (not historical invoices)
        - **Fuel-type specific** mileage expectations
        - **Ownership impact** on resale value
        - **GST calculations** for dealer transactions
        """)

    st.markdown('<div class="section-header">📈 Sample Valuations</div>', unsafe_allow_html=True)

    # Sample comparisons
    sample_data = {
        "Vehicle": [
            "2019 Hyundai Creta SX Diesel",
            "2020 Maruti Baleno Delta Petrol",
            "2018 Honda City VX Petrol"
        ],
        "Odometer": ["75,000 km", "45,000 km", "95,000 km"],
        "Condition": ["Good", "Very Good", "Fair"],
        "C2B Trade-In": ["₹8,45,000", "₹5,32,000", "₹4,85,000"],
        "Fair Market Value": ["₹9,60,000", "₹6,05,000", "₹5,52,000"],
        "Retail Price": ["₹11,45,000", "₹7,22,000", "₹6,58,000"]
    }

    st.dataframe(pd.DataFrame(sample_data), use_container_width=True, hide_index=True)

    st.info(
        "💡 **Tip:** The C2B Trade-In price is optimized for your company's procurement. "
        "It ensures sufficient margin for reconditioning and profitable resale."
    )

# Footer
st.markdown("""
<div class="footer">
    <strong>OBV Hyderabad Valuation Engine v1.0</strong><br>
    Powered by Advanced Algorithmic Pricing • Hyderabad Market Calibrated<br>
    <em>For procurement and trade-in pricing accuracy</em>
</div>
""", unsafe_allow_html=True)
