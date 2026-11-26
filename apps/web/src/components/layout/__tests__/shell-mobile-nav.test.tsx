/**
 * P12/A-1: mobile-nav overlay a11y floor — the four §9.4 mandatory overlay
 * behaviors (skills/nextjs16-tailwind4): Escape closes, focus moves into the
 * sidebar on open, focus returns to the trigger on close, body scroll locks
 * while open. Plus the Tab-cycle focus trap within the open sidebar.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { act, render, screen } from "@testing-library/react";
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

describe("Shell drawer hardening (P16/FE-M2, FE-L4, FE-L5)", () => {
  afterEach(() => {
    document.body.style.overflow = "";
  });

  it("releases the scroll lock and closes the drawer when the viewport crosses into >=md (FE-M2)", async () => {
    // The pre-P16 lock keyed off sidebarOpen only: with the drawer open
    // at 375px, rotating/resizing past the md breakpoint hid the overlay
    // and the X toggle (both md:hidden) while body overflow stayed
    // hidden — a page with no visible scroll and no visible escape.
    const user = userEvent.setup();

    // A capturing matchMedia mock, installed BEFORE render so the
    // component's effect registers its breakpoint listener with it.
    const listeners: Array<(e: { matches: boolean }) => void> = [];
    const matchMediaMock = vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      addEventListener: (_: string, cb: (e: { matches: boolean }) => void) =>
        listeners.push(cb),
      removeEventListener: () => {},
      addListener: (cb: (e: { matches: boolean }) => void) => listeners.push(cb),
      removeListener: () => {},
    }));
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: matchMediaMock,
    });

    render(
      <Shell>
        <div>content</div>
      </Shell>
    );

    await user.click(getToggle());
    expect(document.body.style.overflow).toBe("hidden");
    expect(listeners.length).toBeGreaterThan(0);

    // The viewport crosses into >=md (rotate/resize).
    await act(async () => {
      for (const cb of [...listeners]) cb({ matches: true });
    });

    // The drawer must close and the scroll lock must release.
    expect(document.body.style.overflow).toBe("");
    const aside = screen.getByRole("complementary");
    expect(aside.className).toContain("invisible");

  });

  it("the open mobile drawer exposes dialog semantics (role=dialog + aria-modal) (FE-L5)", async () => {
    const user = userEvent.setup();
    render(
      <Shell>
        <div>content</div>
      </Shell>
    );

    const aside = screen.getByRole("complementary");
    expect(aside).not.toHaveAttribute("role", "dialog");

    await user.click(getToggle());
    expect(aside).toHaveAttribute("role", "dialog");
    expect(aside).toHaveAttribute("aria-modal", "true");

    await user.click(getToggle());
    expect(aside).not.toHaveAttribute("role", "dialog");
  });

  it("the focus trap covers input fields planted in the drawer (FE-L4)", async () => {
    // The pre-P16 selector only matched a[href] + button — any future
    // form control in the drawer footer would silently escape the trap.
    const user = userEvent.setup();
    render(
      <Shell>
        <div>content</div>
      </Shell>
    );

    await user.click(getToggle());
    // The open drawer exposes dialog semantics (FE-L5) — query that.
    const aside = screen.getByRole("dialog");
    expect(aside).toBeInTheDocument();

    // The trap's focusable set: the drawer's own links/buttons exist.
    // Assert the implementation detail the fix owns: the selector also
    // matches input/select/textarea/[tabindex] — planted probe.
    const probe = document.createElement("input");
    probe.setAttribute("data-testid", "trap-probe");
    aside.appendChild(probe);

    // Focus the probe (the last focusable), then Tab — the trap must
    // wrap to the FIRST focusable, not escape to the body.
    probe.focus();
    expect(document.activeElement).toBe(probe);
    await user.keyboard("{Tab}");
    expect(document.activeElement).not.toBe(document.body);
    expect(aside.contains(document.activeElement)).toBe(true);
  });
});
