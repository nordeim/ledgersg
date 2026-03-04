import { Metadata } from "next";
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
 */
export default function BankingPage() {
  return <BankingClient />;
}
