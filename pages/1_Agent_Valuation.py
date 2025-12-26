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
    page_icon="🤖",
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
        color: #E2E8F0;
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

st.title("🤖 Agent-1: Intelligent Valuation Portal")
st.markdown("### The Oracle Agent (Rescue-v2.0)")

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
    make = st.selectbox("Make", ["Maruti", "Hyundai", "Honda", "Tata", "Mahindra", "Kia", "Toyota", "MG"], index=1)
    year = st.selectbox("Year", range(2025, 2010, -1), index=5)
    variant = st.text_input("Variant", value="SX Petrol")
with col2:
    model = st.text_input("Model", value="Creta")
    fuel = st.selectbox("Fuel", ["Petrol", "Diesel", "CNG", "Electric"], index=0)
    km = st.number_input("Odometer (KM)", min_value=0, max_value=200000, value=50000, step=1000)
with col3:
    location = st.text_input("Location", value="Hyderabad")
    owners = st.selectbox("Owners", [1, 2, 3, 4], index=0)
    condition = st.selectbox("Condition", ["Excellent", "Good", "Fair", "Poor"], index=1)

remarks = st.text_area("Additional Remarks", placeholder="E.g. Sunroof, New Tyres...", height=70)

st.markdown("---")

if st.button("Consult Oracle Agent", type="primary", use_container_width=True):
    # Retrieve keys from env 
    search_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    cx = os.getenv("SEARCH_ENGINE_ID")
    
    agent = ValuationAgent(gemini_key, search_key, cx)
    
    with st.status("🤖 Agent is working...", expanded=True) as status:
        st.write(f"1. Browsing market for **{year} {make} {model} {variant} ({fuel})** in **{location}**...")
        result = agent.search_market(make, model, year, variant, location, km, fuel, owners, condition, remarks)
        
        if "error" in result:
            status.update(label="Agent Failed", state="error", expanded=True)
            st.error(result["error"])
        else:
            status.update(label="Valuation Complete", state="complete", expanded=False)
            
            # --- Main Display ---
            st.markdown("---")
            c1, c2 = st.columns([1, 2])
            
            with c1:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.caption("ESTIMATED MARKET VALUE")
                price = result.get('estimated_price', 0)
                fmt_price = f"₹ {price:,.0f}" if price > 0 else "N/A"
                if price == 0:
                    st.markdown(f'<div class="main-metric" style="color: #EF4444">{fmt_price}</div>', unsafe_allow_html=True)
                    st.warning("No valid listings found matching strict criteria.")
                else:
                    st.markdown(f'<div class="main-metric">{fmt_price}</div>', unsafe_allow_html=True)
                
                valid_count = len(result.get('valid_listings', []))
                rejected_count = result.get('rejected_count', 0)
                st.write(f"**{valid_count}** Verified Matches found.")
                st.caption(f"Rejected {rejected_count} irrelevant results.")
                st.markdown('</div>', unsafe_allow_html=True)

            with c2:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.caption("AGENT REASONING")
                st.markdown(f'<div class="reasoning-text">{result.get("reasoning", "No reasoning provided.")}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # Listings Table
            st.subheader("Traceability: Verified Listings")
            if result.get('valid_listings'):
                df = pd.DataFrame(result['valid_listings'])
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No listings passed the strict Agent verification filter.")

