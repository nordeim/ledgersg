import type { NextConfig } from "next";

/**
 * LEDGERSG NEXT.JS CONFIGURATION
 *
 * Features:
 * - Static export for deployment
 * - Security headers (CSP, HSTS, etc.)
 * - Image optimization disabled for static export
 */

const nextConfig: NextConfig = {
  output: "export",
  distDir: "dist",

  // Disable image optimization for static export
  images: {
    unoptimized: true,
  },

  // Security headers
  async headers() {
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
              "connect-src 'self' https://api.peppol.sg https://api.iras.gov.sg",
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
};

export default nextConfig;
