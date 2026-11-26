/**
 * Response-header configuration contract (P13/H-1 + L-1, revised P16/FE-C1).
 *
 * The repo had TWO header sources: src/middleware.ts (deleted in P13)
 * and next.config.ts headers(). The middleware's version silently won —
 * shipping 'unsafe-eval' + 'unsafe-inline' unconditionally (the P11/M-15
 * dev-only exemptions defeated) plus Vercel-specific origins. This gate
 * pins the SINGLE consolidated table in next.config.ts:
 *
 * - the NON-CSP security headers stay consolidated here (P13)
 * - the CSP itself is NOT in this table anymore (P16/FE-C1): production
 *   needs a per-request nonce applied to Next's inline bootstrap scripts,
 *   which only src/proxy.ts + src/lib/csp.ts can do — the contract lives
 *   in src/lib/__tests__/csp.test.ts, and this file guards against a
 *   second CSP source reappearing here (the P13/H-1 override trap).
 * - the cross-origin trio (COOP/CORP/COEP) survives the middleware removal
 * - Permissions-Policy keeps the full directive list
 * - the deprecated X-XSS-Protection is gone (OWASP: drop it)
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import type { NextConfig } from "next";

type HeaderEntry = { key: string; value: string };

async function loadHeaders(nodeEnv: string): Promise<HeaderEntry[]> {
  vi.resetModules();
  vi.stubEnv("NODE_ENV", nodeEnv);
  const mod = await import("../../next.config");
  const config = (mod.default as NextConfig) as {
    headers: () => Promise<Array<{ headers: HeaderEntry[] }>>;
  };
  const result = await config.headers();
  return result[0]?.headers ?? [];
}

function get(headers: HeaderEntry[], key: string): string | undefined {
  return headers.find((h) => h.key === key)?.value;
}

/** Extract a single CSP directive's value from the policy string. */
function cspDirective(csp: string | undefined, name: string): string {
  const directive = (csp ?? "").split(";").find((d) => d.trim().startsWith(name));
  return directive?.slice(name.length).trim() ?? "";
}

describe("consolidated response headers (P13/H-1)", () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
  });

  it("next.config headers carries NO CSP — the proxy owns it (P16/FE-C1 single source)", async () => {
    // A CSP entry here would silently override the proxy's nonce-based
    // policy (proxy-set headers win — the P13/H-1 lesson) and re-ship
    // the hydration-blocking static policy.
    const headers = await loadHeaders("production");
    expect(get(headers, "Content-Security-Policy")).toBeUndefined();
    const devHeaders = await loadHeaders("development");
    expect(get(devHeaders, "Content-Security-Policy")).toBeUndefined();
  });

  it("the cross-origin trio survives the middleware removal", async () => {
    const headers = await loadHeaders("production");
    expect(get(headers, "Cross-Origin-Opener-Policy")).toBe("same-origin");
    expect(get(headers, "Cross-Origin-Resource-Policy")).toBe("same-origin");
    expect(get(headers, "Cross-Origin-Embedder-Policy")).toBe("require-corp");
  });

  it("Permissions-Policy keeps the full directive list", async () => {
    const headers = await loadHeaders("production");
    const pp = get(headers, "Permissions-Policy");
    expect(pp).toBeDefined();
    for (const directive of [
      "camera=()",
      "microphone=()",
      "geolocation=()",
      "payment=()",
      "usb=()",
      "magnetometer=()",
      "gyroscope=()",
    ]) {
      expect(pp).toContain(directive);
    }
  });

  it("the deprecated X-XSS-Protection header is gone", async () => {
    const headers = await loadHeaders("production");
    expect(get(headers, "X-XSS-Protection")).toBeUndefined();
  });

  it("the baseline security headers stay", async () => {
    const headers = await loadHeaders("production");
    expect(get(headers, "Strict-Transport-Security")).toContain("max-age=31536000");
    expect(get(headers, "X-Frame-Options")).toBe("DENY");
    expect(get(headers, "X-Content-Type-Options")).toBe("nosniff");
    expect(get(headers, "Referrer-Policy")).toBe("strict-origin-when-cross-origin");
  });

  it("the CSP builder drops the Vercel-specific origins the middleware shipped", async () => {
    const { buildCsp } = await import("@/lib/csp");
    const csp = buildCsp({ nonce: "n", isDev: false, apiUrl: "http://localhost:8000" });
    expect(csp).not.toContain("vercel.live");
    expect(csp).not.toContain("vercel-insights.com");
    expect(csp).not.toContain("img-src 'self' data: blob: https:");
    expect(cspDirective(csp, "script-src")).not.toContain("unsafe-eval");
    expect(cspDirective(csp, "script-src")).not.toContain("unsafe-inline");
    expect(csp).toContain("upgrade-insecure-requests");
    const devCsp = buildCsp({ isDev: true, apiUrl: "http://localhost:8000" });
    expect(devCsp).toContain("'unsafe-eval'");
    expect(devCsp).toContain("'unsafe-inline'");
  });
});
