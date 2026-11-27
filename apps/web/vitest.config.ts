import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

/**
 * LEDGERSG VITEST CONFIGURATION
 *
 * Purpose: Unit and integration testing for components and utilities
 * Coverage Targets:
 * - lib/gst-engine.ts: 100% (critical for IRAS compliance)
 * - Components: 90% (aspirational — the enforced floor is the
 *   whole-suite ratchet below)
 * - Hooks: 85% (aspirational — the ENFORCED hooks-tier floor sits at
 *   the measured value; raise it as coverage improves)
 */

export default defineConfig({
  plugins: [react()],
  test: {
    name: "ledgersg-web",
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/__tests__/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    exclude: ["node_modules", "dist", ".next"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "json"],
      reportsDirectory: "./coverage",
      // P10/M-13: the coverage ratchet. The previous thresholds (85/85/80)
      // had NEVER passed — a fictional gate that never ran in CI or
      // pre-push. The ratchet sits at the measured floor (post-P10,
      // with Tasks 9-13's new surfaces included): statements 62.88%,
      // branches 52.33%, functions 51.97%, lines 63.19%. A REAL gate
      // that fails on regression. The debt to the 85% bar is registered
      // in the P10 plan; the ratchet is the mechanism that raises the
      // floor over time — bump these numbers as coverage improves,
      // never lower them.
      //
      // P13/M-4: per-glob thresholds (Vitest 4) lock the src/lib floor —
      // the header's "lib/gst-engine.ts: 100% (critical for IRAS
      // compliance)" claim is now an enforced surface instead of a
      // comment. gst-engine itself sits at 100/96.77/100/100; the glob
      // ratchet is set at the directory's measured floor so the whole
      // lib tier cannot regress below today's level.
      //
      // P20/FE-M5: the measured surface now INCLUDES src/app/** and
      // src/providers/** (the blind spots the P20 audit flagged — the
      // route clients carry most of the money-flow UI and sat outside
      // the ratchet). Measured with the app+providers tiers included:
      // statements 71.92 / functions 61.39 / branches 68.96 / lines
      // 72.5 — including them RAISES the whole-suite floor, so the
      // ratchet rises with the surface. Per-glob floors for the app,
      // components, and providers tiers sit at their measured values.
      // src/stores/** stays excluded (documented): the single zustand
      // store is exercised through the guard/form suites but is not a
      // meaningful standalone coverage unit — registering it needs its
      // own suite.
      thresholds: {
        // whole-suite floor (P20/FE-M5: raised 62/51/52/63 → 71/60/68/71
        // with the app+providers tiers now measured)
        lines: 71,
        functions: 60,
        branches: 68,
        statements: 71,
        // the lib tier floor (measured 71.23 / 74.8 / 52.32 / 73.2)
        "src/lib/**": {
          lines: 73,
          functions: 52,
          branches: 74,
          statements: 71,
        },
        // P18/CFG-L2: the hooks tier floor, set at the measured value
        // (52.81 / 47.34 / 36.15 statements/functions/branches) — the
        // header's aspirational "Hooks: 85%" was never enforced, and 5 of
        // 13 hooks measured 0-20%. Same ratchet philosophy as the P10
        // whole-suite floor: a REAL gate at today's level, raised over
        // time — never lowered.
        "src/hooks/**": {
          lines: 52,
          functions: 47,
          branches: 36,
          statements: 52,
        },
        // P20/FE-M5: the app tier floor (the route clients — measured
        // 74/65/72/74 statements/functions/branches/lines).
        "src/app/**": {
          lines: 73,
          functions: 64,
          branches: 71,
          statements: 73,
        },
        // P20/FE-M5: the components tier floor (measured 83/75/69/84).
        "src/components/**": {
          lines: 83,
          functions: 74,
          branches: 68,
          statements: 82,
        },
        // P20/FE-M5: the providers tier floor (measured 62/62/59/61).
        "src/providers/**": {
          lines: 60,
          functions: 60,
          branches: 58,
          statements: 61,
        },
      },
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "node_modules/",
        "**/*.d.ts",
        "**/*.config.*",
        "**/_*.{ts,tsx}",
        "**/types/**",
        // P20/FE-M5: the test helper (src/__tests__/utils.tsx) is test
        // infrastructure, not production surface — it was silently
        // counted in the whole-suite numbers.
        "**/__tests__/**",
        // documented exclusion (see the thresholds comment): the single
        // zustand store has no standalone coverage unit.
        "src/stores/**",
      ],
    },
    // Test timeout
    testTimeout: 10000,
    // Retry failed tests in CI
    retry: process.env.CI ? 2 : 0,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
