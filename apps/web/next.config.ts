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

  // Security headers - only applied in server mode
  async headers() {
    // Security headers don't work with static export
    if (isStaticExport) {
      return [];
    }

    return [
      {
        source: "/:path*",
        headers: [
          // Content Security Policy
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-eval' 'unsafe-inline'",
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
              "font-src 'self' https://fonts.gstatic.com",
              "img-src 'self' data: blob:",
              // Allow connections to backend API and external services
              `connect-src 'self' ${apiUrl} http://localhost:8000 https://api.peppol.sg https://api.iras.gov.sg`,
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self'",
            ].join("; "),
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
          // Permissions-Policy
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
          // X-XSS-Protection (legacy, CSP replaces this)
          {
            key: "X-XSS-Protection",
            value: "1; mode=block",
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
