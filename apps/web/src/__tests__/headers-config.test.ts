/**
 * Response-header configuration contract (P13/H-1 + L-1).
 *
 * The repo had TWO header sources: src/middleware.ts (deleted in P13)
 * and next.config.ts headers(). The middleware's version silently won —
 * shipping 'unsafe-eval' + 'unsafe-inline' unconditionally (the P11/M-15
 * dev-only exemptions defeated) plus Vercel-specific origins. This gate
 * pins the SINGLE consolidated table in next.config.ts:
 *
 * - CSP keeps the env-aware P11/M-15 policy (unsafe-* in dev only)
 * - production CSP carries upgrade-insecure-requests
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

  it("production script-src has NO unsafe-eval and NO unsafe-inline", async () => {
    const headers = await loadHeaders("production");
    const csp = get(headers, "Content-Security-Policy");
    expect(csp).toBeDefined();
    const scriptSrc = cspDirective(csp, "script-src");
    expect(scriptSrc).not.toContain("unsafe-eval");
    expect(scriptSrc).not.toContain("unsafe-inline");
  });

  it("production CSP carries upgrade-insecure-requests", async () => {
    const headers = await loadHeaders("production");
    const csp = get(headers, "Content-Security-Policy");
    expect(csp).toContain("upgrade-insecure-requests");
  });

  it("development CSP keeps the dev-only unsafe exemptions", async () => {
    const headers = await loadHeaders("development");
    const csp = get(headers, "Content-Security-Policy");
    expect(csp).toContain("'unsafe-eval'");
    expect(csp).toContain("'unsafe-inline'");
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

  it("production CSP drops the Vercel-specific origins the middleware shipped", async () => {
    const headers = await loadHeaders("production");
    const csp = get(headers, "Content-Security-Policy");
    expect(csp).not.toContain("vercel.live");
    expect(csp).not.toContain("vercel-insights.com");
    expect(csp).not.toContain("img-src 'self' data: blob: https:");
  });
});
