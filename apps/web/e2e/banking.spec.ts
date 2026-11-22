import { test, expect } from "@playwright/test";

/**
 * LEDGERSG BANKING TESTS (P9/B-1..B-6)
 *
 * The complete payment workflow through the real UI: create a bank
 * account (the B-4 dialog), settle an invoice (Record Payment deep link +
 * contact picker + allocation, B-3/B-3b), import a statement (real
 * multipart, B-1), see the match suggestion render (B-2), and reconcile
 * (B-6's surface). Requires E2E_API_URL (npm run test:e2e:full); skips
 * green with a reason otherwise.
 */

const apiUrl = process.env.E2E_API_URL;

test.skip(
  !apiUrl,
  "requires E2E_API_URL (live backend) — run via npm run test:e2e:full"
);

// The three tests are a WORKFLOW CHAIN sharing live data (test 2 needs
// test 1's bank account; test 3 needs test 2's payment) — the config's
// fullyParallel would race them against each other.
test.describe.configure({ mode: "serial" });

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

test("bank account dialog creates a real account (P9/B-4)", async ({ page }) => {
  await loginViaUi(page);

  await page.getByRole("link", { name: /^Banking$/ }).click();
  await expect(page).toHaveURL(/\/banking\/?$/, { timeout: 20000 });

  // The dead buttons are live: the dialog opens from either branch
  // (empty state or populated header).
  await page
    .getByRole("button", { name: /add bank account|add account/i })
    .first()
    .click();

  // Unique per run — the workflow is re-runnable against a live DB (the
  // duplicate account_number would 400 on a second pass).
  const runId = Date.now().toString(36);
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel(/account name/i).fill(`E2E Operating ${runId}`);
  await dialog.getByLabel(/bank name/i).fill("Development Bank");
  await dialog.getByLabel(/account number/i).fill(`8888-${runId}`);
  // GL account: the seeded 1100 bank-type series (filterable since P9/C-4)
  await dialog.getByLabel(/gl account/i).selectOption({ index: 1 });
  await dialog.getByRole("button", { name: /add account/i }).click();

  // The account appears in the list and the dialog closed.
  await expect(page.getByText(`E2E Operating ${runId}`)).toBeVisible({
    timeout: 15000,
  });
  await expect(page.getByRole("dialog")).toBeHidden();
});

test("record payment settles an invoice end to end (P9/B-3, B-3b)", async ({ page }) => {
  await loginViaUi(page);

  // Find an outstanding invoice (the bootstrap-approved one).
  await page.getByRole("link", { name: /^Invoices$/ }).click();
  await expect(page).toHaveURL(/\/invoices\/?$/, { timeout: 20000 });

  const outstandingRow = page
    .locator("tr", { hasText: /Approved|Sent|Overdue|Partially Paid/ })
    .first();
  await outstandingRow.getByRole("link").first().click();
  await expect(page).toHaveURL(/\/invoices\/[a-f0-9-]+/i, { timeout: 20000 });

  // The P9/B-3b action: Record Payment deep-links into Banking prefilled
  // (?receive=1&contact=…&document=…&amount=…).
  await page.getByRole("button", { name: /record payment/i }).click();
  await expect(page).toHaveURL(/\/banking\/?\?receive=1/, { timeout: 20000 });

  await expect(
    page.getByRole("heading", { name: /receive payment/i })
  ).toBeVisible({ timeout: 15000 });

  // The allocation row carries the outstanding amount — read it.
  const allocationInput = page
    .getByRole("spinbutton", { name: /allocation for/i })
    .first();
  await expect(allocationInput).toHaveValue(/\d+/);
  const due = await allocationInput.inputValue();

  // Bank account: the one the previous test created.
  await page.getByRole("combobox", { name: /bank account/i }).click();
  await page.getByRole("option", { name: /e2e operating/i }).first().click();

  await page.getByLabel("Payment amount").fill(due);
  // Scoped to the overlay — the payments tab behind it carries a
  // "Receive Payment" button of its own (strict mode).
  const receiveOverlay = page.locator("div.fixed.inset-0");
  await receiveOverlay
    .getByRole("button", { name: /receive payment/i })
    .click();

  // The form closes; the invoice settles (full allocation → Paid).
  await expect(receiveOverlay).toBeHidden({ timeout: 20000 });

  await page.getByRole("link", { name: /^Invoices$/ }).click();
  const settledRow = page.locator("tr", { hasText: "INV-" }).filter({
    hasText: /Paid|Partially Paid/,
  });
  await expect(settledRow.first()).toBeVisible({ timeout: 20000 });
});

