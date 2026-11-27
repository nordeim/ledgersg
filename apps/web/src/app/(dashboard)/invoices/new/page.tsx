"use client";

import { useRouter } from "next/navigation";
import { InvoiceFormWrapper } from "@/components/invoice/invoice-form-wrapper";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/providers/auth-provider";

export default function NewInvoicePage() {
  const router = useRouter();
  // P7/F-14: the GST columns/tax breakdown must reflect the organisation's
  // real registration state — a hardcoded true billed non-GST orgs as if
  // registered.
  const { currentOrg } = useAuth();

  const handleSuccess = (invoiceId: string) => {
    router.push(`/invoices/${invoiceId}`);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        {/* P20/FE-H2: the icon-only back link needs an accessible name —
            the primary escape hatch from the money-entry forms was
            announced as an empty link (WCAG 4.1.2 Level A). */}
        <Link
          href="/invoices"
          aria-label="Back to invoices"
          className="inline-flex h-10 w-10 items-center justify-center border border-border text-text-secondary hover:bg-surface"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <h1 className="font-display text-2xl font-bold text-text-primary">
            New Invoice
          </h1>
        </div>
      </div>
      <InvoiceFormWrapper
        isGSTRegistered={!!currentOrg?.gst_registered}
        onSuccess={handleSuccess}
      />
    </div>
  );
}
