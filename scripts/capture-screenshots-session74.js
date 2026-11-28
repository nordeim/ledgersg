// Session-74 screenshot capture — the P38 remediated surfaces.
// Mirrors the repo convention: pixel-verified captures with DOM truths
// asserted per surface (docs/screenshots/256-263_*_session74.png).
// P38 headline: the credit-note InvoiceNow gates + the Celery wiring.
// The feature surface is the credit-note detail page (its "Send via
// InvoiceNow" affordance is now honest — the backend no longer refuses
// what the UI advertises); the standing set follows (the invoices list,
// the banking payments, the reports trial-balance, the ledger, the
// dashboard, the mobile drawer closed/open).
const {
  chromium,
} = require(
  require("path").join(__dirname, "..", "apps", "web", "node_modules", "@playwright", "test")
);
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const BASE = "http://localhost:3000";
const API = "http://127.0.0.1:8000";
const OUT = path.join(__dirname, "..", "docs", "screenshots");

// The credit note's id, resolved through the API once (the newest-first
// list ordering may push CN-00001 past page 1 — the deterministic route).
function resolveCreditNoteId() {
  const loginReq = require("http").request;
  const payload = JSON.stringify({
    email: "demo@ledgersg.sg",
    password: "demo1234pass",
  });
  return new Promise((resolve, reject) => {
    const req = loginReq(
      { host: "127.0.0.1", port: 8000, path: "/api/v1/auth/login/", method: "POST",
        headers: { "Content-Type": "application/json", "Content-Length": payload.length } },
      (res) => {
        let body = "";
        res.on("data", (c) => (body += c));
        res.on("end", () => {
          try { resolve(JSON.parse(body).tokens.access); } catch (e) { reject(e); }
        });
      }
    );
    req.on("error", reject);
    req.write(payload);
    req.end();
  }).then(
    (token) =>
      new Promise((resolve, reject) => {
        const req = loginReq(
          { host: "127.0.0.1", port: 8000, path: "/api/v1/organisations/", method: "GET",
            headers: { Authorization: `Bearer ${token}` } },
          (res) => {
            let body = "";
            res.on("data", (c) => (body += c));
            res.on("end", () => {
              try { resolve({ token, orgId: JSON.parse(body).results[0].id }); } catch (e) { reject(e); }
            });
          }
        );
        req.on("error", reject);
        req.end();
      })
  ).then(
    ({ token, orgId }) =>
      new Promise((resolve, reject) => {
        const req = loginReq(
          { host: "127.0.0.1", port: 8000,
            path: `/api/v1/${orgId}/invoicing/documents/?limit=50`, method: "GET",
            headers: { Authorization: `Bearer ${token}` } },
          (res) => {
            let body = "";
            res.on("data", (c) => (body += c));
            res.on("end", () => {
              try {
                const cn = JSON.parse(body).results.find(
                  (d) => d.document_type === "SALES_CREDIT_NOTE"
                );
                resolve(cn.id);
              } catch (e) { reject(e); }
            });
          }
        );
        req.on("error", reject);
        req.end();
      })
  );
}

const SHOTS = [
  // 256 — the invoices list page 1: the transmitted-documents surface
  // (the credit notes now ride the InvoiceNow workflow the gates own).
  {
    name: "256_invoices_page1_session74",
    url: "/invoices/",
    viewport: [1280, 800],
    truths: [
      ["nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–20 of \d+ rows/],
      ["table", null, null],
    ],
    prevDisabled: true,
  },
  // 257 — the P38 FEATURE surface: the credit-note detail page. The
  // "Send via InvoiceNow" button renders for APPROVED non-quote
  // documents — post-P38 the backend queues what it advertises.
  {
    name: "257_credit_note_detail_session74",
    url: "/invoices/",
    viewport: [1280, 800],
    creditNoteDetail: true,
    truths: [
      ["main", null, /CN-\d+/],
      ["main", null, /credit note/i],
    ],
  },
  // 258 — the banking payments tab (the standing payment surface).
  {
    name: "258_banking_payments_session74",
    url: "/banking/",
    viewport: [1280, 800],
    paymentsTab: true,
    truths: [
      ["[data-testid='payments-list'] nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–\d+ of \d+ rows/],
      ["[data-testid='payments-list']", null, null],
    ],
  },
  // 259 — the reports trial-balance tab (the totals consumer).
  {
    name: "259_reports_trial_balance_session74",
    url: "/reports/",
    viewport: [1280, 800],
    trialBalanceTab: true,
    truths: [
      ["[role='tablist'] [role='tab']", null, /trial balance/i],
      ["table", null, null],
    ],
  },
  // 260 — the ledger page (the standing journal-surface regression).
  {
    name: "260_ledger_lines_session74",
    url: "/ledger/",
    viewport: [1280, 800],
    truths: [
      ["nav[aria-label='Pagination'] p[aria-live='polite']", null, /Showing 1–\d+ of \d+ rows/],
      ["table", null, null],
    ],
  },
  // 261 — the dashboard (the standard post-closure regression).
  {
    name: "261_dashboard_session74",
    url: "/dashboard/",
    viewport: [1280, 800],
    truths: [["h1", null, /command center/i]],
  },
  // 262 — mobile regression: the dashboard with the nav closed.
  {
    name: "262_mobile_dashboard_closed_session74",
    url: "/dashboard/",
    viewport: [375, 812],
    truths: [["aside", "visibility", "hidden"]],
  },
  // 263 — mobile regression: the nav open as the modal overlay.
  {
    name: "263_mobile_nav_open_session74",
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
    console.log(`  capturing ${shot.name}...`);

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

    if (shot.creditNoteDetail) {
      // the deterministic route: the API-resolved credit note's detail page
      const cnId = await resolveCreditNoteId();
      await page.goto(BASE + `/invoices/${cnId}`, { waitUntil: "networkidle" });
      await page.waitForTimeout(1500);
    }

    if (shot.trialBalanceTab) {
      await page.getByRole("tab", { name: /trial balance/i }).click();
      await page.waitForTimeout(1800);
    }
    if (shot.paymentsTab) {
      await page.getByRole("tab", { name: /payments/i }).click();
      await page.waitForTimeout(1500);
    }

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
    results.push({ shot: shot.name, truthsOk, size, md5 });
    await ctx.close();
  }
  await browser.close();

  console.log("\n=== capture summary ===");
  let allOk = true;
  const seen = new Set();
  for (const r of results) {
    const ok = r.truthsOk && r.size > 10000 && !seen.has(r.md5);
    if (!ok) allOk = false;
    seen.add(r.md5);
    console.log(
      `${ok ? "OK  " : "FAIL"} ${r.shot} truths=${r.truthsOk} size=${r.size} md5=${r.md5}`
    );
  }
  console.log(allOk ? "\nALL CAPTURES OK" : "\nCAPTURE FAILURES PRESENT");
  process.exit(allOk ? 0 : 1);
})();
