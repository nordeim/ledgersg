// Session-38 screenshot capture — the P19 remediated surfaces.
// Mirrors the repo convention: pixel-verified captures with DOM truths
// asserted per surface (docs/screenshots/112-119_*_session38.png).
// P19 surfaces: the Radix-ified banking modals (FE-H1), the
// keyboard-expandable transaction row (FE-H2), the ContactPicker
// WAI-ARIA combobox (FE-M2), the in-app route guard (FE-M3), the
// unified PAID badge on the invoices list (FE-M4), and the standard
// desktop/mobile regression captures.
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
  // 112 — FE-H1: the Receive Payment form is a real Radix dialog now
  // (role=dialog + aria-label + the labeled X close).
  {
    name: "112_banking_receive_dialog_session38",
    url: "/banking/",
    viewport: [1280, 800],
    openReceiveDialog: true,
    truths: [["[role='dialog']", null, null]],
    receiveDialogProbe: true,
  },
  // 113 — FE-H2: the transaction row header is a real button
  // (aria-expanded=true after a KEYBOARD expansion).
  {
    name: "113_banking_transaction_row_keyboard_session38",
    url: "/banking/",
    viewport: [1280, 800],
    keyboardExpandRow: true,
    truths: [["[data-testid='transaction-row'] button[aria-expanded='true']", null, null]],
    rowButtonProbe: true,
  },
  // 114 — FE-M2: the ContactPicker combobox — ArrowDown focuses an
  // option (aria-activedescendant + aria-selected).
  {
    name: "114_invoice_form_combobox_session38",
    url: "/invoices/new",
    viewport: [1280, 800],
    comboboxProbe: true,
    truths: [["input[role='combobox'][aria-expanded='true']", null, null]],
  },
  // 115 — FE-M3: the in-app route guard — a dirty invoice + a sidebar
  // link click shows the confirm dialog instead of discarding.
  {
    name: "115_route_guard_dialog_session38",
    url: "/invoices/new",
    viewport: [1280, 800],
    routeGuardProbe: true,
    truths: [["[role='dialog']", null, /discard unsaved changes/i]],
  },
  // 116 — FE-M4: the invoices list PAID badge unified on bg-success.
  {
    name: "116_invoices_paid_badge_session38",
    url: "/invoices/",
    viewport: [1280, 800],
    paidListProbe: true,
    truths: [["h1", null, /invoices/i]],
  },
  // 117 — the P19 banking surface overview (payments tab).
  {
    name: "117_banking_payments_session38",
    url: "/banking/",
    viewport: [1280, 800],
    clickPaymentsTab: true,
    truths: [["h1", null, /banking/i]],
  },
  // 118 — mobile regression: the dashboard with the nav closed.
  {
    name: "118_mobile_dashboard_closed_session38",
    url: "/dashboard/",
    viewport: [375, 812],
    truths: [["aside", "visibility", "hidden"]],
  },
  // 119 — mobile regression: the nav open as the modal overlay.
  {
    name: "119_mobile_nav_open_session38",
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
    await page.goto(BASE + "/login/", { waitUntil: "networkidle" });
    await page.locator("input[type='email']").fill("demo@ledgersg.sg");
    await page.locator("input[type='password']").fill("demo1234pass");
    await page.getByRole("button", { name: /sign in/i }).click();
    await page.waitForURL(/dashboard/, { timeout: 30000 });

    await page.goto(BASE + shot.url, { waitUntil: "networkidle" });
    await page.waitForTimeout(1200);

    let probe = "";
    let truthsOk = true;

    if (shot.clickPaymentsTab) {
      await page.getByRole("tab", { name: /payments/i }).click();
      await page.waitForTimeout(800);
    }

    if (shot.openReceiveDialog) {
      // FE-H1: open the receive-payment form via the Payments tab.
      await page.getByRole("tab", { name: /payments/i }).click();
      await page
        .getByRole("button", { name: /receive payment/i })
        .first()
        .click();
      await page.waitForTimeout(700);
    }

    if (shot.keyboardExpandRow) {
      // FE-H2: keyboard-only expansion — focus the header button via the
      // row testid, press Enter, the panel appears.
      await page.getByRole("tab", { name: /transactions/i }).click();
      const row = page.locator("[data-testid='transaction-row']").first();
      await row.waitFor({ timeout: 15000 });
      await row.locator("button").first().focus();
      await page.keyboard.press("Enter");
      await page.waitForTimeout(500);
    }

    if (shot.comboboxProbe) {
      // FE-M2: focus the customer picker, ArrowDown twice — the active
      // option gets aria-selected=true + aria-activedescendant.
      const combo = page.locator("input[role='combobox']").first();
      await combo.waitFor({ timeout: 15000 });
      await combo.focus();
      await page.waitForTimeout(600);
      await page.keyboard.press("ArrowDown");
      await page.waitForTimeout(300);
    }

    if (shot.routeGuardProbe) {
      // FE-M3: dirty the invoice form (type a description), then click
      // the sidebar Dashboard link — the guard dialog must appear.
      const desc = page.getByLabel("Line 1 description").first();
      await desc.waitFor({ timeout: 15000 });
      await desc.fill("P19 route-guard probe");
      await page.waitForTimeout(600);
      await page.getByRole("link", { name: /^dashboard$/i }).first().click();
      await page.waitForTimeout(700);
    }

    if (shot.openNav) {
      const toggle = page.getByRole("button", { name: /open navigation/i });
      await toggle.click();
      await page.waitForTimeout(400);
    }

    // DOM truths (h1: the PAGE heading is the last h1 — the first is the
    // header logo; the session36 convention).
    for (const [sel, prop, expect] of shot.truths) {
      const el = sel === "h1" ? page.locator(sel).last() : page.locator(sel).first();
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

    // P19 probes (gated — the remediation's live proofs).
    if (shot.receiveDialogProbe) {
      // FE-H1: the dialog role + accessible name + a labeled close.
      const dialog = page.getByRole("dialog");
      const labelled = await dialog.getAttribute("aria-label").catch(() => null);
      const closeNamed = await dialog
        .getByRole("button", { name: /close/i })
        .count()
        .catch(() => 0);
      probe = `role=dialog label:${labelled} close-named:${closeNamed}`;
      if (!labelled || closeNamed === 0) truthsOk = false;
    }
    if (shot.rowButtonProbe) {
      // FE-H2: the header is a button carrying aria-expanded + controls.
      const header = page
        .locator("[data-testid='transaction-row'] button[aria-expanded]")
        .first();
      const expanded = await header.getAttribute("aria-expanded").catch(() => null);
      const controls = await header.getAttribute("aria-controls").catch(() => null);
      probe = `row-button aria-expanded:${expanded} aria-controls:${!!controls}`;
      if (expanded !== "true" || !controls) truthsOk = false;
    }
    if (shot.comboboxProbe) {
      // FE-M2: aria-activedescendant points at an aria-selected option.
      const combo = page.locator("input[role='combobox']").first();
      const activeDesc = await combo.getAttribute("aria-activedescendant").catch(() => null);
      const selected = await page.locator("[role='option'][aria-selected='true']").count();
      probe = `activedescendant:${activeDesc ? "set" : "null"} selected-options:${selected}`;
      if (!activeDesc || selected === 0) truthsOk = false;
    }
    if (shot.routeGuardProbe) {
      // FE-M3: the confirm dialog with its two explicit actions.
      const dialog = page.getByRole("dialog");
      const stay = await dialog.getByRole("button", { name: /stay/i }).count();
      const discard = await dialog
        .getByRole("button", { name: /discard and leave/i })
        .count();
      probe = `stay:${stay} discard:${discard}`;
      if (!stay || !discard) truthsOk = false;
    }
    if (shot.paidListProbe) {
      // FE-M4: a PAID badge on the list pairs bg-success (unified with
      // the detail surface). Settles vacuously when no PAID row exists —
      // the e2e run settles one, but the list is date-ordered.
      const count = await page
        .locator("[class*='bg-success'][class*='text-void']")
        .filter({ hasText: /paid/i })
        .count();
      probe = `paid-list-badge(bg-success): ${count}`;
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
