"use client";

import * as React from "react";
import { AlertTriangle, Loader2, Building2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { LedgerTable } from "@/components/ledger/ledger-table";
import { useAuth } from "@/providers/auth-provider";
import { useLedger } from "@/hooks/use-ledger";

/**
 * Real general ledger (P6/C-5 — replaced the mockData fixture). Rows come
 * from the backend ledger endpoint (one row per journal line).
 */

export function LedgerClient() {
  const { currentOrg, isLoading: authLoading } = useAuth();
  const orgId = currentOrg?.id ?? null;

  const { data, isLoading, isError } = useLedger(orgId);

  // P7/F-12: an authenticated user with no organisation is not an error —
  // a disabled query reports isLoading=false and would fall through to the
  // fake "No journal entries yet" empty state.
  if (authLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-text-secondary">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span>Loading ledger…</span>
      </div>
    );
  }

  if (!currentOrg) {
    return (
      <Card className="border-border bg-carbon">
        <CardContent className="flex flex-col items-center gap-3 py-16">
          <Building2 className="h-8 w-8 text-accent-secondary" />
          <p className="font-medium text-text-primary">No organisation selected</p>
          <p className="text-sm text-text-secondary">
            Select an organisation to view its general ledger.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-text-secondary">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span>Loading ledger…</span>
      </div>
    );
  }

  if (isError) {
    return (
      <Card className="border-border bg-carbon">
        <CardContent className="flex flex-col items-center gap-3 py-16">
          <AlertTriangle className="h-8 w-8 text-alert" />
          <p className="font-medium text-text-primary">Failed to load ledger</p>
          <p className="text-sm text-text-secondary">
            The general ledger could not be loaded from the server.
          </p>
        </CardContent>
      </Card>
    );
  }

  const lines = data?.results ?? [];

  if (lines.length === 0) {
    return (
      <Card className="border-border bg-carbon">
        <CardContent className="flex flex-col items-center gap-3 py-16">
          <p className="font-medium text-text-primary">
            No journal entries yet
          </p>
          <p className="text-sm text-text-secondary">
            Posted journal entries and their lines will appear here.
          </p>
        </CardContent>
      </Card>
    );
  }

  return <LedgerTable data={lines} />;
}
