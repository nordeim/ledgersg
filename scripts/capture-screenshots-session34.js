// Session-34 screenshot capture — the P17 remediated surfaces.
// Mirrors the repo convention: pixel-verified captures with DOM truths
// asserted per surface (docs/screenshots/96-103_*_session34.png).
// P17 surfaces: the --color-success token (received-payment amounts on
// the banking payments tab), the invoice form (the unsaved-changes-guard
// surface), and the org-selector menu (FE-L4 — role=menu +
// menuitemradio + aria-expanded, keyboard-operable).
// P17/DOC-M11: self-resolving require — this script runs from the repo
// root, where a bare require("@playwright/test") cannot resolve; resolve
// it from the web app's node_modules (the prod-csp-smoke.js pattern).
const { chromium } = require(
  require("path").join(__dirname, "..", "apps", "web", "node_modules", "@playwright", "test")
);
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const BASE = "http://localhost:3000";
const OUT = path.join(__dirname, "..", "docs", "screenshots");
const SHOTS = [
  { name: "96_dashboard_desktop_session34", url: "/dashboard/", viewport: [1280, 800], truths: [["h1", null, /command center/i]] },
  { name: "97_banking_payments_session34", url: "/banking/", viewport: [1280, 800], clickPaymentsTab: true, truths: [["h1", null, /banking/i]], successProbe: true },
  { name: "98_invoices_desktop_session34", url: "/invoices/", viewport: [1280, 800], truths: [["h1", null, /invoices/i]] },
  { name: "99_invoice_form_desktop_session34", url: "/invoices/new/", viewport: [1280, 800], truths: [["h1", null, /new invoice|create invoice|invoice/i]] },
  { name: "100_reports_desktop_session34", url: "/reports/", viewport: [1280, 800], truths: [["h1", null, /reports/i]] },
  {
    name: "101_org_selector_menu_session34",
    url: "/dashboard/",
    viewport: [1280, 800],
    openOrgMenu: true,
    truths: [
      ["[role='menu']", null, null],
      ["[role='menuitemradio']", null, /ltd/i],
      ["#org-selector-trigger", "aria-expanded", "true"],
    ],
  },
  { name: "102_mobile_dashboard_closed_session34", url: "/dashboard/", viewport: [375, 812], truths: [["aside", "visibility", "hidden"]] },
  { name: "103_mobile_nav_open_dialog_session34", url: "/dashboard/", viewport: [375, 812], openNav: true, truths: [["aside", "visibility", "visible"], ["aside", "role", "dialog"]] },
];

(async () => {
  const browser = await chromium.launch();
  const results = [];
  for (const shot of SHOTS) {
    const ctx = await browser.newContext({ viewport: { width: shot.viewport[0], height: shot.viewport[1] } });
    const page = await ctx.newPage();
    await page.goto(BASE + "/login/", { waitUntil: "networkidle" });
    await page.locator("input[type='email']").fill("demo@ledgersg.sg");
    await page.locator("input[type='password']").fill("demo1234pass");
    await page.getByRole("button", { name: /sign in/i }).click();
    await page.waitForURL(/dashboard/, { timeout: 30000 });
    await page.goto(BASE + shot.url, { waitUntil: "networkidle" });
    await page.waitForTimeout(1200);
    if (shot.clickPaymentsTab) {
      // The Payments tab carries the received-payment cards whose amounts
      // render with the P17 --color-success utilities (FE-M1 live proof).
      await page.getByRole("tab", { name: /payments/i }).click();
      await page.waitForTimeout(1200);
    }
    if (shot.openNav) {
      const toggle = page.getByRole("button", { name: /open navigation/i });
      await toggle.click();
      await page.waitForTimeout(400);
    }
    if (shot.openOrgMenu) {
      // P17/FE-L4: the org-selector trigger (aria-label "Switch organisation").
      await page.getByRole("button", { name: /switch organisation/i }).click();
      await page.waitForTimeout(400);
    }
    // DOM truths
    let truthsOk = true;
    for (const [sel, prop, expect] of shot.truths) {
      const el = sel === "h1" ? page.locator(sel).last() : page.locator(sel).first();
      if (prop === null && expect === null) {
        // existence truth
        if ((await el.count()) === 0) truthsOk = false;
      } else if (prop === null) {
        const text = (await el.textContent()) || "";
        if (!expect.test(text)) truthsOk = false;
      } else if (prop === "aria-expanded") {
        const role = await el.getAttribute("aria-expanded");
        if (role !== expect) truthsOk = false;
      } else if (prop === "role") {
        const role = await el.getAttribute("role");
        if (role !== expect) truthsOk = false;
      } else {
        const val = await el.evaluate((n, p) => getComputedStyle(n)[p], prop);
        if (val !== expect) truthsOk = false;
      }
    }
    // P17/FE-M1 probe (soft — reported, not gated): does the live page use
    // the --color-success utilities (the token the audit found missing)?
    let successCount = -1;
    if (shot.successProbe) {
      successCount = await page
        .locator("[class*='text-success'], [class*='bg-success']")
        .count();
    }
    const file = path.join(OUT, shot.name + ".png");
    await page.screenshot({ path: file, fullPage: false });
    const size = fs.statSync(file).size;
    const md5 = crypto.createHash("md5").update(fs.readFileSync(file)).digest("hex").slice(0, 12);
    results.push({ name: shot.name, truthsOk, size, md5, successCount });
    await ctx.close();
  }
  await browser.close();
  const md5s = new Set();
  for (const r of results) {
    const unique = !md5s.has(r.md5) && md5s.add(r.md5);
    const probe = r.successCount >= 0 ? ` success-utility els: ${r.successCount}` : "";
    console.log(`${r.truthsOk && unique ? "OK  " : "FAIL"} ${r.name} (${(r.size / 1024).toFixed(0)} KB md5:${r.md5}${probe})`);
  }
  if (results.some((r) => !r.truthsOk) || new Set(results.map((r) => r.md5)).size !== results.length) {
    process.exit(1);
  }
})();
