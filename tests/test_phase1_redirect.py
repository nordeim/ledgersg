#!/usr/bin/env python3
"""
TDD Test for Phase 1: AuthProvider Redirect
Tests that unauthenticated users are redirected to /login
"""

import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright


async def test_unauthenticated_redirect():
    """
    RED Test: Unauthenticated user should be redirected to /login

    Expected Behavior:
    1. Visit /dashboard/ with no cookies
    2. AuthProvider calls /api/v1/auth/me/
    3. Backend returns 401
    4. AuthProvider redirects to /login

    Current Behavior (FAILING):
    1. Visit /dashboard/
    2. Shows "No Organisation Selected" (no redirect)
    """

    print("=" * 60)
    print("PHASE 1: AuthProvider Redirect - TDD TEST")
    print("=" * 60)
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        # Clear all cookies (simulate fresh browser session)
        await context.clear_cookies()

        page = await context.new_page()

        # Track redirects
        redirects = []
        page.on(
            "response",
            lambda response: redirects.append(
                {
                    "url": response.url,
                    "status": response.status,
                }
            )
            if response.status in [301, 302, 303, 307, 308]
            else None,
        )

        print("STEP 1: Visit /dashboard/ with no authentication")
        print("-" * 60)

        # Visit dashboard
        await page.goto(
            "http://localhost:3000/dashboard/", wait_until="networkidle", timeout=15000
        )

        # Wait for potential redirect
        await page.wait_for_timeout(2000)

        # Get current URL
        current_url = page.url
        print(f"Current URL: {current_url}")

        # Check if redirected to login
        is_login_page = "/login" in current_url
        print(f"Is Login Page: {is_login_page}")

        # Get page content
        content = await page.content()
        has_no_org_message = "No Organisation Selected" in content
        has_login_form = "Sign In" in content or "Sign in" in content

        print(f"Has 'No Organisation Selected': {has_no_org_message}")
        print(f"Has Login Form: {has_login_form}")
        print()

        # Take screenshot
        await page.screenshot(path="/tmp/phase1_test_result.png")
        print("Screenshot saved: /tmp/phase1_test_result.png")
        print()

        await browser.close()

        print("=" * 60)
        print("TEST RESULTS")
        print("=" * 60)

        # Expected behavior (currently failing)
        print("Expected: User redirected to /login")
        print(f"Actual: User is on {current_url}")
        print()

        # Test assertion
        if is_login_page:
            print("✅ PASS: User was redirected to login page")
            print("✅ Phase 1 implementation is working correctly")
            return True
        else:
            print("❌ FAIL: User was NOT redirected to login page")
            print("❌ This is EXPECTED before Phase 1 implementation")
            print()
            print("Next Step: Implement AuthProvider redirect logic")
            return False


if __name__ == "__main__":
    result = asyncio.run(test_unauthenticated_redirect())
    exit(0 if result else 1)
