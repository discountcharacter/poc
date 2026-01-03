"""
Flask API Server for Cars24 Automation
Exposes the Playwright automation as HTTP endpoints for n8n
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from cars24_automation import Cars24Automation
import threading
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for n8n webhooks

# Store active automation sessions
automation_sessions = {}

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "running", "service": "Cars24 Automation API"})

@app.route('/api/cars24/start', methods=['POST'])
def start_automation():
    """
    Start Cars24 automation with car details
    """
    try:
        data = request.json
        print(f"\n📥 Received request: {data}")
        
        # Validate required fields
        required_fields = ['make', 'model', 'year', 'mobile', 'city']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing field: {field}"}), 400
        
        # Create new automation session
        session_id = f"session_{int(time.time())}"
        print(f"🆔 Creating session: {session_id}")
        
        automation = Cars24Automation()
        
        try:
            # Start browser
            print(f"🚀 Starting browser for session {session_id}...")
            automation.start_browser(headless=False)
            print("✅ Browser started successfully")
            
            # Fill car details
            print("📝 Filling car details...")
            fill_result = automation.fill_car_details(data)
            
            if not fill_result.get('success'):
                print(f"❌ Fill failed: {fill_result}")
                automation.close_browser()
                return jsonify(fill_result), 500
            
            print("✅ Form filled successfully")
            
            # Request OTP
            print("📲 Requesting OTP...")
            otp_result = automation.request_otp()
            
            if not otp_result.get('success'):
                print(f"❌ OTP request failed: {otp_result}")
                automation.close_browser()
                return jsonify(otp_result), 500
            
            print("✅ OTP requested successfully")
            
            # Store session for later OTP submission
            automation_sessions[session_id] = automation
            print(f"💾 Session stored: {session_id}")
            
            return jsonify({
                "success": True,
                "session_id": session_id,
                "message": "OTP sent to mobile. Please verify."
            })
            
        except Exception as inner_e:
            print(f"❌ Inner exception: {type(inner_e).__name__}: {str(inner_e)}")
            automation.close_browser()
            return jsonify({
                "success": False, 
                "error": f"{type(inner_e).__name__}: {str(inner_e)}"
            }), 500
        
    except Exception as e:
        print(f"❌ Outer exception: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False, 
            "error": f"{type(e).__name__}: {str(e)}"
        }), 500


@app.route('/api/cars24/verify-otp', methods=['POST'])
def verify_otp():
    """
    Verify OTP and get price
    
    Request Body:
    {
        "session_id": "abc123",
        "otp": "123456"
    }
    
    Response:
    {
        "success": true,
        "price": "₹ 4,50,000"
    }
    """
    try:
        data = request.json
        
        # Validate
        if 'session_id' not in data or 'otp' not in data:
            return jsonify({"success": False, "error": "Missing session_id or otp"}), 400
        
        session_id = data['session_id']
        otp = data['otp']
        
        # Get automation session
        if session_id not in automation_sessions:
            return jsonify({"success": False, "error": "Invalid or expired session"}), 400
        
        automation = automation_sessions[session_id]
        
        # Submit OTP and get price
        result = automation.submit_otp(otp)
        
        # Close browser
        automation.close_browser()
        
        # Remove session
        del automation_sessions[session_id]
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/cars24/full-automation', methods=['POST'])
def full_automation():
    """
    Full automation with manual OTP entry
    This endpoint waits for OTP to be provided
    
    Request Body:
    {
        "car_details": {...},
        "otp": "123456"
    }
    """
    try:
        data = request.json
        car_details = data.get('car_details', {})
        otp = data.get('otp')
        
        if not otp:
            return jsonify({"success": False, "error": "OTP is required"}), 400
        
        automation = Cars24Automation()
        automation.start_browser(headless=False)
        
        # Fill details
        automation.fill_car_details(car_details)
        
        # Request OTP
        automation.request_otp()
        
        # Wait for user to visually confirm OTP screen
        time.sleep(5)
        
        # Submit OTP
        result = automation.submit_otp(otp)
        
        # Close
        automation.close_browser()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("🚗 Cars24 Automation API Server Starting...")
    print("=" * 60)
    print("\n📡 Available Endpoints:")
    print("  - POST http://localhost:5000/api/cars24/start")
    print("  - POST http://localhost:5000/api/cars24/verify-otp")
    print("  - GET  http://localhost:5000/health")
    print("\n⚙️  Server will run on: http://localhost:5000")
    print("\n🔗 Use these URLs in your n8n workflows!")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
