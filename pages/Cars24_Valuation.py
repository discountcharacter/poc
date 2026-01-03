import streamlit as st
import json

st.set_page_config(page_title="Cars24 Valuation", page_icon="🚗", layout="wide")

st.title("🚗 Cars24 Valuation Form")
st.caption("Simple webhook data collection")

# Initialize Session State
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "car_data" not in st.session_state:
    st.session_state.car_data = None

def reset_form():
    st.session_state.submitted = False
    st.session_state.car_data = None

# Main Form
if not st.session_state.submitted:
    with st.form("car_valuation_form"):
        st.subheader("📋 Enter Vehicle Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            make = st.selectbox("Car Make", ["Maruti", "Hyundai", "Toyota", "Honda", "Tata", "Mahindra", "Kia", "Other"])
            model = st.text_input("Car Model", placeholder="e.g. Swift")
            year = st.selectbox("Year", range(2025, 2008, -1), index=5)
            variant = st.text_input("Variant", placeholder="e.g. VXI")
            fuel = st.selectbox("Fuel Type", ["Petrol", "Diesel", "CNG", "Electric"])
        
        with col2:
            transmission = st.selectbox("Transmission", ["Manual", "Automatic"])
            km = st.number_input("Kilometers Driven", min_value=0, max_value=200000, value=40000, step=1000)
            state = st.text_input("State", placeholder="e.g. Delhi")
            city = st.text_input("City", placeholder="e.g. New Delhi")
            mobile = st.text_input("Mobile Number", placeholder="9999999999")
        
        submitted = st.form_submit_button("📤 Submit for Valuation", type="primary", use_container_width=True)
        
        if submitted:
            if not mobile or len(mobile) < 10:
                st.error("Please enter a valid 10-digit mobile number")
            elif not model or not city:
                st.error("Please fill in all required fields")
            else:
                # Store car data
                st.session_state.car_data = {
                    "make": make,
                    "model": model,
                    "year": year,
                    "variant": variant,
                    "fuel": fuel,
                    "transmission": transmission,
                    "km": km,
                    "state": state,
                    "city": city,
                    "mobile": mobile
                }
                st.session_state.submitted = True
                st.rerun()

else:
    # Show submitted data
    st.success("✅ Valuation Request Submitted!")
    
    car_data = st.session_state.car_data
    
    # Display car details in a nice card
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 30px; border-radius: 15px; color: white; margin: 20px 0;">
            <h2 style="margin: 0; text-align: center;">
                {car_data['year']} {car_data['make']} {car_data['model']}
            </h2>
            <p style="text-align: center; font-size: 1.2rem; margin: 10px 0;">
                {car_data['variant']} • {car_data['fuel']} • {car_data['transmission']}
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Show details
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Vehicle Information")
        st.write(f"**Make:** {car_data['make']}")
        st.write(f"**Model:** {car_data['model']}")
        st.write(f"**Year:** {car_data['year']}")
        st.write(f"**Variant:** {car_data['variant']}")
        st.write(f"**Fuel Type:** {car_data['fuel']}")
    
    with col2:
        st.markdown("### 📍 Additional Details")
        st.write(f"**Transmission:** {car_data['transmission']}")
        st.write(f"**Kilometers:** {car_data['km']:,} km")
        st.write(f"**City:** {car_data['city']}")
        st.write(f"**State:** {car_data['state']}")
        st.write(f"**Mobile:** {car_data['mobile']}")
    
    # Webhook data display
    st.markdown("---")
    st.markdown("### 🔗 Webhook Data")
    st.info("This data would be sent to your webhook endpoint:")
    
    st.json(car_data)
    
    # Estimated price (static for now)
    st.markdown("---")
    st.markdown("### 💰 Estimated Valuation")
    
    # Simple price estimation based on year and km
    base_price = 500000
    year_depreciation = (2025 - car_data['year']) * 30000
    km_depreciation = (car_data['km'] / 10000) * 15000
    estimated_price = base_price - year_depreciation - km_depreciation
    
    if estimated_price < 100000:
        estimated_price = 100000
    
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                    padding: 40px; border-radius: 20px; text-align: center; color: white;">
            <h3 style="margin: 0; opacity: 0.9;">Estimated Market Value</h3>
            <h1 style="font-size: 3.5rem; margin: 15px 0; font-weight: 800;">
                ₹ {estimated_price:,.0f}
            </h1>
            <p style="margin: 0; opacity: 0.8;">*Approximate estimate based on vehicle details</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.caption("📝 Note: This is a basic estimation. Actual valuation may vary based on vehicle condition, market demand, and other factors.")
    
    # Action buttons
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Value Another Car", use_container_width=True, type="primary"):
            reset_form()
            st.rerun()
    
    with col2:
        if st.button("← Back to Main Portal", use_container_width=True):
            st.switch_page("main.py")

# Footer
st.markdown("---")
st.caption("💡 Cars24 Valuation Portal • Simple & Fast")

