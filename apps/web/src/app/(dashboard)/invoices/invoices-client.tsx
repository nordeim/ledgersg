"use client";

import * as React from "react";
import { useMemo, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  AlertTriangle,
  FileText,
  Loader2,
  Plus,
  Search,
} from "lucide-react";
import { useAuth } from "@/providers/auth-provider";
import { useInvoices, type InvoiceListItem } from "@/hooks/use-invoices";

/**
 * Real invoices list (P5/C-5 part 1 — replaced the hardcoded mockInvoices
 * fixture). Rows come from the backend list endpoint
 * ({results, count} contract, InvoiceDocumentListSerializer shape).
 */

function getStatusBadgeClass(status: string) {
  switch (status) {
    case "PAID":
      return "bg-accent-primary text-void";
    case "SENT":
    case "APPROVED":
      return "bg-accent-secondary text-void";
    case "PARTIALLY_PAID":
      return "bg-accent-secondary/70 text-void";
    case "DRAFT":
      return "bg-surface text-text-secondary border border-border";
    case "OVERDUE":
      return "bg-alert text-white";
    case "VOID":
      return "bg-surface text-text-muted line-through";
    default:
      return "bg-surface text-text-secondary";
  }
}

function formatAmount(value: string) {
  const n = Number(value);
  if (Number.isNaN(n)) return value;
  return n.toLocaleString("en-SG", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function InvoicesClient() {
  const { currentOrg, isLoading: authLoading } = useAuth();
  const orgId = currentOrg?.id ?? null;
  const [search, setSearch] = useState("");

  const { data, isLoading, isError, error } = useInvoices(orgId, {
    // P9/C-2: this page is the invoices list — without the type filter the
    // backend returns EVERY document (quotes and bills rendered as
    // invoices, opening at /invoices/{id} labelled INVOICE with a
    // fabricated Amount Due). The quotes page sends its own filter.
    type: "SALES_INVOICE",
  });

  const filtered = useMemo(() => {
    const invoices = data?.results ?? [];
    const q = search.trim().toLowerCase();
    if (!q) return invoices;
    return invoices.filter(
      (inv) =>
        inv.document_number.toLowerCase().includes(q) ||
        inv.contact_name.toLowerCase().includes(q)
    );
  }, [data, search]);

  if (authLoading) {
    return (
      <div className="flex items-center gap-2 text-text-secondary">
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
        <span className="text-sm">Loading…</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-text-primary">
            Invoices
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            Manage your sales invoices and track payments
          </p>
        </div>
        <Link href="/invoices/new">
          <Button className="rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim">
            <Plus className="h-4 w-4 mr-2" />
            New Invoice
          </Button>
        </Link>
      </div>

      {/* Search */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search invoices…"
            aria-label="Search invoices by number or customer"
            className="w-full pl-9 pr-4 py-2 rounded-sm border border-border bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
          />
        </div>
        {data ? (
          <span className="text-xs text-text-muted tabular-nums">
            {filtered.length} of {data.count} document
            {data.count === 1 ? "" : "s"}
          </span>
        ) : null}
      </div>

      {/* Loading */}
      {isLoading ? (
        <div className="flex items-center gap-2 text-text-secondary py-12 justify-center">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          <span className="text-sm">Loading invoices…</span>
        </div>
      ) : isError ? (
        <Card className="border-alert/40 bg-carbon rounded-sm">
          <CardContent className="py-10">
            <div className="flex flex-col items-center gap-3 text-center">
              <AlertTriangle className="h-8 w-8 text-alert" aria-hidden />
              <div>
                <p className="font-medium text-text-primary">
                  Failed to load invoices
                </p>
                <p className="text-sm text-text-secondary mt-1">
                  {error instanceof Error
                    ? error.message
                    : "An unexpected error occurred."}
                </p>
              </div>
              <Button
                variant="outline"
                className="rounded-sm border-border text-text-secondary"
                onClick={() => window.location.reload()}
              >
                Retry
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : filtered.length === 0 ? (
        <Card className="border-border bg-carbon rounded-sm">
          <CardContent className="py-12">
            <div className="flex flex-col items-center gap-3 text-center">
              <FileText className="h-8 w-8 text-text-muted" aria-hidden />
              <div>
                <p className="font-medium text-text-primary">
                  {search
                    ? "No invoices match your search"
                    : "No invoices yet"}
                </p>
                <p className="text-sm text-text-secondary mt-1">
                  {search
                    ? "Try a different number or customer name."
                    : "Create your first invoice to get started."}
                </p>
              </div>
              {!search ? (
                <Link href="/invoices/new">
                  <Button className="rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim">
                    <Plus className="h-4 w-4 mr-2" />
                    New Invoice
                  </Button>
                </Link>
              ) : null}
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-border bg-carbon rounded-sm">
          <CardHeader>
            <CardTitle className="font-display text-lg text-text-primary">
              Invoices
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border text-left">
                    <th className="pb-3 text-xs font-medium text-text-secondary uppercase">
                      Invoice
                    </th>
                    <th className="pb-3 text-xs font-medium text-text-secondary uppercase">
                      Customer
                    </th>
                    <th className="pb-3 text-xs font-medium text-text-secondary uppercase">
                      Date
                    </th>
                    <th className="pb-3 text-xs font-medium text-text-secondary uppercase">
                      Due Date
                    </th>
                    <th className="pb-3 text-xs font-medium text-text-secondary uppercase text-right">
                      Amount
                    </th>
                    <th className="pb-3 text-xs font-medium text-text-secondary uppercase">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filtered.map((invoice) => (
                    <tr
                      key={invoice.id}
                      className="hover:bg-surface/50 transition-colors"
                    >
                      <td className="py-4">
                        <Link
                          href={`/invoices/${invoice.id}`}
                          className="flex items-center gap-2 group"
                        >
                          <FileText
                            className="h-4 w-4 text-text-muted"
                            aria-hidden
                          />
                          <span className="font-mono text-sm text-text-primary group-hover:text-accent-primary">
                            {invoice.document_number}
                          </span>
                          {invoice.document_type !== "SALES_INVOICE" ? (
                            <span className="px-1.5 py-0.5 rounded-sm text-[10px] font-medium uppercase tracking-wide bg-surface text-text-secondary border border-border">
                              {invoice.document_type.replace(/_/g, " ").toLowerCase()}
                            </span>
                          ) : null}
                        </Link>
                      </td>
                      <td className="py-4">
                        <span className="text-sm text-text-secondary">
                          {invoice.contact_name}
                        </span>
                      </td>
                      <td className="py-4">
                        <span className="text-sm font-mono text-text-secondary">
                          {invoice.issue_date}
                        </span>
                      </td>
                      <td className="py-4">
                        <span className="text-sm font-mono text-text-secondary">
                          {invoice.due_date}
                        </span>
                      </td>
                      <td className="py-4 text-right">
                        <span className="text-sm font-mono font-medium text-text-primary tabular-nums">
                          {invoice.currency} {formatAmount(invoice.total_incl)}
                        </span>
                      </td>
                      <td className="py-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-sm text-xs font-medium ${getStatusBadgeClass(
                            invoice.status
                          )}`}
                        >
                          {invoice.status_display || invoice.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
