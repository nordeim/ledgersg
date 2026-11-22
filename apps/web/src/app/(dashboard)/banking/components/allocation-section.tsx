"use client";

import { useMemo } from "react";
import { Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useInvoices, type InvoiceListItem } from "@/hooks/use-invoices";
import type { PaymentAllocationEntry } from "@/shared/schemas/payment";

/**
 * P9/B-3b: the open-invoice allocation section for the payment forms.
 *
 * The backend has accepted inline allocations since the P5/P6 payment
 * engine ({document_id, allocated_amount}), but no UI ever sent them and
 * no surface let a user settle an invoice against a payment — invoices
 * could never reach PAID through the app. This section lists the chosen
 * contact's outstanding documents and builds the allocations payload.
 */

/** The statuses with an unsettled balance (the dashboard's outstanding set). */
const OUTSTANDING_STATUSES = new Set([
  "SENT",
  "APPROVED",
  "OVERDUE",
  "PARTIALLY_PAID",
]);

interface AllocationSectionProps {
  orgId: string;
  contactId: string;
  /** "SALES_INVOICE" for receive, "PURCHASE_INVOICE" for make. */
  documentType: "SALES_INVOICE" | "PURCHASE_INVOICE";
  allocations: PaymentAllocationEntry[];
  onChange: (allocations: PaymentAllocationEntry[]) => void;
  disabled?: boolean;
}

export function AllocationSection({
  orgId,
  contactId,
  documentType,
  allocations,
  onChange,
  disabled = false,
}: AllocationSectionProps) {
  const { data, isLoading } = useInvoices(orgId, {
    type: documentType,
    contact_id: contactId,
  });

  const openDocuments = useMemo(() => {
    const rows = data?.results ?? [];
    return rows.filter(
      (doc) =>
        OUTSTANDING_STATUSES.has(doc.status) &&
        parseFloat(doc.amount_due || "0") > 0
    );
  }, [data]);

  const allocationFor = (docId: string) =>
    allocations.find((a) => a.document_id === docId)?.allocated_amount ?? "";

  const setAllocation = (doc: InvoiceListItem, raw: string) => {
    const value = raw.trim();
    const rest = allocations.filter((a) => a.document_id !== doc.id);
    if (value === "") {
      onChange(rest);
      return;
    }
    // The backend caps allocations at the outstanding balance; the input
    // clamps to it so the user cannot over-allocate by typing.
    const due = parseFloat(doc.amount_due);
    const num = parseFloat(value);
    const safe = Number.isFinite(num) && num >= 0 ? Math.min(num, due) : 0;
    onChange([
      ...rest,
      { document_id: doc.id, allocated_amount: safe.toFixed(2) },
    ]);
  };

  if (!contactId) return null;

  return (
    <div className="space-y-2">
      <label className="text-sm text-text-secondary">
        Apply to open {documentType === "SALES_INVOICE" ? "invoices" : "bills"}
      </label>
      {isLoading ? (
        <div className="flex items-center gap-2 text-sm text-text-secondary py-2">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          Loading open documents…
        </div>
      ) : openDocuments.length === 0 ? (
        <p className="text-sm text-text-muted py-1">
          No outstanding {documentType === "SALES_INVOICE" ? "invoices" : "bills"} for this contact.
        </p>
      ) : (
        <div className="rounded-sm border border-border divide-y divide-border">
          {openDocuments.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center justify-between gap-4 px-3 py-2.5"
            >
              <div className="min-w-0">
                <div className="font-mono text-sm text-text-primary truncate">
                  {doc.document_number}
                </div>
                <div className="text-xs text-text-muted">
                  Due {doc.due_date} · Outstanding {doc.currency}{" "}
                  {doc.amount_due}
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-xs text-text-secondary">Allocate</span>
                <Input
                  type="number"
                  min="0"
                  max={doc.amount_due}
                  step="0.01"
                  value={allocationFor(doc.id)}
                  onChange={(e) => setAllocation(doc, e.target.value)}
                  disabled={disabled}
                  aria-label={`Allocation for ${doc.document_number}`}
                  className="rounded-sm w-28 text-right"
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
