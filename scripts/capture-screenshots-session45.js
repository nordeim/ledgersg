// Session-45 screenshot capture — the P24 remediated surfaces.
// Mirrors the repo convention: pixel-verified captures with DOM truths
// asserted per surface (docs/screenshots/144-151_*_session45.png).
// P24 surfaces: the paginated general ledger (the headline — page 1 with
// the controls + the summary "Showing 1–20 of N", and page 2 after Next
// with the advanced summary), plus the standard regressions on the
// remediated stack (the mobile drawer closed/open, the desktop band,
// the org selector reading the unified envelope, invoices, banking).
// P17/DOC-M11: self-resolving require — resolve @playwright/test from
// the web app's node_modules (the prod-csp-smoke.js pattern).
const { chromium } = require(
  require("path").join(__dirname, "..", "apps", "web", "node_modules", "@playwright", "test")
);
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const BASE = "http://localhost:3000";
const OUT = path.join(__dirname, "..", "docs", "screenshots");

const SHOTS = [
  // 144 — THE P24 headline: the general ledger page 1 — the
  // server-side pagination controls live over real rows, the summary
  // reading "Showing 1–20 of N rows", Previous disabled on page 1.
  {
    name: "144_ledger_page1_pagination_session45",
    url: "/ledger/",
    viewport: [1280, 800],
    truths: [
      ["nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–20 of \d+ rows/],
      ["table", null, null],
    ],
    prevDisabled: true,
  },
  // 145 — the P24 headline, page 2: click Next — the summary advances
  // past row 20 ("Showing 21–N of N rows"), Previous enables.
  {
    name: "145_ledger_page2_pagination_session45",
    url: "/ledger/",
    viewport: [1280, 800],
    clickNext: true,
    truths: [
      ["nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 21–\d+ of \d+ rows/],
      ["table", null, null],
    ],
    prevDisabled: false,
  },
  // 146 — mobile regression: the dashboard with the nav closed.
  {
    name: "146_mobile_dashboard_closed_session45",
    url: "/dashboard/",
    viewport: [375, 812],
    truths: [["aside", "visibility", "hidden"]],
  },
  // 147 — mobile regression: the nav open as the modal overlay.
  {
    name: "147_mobile_nav_open_session45",
    url: "/dashboard/",
    viewport: [375, 812],
    openNav: true,
    truths: [["aside", "visibility", "visible"], ["aside", "role", "dialog"]],
  },
  // 148 — the desktop band: toggle hidden, the sidebar sticky.
  {
    name: "148_desktop_band_session45",
    url: "/dashboard/",
    viewport: [1280, 800],
    truths: [["aside", "position", "sticky"]],
  },
  // 149 — surface regression: the org selector reading the unified
  // {results, count} envelope (the menu lists the demo org).
  {
    name: "149_org_selector_envelope_session45",
    url: "/dashboard/",
    viewport: [1280, 800],
    orgMenu: true,
    truths: [["[role='menuitemradio']", null, /ledger demo/i]],
  },
  // 150 — surface regression: the invoices list with real rows.
  {
    name: "150_invoices_desktop_session45",
    url: "/invoices/",
    viewport: [1280, 800],
    truths: [["table", null, null]],
  },
  // 151 — surface regression: the banking payments tab with real
  // payment cards (the payments list region; the tab is not the default
  // — the shot drives it live).
  {
    name: "151_banking_payments_session45",
    url: "/banking/",
    viewport: [1280, 800],
    paymentsTab: true,
    truths: [["[data-testid='payments-list']", null, null]],
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

    await page.goto(BASE + "/login/", { waitUntil: "networkidle" });
    await page.locator("input[type='email']").fill("demo@ledgersg.sg");
    await page.locator("input[type='password']").fill("demo1234pass");
    await page.getByRole("button", { name: /sign in/i }).click();
    await page.waitForURL(/dashboard/, { timeout: 30000 });

    await page.goto(BASE + shot.url, { waitUntil: "networkidle" });
    await page.waitForTimeout(1200);

    let truthsOk = true;

    if (shot.orgMenu) {
      await page.getByRole("button", { name: /switch organisation/i }).click();
      await page.waitForTimeout(700);
    }

    if (shot.openNav) {
      const toggle = page.getByRole("button", { name: /open navigation/i });
      await toggle.click();
      await page.waitForTimeout(400);
    }

    // P24: page 2 — drive the pagination control live (the exact user
    // path the e2e gates) and wait for the page to settle.
    if (shot.clickNext) {
      await page.getByRole("button", { name: "Next page" }).click();
      await page.waitForTimeout(1500);
    }

    // The banking payments tab is not the default — click it and wait
    // for the list region.
    if (shot.paymentsTab) {
      await page.getByRole("tab", { name: /payments/i }).click();
      await page.waitForTimeout(1500);
    }

    // P24: the Previous button's disabled state — the boundary contract
    // (disabled on page 1, enabled past it).
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
