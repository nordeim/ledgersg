import { create } from "zustand";

/*
 * LEDGERSG INVOICE STORE
 *
 * Purpose: the unsaved-changes contract for the invoice/quote form
 * (P17/FE-M4 + FE-L3).
 *
 * Form data itself is managed by React Hook Form (single source of
 * truth). This store owns exactly one cross-cutting signal:
 * - hasUnsavedChanges — written by invoice-form.tsx (dirty watch),
 *   read by use-unsaved-changes-guard.ts (the beforeunload dialog).
 *
 * The P16/P17 sweeps deleted the unconsumed UI fields
 * (sidebarCollapsed / compactMode / bcrsEnabled / currentTotals /
 * updateTotals / resetStore) and createInvoiceLine — line templates
 * live in shared/schemas/invoice.ts (createEmptyLine).
 */

interface InvoiceUIState {
  hasUnsavedChanges: boolean;
  setHasUnsavedChanges: (hasChanges: boolean) => void;
}

export const useInvoiceStore = create<InvoiceUIState>()((set) => ({
  hasUnsavedChanges: false,
  setHasUnsavedChanges: (hasChanges) => set({ hasUnsavedChanges: hasChanges }),
}));
