import type { Metadata, Viewport } from "next";
import { Inter, Space_Grotesk, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/providers";

const inter = Inter({
  variable: "--font-body",
  subsets: ["latin"],
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-display",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "LedgerSG — IRAS-Compliant Accounting for Singapore SMBs",
  description:
    "Enterprise-grade double-entry accounting platform purpose-built for Singapore SMBs. IRAS compliant, InvoiceNow ready, GST-native.",
  keywords: [
    "accounting",
    "Singapore",
    "IRAS",
    "GST",
    "InvoiceNow",
    "Peppol",
    "SMB",
  ],
  authors: [{ name: "LedgerSG" }],
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#050505",
};

// P16/FE-C1: the production CSP is nonce-based (src/proxy.ts), and Next
// applies a nonce to its bootstrap scripts only during SERVER-SIDE
// rendering — statically prerendered shells carry no nonce and cannot
// hydrate under the strict policy. Force dynamic rendering for every
// route (the per-request cost is a thin server-component shell for a
// login-gated dashboard app — the documented Next trade for nonces).
export const dynamic = "force-dynamic";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" data-scroll-behavior="smooth">
      <body
        className={`${inter.variable} ${spaceGrotesk.variable} ${jetbrainsMono.variable} antialiased`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
