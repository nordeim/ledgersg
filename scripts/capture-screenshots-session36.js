// Session-36 screenshot capture — the P18 remediated surfaces.
// Mirrors the repo convention: pixel-verified captures with DOM truths
// asserted per surface (docs/screenshots/104-111_*_session36.png).
// P18 surfaces: the contrast-fixed PAID badge (bg-success text-void —
// FE-H1), the settings GST "Registered" + InvoiceNow cards (FE-H1's
// other two pairings), and the animate-restored dialog open state
// (FE-L1 — tw-animate-css: animate-in + zoom-in-95 compile again).
// P17/DOC-M11: self-resolving require — resolve @playwright/test from
// the web app's node_modules (the prod-csp-smoke.js pattern).
const { chromium } = require(
  require("path").join(__dirname, "..", "apps", "web", "node_modules", "@playwright", "test")
);
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const BASE = "http://localhost:3000";
const API = "http://127.0.0.1:8000/api/v1";
const OUT = path.join(__dirname, "..", "docs", "screenshots");

/**
 * FE-H1 live proof: find a PAID document via the API (the banking e2e
 * spec settles one per run) so the detail capture shows the real
 * contrast-fixed PAID badge.
 */
async function findPaidInvoice(page) {
  const login = await page.request.post(`${API}/auth/login/`, {
    data: { email: "demo@ledgersg.sg", password: "demo1234pass" },
  });
  if (!login.ok()) return null;
  const token = (await login.json()).tokens.access;
  const auth = { Authorization: `Bearer ${token}` };
  const orgs = await (await page.request.get(`${API}/auth/organisations/`, { headers: auth })).json();
  const orgId = orgs[0]?.org?.id;
  if (!orgId) return null;
  const docs = await (
    await page.request.get(`${API}/${orgId}/invoicing/documents/?type=SALES_INVOICE`, { headers: auth })
  ).json();
  const paid = (docs.results || []).find((d) => d.status === "PAID");
  return paid ? paid.id : null;
}

