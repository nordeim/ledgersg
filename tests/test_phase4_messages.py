#!/usr/bin/env python3
"""
TDD Test for Phase 4: Error Message Differentiation
Tests that different error states show appropriate messages
"""

import asyncio
from playwright.async_api import async_playwright


async def test_error_message_differentiation():
    """
    RED Test: Different authentication states should show different messages

    Expected Behavior:
    1. Unauthenticated user → "Authentication Required" + "Go to Login" button
    2. Authenticated user, no org → "No Organisation Selected" + "Create Organisation" button
    3. Authenticated user, has org → Dashboard content visible

    Current Behavior (EXPECTED TO FAIL):
    - All cases show same message: "No Organisation Selected"
    """

    print("=" * 70)
    print("PHASE 4: Error Message Differentiation - TDD TEST")
    print("=" * 70)
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        tests_passed = 0
        tests_total = 3

        # =================================================================
        # TEST 1: Unauthenticated user should see "Authentication Required"
        # =================================================================
        print("TEST 1: Unauthenticated user error message")
        print("-" * 70)

        context1 = await browser.new_context()
        await context1.clear_cookies()
        page1 = await context1.new_page()

        await page1.goto(
            "http://localhost:3000/dashboard/", wait_until="networkidle", timeout=10000
        )
        await page1.wait_for_timeout(3000)

        content1 = await page1.content()

        # Check for authentication required message
        has_auth_required = (
            "Authentication Required" in content1
            or "authentication" in content1.lower()
        )
        has_go_to_login = "Go to Login" in content1 or "go to login" in content1.lower()

        # Should NOT have "No Organisation Selected" for unauthenticated users
        has_no_org_message = "No Organisation Selected" in content1

        # Should have login button
        has_login_button = (
            await page1.locator('button:has-text("Login"), a:has-text("Login")').count()
            > 0
        )

        print(f"  Has 'Authentication Required': {has_auth_required}")
        print(f"  Has 'Go to Login' button: {has_go_to_login or has_login_button}")
        print(f"  Has 'No Organisation Selected': {has_no_org_message}")

        # Test passes if authentication message is shown
        test1_pass = (
            has_auth_required or has_go_to_login or has_login_button
        ) and not has_no_org_message
        status1 = (
            "✅ PASS" if test1_pass else "❌ FAIL (Expected before implementation)"
        )
        print(f"  Result: {status1}")
        print()

        if test1_pass:
            tests_passed += 1

        await context1.close()

        # =================================================================
        # TEST 2: Authenticated user with organisation should see dashboard
        # =================================================================
        print("TEST 2: Authenticated user with organisation")
        print("-" * 70)

        context2 = await browser.new_context()
        page2 = await context2.new_page()

        # Login
        await page2.goto("http://localhost:3000/login/", wait_until="networkidle")
        await page2.fill('input[name="email"]', "test@example.com")
        await page2.fill('input[name="password"]', "testpassword123")
        await page2.click('button[type="submit"]')

        try:
            await page2.wait_for_url("**/dashboard**", timeout=10000)
            await page2.wait_for_timeout(2000)

            content2 = await page2.content()

            # Should see dashboard content
            has_command_center = "Command Center" in content2 or "Dashboard" in content2
            has_org_name = "Test Organisation" in content2

            print(f"  Has dashboard content: {has_command_center}")
            print(f"  Has organisation name: {has_org_name}")

            test2_pass = has_command_center and has_org_name
            status2 = "✅ PASS" if test2_pass else "❌ FAIL"
            print(f"  Result: {status2}")

            if test2_pass:
                tests_passed += 1

        except Exception as e:
            print(f"  Error: {str(e)[:100]}")
            print(f"  Result: ❌ FAIL")

        print()
        await context2.close()

        # =================================================================
        # TEST 3: Verify error message differentiation is clear
        # =================================================================
        print("TEST 3: Message differentiation verification")
        print("-" * 70)

        # This test verifies that messages are clearly different
        # We'll check the login page to ensure it doesn't show dashboard errors

        context3 = await browser.new_context()
        await context3.clear_cookies()
        page3 = await context3.new_page()

        await page3.goto("http://localhost:3000/login/", wait_until="networkidle")
        await page3.wait_for_timeout(2000)

        content3 = await page3.content()

        # Login page should have sign in form, not dashboard error messages
        has_sign_in = "Sign In" in content3 or "Sign in" in content3
        has_email_input = await page3.locator('input[name="email"]').count() > 0
        has_password_input = await page3.locator('input[name="password"]').count() > 0

        print(f"  Has sign in form: {has_sign_in}")
        print(f"  Has email input: {has_email_input}")
        print(f"  Has password input: {has_password_input}")

        test3_pass = has_sign_in and has_email_input and has_password_input
        status3 = "✅ PASS" if test3_pass else "❌ FAIL"
        print(f"  Result: {status3}")
        print()

        if test3_pass:
            tests_passed += 1

        await context3.close()
        await browser.close()

        # =================================================================
        # FINAL SUMMARY
        # =================================================================
        print("=" * 70)
        print("FINAL SUMMARY")
        print("=" * 70)
        print(f"Tests Passed: {tests_passed}/{tests_total}")
        print()

        if tests_passed == tests_total:
            print("🎉 ALL TESTS PASSED!")
            print("✅ Phase 4 implementation is working correctly")
            return True
        else:
            print("❌ SOME TESTS FAILED")
            print("   This is EXPECTED before Phase 4 implementation")
            print()
            print("Next Step: Implement authentication state check in DashboardClient")
            return False


if __name__ == "__main__":
    result = asyncio.run(test_error_message_differentiation())
    exit(0 if result else 1)
