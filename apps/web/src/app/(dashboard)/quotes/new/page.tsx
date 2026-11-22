"use client";

import { useRouter } from "next/navigation";
import { InvoiceFormWrapper } from "@/components/invoice/invoice-form-wrapper";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/providers/auth-provider";

/**
 * New quote (P8/Q-4) — the same create contract as the invoice form with
 * document_type: SALES_QUOTE (the QT- numbering the seeded sequence
 * promises). GST columns still follow the org's real registration.
 */
export default function NewQuotePage() {
  const router = useRouter();
  const { currentOrg } = useAuth();

  const handleSuccess = (quoteId: string) => {
    router.push(`/quotes/${quoteId}`);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link
          href="/quotes"
          className="inline-flex h-10 w-10 items-center justify-center border border-border text-text-secondary hover:bg-surface"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <h1 className="font-display text-2xl font-bold text-text-primary">
            New Quote
          </h1>
        </div>
      </div>
      <InvoiceFormWrapper
        isGSTRegistered={!!currentOrg?.gst_registered}
        documentType="SALES_QUOTE"
        onSuccess={handleSuccess}
      />
    </div>
  );
}
