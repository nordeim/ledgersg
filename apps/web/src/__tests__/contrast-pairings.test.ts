/**
 * P18 contrast-contract gates (FE-H1, FE-M2, FE-M3).
 *
 * The P17/FE-M1 token fix made `bg-success` compile — and immediately
 * exposed the pairing debt: three badges paired the neon-green with
 * WHITE text (1.33:1, WCAG AA needs 4.5:1 — effectively illegible).
 * The class of bug: a token-level gate that never checked the
 * FOREGROUND pairings. These gates enumerate every dark-background
 * status-pairing in the source and assert the foreground token, plus
 * compute real WCAG ratios for the palette pairs the components use.
 */
import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const webRoot = resolve(__dirname, "..", "..");
const globalsCss = readFileSync(resolve(webRoot, "src/app/globals.css"), "utf-8");

function themeToken(name: string): string {
  const match = globalsCss.match(new RegExp(`--${name}:\\s*([^;]+);`));
  const value = match?.[1]?.trim();
  if (!value) throw new Error(`missing token --${name}`);
  return value;
}

/** WCAG relative luminance + contrast ratio for two #RRGGBB values. */
function contrast(a: string, b: string): number {
  const lum = (hex: string) => {
    const [r, g, b] = [0, 2, 4].map((i) => parseInt(hex.slice(i + 1, i + 3), 16) / 255);
    const f = (c: number) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
    const [lr, lg, lb] = [f(r), f(g), f(b)];
    return 0.2126 * lr + 0.7152 * lg + 0.0722 * lb;
  };
  const [la, lb] = [lum(a), lum(b)];
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

/** The foreground tokens approved for each bright background token. */
const APPROVED_FOREGROUNDS: Record<string, string[]> = {
  success: ["text-void", "text-carbon"],
  alert: ["text-void", "text-carbon"],
  "accent-primary": ["text-void", "text-carbon"],
  "accent-secondary": ["text-void", "text-carbon"],
  warning: ["text-void", "text-carbon"],
};

function collectPairings(): { file: string; line: number; text: string }[] {
  // The src files that carry status pairings (enumerated, not globbed —
  // the gate fails loudly when a new surface appears un-listed via the
  // class-sweep test below).
  const out = execSync(
    `grep -rn --include='*.tsx' --include='*.ts' -E "bg-(success|alert|accent-primary|accent-secondary|warning)[^\\"]*" ${resolve(webRoot, "src")} || true`,
    { encoding: "utf-8" },
  );
  return out
    .split("\n")
    .filter((l) => l.trim() && !l.includes("__tests__") && /\.(tsx|ts):/.test(l))
    .map((l) => {
      const idx = l.indexOf(":");
      const second = l.indexOf(":", idx + 1);
      return { file: l.slice(0, idx), line: Number(l.slice(idx + 1, second)), text: l };
    });
}

describe("status-pairing contract (P18/FE-H1, FE-M2)", () => {
  // A foreground set ON THE SAME LINE as the opaque background — the
  // cva variant merges (a custom bg over a text-void default variant,
  // e.g. error-fallback's bg-alert Button) and the decorative no-text
  // elements (status dots, icon boxes) are out of this line-level gate's
  // reach; the compiled pairing is still covered by the ratio tests below.
  it("every line-level bright background + foreground pair is approved", () => {
    const failures: string[] = [];
    for (const { text } of collectPairings()) {
      for (const [bg, approved] of Object.entries(APPROVED_FOREGROUNDS)) {
        // Opaque backgrounds only — the /NN translucent washes pair
        // bright text on dark surfaces (a different contract).
        const opaqueBg = new RegExp(`bg-${bg}(?![\\w-/])`);
        if (!opaqueBg.test(text)) continue;
        const hasForeground = /\btext-[a-z][\w-]*\b/.test(text);
        if (!hasForeground) continue; // decorative / variant-inherited
        const hasApproved = approved.some((fg) => new RegExp(`\\b${fg}\\b`).test(text));
        if (!hasApproved) {
          failures.push(`${text.trim()}\n  → bg-${bg} needs one of: ${approved.join(", ")}`);
        }
      }
    }
    expect(failures, failures.join("\n")).toEqual([]);
  });

  it("no text-white/text-text-primary rides a bright status background", () => {
    const offenders = collectPairings()
      .filter(({ text }) =>
        /\b(text-white|text-text-primary)\b/.test(text) &&
        /bg-(success|alert|accent-primary|accent-secondary|warning)(?![\w-/])/.test(text))
      .map(({ text }) => text.trim());
    expect(offenders, offenders.join("\n")).toEqual([]);
  });
});

describe("palette contrast ratios (P18/FE-M3)", () => {
  it("the text tokens meet AA (4.5:1) on the void background they render over", () => {
    const voidBg = themeToken("color-void");
    for (const token of ["color-text-primary", "color-text-secondary", "color-text-muted"]) {
      const ratio = contrast(themeToken(token), voidBg);
      expect(ratio, `--${token} on void is ${ratio.toFixed(2)}:1 (AA needs 4.5)`).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("the bright status backgrounds meet AA with their dark foregrounds", () => {
    const voidFg = themeToken("color-void");
    for (const token of ["color-success", "color-alert", "color-accent-primary", "color-accent-secondary"]) {
      const ratio = contrast(voidFg, themeToken(token));
      expect(ratio, `void on --${token} is ${ratio.toFixed(2)}:1 (AA needs 4.5)`).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("the design header claims only what the palette delivers", () => {
    expect(globalsCss).not.toMatch(/WCAG AAA Contrast/);
    expect(globalsCss).toMatch(/WCAG AA/);
  });
});
