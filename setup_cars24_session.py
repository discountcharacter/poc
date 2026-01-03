#!/usr/bin/env python3
"""
Cars24 Session Setup Script

Run this script to login to Cars24 and save your session.
The session will be used for subsequent automated valuations.

Usage:
    python setup_cars24_session.py
"""

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

SESSION_FILE = Path(__file__).parent / ".cars24_session.json"

def setup_session():
    print("=" * 60)
    print("Cars24 Session Setup")
    print("=" * 60)
    print()
    print("This will open a browser window where you can login to Cars24.")
    print("After logging in, your session will be saved for future use.")
    print()
    
    with sync_playwright() as p:
        # Launch browser in visible mode
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # Navigate to Cars24
        print("Opening Cars24...")
        page.goto("https://www.cars24.com/sell-used-cars")
        
        # Click to start the flow
        try:
            page.click("text=Start with your car brand", timeout=10000)
        except:
            pass
        
        # Select a sample car to get to the login page
        print()
        print("Please complete the following steps in the browser:")
        print("1. Select any car brand (e.g., Maruti Suzuki)")
        print("2. Select any year (e.g., 2020)")
        print("3. Select any model (e.g., Swift)")
        print("4. Select fuel type (e.g., Petrol)")
        print("5. Select transmission (e.g., Manual)")
        print("6. Select any variant")
        print("7. Select state and RTO")
        print("8. Select KM range")
        print("9. Select city")
        print("10. Select 'Just checking price'")
        print("11. Enter your phone number and OTP")
        print()
        print("After you see the price estimate, press Enter here to save the session...")
        
        # Wait for user to complete login
        input()
        
        # Save cookies
        cookies = context.cookies()
        
        with open(SESSION_FILE, 'w') as f:
            json.dump(cookies, f, indent=2)
        
        print()
        print(f"✅ Session saved to: {SESSION_FILE}")
        print()
        print("You can now use the Cars24 engine in MediWay!")
        print("The session should remain valid for several days.")
        
        browser.close()

def verify_session():
    """Verify if a saved session is valid."""
    if not SESSION_FILE.exists():
        print("No session file found.")
        return False
    
    print("Verifying saved session...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        
        # Load saved cookies
        with open(SESSION_FILE, 'r') as f:
            cookies = json.load(f)
        context.add_cookies(cookies)
        
        page = context.new_page()
        page.goto("https://www.cars24.com/sell-used-cars")
        
        # Check if we're logged in (look for user profile or similar)
        time.sleep(2)
        
        # If there's no login prompt, session is likely valid
        login_required = page.query_selector("input[type='tel']") is not None
        
        browser.close()
        
        if login_required:
            print("❌ Session expired. Please run setup again.")
            return False
        else:
            print("✅ Session is valid!")
            return True

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        verify_session()
    else:
        setup_session()
