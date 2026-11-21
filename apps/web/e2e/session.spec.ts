import { test, expect } from "@playwright/test";

/**
 * LEDGERSG SESSION PERSISTENCE TESTS (P4/E-1)
 *
 * The user-visible acceptance test for cross-reload session persistence:
 * before P4, every full page reload dropped the session (the backend set no
 * refresh cookie, the frontend discarded the refresh token, and the client
 * refresh guard could not fire without an in-memory access token) — the
 * user landed back on /login on every reload/new-tab.
 *
 * Now: login sets the HttpOnly refresh cookie; a reload boots the app with
 * no access token in memory, the first `me` call 401s, the client refreshes
 * through the cookie (credentials:"include"), and the retry succeeds — the
 * session survives exactly like in a traditional server-session app.
 *
 * Opt-in: requires E2E_API_URL (live backend + Redis). Green by default:
 * without the backend these tests skip with a reason. No financial writes.
 */

const apiUrl = process.env.E2E_API_URL;

test.skip(!apiUrl, "requires E2E_API_URL (live backend) — run via npm run test:e2e:full");

async function uiLogin(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.locator("input[type='email']").fill(
    process.env.E2E_DEMO_EMAIL ?? "demo@ledgersg.sg"
  );
  await page.locator("input[type='password']").fill(
    process.env.E2E_DEMO_PASSWORD ?? "demo1234"
  );
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20000 });
}

test.describe("Session persistence (P4/E-1)", () => {
  test("the session survives a full page reload", async ({ page }) => {
    await uiLogin(page);

    // The acceptance event: a FULL reload (fresh JS module memory, no
    // access token) must not drop the session — the HttpOnly refresh
    // cookie carries it across.
    await page.reload();

    await expect(page).toHaveURL(/\/dashboard/, { timeout: 20000 });
    // Authenticated shell, not the login form: the sidebar renders.
    await expect(
      page.getByRole("link", { name: /^Invoices$/ })
    ).toBeVisible({ timeout: 15000 });
  });

  test("the reloaded session can still navigate client-side", async ({ page }) => {
    await uiLogin(page);
    await page.reload();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 20000 });

    // The session is functional, not cosmetic: navigation after the reload
    // works without another login.
    await page.getByRole("link", { name: /^Invoices$/ }).click();
    await expect(page).toHaveURL(/\/invoices\/?$/);
  });

  test("logout ends the session — a later reload lands on /login", async ({ page }) => {
    await uiLogin(page);

    // Logout (blacklists the refresh cookie server-side and expires it).
    await page.getByRole("button", { name: /log\s?out/i }).click();
    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });

    // After logout, a reload must NOT resurrect the session.
    await page.reload();
    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });
  });
});
