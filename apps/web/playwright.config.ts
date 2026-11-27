import { defineConfig, devices } from "@playwright/test";

/**
 * LEDGERSG PLAYWRIGHT CONFIGURATION
 *
 * Purpose: E2E testing for critical user flows
 * Coverage: Auth, Invoice creation, Dashboard navigation
 *
 * Projects:
 * - Default: chromium only (works on any machine with `npx playwright install chromium`)
 * - Full matrix (firefox, webkit, Mobile Chrome, Mobile Safari): opt in with
 *   PLAYWRIGHT_PROJECTS=all — requires `npx playwright install` for those browsers.
 *   Rationale (B-1): declaring browsers that are not installed makes
 *   `npm run test:e2e` fail wholesale; green-by-default beats red-by-default.
 *   Mobile viewport coverage is always exercised by the responsive tests in
 *   e2e/navigation.spec.ts via setViewportSize, so the default set loses nothing.
 *
 * Backend-dependent specs (auth error surfacing, the authenticated invoice
 * form, the session-persistence/reload specs) read E2E_API_URL and skip when
 * it is unset — same green-by-default philosophy. `npm run test:e2e:full`
 * sets E2E_API_URL=http://127.0.0.1:8000 and requires the Django backend +
 * Redis to be running.
 *
 * See https://playwright.dev/docs/test-configuration
 */

const fullMatrix = process.env.PLAYWRIGHT_PROJECTS === "all";

// P16/FE-M4: the LIVE suite (E2E_API_URL set) mutates shared backend
// state — the p11 ensureDemoActivity helpers are check-then-create and
// the banking/invoices specs assume file ordering. That contract used
// to live only in the npm script's --workers=1; anyone running
// `E2E_API_URL=... npx playwright test` re-enabled the race. Encode it
// here: the default (no-backend) suite stays parallel; the live suite
// runs serially in the config itself.
const liveBackend = Boolean(process.env.E2E_API_URL);

export default defineConfig({
  testDir: "./e2e",

  /* Run tests in files in parallel — except the live suite (see above) */
  fullyParallel: !liveBackend,

  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* Opt out of parallel tests on CI for stability; the live suite is
     serial by its own contract (P16/FE-M4). */
  workers: process.env.CI ? 1 : liveBackend ? 1 : undefined,

  /* Terminal summary always; HTML report written without opening a browser */
  reporter: [["list"], ["html", { open: "never" }]],

  /* Artifacts from failed runs */
  outputDir: "./test-results",

  /* Shared settings for all the projects below */
  use: {
    /* Base URL to use in actions like `await page.goto('/')` */
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000",

    /* Collect trace when retrying the failed test — and retain it on
       failure. P20/FE-M6: local runs have retries: 0, so
       on-first-retry produced NO trace for local failures (only the
       screenshot); retain-on-failure is Playwright's recommended policy
       for exactly this setup. */
    trace: "retain-on-failure",

    /* Screenshot on failure */
    screenshot: "only-on-failure",

    /* Video recording */
    video: "on-first-retry",

    /* Viewport */
    viewport: { width: 1280, height: 720 },

    /* P20/FE-M6: pin the locale + timezone — the app renders dates via
       toLocaleDateString("en-SG") and date-only strings parse as UTC
       midnight; an unpinned runner timezone makes date assertions
       runner-dependent (and masked the off-by-one the P20/FE-M7 fix
       closed). Asia/Singapore is the user base. */
    locale: "en-SG",
    timezoneId: "Asia/Singapore",

    /* Action timeout */
    actionTimeout: 15000,

    /* Navigation timeout */
    navigationTimeout: 15000,
  },

  /* P13: expect-level timeout for web-first assertions (the default 5s
     is tight for dev-mode on-demand route compilation). */
  expect: { timeout: 10_000 },

  /* Configure projects — chromium by default, full matrix via PLAYWRIGHT_PROJECTS=all */
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },

    ...(fullMatrix
      ? [
          {
            name: "firefox",
            use: { ...devices["Desktop Firefox"] },
          },
          {
            name: "webkit",
            use: { ...devices["Desktop Safari"] },
          },
          {
            name: "Mobile Chrome",
            use: { ...devices["Pixel 5"] },
          },
          {
            name: "Mobile Safari",
            use: { ...devices["iPhone 12"] },
          },
        ]
      : []),
  ],

  /* Run local dev server before starting the tests */
  webServer: {
    command: "npm run dev",
    /* P20/FE-M6 note: Playwright has no strictPort knob and rejects
       port+url together — the url stays the readiness probe. Residual
       caveat (documented, not fixable at this level): under
       reuseExistingServer a pre-existing server on :3000 is still reused
       by design (CI does not reuse). */
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});
