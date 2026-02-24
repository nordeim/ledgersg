"use client";

import { useRouter } from "next/navigation";
import { InvoiceFormWrapper } from "@/components/invoice/invoice-form-wrapper";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function NewInvoicePage() {
  const router = useRouter();

  const handleSuccess = (invoiceId: string) => {
    router.push(`/invoices/${invoiceId}`);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link
          href="/invoices"
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
        isGSTRegistered={true}
        onSuccess={handleSuccess}
      />
    </div>
  );
}
