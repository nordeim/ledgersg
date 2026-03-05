"use client";

import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RotateCcw } from "lucide-react";

export interface PaymentFilters {
  payment_type?: "RECEIVED" | "MADE" | "ALL";
  is_reconciled?: boolean | null;
  date_from?: string;
  date_to?: string;
}

interface PaymentFiltersProps {
  filters: PaymentFilters;
  onChange: (filters: PaymentFilters) => void;
}

export function PaymentFilters({ filters, onChange }: PaymentFiltersProps) {
  const handleReset = () => {
    onChange({
      payment_type: "ALL",
      is_reconciled: null,
      date_from: undefined,
      date_to: undefined,
    });
  };

  const hasActiveFilters = 
    filters.payment_type !== "ALL" || 
    filters.is_reconciled !== null ||
    filters.date_from ||
    filters.date_to;

  return (
    <div className="space-y-4 p-4 border border-border bg-carbon rounded-sm" data-testid="payment-filters">
      {/* Payment Type Tabs */}
      <Tabs
        value={filters.payment_type || "ALL"}
        onValueChange={(value) => 
          onChange({ ...filters, payment_type: value as "RECEIVED" | "MADE" | "ALL" })
        }
        className="w-full"
      >
        <TabsList className="grid w-full grid-cols-3" data-testid="payment-type-tabs">
          <TabsTrigger value="ALL" className="text-sm">
            All Payments
          </TabsTrigger>
          <TabsTrigger value="RECEIVED" className="text-sm">
            Received
          </TabsTrigger>
          <TabsTrigger value="MADE" className="text-sm">
            Made
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Additional Filters */}
      <div className="flex flex-wrap gap-4 items-end">
        {/* Reconciliation Status */}
        <div className="flex-1 min-w-[200px]">
          <label className="text-sm text-text-muted mb-1.5 block">
            Reconciliation Status
          </label>
          <Select
            value={filters.is_reconciled === null ? "all" : filters.is_reconciled ? "reconciled" : "unreconciled"}
            onValueChange={(value) => {
              const is_reconciled = value === "all" ? null : value === "reconciled";
              onChange({ ...filters, is_reconciled });
            }}
          >
            <SelectTrigger className="w-full" data-testid="reconciliation-select">
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
          <label className="text-sm text-text-muted mb-1.5 block">
            From Date
          </label>
          <input
            type="date"
            value={filters.date_from || ""}
            onChange={(e) => onChange({ ...filters, date_from: e.target.value || undefined })}
            className="w-full h-10 px-3 rounded-md border border-border bg-background text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent-primary focus:border-transparent"
            data-testid="date-from-input"
          />
        </div>

        <div className="flex-1 min-w-[200px]">
          <label className="text-sm text-text-muted mb-1.5 block">
            To Date
          </label>
          <input
            type="date"
            value={filters.date_to || ""}
            onChange={(e) => onChange({ ...filters, date_to: e.target.value || undefined })}
            className="w-full h-10 px-3 rounded-md border border-border bg-background text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent-primary focus:border-transparent"
            data-testid="date-to-input"
          />
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
