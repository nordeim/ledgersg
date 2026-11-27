/**
 * P17/FE-L4: org-selector dropdown a11y — the Radix menu contract.
 *
 * The audit found the footer org switcher had no aria-expanded /
 * aria-haspopup on the trigger, no Escape/outside-click close and no
 * arrow-key navigation (a keyboard or screen-reader user cannot operate
 * it). These gates pin the menu contract: trigger semantics, Escape
 * close with focus return, outside-click close, keyboard open, and
 * arrow-key movement with wrap-around + selection.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Shell } from "../shell";

const mockSwitchOrg = vi.fn();

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({
    user: { full_name: "Demo User", email: "demo@ledgersg.sg" },
    organisations: [
      { org: { id: "org-1", name: "Alpha Pte Ltd" }, role: "OWNER" },
      { org: { id: "org-2", name: "Beta Pte Ltd" }, role: "MEMBER" },
      { org: { id: "org-3", name: "Gamma Holdings" }, role: "MEMBER" },
    ],
    currentOrg: { id: "org-1", name: "Alpha Pte Ltd" },
    switchOrg: mockSwitchOrg,
    logout: vi.fn(),
  }),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

const getTrigger = () =>
  screen.getByRole("button", { name: /switch organisation/i });

describe("Shell org-selector menu (P17/FE-L4)", () => {
  beforeEach(() => {
    mockSwitchOrg.mockClear();
  });

  it("trigger exposes the menu contract: aria-haspopup, aria-expanded, aria-controls", () => {
    render(
      <Shell>
        <div>content</div>
      </Shell>
    );

    const trigger = getTrigger();
    expect(trigger).toHaveAttribute("aria-haspopup", "menu");
    expect(trigger).toHaveAttribute("aria-expanded", "false");

    const menuId = trigger.getAttribute("aria-controls");
    expect(menuId).toBeTruthy();
    // The controlled menu exists (hidden semantics are CSS-only).
    expect(document.getElementById(menuId!)).not.toBeNull();
    expect(document.getElementById(menuId!)).toHaveAttribute("role", "menu");
  });

  it("click opens the menu and focus lands on the current organisation item", async () => {
    const user = userEvent.setup();
    render(
      <Shell>
        <div>content</div>
      </Shell>
    );

    await user.click(getTrigger());
    expect(getTrigger()).toHaveAttribute("aria-expanded", "true");

    const current = screen.getByRole("menuitemradio", {
      name: /Alpha Pte Ltd/,
    });
    expect(current).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("menuitemradio", { name: /Beta Pte Ltd/ })).toHaveAttribute("aria-checked", "false");
    expect(document.activeElement).toBe(current);
  });

  it("Escape closes the menu and returns focus to the trigger", async () => {
    const user = userEvent.setup();
    render(
      <Shell>
        <div>content</div>
      </Shell>
    );

    await user.click(getTrigger());
    await user.keyboard("{Escape}");

    expect(getTrigger()).toHaveAttribute("aria-expanded", "false");
    expect(document.activeElement).toBe(getTrigger());
  });

  it("clicking outside closes the menu", async () => {
    const user = userEvent.setup();
    render(
      <Shell>
        <main>
          <h1>Dashboard content</h1>
        </main>
      </Shell>
    );

    await user.click(getTrigger());
    expect(getTrigger()).toHaveAttribute("aria-expanded", "true");

    await user.click(screen.getByRole("heading", { name: "Dashboard content" }));
    expect(getTrigger()).toHaveAttribute("aria-expanded", "false");
  });

  it("ArrowDown on the closed trigger opens the menu", async () => {
    const user = userEvent.setup();
    render(
      <Shell>
        <div>content</div>
      </Shell>
    );

    getTrigger().focus();
    await user.keyboard("{ArrowDown}");

    expect(getTrigger()).toHaveAttribute("aria-expanded", "true");
  });

  it("arrow keys move between items with wrap-around; Enter selects and closes", async () => {
    const user = userEvent.setup();
    render(
      <Shell>
        <div>content</div>
      </Shell>
    );

    await user.click(getTrigger());
    // Focus starts on the current item (org-1 / Alpha).

    // Down twice: Alpha -> Beta -> Gamma
    await user.keyboard("{ArrowDown}");
    expect(document.activeElement).toHaveTextContent("Beta Pte Ltd");
    await user.keyboard("{ArrowDown}");
    expect(document.activeElement).toHaveTextContent("Gamma Holdings");

    // Wrap-around: Down from the last returns to the first.
    await user.keyboard("{ArrowDown}");
    expect(document.activeElement).toHaveTextContent("Alpha Pte Ltd");

    // Up from the first wraps to the last.
    await user.keyboard("{ArrowUp}");
    expect(document.activeElement).toHaveTextContent("Gamma Holdings");

    // Enter selects the focused item, closes the menu and switches org.
    await user.keyboard("{Enter}");
    expect(getTrigger()).toHaveAttribute("aria-expanded", "false");
    expect(mockSwitchOrg).toHaveBeenCalledWith("org-3");
  });
});

describe("Shell nested Escape (P18/FE-M1)", () => {
  beforeEach(() => {
    mockSwitchOrg.mockClear();
  });

  it("with drawer + org menu open, the first Escape closes only the menu; the second closes the drawer", async () => {
    const user = userEvent.setup();
    render(
      <Shell>
        <div>content</div>
      </Shell>
    );

    // Open the mobile drawer (the nav toggle is md:hidden).
    const navToggle = screen.getByRole("button", { name: /open navigation/i });
    await user.click(navToggle);

    // Open the org menu inside the drawer.
    await user.click(getTrigger());
    expect(getTrigger()).toHaveAttribute("aria-expanded", "true");

    // First Escape: the menu consumes it — the drawer stays open and
    // focus returns to the (still visible) trigger.
    await user.keyboard("{Escape}");
    expect(getTrigger()).toHaveAttribute("aria-expanded", "false");
    expect(navToggle).toHaveAttribute("aria-expanded", "true");
    expect(document.activeElement).toBe(getTrigger());

    // Second Escape: the drawer closes.
    await user.keyboard("{Escape}");
    expect(navToggle).toHaveAttribute("aria-expanded", "false");
  });
});