test("statement import sends real multipart and matches reconcile (P9/B-1, B-2, B-6)", async ({
  page,
}) => {
  await loginViaUi(page);

  await page.getByRole("link", { name: /^Banking$/ }).click();

  // Read the payment amount from the Payments tab (the settled payment).
  await page.getByRole("tab", { name: /payments/i }).click();
  const paymentCard = page
    .getByTestId("payment-card")
    .filter({ hasText: "Marina" })
    .first();
  await expect(paymentCard).toBeVisible({ timeout: 15000 });
  const amountText =
    (await paymentCard.getByText("+SGD").first().textContent()) ?? "";
  const amount = amountText.replace(/[^\d.]/g, "");
  expect(amount).toMatch(/\d+/);

  await page.getByRole("tab", { name: /transactions/i }).click();
  await page.getByRole("button", { name: /import statement/i }).click();

  // The import form overlay (scoped — the transaction filters carry a
  // bank-account combobox of their own).
  const overlay = page
    .locator("div.fixed.inset-0")
    .filter({ hasText: "Import Bank Statement" });
  await overlay.getByRole("combobox", { name: /bank account/i }).click();
  await page.getByRole("option", { name: /e2e operating/i }).first().click();

  // Real file upload — the multipart path (pre-P9 the import could never
  // succeed: JSON.stringify(FormData) sent "{}" with a JSON content-type).
  await overlay.locator("#csv-file").setInputFiles({
    name: "statement.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "transaction_date,amount,description,reference\n" +
        `2026-11-15,${amount},Payment received - Marina Consulting,E2E-REF-001\n`,
      "utf8"
    ),
  });
  await overlay.getByRole("button", { name: /^import$/i }).click();

  // The import succeeded — the form closed and the transaction lists.
  await expect(overlay).toBeHidden({ timeout: 20000 });
  const transactionRow = page.getByTestId("transaction-row").filter({
    hasText: "Marina Consulting",
  });
  await expect(transactionRow.first()).toBeVisible({ timeout: 20000 });

  // Reconcile: the match suggestion must RENDER (pre-P9 the envelope
  // mismatch always showed "No matching payments found").
  await transactionRow.first().locator("div.cursor-pointer").click();
  await transactionRow
    .first()
    .getByRole("button", { name: /reconcile/i })
    .click();

  // The payment number is sequence-prefixed (RCP-00001) — the match row
  // is the only overlay button carrying it.
  const matchRow = page
    .locator("div.fixed.inset-0")
    .getByRole("button", { name: /rcp-\d|rec-\d/i })
    .first();
  await expect(matchRow).toBeVisible({ timeout: 15000 });
  await matchRow.click();

  await page
    .locator("div.fixed.inset-0")
    .getByRole("button", { name: /^reconcile$/i })
    .click();

  // The overlay closes and the transaction shows reconciled (the badge
  // AND the "Reconciled: <timestamp>" line both carry the word — .first()
  // is the badge).
  await expect(
    page.locator("div.fixed.inset-0").filter({ hasText: "Suggested Matches" })
  ).toBeHidden({ timeout: 20000 });
  await expect(
    transactionRow.first().getByText("Unreconciled")
  ).toBeHidden({ timeout: 20000 });
  await expect(
    transactionRow.first().getByText("Reconciled").first()
  ).toBeVisible({ timeout: 20000 });
});
