#!/usr/bin/env python3
"""
TDD Test for Phase 2: Login Backend Integration
Tests that login form connects to backend and redirects to dashboard
"""

import asyncio
import json
from playwright.async_api import async_playwright


async def test_login_flow():
    """
    RED Test: Login with valid credentials should redirect to dashboard

    Expected Behavior:
    1. Visit /login/
    2. Enter valid credentials (test@example.com / testpassword123)
    3. Submit form
    4. Backend returns JWT tokens
    5. Frontend stores tokens
    6. Redirect to /dashboard/
    7. Dashboard shows organisation data

    Current Behavior (FAILING):
    1. Login page uses simulated authentication
    2. No backend API call
    3. Just redirects after 1 second timeout
    """

    print("=" * 70)
    print("PHASE 2: Login Backend Integration - TDD TEST")
    print("=" * 70)
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        # Clear all cookies (fresh session)
        await context.clear_cookies()

        page = await context.new_page()

        # Track network requests
        requests_log = []
        page.on(
            "request",
            lambda req: requests_log.append(
                {
                    "url": req.url,
                    "method": req.method,
                }
            ),
        )

        # Track responses
        responses_log = []
        page.on(
            "response",
            lambda res: responses_log.append(
                {
                    "url": res.url,
                    "status": res.status,
                    "method": res.request.method,
                }
            ),
        )

        print("STEP 1: Visit login page")
        print("-" * 70)
        await page.goto(
            "http://localhost:3001/login/", wait_until="networkidle", timeout=15000
        )
        print(f"Current URL: {page.url}")
        print()

        print("STEP 2: Fill login form")
        print("-" * 70)

        # Fill email
        await page.fill('input[name="email"]', "test@example.com")
        print("✓ Entered email: test@example.com")

        # Fill password
        await page.fill('input[name="password"]', "testpassword123")
        print("✓ Entered password: testpassword123")
        print()

        print("STEP 3: Submit login form")
        print("-" * 70)

        # Click submit button
        await page.click('button[type="submit"]')
        print("✓ Clicked 'Sign In' button")

        # Wait for navigation or error
        try:
            await page.wait_for_url("**/dashboard/**", timeout=10000)
            print("✓ Redirected to dashboard")
        except:
            print("✗ Did NOT redirect to dashboard (timeout after 10s)")

        await page.wait_for_timeout(2000)

        # Get current URL
        current_url = page.url
        is_dashboard = "/dashboard" in current_url
        print(f"\nCurrent URL: {current_url}")
        print(f"Is Dashboard: {is_dashboard}")

        # Check for API calls
        print("\n" + "=" * 70)
        print("STEP 4: Analyze network requests")
        print("=" * 70)

        login_api_calls = [r for r in requests_log if "/auth/login/" in r["url"]]
        print(f"Login API calls: {len(login_api_calls)}")

        if login_api_calls:
            print("\n✓ Login API was called:")
            for req in login_api_calls:
                print(f"  - {req['method']} {req['url']}")

        me_api_calls = [r for r in requests_log if "/auth/me/" in r["url"]]
        print(f"\nAuth me API calls: {len(me_api_calls)}")

        orgs_api_calls = [r for r in requests_log if "/organisations/" in r["url"]]
        print(f"Organisations API calls: {len(orgs_api_calls)}")

        # Check response statuses
        login_responses = [r for r in responses_log if "/auth/login/" in r["url"]]
        if login_responses:
            print("\nLogin API response:")
            for res in login_responses:
                print(f"  - {res['method']} {res['url']} → {res['status']}")

        # Check page content
        content = await page.content()
        has_command_center = "Command Center" in content or "Dashboard" in content
        has_error_message = (
            "Invalid email or password" in content or "error" in content.lower()
        )

        print("\n" + "=" * 70)
        print("STEP 5: Check page content")
        print("=" * 70)
        print(f"Has Dashboard content: {has_command_center}")
        print(f"Has error message: {has_error_message}")

        # Take screenshot
        await page.screenshot(path="/tmp/phase2_test_result.png")
        print("\nScreenshot saved: /tmp/phase2_test_result.png")

        # Check cookies
        cookies = await context.cookies()
        print(f"\nCookies: {len(cookies)}")

        await browser.close()

        print("\n" + "=" * 70)
        print("TEST RESULTS")
        print("=" * 70)

        # Test assertions
        test_passed = True

        if not login_api_calls:
            print("❌ FAIL: Login API was NOT called")
            print("   → Login page is using simulated authentication")
            test_passed = False
        else:
            print("✅ PASS: Login API was called")

        if not is_dashboard:
            print("❌ FAIL: User was NOT redirected to dashboard")
            print(f"   → Current URL: {current_url}")
            test_passed = False
        else:
            print("✅ PASS: User was redirected to dashboard")

        if not has_command_center:
            print("❌ FAIL: Dashboard content not visible")
            test_passed = False
        else:
            print("✅ PASS: Dashboard content is visible")

        print()

        if test_passed:
            print("✅ ALL TESTS PASSED - Phase 2 implementation is working")
            return True
        else:
            print(
                "❌ SOME TESTS FAILED - This is EXPECTED before Phase 2 implementation"
            )
            print("\nNext Steps:")
            print("1. Modify AuthProvider.login() to match backend response")
            print("2. Connect login page to AuthProvider.login()")
            print("3. Handle API errors appropriately")
            return False


if __name__ == "__main__":
    result = asyncio.run(test_login_flow())
    exit(0 if result else 1)
