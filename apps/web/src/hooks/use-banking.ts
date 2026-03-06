/**
 * Banking Hooks - LedgerSG Frontend
 *
 * Provides hooks for banking operations:
 * - Bank accounts CRUD
 * - Payments (receive/make)
 * - Payment allocation
 * - Bank reconciliation
 *
 * All hooks use TanStack Query for caching and state management.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, endpoints } from "@/lib/api-client";
import { toast } from "@/hooks/use-toast";
import type {
  BankAccount,
  BankAccountInput,
  BankAccountUpdate,
  Payment,
  PaymentReceiveInput,
  PaymentMakeInput,
  PaymentVoidInput,
} from "@/shared/schemas";

// ============================================
// BANK ACCOUNTS
// ============================================

/**
 * List bank accounts with optional filters
 */
export function useBankAccounts(
  orgId: string | null,
  filters?: {
    is_active?: boolean;
    currency?: string;
    search?: string;
  }
) {
  const queryString = filters
    ? "?" + new URLSearchParams(
        Object.entries(filters).filter(([, v]) => v !== undefined && v !== null) as [string, string][]
      ).toString()
    : "";

  return useQuery({
    queryKey: [orgId, "bank-accounts", filters],
    queryFn: async () => {
      const response = await api.get<{
        results: BankAccount[];
        count: number;
        next?: string;
        previous?: string;
      }>(endpoints.banking(orgId!).accounts + queryString);
      return response;
    },
    enabled: !!orgId,
  });
}

/**
 * Get single bank account detail
 */
export function useBankAccount(orgId: string | null, accountId: string | null) {
  return useQuery({
    queryKey: [orgId, "bank-accounts", accountId],
    queryFn: async () => {
      const response = await api.get<BankAccount>(
        endpoints.banking(orgId!).accountDetail(accountId!)
      );
      return response;
    },
    enabled: !!orgId && !!accountId,
  });
}

/**
 * Create bank account
 */
export function useCreateBankAccount(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: BankAccountInput) => {
      const response = await api.post<BankAccount>(
        endpoints.banking(orgId).accounts,
        data
      );
      return response;
    },
    onSuccess: () => {
      toast({
        title: "Bank account created",
        description: "Your bank account has been created successfully.",
        variant: "success",
      });
      queryClient.invalidateQueries({ queryKey: [orgId, "bank-accounts"] });
      queryClient.invalidateQueries({ queryKey: [orgId, "dashboard"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to create bank account",
        description: error.message || "An error occurred while creating the bank account.",
        variant: "error",
      });
    },
  });
}

/**
 * Update bank account
 */
export function useUpdateBankAccount(orgId: string, accountId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: BankAccountUpdate) => {
      const response = await api.patch<BankAccount>(
        endpoints.banking(orgId).accountDetail(accountId),
        data
      );
      return response;
    },
    onSuccess: () => {
      toast({
        title: "Bank account updated",
        description: "Your bank account has been updated successfully.",
        variant: "success",
      });
      queryClient.invalidateQueries({ queryKey: [orgId, "bank-accounts", accountId] });
      queryClient.invalidateQueries({ queryKey: [orgId, "bank-accounts"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to update bank account",
        description: error.message || "An error occurred while updating the bank account.",
        variant: "error",
      });
    },
  });
}

/**
 * Deactivate bank account (soft delete)
 */
export function useDeactivateBankAccount(orgId: string, accountId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await api.delete<{ id: string; is_active: boolean }>(
        endpoints.banking(orgId).accountDetail(accountId)
      );
      return response;
    },
    onSuccess: () => {
      toast({
        title: "Bank account deactivated",
        description: "The bank account has been deactivated successfully.",
        variant: "success",
      });
      queryClient.invalidateQueries({ queryKey: [orgId, "bank-accounts"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to deactivate bank account",
        description: error.message || "An error occurred while deactivating the bank account.",
        variant: "error",
      });
    },
  });
}

// ============================================
// PAYMENTS
// ============================================

/**
 * List payments with optional filters
 */
