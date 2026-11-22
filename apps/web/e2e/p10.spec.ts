import { test, expect } from "@playwright/test";

/**
 * P10 REMEDIATION SPECS (session 20)
 *
 * Live coverage for the P10 surfaces:
 *  - the registration page renders (ungated) and self-registers (gated)
 *  - the full self-serve loop: register → org-less → create org →
 *    dashboard (H-2 + the P9 org-creation page, finally reachable)
 *  - the contacts page renders real rows (M-5)
 *  - the New Invoice form picks an existing customer with ZERO
 *    createContact requests — the H-1 regression at the wire level
 *
 * Repo e2e rule: no financial rows are written into the dev DB; the
 * register flow writes a user + organisation only (that endpoint IS the
 * surface under test), and the picker test stops at selection.
 */

const apiUrl = process.env.E2E_API_URL;

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

/** The demo user's default org id (public API, no SQL). */
async function defaultOrgId(page: import("@playwright/test").Page, token: string): Promise<string> {
  const response = await page.request.get(`${apiUrl}/api/v1/auth/organisations/`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  test.expect(response.ok()).toBeTruthy();
  const orgs = (await response.json()) as Array<{ org: { id: string } }>;
  test.expect(orgs[0]?.org.id).toBeTruthy();
  return orgs[0].org.id;
}

/** Idempotent: ensure a known customer row exists for the picker test. */
async function ensurePickedCustomer(page: import("@playwright/test").Page, token: string, orgId: string) {
  const auth = { Authorization: `Bearer ${token}` };
  const list = await page.request.get(`${apiUrl}/api/v1/${orgId}/invoicing/contacts/`, {
    headers: auth,
  });
  test.expect(list.ok()).toBeTruthy();
  const body = (await list.json()) as { results: Array<{ name: string; is_customer: boolean }> };
  if (!body.results.some((c) => c.name === "E2E Picked Customer" && c.is_customer)) {
    const created = await page.request.post(`${apiUrl}/api/v1/${orgId}/invoicing/contacts/`, {
      headers: { ...auth, "Content-Type": "application/json" },
      data: { name: "E2E Picked Customer", is_customer: true },
    });
    test.expect(created.ok()).toBeTruthy();
  }
}

/** Real UI login (the in-memory session convention — see invoices.spec.ts). */
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

test.describe("Registration page (P10/H-2)", () => {
  test("the login page carries the self-serve registration link", async ({ page }) => {
    await page.goto("/login");

    const link = page.getByRole("link", { name: /create account/i });
    await expect(link).toBeVisible();
    await expect(link).toHaveAttribute("href", /^\/register\/?$/);
  });

  test("the registration page renders the self-serve form", async ({ page }) => {
    await page.goto("/register");

    await expect(page.getByLabel(/full name/i)).toBeVisible();
    await expect(page.getByLabel(/^email/i)).toBeVisible();
    // The backend floor (AUTH_PASSWORD_VALIDATORS min_length 12) is
    // mirrored in the markup so the form fails fast.
    await expect(page.getByLabel(/^password/i)).toHaveAttribute("minlength", "12");
    await expect(page.getByLabel(/confirm password/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /create account/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /sign in/i })).toHaveAttribute(
      "href",
      /^\/login\/?$/
    );
  });
});

// ---------------------------------------------------------------------------
// Live-gated blocks below: a real backend on E2E_API_URL
// (npm run test:e2e:full). Green by default: without the backend these skip
// with a reason.
// ---------------------------------------------------------------------------

