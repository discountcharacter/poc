import streamlit as st
import requests
import json
import time

st.set_page_config(page_title="Cars24 Valuation Automation", page_icon="🚗", layout="wide")

st.title("🚗 Cars24 Instant Valuation (N8n Automation)")
st.caption("Powered by N8n Webhooks & Browser Automation")

# Initialize Session State
if "stage" not in st.session_state:
    st.session_state.stage = "input"  # input -> otp -> result
if "browserWSEndpoint" not in st.session_state:
    st.session_state.browserWSEndpoint = None
if "valuation_price" not in st.session_state:
    st.session_state.valuation_price = None

def reset_app():
    st.session_state.stage = "input"
    st.session_state.browserWSEndpoint = None
    st.session_state.valuation_price = None

# --- Stage 1: Input Form ---
if st.session_state.stage == "input":
    with st.form("car_details_form"):
        st.subheader("Step 1: Vehicle Details")
        col1, col2 = st.columns(2)
        
        with col1:
            make = st.text_input("Car Make", placeholder="e.g. Maruti")
            model = st.text_input("Car Model", placeholder="e.g. Swift")
            year = st.selectbox("Year", range(2025, 2008, -1), index=4)
            variant = st.text_input("Variant", placeholder="e.g. VXI")
        
        with col2:
            km = st.number_input("Kilometers Driven", min_value=0, max_value=200000, value=40000, step=1000)
            state = st.text_input("Registration State/Location", value="DL")
            mobile = st.text_input("Mobile Number", placeholder="9999999999")
        
        submitted = st.form_submit_button("Get OTP", type="primary", use_container_width=True)
        
        if submitted:
            if not mobile or len(mobile) < 10:
                st.error("Please enter a valid mobile number.")
            else:
                payload = {
                    "make": make,
                    "model": model,
                    "year": year,
                    "variant": variant,
                    "km": km,
                    "state": state,
                    "mobile": mobile
                }
                
                with st.spinner("🚀 Automating Cars24 Input... (This may take 30-60s)"):
                    try:
                        # Webhook 1
                        url = "https://jaiswal007.app.n8n.cloud/webhook/car-details"
                        response = requests.post(url, json=payload, timeout=120)
                        
                        if response.status_code == 200:
                            data = response.json()
                            endpoint = data.get("browserWSEndpoint")
                            
                            if endpoint:
                                st.session_state.browserWSEndpoint = endpoint
                                st.session_state.stage = "otp"
                                st.success("OTP Sent! Browser session active.")
                                st.rerun()
                            else:
                                st.error("Failed to start browser session. No endpoint returned.")
                                st.write("Response:", data)
                        else:
                            st.error(f"Webhook Failed: {response.status_code}")
                            st.write(response.text)
                            
                    except Exception as e:
                        st.error(f"Connection Error: {e}")

# --- Stage 2: OTP Verification ---
elif st.session_state.stage == "otp":
    with st.container():
        st.subheader("Step 2: OTP Verification")
        st.info("Please enter the OTP sent to your mobile number.")
        
        otp = st.text_input("Enter 4-digit OTP", max_chars=6)
        
        if st.button("Submit OTP", type="primary"):
            if not otp:
                st.warning("Please enter OTP.")
            else:
                payload = {
                    "otp": otp,
                    "browserWSEndpoint": st.session_state.browserWSEndpoint
                }
                
                with st.spinner("🔐 Verifying & Fetching Valuation..."):
                    try:
                        # Webhook 2
                        url = "https://jaiswal007.app.n8n.cloud/webhook/otp-verification"
                        response = requests.post(url, json=payload, timeout=60)
                        
                        if response.status_code == 200:
                            # Expecting direct price or json with price
                            try:
                                res_json = response.json()
                                price = res_json.get("price", "N/A")
                            except:
                                price = response.text
                                
                            st.session_state.valuation_price = price
                            st.session_state.stage = "result"
                            st.rerun()
                        else:
                            st.error(f"OTP Verification Failed: {response.status_code}")
                            st.write(response.text)
                    except Exception as e:
                        st.error(f"Error: {e}")

# --- Stage 3: Result Display ---
elif st.session_state.stage == "result":
    st.balloons()
    st.container()
    st.success("Valuation Successful!")
    
    st.markdown(f"""
        <div style="padding: 20px; background-color: #f0fdf4; border: 2px solid #22c55e; border-radius: 10px; text-align: center;">
            <h3 style="color: #166534; margin: 0;">Cars24 Estimated Value</h3>
            <h1 style="color: #15803d; font-size: 3.5rem; margin: 10px 0;">{st.session_state.valuation_price}</h1>
            <p style="color: #166534;">*Based on real-time automation</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    if st.button("Start Over", use_container_width=True):
        reset_app()
        st.rerun()

# Debug / Footer
st.markdown("---")
st.caption("Automation Status: Active | N8n Cloud")
