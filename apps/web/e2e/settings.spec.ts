import { test, expect } from "@playwright/test";

/**
 * LEDGERSG SETTINGS TESTS (P6/C-5)
 *
 * Authenticated coverage of the real organisation settings page.
 * Requires a live backend on E2E_API_URL (npm run test:e2e:full);
 * green by default otherwise — these specs skip with a reason.
 */

const apiUrl = process.env.E2E_API_URL;

test.skip(!apiUrl, "requires E2E_API_URL (live backend) — run via npm run test:e2e:full");

async function loginViaUi(page: import("@playwright/test").Page) {
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

test.describe("Settings page (P6/C-5 — real data)", () => {
  test("renders the real organisation details (never the mock defaults)", async ({ page }) => {
    await loginViaUi(page);

    await page.getByRole("link", { name: /^Settings$/ }).click();
    await expect(page).toHaveURL(/\/settings\/?$/);

    // The form must settle on real org data — the mock defaults
    // ("Demo Company Pte Ltd") are gone and the company name is non-empty.
    const nameInput = page.getByLabel("Company Name");
    await expect(nameInput).not.toHaveValue("Demo Company Pte Ltd", {
      timeout: 30000,
    });
    await expect(nameInput).not.toHaveValue("");

    // The GST card reflects the real registration state.
    await expect(
      page.getByText(/registered/i).or(page.getByText(/not registered/i)).first()
    ).toBeVisible({ timeout: 30000 });
  });
});
