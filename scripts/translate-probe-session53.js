#!/usr/bin/env node
/* The dedicated Tailwind v4 `translate` property live probe (the P23 class
 * of defect, re-settled on the P27 tree — session 53): opens the mobile
 * drawer at 375px and samples the computed `translate` mid-flight to prove
 * the 300ms slide INTERPOLATES (Tailwind v4 animates translate-x-* through
 * the standalone `translate` CSS property, not `transform`), plus the
 * transition-property contract and the Escape close. */
const path = require("path");
const { chromium } = require(path.join(
  __dirname, "..", "apps", "web", "node_modules", "@playwright", "test"
));

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 375, height: 700 } });
  await page.goto("http://localhost:3000/login", { waitUntil: "networkidle" });

  // Login (the documented e2e credentials)
  await page.fill("input[type='email']", "demo@ledgersg.sg");
  await page.fill("input[type='password']", "demo1234pass");
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL("**/dashboard**", { timeout: 20000 });

  const toggle = page.getByRole("button", { name: /open navigation|close navigation/i });
  await toggle.waitFor({ state: "visible", timeout: 10000 });

  // Closed contract
  const closed = await page.evaluate(() => {
    const aside = document.querySelector("aside");
    const cs = getComputedStyle(aside);
    return { translate: cs.translate, visibility: cs.visibility };
  });
  console.log("closed:", JSON.stringify(closed));

  // Click open and sample mid-flight
  await toggle.click();
  const samples = [];
  for (let i = 0; i < 12; i++) {
    const s = await page.evaluate(() => {
      const aside = document.querySelector("aside");
      return {
        translate: getComputedStyle(aside).translate,
        visibility: getComputedStyle(aside).visibility,
        role: aside.getAttribute("role"),
      };
    });
    samples.push(s.translate);
    await page.waitForTimeout(40);
  }
  const mids = samples.filter((v) => v && v !== "none" && !v.startsWith("-100%") && v !== "0px");
  console.log("samples:", JSON.stringify(samples.slice(0, 10)));
  console.log("mid-flight count:", mids.length);

  // Open contract + transition property
  const open = await page.evaluate(() => {
    const aside = document.querySelector("aside");
    const cs = getComputedStyle(aside);
    return { translate: cs.translate, visibility: cs.visibility, role: aside.getAttribute("role"), tp: cs.transitionProperty };
  });
  console.log("open:", JSON.stringify(open));

  // Escape closes
  await page.keyboard.press("Escape");
  await page.waitForTimeout(400);
  const afterEsc = await page.evaluate(() => {
    const aside = document.querySelector("aside");
    return { translate: getComputedStyle(aside).translate, visibility: getComputedStyle(aside).visibility };
  });
  console.log("afterEscape:", JSON.stringify(afterEsc));

  const pass =
    mids.length >= 3 &&
    open.tp.includes("translate") &&
    (afterEsc.visibility === "hidden" || (afterEsc.translate || "").startsWith("-100%"));
  console.log(pass ? "PROBE PASS — the slide interpolates; translate in transitionProperty; Escape closes" : "PROBE FAIL");
  await browser.close();
  process.exit(pass ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(1); });
