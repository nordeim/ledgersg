import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

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
    process.env.E2E_DEMO_PASSWORD ?? "demo1234pass"
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

  // -------------------------------------------------------------------------
  // P13 additions: the closed-drawer focusability fix (H-2), the overlay
  // z-index hit-target fix (M-1), and an axe scan of the OPEN overlay —
  // the a11y floor locked in the suite instead of only in the live audits.
  // -------------------------------------------------------------------------

  test("P13/H-2: the closed sidebar is visibility-hidden (not tabbable) at 375", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await loginViaUi(page);

    const toggle = getToggle(page);
    await expect(toggle).toHaveAttribute("aria-expanded", "false");

    // The off-canvas drawer must not be focusable: visibility:hidden beats
    // the transform-only off-screen approach (which left ~10 invisible
    // focusables in the tab order before the header).
    const aside = page.locator("aside");
    await expect(aside).toHaveCSS("visibility", "hidden");
    // CSS locator (NOT a role locator): a visibility:hidden element is
    // excluded from the accessibility tree, so getByRole cannot resolve
    // it — which is exactly the behavior this spec pins.
    const firstNavLink = page.locator(
      "aside #main-navigation a[href='/dashboard/']"
    );
    await expect(firstNavLink).toHaveCSS("visibility", "hidden");

    // Opening restores visibility (the animation-friendly flip).
    await toggle.click();
    await expect(aside).toHaveCSS("visibility", "visible");
    await expect(firstNavLink).toHaveCSS("visibility", "visible");
    await page.keyboard.press("Escape");
    await expect(aside).toHaveCSS("visibility", "hidden");
  });

  test("P13/M-1: the X toggle is the real click target while the menu is open", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await loginViaUi(page);

    const toggle = getToggle(page);
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "true");

    // The header (z-50) must paint ABOVE the overlay (z-40): the toggle
    // reports its own box (not covered) and clicking it closes the menu.
    const box = await toggle.boundingBox();
    expect(box).not.toBeNull();
    const atCenter = await page.evaluate(
      ([x, y]) => {
        const el = document.elementFromPoint(x, y);
        return el?.closest("button")?.getAttribute("aria-label") ?? null;
      },
      [box!.x + box!.width / 2, box!.y + box!.height / 2]
    );
    expect(atCenter).toMatch(/close navigation/i);

    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
  });

  test("P13: the open overlay passes an axe accessibility scan", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await loginViaUi(page);

    const toggle = getToggle(page);
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await page.waitForTimeout(400); // let the slide-in finish

    const results = await new AxeBuilder({ page })
      .include("aside")
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    const violations = results.violations.filter(
      (v) => v.id !== "color-contrast" // theme-level, tracked separately
    );
    expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
  });
});
