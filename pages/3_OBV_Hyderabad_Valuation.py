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
import sys
import os

# Optional plotly import (fallback if not available)
try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

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
    page_title="OBV Algo Valuation",
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
st.markdown('<h1 class="main-title">OBV Algo Valuation</h1>', unsafe_allow_html=True)

# Main content - Input Form
st.markdown("### 📋 Vehicle Details")

# Basic Information
st.markdown("#### Basic Information")
make = st.text_input("Make", value="Maruti Suzuki", help="e.g., Maruti, Hyundai, Honda")
model = st.text_input("Model", value="Swift", help="e.g., Swift, City, Creta")
variant = st.text_input("Variant", value="VXI", help="e.g., VXi, SX, ZX+")

col1, col2 = st.columns(2)
with col1:
    year = st.selectbox(
        "Year",
        options=list(range(datetime.now().year, 1989, -1)),
        index=6,  # Default to 2020
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
        index=0,  # Default Petrol
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
        st.markdown(f"""
        <div style="font-size: 0.85rem; color: #666; text-transform: uppercase; letter-spacing: 0.5px;">Vehicle</div>
        <div style="font-size: 1.1rem; font-weight: 600; margin-top: 0.3rem;">{year} {make} {model}</div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div style="font-size: 0.85rem; color: #666; text-transform: uppercase; letter-spacing: 0.5px;">Odometer</div>
        <div style="font-size: 1.1rem; font-weight: 600; margin-top: 0.3rem;">{odometer:,} km</div>
        """, unsafe_allow_html=True)
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
        st.markdown(f"""
        <div style="font-size: 0.85rem; color: #666; text-transform: uppercase; letter-spacing: 0.5px;">Age</div>
        <div style="font-size: 1.1rem; font-weight: 600; margin-top: 0.3rem;">{age:.1f} years</div>
        """, unsafe_allow_html=True)

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
        if PLOTLY_AVAILABLE:
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
        else:
            # Fallback: Table-based breakdown
            st.markdown("**Price Waterfall: Base Price → Fair Market Value**")
            breakdown_data = {
                "Step": [
                    "1. Base Price (Current New)",
                    "2. After Depreciation",
                    "3. After Odometer Adjustment",
                    "4. After Condition Adjustment",
                    "5. After Ownership Factor",
                    "6. After Location Factor",
                    "**Final Fair Market Value**"
                ],
                "Price": [
                    f"₹{result.base_price:,.0f}",
                    f"₹{result.depreciated_value:,.0f}",
                    f"₹{result.usage_adjusted_value:,.0f}",
                    f"₹{result.condition_adjusted_value:,.0f}",
                    f"₹{result.condition_adjusted_value * result.ownership_multiplier:,.0f}",
                    f"₹{result.fair_market_value:,.0f}",
                    f"**₹{result.fair_market_value:,.0f}**"
                ],
                "Change": [
                    "—",
                    f"₹{result.depreciated_value - result.base_price:,.0f}",
                    f"₹{result.usage_adjusted_value - result.depreciated_value:,.0f}",
                    f"₹{result.condition_adjusted_value - result.usage_adjusted_value:,.0f}",
                    f"₹{result.condition_adjusted_value * (result.ownership_multiplier - 1):,.0f}",
                    f"₹{result.fair_market_value - result.condition_adjusted_value * result.ownership_multiplier:,.0f}",
                    "—"
                ]
            }
            st.dataframe(pd.DataFrame(breakdown_data), use_container_width=True, hide_index=True)

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


# Footer
st.markdown("""
<div class="footer">
    <strong>OBV Algo Valuation v1.0</strong><br>
    Powered by Advanced Algorithmic Pricing<br>
    <em>For procurement and trade-in pricing accuracy</em>
</div>
""", unsafe_allow_html=True)
