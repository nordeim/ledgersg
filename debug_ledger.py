#!/usr/bin/env python3
"""Debug script to check Ledger page structure"""

import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:3000"
CREDENTIALS = {"email": "lakshmi@kitchen.example", "password": "SecurePass123!"}


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        # Login
        print("🔐 Logging in...")
        await page.goto(f"{BASE_URL}/login")
        await page.wait_for_load_state("networkidle")

        await page.locator('input[type="email"]').fill(CREDENTIALS["email"])
        await page.locator('input[type="password"]').fill(CREDENTIALS["password"])

        async with page.expect_navigation(timeout=15000):
            await page.locator('button:has-text("Sign In")').click()

        await page.wait_for_load_state("networkidle")
        print(f"📍 After login: {page.url}")

        # Navigate to Ledger
        print("📊 Navigating to Ledger...")
        await page.goto(f"{BASE_URL}/ledger")
        await page.wait_for_load_state("networkidle")
        print(f"📍 Ledger URL: {page.url}")

        # Take screenshot
        await page.screenshot(path="/tmp/lakshmi/debug-ledger.png", full_page=True)
        print("📸 Screenshot saved")

        # Get all buttons
        print("\n🔍 Finding all buttons on page:")
        buttons = await page.locator("button").all()
        for i, btn in enumerate(buttons[:20]):
            text = await btn.inner_text()
            visible = await btn.is_visible()
            print(f"  Button {i}: '{text}' (visible: {visible})")

        # Get all links
        print("\n🔍 Finding all links:")
        links = await page.locator("a").all()
        for i, link in enumerate(links[:20]):
            text = await link.inner_text()
            href = await link.get_attribute("href")
            print(f"  Link {i}: '{text}' -> {href}")

        # Check for "New" buttons specifically
        print("\n🔍 Looking for 'New' buttons:")
        new_buttons = await page.locator('button:has-text("New")').all()
        print(f"  Found {len(new_buttons)} 'New' buttons")

        # Get page title and headings
        print("\n📄 Page structure:")
        title = await page.title()
        print(f"  Title: {title}")

        headings = await page.locator("h1, h2, h3").all()
        for h in headings[:10]:
            text = await h.inner_text()
            level = await h.evaluate("el => el.tagName")
            print(f"  {level}: '{text}'")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
