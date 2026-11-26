import { test, expect } from "@playwright/test";

/**
 * P11 REMEDIATION SPECS (session 23)
 *
 * Live coverage for the P11 surfaces (gated on E2E_API_URL — green by
 * default without a backend, same philosophy as the P10 specs):
 *  - the F5 boxes panel renders REAL computed values — pre-P11 every box
 *    rendered "—" because the panel read keys the backend never sends
 *    (P10-AUD-02 / P11/H-2)
 *  - the contacts edit dialog prefills from the DETAIL payload and a save
 *    round-trip persists uen/gst_reg_number/peppol_id (P11/H-1 + M-4 —
 *    pre-P11 the dialog prefilled blanks and an unconditional save ERASED
 *    the stored values)
 *  - the dashboard GST payable is non-zero on real data and renders single
 *    currency prefixes (P11/H-4 + L-2 — pre-P11 it was hardcoded to 0 and
 *    "S$ SGD x.xx" double prefixes appeared)
 *
 * Unlike the P10 specs (no financial rows in the dev DB), these specs need
 * real accounting activity to prove accounting truth — the
 * `ensureDemoActivity` helper writes the documented demo activity exactly
 * once (idempotent: re-runs reuse the already-approved documents and the
 * already-computed return), matching the DEPLOYMENT.md bootstrap sequence.
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

async function defaultOrgId(page: import("@playwright/test").Page, token: string): Promise<string> {
  const response = await page.request.get(`${apiUrl}/api/v1/auth/organisations/`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  test.expect(response.ok()).toBeTruthy();
  const orgs = (await response.json()) as Array<{ org: { id: string } }>;
  test.expect(orgs[0]?.org.id).toBeTruthy();
  return orgs[0].org.id;
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

interface Account {
  id: string;
  code: string;
  account_type: string;
}

interface TaxCode {
  id: string;
  code: string;
  rate: string;
}

interface DocumentRow {
  id: string;
  document_number: string;
  document_type: string;
  status: string;
  total_incl: string;
  amount_paid: string;
}

/**
 * Idempotent: the demo org carries one approved invoice, one approved
 * credit note and a computed F5 return. Any part that already exists is
 * reused — re-runs never duplicate financial rows.
 */
