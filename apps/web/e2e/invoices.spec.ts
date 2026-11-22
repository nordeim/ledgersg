import { test, expect } from "@playwright/test";

/**
 * LEDGERSG INVOICE FORM TESTS (P3/D-5 + D-1/D-3 evidence)
 *
 * Authenticated coverage of the New Invoice form. Sessions are in-memory
 * (access token in the api-client module; the backend returns tokens in
 * the body and sets no cookie), so the spec drives the REAL user path:
 * UI login → dashboard → sidebar (client-side <Link>) → invoices → new.
 * A full page reload would drop the session — every navigation here is
 * client-side, exactly how a real user moves.
 *
 * Setup ensures the org has a revenue account (created through the public
 * API; the dev DB ships without a chart of accounts).
 *
 * Opt-in: requires E2E_API_URL (live backend + Redis). Green by default:
 * without the backend these tests skip with a reason. NO submission is
 * performed — playwright must not write financial rows into the dev DB.
 */

const apiUrl = process.env.E2E_API_URL;

test.skip(!apiUrl, "requires E2E_API_URL (live backend) — run via npm run test:e2e:full");

interface LoginResponse {
  tokens: { access: string; refresh: string };
}

async function apiLoginToken(page: import("@playwright/test").Page): Promise<string> {
  const response = await page.request.post(`${apiUrl}/api/v1/auth/login/`, {
    data: {
      email: process.env.E2E_DEMO_EMAIL ?? "demo@ledgersg.sg",
      password: process.env.E2E_DEMO_PASSWORD ?? "demo1234",
    },
  });
  test.expect(response.ok()).toBeTruthy();
  const body = (await response.json()) as LoginResponse;
  return body.tokens.access;
}

/** Ensure the default org has a revenue account (public API, no SQL). */
async function ensureRevenueAccount(page: import("@playwright/test").Page, token: string) {
  const auth = { Authorization: `Bearer ${token}` };

  const orgsResponse = await page.request.get(`${apiUrl}/api/v1/auth/organisations/`, {
    headers: auth,
  });
  test.expect(orgsResponse.ok()).toBeTruthy();
  const orgs = (await orgsResponse.json()) as Array<{ org: { id: string } }>;
  const orgId = orgs[0]?.org.id;
  test.expect(orgId).toBeTruthy();

  const list = await page.request.get(
    `${apiUrl}/api/v1/${orgId}/accounts/?account_type=REVENUE`,
    { headers: auth }
  );
  test.expect(list.ok()).toBeTruthy();
  const listBody = (await list.json()) as { results: Array<{ id: string }> };

  if (listBody.results.length === 0) {
    const created = await page.request.post(`${apiUrl}/api/v1/${orgId}/accounts/`, {
      headers: auth,
      data: {
        code: "4900",
        name: "Test Revenue",
        account_type: "REVENUE",
        is_active: true,
      },
    });
    test.expect(created.ok()).toBeTruthy();
  }
}

/**
 * Real UI login + client-side navigation to /invoices/new (the session is
 * memory-only — a page.goto would drop it).
 */
async function openNewInvoiceForm(page: import("@playwright/test").Page) {
  const token = await apiLoginToken(page);
  await ensureRevenueAccount(page, token);

  await page.goto("/login");
  await page.locator("input[type='email']").fill(
    process.env.E2E_DEMO_EMAIL ?? "demo@ledgersg.sg"
  );
  await page.locator("input[type='password']").fill(
    process.env.E2E_DEMO_PASSWORD ?? "demo1234"
  );
  await page.getByRole("button", { name: /sign in/i }).click();

  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20000 });

  // Client-side navigations only (in-memory session). The New Invoice
  // link is scoped to the main region — the shell header also carries one
  // since P7/F-17 (strict mode resolves both otherwise).
  await page.getByRole("link", { name: /^Invoices$/ }).click();
  await expect(page).toHaveURL(/\/invoices\/?$/);
  // The list header always carries the CTA; the empty state adds a second
  // one inside main (strict mode) — take the first.
  await page
    .getByRole("main")
    .getByRole("link", { name: /new invoice/i })
    .first()
    .click();
  await expect(page).toHaveURL(/\/invoices\/new\/?$/);

  await expect(page.getByRole("heading", { name: /new invoice/i })).toBeVisible({
    timeout: 15000,
  });
}

