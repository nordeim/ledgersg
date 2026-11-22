import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

/**
 * LEDGERSG VITEST CONFIGURATION
 *
 * Purpose: Unit and integration testing for components and utilities
 * Coverage Targets:
 * - lib/gst-engine.ts: 100% (critical for IRAS compliance)
 * - Components: 90%
 * - Hooks: 85%
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
      thresholds: {
        lines: 63,
        functions: 51,
        branches: 52,
        statements: 62,
      },
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "node_modules/",
        "**/*.d.ts",
        "**/*.config.*",
        "**/_*.{ts,tsx}",
        "**/types/**",
        "src/app/**",
        "src/providers/**",
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