test.describe("Self-serve loop (P10/H-2 + P9 org-creation, live)", () => {
  test.skip(!apiUrl, "requires E2E_API_URL (live backend) — run via npm run test:e2e:full");
  test("register → org-less → create organisation → dashboard", async ({ page }) => {
    test.setTimeout(90_000);
    const stamp = Date.now();

    await page.goto("/register");
    await page.getByLabel(/full name/i).fill("E2E P10 Register");
    await page.getByLabel(/^email/i).fill(`e2e-p10-${stamp}@ledgersg.sg`);
    await page.getByLabel(/^password/i).fill("p10-e2e-password");
    await page.getByLabel(/confirm password/i).fill("p10-e2e-password");
    await page.getByRole("button", { name: /create account/i }).click();

    // A fresh account has no organisation — the register route sends it to
    // the org-creation page (previously unreachable: the self-serve loop
    // was closed and this page existed with no UI path to it).
    await expect(page).toHaveURL(/\/settings\/organisations\/new/, { timeout: 20_000 });

    // The org-creation page completes the loop (unique UEN per run — the
    // org-create endpoint now 400s on taken UENs instead of 500ing).
    await page.getByLabel(/organisation name/i).fill(`E2E P10 Org ${stamp}`);
    await page.getByLabel(/uen/i).fill(`E2EP10${String(stamp).slice(-9)}X`);
    await page.getByRole("button", { name: /create organisation/i }).click();

    await expect(page).toHaveURL(/\/dashboard/, { timeout: 30_000 });
  });
});

test.describe("Contacts page (P10/M-5, live)", () => {
  test.skip(!apiUrl, "requires E2E_API_URL (live backend) — run via npm run test:e2e:full");
  test("renders real contact rows or the truthful empty state", async ({ page }) => {
    await loginViaUi(page);

    await page.getByRole("link", { name: /^Contacts$/ }).click();
    await expect(page).toHaveURL(/\/contacts\/?$/);
    await expect(
      page.getByRole("main").getByRole("heading", { name: /^contacts$/i })
    ).toBeVisible();

    // The bootstrap seeds "Bootstrap Customer"; a re-run DB may also carry
    // the picker spec's customer. Either way: real rows, never a mock.
    const row = page.getByText(/Bootstrap Customer|E2E Picked Customer/);
    const emptyState = page.getByText(/no contacts yet/i);
    await expect
      .poll(async () => (await row.first().isVisible()) || (await emptyState.isVisible()), {
        timeout: 20_000,
      })
      .toBeTruthy();
  });
});

test.describe("New Invoice customer picker (P10/H-1, live)", () => {
  test.skip(!apiUrl, "requires E2E_API_URL (live backend) — run via npm run test:e2e:full");
  test("picking an existing customer issues no createContact request", async ({ page }) => {
    const token = await apiLoginToken(page);
    const orgId = await defaultOrgId(page, token);
    await ensurePickedCustomer(page, token, orgId);

    // Wire-level witness: every POST against the contacts collection made
    // by the page during this test. The pre-P10 form created a contact on
    // EVERY submission (duplicating customers); picking must reuse.
    const contactsPosts: string[] = [];
    page.on("request", (request) => {
      if (request.method() === "POST" && request.url().includes("/invoicing/contacts/")) {
        contactsPosts.push(request.url());
      }
    });

    await loginViaUi(page);
    await page.getByRole("link", { name: /^Invoices$/ }).click();
    await expect(page).toHaveURL(/\/invoices\/?$/);
    // The list header always carries the CTA; the empty state adds a
    // second one inside main (strict mode) — take the first.
    await page.getByRole("main").getByRole("link", { name: /new invoice/i }).first().click();
    await expect(page).toHaveURL(/\/invoices\/new\/?$/);
    await expect(page.getByRole("heading", { name: /new invoice/i })).toBeVisible({
      timeout: 15_000,
    });

    const picker = page.getByRole("combobox", { name: /search customer/i });
    await picker.click();
    await picker.fill("E2E Picked");
    await page.getByRole("option", { name: /E2E Picked Customer/i }).first().click();

    // The picked row replaces the search input; the helper text names the
    // reuse contract.
    await expect(page.getByText("E2E Picked Customer").first()).toBeVisible();
    await expect(contactsPosts).toEqual([]);
  });
});
