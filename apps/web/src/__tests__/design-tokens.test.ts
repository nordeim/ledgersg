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
import { beforeAll, describe, expect, it } from "vitest";

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

describe("Tailwind v4 compiled-utility gates (P18/FE-L1)", () => {
  /**
   * The tailwindcss-animate family (animate-in/out, fade-in-0, zoom-in-95,
   * slide-in-from-*, slide-out-to-*) is a v3 PLUGIN vocabulary — in v4 it
   * silently compiles to NOTHING unless the v4-native replacement
   * (tw-animate-css) is imported. The Radix primitives (dialog, select,
   * toast) carry these classes: their enter/exit animations died in the
   * v4 migration. This gate compiles the real source through the repo's
   * own @tailwindcss/postcss pipeline and asserts the utilities exist.
   */
  let compiled: string;

  beforeAll(async () => {
    const { default: postcss } = await import("postcss");
    const { default: tailwind } = await import("@tailwindcss/postcss");
    const { resolve } = await import("node:path");
    const globals = readFileSync(resolve(__dirname, "../app/globals.css"), "utf-8");
    const result = await postcss([tailwind()]).process(
      globals + `\n@source "${resolve(__dirname, "..")}";`,
      { from: resolve(__dirname, "../app/globals.css") }
    );
    compiled = result.css;
  });

  it("imports the v4-native animate vocabulary (tw-animate-css)", async () => {
    const { resolve } = await import("node:path");
    const pkg = JSON.parse(readFileSync(resolve(__dirname, "../../package.json"), "utf-8"));
    expect(pkg.dependencies?.["tw-animate-css"], "the v4-native replacement must be a dependency").toBeDefined();
    expect(globalsCss).toMatch(/@import\s+"tw-animate-css"/);
  });

  it.each([
    "animate-in",
    "animate-out",
    "fade-in-0",
    "fade-out-0",
    "zoom-in-95",
    "zoom-out-95",
    "slide-in-from-top-2",
    "slide-out-to-right-full",
  ])("%s compiles to real CSS (the Radix primitives use it)", (utility: string) => {
    expect(compiled, `the compiled CSS must contain .${utility}`).toContain(`.${utility}`);
  });
});
