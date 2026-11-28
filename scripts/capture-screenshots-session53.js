// Session-53 screenshot capture — the P28 remediated surfaces.
// Mirrors the repo convention: pixel-verified captures with DOM truths
// asserted per surface (docs/screenshots/176-183_*_session53.png).
// P28 headline: the SQL-level push-down — the four service-driven list
// surfaces (contacts, documents[invoices+quotes], payments, bank
// transactions) now fetch ONLY the requested page (SQL LIMIT/OFFSET)
// and count via SQL COUNT(*); the envelope is byte-identical, so the
// captures pin the same pagination summaries the P24-P27 contract
// established, plus the standard mobile-nav regressions.
const {
  chromium,
} = require(
  require("path").join(__dirname, "..", "apps", "web", "node_modules", "@playwright", "test")
);
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const BASE = "http://localhost:3000";
const API = process.env.E2E_API_URL || "http://127.0.0.1:8000";
const OUT = path.join(__dirname, "..", "docs", "screenshots");

/** Count-driven, idempotent quote top-up (the P26/FE-P1 convention):
 * the capture needs >= 1 QUOTE on the demo org for the pagination to
 * render; the fodder is DRAFT (no journal impact). */
async function ensureQuoteFodder(page) {
  const login = await page.request.post(`${API}/api/v1/auth/login/`, {
    data: { email: "demo@ledgersg.sg", password: "demo1234pass" },
  });
  const token = (await login.json()).tokens.access;
  const auth = { Authorization: `Bearer ${token}` };
  const orgs = await (
    await page.request.get(`${API}/api/v1/auth/organisations/`, { headers: auth })
  ).json();
  const orgId = orgs.results[0].org.id;
  const list = await (
    await page.request.get(
      `${API}/api/v1/${orgId}/invoicing/documents/?type=SALES_QUOTE`,
      { headers: auth }
    )
  ).json();
  if ((list.count ?? 0) > 0) return;
  const contacts = await (
    await page.request.get(`${API}/api/v1/${orgId}/invoicing/contacts/`, {
      headers: auth,
    })
  ).json();
  const accounts = await (
    await page.request.get(`${API}/api/v1/${orgId}/accounts/?account_type=REVENUE`, {
      headers: auth,
    })
  ).json();
  const taxCodes = await (
    await page.request.get(`${API}/api/v1/${orgId}/gst/tax-codes/?is_active=true`, {
      headers: auth,
    })
  ).json();
  const sr = taxCodes.results.find((t) => t.code === "SR");
  const issueDate = new Date().toISOString().slice(0, 10);
  const created = await page.request.post(
    `${API}/api/v1/${orgId}/invoicing/documents/`,
    {
      headers: { ...auth, "Content-Type": "application/json" },
      data: {
        document_type: "SALES_QUOTE",
        contact_id: contacts.results[0].id,
        issue_date: issueDate,
        due_date: issueDate,
        currency: "SGD",
        reference: "CAPTURE-QUOTE-FODDER",
        lines: [
          {
            account_id: accounts.results[0].id,
            description: "capture pagination fodder",
            quantity: 1,
            unit_price: "10.00",
            tax_code_id: sr.id,
          },
        ],
      },
    }
  );
  if (!created.ok()) throw new Error(`quote fodder POST failed: ${created.status()}`);
}

