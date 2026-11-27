// Session-42 screenshot capture — the P21 remediated surfaces.
// Mirrors the repo convention: pixel-verified captures with DOM truths
// asserted per surface (docs/screenshots/128-135_*_session42.png).
// P21 surfaces: the Make-Payment Reference accessible name (FE-H1), the
// keyboard-reachable sr-only CSV import input (FE-H2), the payment-card
// button contract (FE-M4), the loader live regions (FE-M2 — captured by
// DELAYING the bank-accounts response so the skeleton stays on screen),
// the lexical GST year (FE-M3), the org selector reading the unified
// {results, count} envelope (BE-M6), and the standard mobile regression
// captures (the nav closed + open-as-dialog).
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

const CURRENT_YEAR = String(new Date().getFullYear());

const SHOTS = [
  // 128 — FE-H1: the Make Payment form's Reference input is named
  // (aria-label; the label is visible but unassociated).
  {
    name: "128_make_payment_reference_name_session42",
    url: "/banking/",
    viewport: [1280, 800],
    paymentsTab: true,
    makePaymentDialog: true,
    referenceProbe: true,
    truths: [["input[aria-label='Reference']", null, null]],
  },
  // 129 — FE-H2: the CSV import's file input is sr-only (focusable +
  // labelled), not display:none; the import dialog carries unique ids.
  {
    name: "129_csv_import_sr_only_session42",
    url: "/banking/",
    viewport: [1280, 800],
    transactionsTab: true,
    importDialog: true,
    truths: [["#import-bank-account", null, null]],
    csvProbe: true,
  },
  // 130 — FE-M4: the payment card carries the button contract
  // (role=button + tabindex) on the Payments tab.
  {
    name: "130_payment_card_button_session42",
    url: "/banking/",
    viewport: [1280, 800],
    paymentsTab: true,
    truths: [["[data-testid='payment-card'][role='button']", null, null]],
  },
  // 131 — FE-M2: the banking loader is a live region (captured by
  // delaying the bank-accounts response — the skeleton stays visible).
  {
    name: "131_banking_loader_live_region_session42",
    url: "/banking/",
    viewport: [1280, 800],
    delayAccounts: true,
    truths: [["[data-testid='accounts-loading-skeleton'][role='status']", null, null]],
  },
  // 132 — FE-M3: the GST F5 tab derives its year lexically — the
  // section heading carries the current calendar year.
  {
    name: "132_reports_gst_year_lexical_session42",
    url: "/reports/",
    viewport: [1280, 800],
    gstTab: true,
    truths: [["#gst-f5-year-heading", null, new RegExp(CURRENT_YEAR)]],
  },
  // 133 — BE-M6: the org selector reads the unified {results, count}
  // envelope — the menu lists the demo org (an empty menu would mean
  // the .results read broke).
  {
    name: "133_org_selector_envelope_session42",
    url: "/dashboard/",
    viewport: [1280, 800],
    orgMenu: true,
    truths: [["[role='menuitemradio']", null, /ledger demo/i]],
  },
  // 134 — mobile regression: the dashboard with the nav closed.
  {
    name: "134_mobile_dashboard_closed_session42",
    url: "/dashboard/",
    viewport: [375, 812],
    truths: [["aside", "visibility", "hidden"]],
  },
  // 135 — mobile regression: the nav open as the modal overlay.
  {
    name: "135_mobile_nav_open_session42",
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

    // FE-M2: delay the bank-accounts response so the skeleton loader
    // stays on screen during the capture.
    if (shot.delayAccounts) {
      await page.route(/\/banking\/bank-accounts/, async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 4000));
        await route.continue();
      });
    }

    await page.goto(BASE + "/login/", { waitUntil: "networkidle" });
    await page.locator("input[type='email']").fill("demo@ledgersg.sg");
    await page.locator("input[type='password']").fill("demo1234pass");
    await page.getByRole("button", { name: /sign in/i }).click();
    await page.waitForURL(/dashboard/, { timeout: 30000 });

    // FE-M2 loader shots: capture while the response is still in
    // flight (networkidle would consume the delay and the skeleton
    // would be gone).
    const waitUntil = shot.delayAccounts ? "domcontentloaded" : "networkidle";
    await page.goto(BASE + shot.url, { waitUntil });
    await page.waitForTimeout(shot.delayAccounts ? 1500 : 1200);

    let probe = "";
    let truthsOk = true;

    if (shot.paymentsTab) {
      await page.getByRole("tab", { name: /payments/i }).click();
      await page.waitForTimeout(900);
    }
    if (shot.transactionsTab) {
      await page.getByRole("tab", { name: /transactions/i }).click();
      await page.waitForTimeout(900);
    }
    if (shot.makePaymentDialog) {
      await page.getByRole("button", { name: /make payment/i }).first().click();
      await page.waitForTimeout(900);
    }
    if (shot.importDialog) {
      await page.getByRole("button", { name: /import statement/i }).first().click();
      await page.waitForTimeout(900);
    }
    if (shot.gstTab) {
      await page.getByRole("tab", { name: /gst f5/i }).click();
      await page.waitForTimeout(900);
    }
    if (shot.orgMenu) {
      await page.getByRole("button", { name: /switch organisation/i }).click();
      await page.waitForTimeout(700);
    }
    if (shot.openNav) {
      const toggle = page.getByRole("button", { name: /open navigation/i });
      await toggle.click();
      await page.waitForTimeout(400);
    }

    // FE-H1: fill the Reference input BY ITS ACCESSIBLE NAME.
    if (shot.referenceProbe) {
      const reference = page.getByLabel("Reference", { exact: true });
      await reference.waitFor({ timeout: 15000 });
      await reference.fill("BILL-000042");
      await page.waitForTimeout(400);
      probe = "reference-by-label:1";
    }

    // FE-H2: the CSV file input carries sr-only (not hidden) + the
    // label association resolves.
    if (shot.csvProbe) {
      const cls = await page.locator("#csv-file").getAttribute("class");
      const labelled = await page.getByLabel(/CSV File/i).count();
      probe = `csv-class:${cls} csv-by-label:${labelled}`;
      if (!cls || !cls.includes("sr-only") || cls.includes("hidden") || !labelled) {
        truthsOk = false;
      }
    }

    for (const [sel, prop, expect] of shot.truths) {
      const el =
        sel === "h1"
          ? page.locator(sel).last()
          : sel === "#gst-f5-year-heading"
            ? page.getByRole("heading", { name: new RegExp(`GST F5 Returns \\(${CURRENT_YEAR}\\)`, "i") })
            : page.locator(sel).first();
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
    results.push({ name: shot.name, truthsOk, size, md5, probe });
    await ctx.close();
  }
  await browser.close();
  const md5s = new Set();
  for (const r of results) {
    const unique = !md5s.has(r.md5) && md5s.add(r.md5);
    const probe = r.probe ? ` | ${r.probe}` : "";
    console.log(
      `${r.truthsOk && unique ? "OK  " : "FAIL"} ${r.name} (${(r.size / 1024).toFixed(0)} KB md5:${r.md5}${probe})`
    );
  }
  if (
    results.some((r) => !r.truthsOk) ||
    new Set(results.map((r) => r.md5)).size !== results.length
  ) {
    process.exit(1);
  }
})();
