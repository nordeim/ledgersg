// Mobile-nav live verification probe (session 29)
// Verifies the P12/P13 contract at 375/800/1280 + the documented v4 trap sweep.
// P17/DOC-M11: self-resolving require — this script runs from the repo root,
// where a bare require("@playwright/test") cannot resolve; resolve it from
// the web app's node_modules (the prod-csp-smoke.js pattern).
const { chromium } = require(
  require("path").join(__dirname, "..", "apps", "web", "node_modules", "@playwright", "test")
);
const BASE = "http://localhost:3000";

(async () => {
  const browser = await chromium.launch();
  const results = [];
  const check = (name, ok, detail = "") => results.push({ name, ok, detail });

  for (const [w, h, label] of [[375, 812, "mobile"], [800, 1024, "tablet"], [1280, 800, "desktop"]]) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h } });
    const page = await ctx.newPage();
    const errors = [];
    page.on("console", (m) => { if (m.type() === "error") errors.push(m.text().slice(0, 80)); });
    // Session-30 fix: the shell (with the nav aside) renders on the
    // DASHBOARD — log in through the real UI first (the login page has no
    // sidebar; the pre-P14 probe asserted against nothing).
    await page.goto(BASE + "/login/", { waitUntil: "networkidle" });
    await page.locator("input[type='email']").fill("demo@ledgersg.sg");
    await page.locator("input[type='password']").fill("demo1234pass");
    await page.getByRole("button", { name: /sign in/i }).click();
    await page.waitForURL(/dashboard/, { timeout: 30000 });
    await page.waitForTimeout(500);

    if (label === "mobile") {
      // toggle visible + operable
      const toggle = page.getByRole("button", { name: /open navigation/i });
      check(`[${label}] toggle visible`, await toggle.isVisible());
      // closed aside is invisible (P13/H-2)
      const aside = page.locator("aside").first();
      const vis = await aside.evaluate((el) => getComputedStyle(el).visibility);
      check(`[${label}] closed aside visibility:hidden`, vis === "hidden", `got=${vis}`);
      // open
      await toggle.click();
      await page.waitForTimeout(300);
      const visOpen = await aside.evaluate((el) => getComputedStyle(el).visibility);
      check(`[${label}] open aside visible`, visOpen === "visible", `got=${visOpen}`);
      // overlay present, z-40; header z-50 above
      const overlay = page.locator("div.fixed.inset-0.z-40").first();
      check(`[${label}] overlay present`, await overlay.count() > 0);
      // X toggle is the hit target (P13/M-1)
      const closeBtn = page.getByRole("button", { name: /close navigation/i });
      const hit = await closeBtn.evaluate((el) => {
        const r = el.getBoundingClientRect();
        const topEl = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
        return topEl === el || el.contains(topEl);
      });
      check(`[${label}] X toggle is real hit target`, hit);
      await closeBtn.click();
      // P13/H-2's transition-[transform,visibility] keeps visibility:visible
      // THROUGH the slide-out (visibility is discretely-animatable — it flips
      // at the END while closing). Poll until the transition completes
      // instead of a fixed 300ms (the session-29 timing lesson).
      let visClosed = "visible";
      for (let i = 0; i < 20; i++) {
        await page.waitForTimeout(100);
        visClosed = await aside.evaluate((el) => getComputedStyle(el).visibility);
        if (visClosed === "hidden") break;
      }
      check(`[${label}] closed again after X`, visClosed === "hidden", `got=${visClosed}`);
      // horizontal overflow check
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
      check(`[${label}] no horizontal overflow`, !overflow);
    } else {
      const toggle = page.getByRole("button", { name: /open navigation/i });
      check(`[${label}] toggle hidden`, !(await toggle.isVisible()));
      const aside = page.locator("aside").first();
      const vis = await aside.evaluate((el) => getComputedStyle(el).visibility);
      check(`[${label}] aside visible`, vis === "visible", `got=${vis}`);
      const pos = await aside.evaluate((el) => getComputedStyle(el).position);
      check(`[${label}] aside sticky`, pos === "sticky", `got=${pos}`);
    }
    // console errors: only the documented anonymous /auth/me 401 class
    const realErrors = errors.filter((e) => !e.includes("auth/me") && !e.includes("401") && !e.includes("Failed to load resource"));
    check(`[${label}] no unexpected console errors`, realErrors.length === 0, realErrors.join(" | ").slice(0, 120));
    await ctx.close();
  }

  // v4 trap sweep on the login surface (space-y children carry no explicit margins)
  const page = await browser.newPage({ viewport: { width: 375, height: 812 } });
  await page.goto(BASE + "/login/", { waitUntil: "networkidle" });
  const trap = await page.evaluate(() => {
    const out = { spaceyChildren: [] };
    for (const el of document.querySelectorAll("[class*='space-y']")) {
      for (const child of el.children) {
        const cs = getComputedStyle(child);
        if (cs.marginTop !== "0px" || (cs.marginBottom !== "0px" && !el.className.includes("space-y")))
          out.spaceyChildren.push({ cls: child.className.slice(0, 40), mt: cs.marginTop, mb: cs.marginBottom });
      }
    }
    return out;
  });
  check("[v4] space-y children carry no explicit margins (nav trap)", trap.spaceyChildren.length === 0, JSON.stringify(trap.spaceyChildren).slice(0, 200));

  await browser.close();
  let fails = 0;
  for (const r of results) { if (!r.ok) fails++; console.log(`${r.ok ? "PASS" : "FAIL"} ${r.name}${r.detail ? " — " + r.detail : ""}`); }
  console.log(`\n${results.length - fails}/${results.length} passed`);
  process.exit(fails ? 1 : 0);
})();
