#!/usr/bin/env python3
"""
Dashboard Investigation Script
Analyzes why the dashboard shows "No Organisation Selected"
"""

import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright


async def investigate_dashboard():
    print("=== DASHBOARD INVESTIGATION STARTED ===\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)

        context = await browser.new_context(record_har_path="/tmp/dashboard-har.json")

        page = await context.new_page()

        # Track all network requests and responses
        requests_log = []
        responses_log = []
        console_log = []
        errors_log = []

        async def on_request(request):
            requests_log.append(
                {
                    "url": request.url,
                    "method": request.method,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        async def on_response(response):
            request = response.request
            body = None
            try:
                if "application/json" in (response.headers.get("content-type") or ""):
                    body = await response.json()
            except:
                pass

            responses_log.append(
                {
                    "url": response.url,
                    "method": request.method,
                    "status": response.status,
                    "status_text": response.status_text,
                    "headers": dict(response.headers),
                    "body": body,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        async def on_console(msg):
            console_log.append(
                {
                    "type": msg.type,
                    "text": msg.text,
                    "location": msg.location,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        async def on_error(error):
            errors_log.append(
                {
                    "message": error.message,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        page.on("request", on_request)
        page.on("response", on_response)
        page.on("console", on_console)
        page.on("pageerror", on_error)

        print("1. NAVIGATING TO DASHBOARD...\n")
        await page.goto(
            "http://localhost:3000/dashboard/", wait_until="networkidle", timeout=30000
        )

        # Wait for async operations
        await page.wait_for_timeout(3000)

        print("2. CHECKING PAGE STATE...\n")

        # Get page title
        title = await page.title()
        print(f"   Page Title: {title}")

        # Get current URL
        url = page.url
        print(f"   Current URL: {url}")

        # Check if redirected to login
        is_login_page = "/login" in url
        print(f"   Is Login Page: {is_login_page}")

        # Check for specific elements
        has_loader = await page.locator(".animate-spin").count() > 0
        print(f"   Has Loader: {has_loader}")

        has_alert_triangle = await page.locator("svg.lucide-alert-triangle").count() > 0
        print(f"   Has AlertTriangle Icon: {has_alert_triangle}")

        has_org_text = await page.locator("text=No Organisation Selected").count() > 0
        print(f"   Has 'No Organisation Selected': {has_org_text}")

        # Get main text content
        main_text = await page.locator("body").text_content()
        if main_text:
            print(f"   Main Text (first 200 chars): {main_text[:200]}")

        print("\n3. ANALYZING NETWORK REQUESTS...\n")

        # Filter auth-related requests/responses
        auth_requests = [
            r
            for r in requests_log
            if "/auth/" in r["url"] or "/organisations/" in r["url"]
        ]
        print(f"   Auth-related Requests: {len(auth_requests)}")

        auth_responses = [
            r
            for r in responses_log
            if "/auth/" in r["url"] or "/organisations/" in r["url"]
        ]
        print(f"   Auth-related Responses: {len(auth_responses)}")

        if auth_responses:
            print("\n   Auth Response Details:")
            for res in auth_responses:
                print(f"   - {res['method']} {res['url']}")
                print(f"     Status: {res['status']} {res['status_text']}")
                if res["body"]:
                    body_str = json.dumps(res["body"], indent=2)
                    print(f"     Body: {body_str[:300]}")

        # Check cookies
        cookies = await context.cookies()
        print(f"\n   Total Cookies: {len(cookies)}")
        for cookie in cookies:
            if any(x in cookie["name"] for x in ["refresh", "access", "session"]):
                print(f"   - {cookie['name']}: {cookie['value'][:20]}...")
                print(f"     Domain: {cookie['domain']}, Path: {cookie['path']}")
                print(
                    f"     HttpOnly: {cookie['httpOnly']}, Secure: {cookie['secure']}"
                )

        print("\n4. ANALYZING CONSOLE MESSAGES...\n")
        print(f"   Total Console Messages: {len(console_log)}")

        error_msgs = [m for m in console_log if m["type"] == "error"]
        if error_msgs:
            print(f"   Error Messages: {len(error_msgs)}")
            for err in error_msgs:
                print(f"   - [{err['type']}] {err['text']}")
                if err.get("location"):
                    loc = err["location"]
                    print(f"     at {loc.get('url')}:{loc.get('lineNumber')}")

        print("\n5. ANALYZING JAVASCRIPT ERRORS...\n")
        print(f"   JS Errors: {len(errors_log)}")
        for err in errors_log:
            print(f"   - {err['message']}")

        # Take screenshot
        await page.screenshot(path="/tmp/dashboard-screenshot.png", full_page=True)
        print("\n6. SCREENSHOT SAVED: /tmp/dashboard-screenshot.png\n")

        print("7. HAR FILE SAVED: /tmp/dashboard-har.json\n")

        # Summary
        print("=== INVESTIGATION SUMMARY ===\n")
        print("Root Cause Analysis:")
        print("====================")

        if is_login_page:
            print("✓ User was redirected to LOGIN PAGE")
            print("  → No valid authentication session")
            print("  → Browser has no refresh token cookie")
            print("  → AuthProvider caught 401 error and cleared state")
        elif has_org_text:
            print("✓ Dashboard rendered with 'No Organisation Selected'")
            print("  → User is authenticated but has no organisation")
            print("  → OR auth check succeeded but organisation fetch failed")
            print("  → Check auth/me/ and auth/organisations/ responses")

            me_response = next(
                (r for r in auth_responses if "/auth/me/" in r["url"]), None
            )
            orgs_response = next(
                (r for r in auth_responses if "/organisations/" in r["url"]), None
            )

            if me_response:
                print(f"\n  auth/me/ status: {me_response['status']}")
                if me_response["status"] == 401:
                    print("  → User is NOT authenticated (401)")
                elif me_response["status"] == 200:
                    print("  → User IS authenticated")
                    if me_response.get("body"):
                        print(f"  → User data: {json.dumps(me_response['body'])}")

            if orgs_response:
                print(f"\n  organisations/ status: {orgs_response['status']}")
                if orgs_response["status"] == 401:
                    print("  → Organisations fetch failed (401)")
                elif orgs_response["status"] == 200:
                    print("  → Organisations fetch succeeded")
                    if orgs_response.get("body"):
                        if isinstance(orgs_response["body"], list):
                            count = len(orgs_response["body"])
                            print(f"  → Organisations count: {count}")
                            if count == 0:
                                print("  → User has NO organisations (empty array)")
        elif has_loader:
            print("✓ Dashboard is still LOADING")
            print("  → AuthProvider is still checking session")
            print("  → API calls may be slow or timing out")
        else:
            print("✓ Dashboard rendered successfully (or unknown state)")
            print("  → Check screenshot for actual content")

        print("\n=== INVESTIGATION COMPLETE ===\n")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(investigate_dashboard())
