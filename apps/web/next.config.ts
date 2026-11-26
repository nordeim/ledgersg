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
 * - Security headers (HSTS, XFO, COOP/COEP/CORP, ...) — served via
 *   headers() in server mode. The CSP is NOT here: `src/proxy.ts` owns
 *   it (P16/FE-C1 — the per-request nonce needs the request header
 *   mechanism; two sources would re-create the P13/H-1 override trap).
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

// Backend API URL for rewrites
const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  // Output mode: 'standalone' (default) or 'export' (experimental — see header)
  output: isServerMode ? "standalone" : "export",
  distDir: isServerMode ? ".next" : "dist",

  // P16/FE-L1: Next 16's dev-origin protection silently blocks dev
  // chunks for the 127.0.0.1 origin (the documented trap in
  // docs/Tailwind-V4-Validation-Report.md) — allow both dev origins.
  allowedDevOrigins: ["127.0.0.1"],

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
  // P13/H-1 + L-1: this is the SINGLE source of the NON-CSP response
  // headers. src/middleware.ts was deleted in P13 — its header set
  // silently overrode this table (middleware-set headers win). The
  // middleware's unique headers (the cross-origin trio,
  // upgrade-insecure-requests, the fuller Permissions-Policy) are
  // consolidated here; the deprecated X-XSS-Protection is dropped (OWASP:
  // modern browsers ignore it and it enables XSS in old ones). This also
  // retires the Next 16 middleware→proxy deprecation warning.
  //
  // P16/FE-C1: the Content-Security-Policy lives in src/proxy.ts —
  // production needs a per-request nonce applied to Next's inline
  // bootstrap scripts, which only the proxy's request-header mechanism
  // can do. A static `script-src 'self'` here blocked every non-nonced
  // inline script in the shipped build (no hydration). Do NOT add a CSP
  // entry back to this table: proxy-set headers win, and a second source
  // re-creates the P13/H-1 override trap.
  async headers() {
    // Security headers don't work with static export
    if (isStaticExport) {
      return [];
    }

    return [
      {
        source: "/:path*",
        headers: [
          // (Content-Security-Policy — set by src/proxy.ts, NOT here)
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
