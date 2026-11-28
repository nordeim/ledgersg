// Session-62 screenshot capture — the P32 remediated surfaces.
// Mirrors the repo convention: pixel-verified captures with DOM truths
// asserted per surface (docs/screenshots/208-215_*_session62.png).
// P32 headline: the dead-code/shadow/suppress closure (the 3 service
// seams — payment void's dead reversal binding, the transition's dead
// old_status, approve's dead fiscal_period — plus the F402 status
// shadow in DocumentSummaryView, the journal_service E741/A001 renames
// and the SIM105 suppress conversions) + the tests-tree residual
// closure (the F811 conftest placement) + the extended closed-class
// ratchet. The closures are response-byte-stable, so the captures pin
// the rendered surfaces whose service seams the sprint touched (the
// trial-balance report — the get_trial_balance rename seam; the
// invoices area — the DocumentSummaryView sibling; the ledger — the
// journal service surfaces) plus the standing list/mobile regressions.
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
  // 208 — the reports trial-balance tab: THE P32 headline surface —
  // the get_trial_balance seam where the A001 credits->credit_total
  // rename lives (the incomplete first attempt broke exactly this
  // surface; the fix restored it — live-verified this session).
  {
    name: "208_reports_trial_balance_session62",
    url: "/reports/",
    viewport: [1280, 800],
    trialBalanceTab: true,
    truths: [
      ["[role='tablist'] [role='tab']", null, /trial balance/i],
      ["table", null, null],
    ],
  },
  // 209 — the reports P&L tab (the standing reports regression).
  {
    name: "209_reports_pl_session62",
    url: "/reports/",
    viewport: [1280, 800],
    plTab: true,
    truths: [["table", null, null]],
  },
  // 210 — the invoices list page 1 (the DocumentSummaryView sibling
  // surface — the F402 status_value rename; the standing regression).
  {
    name: "210_invoices_page1_session62",
    url: "/invoices/",
    viewport: [1280, 800],
    truths: [
      ["nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–20 of \d+ rows/],
      ["table", null, null],
    ],
    prevDisabled: true,
  },
  // 211 — the ledger page (the journal-service surfaces: the E741
  // renames, the SIM105 suppress, the balance-cache invalidation).
  {
    name: "211_ledger_lines_session62",
    url: "/ledger/",
    viewport: [1280, 800],
    truths: [
      ["nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–\d+ of \d+ rows/],
      ["table", null, null],
    ],
  },
  // 212 — the banking payments tab (the payment_service void seam —
  // the dead reversal binding closure; the standing regression).
  {
    name: "212_banking_payments_session62",
    url: "/banking/",
    viewport: [1280, 800],
    paymentsTab: true,
    truths: [
      ["[data-testid='payments-list'] nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–\d+ of \d+ rows/],
      ["[data-testid='payments-list']", null, null],
    ],
  },
  // 213 — the dashboard (the standard post-closure regression).
  {
    name: "213_dashboard_session62",
    url: "/dashboard/",
    viewport: [1280, 800],
    truths: [["h1", null, /command center/i]],
  },
  // 214 — mobile regression: the dashboard with the nav closed.
  {
    name: "214_mobile_dashboard_closed_session62",
    url: "/dashboard/",
    viewport: [375, 812],
    truths: [["aside", "visibility", "hidden"]],
  },
  // 215 — mobile regression: the nav open as the modal overlay.
  {
    name: "215_mobile_nav_open_session62",
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

    if (shot.trialBalanceTab) {
      await page.getByRole("tab", { name: /trial balance/i }).click();
      await page.waitForTimeout(1800);
    }
    if (shot.plTab) {
      await page.getByRole("tab", { name: /profit/i }).click();
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
    if (!r.truthsOk || r.size <= 10000 || seen.has(r.md5)) allOk = false;
    seen.add(r.md5);
    console.log(
      `${ok ? "OK  " : "FAIL"} ${r.shot} truths=${r.truthsOk} size=${r.size} md5=${r.md5}`
    );
  }
  process.exit(allOk ? 0 : 1);
})();
