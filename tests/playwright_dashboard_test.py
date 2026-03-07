import asyncio
from playwright.async_api import async_playwright

async def inspect_dashboard():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Capture console messages
        page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.type} {msg.text}"))
        
        # Capture network requests
        page.on("request", lambda req: print(f"REQUEST: {req.method} {req.url}") if "localhost:8000" in req.url or "dashboard" in req.url else None)
        page.on("response", lambda res: print(f"RESPONSE: {res.status} {res.url}") if "localhost:8000" in res.url or "dashboard" in res.url else None)
        
        # Navigate to dashboard
        print("\n=== NAVIGATING TO DASHBOARD ===\n")
        await page.goto('http://localhost:3000/dashboard/', wait_until='networkidle', timeout=10000)
        
        # Wait for async operations
        await page.wait_for_timeout(3000)
        
        # Check for loading spinner
        spinner = await page.query_selector('svg.lucide-loader-circle')
        if spinner:
            print("\n⚠️  LOADING SPINNER STILL VISIBLE - Dashboard not loaded")
        else:
            print("\n✅ No loading spinner found")
        
        # Get page title
        title = await page.title()
        print(f"Page title: {title}")
        
        # Check for error messages
        error_elements = await page.query_selector_all('text=/error|Error|failed|Failed/i')
        if error_elements:
            print(f"⚠️  Found error elements: {len(error_elements)}")
        
        # Get page content
        content = await page.content()
        if "Loading" in content:
            print("⚠️  'Loading' text still present in page")
        
        await browser.close()

asyncio.run(inspect_dashboard())
