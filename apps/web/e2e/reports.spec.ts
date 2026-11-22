import { test, expect } from "@playwright/test";

/**
 * LEDGERSG REPORTS TESTS (P8/R-7)
 *
 * The reports page renders real statements from the live backend — the
 * pre-P8 page was a static card grid with dead Generate buttons. Requires
 * E2E_API_URL (npm run test:e2e:full); skips green with a reason
 * otherwise.
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

test("reports page renders the real statement tabs (never the dead Generate shell)", async ({
  page,
}) => {
  await loginViaUi(page);

  await page.getByRole("link", { name: /^Reports$/ }).click();
  await expect(page).toHaveURL(/\/reports\/?$/, { timeout: 20000 });

  // The P8 tab set — the pre-P8 shell had none of these
  await expect(page.getByRole("tab", { name: /trial balance/i })).toBeVisible();
  await expect(page.getByRole("tab", { name: /profit & loss/i })).toBeVisible();
  await expect(page.getByRole("tab", { name: /balance sheet/i })).toBeVisible();
  await expect(page.getByRole("tab", { name: /gst f5/i })).toBeVisible();
  await expect(page.getByRole("tab", { name: /aged/i })).toBeVisible();

  // A truthful trial-balance state: either rows (table cells) or the
  // explicit empty state — never the dead "Generate" buttons.
  const body = page.getByRole("main");
  const hasRows = await body
    .locator("table tbody tr")
    .first()
    .isVisible({ timeout: 15000 })
    .catch(() => false);
  if (hasRows) {
    await expect(body.locator("table tbody tr").first()).toBeVisible();
  } else {
    await expect(
      body.getByText(/no journal activity/i)
    ).toBeVisible();
  }
  await expect(
    page.getByRole("button", { name: /^generate$/i })
  ).toHaveCount(0);
});
