"""
Final Dashboard Test - After CORS Fix
"""

from playwright.sync_api import sync_playwright
import time


def test_dashboard_after_cors_fix():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Track console messages
        console_messages = []
        page.on("console", lambda msg: console_messages.append(f"{msg.type()}: {msg.text}"))

        # Track network failures
        failed_requests = []
        page.on(
            "requestfailed",
            lambda req: failed_requests.append(f"{req.method} {req.url}: {req.failure}"),
        )

        # Navigate to dashboard
        print("📍 Navigating to http://localhost:3000/dashboard/")
        page.goto("http://localhost:3000/dashboard/", wait_until="networkidle", timeout=30000)

        # Wait for content to load
        time.sleep(5)

        # Take screenshot
        page.screenshot(path="/tmp/dashboard_final.png", full_page=True)
        print("📸 Screenshot saved to /tmp/dashboard_final.png")

        # Check page state
        content = page.content()
        title = page.title()

        print(f"\n📊 Page Title: {title}")

        # Check for specific elements
        has_loading = "Loading" in content or "loading" in content
        has_no_org = "No Organisation Selected" in content
        has_dashboard = "Dashboard" in content
        has_error = "Error" in content or "error" in content.lower()

        print(f"\n🔍 Page State:")
        print(f"  - Has 'Loading': {has_loading}")
        print(f"  - Has 'No Organisation': {has_no_org}")
        print(f"  - Has 'Dashboard': {has_dashboard}")
        print(f"  - Has 'Error': {has_error}")

        # Print console messages
        if console_messages:
            print(f"\n📋 Console Messages ({len(console_messages)}):")
            for msg in console_messages[:10]:  # First 10
                print(f"  {msg}")

        # Print failed requests
        if failed_requests:
            print(f"\n❌ Failed Requests ({len(failed_requests)}):")
            for req in failed_requests[:10]:
                print(f"  {req}")

        browser.close()

        return {
            "title": title,
            "has_loading": has_loading,
            "has_no_org": has_no_org,
            "has_dashboard": has_dashboard,
            "has_error": has_error,
            "console_count": len(console_messages),
            "failed_count": len(failed_requests),
        }


if __name__ == "__main__":
    result = test_dashboard_after_cors_fix()
    print(f"\n✅ Test Complete: {result}")
