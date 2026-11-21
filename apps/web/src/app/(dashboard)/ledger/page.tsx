import type { Metadata } from "next";
import { LedgerClient } from "./ledger-client";

export const metadata: Metadata = {
  title: "General Ledger — LedgerSG",
  description: "View your general ledger and journal entries",
};

export default function LedgerPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-text-primary">
          General Ledger
        </h1>
        <p className="text-sm text-text-secondary mt-1">
          View and manage journal entries
        </p>
      </div>
      <LedgerClient />
    </div>
  );
}
