import { test, expect } from "@playwright/test";

/**
 * LEDGERSG AUTH TESTS (P3/D-5)
 *
 * Coverage:
 * - Login form client-side validation (always runs — backend not required)
 * - Failed-login error surfacing (opt-in: E2E_API_URL pointing at a live
 *   backend, matching the green-by-default philosophy of B-1)
 */

const apiUrl = process.env.E2E_API_URL;

test.describe("Login form", () => {
  test("renders the branded login form with email and password fields", async ({ page }) => {
    await page.goto("/login");

    await expect(page.locator("input[type='email']")).toBeVisible();
    await expect(page.locator("input[type='password']")).toBeVisible();
    await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
  });

  test("native validation blocks an empty submission without a backend call", async ({ page }) => {
    await page.goto("/login");

    // The form uses native required attributes — chromium blocks the
    // submit event itself, so no error banner and no navigation happen.
    await expect(page.locator("input[type='email']")).toHaveAttribute("required");
    await expect(page.locator("input[type='password']")).toHaveAttribute("required");

    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page).toHaveURL(/\/login/);
    // no "Unable to connect" banner => the request was never made (an empty
    // toast region node may exist; only visible error text counts)
    await expect(page.getByText(/unable to connect|invalid email or password/i)).toHaveCount(0);
  });

  test("password field masks input", async ({ page }) => {
    await page.goto("/login");

    await expect(page.locator("input[type='password']")).toHaveAttribute("type", "password");
  });
});

// Opt-in block: needs a live backend on E2E_API_URL (npm run test:e2e:full).
// Green by default: without the backend these tests skip with a reason.
test.describe("Login form (backend required)", () => {
  test.skip(!apiUrl, "requires E2E_API_URL (live backend) — run via npm run test:e2e:full");

  test("a wrong password surfaces the backend error, not a silent failure", async ({ page }) => {
    await page.goto("/login");

    await page.locator("input[type='email']").fill("demo@ledgersg.sg");
    await page.locator("input[type='password']").fill("definitely-wrong-password");
    await page.getByRole("button", { name: /sign in/i }).click();

    // The form surfaces the auth failure (exact copy may evolve; assert an
    // error indication appears and we stay on /login)
    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });
    await expect(
      page
        .locator("[role='alert'], .text-alert, [data-testid='login-error']")
        .first()
    ).toBeVisible({ timeout: 15000 });
  });
});
