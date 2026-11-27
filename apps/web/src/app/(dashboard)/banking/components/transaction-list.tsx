"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertTriangle, Upload, RefreshCw } from "lucide-react";
import { useBankTransactions } from "@/hooks/use-banking";
import { TablePagination } from "@/components/ui/table-pagination";
import { TransactionRow } from "./transaction-row";
import { useUnreconcileTransaction } from "@/hooks/use-banking";
import type { BankTransaction } from "@/shared/schemas";

interface TransactionListProps {
  orgId: string;
  filters?: {
    bank_account_id?: string;
    is_reconciled?: boolean | null;
    unreconciled_only?: boolean;
    date_from?: string;
    date_to?: string;
  };
  onTransactionClick?: (transaction: BankTransaction) => void;
  onImportClick?: () => void;
}

/** P26: the page size — the ledger's convention (P24), one consistent
 * control across every list surface. */
const TRANSACTIONS_PAGE_SIZE = 20;

export function TransactionList({ 
  orgId, 
  filters = {}, 
  onTransactionClick,
  onImportClick 
}: TransactionListProps) {
  const [offset, setOffset] = useState(0);
  const { data, isLoading, error, refetch, isFetching } = useBankTransactions(
    orgId,
    filters,
    { limit: TRANSACTIONS_PAGE_SIZE, offset }
  );

  if (isLoading) {
    return (
      <div className="space-y-3" data-testid="transactions-loading">
        {[1, 2, 3].map((i) => (
          <Card key={i} className="border-border bg-surface rounded-sm" data-testid="transaction-skeleton">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="space-y-2 flex-1">
                  <Skeleton className="h-5 w-32" />
                  <Skeleton className="h-4 w-48" />
                </div>
                <Skeleton className="h-8 w-24" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive" className="rounded-sm" data-testid="transactions-error">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Failed to load transactions</AlertTitle>
        <AlertDescription className="flex flex-col gap-2">
          <p>Failed to load transactions. Please try again.</p>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => refetch()}
            className="w-fit"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  if (!data || data.count === 0) {
    return (
      <Card className="border-border bg-carbon rounded-sm" data-testid="transactions-empty">
        <CardContent className="py-12">
          <div className="text-center">
            <Upload className="h-12 w-12 text-text-muted mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              No transactions imported
            </h3>
            <p className="text-text-secondary mb-4">
              Import your first bank statement to get started with reconciliation.
            </p>
            <Button
              onClick={onImportClick}
              className="rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim"
            >
              <Upload className="h-4 w-4 mr-2" />
              Import Statement
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4" data-testid="transactions-list">
      {/* P26: the registered P10/L-2 debt retired — the shared page
          control with the truthful page-math summary replaces the bare
          count line (the "Load more" button had been doubly dead). */}
      <TablePagination
        offset={offset}
        limit={TRANSACTIONS_PAGE_SIZE}
        count={data.count}
        onPageChange={setOffset}
        disabled={isFetching}
      />
      
      <div className="space-y-3">
        {data.results.map((transaction) => (
          <TransactionRowWrapper
            key={transaction.id}
            orgId={orgId}
            transaction={transaction}
            onReconcile={onTransactionClick}
          />
        ))}
      </div>
    </div>
  );
}

/** P9/B-6: the per-row unreconcile action (hooks cannot live in a map
 * callback — the wrapper owns the mutation). */
function TransactionRowWrapper({
  orgId,
  transaction,
  onReconcile,
}: {
  orgId: string;
  transaction: BankTransaction;
  onReconcile?: (transaction: BankTransaction) => void;
}) {
  const unreconcile = useUnreconcileTransaction(orgId, transaction.id);
  return (
    <TransactionRow
      transaction={transaction}
      onReconcile={onReconcile}
      onUnreconcile={() => unreconcile.mutate()}
    />
  );
}
