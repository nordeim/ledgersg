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
      thresholds: {
        lines: 85,
        functions: 85,
        branches: 80,
        statements: 85,
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