test.describe("Invoices list page (P5/C-5 — real data)", () => {
  test("renders real backend rows or a truthful empty state (never mocks)", async ({ page }) => {
    const token = await apiLoginToken(page);
    await ensureRevenueAccount(page, token);

    await page.goto("/login");
    await page.locator("input[type='email']").fill(
      process.env.E2E_DEMO_EMAIL ?? "demo@ledgersg.sg"
    );
    await page.locator("input[type='password']").fill(
      process.env.E2E_DEMO_PASSWORD ?? "demo1234"
    );
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page).toHaveURL(/\/dashboard/, { timeout: 20000 });

    // Client-side navigation (the P4 cookie flow keeps the session alive)
    await page.getByRole("link", { name: /^Invoices$/ }).click();
    await expect(page).toHaveURL(/\/invoices\/?$/);

    // The page must settle into one of its two truthful states: rows from
    // the backend list endpoint, or the empty state. The mock fixture is
    // gone — ABC Pte Ltd was a hardcoded row that only existed pre-P5.
    const emptyState = page.getByText(/no invoices yet/i);
    const tableHeader = page.getByRole("columnheader", { name: /invoice/i });

    await expect
      .poll(async () => (await emptyState.isVisible()) || (await tableHeader.isVisible()), {
        timeout: 30000,
      })
      .toBeTruthy();

    await expect(page.getByText("Singapore Tech Solutions")).toHaveCount(0);
  });
});

test.describe("New Invoice form (authenticated)", () => {
  test("renders the form with account and effective tax-code selects", async ({ page }) => {
    await openNewInvoiceForm(page);

    // Per-line posting account select exists (backend add_line contract)
    await expect(page.getByRole("combobox", { name: "Account" }).first()).toBeVisible({
      timeout: 30000,
    });

    // Tax-code select shows server-resolved rows with the effective rate
    // (SR is 9% today on the seeded rate history)
    const taxSelect = page.getByRole("combobox", { name: "Tax code" }).first();
    await expect(taxSelect).toBeVisible();
    await taxSelect.click();
    await expect(page.getByRole("option", { name: /SR/ }).first()).toBeVisible();
    await expect(
      page.getByRole("option", { name: /SR · 9%/ }).first()
    ).toBeVisible();
  });

  test("computes the line preview live as the user types", async ({ page }) => {
    await openNewInvoiceForm(page);

    await page.getByLabel("Line description").first().fill("E2E preview check");
    await page.getByLabel("Quantity").first().fill("2");
    await page.getByLabel("Unit price").first().fill("100");

    // 2 x 100 at SR 9% => 218.00 (server-resolved rate drives the preview)
    await expect(page.getByLabel("Line total").first()).toHaveText("218.00", {
      // generous: first compile of the form page under a cold dev server
      timeout: 30000,
    });
  });

  test("populates the account select from the organisation's accounts", async ({ page }) => {
    await openNewInvoiceForm(page);

    const accountSelect = page.getByRole("combobox", { name: "Account" }).first();
    await accountSelect.click();

    // At least one account option from the org's chart of accounts
    const options = page.getByRole("option");
    await expect(options.first()).toBeVisible({ timeout: 30000 });
    const count = await options.count();
    test.expect(count).toBeGreaterThanOrEqual(1);
  });
});

