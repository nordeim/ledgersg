import { NextRequest, NextResponse } from "next/server";

import { buildCsp } from "@/lib/csp";

/**
 * Per-request Content-Security-Policy with a fresh nonce (P16/FE-C1).
 *
 * The mechanism (per the Next.js 16 CSP guide): generate a single-use
 * nonce per request, set the CSP on BOTH the request headers (Next parses
 * the nonce from the request CSP and applies it to its bootstrap scripts
 * — the `_R_` boot script and the `__next_f` payloads) and the response
 * headers (what the browser enforces). Nonces require dynamic rendering —
 `src/app/layout.tsx` opts the app into `force-dynamic`.
 *
 * Single source of truth (P13/H-1): the CSP is set ONLY here. The rest
 * of the security-header table (HSTS, X-Frame-Options, COOP/COEP/CORP,
 * Permissions-Policy, ...) stays in `next.config.ts` headers() — no key
 * overlaps, so no silent override.
 */

export function proxy(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
  const isDev = process.env.NODE_ENV === "development";
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const contentSecurityPolicy = buildCsp(
    isDev ? { isDev, apiUrl } : { nonce, isDev, apiUrl }
  );

  const requestHeaders = new Headers(request.headers);
  if (!isDev) {
    requestHeaders.set("x-nonce", nonce);
    // Next reads the nonce out of the REQUEST CSP header.
    requestHeaders.set("Content-Security-Policy", contentSecurityPolicy);
  }

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", contentSecurityPolicy);
  return response;
}

export const config = {
  // Every document route; skip the static-asset paths (no document
  // response needs a nonce, and skipping keeps the proxy off the hot
  // path for chunks).
  matcher: ["/((?!_next/static|_next/image|favicon\\.ico).*)"],
};
