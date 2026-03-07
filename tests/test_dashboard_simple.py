"""
Simple Dashboard Test - After CORS Fix
"""

from playwright.sync_api import sync_playwright
import time


def test_dashboard():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to dashboard
        print("📍 Navigating to http://localhost:3000/dashboard/")
        page.goto("http://localhost:3000/dashboard/", timeout=30000)

        # Wait for content
        time.sleep(8)

        # Take screenshot
        page.screenshot(path="/tmp/dashboard_final.png", full_page=True)
        print("📸 Screenshot saved")

        # Get page info
        title = page.title()
        content = page.content()

        print(f"📄 Title: {title}")
        print(f"✅ Has 'Dashboard': {'Dashboard' in content}")
        print(f"⚠️  Has 'Loading': {'Loading' in content}")
        print(f"🏢 Has 'No Organisation': {'No Organisation' in content}")

        browser.close()


if __name__ == "__main__":
    test_dashboard()
