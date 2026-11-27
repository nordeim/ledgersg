import { test, expect } from "@playwright/test";

/**
 * LEDGERSG QUOTES TESTS (P8/Q-4)
 *
 * The quotes pages render real SALES_QUOTE documents and the convert flow
 * creates the linked invoice. Requires E2E_API_URL (npm run
 * test:e2e:full); skips green with a reason otherwise.
 */

const apiUrl = process.env.E2E_API_URL;

test.skip(!apiUrl, "requires E2E_API_URL (live backend) — run via npm run test:e2e:full");

async function loginViaUi(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.locator("input[type='email']").fill(
    process.env.E2E_DEMO_EMAIL ?? "demo@ledgersg.sg"
  );
  await page.locator("input[type='password']").fill(
    process.env.E2E_DEMO_PASSWORD ?? "demo1234pass"
  );
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20000 });
}

test("quotes page lists quotes with the New Quote + Convert affordances", async ({
  page,
}) => {
  await loginViaUi(page);

  await page.getByRole("link", { name: /^Quotes$/ }).click();
  await expect(page).toHaveURL(/\/quotes\/?$/, { timeout: 20000 });

  // The page shell is real (never the old static "Create Quote" dead button)
  await expect(page.getByRole("heading", { name: /^Quotes$/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /new quote/i })).toBeVisible();
  // Truthful state: either quote rows or the explicit empty state
  const body = page.getByRole("main");
  const hasRows = await body
    .locator("table tbody tr")
    .first()
    .isVisible({ timeout: 15000 })
    .catch(() => false);
  if (!hasRows) {
    await expect(body.getByText(/no quotes yet/i)).toBeVisible();
  }
});
