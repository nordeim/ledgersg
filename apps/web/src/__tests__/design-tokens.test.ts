/**
 * Design-token contract gates (P17/FE-M1, FE-L2).
 *
 * Tailwind v4 generates utilities ONLY for tokens that exist in the
 * CSS-first @theme block — an unknown utility silently compiles to
 * nothing. The audit found 14 usages of text-success/bg-success across
 * 10 files with no --color-success token: the PAID badge rendered
 * white-on-transparent and every green financial-status semantic
 * silently vanished. These gates read the token source directly (the
 * compiled CSS is a build artifact — the source is the contract).
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const globalsCss = readFileSync(
  resolve(__dirname, "../app/globals.css"),
  "utf-8",
);

function themeToken(name: string): string | undefined {
  const match = globalsCss.match(new RegExp(`--${name}:\\s*([^;]+);`));
  return match?.[1]?.trim();
}

describe("design tokens (P17/FE-M1, FE-L2)", () => {
  it("defines --color-success (the status-green the components already use)", () => {
    const value = themeToken("color-success");
    expect(value, "--color-success must exist in @theme").toBeDefined();
    // The palette header documents it: "Status Only: #00FF94 (Pure neon
    // for badges/icons)" — the token must be that documented value.
    expect(value).toBe("#00FF94");
  });

  it("documents the token in the palette comment block", () => {
    // The palette header already promises the status green; the token
    // living in @theme is what makes the classes real.
    expect(globalsCss).toMatch(/Status Only:\s*#00FF94/i);
  });
});
