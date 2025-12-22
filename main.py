import streamlit as st
import os
from dotenv import load_dotenv
import pandas as pd

# Load environment variables (Server-side only)
load_dotenv()

from src.engine_logic import calculate_logic_price
from src.engine_scout import fetch_market_prices
from src.engine_oracle import get_gemini_estimate
from src.engine_sniper import fetch_closest_match
from src.engine_ml import get_ml_prediction
from src.engine_smart_scraper import SmartCarScraper
from src.ensemble_predictor import EnsemblePricePredictor
from src.utils import format_currency
import statistics

# Initialize New Engines
@st.cache_resource
def get_smart_scraper():
    return SmartCarScraper()

@st.cache_resource
def get_ensemble_predictor():
    predictor = EnsemblePricePredictor()
    predictor.load_models()
    return predictor

# Optional: Engine F (Cars24) - Requires Playwright
try:
    from src.engine_cars24 import get_cars24_price, session_exists as cars24_session_exists
    CARS24_SUPPORTED = True
except (ImportError, ModuleNotFoundError):
    CARS24_SUPPORTED = False

# Page Config
st.set_page_config(
    page_title="Valuation Portal",
    page_icon=None,
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Modern Futuristic Light Mode CSS
VERSION = "Rescue-v1.0.5"
st.caption(f"Engine Build: {VERSION}")
st.markdown("""
<style>
    /* 1. Force Light Mode Background & Font */
    .stApp {
        background-color: #FFFFFF;
        background-image: 
            radial-gradient(at 0% 0%, hsla(210,100%,96%,1) 0, transparent 50%), 
            radial-gradient(at 100% 0%, hsla(220,100%,96%,1) 0, transparent 50%);
    }

    html, body, [class*="css"] {
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
        color: #111827 !important; 
    }
    
    /* 2. Header Styling (Centered) */
    h1 {
        font-weight: 800;
        font-size: 3rem;
        background: -webkit-linear-gradient(25deg, #2563EB, #1E40AF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        letter-spacing: -1.5px;
        text-align: center;
        width: 100%;
    }
    .subtitle {
        text-align: center;
        font-size: 1.25rem;
        color: #6B7280;
        margin-bottom: 3rem;
        font-weight: 500;
        width: 100%;
        display: block;
    }
    
    /* 3. Input Styling (White Background, Black Text) */
    .stTextInput > div > div, 
    .stSelectbox > div > div, 
    .stNumberInput > div > div {
        background-color: #FFFFFF !important;
        color: #111827 !important;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stNumberInput > div > div > input {
        color: #111827 !important;
        background-color: transparent !important;
    }
    
    /* Input Labels */
    .stTextInput label, .stSelectbox label, .stNumberInput label, .stSlider label {
        color: #374151 !important;
        font-weight: 600;
        font-size: 0.9rem;
    }

    
    /* 5. Metric Cards (Glassmorphism) */
    .metric-props {
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.8);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05); 
        width: 100%;
        height: 100%;
        transition: transform 0.2s ease;
    }
    .metric-props:hover {
        transform: translateY(-2px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05);
    }
    
    .metric-value {
        font-size: 32px;
        font-weight: 800;
        margin-top: 8px;
        color: #2563EB; /* Primary Blue */
    }
    .metric-label {
        font-size: 13px;
        font-weight: 700;
        color: #9CA3AF;
        text-transform: uppercase;
        letter-spacing: 1.2px;
    }
    
    /* 6. Main Price Card (Prominent Glass) */
    .main-price-card {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        border-radius: 24px;
        padding: 60px;
        text-align: center;
        margin-bottom: 50px;
        box-shadow: 0 20px 25px -5px rgba(37, 99, 235, 0.4);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.1);
        position: relative;
        overflow: hidden;
    }
    .main-price-card::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: radial-gradient(circle at top right, rgba(255,255,255,0.2), transparent);
        pointer-events: none;
    }

    .main-price-val {
        font-size: 80px;
        font-weight: 800;
        color: #FFFFFF;
        font-feature-settings: "tnum";
        text-shadow: 0 2px 20px rgba(0,0,0,0.15);
        line-height: 1.1;
    }
    .main-price-sub {
        color: rgba(255, 255, 255, 0.9);
        font-size: 18px;
        font-weight: 500;
        margin-top: 10px;
        letter-spacing: 0.5px;
    }
    
    /* 7. Buttons */
    .stButton > button {
        background: #111827; 
        color: white;
        border: none;
        padding: 0.8rem 2rem;
        border-radius: 12px;
        font-weight: 600;
        width: 100%;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background: #374151;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    
    /* 8. Debug Expander */
    .streamlit-expanderHeader {
        background-color: transparent;
        color: #4B5563;
        font-weight: 500;
    }
    .debug-content {
        background: #F9FAFB;
        padding: 15px;
        border-radius: 8px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        color: #374151;
        border: 1px solid #E5E7EB;
    }
</style>
""", unsafe_allow_html=True)

def main():
    api_key_gemini = os.getenv("GOOGLE_API_KEY")
    api_key_search = os.getenv("GOOGLE_SEARCH_API_KEY")
    search_cx = os.getenv("SEARCH_ENGINE_ID")
    
    missing_keys = []
    if not api_key_gemini: missing_keys.append("GOOGLE_API_KEY")
    if not api_key_search: missing_keys.append("GOOGLE_SEARCH_API_KEY")
    if not search_cx: missing_keys.append("SEARCH_ENGINE_ID")
    
    if missing_keys:
        st.error(f"Configuration Error: Missing API Keys on Server: {', '.join(missing_keys)}")
        st.stop()

    # Centered Header
    st.markdown("<h1>AutoValuation.</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Intelligent Pricing Engine</div>", unsafe_allow_html=True)

    
    # --- Inputs ---
    # Row 1: Vehicle Identity
    col1, col2, col3, col4 = st.columns(4)
    
    make_options = ["Maruti", "Hyundai", "Toyota", "Honda", "Tata", "Mahindra", "Kia", "BMW", "Mercedes-Benz", "Other"]
    with col1: 
        selected_make = st.selectbox("Make", make_options)
        if selected_make == "Other":
            make = st.text_input("Enter Make", value="Ford")
        else:
            make = selected_make
        
    model_map = {
        "Maruti": ["Swift", "Baleno", "Brezza"],
        "Hyundai": ["Creta", "i20", "Verna", "Venue"],
        "Toyota": ["Fortuner", "Innova", "Glanza"],
        "Honda": ["City", "Amaze", "Civic"],
        "Tata": ["Nexon", "Harrier", "Safari"],
        "Mahindra": ["Thar", "XUV700", "Scorpio"],
        "Kia": ["Seltos", "Sonet", "Carens"],
        "BMW": ["3 Series", "5 Series", "X1"],
        "Mercedes-Benz": ["C-Class", "E-Class", "GLC"]
    }
    
    with col2: 
        # If make is custom (not in map), default to text input requirement or simple "Other" list
        if selected_make == "Other":
            model = st.text_input("Enter Model", value="Endeavour")
        else:
            # Dropdown with "Other" option included
            model_options = model_map.get(make, []) + ["Other"]
            selected_model = st.selectbox("Model", model_options)
            if selected_model == "Other":
                model = st.text_input("Enter Model Name", value="")
            else:
                model = selected_model

    with col3: year = st.selectbox("Year", range(2025, 2009, -1), index=5)
    with col4: variant = st.text_input("Variant", value="SX")

    # Row 2: Condition & Usage
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a: km = st.number_input("Odometer (KM)", min_value=0, max_value=200000, value=50000, step=1000)
    with col_b: fuel = st.selectbox("Fuel", ["Petrol", "Diesel", "CNG", "Electric"])
    with col_c: owners = st.selectbox("Owners", [1, 2, 3, 4], index=0)
    with col_d: condition = st.selectbox("Condition", ["Excellent", "Good", "Fair", "Poor"], index=1)
    
    # Row 3: Location (New)
    col_x, col_y = st.columns([1, 1])
    with col_x:
        location = st.text_input("Location (City/State)", value="Mumbai", help="Location influences demand and pricing.")
    with col_y:
        remarks = st.text_area("Additional Remarks / Observations", height=100, placeholder="E.g. Sunroof, Accident History, New Tyres, VIP Number, Scratch on door...", help="These details will be used by all engines to refine the price.")

    st.markdown("")
    if st.button("Calculate Value", type="primary", use_container_width=True):
        st.markdown("")
        run_valuation(make, model, year, variant, km, condition, owners, fuel, location, remarks, api_key_gemini, api_key_search, search_cx)


def run_valuation(make, model, year, variant, km, condition, owners, fuel, location, remarks, gemini_key, search_key, cx):
    
    with st.spinner("Orchestrating Intelligent Valuation..."):
        
        # 1. Engine D: The Sniper (Closest Match from Multiple Sources)
        # We run this early to use its data for Oracle
        sniper_price, sniper_sources, sniper_debug = fetch_closest_match(make, model, year, variant, km, location, search_key, cx)
        
        # Extract URLs from sources dict
        carwale_data = sniper_sources.get("carwale", {}) if sniper_sources else {}
        spinny_data = sniper_sources.get("spinny", {}) if sniper_sources else {}
        carwale_url = carwale_data.get("url") if carwale_data else None
        spinny_url = spinny_data.get("url") if spinny_data else None
        
        # 2. Logic
        logic_price, logic_log = calculate_logic_price(make, model, year, variant, km, condition, owners, location, remarks, search_key, cx)

        # 3. Scout
        scout_price, scout_data = fetch_market_prices(make, model, year, variant, km, search_key, cx, location, remarks)
        
        # 4. Engine E: ML Predictor (The Brain)
        ml_price, ml_conf, ml_debug = get_ml_prediction(make, model, year, variant, km, location)
        
        # 5. Oracle
        # Build Context for RAG
        context_data = f"""
        Real Base Price (Launch): {logic_price if logic_price else 'Unknown'}
        Depreciation Logic Value: {logic_price}
        Market Listings Average: {scout_price}
        Specific Sniper Listing Match: {sniper_price} (CarWale: {carwale_url}, Spinny: {spinny_url})
        ML Model Prediction: {ml_price} (trained on historical data)
        Scout Search Data: {scout_data[:500]}...
        Sniper Debug: {sniper_debug}
        """
        
        variant_full = f"{variant} {fuel}"
        oracle_price, oracle_debug = get_gemini_estimate(make, model, year, variant_full, km, condition, location, remarks, context_data, gemini_key)
        
        # 6. Engine G: Smart Scraper (Deep Market Research)
        smart_scraper = get_smart_scraper()
        smart_market_data = smart_scraper.get_market_data(make, model, year, fuel, location, km)
        smart_market_price = None
        if smart_market_data.get('success'):
            smart_market_price = int(smart_market_data['statistics']['median'] * 100000)
            
        # 7. Engine H: Ensemble ML (The Supreme Oracle)
        ensemble_predictor = get_ensemble_predictor()
        # Map our local data to what the predictor expects
        car_info = {
            'year': year, 'km_driven': km, 'fuel': fuel, 
            'make': make, 'model': model, 'city': location
        }
        ensemble_result = ensemble_predictor.predict(car_info, smart_market_data)
        ensemble_price = int(ensemble_result['final_price'] * 100000)
        
        # 8. Engine F: Cars24 (Browser Automation)
        cars24_price = None
        cars24_debug = "Session not configured. Run setup_cars24_session.py first."
        if CARS24_SUPPORTED and cars24_session_exists():
            try:
                transmission = "Automatic" if "auto" in variant.lower() or "amt" in variant.lower() or "cvt" in variant.lower() else "Manual"
                cars24_price, cars24_debug = get_cars24_price(make, model, year, variant, fuel, transmission, km, location)
            except Exception as e:
                cars24_debug = f"Error: {str(e)}"
        elif not CARS24_SUPPORTED:
            cars24_debug = "Cars24 engine (Playwright) is not supported in this environment."
        
    # --- CONSENSUS CALCULATION (Robust IQR Method) ---
    engine_results = {
        "Logic": logic_price,
        "Scout": scout_price,
        "Oracle": oracle_price,
        "Ensemble": ensemble_result.get('final_price', 0), # Use ensemble_result here
        "Scraper": smart_market_data['statistics']['median'] if smart_market_data.get('success') else 0, # Use smart_market_data here
        "Sniper": sniper_price,
        "ML Prediction": ml_price,
        "Cars24": cars24_price # Use cars24_price here
    }
    
    # Filter valid non-zero results
    valid_results = {k: v for k, v in engine_results.items() if v and v > 0} # Ensure v is not None and > 0
    
    if not valid_results:
        final_price = 0
    else:
        prices = list(valid_results.values())
        if len(prices) >= 4:
            # IQR Outlier Removal
            q1, q3 = np.percentile(prices, [25, 75])
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            filtered_prices = [p for p in prices if lower <= p <= upper]
            # If everything is filtered (shouldn't happen), fallback to original list
            if not filtered_prices: filtered_prices = prices
        else:
            filtered_prices = prices
            
        # Weighted Final Price
        # Priorities: Ensemble (40%), Scraper (30%), Logic/Oracle/Sniper (10% each)
        weights = {
            "Ensemble": 0.40,
            "Scraper": 0.30,
            "Logic": 0.10,
            "Oracle": 0.10,
            "Sniper": 0.10,
            "Scout": 0.05, # Added default weights for other engines
            "ML Prediction": 0.05,
            "Cars24": 0.05
        }
        
        weighted_sum = 0
        total_weight = 0
        
        for name, price in valid_results.items():
            if price in filtered_prices:
                w = weights.get(name, 0.05) # Default weight for others
                weighted_sum += price * w
                total_weight += w
        
        final_price = weighted_sum / total_weight if total_weight > 0 else np.median(filtered_prices)

    # 4. Display Consensus
    st.markdown("---")
    st.subheader("🏁 Final Valuation Consensus")
    
    col_f1, col_f2 = st.columns([1, 1])
    with col_f1:
        st.metric("Fair Market Value", f"₹ {format_currency(final_price)}", delta=f"{len(valid_results)} Engines Contributing")
    with col_f2:
        conf_score = "High" if len(filtered_prices) >= 5 else "Medium"
        st.info(f"Consensus Confidence: **{conf_score}** (IQR filtered {len(prices) - len(filtered_prices)} outliers)")

    # Consolidate Breakdown for Graph
    graph_data = pd.DataFrame({
        "Engine": list(valid_results.keys()),
        "Price (Lakhs)": [v / 100000 for v in list(valid_results.values())], # Convert to Lakhs for graph
        "Status": ["Included" if v in filtered_prices else "Outlier" for v in valid_results.values()]
    })
    st.bar_chart(graph_data, x="Engine", y="Price (Lakhs)", color="Status")
    
    # Hero Card (moved here to be after final_price calculation)
    c_main, c_hero = st.columns([1, 2])
    with c_main:
        # This section is now redundant as the main metric is displayed above
        pass
             
    # Breakdown Grid - 8 engines (2 rows of 4)
    row1 = st.columns(4)
    row2 = st.columns(4)
    
    with row1[0]:
        st.markdown(f"""
        <div class="metric-props">
            <div class="metric-label">LOGIC (REAL BASE)</div>
            <div class="metric-value">{format_currency(logic_price)}</div>
        </div>
        """, unsafe_allow_html=True)
        with st.expander("Details"):
            st.markdown('<div class="debug-content">', unsafe_allow_html=True)
            for l in logic_log: st.write(l)
            st.markdown('</div>', unsafe_allow_html=True)
            
    with row1[1]:
        st.markdown(f"""
        <div class="metric-props">
            <div class="metric-label">MARKET SEARCH</div>
            <div class="metric-value">{format_currency(scout_price) if scout_price else "No Data"}</div>
        </div>
        """, unsafe_allow_html=True)
        with st.expander("Listings"):
            st.markdown('<div class="debug-content">', unsafe_allow_html=True)
            st.text(scout_data)
            st.markdown('</div>', unsafe_allow_html=True)

    with row1[2]:
        st.markdown(f"""
        <div class="metric-props">
            <div class="metric-label">AI RAG ESTIMATE</div>
            <div class="metric-value">{format_currency(oracle_price)}</div>
        </div>
        """, unsafe_allow_html=True)
        with st.expander("AI Analysis"):
             st.markdown('<div class="debug-content">', unsafe_allow_html=True)
             st.write(oracle_debug)
             st.markdown('</div>', unsafe_allow_html=True)

    with row1[3]:
        st.markdown(f"""
        <div class="metric-props" style="border-top: 3px solid #3B82F6; background: rgba(59, 130, 246, 0.05);">
            <div class="metric-label" style="color: #2563EB">ENSEMBLE ML (SUPREME)</div>
            <div class="metric-value" style="color: #1E40AF">{format_currency(ensemble_price)}</div>
        </div>
        """, unsafe_allow_html=True)
        with st.expander("Breakdown"):
            st.markdown('<div class="debug-content">', unsafe_allow_html=True)
            st.write(f"Confidence: **{ensemble_result['confidence']}**")
            st.json(ensemble_result['breakdown'])
            st.markdown('</div>', unsafe_allow_html=True)

    with row2[0]:
        st.markdown(f"""
        <div class="metric-props">
            <div class="metric-label">SMART SCRAPER</div>
            <div class="metric-value">{format_currency(smart_market_price) if smart_market_price else "No Data"}</div>
        </div>
        """, unsafe_allow_html=True)
        with st.expander("Market Map"):
            st.markdown('<div class="debug-content">', unsafe_allow_html=True)
            if smart_market_data.get('success'):
                st.write(f"Found {smart_market_data['count']} filtered listings.")
                st.json(smart_market_data['statistics'])
            else:
                st.write(smart_market_data.get('message', 'No data'))
            st.markdown('</div>', unsafe_allow_html=True)

    with row2[1]:
        val_sniper = format_currency(sniper_price) if sniper_price else "No Match"
        st.markdown(f"""
        <div class="metric-props">
            <div class="metric-label">DIRECT MATCH (SNIPER)</div>
            <div class="metric-value" style="color: #DC2626">{val_sniper}</div>
        </div>
        """, unsafe_allow_html=True)
        with st.expander("Sniper Match Info"):
             st.markdown('<div class="debug-content">', unsafe_allow_html=True)
             st.write(sniper_debug)
             st.markdown('</div>', unsafe_allow_html=True)

    with row2[2]:
        val_ml = format_currency(ml_price) if ml_price else "No Model data"
        st.markdown(f"""
        <div class="metric-props">
            <div class="metric-label">ML PREDICTION (BRAIN v1)</div>
            <div class="metric-value" style="color: #9333ea">{val_ml}</div>
        </div>
        """, unsafe_allow_html=True)
        with st.expander("Model Data"):
             st.markdown('<div class="debug-content">', unsafe_allow_html=True)
             st.write(ml_debug)
             st.write(f"Confidence: {int(ml_conf*100)}%")
             st.markdown('</div>', unsafe_allow_html=True)

    with row2[3]:
        val_c24 = format_currency(cars24_price) if cars24_price else "N/A"
        st.markdown(f"""
        <div class="metric-props">
            <div class="metric-label">CARS24</div>
            <div class="metric-value" style="color: #ea580c">{val_c24}</div>
        </div>
        """, unsafe_allow_html=True)
        with st.expander("Cars24 Info"):
            st.markdown('<div class="debug-content">', unsafe_allow_html=True)
            st.write(cars24_debug)
            if CARS24_SUPPORTED and not cars24_session_exists():
                st.warning("Run `python setup_cars24_session.py` to enable")
            elif not CARS24_SUPPORTED:
                st.info("Desktop only feature")
            st.markdown('</div>', unsafe_allow_html=True)
    
    # 3. Chart
    st.markdown("### Consensus Graph")
    graph_data = pd.DataFrame({
        "Source": ["Scraper", "Ensemble ML", "Depreciation", "Market Avg", "AI RAG", "ML Brain", "Sniper", "Cars24"],
        "Value": [smart_market_price or 0, ensemble_price or 0, logic_price or 0, scout_price or 0, oracle_price or 0, ml_price or 0, sniper_price or 0, cars24_price or 0]
    }).set_index("Source")
    
    st.bar_chart(graph_data, color="#2563EB")

if __name__ == "__main__":
    main()
