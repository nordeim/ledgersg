#!/usr/bin/env python3
"""
TDD Test for Phase 3: Authentication Guard
Tests that protected routes require authentication
"""

import asyncio
from playwright.async_api import async_playwright


async def test_authentication_guard():
    """
    RED Test: Protected routes should redirect to login when not authenticated

    Expected Behavior:
    1. Clear all cookies (no authentication)
    2. Visit protected route (e.g., /invoices/)
    3. Should redirect to /login
    4. Should NOT show protected content

    Current Behavior (EXPECTED TO FAIL):
    1. Visit protected route
    2. Shows "No Organisation Selected" (no route guard)
    """

    print("=" * 70)
    print("PHASE 3: Authentication Guard - TDD TEST")
    print("=" * 70)
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # Test multiple protected routes
        protected_routes = [
            "/invoices/",
            "/quotes/",
            "/ledger/",
            "/banking/",
            "/reports/",
            "/settings/",
        ]

        results = []

        for route in protected_routes:
            context = await browser.new_context()
            await context.clear_cookies()
            page = await context.new_page()

            print(f"Testing route: {route}")
            print("-" * 70)

            # Track redirects
            final_url = None
            redirect_occurred = False

            try:
                # Visit protected route
                await page.goto(
                    f"http://localhost:3000{route}",
                    wait_until="networkidle",
                    timeout=10000,
                )
                await page.wait_for_timeout(2000)

                final_url = page.url
                redirect_occurred = "/login" in final_url

                print(f"  Initial URL: http://localhost:3000{route}")
                print(f"  Final URL: {final_url}")
                print(f"  Redirected to login: {redirect_occurred}")

                # Check for protected content
                content = await page.content()
                has_protected_content = any(
                    [
                        "Invoices" in content and "New Invoice" in content,
                        "Quotes" in content and "New Quote" in content,
                        "Ledger" in content and "Journal Entry" in content,
                        "Banking" in content and "Bank Accounts" in content,
                        "Reports" in content and "Financial" in content,
                        "Settings" in content and "Organisation" in content,
                    ]
                )

                # Check for login form
                has_login_form = "Sign In" in content or "Sign in" in content

                print(f"  Has protected content: {has_protected_content}")
                print(f"  Has login form: {has_login_form}")
                print()

                # Store result
                test_passed = redirect_occurred and not has_protected_content
                results.append(
                    {
                        "route": route,
                        "passed": test_passed,
                        "redirected": redirect_occurred,
                        "has_protected_content": has_protected_content,
                    }
                )

            except Exception as e:
                print(f"  Error: {str(e)[:100]}")
                print()
                results.append(
                    {
                        "route": route,
                        "passed": False,
                        "error": str(e),
                    }
                )

            await context.close()

        await browser.close()

        # Summary
        print("=" * 70)
        print("TEST RESULTS SUMMARY")
        print("=" * 70)
        print()

        passed = sum(1 for r in results if r.get("passed", False))
        total = len(results)

        for result in results:
            status = "✅ PASS" if result.get("passed") else "❌ FAIL"
            print(f"{status}: {result['route']}")
            if not result.get("passed"):
                if "error" in result:
                    print(f"        Error: {result['error'][:100]}")
                else:
                    print(f"        Redirected: {result.get('redirected')}")
                    print(
                        f"        Has protected content: {result.get('has_protected_content')}"
                    )

        print()
        print(f"Tests Passed: {passed}/{total}")
        print()

        if passed == total:
            print("🎉 ALL TESTS PASSED!")
            print("✅ Phase 3 implementation is working correctly")
            return True
        else:
            print("❌ SOME TESTS FAILED")
            print("   This is EXPECTED before Phase 3 implementation")
            print()
            print("Next Step: Implement authentication guard in DashboardLayout")
            return False


if __name__ == "__main__":
    result = asyncio.run(test_authentication_guard())
    exit(0 if result else 1)
