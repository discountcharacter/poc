"""
Cars24 Browser Automation Script
Uses Playwright to automate Cars24 valuation process
"""

from playwright.sync_api import sync_playwright
import time
import json

class Cars24Automation:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
    def start_browser(self, headless=False):
        """Start browser and return WebSocket endpoint"""
        try:
            print("🚀 Starting Playwright...")
            self.playwright = sync_playwright().start()
            
            print("🌐 Launching browser...")
            self.browser = self.playwright.chromium.launch(
                headless=headless,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            print("📄 Creating context...")
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            print("✅ Opening new page...")
            self.page = self.context.new_page()
            
            return "browser_started"
            
        except Exception as e:
            print(f"❌ Error starting browser: {e}")
            self.close_browser()
            raise
    
    def fill_car_details(self, car_data):
        """
        Navigate to Cars24 and fill in car details
        
        Args:
            car_data: dict with keys: make, model, year, variant, fuel, 
                     transmission, km, state, city, mobile
        """
        try:
            # Navigate to Cars24
            print("🌐 Navigating to Cars24...")
            self.page.goto("https://www.cars24.com/sell-used-car/", timeout=30000)
            
            # Wait for page to load
            time.sleep(2)
            
            # Fill in the form (selectors may need adjustment based on actual site)
            print("📝 Filling form...")
            
            # City/Location
            if self.page.locator('input[placeholder*="city" i], input[name*="city" i]').count() > 0:
                self.page.fill('input[placeholder*="city" i], input[name*="city" i]', car_data.get('city', ''))
                time.sleep(1)
            
            # Mobile Number
            if self.page.locator('input[type="tel"], input[placeholder*="mobile" i]').count() > 0:
                self.page.fill('input[type="tel"], input[placeholder*="mobile" i]', car_data.get('mobile', ''))
                time.sleep(1)
            
            # Car Make/Brand
            if self.page.locator('input[placeholder*="brand" i], select[name*="make" i]').count() > 0:
                self.page.click('input[placeholder*="brand" i], select[name*="make" i]')
                time.sleep(1)
                # Type to search
                self.page.keyboard.type(car_data.get('make', ''))
                time.sleep(1)
                # Press Enter to select first option
                self.page.keyboard.press('Enter')
                time.sleep(1)
            
            # Car Model
            if self.page.locator('input[placeholder*="model" i]').count() > 0:
                self.page.click('input[placeholder*="model" i]')
                time.sleep(1)
                self.page.keyboard.type(car_data.get('model', ''))
                time.sleep(1)
                self.page.keyboard.press('Enter')
                time.sleep(1)
            
            # Year
            if self.page.locator('select[name*="year" i], input[placeholder*="year" i]').count() > 0:
                year_selector = 'select[name*="year" i], input[placeholder*="year" i]'
                if self.page.locator('select[name*="year" i]').count() > 0:
                    self.page.select_option('select[name*="year" i]', str(car_data.get('year', '')))
                else:
                    self.page.fill(year_selector, str(car_data.get('year', '')))
                time.sleep(1)
            
            # Fuel Type
            if self.page.locator('select[name*="fuel" i], button:has-text("' + car_data.get('fuel', 'Petrol') + '")').count() > 0:
                fuel = car_data.get('fuel', 'Petrol')
                # Try button first
                if self.page.locator(f'button:has-text("{fuel}")').count() > 0:
                    self.page.click(f'button:has-text("{fuel}")')
                else:
                    self.page.select_option('select[name*="fuel" i]', fuel)
                time.sleep(1)
            
            # Transmission
            if self.page.locator('select[name*="transmission" i]').count() > 0:
                self.page.select_option('select[name*="transmission" i]', car_data.get('transmission', 'Manual'))
                time.sleep(1)
            
            # KM Driven
            if self.page.locator('input[placeholder*="km" i], input[name*="odometer" i]').count() > 0:
                self.page.fill('input[placeholder*="km" i], input[name*="odometer" i]', str(car_data.get('km', '')))
                time.sleep(1)
            
            print("✅ Form filled successfully")
            return {"success": True, "message": "Form filled"}
            
        except Exception as e:
            print(f"❌ Error filling form: {e}")
            return {"success": False, "error": str(e)}
    
    def request_otp(self):
        """Click the Get OTP button"""
        try:
            print("📲 Requesting OTP...")
            
            # Find and click OTP button (multiple possible selectors)
            otp_buttons = [
                'button:has-text("Get OTP")',
                'button:has-text("Send OTP")',
                'button[type="submit"]',
                'button:has-text("Proceed")',
            ]
            
            clicked = False
            for selector in otp_buttons:
                if self.page.locator(selector).count() > 0:
                    self.page.click(selector)
                    clicked = True
                    break
            
            if not clicked:
                return {"success": False, "error": "OTP button not found"}
            
            time.sleep(3)
            print("✅ OTP requested")
            return {"success": True, "message": "OTP sent"}
            
        except Exception as e:
            print(f"❌ Error requesting OTP: {e}")
            return {"success": False, "error": str(e)}
    
    def submit_otp(self, otp):
        """Submit OTP and extract price"""
        try:
            print(f"🔐 Submitting OTP: {otp}")
            
            # Find OTP input field
            otp_input = 'input[type="text"][maxlength="6"], input[placeholder*="OTP" i], input[name*="otp" i]'
            
            if self.page.locator(otp_input).count() > 0:
                self.page.fill(otp_input, otp)
                time.sleep(1)
                
                # Submit
                submit_buttons = [
                    'button:has-text("Verify")',
                    'button:has-text("Submit")',
                    'button[type="submit"]'
                ]
                
                for selector in submit_buttons:
                    if self.page.locator(selector).count() > 0:
                        self.page.click(selector)
                        break
                
                # Wait for price to appear
                print("⏳ Waiting for valuation...")
                time.sleep(5)
                
                # Extract price (multiple possible selectors)
                price_selectors = [
                    '.valuation-price',
                    '[class*="price"]',
                    'h1:has-text("₹")',
                    'div:has-text("₹")',
                ]
                
                price = None
                for selector in price_selectors:
                    if self.page.locator(selector).count() > 0:
                        price_text = self.page.locator(selector).first.inner_text()
                        if '₹' in price_text:
                            price = price_text
                            break
                
                if price:
                    print(f"💰 Price extracted: {price}")
                    return {"success": True, "price": price}
                else:
                    # Take screenshot for debugging
                    self.page.screenshot(path="cars24_screenshot.png")
                    return {"success": False, "error": "Price not found", "screenshot": "cars24_screenshot.png"}
            else:
                return {"success": False, "error": "OTP input field not found"}
                
        except Exception as e:
            print(f"❌ Error submitting OTP: {e}")
            return {"success": False, "error": str(e)}
    
    def close_browser(self):
        """Close the browser and cleanup"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            print("🔒 Browser closed successfully")
        except Exception as e:
            print(f"Warning during cleanup: {e}")


# Test function
if __name__ == "__main__":
    automation = Cars24Automation()
    
    # Test data
    test_data = {
        "make": "Maruti",
        "model": "Swift",
        "year": 2020,
        "variant": "VXI",
        "fuel": "Petrol",
        "transmission": "Manual",
        "km": 40000,
        "city": "Delhi",
        "mobile": "9999999999"
    }
    
    print("🚀 Starting Cars24 Automation Test...")
    automation.start_browser(headless=False)
    automation.fill_car_details(test_data)
    automation.request_otp()
    
    # Wait for manual OTP entry
    otp = input("Enter OTP: ")
    result = automation.submit_otp(otp)
    print(f"Result: {result}")
    
    time.sleep(5)
    automation.close_browser()
