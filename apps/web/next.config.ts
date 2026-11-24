import type { NextConfig } from "next";

/**
 * LEDGERSG NEXT.JS CONFIGURATION
 *
 * Features:
 * - Server mode (standalone) — the ONLY production path (P10/M-12:
 *   the static-export mode was retired truthfully: it cannot support
 *   API-driven detail routes — generateStaticParams cannot enumerate
 *   live IDs, and the export build was already failing on
 *   /invoices/[id] and /quotes/[id])
 * - Security headers (CSP, HSTS, etc.) — served via headers() in server mode
 * - CORS configuration for backend API
 * - Image optimization
 *
 * Mode Selection:
 * - `npm run build:server` → `npm run start` (standalone; the default)
 * - NEXT_OUTPUT_MODE=export is still honoured for experiments, but no
 *   script ships it and the export build fails on detail routes.
 */

// Determine output mode from environment variable. Default standalone —
// a raw `next build` (no env) must produce the WORKING mode (P10/M-12).
const outputMode = process.env.NEXT_OUTPUT_MODE || "standalone";
const isStaticExport = outputMode === "export";
const isServerMode = outputMode === "standalone" || !isStaticExport;

// Backend API URL for CSP and rewrites
const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// P11/M-15: the dev-only CSP exemptions key off the build mode, not
// isServerMode (both dev server and production standalone are server
// mode — what differs is NODE_ENV).
const isDev = process.env.NODE_ENV === "development";

const nextConfig: NextConfig = {
  // Output mode: 'standalone' (default) or 'export' (experimental — see header)
  output: isServerMode ? "standalone" : "export",
  distDir: isServerMode ? ".next" : "dist",

  // Image optimization: disabled for static, enabled for server
  images: {
    unoptimized: isStaticExport,
  },

  // Enable React Strict Mode
  reactStrictMode: true,

  // Configure trailing slashes for Django backend compatibility
  trailingSlash: true,

  // Security headers - only applied in server mode.
  //
  // P13/H-1 + L-1: this is the SINGLE source of response headers.
  // src/middleware.ts was deleted in P13 — its header set silently
  // overrode this table (middleware-set headers win), shipping
  // 'unsafe-eval' + 'unsafe-inline' unconditionally and defeating the
  // P11/M-15 env-aware policy. The middleware's unique headers (the
  // cross-origin trio, upgrade-insecure-requests, the fuller
  // Permissions-Policy) are consolidated here; the deprecated
  // X-XSS-Protection is dropped (OWASP: modern browsers ignore it and
  // it enables XSS in old ones). This also retires the Next 16
  // middleware→proxy deprecation warning.
  async headers() {
    // Security headers don't work with static export
    if (isStaticExport) {
      return [];
    }

    const csp = [
      "default-src 'self'",
      // P11/M-15: the unsafe-eval/unsafe-inline exemptions apply
      // in DEVELOPMENT only (dev overlays/HMR need them; Next 16's
      // standalone production build does not).
      isDev
        ? "script-src 'self' 'unsafe-eval' 'unsafe-inline'"
        : "script-src 'self'",
      "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
      "font-src 'self' https://fonts.gstatic.com",
      "img-src 'self' data: blob:",
      // P11/M-15: connect-src derives from NEXT_PUBLIC_API_URL
      // (the same env the client reads) instead of hardcoding
      // localhost:8000 twice plus placeholder external APIs.
      `connect-src 'self' ${apiUrl} https://api.peppol.sg https://api.iras.gov.sg`,
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
      // upgrade-insecure-requests is a production posture (dev runs on
      // plain http://localhost by design).
      ...(isDev ? [] : ["upgrade-insecure-requests"]),
    ].join("; ");

    return [
      {
        source: "/:path*",
        headers: [
          // Content Security Policy
          {
            key: "Content-Security-Policy",
            value: csp,
          },
          // HTTP Strict Transport Security
          {
            key: "Strict-Transport-Security",
            value: "max-age=31536000; includeSubDomains; preload",
          },
          // X-Frame-Options
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          // X-Content-Type-Options
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          // Referrer-Policy
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          // Permissions-Policy (the full directive list, ported from the
          // removed middleware)
          {
            key: "Permissions-Policy",
            value:
              "camera=(), microphone=(), geolocation=(), payment=(), usb=(), magnetometer=(), gyroscope=()",
          },
          // Cross-origin policies (ported from the removed middleware)
          {
            key: "Cross-Origin-Opener-Policy",
            value: "same-origin",
          },
          {
            key: "Cross-Origin-Resource-Policy",
            value: "same-origin",
          },
          {
            key: "Cross-Origin-Embedder-Policy",
            value: "require-corp",
          },
        ],
      },
    ];
  },

  // Rewrites for API proxy (development only)
  async rewrites() {
    // Rewrites don't work with static export
    if (isStaticExport) {
      return [];
    }

    // In development, proxy API calls to backend
    if (process.env.NODE_ENV === "development") {
      return [
        {
          source: "/api/:path*",
          destination: `${apiUrl}/api/:path*`,
        },
      ];
    }

    return [];
  },

  // CORS configuration for API routes
  async redirects() {
    return [];
  },
};

export default nextConfig;
