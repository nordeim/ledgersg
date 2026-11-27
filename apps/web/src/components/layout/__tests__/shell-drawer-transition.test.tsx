/**
 * P23/FE-M1: the drawer-slide transition contract — Tailwind v4 renders
 * `translate-x-*` via the STANDALONE `translate` CSS property (not
 * `transform: matrix(...)`), so the aside's transition list MUST include
 * `translate` or the 300ms slide never interpolates (the drawer snaps).
 * This is the compiled-CSS gate the 13 prior mobile-nav settlements lacked:
 * every functional probe (state/visibility/focus/scroll) was green while
 * the animation was dead config (Trap 5(b) in
 * docs/Tailwind-V4-Validation-Report.md — computed-style must cover the
 * property the engine actually animates).
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
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

describe("Shell drawer slide transition (P23/FE-M1)", () => {
  it("the closed aside transitions transform, translate AND visibility (the v4 standalone-property contract)", () => {
    render(
      <Shell>
        <div>content</div>
      </Shell>
    );

    // The closed drawer (complementary role while closed — the dialog
    // role only applies while open): its class token carries the
    // transition list plus the positioning contract.
    const aside = screen.getByRole("complementary");

    // THE contract: v4 animates the slide through the standalone
    // `translate` property — a transition list without it compiles to
    // `transition-property: transform,visibility` and the 300ms slide
    // snaps (verified live: duration 0.3s with nothing to interpolate).
    // `transform` stays for matrix-engine robustness; `visibility`
    // stays for the P13/H-2 discrete hide (closing stays visible through
    // the slide-out, opening flips visible immediately).
    expect(aside.className).toContain(
      "transition-[transform,translate,visibility]"
    );

    // The positioning contract the transition animates (unchanged):
    expect(aside.className).toContain("-translate-x-full");
    expect(aside.className).toContain("md:translate-x-0");
    expect(aside.className).toContain("invisible");
    expect(aside.className).toContain("md:visible");
  });
});