export function usePayments(
  orgId: string | null,
  filters?: {
    payment_type?: "RECEIVED" | "MADE";
    contact_id?: string;
    bank_account_id?: string;
    date_from?: string;
    date_to?: string;
    is_reconciled?: boolean | null;
    is_voided?: boolean;
  }
) {
  const queryString = filters
    ? "?" + new URLSearchParams(
        Object.entries(filters).filter(([, v]) => v !== undefined && v !== null) as [string, string][]
      ).toString()
    : "";

  return useQuery({
    queryKey: [orgId, "payments", filters],
    queryFn: async () => {
      const response = await api.get<{
        results: Payment[];
        count: number;
        next?: string;
        previous?: string;
      }>(endpoints.banking(orgId!).payments + queryString);
      return response;
    },
    enabled: !!orgId,
  });
}

/**
 * Get single payment detail
 */
export function usePayment(orgId: string | null, paymentId: string | null) {
  return useQuery({
    queryKey: [orgId, "payments", paymentId],
    queryFn: async () => {
      const response = await api.get<Payment>(
        endpoints.banking(orgId!).paymentDetail(paymentId!)
      );
      return response;
    },
    enabled: !!orgId && !!paymentId,
  });
}

/**
 * Receive payment from customer
 */
export function useReceivePayment(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: PaymentReceiveInput) => {
      const response = await api.post<Payment>(
        endpoints.banking(orgId).receivePayment,
        data
      );
      return response;
    },
    onSuccess: () => {
      toast({
        title: "Payment received",
        description: "The payment has been recorded successfully.",
        variant: "success",
      });
      queryClient.invalidateQueries({ queryKey: [orgId, "payments"] });
      queryClient.invalidateQueries({ queryKey: [orgId, "dashboard"] });
      queryClient.invalidateQueries({ queryKey: [orgId, "invoices"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to receive payment",
        description: error.message || "An error occurred while receiving the payment.",
        variant: "error",
      });
    },
  });
}

/**
 * Make payment to supplier
 */
export function useMakePayment(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: PaymentMakeInput) => {
      const response = await api.post<Payment>(
        endpoints.banking(orgId).makePayment,
        data
      );
      return response;
    },
    onSuccess: () => {
      toast({
        title: "Payment made",
        description: "The payment has been recorded successfully.",
        variant: "success",
      });
      queryClient.invalidateQueries({ queryKey: [orgId, "payments"] });
      queryClient.invalidateQueries({ queryKey: [orgId, "dashboard"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to make payment",
        description: error.message || "An error occurred while making the payment.",
        variant: "error",
      });
    },
  });
}

/**
 * Allocate payment to invoices/bills
 */
export function useAllocatePayment(orgId: string, paymentId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: { allocations: Array<{ document_id: string; allocated_amount: string }> }) => {
      const response = await api.post<Payment>(
        endpoints.banking(orgId).allocatePayment(paymentId),
        data
      );
      return response;
    },
    onSuccess: () => {
      toast({
        title: "Payment allocated",
        description: "The payment has been allocated successfully.",
        variant: "success",
      });
      queryClient.invalidateQueries({ queryKey: [orgId, "payments", paymentId] });
      queryClient.invalidateQueries({ queryKey: [orgId, "payments"] });
      queryClient.invalidateQueries({ queryKey: [orgId, "invoices"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to allocate payment",
        description: error.message || "An error occurred while allocating the payment.",
        variant: "error",
      });
    },
  });
}

/**
 * Void payment
 */
export function useVoidPayment(orgId: string, paymentId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: PaymentVoidInput) => {
      const response = await api.post<Payment>(
        endpoints.banking(orgId).voidPayment(paymentId),
        data
      );
      return response;
    },
    onSuccess: () => {
      toast({
        title: "Payment voided",
        description: "The payment has been voided successfully.",
        variant: "warning",
      });
      queryClient.invalidateQueries({ queryKey: [orgId, "payments"] });
      queryClient.invalidateQueries({ queryKey: [orgId, "dashboard"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to void payment",
        description: error.message || "An error occurred while voiding the payment.",
        variant: "error",
      });
    },
  });
}

// ============================================
// BANK TRANSACTIONS (RECONCILIATION)
// ============================================

/**
 * Bank transaction type
 */
