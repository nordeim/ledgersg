const { chromium } = require('playwright');

async function investigateDashboard() {
  console.log('=== DASHBOARD INVESTIGATION STARTED ===\n');
  
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 500,
  });
  
  const context = await browser.newContext({
    // Enable request interception to monitor API calls
    recordHar: {
      path: '/tmp/dashboard-har.json',
    },
  });
  
  const page = await context.newPage();
  
  // Track all network requests
  const requests = [];
  page.on('request', req => {
    requests.push({
      url: req.url(),
      method: req.method(),
      timestamp: new Date().toISOString(),
    });
  });
  
  // Track all responses
  const responses = [];
  page.on('response', async res => {
    const req = res.request();
    let body = null;
    try {
      if (res.headers()['content-type']?.includes('application/json')) {
        body = await res.json();
      }
    } catch (e) {
      // Ignore parsing errors
    }
    
    responses.push({
      url: res.url(),
      method: req.method(),
      status: res.status(),
      statusText: res.statusText(),
      headers: res.headers(),
      body: body,
      timestamp: new Date().toISOString(),
    });
  });
  
  // Track console messages
  const consoleMessages = [];
  page.on('console', msg => {
    consoleMessages.push({
      type: msg.type(),
      text: msg.text(),
      location: msg.location(),
      timestamp: new Date().toISOString(),
    });
  });
  
  // Track JavaScript errors
  const errors = [];
  page.on('pageerror', error => {
    errors.push({
      message: error.message,
      stack: error.stack,
      timestamp: new Date().toISOString(),
    });
  });
  
  console.log('1. NAVIGATING TO DASHBOARD...\n');
  await page.goto('http://localhost:3000/dashboard/', { 
    waitUntil: 'networkidle',
    timeout: 30000,
  });
  
  // Wait a bit for any async operations
  await page.waitForTimeout(3000);
  
  console.log('2. CHECKING PAGE STATE...\n');
  
  // Get page title
  const title = await page.title();
  console.log('   Page Title:', title);
  
  // Get page URL (check for redirects)
  const url = page.url();
  console.log('   Current URL:', url);
  
  // Check if we're on login page (redirected)
  const isLoginPage = url.includes('/login');
  console.log('   Is Login Page:', isLoginPage);
  
  // Get page content
  const content = await page.content();
  console.log('   Page Content Length:', content.length);
  
  // Check for specific elements
  const hasLoader = await page.locator('.animate-spin').count() > 0;
  console.log('   Has Loader:', hasLoader);
  
  const hasAlertTriangle = await page.locator('svg.lucide-alert-triangle').count() > 0;
  console.log('   Has AlertTriangle Icon:', hasAlertTriangle);
  
  const hasOrganisationText = await page.locator('text=No Organisation Selected').count() > 0;
  console.log('   Has "No Organisation Selected" Text:', hasOrganisationText);
  
  const hasLoginButton = await page.locator('button:has-text("Login")').count() > 0;
  console.log('   Has Login Button:', hasLoginButton);
  
  // Try to get the actual displayed text
  const mainText = await page.locator('body').textContent();
  console.log('   Main Text (first 200 chars):', mainText?.substring(0, 200));
  
  console.log('\n3. ANALYZING NETWORK REQUESTS...\n');
  
  // Find auth-related requests
  const authRequests = requests.filter(r => 
    r.url.includes('/auth/') || r.url.includes('/organisations/')
  );
  console.log('   Auth-related Requests:', authRequests.length);
  
  const authResponses = responses.filter(r => 
    r.url.includes('/auth/') || r.url.includes('/organisations/')
  );
  console.log('   Auth-related Responses:', authResponses.length);
  
  // Print details of auth requests/responses
  if (authResponses.length > 0) {
    console.log('\n   Auth Response Details:');
    for (const res of authResponses) {
      console.log(`   - ${res.method} ${res.url}`);
      console.log(`     Status: ${res.status} ${res.statusText}`);
      if (res.body) {
        console.log(`     Body:`, JSON.stringify(res.body, null, 2).substring(0, 200));
      }
    }
  }
  
  // Check for cookies
  const cookies = await context.cookies();
  console.log('\n   Cookies:', cookies.length);
  for (const cookie of cookies) {
    if (cookie.name.includes('refresh') || cookie.name.includes('access') || cookie.name.includes('session')) {
      console.log(`   - ${cookie.name}: ${cookie.value.substring(0, 20)}...`);
      console.log(`     Domain: ${cookie.domain}, Path: ${cookie.path}`);
      console.log(`     HttpOnly: ${cookie.httpOnly}, Secure: ${cookie.secure}`);
    }
  }
  
  console.log('\n4. ANALYZING CONSOLE MESSAGES...\n');
  console.log('   Total Console Messages:', consoleMessages.length);
  
  const errorMessages = consoleMessages.filter(m => m.type === 'error');
  if (errorMessages.length > 0) {
    console.log('   Error Messages:', errorMessages.length);
    for (const err of errorMessages) {
      console.log(`   - [${err.type}] ${err.text}`);
      if (err.location) {
        console.log(`     at ${err.location.url}:${err.location.lineNumber}`);
      }
    }
  }
  
  const warningMessages = consoleMessages.filter(m => m.type === 'warning');
  if (warningMessages.length > 0) {
    console.log('   Warning Messages:', warningMessages.length);
    for (const warn of warningMessages) {
      console.log(`   - [${warn.type}] ${warn.text}`);
    }
  }
  
  console.log('\n5. ANALYZING JAVASCRIPT ERRORS...\n');
  console.log('   JS Errors:', errors.length);
  if (errors.length > 0) {
    for (const err of errors) {
      console.log(`   - ${err.message}`);
      console.log(`     Stack: ${err.stack?.substring(0, 200)}`);
    }
  }
  
  // Take a screenshot
  await page.screenshot({ path: '/tmp/dashboard-screenshot.png', fullPage: true });
  console.log('\n6. SCREENSHOT SAVED: /tmp/dashboard-screenshot.png\n');
  
  // Get the HAR file path
  console.log('7. HAR FILE SAVED: /tmp/dashboard-har.json\n');
  
  // Summary
  console.log('=== INVESTIGATION SUMMARY ===\n');
  console.log('Root Cause Analysis:');
  console.log('====================');
  
  if (isLoginPage) {
    console.log('✓ User was redirected to LOGIN PAGE');
    console.log('  → No valid authentication session');
    console.log('  → Browser has no refresh token cookie');
    console.log('  → AuthProvider caught 401 error and cleared state');
  } else if (hasOrganisationText) {
    console.log('✓ Dashboard rendered with "No Organisation Selected"');
    console.log('  → User is authenticated but has no organisation');
    console.log('  → OR auth check succeeded but organisation fetch failed');
    console.log('  → Check auth/me/ and auth/organisations/ responses');
    
    if (authResponses.length > 0) {
      const meResponse = authResponses.find(r => r.url.includes('/auth/me/'));
      const orgsResponse = authResponses.find(r => r.url.includes('/organisations/'));
      
      if (meResponse) {
        console.log(`\n  auth/me/ status: ${meResponse.status}`);
        if (meResponse.status === 401) {
          console.log('  → User is NOT authenticated (401)');
        } else if (meResponse.status === 200) {
          console.log('  → User IS authenticated');
          if (meResponse.body) {
            console.log('  → User data:', JSON.stringify(meResponse.body));
          }
        }
      }
      
      if (orgsResponse) {
        console.log(`\n  organisations/ status: ${orgsResponse.status}`);
        if (orgsResponse.status === 401) {
          console.log('  → Organisations fetch failed (401)');
        } else if (orgsResponse.status === 200) {
          console.log('  → Organisations fetch succeeded');
          if (orgsResponse.body) {
            if (Array.isArray(orgsResponse.body)) {
              console.log(`  → Organisations count: ${orgsResponse.body.length}`);
              if (orgsResponse.body.length === 0) {
                console.log('  → User has NO organisations (empty array)');
              }
            }
          }
        }
      }
    }
  } else if (hasLoader) {
    console.log('✓ Dashboard is still LOADING');
    console.log('  → AuthProvider is still checking session');
    console.log('  → API calls may be slow or timing out');
  } else {
    console.log('✓ Dashboard rendered successfully (or unknown state)');
    console.log('  → Check screenshot for actual content');
  }
  
  console.log('\n=== INVESTIGATION COMPLETE ===\n');
  
  await browser.close();
}

investigateDashboard().catch(console.error);
