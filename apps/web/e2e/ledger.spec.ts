import { test, expect } from "@playwright/test";

/**
 * LEDGERSG GENERAL LEDGER TESTS (P6/C-5)
 *
 * Authenticated coverage of the real ledger page. Requires a live backend
 * on E2E_API_URL (npm run test:e2e:full); green by default otherwise —
 * these specs skip with a reason.
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

test.describe("General ledger page (P6/C-5 — real data)", () => {
  test("renders real journal lines or a truthful empty state (never mocks)", async ({ page }) => {
    await loginViaUi(page);

    await page.getByRole("link", { name: /^Ledger$/ }).click();
    await expect(page).toHaveURL(/\/ledger\/?$/);

    await expect(page.getByRole("heading", { name: /general ledger/i })).toBeVisible();

    // The page must settle into one of its two truthful states: line rows
    // from the backend ledger endpoint, or the empty state. The mock
    // fixture is gone — "Office supplies purchase" only existed pre-P6.
    const emptyState = page.getByText(/no journal entries yet/i);
    const tableHeader = page.getByRole("columnheader", { name: /entry #/i });

    await expect
      .poll(async () => (await emptyState.isVisible()) || (await tableHeader.isVisible()), {
        timeout: 30000,
      })
      .toBeTruthy();

    await expect(page.getByText("Office supplies purchase")).toHaveCount(0);
  });
});

test.describe("General ledger pagination (P24/FE-M2 — the server-side pages)", () => {
  test("the pagination controls page the ledger live — Next advances, Previous returns (P24/FE-P1)", async ({ page }) => {
    await loginViaUi(page);

    await page.getByRole("link", { name: /^Ledger$/ }).click();
    await expect(page).toHaveURL(/\/ledger\/?$/);

    // The demo substrate posts 36+ journal lines (the §9 bootstrap),
    // so page 1 at page size 20 is a full page with a live Next.
    const pagination = page.getByRole("navigation", { name: "Pagination" });
    await expect(pagination).toBeVisible({ timeout: 30000 });

    const summary = page.getByText(/Showing 1–20 of \d+ rows/);
    await expect(summary).toBeVisible();
    const next = page.getByRole("button", { name: /next page/i });
    const previous = page.getByRole("button", { name: /previous page/i });
    await expect(previous).toBeDisabled();
    await expect(next).toBeEnabled();

    // Page 1's first row (the newest entry by the endpoint's order).
    const firstRowEntryBefore = await page
      .getByRole("row")
      .nth(1)
      .locator("td")
      .first()
      .innerText();

    await next.click();

    // Page 2: the summary advances past row 20 and the row set changes.
    await expect(page.getByText(/Showing 21–\d+ of \d+ rows/)).toBeVisible({
      timeout: 30000,
    });
    await expect(previous).toBeEnabled();
    const firstRowEntryPage2 = await page
      .getByRole("row")
      .nth(1)
      .locator("td")
      .first()
      .innerText();
    expect(firstRowEntryPage2).not.toBe(firstRowEntryBefore);

    await previous.click();
    await expect(page.getByText(/Showing 1–20 of \d+ rows/)).toBeVisible({
      timeout: 30000,
    });
    await expect(previous).toBeDisabled();
  });
});
