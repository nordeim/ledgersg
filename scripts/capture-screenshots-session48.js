// Session-48 screenshot capture — the P25 remediated surfaces.
// Mirrors the repo convention: pixel-verified captures with DOM truths
// asserted per surface (docs/screenshots/152-159_*_session48.png).
// P25 surfaces: the fresh-substrate paginated general ledger (the
// headline — a single §9 bootstrap now stocks 36+ lines, so page 1
// reads "Showing 1–20 of N" over the fodder and page 2 lives after
// Next), the P25 aria-conformant pagination buttons ("Previous page"/
// "Next page" — the WCAG 2.5.3 Label-in-Name fix), plus the standard
// regressions on the remediated stack (the mobile drawer closed/open,
// the desktop band, the org selector, invoices, banking payments).
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
  // 152 — THE P25 headline: the general ledger page 1 on the FRESH
  // substrate — the server-side pagination controls live over the
  // bootstrap's own fodder (a single §9 run now stocks 36+ lines),
  // Previous disabled on page 1.
  {
    name: "152_ledger_page1_fresh_substrate_session48",
    url: "/ledger/",
    viewport: [1280, 800],
    truths: [
      ["nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–20 of \d+ rows/],
      ["table", null, null],
      // P25/FE-L1: the accessible names carry the visible text.
      ["nav[aria-label='Pagination'] button:first-of-type", "aria-label", "Previous page"],
    ],
    prevDisabled: true,
  },
  // 153 — the P25 headline, page 2: click Next — the summary advances
  // past row 20 ("Showing 21–N of N rows"), Previous enables.
  {
    name: "153_ledger_page2_fresh_substrate_session48",
    url: "/ledger/",
    viewport: [1280, 800],
    clickNext: true,
    truths: [
      ["nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 21–\d+ of \d+ rows/],
      ["table", null, null],
      ["nav[aria-label='Pagination'] button:last-of-type", "aria-label", "Next page"],
    ],
    prevDisabled: false,
  },
  // 154 — mobile regression: the dashboard with the nav closed.
  {
    name: "154_mobile_dashboard_closed_session48",
    url: "/dashboard/",
    viewport: [375, 812],
    truths: [["aside", "visibility", "hidden"]],
  },
  // 155 — mobile regression: the nav open as the modal overlay.
  {
    name: "155_mobile_nav_open_session48",
    url: "/dashboard/",
    viewport: [375, 812],
    openNav: true,
    truths: [["aside", "visibility", "visible"], ["aside", "role", "dialog"]],
  },
  // 156 — the desktop band: the sidebar sticky.
  {
    name: "156_desktop_band_session48",
    url: "/dashboard/",
    viewport: [1280, 800],
    truths: [["aside", "position", "sticky"]],
  },
  // 157 — surface regression: the org selector reading the unified
  // {results, count} envelope (the menu lists the demo org).
  {
    name: "157_org_selector_envelope_session48",
    url: "/dashboard/",
    viewport: [1280, 800],
    orgMenu: true,
    truths: [["[role='menuitemradio']", null, /ledger demo/i]],
  },
  // 158 — surface regression: the invoices list with real rows.
  {
    name: "158_invoices_desktop_session48",
    url: "/invoices/",
    viewport: [1280, 800],
    truths: [["table", null, null]],
  },
  // 159 — surface regression: the banking payments tab with real
  // payment cards (the payments list region; the tab is not the
  // default — the shot drives it live).
  {
    name: "159_banking_payments_session48",
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

    // P25: page 2 — drive the pagination control live (the exact user
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

    // The Previous button's disabled state — the boundary contract
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
