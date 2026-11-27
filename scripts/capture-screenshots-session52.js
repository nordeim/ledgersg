// Session-52 screenshot capture — the P27 remediated surfaces.
// Mirrors the repo convention: pixel-verified captures with DOM truths
// asserted per surface (docs/screenshots/168-175_*_session52.png).
// P27 headline: the pagination state-machine truth — the invoices page 2
// HELD past the old mount-run race window (the P26 code silently
// reverted a click inside ~600ms of mount to the cached page 1; the
// capture waits 1.5s past the click and asserts the page-2 summary is
// still showing), plus the standard mobile-nav regressions.
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
  // 168 — the invoices list page 1: server-side paginated at size 20,
  // Previous disabled on the boundary.
  {
    name: "168_invoices_page1_paginated_session52",
    url: "/invoices/",
    viewport: [1280, 800],
    truths: [
      ["nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–20 of \d+ rows/],
      ["table", null, null],
      ["nav[aria-label='Pagination'] button:first-of-type", "aria-label", "Previous page"],
    ],
    prevDisabled: true,
  },
  // 169 — THE P27 HEADLINE: click Next and WAIT PAST THE OLD RACE
  // WINDOW (1.5s >> the ~600ms mount-run window). The page-2 summary
  // must STILL be showing — the pre-P27 code snapped back to the
  // cached page 1 here (the click silently lost).
  {
    name: "169_invoices_page2_held_session52",
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
  // 170 — the contacts surface: the envelope-consuming list with the
  // shared control.
  {
    name: "170_contacts_paginated_session52",
    url: "/contacts/",
    viewport: [1280, 800],
    truths: [
      ["nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–\d+ of \d+ rows/],
      ["[data-testid='contacts-list']", null, null],
    ],
  },
  // 171 — the banking payments tab: the shared control.
  {
    name: "171_banking_payments_paginated_session52",
    url: "/banking/",
    viewport: [1280, 800],
    paymentsTab: true,
    truths: [
      ["[data-testid='payments-list'] nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–\d+ of \d+ rows/],
      ["[data-testid='payments-list']", null, null],
    ],
  },
  // 172 — the banking transactions tab: the same wiring.
  {
    name: "172_banking_transactions_paginated_session52",
    url: "/banking/",
    viewport: [1280, 800],
    transactionsTab: true,
    truths: [
      ["[data-testid='transactions-list'] nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–\d+ of \d+ rows/],
    ],
  },
  // 173 — mobile regression: the dashboard with the nav closed.
  {
    name: "173_mobile_dashboard_closed_session52",
    url: "/dashboard/",
    viewport: [375, 812],
    truths: [["aside", "visibility", "hidden"]],
  },
  // 174 — mobile regression: the nav open as the modal overlay.
  {
    name: "174_mobile_nav_open_session52",
    url: "/dashboard/",
    viewport: [375, 812],
    openNav: true,
    truths: [["aside", "visibility", "visible"], ["aside", "role", "dialog"]],
  },
  // 175 — the desktop band: the sidebar sticky.
  {
    name: "175_desktop_band_session52",
    url: "/dashboard/",
    viewport: [1280, 800],
    truths: [["aside", "position", "sticky"]],
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

    if (shot.openNav) {
      const toggle = page.getByRole("button", { name: /open navigation/i });
      await toggle.click();
      await page.waitForTimeout(400);
    }

    // P27: page 2 — drive the pagination control live and wait WELL
    // PAST the old race window; the page-2 state must hold.
    if (shot.clickNext) {
      await page.getByRole("button", { name: "Next page" }).click();
      await page.waitForTimeout(shot.waitPastRace ? 1500 : 500);
    }

    // The banking tabs are not the default — click and wait for the
    // list region.
    if (shot.paymentsTab) {
      await page.getByRole("tab", { name: /payments/i }).click();
      await page.waitForTimeout(1500);
    }
    if (shot.transactionsTab) {
      await page.getByRole("tab", { name: /transactions/i }).click();
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
