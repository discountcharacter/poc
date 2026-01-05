import streamlit as st
import os
import sys
import pandas as pd
from dotenv import load_dotenv

# Ensure src is in path (Parent directory)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.agent_graph import ValuationAgent

load_dotenv()

st.set_page_config(
    page_title="Agent-1: Intelligent Valuation",
    page_icon="💼",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .reportview-container {
        background: #0E1117;
    }
    .main-metric {
        font-size: 3.5rem;
        font-weight: 700;
        color: #10B981;
    }
    .card {
        background-color: #1E293B;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #334155;
        margin-bottom: 20px;
    }
    .reasoning-text {
        font-family: 'Courier New', monospace;
        color: #94A3B8; /* Darker Gray */
        line-height: 1.6;
    }
    .stButton>button {
        background-color: #2563EB;
        color: white;
        border-radius: 8px;
        height: 50px;
        font-size: 1.2rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("Agent-1: Intelligent Valuation Portal")
st.markdown("### Automated Market Analysis (Rescue-v2.0)")

# Sidebar Configuration
with st.sidebar:
    st.header("Agent Config")
    gemini_key = os.getenv("GOOGLE_API_KEY")
    search_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    
    status_color = "green" if (gemini_key and search_key) else "red"
    st.markdown(f"API Status: <span style='color:{status_color}'>●</span>", unsafe_allow_html=True)
    
    st.info("""
    **How it works:**
    1. Agent searches for real-time listings on CarWale/Spinny/etc.
    2. Agent reads the search snippets (Human-like reading).
    3. Agent uses LLM reasoning to filter out junk (e.g. "Reviews", "Comparisons").
    4. Calculates median of verified matches.
    """)

# Input Grid
col1, col2, col3 = st.columns(3)
with col1:
    make_options = ["Maruti", "Hyundai", "Honda", "Tata", "Mahindra", "Kia", "Toyota", "MG", "Volkswagen", "Renault", "Ford", "Skoda", "Nissan", "Other"]
    make_input = st.selectbox("Make", make_options, index=1)
    if make_input == "Other":
        make = st.text_input("Enter Custom Make", value="Volvo")
    else:
        make = make_input
        
    year = st.selectbox("Year", range(2025, 1989, -1), index=5)
    variant = st.text_input("Variant", value="SX Petrol")
with col2:
    model = st.text_input("Model", value="Creta")
    fuel = st.selectbox("Fuel", ["Petrol", "Diesel", "CNG", "Electric"], index=0)
    km = st.number_input("Odometer (KM)", min_value=0, max_value=1000000, value=50000, step=1000)
with col3:
    location = st.text_input("Location", value="Hyderabad")
    owners = st.selectbox("Owners", [1, 2, 3, 4], index=0)
    condition = st.selectbox("Condition", ["Excellent", "Good", "Fair", "Poor"], index=1)

remarks = st.text_area("Additional Remarks", placeholder="E.g. Sunroof, New Tyres...", height=70)

st.markdown("---")

if st.button("Consult Agent", type="primary", use_container_width=True):
    # Retrieve keys from env 
    search_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    cx = os.getenv("SEARCH_ENGINE_ID")
    
    agent = ValuationAgent(gemini_key, search_key, cx)
    
    with st.status("Agent is working...", expanded=True) as status:
        st.write(f"1. Browsing market for **{year} {make} {model} {variant} ({fuel})** in **{location}**...")
        result = agent.search_market(make, model, year, variant, location, km, fuel, owners, condition, remarks)
        
        if "error" in result:
            status.update(label="Agent Failed", state="error", expanded=True)
            st.error(result["error"])
        else:
            status.update(label="Valuation Complete", state="complete", expanded=False)
            
            # --- Main Display ---
            st.markdown("---")
            # --- Main Display ---
            st.markdown("---")
            
            # Imports
            from src.procurement_algo import ProcurementAlgo
            from src.formula_engine import FormulaEngine

            # 1. Calculate All Values First
            # Agent Market Price
            market_price = result.get('market_price') or result.get('estimated_price', 0)
            
            # Procurement Algo
            market_price_val = int(market_price)
            proc_res = ProcurementAlgo.calculate_procurement_price(
                market_price_val, make, model, year, km, owners, condition
            )
            buy_price = proc_res['final_procurement_price']
            base_proc = proc_res['base_procurement']
            
            # Logic: If Bonus/Inflation (Final > Base), clamp range as requested
            # User: "make base_procurement as lower end, current lower range as new upper limit"
            if buy_price > base_proc:
                 buy_low = float(base_proc)
                 buy_high = max(float(base_proc), buy_price * 0.95)
            else:
                 # Standard range for Penalty cases
                 buy_low = buy_price * 0.95
                 buy_high = buy_price * 1.05
            
            # Formula Engine
            f_engine = FormulaEngine()
            formula_res = f_engine.calculate_price(make, model, variant, year, km, fuel, owners, condition, location)

            # 2. Display Grid
            c1, c2 = st.columns(2)
            
            # --- Left Column: Procurement & Market ---
            with c1:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                
                # A. Recommended Procurement (Top Priority)
                st.caption("RECOMMENDED PROCUREMENT PRICE (Precision Algo)")
                st.markdown(
                    f"<div style='font-size: 2.2rem; font-weight: 700; color: #3B82F6'>"
                    f"₹ {buy_low:,.0f} - ₹ {buy_high:,.0f}</div>", 
                    unsafe_allow_html=True
                )
                
                st.info(f"Basis: {proc_res['details']}.")
                st.caption("Algo Breakdown:")
                st.json(proc_res) # Shown Directly
                
                st.markdown("---")
                
                # B. Market Retail Price (Below Procurement)
                st.caption("MARKET RETAIL PRICE (High Range)")
                fmt_price = f"₹ {market_price:,.0f}" if market_price > 0 else "N/A"
                if market_price == 0:
                     st.markdown(f'<div class="main-metric" style="color: #EF4444">{fmt_price}</div>', unsafe_allow_html=True)
                else:
                     st.markdown(f'<div class="main-metric">{fmt_price}</div>', unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)

            # --- Right Column: Formula & Reasoning ---
            with c2:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                
                # C. Formula Value (Next to Procurement)
                st.caption("FORMULA VALUE (Base Price Logic)")
                if "error" in formula_res:
                    st.error(formula_res["error"])
                else:
                    f_price = formula_res["price"]
                    f_base = formula_res["base_new_price"]
                    st.markdown(f'<div class="main-metric" style="color: #F59E0B">₹ {f_price:,.0f}</div>', unsafe_allow_html=True)
                    st.caption(f"derived from Base New Price: ₹ {f_base:,.0f}")
                    
                    st.caption("Formula Breakdown:")
                    st.json(formula_res["factors"]) # Shown Directly
                    st.caption("Logic: Base * Dep * KM * Fuel * Owner * Cond")
                
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Agent Reasoning
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.caption("AGENT REASONING")
                st.markdown(f'<div class="reasoning-text">{result.get("reasoning", "No reasoning provided.")}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

                # Agent Reasoning & Evidence
                st.markdown("### Evidence (Verified Listings)")
                st.dataframe(pd.DataFrame(result.get("valid_listings", [])))
                valid_count = len(result.get('valid_listings', []))
                rejected_count = result.get('rejected_count', 0)
                st.write(f"**{valid_count}** Verified Matches found.")
                st.caption(f"Rejected {rejected_count} irrelevant results.")
                st.markdown('</div>', unsafe_allow_html=True)

            # Listings Table with Links
            st.subheader("Traceability: Verified Listings")
            listings = result.get('valid_listings', [])
            if listings:
                # Convert to DF but make links clickable
                df_data = []
                for item in listings:
                    link = item.get("link", "#")
                    title = item.get("title", "Unknown")
                    price = item.get("price")
                    
                    # Safe Price Formatting
                    try:
                        price_val = float(price) if price is not None else 0
                    except (ValueError, TypeError):
                        price_val = 0
                        
                    # Streamlit LinkColumn format
                    df_data.append({
                        "Source": item.get("source", "Web"),
                        "Title": title,
                        "Price": f"₹ {price_val:,.0f}" if price_val > 0 else "N/A",
                        "URL": link
                    })
                
                st.dataframe(
                    pd.DataFrame(df_data), 
                    column_config={"URL": st.column_config.LinkColumn("Evidence Link")},
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.info("No listings passed the strict Agent verification filter.")

