// Session-40 screenshot capture — the P20 remediated surfaces.
// Mirrors the repo convention: pixel-verified captures with DOM truths
// asserted per surface (docs/screenshots/120-127_*_session40.png).
// P20 surfaces: the invoice-form Notes/Terms accessible names (FE-H1),
// the named back links on the new pages (FE-H2), the ContactPicker blur
// dismissal (FE-M1), the one-h1-per-page shell (FE-L2), the gst-f5-chart
// valid ARIA table (FE-M4), the timezone-safe date render on the invoice
// detail (FE-M7), and the standard desktop/mobile regression captures.
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
  // 120 — FE-H1: the invoice form Notes & Terms textareas are named
  // (label[for] + textarea#id association).
  {
    name: "120_invoice_form_notes_terms_labels_session40",
    url: "/invoices/new",
    viewport: [1280, 800],
    focusNotes: true,
    truths: [["textarea#invoice-notes", null, null], ["textarea#invoice-terms", null, null]],
    notesProbe: true,
  },
  // 121 — FE-H2: the icon-only back link on /invoices/new carries its
  // accessible name.
  {
    name: "121_invoices_new_back_link_session40",
    url: "/invoices/new",
    viewport: [1280, 800],
    truths: [["a[aria-label='Back to invoices']", null, null]],
    backLinkProbe: true,
  },
  // 122 — FE-M1: the ContactPicker dismisses its listbox on Tab-away
  // (the open state captured first, then the dismissal proof).
  {
    name: "122_contact_picker_blur_dismissal_session40",
    url: "/invoices/new",
    viewport: [1280, 800],
    comboboxBlurProbe: true,
    truths: [["input[role='combobox'][aria-expanded='false']", null, null]],
  },
  // 123 — FE-L2: exactly ONE h1 on the dashboard (the sidebar brand is
  // a paragraph now, not a heading).
  {
    name: "123_dashboard_single_h1_session40",
    url: "/dashboard/",
    viewport: [1280, 800],
    singleH1Probe: true,
    truths: [["h1", null, /command center/i]],
  },
  // 124 — FE-M4: the gst-f5-chart data table view has the valid ARIA
  // owned structure (row > columnheader).
  {
    name: "124_gst_chart_aria_table_session40",
    url: "/dashboard/",
    viewport: [1280, 800],
    chartTableProbe: true,
    truths: [["[role='table'][aria-label='GST F5 Return Breakdown'] [role='row'] [role='columnheader']", null, null]],
  },
  // 125 — the desktop invoices list overview (regression; the PAID
  // badges and scope=col headers live here).
  {
    name: "125_invoices_desktop_session40",
    url: "/invoices/",
    viewport: [1280, 800],
    truths: [["th[scope='col']", null, null]],
  },
  // 126 — mobile regression: the dashboard with the nav closed.
  {
    name: "126_mobile_dashboard_closed_session40",
    url: "/dashboard/",
    viewport: [375, 812],
    truths: [["aside", "visibility", "hidden"]],
  },
  // 127 — mobile regression: the nav open as the modal overlay.
  {
    name: "127_mobile_nav_open_session40",
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

    if (shot.openNav) {
      const toggle = page.getByRole("button", { name: /open navigation/i });
      await toggle.click();
      await page.waitForTimeout(400);
    }

    if (shot.focusNotes) {
      // FE-H1: focus + type into the Notes textarea through its label
      // association (getByLabel proves the accessible name).
      const notes = page.getByLabel("Notes", { exact: true });
      await notes.waitFor({ timeout: 15000 });
      await notes.fill("P20 label-association probe");
      await page.waitForTimeout(400);
    }

    if (shot.comboboxBlurProbe) {
      // FE-M1: open the picker (ArrowDown shows the listbox), then Tab
      // away — the listbox must dismiss (aria-expanded=false).
      const combo = page.locator("input[role='combobox']").first();
      await combo.waitFor({ timeout: 15000 });
      await combo.focus();
      await page.waitForTimeout(600);
      await page.keyboard.press("ArrowDown");
      await page.waitForTimeout(400);
      const openBefore = await combo.getAttribute("aria-expanded");
      await page.keyboard.press("Tab");
      await page.waitForTimeout(700);
      const openAfter = await combo.getAttribute("aria-expanded");
      probe = `expanded before-tab:${openBefore} after-tab:${openAfter}`;
      if (openAfter !== "false") truthsOk = false;
    }

    if (shot.chartTableProbe) {
      // FE-M4: flip the chart card into its data-table view.
      const toggle = page.getByRole("button", { name: /show data table/i });
      if ((await toggle.count()) > 0) {
        await toggle.first().click();
        await page.waitForTimeout(500);
      }
    }

    // DOM truths. NOTE (the P20/FE-L2 change): the sidebar brand is no
    // longer an h1, so the page h1 is both first and last — the LAST
    // convention is kept for continuity.
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

    // P20 probes (gated — the remediation's live proofs).
    if (shot.notesProbe) {
      // FE-H1: both textareas resolve BY LABEL (the accessible-name
      // proof) and the label[for] association exists.
      const notesNamed = await page.getByLabel("Notes", { exact: true }).count();
      const termsNamed = await page
        .getByLabel("Terms & Conditions", { exact: true })
        .count();
      const notesFor = await page
        .locator("label[for='invoice-notes']")
        .count();
      const termsFor = await page
        .locator("label[for='invoice-terms']")
        .count();
      probe = `notes-by-label:${notesNamed} terms-by-label:${termsNamed} for-attrs:${notesFor + termsFor}`;
      if (!notesNamed || !termsNamed || notesFor + termsFor < 2) truthsOk = false;
    }
    if (shot.backLinkProbe) {
      // FE-H2: the back link resolves BY NAME on both new pages.
      const back = page.getByRole("link", { name: "Back to invoices" });
      const named = await back.count();
      probe = `back-link-by-name:${named}`;
      if (!named) truthsOk = false;
    }
    if (shot.singleH1Probe) {
      // FE-L2: exactly one h1 (the page's own) — the brand is a <p>.
      const h1Count = await page.locator("h1").count();
      const brandP = await page.locator("p:has-text('LEDGER')").count();
      probe = `h1-count:${h1Count} brand-as-p:${brandP}`;
      if (h1Count !== 1) truthsOk = false;
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