const SHOTS = [
  // 176 — the invoices list page 1: served by the SQL-bounded documents
  // query (LIMIT 20), Previous disabled on the boundary.
  {
    name: "176_invoices_page1_pushdown_session53",
    url: "/invoices/",
    viewport: [1280, 800],
    truths: [
      ["nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–20 of \d+ rows/],
      ["table", null, null],
      ["nav[aria-label='Pagination'] button:first-of-type", "aria-label", "Previous page"],
    ],
    prevDisabled: true,
  },
  // 177 — page 2 of the same surface: the offset page — the query that
  // used to fetch the FULL table and Python-slice now carries
  // LIMIT 20 OFFSET 20; the page-2 state holds past the P27 race
  // window (the pin carried forward).
  {
    name: "177_invoices_page2_pushdown_session53",
    url: "/invoices/",
    viewport: [1280, 800],
    clickNext: true,
    waitPastRace: true,
    truths: [
      ["nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 21–\d+ of \d+ rows/],
      ["nav[aria-label='Pagination'] button:last-of-type", "aria-label", "Next page"],
    ],
    prevDisabled: false,
  },
  // 178 — the contacts surface: the pushed-down contacts query.
  {
    name: "178_contacts_pushdown_session53",
    url: "/contacts/",
    viewport: [1280, 800],
    truths: [
      ["nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–\d+ of \d+ rows/],
      ["[data-testid='contacts-list']", null, null],
    ],
  },
  // 179 — the quotes surface: the second documents consumer (the same
  // pushed-down query under the type filter).
  {
    name: "179_quotes_pushdown_session53",
    url: "/quotes/",
    viewport: [1280, 800],
    stockQuotes: true,
    truths: [
      ["nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–\d+ of \d+ rows/],
      ["table", null, null],
    ],
  },
  // 180 — the banking payments tab: the pushed-down payments query.
  {
    name: "180_banking_payments_pushdown_session53",
    url: "/banking/",
    viewport: [1280, 800],
    paymentsTab: true,
    truths: [
      ["[data-testid='payments-list'] nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–\d+ of \d+ rows/],
      ["[data-testid='payments-list']", null, null],
    ],
  },
  // 181 — the banking transactions tab: the pushed-down bank-transaction
  // query (the fourth surface).
  {
    name: "181_banking_transactions_pushdown_session53",
    url: "/banking/",
    viewport: [1280, 800],
    transactionsTab: true,
    truths: [
      ["[data-testid='transactions-list'] nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–\d+ of \d+ rows/],
    ],
  },
  // 182 — mobile regression: the dashboard with the nav closed.
  {
    name: "182_mobile_dashboard_closed_session53",
    url: "/dashboard/",
    viewport: [375, 812],
    truths: [["aside", "visibility", "hidden"]],
  },
  // 183 — mobile regression: the nav open as the modal overlay + the
  // desktop-band sticky aside pin.
  {
    name: "183_mobile_nav_open_session53",
    url: "/dashboard/",
    viewport: [375, 812],
    openNav: true,
    truths: [["aside", "visibility", "visible"], ["aside", "role", "dialog"]],
  },
];

(async () => {
  const browser = await chromium.launch();
  const results = [];
  for (const shot of SHOTS) {
    const ctx = await browser.newContext({
      viewport: { width: shot.viewport[0], height: shot.viewport[1] },
    });
    const page = await ctx.newPage();
    console.log(`  capturing ${shot.name}...`);

    await page.goto(BASE + "/login/", { waitUntil: "networkidle" });
    await page.locator("input[type='email']").fill("demo@ledgersg.sg");
    await page.locator("input[type='password']").fill("demo1234pass");
    await page.getByRole("button", { name: /sign in/i }).click();
    await page.waitForURL(/dashboard/, { timeout: 30000 });

    await page.goto(BASE + shot.url, { waitUntil: "networkidle" });
    await page.waitForTimeout(1200);

    // The quotes surface needs its fodder stocked before the capture
    // (count-driven, idempotent — the P26/FE-P1 convention).
    if (shot.stockQuotes) {
      await ensureQuoteFodder(page);
      await page.reload({ waitUntil: "networkidle" });
      await page.waitForTimeout(1200);
    }

    let truthsOk = true;

    if (shot.openNav) {
      const toggle = page.getByRole("button", { name: /open navigation/i });
      await toggle.click();
      await page.waitForTimeout(400);
    }

    if (shot.clickNext) {
      await page.getByRole("button", { name: "Next page" }).click();
      await page.waitForTimeout(shot.waitPastRace ? 1500 : 500);
    }

    if (shot.paymentsTab) {
      await page.getByRole("tab", { name: /payments/i }).click();
      await page.waitForTimeout(1500);
    }
    if (shot.transactionsTab) {
      await page.getByRole("tab", { name: /transactions/i }).click();
      await page.waitForTimeout(1500);
    }

    if (shot.prevDisabled !== undefined) {
      const prev = page.getByRole("button", { name: "Previous page" });
      const isDisabled = await prev.isDisabled();
      if (isDisabled !== shot.prevDisabled) {
        truthsOk = false;
        console.log(
          `    [truth-fail] previous disabled=${isDisabled} != ${shot.prevDisabled}`
        );
      }
    }

    for (const [sel, prop, expect] of shot.truths) {
      const el = page.locator(sel).first();
      if (prop === null && expect === null) {
        if ((await el.count()) === 0) {
          truthsOk = false;
          console.log(`    [truth-fail] ${sel}: no element`);
        }
      } else if (prop === null) {
        const text = (await el.textContent()) || "";
        if (!expect.test(text)) {
          truthsOk = false;
          console.log(`    [truth-fail] ${sel}: text=${JSON.stringify(text.slice(0, 60))} !~ ${expect}`);
        }
      } else if (prop === "role") {
        const role = await el.getAttribute("role");
        if (role !== expect) {
          truthsOk = false;
          console.log(`    [truth-fail] ${sel}: role=${role} != ${expect}`);
        }
      } else if (prop === "aria-label") {
        const label = await el.getAttribute("aria-label");
        if (label !== expect) {
          truthsOk = false;
          console.log(`    [truth-fail] ${sel}: aria-label=${label} != ${expect}`);
        }
      } else {
        const val = await el.evaluate((n, p) => getComputedStyle(n)[p], prop);
        if (val !== expect) {
          truthsOk = false;
          console.log(`    [truth-fail] ${sel}: ${prop}=${val} != ${expect}`);
        }
      }
    }

    const file = path.join(OUT, shot.name + ".png");
    await page.screenshot({ path: file, fullPage: false });
    const size = fs.statSync(file).size;
    const md5 = crypto
      .createHash("md5")
      .update(fs.readFileSync(file))
      .digest("hex")
      .slice(0, 12);
    results.push({ name: shot.name, truthsOk, size, md5 });
    await ctx.close();
  }
  await browser.close();
  const md5s = new Set();
  for (const r of results) {
    const unique = !md5s.has(r.md5) && md5s.add(r.md5);
    console.log(
      `${r.truthsOk && unique ? "OK  " : "FAIL"} ${r.name} (${(r.size / 1024).toFixed(0)} KB md5:${r.md5})`
    );
  }
  if (
    results.some((r) => !r.truthsOk) ||
    new Set(results.map((r) => r.md5)).size !== results.length
  ) {
    process.exit(1);
  }
})();
