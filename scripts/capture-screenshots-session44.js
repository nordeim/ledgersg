// Session-44 screenshot capture — the P23 remediated surfaces.
// Mirrors the repo convention: pixel-verified captures with DOM truths
// asserted per surface (docs/screenshots/136-143_*_session44.png).
// P23 surfaces: the drawer-slide transition truth (FE-M1 — the mid-flight
// slide captured ~160ms after the toggle click, with the computed
// transitionProperty asserting `translate` present; the closed/open mobile
// regression captures), the standard desktop band, and the P21-surface
// regressions (the loader live region, the org selector, invoices,
// settings) re-probed on the remediated stack.
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
  // 136 — mobile regression: the dashboard with the nav closed.
  {
    name: "136_mobile_dashboard_closed_session44",
    url: "/dashboard/",
    viewport: [375, 812],
    truths: [["aside", "visibility", "hidden"]],
  },
  // 137 — mobile regression: the nav open as the modal overlay.
  {
    name: "137_mobile_nav_open_session44",
    url: "/dashboard/",
    viewport: [375, 812],
    openNav: true,
    truths: [["aside", "visibility", "visible"], ["aside", "role", "dialog"]],
  },
  // 138 — FE-M1, the P23 headline: the drawer MID-SLIDE — the transition
  // contract asserting `translate` in the computed transitionProperty,
  // captured ~160ms after the toggle click so the interpolated position
  // is on screen (pre-P23 the drawer snapped: no mid-flight frame
  // existed).
  {
    name: "138_drawer_mid_slide_session44",
    url: "/dashboard/",
    viewport: [375, 812],
    midSlide: true,
    truths: [["aside", "visibility", "visible"]],
    transitionProbe: true,
  },
  // 139 — the desktop band: toggle hidden, the sidebar sticky.
  {
    name: "139_desktop_band_session44",
    url: "/dashboard/",
    viewport: [1280, 800],
    truths: [["aside", "position", "sticky"]],
  },
  // 140 — the P21-surface regression: the banking loader live region
  // (delay the bank-accounts response so the skeleton stays on screen).
  {
    name: "140_banking_loader_live_region_session44",
    url: "/banking/",
    viewport: [1280, 800],
    delayAccounts: true,
    truths: [["[data-testid='accounts-loading-skeleton'][role='status']", null, null]],
  },
  // 141 — the P21-surface regression: the org selector reading the
  // unified {results, count} envelope (the menu lists the demo org).
  {
    name: "141_org_selector_envelope_session44",
    url: "/dashboard/",
    viewport: [1280, 800],
    orgMenu: true,
    truths: [["[role='menuitemradio']", null, /ledger demo/i]],
  },
  // 142 — surface regression: the invoices list with real rows.
  {
    name: "142_invoices_desktop_session44",
    url: "/invoices/",
    viewport: [1280, 800],
    truths: [["table", null, null]],
  },
  // 143 — surface regression: the settings page renders its h1 + the
  // org-management surface (the page is card-based, no table).
  {
    name: "143_settings_desktop_session44",
    url: "/settings/",
    viewport: [1280, 800],
    truths: [["h1", null, /^settings$/i]],
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

    // The loader shot: delay the bank-accounts response so the skeleton
    // stays visible during the capture.
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

    const waitUntil = shot.delayAccounts ? "domcontentloaded" : "networkidle";
    await page.goto(BASE + shot.url, { waitUntil });
    await page.waitForTimeout(shot.delayAccounts ? 1500 : 1200);

    let probe = "";
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

    // FE-M1: open the drawer and capture it MID-SLIDE (~160ms in, the
    // interpolated position is on screen) — the pre-P23 drawer had no
    // mid-flight frame (it snapped).
    if (shot.midSlide) {
      const toggle = page.getByRole("button", { name: /open navigation/i });
      await toggle.click();
      await page.waitForTimeout(160);
    }

    // FE-M1: the transition contract — the computed transitionProperty
    // must carry `translate` (the v4 standalone slide property) and
    // `visibility` (the P13/H-2 discrete hide).
    if (shot.transitionProbe) {
      const tp = await page.locator("aside").evaluate(
        (el) => getComputedStyle(el).transitionProperty
      );
      const midTranslate = await page.locator("aside").evaluate(
        (el) => getComputedStyle(el).translate
      );
      probe = `transitionProperty:${tp} mid-translate:${midTranslate}`;
      if (!tp.includes("translate") || !tp.includes("visibility")) {
        truthsOk = false;
        console.log(`    [truth-fail] transitionProperty=${tp}`);
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
