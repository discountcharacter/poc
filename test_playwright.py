"""
Simple Test Script to Check if Playwright Works
Run this to diagnose the issue
"""

from playwright.sync_api import sync_playwright
import sys

print("=" * 60)
print("Testing Playwright Browser Launch")
print("=" * 60)

try:
    print("\n1. Starting Playwright...")
    playwright = sync_playwright().start()
    print("   ✅ Playwright started")
    
    print("\n2. Launching Chromium browser...")
    browser = playwright.chromium.launch(headless=False)
    print("   ✅ Browser launched")
    
    print("\n3. Creating new page...")
    page = browser.new_page()
    print("   ✅ Page created")
    
    print("\n4. Navigating to Google...")
    page.goto("https://www.google.com", timeout=10000)
    print("   ✅ Navigation successful")
    
    print("\n5. Taking screenshot...")
    page.screenshot(path="test_screenshot.png")
    print("   ✅ Screenshot saved: test_screenshot.png")
    
    print("\n6. Closing browser...")
    browser.close()
    playwright.stop()
    print("   ✅ Browser closed")
    
    print("\n" + "=" * 60)
    print("✅ SUCCESS! Playwright is working correctly")
    print("=" * 60)
    
except Exception as e:
    print("\n" + "=" * 60)
    print(f"❌ ERROR: {type(e).__name__}")
    print(f"Message: {str(e)}")
    print("=" * 60)
    print("\nPossible solutions:")
    print("1. Run: python -m playwright install chromium")
    print("2. Check if antivirus is blocking browser")
    print("3. Try running as administrator")
    sys.exit(1)
