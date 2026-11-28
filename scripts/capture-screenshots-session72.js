// Session-72 screenshot capture — the P37 remediated surfaces.
// Mirrors the repo convention: pixel-verified captures with DOM truths
// asserted per surface (docs/screenshots/248-255_*_session72.png).
// P37 headline: the credit-note reference truth (the BillingReference
// wiring + the Schematron BR-SG-07 pin + the PDF presentation). The
// credit note is API/PDF-level (no dedicated browser surface), so the
// captures pin the rendered consumer surfaces (the invoices list — the
// transmitted documents, the invoice detail, the banking payments, the
// reports) plus the standing mobile regressions.
const {
  chromium,
} = require(
  require("path").join(__dirname, "..", "apps", "web", "node_modules", "@playwright", "test")
);
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const BASE = "http://localhost:3000";
const OUT = path.join(__dirname, "..", "docs", "screenshots");

const SHOTS = [
  // 248 — the invoices list page 1: the transmitted-documents surface
  // (the credit notes ride the same pipeline the reference now guards).
  {
    name: "248_invoices_page1_session72",
    url: "/invoices/",
    viewport: [1280, 800],
    truths: [
      ["nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–20 of \d+ rows/],
      ["table", null, null],
    ],
    prevDisabled: true,
  },
  // 249 — the invoice detail (the document-detail surface).
  {
    name: "249_invoice_detail_session72",
    url: "/invoices/",
    viewport: [1280, 800],
    firstRow: true,
    truths: [["main", null, null]],
  },
  // 250 — the banking payments tab (the standing payment surface).
  {
    name: "250_banking_payments_session72",
    url: "/banking/",
    viewport: [1280, 800],
    paymentsTab: true,
    truths: [
      ["[data-testid='payments-list'] nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–\d+ of \d+ rows/],
      ["[data-testid='payments-list']", null, null],
    ],
  },
  // 251 — the reports trial-balance tab (the totals consumer).
  {
    name: "251_reports_trial_balance_session72",
    url: "/reports/",
    viewport: [1280, 800],
    trialBalanceTab: true,
    truths: [
      ["[role='tablist'] [role='tab']", null, /trial balance/i],
      ["table", null, null],
    ],
  },
  // 252 — the ledger page (the standing journal-surface regression).
  {
    name: "252_ledger_lines_session72",
    url: "/ledger/",
    viewport: [1280, 800],
    truths: [
      ["nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–\d+ of \d+ rows/],
      ["table", null, null],
    ],
  },
  // 253 — the dashboard (the standard post-closure regression).
  {
    name: "253_dashboard_session72",
    url: "/dashboard/",
    viewport: [1280, 800],
    truths: [["h1", null, /command center/i]],
  },
  // 254 — mobile regression: the dashboard with the nav closed.
  {
    name: "254_mobile_dashboard_closed_session72",
    url: "/dashboard/",
    viewport: [375, 812],
    truths: [["aside", "visibility", "hidden"]],
  },
  // 255 — mobile regression: the nav open as the modal overlay.
  {
    name: "255_mobile_nav_open_session72",
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

    let truthsOk = true;

    if (shot.openNav) {
      const toggle = page.getByRole("button", { name: /open navigation/i });
      await toggle.click();
      await page.waitForTimeout(400);
    }

    if (shot.firstRow) {
      // from the invoices list, open the first document row
      await page.goto(BASE + "/invoices/", { waitUntil: "networkidle" });
      await page.waitForTimeout(800);
      const row = page.locator("table tbody tr").first();
      await row.locator("a").first().click();
      await page.waitForTimeout(1500);
    }

    if (shot.trialBalanceTab) {
      await page.getByRole("tab", { name: /trial balance/i }).click();
      await page.waitForTimeout(1800);
    }
    if (shot.paymentsTab) {
      await page.getByRole("tab", { name: /payments/i }).click();
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
    if (!ok) allOk = false;
    seen.add(r.md5);
    console.log(
      `${ok ? "OK  " : "FAIL"} ${r.shot} truths=${r.truthsOk} size=${r.size} md5=${r.md5}`
    );
  }
  console.log(allOk ? "\nALL CAPTURES OK" : "\nCAPTURE FAILURES PRESENT");
  process.exit(allOk ? 0 : 1);
})();
