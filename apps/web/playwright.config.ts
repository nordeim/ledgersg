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

export default defineConfig({
  testDir: "./e2e",

  /* Run tests in files in parallel */
  fullyParallel: true,

  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* Opt out of parallel tests on CI for stability */
  workers: process.env.CI ? 1 : undefined,

  /* Terminal summary always; HTML report written without opening a browser */
  reporter: [["list"], ["html", { open: "never" }]],

  /* Artifacts from failed runs */
  outputDir: "./test-results",

  /* Shared settings for all the projects below */
  use: {
    /* Base URL to use in actions like `await page.goto('/')` */
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000",

    /* Collect trace when retrying the failed test */
    trace: "on-first-retry",

    /* Screenshot on failure */
    screenshot: "only-on-failure",

    /* Video recording */
    video: "on-first-retry",

    /* Viewport */
    viewport: { width: 1280, height: 720 },

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
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});