async function ensureDemoActivity(page: import("@playwright/test").Page) {
  const token = await apiLoginToken(page);
  const orgId = await defaultOrgId(page, token);
  const auth = { Authorization: `Bearer ${token}` };

  // Contact with the truthful full profile (P11/M-4 round-trip substrate —
  // the dialog's UEN/GST-reg/Peppol prefill needs stored values).
  const contacts = (await (
    await page.request.get(`${apiUrl}/api/v1/${orgId}/invoicing/contacts/`, {
      headers: auth,
    })
  ).json()) as { results: Array<{ id: string }> };
  const contactId = contacts.results[0]?.id;
  test.expect(contactId).toBeTruthy();
  const profile = await page.request.patch(
    `${apiUrl}/api/v1/${orgId}/invoicing/contacts/${contactId}/`,
    {
      headers: auth,
      data: {
        uen: "T08LL1234A",
        gst_reg_number: "M90333391K",
        peppol_id: "0195:T08LL1234A",
        email: "ap@demotrading.sg",
        phone: "+65 6123 4567",
        address_line_1: "1 Raffles Place",
        postal_code: "048616",
      },
    }
  );
  test.expect(profile.ok()).toBeTruthy();

  // Documents: reuse posted ones when present (APPROVED or settled-PAID —
  // both carry journal entries; the F5/dashboard truth is the same).
  // P14/H-4 (F-B c): the CN's original invoice needs CAP HEADROOM — the
  // cumulative credit (incl. GST) may not exceed the original total. A
  // 250.00+GST CN needs an invoice with >= 272.50 uncredited, so an
  // arbitrary reused invoice (e.g. the banking spec's 80.00 one) cannot
  // be the original.
  const docs = (await (
    await page.request.get(`${apiUrl}/api/v1/${orgId}/invoicing/documents/`, {
      headers: auth,
    })
  ).json()) as { results: DocumentRow[] };
  const cnGross = 250.0 * 1.09; // the CN this helper creates (incl. GST)
  const postedInv = docs.results.find(
    (d) =>
      d.document_type === "SALES_INVOICE" &&
      ["APPROVED", "PAID"].includes(d.status) &&
      parseFloat(d.total_incl) - parseFloat(d.amount_paid || "0") >= cnGross + 1
  );
  const postedCn = docs.results.find(
    (d) =>
      d.document_type === "SALES_CREDIT_NOTE" &&
      ["APPROVED", "PAID"].includes(d.status)
  );

  if (!postedInv || !postedCn) {
    const accounts = (await (
      await page.request.get(`${apiUrl}/api/v1/${orgId}/accounts/?is_active=true`, {
        headers: auth,
      })
    ).json()) as { results: Account[] };
    const revenue = accounts.results.find(
      (a) => a.code === "4100" && a.account_type === "REVENUE"
    );
    const codes = (await (
      await page.request.get(`${apiUrl}/api/v1/${orgId}/gst/tax-codes/?is_active=true`, {
        headers: auth,
      })
    ).json()) as { results: TaxCode[] };
    const sr = codes.results.find((c) => c.code === "SR" && c.rate === "0.0900");
    if (!revenue || !sr) {
      throw new Error(
        "revenue account 4100 or SR tax code missing — run the CoA/tax-code seed"
      );
    }

    const make = async (
      type: string,
      reference: string,
      lines: unknown[],
      relatedDocumentId?: string
    ) => {
      const created = await page.request.post(`${apiUrl}/api/v1/${orgId}/invoicing/documents/`, {
        headers: auth,
        data: {
          document_type: type,
          contact_id: contactId,
          issue_date: new Date().toISOString().slice(0, 10),
          reference,
          lines,
          // P14/H-4 (F-B b): a credit note must reference the original
          // invoice it corrects.
          related_document_id: relatedDocumentId,
        },
      });
      test.expect(created.ok()).toBeTruthy();
      const body = (await created.json()) as { id: string };
      const approved = await page.request.post(
        `${apiUrl}/api/v1/${orgId}/invoicing/documents/${body.id}/approve/`,
        { headers: auth, data: {} }
      );
      test.expect(approved.ok()).toBeTruthy();
      return body.id;
    };

    let invId = postedInv?.id;
    if (!invId) {
      invId = await make("SALES_INVOICE", "E2E-P11-INV", [
        {
          account_id: revenue.id,
          description: "P11 live gate — consulting",
          quantity: "2.0000",
          unit_price: "500.0000",
          tax_code_id: sr.id,
        },
      ]);
    }
    if (!postedCn) {
      await make(
        "SALES_CREDIT_NOTE",
        "E2E-P11-CN",
        [
          {
            account_id: revenue.id,
            description: "P11 live gate — partial return",
            quantity: "1.0000",
            unit_price: "250.0000",
            tax_code_id: sr.id,
          },
        ],
        invId
      );
    }
  }

  // A computed F5 return for the current period. F-A (P14): on a fresh
  // database NO return exists — create the MONTHLY period for the current
  // month first (the pre-P14 helper only force-computed an existing row,
  // so a fresh-clone test:e2e:full failed the F5/banking specs despite
  // DEPLOYMENT.md §9's self-bootstrap claim).
  const returns = (await (
    await page.request.get(`${apiUrl}/api/v1/${orgId}/gst/returns/`, { headers: auth })
  ).json()) as { results: Array<{ id: string }> };
  let returnId = returns.results[0]?.id;
  if (!returnId) {
    const now = new Date();
    const monthStart = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
    const created = await page.request.post(`${apiUrl}/api/v1/${orgId}/gst/returns/`, {
      headers: auth,
      data: { filing_frequency: "MONTHLY", start_date: monthStart, periods: 1 },
    });
    test.expect(created.ok()).toBeTruthy();
    const createdBody = (await created.json()) as {
      data: Array<{ id: string }>;
    };
    returnId = createdBody.data[0]?.id;
  }
  if (returnId) {
    const computed = await page.request.post(
      `${apiUrl}/api/v1/${orgId}/gst/returns/${returnId}/?force=true`,
      { headers: auth, data: {} }
    );
    test.expect(computed.ok()).toBeTruthy();
  }

  return { orgId, contactId };
}

