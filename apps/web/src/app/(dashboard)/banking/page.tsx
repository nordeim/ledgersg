import { Suspense } from "react";
import { Metadata } from "next";
import { Loader2 } from "lucide-react";
import { BankingClient } from "./banking-client";

export const metadata: Metadata = {
  title: "Banking — LedgerSG",
  description: "Manage bank accounts, payments, and reconciliation",
};

/**
 * Banking Page
 *
 * Server component that delegates to BankingClient for data fetching.
 * Follows the pattern from dashboard/page.tsx
 *
 * P10/L-7: BankingClient reads useSearchParams() — a client hook that
 * needs a Suspense boundary at the page level, or any prerender refactor
 * (next build's static analysis) would break with "useSearchParams()
 * should be wrapped in a suspense boundary". The boundary makes the
 * requirement structural instead of dodged by the dashboard layout's
 * mounted-gate.
 */
export default function BankingPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-[60vh]">
          <Loader2 className="h-8 w-8 animate-spin text-accent-primary" />
        </div>
      }
    >
      <BankingClient />
    </Suspense>
  );
}
