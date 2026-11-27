import { describe, expect, it } from "vitest";

import { buildCsp } from "@/lib/csp";

/**
 * P16/FE-C1: the production CSP must be nonce-based.
 *
 * The pre-P16 production branch was `script-src 'self'` while every
 * prerendered page carried NON-nonced inline bootstrap scripts
 * (<script id="_R_">, the __next_f payload pushes) — browsers blocked
 * them, so the shipped production app could not hydrate. The dev-only
 * suite (next dev allows unsafe-inline) structurally could not catch it.
 *
 * The contract under test:
 * - PRODUCTION: `script-src 'self' 'nonce-<n>' 'strict-dynamic'` — the
 *   nonce is applied to Next's bootstrap scripts automatically (the
 *   request-header mechanism); NO unsafe-eval, NO unsafe-inline.
 * - DEVELOPMENT: the pre-P16 dev exemption set is preserved exactly
 *   (unsafe-eval + unsafe-inline, no nonce — dev overlays/HMR).
 * - style-src keeps 'unsafe-inline' in BOTH modes: React `style=`
 *   attributes are CSP-governed without it, and Next auto-nonces only
 *   its own generated <style> tags, not component style attributes.
 * - connect-src derives from the API URL (P11/M-15).
 */
describe("buildCsp (P16/FE-C1 — nonce-based production CSP)", () => {
  const apiUrl = "http://127.0.0.1:8000";

  it("production: script-src carries the nonce + strict-dynamic and no unsafe-*", () => {
    const csp = buildCsp({ nonce: "abc123==", isDev: false, apiUrl });
    expect(csp).toContain(
      "script-src 'self' 'nonce-abc123==' 'strict-dynamic'"
    );
    expect(csp).not.toContain("unsafe-eval");
    // P17: scoped to the script-src directive — style-src keeps its
    // documented 'unsafe-inline' (React style attributes).
    const scriptSrc = csp.split(";").find((d) => d.trim().startsWith("script-src")) ?? "";
    expect(scriptSrc).not.toContain("unsafe-inline");
  });

  it("production: script-src contains no unsafe-inline anywhere in that directive", () => {
    const csp = buildCsp({ nonce: "n", isDev: false, apiUrl });
    const scriptSrc = csp
      .split(";")
      .map((d) => d.trim())
      .find((d) => d.startsWith("script-src"));
    expect(scriptSrc).toBe("script-src 'self' 'nonce-n' 'strict-dynamic'");
  });

  it("production: upgrades insecure requests", () => {
    const csp = buildCsp({ nonce: "n", isDev: false, apiUrl });
    expect(csp).toContain("upgrade-insecure-requests");
  });

  it("development: preserves the documented dev exemption set exactly (no nonce)", () => {
    const csp = buildCsp({ isDev: true, apiUrl });
    const scriptSrc = csp
      .split(";")
      .map((d) => d.trim())
      .find((d) => d.startsWith("script-src"));
    expect(scriptSrc).toBe("script-src 'self' 'unsafe-eval' 'unsafe-inline'");
    expect(csp).not.toContain("nonce-");
    expect(csp).not.toContain("upgrade-insecure-requests");
  });

  it("both modes: style-src keeps 'unsafe-inline' (React style attributes)", () => {
    for (const isDev of [true, false]) {
      const csp = buildCsp({
        nonce: isDev ? undefined : "n",
        isDev,
        apiUrl,
      });
      // P17/FE-L1: fonts are self-hosted (next/font) — no Google origin.
      expect(csp).toContain("style-src 'self' 'unsafe-inline'");
      expect(csp).not.toContain("fonts.googleapis.com");
    }
  });

  it("both modes: connect-src derives from the API URL (P11/M-15)", () => {
    for (const isDev of [true, false]) {
      const csp = buildCsp({
        nonce: isDev ? undefined : "n",
        isDev,
        apiUrl: "http://10.0.0.5:9000",
      });
      expect(csp).toContain("connect-src 'self' http://10.0.0.5:9000");
    }
  });

  it("both modes: the hardening directives survive", () => {
    for (const isDev of [true, false]) {
      const csp = buildCsp({
        nonce: isDev ? undefined : "n",
        isDev,
        apiUrl,
      });
      expect(csp).toContain("default-src 'self'");
      expect(csp).toContain("frame-ancestors 'none'");
      expect(csp).toContain("base-uri 'self'");
      expect(csp).toContain("form-action 'self'");
      // P17/FE-L1: no gstatic origin — the compiled @font-face src
      // points at /_next/static/media only.
      expect(csp).toContain("font-src 'self'");
      expect(csp).not.toContain("fonts.gstatic.com");
      expect(csp).toContain("img-src 'self' data: blob:");
    }
  });

  it("production without a nonce is a programming error (fail closed)", () => {
    expect(() => buildCsp({ isDev: false, apiUrl })).toThrow(/nonce/i);
  });
});

describe("buildCsp (P19/X-M1 — production violation reporting)", () => {
  it("production: carries report-uri bound to the backend CSP endpoint", () => {
    const csp = buildCsp({
      nonce: "abc123",
      isDev: false,
      apiUrl: "https://api.ledgersg.example",
    });
    expect(csp).toContain(
      "report-uri https://api.ledgersg.example/api/v1/security/csp-report/"
    );
  });

  it("development: no report-uri (the endpoint is cross-origin noise locally)", () => {
    const csp = buildCsp({ isDev: true, apiUrl: "http://localhost:8000" });
    expect(csp).not.toContain("report-uri");
  });
});
