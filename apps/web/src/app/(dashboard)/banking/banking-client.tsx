"use client";

import * as React from "react";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Plus, Landmark, CreditCard, ArrowLeftRight, Loader2, AlertTriangle, Building2, X, Upload } from "lucide-react";
import { useAuth } from "@/providers/auth-provider";
import { useBankAccounts } from "@/hooks/use-banking";
import { formatOpeningBalance } from "@/shared/schemas/bank-account";
import { PaymentList } from "./components/payment-list";
import { PaymentFilters, type PaymentFilters as PaymentFiltersType } from "./components/payment-filters";
import { ReceivePaymentForm } from "./components/receive-payment-form";
import { TransactionList } from "./components/transaction-list";
import { TransactionFilters, type TransactionFilters as TransactionFiltersType } from "./components/transaction-filters";
import { ReconciliationSummary } from "./components/reconciliation-summary";
import { ImportTransactionsForm } from "./components/import-transactions-form";
import { ReconcileForm } from "./components/reconcile-form";
import type { Payment } from "@/shared/schemas";
import type { BankTransaction } from "@/shared/schemas";

export function BankingClient() {
  const { currentOrg, isLoading: authLoading } = useAuth();
  const orgId = currentOrg?.id ?? null;

  const { data: accountsData, isLoading, error } = useBankAccounts(orgId, {
    is_active: true,
  });

  if (authLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin text-accent-primary" />
      </div>
    );
  }

  if (!orgId) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-warning mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-text-primary mb-2">
            No Organisation Selected
          </h2>
          <p className="text-text-secondary">
            Please select an organisation to view banking
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-text-primary">
            Banking
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            Manage bank accounts, payments, and reconciliation
          </p>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="accounts" className="w-full">
        <TabsList className="grid w-full max-w-md grid-cols-3">
          <TabsTrigger value="accounts" className="gap-2">
            <Building2 className="h-4 w-4" />
            Accounts
          </TabsTrigger>
          <TabsTrigger value="payments" className="gap-2">
            <CreditCard className="h-4 w-4" />
            Payments
          </TabsTrigger>
          <TabsTrigger value="transactions" className="gap-2">
            <ArrowLeftRight className="h-4 w-4" />
            Transactions
          </TabsTrigger>
        </TabsList>

        {/* Bank Accounts Tab */}
        <TabsContent value="accounts">
          <BankAccountsTab
            accountsData={accountsData}
            isLoading={isLoading}
            error={error}
          />
        </TabsContent>

        {/* Payments Tab */}
        <TabsContent value="payments">
          <PaymentsTab />
        </TabsContent>

        {/* Bank Transactions Tab */}
        <TabsContent value="transactions">
          <BankTransactionsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ============================================
// BANK ACCOUNTS TAB
// ============================================

interface BankAccountsTabProps {
  accountsData: { results: any[]; count: number } | undefined;
  isLoading: boolean;
  error: Error | null;
}