interface BankTransaction {
  id: string;
  org: string;
  bank_account: string;
  bank_account_name?: string;
  transaction_date: string;
  value_date?: string;
  description: string;
  reference?: string;
  amount: string;
  running_balance?: string;
  is_reconciled: boolean;
  reconciled_at?: string;
  matched_payment?: string;
  import_source: "CSV" | "OFX" | "MT940" | "API";
  external_id?: string;
  created_at: string;
  updated_at: string;
}

/**
 * List bank transactions with optional filters
 */
export function useBankTransactions(
  orgId: string | null,
  filters?: {
    bank_account_id?: string;
    date_from?: string;
    date_to?: string;
    is_reconciled?: boolean | null;
    unreconciled_only?: boolean;
  }
) {
  const queryString = filters
    ? "?" + new URLSearchParams(
        Object.entries(filters).filter(([, v]) => v !== undefined && v !== null) as [string, string][]
      ).toString()
    : "";

  return useQuery({
    queryKey: [orgId, "bank-transactions", filters],
    queryFn: async () => {
      const response = await api.get<{
        results: BankTransaction[];
        count: number;
        next?: string;
        previous?: string;
      }>(endpoints.banking(orgId!).transactions + queryString);
      return response;
    },
    enabled: !!orgId,
  });
}

/**
 * Import bank transactions from CSV
 */
export function useImportBankTransactions(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: { bank_account_id: string; file: File }) => {
      const formData = new FormData();
      formData.append("bank_account_id", data.bank_account_id);
      formData.append("file", data.file);

      const response = await api.post<{
        imported: number;
        duplicates: number;
        errors?: Array<{ row: number; message: string }>;
      }>(
        endpoints.banking(orgId).transactionImport,
        formData
      );
      return response;
    },
    onSuccess: (data) => {
      toast({
        title: "Transactions imported",
        description: `Imported ${data.imported} transactions. ${data.duplicates > 0 ? `${data.duplicates} duplicates skipped.` : ''}`,
        variant: "success",
      });
      queryClient.invalidateQueries({ queryKey: [orgId, "bank-transactions"] });
      queryClient.invalidateQueries({ queryKey: [orgId, "dashboard"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to import transactions",
        description: error.message || "An error occurred while importing transactions.",
        variant: "error",
      });
    },
  });
}

/**
 * Reconcile bank transaction to payment
 */
export function useReconcileTransaction(orgId: string, transactionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: { payment_id: string }) => {
      const response = await api.post<BankTransaction>(
        endpoints.banking(orgId).transactionReconcile(transactionId),
        data
      );
      return response;
    },
    onSuccess: () => {
      toast({
        title: "Transaction reconciled",
        description: "The transaction has been reconciled successfully.",
        variant: "success",
      });
      queryClient.invalidateQueries({ queryKey: [orgId, "bank-transactions"] });
      queryClient.invalidateQueries({ queryKey: [orgId, "payments"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to reconcile transaction",
        description: error.message || "An error occurred while reconciling the transaction.",
        variant: "error",
      });
    },
  });
}

/**
 * Unreconcile bank transaction
 */
export function useUnreconcileTransaction(orgId: string, transactionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await api.post<BankTransaction>(
        endpoints.banking(orgId).transactionUnreconcile(transactionId)
      );
      return response;
    },
    onSuccess: () => {
      toast({
        title: "Transaction unreconciled",
        description: "The reconciliation has been removed successfully.",
        variant: "success",
      });
      queryClient.invalidateQueries({ queryKey: [orgId, "bank-transactions"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to unreconcile transaction",
        description: error.message || "An error occurred while unreconciling the transaction.",
        variant: "error",
      });
    },
  });
}

/**
 * Suggest payment matches for a bank transaction
 */
export function useSuggestMatches(
  orgId: string | null,
  transactionId: string | null,
  tolerance?: string
) {
  const queryString = tolerance
    ? `?tolerance=${tolerance}`
    : "";

  interface PaymentMatch {
    payment_id: string;
    payment_number: string;
    amount: string;
    contact_name: string;
    match_score: number;
  }

  return useQuery({
    queryKey: [orgId, "bank-transactions", transactionId, "matches", tolerance],
    queryFn: async () => {
      const response = await api.get<PaymentMatch[]>(
        endpoints.banking(orgId!).transactionSuggestMatches(transactionId!) + queryString
      );
      return response;
    },
    enabled: !!orgId && !!transactionId,
  });
}
