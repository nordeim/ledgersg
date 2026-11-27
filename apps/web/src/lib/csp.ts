/**
 * Content-Security-Policy builder (P16/FE-C1).
 *
 * SINGLE SOURCE OF TRUTH for the CSP string. The header itself is set by
 * `src/proxy.ts` (never also in `next.config.ts` headers — the P13/H-1
 * lesson: proxy-set headers silently override the config table for the
 * same key).
 *
 * Why nonce-based in production: Next.js ships non-nonced inline bootstrap
 * scripts (the `_R_` boot script + the `self.__next_f.push(...)` flight
 * payloads) on every page. A static `script-src 'self'` blocks them, so
 * the app never hydrates. The proxy generates a per-request nonce and
 * forwards the CSP on the REQUEST headers — Next parses the nonce out of
 * the request CSP and applies it to its own scripts automatically (the
 * documented mechanism; requires dynamic rendering, which the root layout
 * opts into).
 *
 * Development keeps the pre-P16 exemption set (unsafe-eval for React's
 * eval-based debugging + unsafe-inline for dev overlays/HMR) with no
 * nonce: local-only surface, and a nonce alongside 'unsafe-inline' is
 * ignored by CSP3 browsers anyway.
 *
 * style-src keeps 'unsafe-inline' in BOTH modes: React `style=` attributes
 * are CSP-governed without it, and Next auto-nonces only its own
 * generated <style> tags, not component style attributes. script-src is
 * the XSS-critical directive; this is the documented compromise.
 */

export interface CspOptions {
  /** Cryptographically random, single-use nonce (base64). Required in production. */
  nonce?: string;
  isDev: boolean;
  /** The backend API origin (P11/M-15: derived from NEXT_PUBLIC_API_URL). */
  apiUrl: string;
}

export function buildCsp({ nonce, isDev, apiUrl }: CspOptions): string {
  const scriptSrc = isDev
    ? "script-src 'self' 'unsafe-eval' 'unsafe-inline'"
    : `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`;

  if (!isDev && !nonce) {
    // Fail closed: a nonce-less production CSP would either block
    // hydration (strict) or silently weaken the policy (permissive).
    throw new Error(
      "buildCsp: a nonce is required for the production CSP (P16/FE-C1)"
    );
  }

  return [
    "default-src 'self'",
    scriptSrc,
    // P17/FE-L1: fonts are self-hosted via next/font (every compiled
    // @font-face src points at /_next/static/media) — the Google origins
    // were dead policy-widening; CSP is only as strong as its loosest
    // unused allowance. Re-add them only when a runtime font fetch
    // actually ships.
    "style-src 'self' 'unsafe-inline'",
    "font-src 'self'",
    "img-src 'self' data: blob:",
    // P17/FE-L1: api.peppol.sg / api.iras.gov.sg map to the
    // NEXT_PUBLIC_ENABLE_* flags the .env.example marks "RESERVED — NOT
    // READ BY THE CODE"; zero browser-side callers exist. connect-src
    // stays 'self' + the backend origin until those integrations ship.
    `connect-src 'self' ${apiUrl}`,
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    // P19/X-M1: production violations report to the backend's (already
    // existing, already tested) CSP report endpoint — without this the
    // ENFORCED policy's failures were invisible in production (the exact
    // hydration-break class P16/FE-C1 fixed would return silently).
    // Dev keeps no report-uri: the endpoint is cross-origin noise locally.
    ...(isDev ? [] : [`report-uri ${apiUrl}/api/v1/security/csp-report/`]),
    // Production posture only — dev runs on plain http://localhost by design.
    ...(isDev ? [] : ["upgrade-insecure-requests"]),
  ].join("; ");
}