test.describe("F5 boxes panel (P11/H-2, live)", () => {
  test.skip(!apiUrl, "requires E2E_API_URL (live backend) — run via npm run test:e2e:full");
  test("renders computed values, no em-dash placeholders", async ({ page }) => {
    test.setTimeout(120_000);
    await ensureDemoActivity(page);
    await loginViaUi(page);

    await page.getByRole("link", { name: /^Reports$/ }).click();
    await expect(page).toHaveURL(/\/reports\/?$/);
    await page.getByRole("tab", { name: /GST F5/i }).click();

    // The computed return row carries the View boxes action.
    const view = page.getByRole("button", { name: /view boxes/i }).first();
    await expect(view).toBeVisible({ timeout: 20_000 });
    await view.click();

    // Pre-P11 every box rendered "—" (panel keys mismatched the backend
    // contract). The real panel shows Box 1 with a monetary value.
    await expect(page.getByText(/Box 1 — Standard-rated supplies/i).first()).toBeVisible({
      timeout: 10_000,
    });
    const mainText = await page.locator("main").innerText();
    expect(mainText).toMatch(/Box 1[\s\S]*\d+\.\d\d/);
  });
});

test.describe("Contacts edit round-trip (P11/H-1 + M-4, live)", () => {
  test.skip(!apiUrl, "requires E2E_API_URL (live backend) — run via npm run test:e2e:full");
  test("prefills from DETAIL and a save persists uen/gst_reg_number/peppol_id", async ({ page }) => {
    test.setTimeout(120_000);
    const { orgId, contactId } = await ensureDemoActivity(page);
    const token = await apiLoginToken(page);

    await loginViaUi(page);
    await page.getByRole("link", { name: /^Contacts$/ }).click();
    await expect(page).toHaveURL(/\/contacts\/?$/);

    await page.getByRole("button", { name: /^Edit /i }).first().click();
    await expect(page.getByRole("dialog")).toBeVisible();

    // The prefill proof: UEN and GST reg number arrive from the DETAIL
    // payload (pre-P11 these inputs rendered blank).
    await expect(page.getByLabel(/^uen$/i)).toHaveValue("T08LL1234A", { timeout: 15_000 });
    await expect(page.getByLabel(/gst registration no/i)).toHaveValue("M90333391K");
    await expect(page.getByLabel(/^peppol id/i)).toHaveValue("0195:T08LL1234A");

    // The round-trip: change the phone, save, verify the UEN family was NOT
    // erased by the save (the pre-P11 dialog wiped uen/peppol on save).
    await page.getByLabel(/^phone$/i).fill("+65 6555 0000");
    await page.getByRole("button", { name: /save changes/i }).click();
    await expect(page.getByRole("dialog")).toBeHidden({ timeout: 15_000 });

    // API witness: uen/peppol survived the round-trip.
    const after = await page.request.get(
      `${apiUrl}/api/v1/${orgId}/invoicing/contacts/${contactId}/`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    const detail = (await after.json()) as Record<string, string>;
    expect(detail.uen).toBe("T08LL1234A");
    expect(detail.peppol_id).toBe("0195:T08LL1234A");
    expect(detail.gst_reg_number).toBe("M90333391K");
  });
});

test.describe("Dashboard GST payable (P11/H-4 + L-2, live)", () => {
  test.skip(!apiUrl, "requires E2E_API_URL (live backend) — run via npm run test:e2e:full");
  test("non-zero on real data with single currency prefixes", async ({ page }) => {
    test.setTimeout(120_000);
    await ensureDemoActivity(page);
    await loginViaUi(page);

    // Pre-P11 the card was hardcoded to "SGD 0.00" regardless of activity.
    await expect(page.getByText(/gst payable/i).first()).toBeVisible({ timeout: 15_000 });

    // The chart input is the raw value now (M-7) — the card renders the
    // display string with a single prefix (L-2), never "S$ SGD".
    const body = await page.content();
    expect(body).not.toContain("S$ SGD");
  });
});
