import os
import subprocess
import sys
import streamlit as st

def install_playwright_browsers():
    """
    Ensures Playwright chromium is installed.
    Designed for Streamlit Cloud deployment.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        st.error("Playwright package not found. Please add 'playwright' to requirements.txt")
        return False

    # Check for chromium binary in standard cache locations
    # On Streamlit Cloud it's usually in ~/.cache/ms-playwright/
    playwright_path = os.path.expanduser("~/.cache/ms-playwright")
    
    # Simple check: if the directory exists and contains chromium, we assume it's installed
    # More robust: run 'playwright install chromium' and catch errors
    
    if "PLAYWRIGHT_INSTALLED" not in st.session_state:
        with st.spinner("🔧 First run: Installing browser binaries (will take ~1 min)..."):
            try:
                # Install only chromium to save space and time
                subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
                st.session_state["PLAYWRIGHT_INSTALLED"] = True
                print("✅ Playwright Chromium installed successfully.")
                return True
            except Exception as e:
                st.error(f"Failed to install Playwright browsers: {e}")
                return False
    return True