test.describe("Invoice detail page (P6/C-5 — real data)", () => {
  test("renders the real document with its payment state (never mocks)", async ({ page }) => {
    const token = await apiLoginToken(page);
    const auth = { Authorization: `Bearer ${token}` };

    // List the org's documents through the public API, take the first.
    const orgsResponse = await page.request.get(`${apiUrl}/api/v1/auth/organisations/`, {
      headers: auth,
    });
    test.expect(orgsResponse.ok()).toBeTruthy();
    const orgs = (await orgsResponse.json()) as Array<{ org: { id: string } }>;
    const orgId = orgs[0]?.org.id;
    test.expect(orgId).toBeTruthy();

    const listResponse = await page.request.get(
      `${apiUrl}/api/v1/${orgId}/invoicing/documents/?type=SALES_INVOICE`,
      { headers: auth }
    );
    test.expect(listResponse.ok()).toBeTruthy();
    const listBody = (await listResponse.json()) as {
      results: Array<{ id: string; document_number: string }>;
    };

    await page.goto("/login");
    await page.locator("input[type='email']").fill(
      process.env.E2E_DEMO_EMAIL ?? "demo@ledgersg.sg"
    );
    await page.locator("input[type='password']").fill(
      process.env.E2E_DEMO_PASSWORD ?? "demo1234"
    );
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page).toHaveURL(/\/dashboard/, { timeout: 20000 });

    await page.getByRole("link", { name: /^Invoices$/ }).click();
    await expect(page).toHaveURL(/\/invoices\/?$/);

    if (listBody.results.length === 0) {
      // Truthful empty state — the org has no documents.
      await expect(page.getByText(/no invoices yet/i)).toBeVisible({ timeout: 30000 });
      return;
    }

    const first = listBody.results[0];
    await page.locator("table tbody tr a").first().click();
    await expect(page).toHaveURL(new RegExp(`/invoices/${first.id}`), {
      timeout: 30000,
    });

    // The real document number, and the payment state (P6/F-11) — the
    // mock fixture's INV-2024-0001 demo IDs are gone.
    await expect(page.getByText(first.document_number).first()).toBeVisible({
      timeout: 30000,
    });
    await expect(page.getByText(/amount due/i).first()).toBeVisible();
    await expect(page.getByText("INV-2024-0001")).toHaveCount(0);
  });
});

test.describe("Invoice detail — void flow (P7/F-1)", () => {
  test("the Void button opens a required-reason dialog and blocks empty submission", async ({ page }) => {
    const token = await apiLoginToken(page);
    const auth = { Authorization: `Bearer ${token}` };

    const orgsResponse = await page.request.get(`${apiUrl}/api/v1/auth/organisations/`, {
      headers: auth,
    });
    test.expect(orgsResponse.ok()).toBeTruthy();
    const orgs = (await orgsResponse.json()) as Array<{ org: { id: string } }>;
    const orgId = orgs[0]?.org.id;
    test.expect(orgId).toBeTruthy();

    const listResponse = await page.request.get(
      `${apiUrl}/api/v1/${orgId}/invoicing/documents/?type=SALES_INVOICE`,
      { headers: auth }
    );
    const listBody = (await listResponse.json()) as {
      results: Array<{ id: string; status: string; document_number: string }>;
    };
    test.skip(!listBody.results?.length, "org has no documents to void against");

    // P9: the banking workflow spec settles the approved invoice first
    // (alphabetical file order) — a PAID invoice has no Void button
    // (P8/G-3: credit note is the remedy), so target a VOIDABLE status.
    const VOIDABLE = ["DRAFT", "SENT", "APPROVED", "OVERDUE", "PARTIALLY_PAID"];
    const target = listBody.results.find((d) => VOIDABLE.includes(d.status));
    test.skip(!target, "no voidable documents exist");
    const voidable = target!;

    await page.goto("/login");
    await page.locator("input[type='email']").fill(
      process.env.E2E_DEMO_EMAIL ?? "demo@ledgersg.sg"
    );
    await page.locator("input[type='password']").fill(
      process.env.E2E_DEMO_PASSWORD ?? "demo1234"
    );
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 20000 });

    // Client-side navigation to the detail page
    await page.getByRole("link", { name: /^Invoices$/ }).click();
    await expect(page).toHaveURL(/\/invoices\/?$/);
    // Click the TARGET's row (the first row may be the settled PAID
    // invoice from the banking workflow spec).
    await page
      .locator("tr", { hasText: voidable.document_number })
      .getByRole("link")
      .first()
      .click();
    await expect(page).toHaveURL(/\/invoices\//, { timeout: 30000 });

    // Void opens the dialog (never a bare mutation — P7/F-1)
    await page.getByRole("button", { name: /^void$/i }).click();
    const reasonField = page.getByLabel(/reason for voiding/i);
    await expect(reasonField).toBeVisible({ timeout: 15000 });

    // The confirm button is disabled without a reason
    const confirm = page.getByRole("button", { name: /void invoice/i });
    await expect(confirm).toBeDisabled();

    // Typing a reason enables it; Cancel closes without any API call
    await reasonField.fill("e2e: dialog check");
    await expect(confirm).toBeEnabled();
    await page.getByRole("button", { name: /cancel/i }).click();
    await expect(reasonField).toHaveCount(0);
  });
});