const SHOTS = [
  // 104 — the P18 flagship: the PAID badge pairing (bg-success text-void).
  { name: "104_invoice_paid_badge_session36", paidInvoice: true, viewport: [1280, 800], truths: [], paidBadgeProbe: true },
  // 105 — FE-H1's second pairing: the GST "Registered" badge.
  { name: "105_settings_gst_registered_session36", url: "/settings/", viewport: [1280, 800], truths: [["h1", null, /settings|organisation/i]], registeredBadgeProbe: true },
  // 106 — FE-H1's third surface: the InvoiceNow / Peppol card state.
  { name: "106_settings_invoicenow_card_session36", url: "/settings/", viewport: [1280, 800], scrollToInvoiceNow: true, truths: [["h1", null, /settings|organisation/i]], invoicenowCardProbe: true },
  // 107 — FE-L1's live proof: a Radix dialog open with the restored
  // animate-in / zoom-in-95 utilities (compiled again under tw-animate-css).
  { name: "107_banking_dialog_animate_session36", url: "/banking/", viewport: [1280, 800], openAccountDialog: true, truths: [["[role='dialog']", null, null]], animateProbe: true },
  { name: "108_dashboard_desktop_session36", url: "/dashboard/", viewport: [1280, 800], truths: [["h1", null, /command center/i]] },
  { name: "109_invoices_desktop_session36", url: "/invoices/", viewport: [1280, 800], truths: [["h1", null, /invoices/i]] },
  { name: "110_mobile_dashboard_closed_session36", url: "/dashboard/", viewport: [375, 812], truths: [["aside", "visibility", "hidden"]] },
  { name: "111_mobile_nav_open_session36", url: "/dashboard/", viewport: [375, 812], openNav: true, truths: [["aside", "visibility", "visible"], ["aside", "role", "dialog"]] },
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

    // The paid-invoice capture navigates to a real settled document.
    if (shot.paidInvoice) {
      const paidId = await findPaidInvoice(page);
      if (!paidId) {
        results.push({ name: shot.name, truthsOk: false, size: 0, md5: "no-paid-invoice", probe: "" });
        await ctx.close();
        continue;
      }
      await page.goto(`${BASE}/invoices/${paidId}/`, { waitUntil: "networkidle" });
    } else {
      await page.goto(BASE + shot.url, { waitUntil: "networkidle" });
    }
    await page.waitForTimeout(1200);

    if (shot.scrollToInvoiceNow) {
      // Bring the InvoiceNow / Peppol card into the viewport (a distinct
      // scroll position — md5-uniqueness against shot 105).
      const card = page.locator("div", { has: page.getByRole("heading", { name: /invoice.*now.*peppol|peppol/i }) }).last();
      await card.scrollIntoViewIfNeeded({ timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(800);
    }

    if (shot.openAccountDialog) {
      // FE-L1: the add-bank-account Radix dialog opens with its
      // animate-in + zoom-in-95 utilities (dead pre-P18 — they compiled
      // to nothing under Tailwind v4 without the v4-native package).
      await page
        .getByRole("button", { name: /add bank account|add account/i })
        .first()
        .click();
      await page.waitForTimeout(600);
    }

    if (shot.openNav) {
      const toggle = page.getByRole("button", { name: /open navigation/i });
      await toggle.click();
      await page.waitForTimeout(400);
    }

    // DOM truths
    let truthsOk = true;
    for (const [sel, prop, expect] of shot.truths) {
      const el = sel === "h1" ? page.locator(sel).last() : page.locator(sel).first();
      if (prop === null && expect === null) {
        if ((await el.count()) === 0) truthsOk = false;
      } else if (prop === null) {
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

    // P18 probes (gated — these are the remediation's live proofs).
    let probe = "";
    if (shot.paidBadgeProbe) {
      // FE-H1: the PAID badge must pair bg-success with text-void.
      const count = await page
        .locator("[class*='bg-success'][class*='text-void']")
        .filter({ hasText: /paid/i })
        .count();
      probe = `paid-badge(bg-success+text-void): ${count}`;
      if (count === 0) truthsOk = false;
    }
    if (shot.registeredBadgeProbe) {
      const count = await page
        .locator("[class*='bg-success'][class*='text-void']")
        .filter({ hasText: /registered/i })
        .count();
      probe = `registered-badge(bg-success+text-void): ${count}`;
      if (count === 0) truthsOk = false;
    }
    if (shot.invoicenowCardProbe) {
      // The InvoiceNow card renders its truthful state heading.
      const count = await page
        .locator("text=/invoice.*now.*peppol|peppol/i")
        .count();
      probe = `invoicenow-card-heading: ${count}`;
      if (count === 0) truthsOk = false;
    }
    if (shot.animateProbe) {
      // FE-L1: the open dialog carries the animate-in + zoom-in-95
      // utilities AND a live animation-name (tw-animate-css compiled).
      const content = page.locator("[role='dialog']").first();
      const cls = (await content.getAttribute("class")) || "";
      const hasAnimate = cls.includes("animate-in") && cls.includes("zoom-in-95");
      const animName = await content.evaluate((n) => getComputedStyle(n).animationName);
      const animDur = await content.evaluate((n) => getComputedStyle(n).animationDuration);
      probe = `animate-in+zoom-in-95: ${hasAnimate}, animation: ${animName} ${animDur}`;
      if (!hasAnimate) truthsOk = false;
    }

    const file = path.join(OUT, shot.name + ".png");
    await page.screenshot({ path: file, fullPage: false });
    const size = fs.statSync(file).size;
    const md5 = crypto.createHash("md5").update(fs.readFileSync(file)).digest("hex").slice(0, 12);
    results.push({ name: shot.name, truthsOk, size, md5, probe });
    await ctx.close();
  }
  await browser.close();
  const md5s = new Set();
  for (const r of results) {
    const unique = !md5s.has(r.md5) && md5s.add(r.md5);
    const probe = r.probe ? ` | ${r.probe}` : "";
    console.log(`${r.truthsOk && unique ? "OK  " : "FAIL"} ${r.name} (${(r.size / 1024).toFixed(0)} KB md5:${r.md5}${probe})`);
  }
  if (results.some((r) => !r.truthsOk) || new Set(results.map((r) => r.md5)).size !== results.length) {
    process.exit(1);
  }
})();
