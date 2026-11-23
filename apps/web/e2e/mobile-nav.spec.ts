import { test, expect } from "@playwright/test";

/**
 * LEDGERSG MOBILE NAVIGATION TESTS (P12/A-2)
 *
 * The authenticated mobile-nav contract at a 375px viewport: the toggle
 * opens the sidebar overlay, nav links navigate AND auto-close it, Escape
 * closes it (P12/A-1), and the desktop band hides the toggle with the
 * sidebar sticky. Requires E2E_API_URL (npm run test:e2e:full); skips
 * green with a reason otherwise.
 */

const apiUrl = process.env.E2E_API_URL;

test.skip(
  !apiUrl,
  "requires E2E_API_URL (live backend) — run via npm run test:e2e:full"
);

async function loginViaUi(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.locator("input[type='email']").fill(
    process.env.E2E_DEMO_EMAIL ?? "demo@ledgersg.sg"
  );
  await page.locator("input[type='password']").fill(
    process.env.E2E_DEMO_PASSWORD ?? "demo1234"
  );
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20000 });
}

const getToggle = (page: import("@playwright/test").Page) =>
  page.getByRole("button", { name: /open navigation|close navigation/i });

test.describe("Mobile navigation (P12/A-1 + A-2)", () => {
  test("toggle opens the sidebar overlay and Escape closes it", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await loginViaUi(page);

    const toggle = getToggle(page);
    await expect(toggle).toBeVisible();

    // opens
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await expect(
      page.getByRole("navigation", { name: /main navigation/i })
    ).toBeVisible();

    // P12/A-1: Escape closes the open overlay
    await page.keyboard.press("Escape");
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
  });

  test("nav link navigates AND auto-closes the sidebar", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await loginViaUi(page);

    const toggle = getToggle(page);
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "true");

    // exact+scoped: the logo link ("L LEDGERSG") substring-matches 'Ledger'
    // otherwise — strict mode resolves to 2 elements.
    await page
      .getByRole("navigation", { name: /main navigation/i })
      .getByRole("link", { name: "Ledger", exact: true })
      .click();
    await expect(page).toHaveURL(/\/ledger\/?$/, { timeout: 20000 });

    // the sidebar closed itself on navigation
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
  });

  test("desktop band: toggle hidden, sidebar sticky", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await loginViaUi(page);

    await expect(getToggle(page)).toBeHidden();

    const sidebar = page.locator("aside");
    await expect(sidebar).toBeVisible();
    await expect(sidebar).toHaveCSS("position", "sticky");
  });
});
