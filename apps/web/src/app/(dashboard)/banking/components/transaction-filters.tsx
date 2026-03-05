"use client";

import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RotateCcw } from "lucide-react";

export interface TransactionFilters {
  bank_account_id?: string;
  is_reconciled?: boolean | null;
  unreconciled_only?: boolean;
  date_from?: string;
  date_to?: string;
}

interface TransactionFiltersProps {
  filters: TransactionFilters;
  onChange: (filters: TransactionFilters) => void;
  bankAccounts: Array<{ id: string; account_name: string }>;
}

export function TransactionFilters({
  filters,
  onChange,
  bankAccounts,
}: TransactionFiltersProps) {
  const handleReset = () => {
    onChange({
      bank_account_id: undefined,
      is_reconciled: null,
      unreconciled_only: false,
      date_from: undefined,
      date_to: undefined,
    });
  };

  const hasActiveFilters =
    filters.bank_account_id !== undefined ||
    filters.is_reconciled !== null ||
    filters.unreconciled_only ||
    filters.date_from !== undefined ||
    filters.date_to !== undefined;

  const handleBankAccountChange = (value: string) => {
    onChange({
      ...filters,
      bank_account_id: value === "all" ? undefined : value,
    });
  };

  const handleReconciliationChange = (value: string) => {
    let is_reconciled: boolean | null = null;
    if (value === "reconciled") is_reconciled = true;
    else if (value === "unreconciled") is_reconciled = false;
    
    onChange({
      ...filters,
      is_reconciled,
    });
  };

  const handleUnreconciledToggle = () => {
    onChange({
      ...filters,
      unreconciled_only: !filters.unreconciled_only,
    });
  };

  const handleDateFromChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({
      ...filters,
      date_from: e.target.value || undefined,
    });
  };

  const handleDateToChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({
      ...filters,
      date_to: e.target.value || undefined,
    });
  };

  // Convert boolean | null to string for select
  const getReconciliationValue = () => {
    if (filters.is_reconciled === null) return "all";
    if (filters.is_reconciled === true) return "reconciled";
    return "unreconciled";
  };

  return (
    <div className="space-y-4 p-4 border border-border bg-carbon rounded-sm" data-testid="transaction-filters">
      <div className="flex flex-wrap gap-4 items-end">
        {/* Bank Account Select */}
        <div className="flex-1 min-w-[200px]">
          <label className="text-sm text-text-muted mb-1.5 block" htmlFor="bank-account">
            Bank Account
          </label>
          <Select
            value={filters.bank_account_id || "all"}
            onValueChange={handleBankAccountChange}
          >
            <SelectTrigger className="w-full" id="bank-account" data-testid="bank-account-select">
              <SelectValue placeholder="Select account" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Accounts</SelectItem>
              {bankAccounts.map((account) => (
                <SelectItem key={account.id} value={account.id}>
                  {account.account_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Reconciliation Status */}
        <div className="flex-1 min-w-[200px]">
          <label className="text-sm text-text-muted mb-1.5 block" htmlFor="reconciliation-status">
            Reconciliation Status
          </label>
          <Select
            value={getReconciliationValue()}
            onValueChange={handleReconciliationChange}
          >
            <SelectTrigger className="w-full" id="reconciliation-status" data-testid="reconciliation-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="reconciled">Reconciled</SelectItem>
              <SelectItem value="unreconciled">Unreconciled</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Date Range */}
        <div className="flex-1 min-w-[200px]">
          <label className="text-sm text-text-muted mb-1.5 block" htmlFor="date-from">
            From Date
          </label>
          <input
            id="date-from"
            type="date"
            value={filters.date_from || ""}
            onChange={handleDateFromChange}
            className="w-full h-10 px-3 rounded-md border border-border bg-background text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent-primary focus:border-transparent"
            data-testid="date-from-input"
          />
        </div>

        <div className="flex-1 min-w-[200px]">
          <label className="text-sm text-text-muted mb-1.5 block" htmlFor="date-to">
            To Date
          </label>
          <input
            id="date-to"
            type="date"
            value={filters.date_to || ""}
            onChange={handleDateToChange}
            className="w-full h-10 px-3 rounded-md border border-border bg-background text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent-primary focus:border-transparent"
            data-testid="date-to-input"
          />
        </div>
      </div>

      {/* Second row: Checkbox and Reset */}
      <div className="flex items-center justify-between">
        {/* Unreconciled Only Toggle */}
        <div className="flex items-center gap-2">
          <input
            id="unreconciled-only"
            type="checkbox"
            checked={filters.unreconciled_only}
            onChange={handleUnreconciledToggle}
            className="h-4 w-4 rounded border-border text-accent-primary focus:ring-accent-primary"
            data-testid="unreconciled-only-checkbox"
          />
          <label htmlFor="unreconciled-only" className="text-sm text-text-secondary cursor-pointer">
            Unreconciled Only
          </label>
        </div>

        {/* Reset Button */}
        <Button
          variant="outline"
          onClick={handleReset}
          disabled={!hasActiveFilters}
          className="h-10"
          data-testid="reset-filters-button"
        >
          <RotateCcw className="h-4 w-4 mr-2" />
          Reset
        </Button>
      </div>
    </div>
  );
}
