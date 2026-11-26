// Session-32 screenshot capture — the P16 remediated surfaces.
// Mirrors the repo convention: pixel-verified captures with DOM truths
// asserted per surface (docs/screenshots/88-95_*_session32.png).
// P16 deltas vs session 30: the open mobile nav now exposes dialog
// semantics (role=dialog + aria-modal — FE-L5), and the dashboard is the
// orgId-first-keyed live surface (FE-H1).
// P17/DOC-M11: self-resolving require — this script runs from the repo
// root, where a bare require("@playwright/test") cannot resolve; resolve it
// from the web app's node_modules (the prod-csp-smoke.js pattern).
const { chromium } = require(
  require("path").join(__dirname, "..", "apps", "web", "node_modules", "@playwright", "test")
);
const fs = require("fs");
const path = require("path");

const BASE = "http://localhost:3000";
const OUT = path.join(__dirname, "..", "docs", "screenshots");
const SHOTS = [
  { name: "88_dashboard_desktop_session32", url: "/dashboard/", viewport: [1280, 800], truths: [["h1", null, /command center/i]] },
  { name: "89_invoices_desktop_session32", url: "/invoices/", viewport: [1280, 800], truths: [["h1", null, /invoices/i]] },
  { name: "90_banking_payments_session32", url: "/banking/", viewport: [1280, 800], truths: [["h1", null, /banking/i]] },
  { name: "91_reports_desktop_session32", url: "/reports/", viewport: [1280, 800], truths: [["h1", null, /reports/i]] },
  { name: "92_settings_desktop_session32", url: "/settings/", viewport: [1280, 800], truths: [["h1", null, /settings/i]] },
  { name: "93_mobile_dashboard_closed_session32", url: "/dashboard/", viewport: [375, 812], truths: [["aside", "visibility", "hidden"]] },
  { name: "94_mobile_nav_open_dialog_session32", url: "/dashboard/", viewport: [375, 812], openNav: true, truths: [["aside", "visibility", "visible"], ["aside", "role", "dialog"]] },
  { name: "95_mobile_ledger_session32", url: "/ledger/", viewport: [375, 812], truths: [["h1", null, /ledger/i]] },
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
    if (shot.openNav) {
      const toggle = page.getByRole("button", { name: /open navigation/i });
      await toggle.click();
      await page.waitForTimeout(400);
    }
    // DOM truths
    let truthsOk = true;
    for (const [sel, prop, expect] of shot.truths) {
      // the shell renders the logo h1 first; the PAGE title is the last h1
      const el = sel === "h1" ? page.locator(sel).last() : page.locator(sel).first();
      if (prop === null) {
        const text = (await el.textContent()) || "";
        if (!expect.test(text)) truthsOk = false;
      } else if (prop === "role") {
        const role = await el.getAttribute("role");
        if (role !== expect) truthsOk = false;
      } else {
        const val = await el.evaluate((n, p) => getComputedStyle(n)[p], prop);
        if (val !== expect) truthsOk = false;
      }
    }
    const file = path.join(OUT, shot.name + ".png");
    await page.screenshot({ path: file, fullPage: false });
    const size = fs.statSync(file).size;
    results.push({ name: shot.name, truthsOk, size });
    await ctx.close();
  }
  await browser.close();
  for (const r of results) {
    console.log(`${r.truthsOk ? "OK  " : "FAIL"} ${r.name} (${(r.size / 1024).toFixed(0)} KB)`);
  }
  if (results.some((r) => !r.truthsOk)) process.exit(1);
})();
