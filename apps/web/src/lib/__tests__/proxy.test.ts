/**
 * Proxy nonce orchestration contract (P17/FE-M3).
 *
 * The P16 nonce-CSP fix (FE-C1) lives in src/proxy.ts + src/lib/csp.ts.
 * No automated test imported proxy.ts — Playwright's webServer boots
 * `next dev` (dev CSP: the unsafe-inline/eval exemption set, no nonce),
 * so the EXACT production failure class the sprint fixed (strict CSP
 * blocking Next's non-nonced inline bootstrap scripts) was invisible to
 * every suite except the manual prod-csp-smoke.js. These gates drive
 * `proxy()` directly with a NextRequest in production mode.
 */
import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { NextRequest } from "next/server";

describe("proxy() nonce orchestration (P17/FE-M3)", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubEnv("NODE_ENV", "production");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  async function callProxy(url = "http://localhost:3000/login/") {
    const mod = await import("../../proxy");
    const request = new NextRequest(new Request(url, { method: "GET" }));
    return mod.proxy(request);
  }

  it("sets a per-request nonce on the REQUEST headers (Next reads it from there)", async () => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
    const mod = await import("../../proxy");
    const request = new NextRequest(new Request("http://localhost:3000/login/"));
    const response = mod.proxy(request);

    const requestCsp = response.headers.get("Content-Security-Policy") ?? "";
    // The proxy mutates request headers via NextResponse.next({request});
    // the response CSP must carry the nonce.
    expect(requestCsp).toMatch(/script-src [^;]*'nonce-[^']+'/);
    expect(requestCsp).toContain("'strict-dynamic'");
  });

  it("rotates the nonce per request (single-use contract)", async () => {
    const first = await callProxy();
    const second = await callProxy();
    const extractNonce = (policy: string | null) =>
      policy?.match(/'nonce-([^']+)'/)?.[1];
    const n1 = extractNonce(first.headers.get("Content-Security-Policy"));
    const n2 = extractNonce(second.headers.get("Content-Security-Policy"));
    expect(n1).toBeDefined();
    expect(n2).toBeDefined();
    expect(n1).not.toBe(n2);
  });

  it("response CSP has no unsafe-eval/unsafe-inline in script-src (production)", async () => {
    const response = await callProxy();
    const csp = response.headers.get("Content-Security-Policy") ?? "";
    const scriptSrc = csp.match(/script-src [^;]+/)?.[0] ?? "";
    expect(scriptSrc).not.toContain("unsafe-eval");
    expect(scriptSrc).not.toContain("unsafe-inline");
  });

  it("production CSP omits the dead font origins (P17/FE-L1)", async () => {
    const response = await callProxy();
    const csp = response.headers.get("Content-Security-Policy") ?? "";
    // Fonts are self-hosted via next/font — compiled @font-face src
    // points at /_next/static/media only; the Google origins were dead
    // policy-widening.
    expect(csp).not.toContain("fonts.googleapis.com");
    expect(csp).not.toContain("fonts.gstatic.com");
  });
});
