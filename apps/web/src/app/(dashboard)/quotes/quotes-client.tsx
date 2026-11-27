"use client";

import * as React from "react";
import Link from "next/link";
import { AlertTriangle, Loader2, Building2, Plus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/providers/auth-provider";
import { TablePagination } from "@/components/ui/table-pagination";
import { useInvoices, useConvertQuote } from "@/hooks/use-invoices";

/**
 * Real quotes list (P8/Q-4 — replaced the static shell). Quotes are
 * SALES_QUOTE documents on the same documents endpoint (?type= — the
 * filter key the backend actually reads).
 */

const CONVERTIBLE = new Set(["DRAFT", "SENT"]);

/** P26: the page size — the ledger's convention (P24), one consistent
 * control across every list surface. */
const QUOTES_PAGE_SIZE = 20;

export function QuotesClient() {
  const { currentOrg, isLoading: authLoading } = useAuth();
  const orgId = currentOrg?.id ?? null;
  const [offset, setOffset] = React.useState(0);
  const { data, isLoading, isError, isFetching } = useInvoices(
    orgId,
    {
      type: "SALES_QUOTE",
    },
    undefined,
    { limit: QUOTES_PAGE_SIZE, offset }
  );
  const convertQuote = useConvertQuote(orgId ?? "");

  if (authLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-text-secondary">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span>Loading quotes…</span>
      </div>
    );
  }

  // P7/F-12: an authenticated user with no organisation is not an error.
  if (!currentOrg) {
    return (
      <Card className="border-border bg-carbon">
        <CardContent className="flex flex-col items-center gap-3 py-16">
          <Building2 className="h-8 w-8 text-accent-secondary" />
          <p className="font-medium text-text-primary">No organisation selected</p>
          <p className="text-sm text-text-secondary">
            Select an organisation to view its quotes.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-text-secondary">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span>Loading quotes…</span>
      </div>
    );
  }

  if (isError) {
    return (
      <Card className="border-border bg-carbon">
        <CardContent className="flex flex-col items-center gap-3 py-16">
          <AlertTriangle className="h-8 w-8 text-alert" />
          <p className="font-medium text-text-primary">Failed to load quotes</p>
          <p className="text-sm text-text-secondary">
            The quotes could not be loaded from the server.
          </p>
        </CardContent>
      </Card>
    );
  }

  const quotes = data?.results ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-text-primary">
            Quotes
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            Create and manage customer quotations
          </p>
        </div>
        <Link
          href="/quotes/new"
          className="inline-flex h-10 items-center gap-2 rounded-sm bg-accent-primary px-4 py-2 text-sm font-medium text-void transition-colors hover:bg-accent-primary-dim focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-void"
        >
          <Plus className="h-4 w-4" />
          New Quote
        </Link>
      </div>

      <Card className="border-border bg-carbon">
        <CardContent className="pt-6">
          {(data?.count ?? 0) === 0 ? (
            <div className="flex flex-col items-center gap-3 py-16">
              <p className="font-medium text-text-primary">No quotes yet</p>
              <p className="text-sm text-text-secondary">
                Create your first quotation — convert it to an invoice when
                the customer accepts.
              </p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-text-muted">
                  <th scope="col" className="py-2 pr-4 font-medium">Number</th>
                  <th scope="col" className="py-2 pr-4 font-medium">Customer</th>
                  <th scope="col" className="py-2 pr-4 font-medium">Issue</th>
                  <th scope="col" className="py-2 pr-4 font-medium">Valid until</th>
                  <th scope="col" className="py-2 pr-4 font-medium">Status</th>
                  <th scope="col" className="py-2 pr-4 text-right font-medium">Total</th>
                  <th scope="col" className="py-2 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {quotes.map((quote) => (
                  <tr key={quote.id} className="border-b border-border/50">
                    <td className="py-2 pr-4">
                      <Link
                        href={`/quotes/${quote.id}`}
                        className="font-mono text-xs text-accent-primary hover:underline"
                      >
                        {quote.document_number}
                      </Link>
                    </td>
                    <td className="py-2 pr-4 text-text-primary">
                      {quote.contact_name}
                    </td>
                    <td className="py-2 pr-4 text-text-secondary">{quote.issue_date}</td>
                    <td className="py-2 pr-4 text-text-secondary">{quote.due_date}</td>
                    <td className="py-2 pr-4">
                      <Badge
                        variant={
                          quote.related_document_id ? "default" : "secondary"
                        }
                      >
                        {/* P9/C-6: CONVERTED means a linked invoice exists —
                            an approved-but-unconverted quote is APPROVED. */}
                        {quote.related_document_id
                          ? "CONVERTED"
                          : quote.status}
                      </Badge>
                    </td>
                    <td className="py-2 pr-4 text-right font-mono text-text-primary">
                      {Number(quote.total_incl).toLocaleString("en-SG", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </td>
                    <td className="py-2 text-right">
                      {CONVERTIBLE.has(quote.status) ? (
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-8 rounded-sm border-border"
                          disabled={convertQuote.isPending}
                          onClick={() => convertQuote.mutate(quote.id)}
                        >
                          {convertQuote.isPending ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : null}
                          Convert
                        </Button>
                      ) : (
                        <span className="text-xs text-text-muted">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      {/* P26: the shared page control — the truthful total + the
          boundary-disabled buttons. */}
      {data && data.count > 0 && (
        <TablePagination
          offset={offset}
          limit={QUOTES_PAGE_SIZE}
          count={data.count}
          onPageChange={setOffset}
          disabled={isFetching}
        />
      )}
    </div>
  );
}
