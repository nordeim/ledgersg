import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // P18: generated test artifacts (coverage/ from `npm run
    // test:coverage`, test-results/ + playwright-report/ from Playwright
    // runs) — all gitignored build outputs; eslint must not scan them
    // (a leftover coverage/block-navigation.js surfaced as a phantom
    // 6th warning against the documented 5-warning parity).
    "coverage/**",
    "test-results/**",
    "playwright-report/**",
  ]),
]);

export default eslintConfig;