function BankAccountsTab({ accountsData, isLoading, error }: BankAccountsTabProps) {
  if (isLoading) {
    return (
      <Card className="border-border bg-carbon rounded-sm">
        <CardContent className="py-12">
          <div data-testid="accounts-loading-skeleton" className="flex items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-accent-primary" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-border bg-carbon rounded-sm">
        <CardContent className="py-12">
          <div className="text-center">
            <AlertTriangle className="h-12 w-12 text-alert mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              Failed to load bank accounts
            </h3>
            <p className="text-text-secondary">Please try refreshing the page</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!accountsData || accountsData.count === 0) {
    return (
      <Card className="border-border bg-carbon rounded-sm">
        <CardContent className="py-12">
          <div className="text-center">
            <Landmark className="h-12 w-12 text-text-muted mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              No bank accounts
            </h3>
            <p className="text-text-secondary mb-4">
              Add your first bank account to start tracking transactions
            </p>
            <Button className="rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim">
              <Plus className="h-4 w-4 mr-2" />
              Add Bank Account
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border bg-carbon rounded-sm">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="font-display text-lg text-text-primary">
          Bank Accounts ({accountsData.count})
        </CardTitle>
        <Button
          size="sm"
          type="button"
          className="rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add Account
        </Button>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {accountsData.results.map((account) => (
            <div
              key={account.id}
              className="flex items-center justify-between p-4 rounded-sm border border-border bg-surface hover:border-accent-primary/50 transition-colors"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-text-primary">
                    {account.account_name}
                  </span>
                  {account.is_default && (
                    <Badge variant="outline" className="text-xs rounded-sm">
                      Default
                    </Badge>
                  )}
                </div>
                <div className="text-sm text-text-secondary">
                  {account.bank_name} &bull; {account.account_number}
                </div>
                {account.paynow_type && (
                  <div className="flex items-center gap-1 mt-1">
                    <Badge variant="secondary" className="text-xs rounded-sm">
                      PayNow
                    </Badge>
                    <span className="text-xs text-text-muted">
                      {account.paynow_type}
                    </span>
                  </div>
                )}
              </div>
              <div className="text-right">
                <div className="font-mono text-lg font-medium text-text-primary tabular-nums">
                  S$ {formatOpeningBalance(account.opening_balance)}
                </div>
                <div className="text-xs text-text-muted">{account.currency}</div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================
// PAYMENTS TAB (Implemented)
// ============================================

function PaymentsTab() {
  const { currentOrg } = useAuth();
  const orgId = currentOrg?.id ?? null;
  const [showReceiveForm, setShowReceiveForm] = useState(false);
  const [showMakeForm, setShowMakeForm] = useState(false);
  const [paymentFilters, setPaymentFilters] = useState<{
    payment_type?: "RECEIVED" | "MADE";
    is_reconciled?: boolean | null;
    date_from?: string;
    date_to?: string;
  }>({
    payment_type: undefined,
    is_reconciled: null,
  });

  if (!orgId) {
    return (
      <Card className="border-border bg-carbon rounded-sm">
        <CardContent className="py-12 text-center">
          <AlertTriangle className="h-12 w-12 text-warning mx-auto mb-4" />
          <p className="text-text-secondary">No organisation selected</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {showReceiveForm && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <ReceivePaymentForm
            orgId={orgId}
            onSuccess={() => setShowReceiveForm(false)}
            onCancel={() => setShowReceiveForm(false)}
          />
        </div>
      )}

      <PaymentFilters 
        filters={{
          payment_type: paymentFilters.payment_type === undefined ? "ALL" : paymentFilters.payment_type,
          is_reconciled: paymentFilters.is_reconciled,
          date_from: paymentFilters.date_from,
          date_to: paymentFilters.date_to,
        }}
        onChange={(newFilters) => {
          setPaymentFilters({
            payment_type: newFilters.payment_type === "ALL" ? undefined : newFilters.payment_type,
            is_reconciled: newFilters.is_reconciled,
            date_from: newFilters.date_from,
            date_to: newFilters.date_to,
          });
        }}
      />
      
      <Card className="border-border bg-carbon rounded-sm">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="font-display text-lg text-text-primary">
            Payments
          </CardTitle>
          <div className="flex gap-2">
            <Button
              onClick={() => setShowReceiveForm(true)}
              className="rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim"
            >
              <Plus className="h-4 w-4 mr-2" />
              Receive Payment
            </Button>
            <Button
              onClick={() => setShowMakeForm(true)}
              variant="outline"
              className="rounded-sm"
            >
              <Plus className="h-4 w-4 mr-2" />
              Make Payment
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <PaymentList orgId={orgId} filters={paymentFilters} />
        </CardContent>
      </Card>
    </div>
  );
}

// ============================================
// BANK TRANSACTIONS TAB (Implemented)
// ============================================

function BankTransactionsTab() {
  const { currentOrg } = useAuth();
  const orgId = currentOrg?.id ?? null;

  const [showImportForm, setShowImportForm] = useState(false);
  const [showReconcileForm, setShowReconcileForm] = useState(false);
  const [selectedTransaction, setSelectedTransaction] = useState<BankTransaction | null>(null);

  const [transactionFilters, setTransactionFilters] = useState<TransactionFiltersType>({
    bank_account_id: undefined,
    is_reconciled: null,
    unreconciled_only: false,
    date_from: undefined,
    date_to: undefined,
  });

  const { data: accountsData } = useBankAccounts(orgId, { is_active: true });
  const bankAccounts = accountsData?.results || [];

  if (!orgId) {
    return (
      <Card className="border-border bg-carbon rounded-sm">
        <CardContent className="py-12 text-center">
          <AlertTriangle className="h-12 w-12 text-warning mx-auto mb-4" />
          <p className="text-text-secondary">No organisation selected</p>
        </CardContent>
      </Card>
    );
  }

  const handleTransactionClick = (transaction: BankTransaction) => {
    setSelectedTransaction(transaction);
    setShowReconcileForm(true);
  };

  const handleCloseReconcileForm = () => {
    setShowReconcileForm(false);
    setSelectedTransaction(null);
  };

  return (
    <div className="space-y-4">
      {/* Import Modal */}
      {showImportForm && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <ImportTransactionsForm
            orgId={orgId}
            onSuccess={() => setShowImportForm(false)}
            onCancel={() => setShowImportForm(false)}
          />
        </div>
      )}

      {/* Reconcile Modal */}
      {showReconcileForm && selectedTransaction && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <ReconcileForm
            transaction={selectedTransaction}
            orgId={orgId}
            onClose={handleCloseReconcileForm}
          />
        </div>
      )}

      {/* Reconciliation Summary */}
      <ReconciliationSummary
        orgId={orgId}
        bankAccountId={transactionFilters.bank_account_id}
      />

      {/* Transaction Filters */}
      <TransactionFilters
        filters={transactionFilters}
        onChange={setTransactionFilters}
        bankAccounts={bankAccounts}
      />

      {/* Transaction List Card */}
      <Card className="border-border bg-carbon rounded-sm">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="font-display text-lg text-text-primary">
            Bank Transactions
          </CardTitle>
          <Button
            onClick={() => setShowImportForm(true)}
            className="rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim"
          >
            <Upload className="h-4 w-4 mr-2" />
            Import Statement
          </Button>
        </CardHeader>
        <CardContent>
          <TransactionList
            orgId={orgId}
            filters={transactionFilters}
            onTransactionClick={handleTransactionClick}
            onImportClick={() => setShowImportForm(true)}
          />
        </CardContent>
      </Card>
    </div>
  );
}

export default BankingClient;
