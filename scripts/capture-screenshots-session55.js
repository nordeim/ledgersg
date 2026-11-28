// Session-55 screenshot capture — the P29 remediated surfaces.
// Mirrors the repo convention: pixel-verified captures with DOM truths
// asserted per surface (docs/screenshots/184-191_*_session55.png).
// P29 headline: the detail-view N+1 closure — the three detail seams
// (document detail, journal entry detail, payment detail) now fetch
// their related rows in a bounded, line-count-independent set (the
// contact + lines-with-account-tax_code prefetch on the document; the
// lines-with-account prefetch on the journal entry; the contact +
// bank_account join on the payment); the payloads are byte-identical,
// so the captures pin the rendered detail surfaces plus the standard
// list/mobile-nav regressions.
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

/** Fetch the demo org's first invoice id (the detail capture needs a
 * real document to render; count-driven, read-only). */
async function firstInvoiceId(page) {
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
    await page.request.get(`${API}/api/v1/${orgId}/invoicing/documents/`, {
      headers: auth,
    })
  ).json();
  const invoice = (list.results || []).find(
    (d) => d.document_type === "SALES_INVOICE"
  );
  if (!invoice) throw new Error("no SALES_INVOICE on the demo org");
  return invoice.id;
}

const SHOTS = [
  // 184 — the invoice detail page: THE P29 headline surface — the
  // lines table renders from the bounded prefetch (contact + lines +
  // account + tax_code fetched in 3 queries regardless of line count;
  // the pre-P29 walk paid 2 per line).
  {
    name: "184_invoice_detail_bounded_session55",
    url: null, // resolved per-run via firstInvoiceId
    viewport: [1280, 800],
    truths: [
      ["h1", null, /^(INV-|CN-)\d+/],
      ["table", null, null],
      ["text=Subtotal", null, null],
    ],
  },
  // 185 — the invoices list page 1: the P28 push-down holds (LIMIT 20),
  // Previous disabled on the boundary.
  {
    name: "185_invoices_page1_pushdown_session55",
    url: "/invoices/",
    viewport: [1280, 800],
    truths: [
      ["nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–20 of \d+ rows/],
      ["table", null, null],
    ],
    prevDisabled: true,
  },
  // 186 — the ledger page: the journal lines table renders with the
  // account codes (the surface fed by the SQL-paged ledger; the journal
  // detail seam behind the entries now prefetches lines+accounts).
  {
    name: "186_ledger_lines_session55",
    url: "/ledger/",
    viewport: [1280, 800],
    truths: [
      ["nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–\d+ of \d+ rows/],
      ["table", null, null],
    ],
  },
  // 187 — the banking payments tab: the payment rows render (the
  // detail seam behind the rows now joins contact + bank_account).
  {
    name: "187_banking_payments_session55",
    url: "/banking/",
    viewport: [1280, 800],
    paymentsTab: true,
    truths: [
      ["[data-testid='payments-list'] nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–\d+ of \d+ rows/],
      ["[data-testid='payments-list']", null, null],
    ],
  },
  // 188 — the banking transactions tab.
  {
    name: "188_banking_transactions_session55",
    url: "/banking/",
    viewport: [1280, 800],
    transactionsTab: true,
    truths: [
      ["[data-testid='transactions-list'] nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–\d+ of \d+ rows/],
    ],
  },
  // 189 — the contacts surface (the pushed-down contacts query).
  {
    name: "189_contacts_session55",
    url: "/contacts/",
    viewport: [1280, 800],
    truths: [
      ["nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–\d+ of \d+ rows/],
      ["[data-testid='contacts-list']", null, null],
    ],
  },
  // 190 — mobile regression: the dashboard with the nav closed.
  {
    name: "190_mobile_dashboard_closed_session55",
    url: "/dashboard/",
    viewport: [375, 812],
    truths: [["aside", "visibility", "hidden"]],
  },
  // 191 — mobile regression: the nav open as the modal overlay.
  {
    name: "191_mobile_nav_open_session55",
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

    let target = shot.url;
    if (target === null) {
      const id = await firstInvoiceId(page);
      target = `/invoices/${id}/`;
    }

    await page.goto(BASE + target, { waitUntil: "networkidle" });
    await page.waitForTimeout(1200);

    let truthsOk = true;

    if (shot.openNav) {
      const toggle = page.getByRole("button", { name: /open navigation/i });
      await toggle.click();
      await page.waitForTimeout(400);
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
