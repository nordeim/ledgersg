/**
 * P11 screenshot capture (session 23).
 *
 * Drives the real frontend dev server (localhost:3000) as a user, walks the
 * P11 remediated surfaces, and saves PNG captures under docs/screenshots/
 * following the repo convention (<n>_<surface>_session<N>.png).
 *
 * Run from apps/web with both dev servers up and the bootstrap activity in
 * place (docs/DEPLOYMENT.md "Live gate bootstrap"):
 *
 *   node scripts/p11_screenshots.mjs
 *
 * Requires: frontend dev server on :3000, backend on :8000, the demo user
 * (demo@ledgersg.sg / demo1234 per the deployment bootstrap).
 */

import { chromium } from "playwright";

const WEB = "http://localhost:3000";
const SHOTS = "../../docs/screenshots";
const EMAIL = process.env.E2E_DEMO_EMAIL ?? "demo@ledgersg.sg";
const PASSWORD = process.env.E2E_DEMO_PASSWORD ?? "demo1234";

const targets = [
  // [file, path, comment]
  ["59_dashboard_gst_truth_session23.png", "/dashboard",
   "Dashboard — gst_payable truth (H-4), revenue chart (M-7), single prefixes (L-2)"],
  ["60_contacts_list_session23.png", "/contacts",
   "Contacts list — Peppol badge gates on peppol_id, permission-gated actions (L-1)"],
  ["62_invoices_list_session23.png", "/invoices",
   "Documents — approved invoice rows"],
  ["63_reports_gst_f5_session23.png", "/reports",
   "Reports — GST F5 tab: box labels truth (H-2), computed boxes"],
  ["64_ledger_reversed_cn_session23.png", "/ledger",
   "Journal — the credit note entry posts reversed lines (C-1)"],
  ["65_settings_profile_session23.png", "/settings",
   "Settings — org profile card (M-5 typed PATCH serializer)"],
];

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();

const log = (...a) => console.log("[shot]", ...a);

// --- login through the real UI -------------------------------------------
await page.goto(`${WEB}/login`, { waitUntil: "networkidle" });
await page.locator("input[type='email']").fill(EMAIL);
await page.locator("input[type='password']").fill(PASSWORD);
await page.getByRole("button", { name: /sign in|log in/i }).click();
await page.waitForURL(/dashboard/, { timeout: 30000 });
await page.waitForLoadState("networkidle");
log("logged in ->", page.url());

for (const [file, path, comment] of targets) {
  await page.goto(`${WEB}${path}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(1200); // let charts/panels settle

  if (path === "/reports") {
    // open the GST F5 tab
    const tab = page.getByRole("tab", { name: /GST F5/i });
    if (await tab.count()) {
      await tab.click();
      await page.waitForTimeout(800);
      // expand the computed boxes for the current return
      const view = page.getByRole("button", { name: /view boxes/i }).first();
      if (await view.count()) {
        await view.click();
        await page.waitForTimeout(900);
      }
    }
  }

  await page.screenshot({ path: `${SHOTS}/${file}`, fullPage: false });
  log("saved", file, "—", comment);
}

// --- contacts edit dialog (prefill proof, H-1/M-3/M-4) --------------------
await page.goto(`${WEB}/contacts`, { waitUntil: "networkidle" });
await page.waitForTimeout(800);
const editBtn = page.getByRole("button", { name: /^Edit /i }).first();
if (await editBtn.count()) {
  await editBtn.click();
  await page.waitForTimeout(1500); // detail fetch + prefill
  await page.screenshot({
    path: `${SHOTS}/61_contacts_edit_prefill_session23.png`,
  });
  log("saved 61_contacts_edit_prefill_session23.png — Edit dialog prefilled from DETAIL (H-1), GST reg number field (M-4)");
} else {
  log("WARN: contacts edit button not found");
}

await browser.close();
console.log("DONE");
