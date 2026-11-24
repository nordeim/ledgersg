/**
 * P12/A-1: mobile-nav overlay a11y floor — the four §9.4 mandatory overlay
 * behaviors (skills/nextjs16-tailwind4): Escape closes, focus moves into the
 * sidebar on open, focus returns to the trigger on close, body scroll locks
 * while open. Plus the Tab-cycle focus trap within the open sidebar.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Shell } from "../shell";

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({
    user: { full_name: "Demo User", email: "demo@ledgersg.sg" },
    organisations: [],
    currentOrg: null,
    switchOrg: vi.fn(),
    logout: vi.fn(),
  }),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

const getToggle = () =>
  screen.getByRole("button", { name: /open navigation|close navigation/i });

describe("Shell mobile navigation overlay (P12/A-1)", () => {
  afterEach(() => {
    document.body.style.overflow = "";
  });

  it("opens on toggle click and locks body scroll while open", async () => {
    const user = userEvent.setup();
    render(
      <Shell>
        <div>content</div>
      </Shell>
    );

    expect(document.body.style.overflow).toBe("");
    await user.click(getToggle());

    expect(getToggle()).toHaveAttribute("aria-expanded", "true");
    expect(document.body.style.overflow).toBe("hidden");
  });

  it("moves focus into the sidebar when the menu opens", async () => {
    const user = userEvent.setup();
    render(
      <Shell>
        <div>content</div>
      </Shell>
    );

    await user.click(getToggle());

    // the first navigation link receives focus
    expect(document.activeElement).toBe(
      screen.getByRole("link", { name: "Dashboard" })
    );
  });

  it("Escape closes the open menu", async () => {
    const user = userEvent.setup();
    render(
      <Shell>
        <div>content</div>
      </Shell>
    );

    await user.click(getToggle());
    expect(getToggle()).toHaveAttribute("aria-expanded", "true");

    await user.keyboard("{Escape}");

    expect(getToggle()).toHaveAttribute("aria-expanded", "false");
  });

  it("returns focus to the toggle and unlocks scroll on close", async () => {
    const user = userEvent.setup();
    render(
      <Shell>
        <div>content</div>
      </Shell>
    );

    await user.click(getToggle());
    expect(document.body.style.overflow).toBe("hidden");

    await user.keyboard("{Escape}");

    expect(getToggle()).toHaveAttribute("aria-expanded", "false");
    expect(getToggle()).toHaveFocus();
    expect(document.body.style.overflow).toBe("");
  });

  it("overlay click closes the menu (regression guard)", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <Shell>
        <div>content</div>
      </Shell>
    );

    await user.click(getToggle());
    const overlay = container.querySelector("div.fixed.inset-0");
    expect(overlay).not.toBeNull();

    await user.click(overlay as HTMLElement);

    expect(getToggle()).toHaveAttribute("aria-expanded", "false");
    expect(document.body.style.overflow).toBe("");
  });

  it("traps Tab within the sidebar while the menu is open", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <Shell>
        <div>content</div>
      </Shell>
    );

    await user.click(getToggle());

    const aside = container.querySelector("aside");
    expect(aside).not.toBeNull();
    const focusables = (aside as HTMLElement).querySelectorAll<HTMLElement>(
      "a[href], button:not([disabled])"
    );
    expect(focusables.length).toBeGreaterThan(1);
    const first = focusables[0];
    const last = focusables[focusables.length - 1];

    // Tab from the last focusable wraps to the first
    last.focus();
    await user.tab();
    expect(document.activeElement).toBe(first);

    // Shift+Tab from the first wraps to the last
    first.focus();
    await user.tab({ shift: true });
    expect(document.activeElement).toBe(last);
  });

  it("re-opens after close (no stuck state)", async () => {
    const user = userEvent.setup();
    render(
      <Shell>
        <div>content</div>
      </Shell>
    );

    await user.click(getToggle());
    await user.keyboard("{Escape}");
    expect(getToggle()).toHaveAttribute("aria-expanded", "false");

    await user.click(getToggle());
    expect(getToggle()).toHaveAttribute("aria-expanded", "true");
    expect(document.body.style.overflow).toBe("hidden");

    await user.keyboard("{Escape}");
  });

  // -------------------------------------------------------------------------
  // P13/H-2: the CLOSED off-canvas sidebar must not be keyboard-focusable.
  // A transform only moves the element off-screen — the ~10 focusables
  // (logo, 8 nav links, logout) stayed in the tab order at mobile width,
  // before the header toggle (WCAG 2.4.3/2.4.7). visibility:hidden removes
  // elements from the tab order and the a11y tree; the transition covers
  // it so the slide animation still renders.
  // -------------------------------------------------------------------------
  it("the closed sidebar is visibility-hidden below md (not tabbable)", async () => {
    const { container } = render(
      <Shell>
        <div>content</div>
      </Shell>
    );

    const aside = container.querySelector("aside");
    expect(aside).not.toBeNull();
    expect(getToggle()).toHaveAttribute("aria-expanded", "false");
    expect((aside as HTMLElement).className).toContain("invisible");
    // the md band restores visibility (the sticky desktop sidebar)
    expect((aside as HTMLElement).className).toContain("md:visible");
  });

  it("the open sidebar is visible (the class flips with the menu)", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <Shell>
        <div>content</div>
      </Shell>
    );

    await user.click(getToggle());

    const aside = container.querySelector("aside");
    expect(aside).not.toBeNull();
    expect((aside as HTMLElement).className).not.toContain("invisible");
  });
});
