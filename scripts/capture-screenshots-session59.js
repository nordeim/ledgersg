// Session-59 screenshot capture — the P31 remediated surfaces.
// Mirrors the repo convention: pixel-verified captures with DOM truths
// asserted per surface (docs/screenshots/200-207_*_session59.png).
// P31 headline: the B904 exception-chaining closure (66 raise-inside-
// except sites now chain explicitly — 62 `from exc` preserving the
// cause, 4 `from None` where the message already embeds the original
// error string) + the tests-tree mechanical extension (221 findings
// closed) + the unified closed-class ratchet. The chaining is
// backend-invisible (the response bytes are pinned byte-identical), so
// the captures pin the rendered surfaces whose error contracts are the
// chaining consumers (the allocation typed-400 seam, the not-found
// 404 seam) plus the standing list/detail/mobile-nav regressions.
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
  // 200 — the banking payments tab: THE P31 headline surface — the
  // allocation flow behind the typed-400 bodies (the money-parse
  // ValidationError whose __cause__ the T2 gate pins; the response
  // bytes byte-identical under the chaining closure).
  {
    name: "200_banking_payments_chaining_session59",
    url: "/banking/",
    viewport: [1280, 800],
    paymentsTab: true,
    truths: [
      ["[data-testid='payments-list'] nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–\d+ of \d+ rows/],
      ["[data-testid='payments-list']", null, null],
    ],
  },
  // 201 — the invoice detail page: the ResourceNotFound seam (the T1
  // gate pins __cause__ = InvoiceDocument.DoesNotExist; the rendered
  // detail is the surface that 404s when the translation fires).
  {
    name: "201_invoice_detail_notfound_seam_session59",
    url: null, // resolved per-run via firstInvoiceId
    viewport: [1280, 800],
    truths: [
      ["h1", null, /^(INV-|CN-)\d+/],
      ["table", null, null],
      ["text=Subtotal", null, null],
    ],
  },
  // 202 — the invoices list page 1 (the standing list regression).
  {
    name: "202_invoices_page1_session59",
    url: "/invoices/",
    viewport: [1280, 800],
    truths: [
      ["nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–20 of \d+ rows/],
      ["table", null, null],
    ],
    prevDisabled: true,
  },
  // 203 — the ledger page (the SQL-paged ledger regression).
  {
    name: "203_ledger_lines_session59",
    url: "/ledger/",
    viewport: [1280, 800],
    truths: [
      ["nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–\d+ of \d+ rows/],
      ["table", null, null],
    ],
  },
  // 204 — the banking transactions tab (the P30 headline surface, the
  // standing regression).
  {
    name: "204_banking_transactions_session59",
    url: "/banking/",
    viewport: [1280, 800],
    transactionsTab: true,
    truths: [
      ["[data-testid='transactions-list'] nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–\d+ of \d+ rows/],
      ["[data-testid='transactions-list']", null, null],
    ],
  },
  // 205 — the dashboard (the standard post-closure regression).
  {
    name: "205_dashboard_session59",
    url: "/dashboard/",
    viewport: [1280, 800],
    truths: [["h1", null, /command center/i]],
  },
  // 206 — mobile regression: the dashboard with the nav closed.
  {
    name: "206_mobile_dashboard_closed_session59",
    url: "/dashboard/",
    viewport: [375, 812],
    truths: [["aside", "visibility", "hidden"]],
  },
  // 207 — mobile regression: the nav open as the modal overlay.
  {
    name: "207_mobile_nav_open_session59",
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
    results.push({ shot: shot.name, truthsOk, size, md5 });
    await ctx.close();
  }
  await browser.close();

  console.log("\n=== capture summary ===");
  let allOk = true;
  const seen = new Set();
  for (const r of results) {
    const ok = r.truthsOk && r.size > 10000 && !seen.has(r.md5);
    if (!r.truthsOk || r.size <= 10000 || seen.has(r.md5)) allOk = false;
    seen.add(r.md5);
    console.log(
      `${ok ? "OK  " : "FAIL"} ${r.shot} truths=${r.truthsOk} size=${r.size} md5=${r.md5}`
    );
  }
  process.exit(allOk ? 0 : 1);
})();
