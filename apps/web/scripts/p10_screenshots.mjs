/**
 * P10 (session 20) screenshot capture — the remediated surfaces, through
 * the real UI login path, content-based waits (no blind timeouts).
 *
 * Run by scripts/p10_screenshots.sh with backend + web dev server already
 * up. Writes 53..58_*_session20.png into docs/screenshots/.
 */
import { chromium } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

// apps/web/scripts -> repo docs/screenshots (resolve from THIS file, not
// the CWD — the first run wrote into apps/docs/ by accident).
const OUT = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../../docs/screenshots"
);
const EMAIL = process.env.E2E_DEMO_EMAIL ?? "demo@ledgersg.sg";
const PASSWORD = process.env.E2E_DEMO_PASSWORD ?? "demo1234pass";

if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true });

async function shot(page, name) {
  await page.screenshot({ path: path.join(OUT, name), fullPage: false });
  console.log(`[shot] ${name}`);
}

async function login(page) {
  await page.goto("http://localhost:3000/login");
  await page.locator("input[type='email']").fill(EMAIL);
  await page.locator("input[type='password']").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL(/\/dashboard/, { timeout: 30000 });
}

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();

// 1. The registration page (P10/H-2) — anonymous, straight URL.
await page.goto("http://localhost:3000/register");
await page.getByRole("button", { name: /create account/i }).waitFor({ state: "visible", timeout: 20000 });
await shot(page, "53_register_page_session20.png");

// 2. Log in through the real UI path.
await login(page);

// 3. Contacts page (P10/M-5).
await page.getByRole("link", { name: /^Contacts$/ }).click();
await page.waitForURL(/\/contacts\/?$/, { timeout: 20000 });
await page.getByRole("main").getByRole("heading", { name: /^contacts$/i }).waitFor();
// Content wait: real rows or the truthful empty state.
await page
  .getByTestId("contacts-list")
  .or(page.getByText("No contacts yet."))
  .first()
  .waitFor({ timeout: 20000 });
await shot(page, "54_contacts_page_session20.png");

// 4. Invoice form with the customer picker open (P10/H-1).
await page.getByRole("link", { name: /^Invoices$/ }).click();
await page.waitForURL(/\/invoices\/?$/, { timeout: 20000 });
await page
  .getByRole("main")
  .getByRole("link", { name: /new invoice/i })
  .first()
  .click();
await page.waitForURL(/\/invoices\/new\/?$/, { timeout: 20000 });
await page.getByRole("heading", { name: /new invoice/i }).waitFor({ timeout: 20000 });
const picker = page.getByRole("combobox", { name: /search customer/i });
await picker.click();
// The listbox opens with results (the dev DB carries customers).
await page.getByRole("listbox", { name: /customer results/i }).waitFor({ timeout: 15000 });
await shot(page, "55_invoice_contact_picker_session20.png");

// 5. Reports GST F5 tab (P10/H-3) — create the return periods through the
// tab's own affordance, then open the boxes panel (the F5 view).
await page.getByRole("link", { name: /^Reports$/ }).click();
await page.waitForURL(/\/reports\/?$/, { timeout: 20000 });
await page.getByRole("tab", { name: /gst f5/i }).click();
await page
  .getByText(/GST F5 Returns/i)
  .first()
  .waitFor({ timeout: 20000 });

const periodsButton = page.getByRole("button", { name: /create return periods/i });
if (await periodsButton.isEnabled()) {
  const hasPeriods = await page.getByRole("table").count();
  if (hasPeriods === 0) {
    await periodsButton.click();
    await page.getByRole("dialog").waitFor({ timeout: 10000 });
    await page.getByLabel(/period start/i).fill("2026-01-01");
    await page.getByRole("button", { name: /create periods/i }).click();
    await page.getByRole("dialog").waitFor({ state: "hidden", timeout: 20000 });
  }
}
// The returns table (with the deadline banner above it).
await page.getByRole("table").first().waitFor({ timeout: 20000 });
// Open the boxes panel on the first row.
await page.getByRole("button", { name: /view boxes/i }).first().click();
await page.getByText(/box 1/i).first().waitFor({ timeout: 20000 });
await shot(page, "56_gst_f5_boxes_session20.png");

// 6. Settings page (P10/M-8..M-10): fiscal, change-password, InvoiceNow.
await page.getByRole("link", { name: /^Settings$/ }).click();
await page.waitForURL(/\/settings\/?$/, { timeout: 20000 });
await page.getByText(/change password/i).first().waitFor({ timeout: 20000 });
await page.getByText(/invoicenow/i).first().waitFor({ timeout: 20000 });
await page.screenshot({
  path: path.join(OUT, "57_settings_cards_session20.png"),
  fullPage: true,
});
console.log("[shot] 57_settings_cards_session20.png");

// 7. Bank-account edit dialog (P10/M-6).
await page.getByRole("link", { name: /^Banking$/ }).click();
await page.waitForURL(/\/banking\/?$/, { timeout: 20000 });
await page.getByRole("tab", { name: /^accounts$/i }).click();
// The accounts grid: the per-card Edit button (Task 9). Content wait:
// at least one Edit button exists.
const editButton = page.getByRole("button", { name: /^edit /i }).first();
await editButton.waitFor({ timeout: 20000 });
await editButton.click();
await page.getByRole("dialog").waitFor({ timeout: 10000 });
await page.getByText(/edit bank account/i).first().waitFor({ timeout: 10000 });
await shot(page, "58_bank_account_edit_session20.png");

await browser.close();
console.log("[shot] done: 6 screenshots");
