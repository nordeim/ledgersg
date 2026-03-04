/**
 * Banking Hooks Tests (TDD)
 *
 * Tests validate:
 * - Query hooks fetch data correctly
 * - Filters are applied properly
 * - Mutations create/update/delete resources
 * - Cache invalidation works correctly
 * - Toast notifications display
 * - Error handling
 *
 * Backend Reference: apps/backend/apps/banking/
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@/__tests__/utils";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useBankAccounts,
  useBankAccount,
  useCreateBankAccount,
  useUpdateBankAccount,
  useDeactivateBankAccount,
  usePayments,
  usePayment,
  useReceivePayment,
  useMakePayment,
  useAllocatePayment,
  useVoidPayment,
  useBankTransactions,
  useImportBankTransactions,
  useReconcileTransaction,
  useUnreconcileTransaction,
  useSuggestMatches,
} from "../use-banking";
import * as apiClient from "@/lib/api-client";
import { toast } from "@/hooks/use-toast";

// Mock API client
vi.mock("@/lib/api-client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  endpoints: {
    banking: (orgId: string) => ({
      accounts: `/api/v1/${orgId}/banking/bank-accounts/`,
      accountDetail: (id: string) => `/api/v1/${orgId}/banking/bank-accounts/${id}/`,
      payments: `/api/v1/${orgId}/banking/payments/`,
      paymentDetail: (id: string) => `/api/v1/${orgId}/banking/payments/${id}/`,
      receivePayment: `/api/v1/${orgId}/banking/payments/receive/`,
      makePayment: `/api/v1/${orgId}/banking/payments/make/`,
      allocatePayment: (id: string) => `/api/v1/${orgId}/banking/payments/${id}/allocate/`,
      voidPayment: (id: string) => `/api/v1/${orgId}/banking/payments/${id}/void/`,
      transactions: `/api/v1/${orgId}/banking/bank-transactions/`,
      transactionImport: `/api/v1/${orgId}/banking/bank-transactions/import/`,
      transactionReconcile: (id: string) => `/api/v1/${orgId}/banking/bank-transactions/${id}/reconcile/`,
      transactionUnreconcile: (id: string) => `/api/v1/${orgId}/banking/bank-transactions/${id}/unreconcile/`,
      transactionSuggestMatches: (id: string) => `/api/v1/${orgId}/banking/bank-transactions/${id}/suggest-matches/`,
    }),
  },
}));

// Mock toast
vi.mock("@/hooks/use-toast", () => ({
  toast: vi.fn(),
}));

// Helper to create wrapper with QueryClient
const createWrapper = (queryClient?: QueryClient) => {
  const client = queryClient || new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={client}>
        {children}
      </QueryClientProvider>
    );
  };
};

describe("Banking Hooks", () => {
  const validOrgId = "550e8400-e29b-41d4-a716-446655440001";
  const validAccountId = "550e8400-e29b-41d4-a716-446655440002";
  const validPaymentId = "550e8400-e29b-41d4-a716-446655440003";
  const validTransactionId = "550e8400-e29b-41d4-a716-446655440004";

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================
  // BANK ACCOUNTS
  // ============================================

  describe("useBankAccounts", () => {
    it("should fetch bank accounts list", async () => {
      const mockAccounts = [
        {
          id: validAccountId,
          account_name: "Main Operating Account",
          bank_name: "DBS Bank",
          account_number: "1234567890",
          currency: "SGD",
          is_active: true,
          opening_balance: "10000.0000",
        },
        {
          id: "550e8400-e29b-41d4-a716-446655440005",
          account_name: "USD Account",
          bank_name: "OCBC Bank",
          account_number: "9876543210",
          currency: "USD",
          is_active: true,
          opening_balance: "5000.0000",
        },
      ];

      vi.mocked(apiClient.api.get).mockResolvedValueOnce({
        results: mockAccounts,
        count: 2,
      });

      const { result } = renderHook(() => useBankAccounts(validOrgId), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.results).toHaveLength(2);
      expect(result.current.data?.results[0].account_name).toBe("Main Operating Account");
    });

    it("should apply filters to query", async () => {
      vi.mocked(apiClient.api.get).mockResolvedValueOnce({ results: [], count: 0 });

      renderHook(
        () => useBankAccounts(validOrgId, { is_active: true, currency: "SGD" }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(apiClient.api.get).toHaveBeenCalled());

      expect(apiClient.api.get).toHaveBeenCalledWith(
        expect.stringContaining("is_active=true")
      );
      expect(apiClient.api.get).toHaveBeenCalledWith(
        expect.stringContaining("currency=SGD")
      );
    });

    it("should be disabled when orgId is null", () => {
      const { result } = renderHook(() => useBankAccounts(null), {
        wrapper: createWrapper(),
      });

      // When orgId is null, enabled is false, so the query is not running
      expect(result.current.fetchStatus).toBe("idle");
      expect(apiClient.api.get).not.toHaveBeenCalled();
    });

    it("should handle search filter", async () => {
      vi.mocked(apiClient.api.get).mockResolvedValueOnce({ results: [], count: 0 });

      renderHook(
        () => useBankAccounts(validOrgId, { search: "DBS" }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(apiClient.api.get).toHaveBeenCalled());

      expect(apiClient.api.get).toHaveBeenCalledWith(
        expect.stringContaining("search=DBS")
      );
    });

    it("should construct correct query key", async () => {
      const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

      vi.mocked(apiClient.api.get).mockResolvedValueOnce({ results: [], count: 0 });

      renderHook(
        () => useBankAccounts(validOrgId, { currency: "USD" }),
        { wrapper: createWrapper(queryClient) }
      );

      await waitFor(() => expect(apiClient.api.get).toHaveBeenCalled());

      const cache = queryClient.getQueryCache();
      const queries = cache.findAll();

      expect(queries.length).toBeGreaterThan(0);
      expect(queries[0].queryKey).toContain(validOrgId);
      expect(queries[0].queryKey).toContain("bank-accounts");
    });
  });

  describe("useBankAccount", () => {
    it("should fetch single bank account", async () => {
      const mockAccount = {
        id: validAccountId,
        account_name: "Main Operating Account",
        bank_name: "DBS Bank",
        account_number: "1234567890",
        currency: "SGD",
        is_active: true,
        opening_balance: "10000.0000",
      };

      vi.mocked(apiClient.api.get).mockResolvedValueOnce(mockAccount);

      const { result } = renderHook(
        () => useBankAccount(validOrgId, validAccountId),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockAccount);
      expect(apiClient.api.get).toHaveBeenCalledWith(
        expect.stringContaining(validAccountId)
      );
    });

    it("should be disabled when accountId is null", () => {
      const { result } = renderHook(
        () => useBankAccount(validOrgId, null),
        { wrapper: createWrapper() }
      );

      expect(result.current.fetchStatus).toBe("idle");
      expect(apiClient.api.get).not.toHaveBeenCalled();
    });

    it("should be disabled when orgId is null", () => {
      const { result } = renderHook(
        () => useBankAccount(null, validAccountId),
        { wrapper: createWrapper() }
      );

      expect(result.current.fetchStatus).toBe("idle");
      expect(apiClient.api.get).not.toHaveBeenCalled();
    });
  });

  describe("useCreateBankAccount", () => {
    it("should create bank account and invalidate queries", async () => {
      const mockAccount = {
        id: "new-acc",
        account_name: "New Account",
        bank_name: "DBS Bank",
      };

      vi.mocked(apiClient.api.post).mockResolvedValueOnce(mockAccount);

      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      });
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const { result } = renderHook(() => useCreateBankAccount(validOrgId), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({
          account_name: "New Account",
          bank_name: "DBS",
          account_number: "123",
          gl_account: "550e8400-e29b-41d4-a716-446655440006",
        });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(apiClient.api.post).toHaveBeenCalledWith(
        expect.stringContaining("/bank-accounts/"),
        expect.objectContaining({ account_name: "New Account" })
      );

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: [validOrgId, "bank-accounts"],
      });

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: [validOrgId, "dashboard"],
      });
    });

    it("should show success toast", async () => {
      const mockAccount = { id: "new-acc" };
      vi.mocked(apiClient.api.post).mockResolvedValueOnce(mockAccount);

      const { result } = renderHook(() => useCreateBankAccount(validOrgId), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({
          account_name: "New Account",
          bank_name: "DBS",
          account_number: "123",
          gl_account: "550e8400-e29b-41d4-a716-446655440006",
        });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Bank account created",
          variant: "success",
        })
      );
    });

    it("should handle errors", async () => {
      const error = new Error("Bank name cannot be blank");
      vi.mocked(apiClient.api.post).mockRejectedValueOnce(error);

      const { result } = renderHook(() => useCreateBankAccount(validOrgId), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({
          account_name: "",
          bank_name: "",
          account_number: "",
          gl_account: "",
        });
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Failed to create bank account",
          variant: "error",
        })
      );
    });
  });

  describe("useUpdateBankAccount", () => {
    it("should update bank account", async () => {
      const mockAccount = {
        id: validAccountId,
        account_name: "Updated Account",
      };

      vi.mocked(apiClient.api.patch).mockResolvedValueOnce(mockAccount);

      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      });
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const { result } = renderHook(
        () => useUpdateBankAccount(validOrgId, validAccountId),
        { wrapper: createWrapper(queryClient) }
      );

      await act(async () => {
        result.current.mutate({ account_name: "Updated Account" });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(apiClient.api.patch).toHaveBeenCalledWith(
        expect.stringContaining(validAccountId),
        expect.objectContaining({ account_name: "Updated Account" })
      );

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: [validOrgId, "bank-accounts", validAccountId],
      });

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: [validOrgId, "bank-accounts"],
      });
    });
  });

  describe("useDeactivateBankAccount", () => {
    it("should deactivate bank account", async () => {
      const mockResponse = {
        id: validAccountId,
        is_active: false,
      };

      vi.mocked(apiClient.api.delete).mockResolvedValueOnce(mockResponse);

      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      });
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const { result } = renderHook(
        () => useDeactivateBankAccount(validOrgId, validAccountId),
        { wrapper: createWrapper(queryClient) }
      );

      await act(async () => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(apiClient.api.delete).toHaveBeenCalledWith(
        expect.stringContaining(validAccountId)
      );

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: [validOrgId, "bank-accounts"],
      });

      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Bank account deactivated",
          variant: "success",
        })
      );
    });
  });

  // ============================================
  // PAYMENTS
  // ============================================

  describe("usePayments", () => {
    it("should fetch payments list", async () => {
      const mockPayments = [
        {
          id: validPaymentId,
          payment_type: "RECEIVED",
          payment_number: "RCP-000001",
          amount: "1000.0000",
        },
        {
          id: "550e8400-e29b-41d4-a716-446655440007",
          payment_type: "MADE",
          payment_number: "PAY-000001",
          amount: "5000.0000",
        },
      ];

      vi.mocked(apiClient.api.get).mockResolvedValueOnce({
        results: mockPayments,
        count: 2,
      });

      const { result } = renderHook(() => usePayments(validOrgId), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.results).toHaveLength(2);
      expect(result.current.data?.results[0].payment_type).toBe("RECEIVED");
    });

    it("should filter by payment_type", async () => {
      vi.mocked(apiClient.api.get).mockResolvedValueOnce({ results: [], count: 0 });

      renderHook(
        () => usePayments(validOrgId, { payment_type: "RECEIVED" }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(apiClient.api.get).toHaveBeenCalled());

      expect(apiClient.api.get).toHaveBeenCalledWith(
        expect.stringContaining("payment_type=RECEIVED")
      );
    });

    it("should filter by date range", async () => {
      vi.mocked(apiClient.api.get).mockResolvedValueOnce({ results: [], count: 0 });

      renderHook(
        () => usePayments(validOrgId, {
          date_from: "2024-01-01",
          date_to: "2024-12-31",
        }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(apiClient.api.get).toHaveBeenCalled());

      expect(apiClient.api.get).toHaveBeenCalledWith(
        expect.stringContaining("date_from=2024-01-01")
      );
      expect(apiClient.api.get).toHaveBeenCalledWith(
        expect.stringContaining("date_to=2024-12-31")
      );
    });

    it("should be disabled when orgId is null", () => {
      const { result } = renderHook(() => usePayments(null), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
      expect(apiClient.api.get).not.toHaveBeenCalled();
    });
  });

  describe("usePayment", () => {
    it("should fetch single payment", async () => {
      const mockPayment = {
        id: validPaymentId,
        payment_type: "RECEIVED",
        payment_number: "RCP-000001",
        amount: "1000.0000",
        allocations: [],
      };

      vi.mocked(apiClient.api.get).mockResolvedValueOnce(mockPayment);

      const { result } = renderHook(
        () => usePayment(validOrgId, validPaymentId),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockPayment);
    });

    it("should be disabled when paymentId is null", () => {
      const { result } = renderHook(
        () => usePayment(validOrgId, null),
        { wrapper: createWrapper() }
      );

      expect(result.current.fetchStatus).toBe("idle");
      expect(apiClient.api.get).not.toHaveBeenCalled();
    });
  });

  describe("useReceivePayment", () => {
    it("should create received payment", async () => {
      const mockPayment = {
        id: validPaymentId,
        payment_type: "RECEIVED",
        payment_number: "RCP-000001",
      };

      vi.mocked(apiClient.api.post).mockResolvedValueOnce(mockPayment);

      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      });
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const { result } = renderHook(() => useReceivePayment(validOrgId), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({
          contact_id: "550e8400-e29b-41d4-a716-446655440008",
          bank_account_id: validAccountId,
          payment_date: "2024-01-20",
          amount: "1000.0000",
          payment_method: "BANK_TRANSFER",
        });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(apiClient.api.post).toHaveBeenCalledWith(
        expect.stringContaining("/payments/receive/"),
        expect.objectContaining({ amount: "1000.0000" })
      );

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: [validOrgId, "payments"],
      });

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: [validOrgId, "dashboard"],
      });

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: [validOrgId, "invoices"],
      });

      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Payment received",
          variant: "success",
        })
      );
    });

    it("should handle errors", async () => {
      const error = new Error("Contact must be a customer");
      vi.mocked(apiClient.api.post).mockRejectedValueOnce(error);

      const { result } = renderHook(() => useReceivePayment(validOrgId), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({
          contact_id: "",
          bank_account_id: "",
          payment_date: "",
          amount: "0",
          payment_method: "BANK_TRANSFER",
        });
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Failed to receive payment",
          variant: "error",
        })
      );
    });
  });

  describe("useMakePayment", () => {
    it("should create made payment", async () => {
      const mockPayment = {
        id: validPaymentId,
        payment_type: "MADE",
        payment_number: "PAY-000001",
      };

      vi.mocked(apiClient.api.post).mockResolvedValueOnce(mockPayment);

      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      });
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const { result } = renderHook(() => useMakePayment(validOrgId), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({
          contact_id: "550e8400-e29b-41d4-a716-446655440009",
          bank_account_id: validAccountId,
          payment_date: "2024-01-20",
          amount: "5000.0000",
          payment_method: "GIRO",
        });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(apiClient.api.post).toHaveBeenCalledWith(
        expect.stringContaining("/payments/make/"),
        expect.objectContaining({ amount: "5000.0000" })
      );

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: [validOrgId, "payments"],
      });

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: [validOrgId, "dashboard"],
      });

      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Payment made",
          variant: "success",
        })
      );
    });
  });

  describe("useAllocatePayment", () => {
    it("should allocate payment to invoices", async () => {
      const mockPayment = {
        id: validPaymentId,
        is_reconciled: false,
      };

      vi.mocked(apiClient.api.post).mockResolvedValueOnce(mockPayment);

      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      });
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const { result } = renderHook(
        () => useAllocatePayment(validOrgId, validPaymentId),
        { wrapper: createWrapper(queryClient) }
      );

      await act(async () => {
        result.current.mutate({
          allocations: [
            {
              document_id: "550e8400-e29b-41d4-a716-446655440010",
              allocated_amount: "500.0000",
            },
          ],
        });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(apiClient.api.post).toHaveBeenCalledWith(
        expect.stringContaining("/allocate/"),
        expect.objectContaining({
          allocations: expect.arrayContaining([
            expect.objectContaining({ allocated_amount: "500.0000" }),
          ]),
        })
      );

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: [validOrgId, "payments", validPaymentId],
      });

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: [validOrgId, "payments"],
      });

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: [validOrgId, "invoices"],
      });

      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Payment allocated",
          variant: "success",
        })
      );
    });
  });

  describe("useVoidPayment", () => {
    it("should void payment", async () => {
      const mockPayment = {
        id: validPaymentId,
        is_voided: true,
      };

      vi.mocked(apiClient.api.post).mockResolvedValueOnce(mockPayment);

      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      });
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const { result } = renderHook(
        () => useVoidPayment(validOrgId, validPaymentId),
        { wrapper: createWrapper(queryClient) }
      );

      await act(async () => {
        result.current.mutate({ reason: "Duplicate entry" });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(apiClient.api.post).toHaveBeenCalledWith(
        expect.stringContaining("/void/"),
        expect.objectContaining({ reason: "Duplicate entry" })
      );

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: [validOrgId, "payments"],
      });

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: [validOrgId, "dashboard"],
      });

      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Payment voided",
          variant: "warning",
        })
      );
    });
  });

  // ============================================
  // BANK TRANSACTIONS (RECONCILIATION)
  // ============================================

  describe("useBankTransactions", () => {
    it("should fetch bank transactions list", async () => {
      const mockTransactions = [
        {
          id: validTransactionId,
          transaction_date: "2024-01-15",
          amount: "1000.0000",
          is_reconciled: false,
        },
      ];

      vi.mocked(apiClient.api.get).mockResolvedValueOnce({
        results: mockTransactions,
        count: 1,
      });

      const { result } = renderHook(() => useBankTransactions(validOrgId), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.results).toHaveLength(1);
    });

    it("should filter by bank_account_id", async () => {
      vi.mocked(apiClient.api.get).mockResolvedValueOnce({ results: [], count: 0 });

      renderHook(
        () => useBankTransactions(validOrgId, { bank_account_id: validAccountId }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(apiClient.api.get).toHaveBeenCalled());

      expect(apiClient.api.get).toHaveBeenCalledWith(
        expect.stringContaining("bank_account_id=")
      );
    });

    it("should filter unreconciled_only", async () => {
      vi.mocked(apiClient.api.get).mockResolvedValueOnce({ results: [], count: 0 });

      renderHook(
        () => useBankTransactions(validOrgId, { unreconciled_only: true }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(apiClient.api.get).toHaveBeenCalled());

      expect(apiClient.api.get).toHaveBeenCalledWith(
        expect.stringContaining("unreconciled_only=true")
      );
    });

    it("should be disabled when orgId is null", () => {
      const { result } = renderHook(() => useBankTransactions(null), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
      expect(apiClient.api.get).not.toHaveBeenCalled();
    });
  });

  describe("useImportBankTransactions", () => {
    it("should import bank transactions", async () => {
      const mockResult = {
        imported: 10,
        duplicates: 2,
      };

      vi.mocked(apiClient.api.post).mockResolvedValueOnce(mockResult);

      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      });
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const { result } = renderHook(() => useImportBankTransactions(validOrgId), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({
          bank_account_id: validAccountId,
          file: new File([], "transactions.csv"),
        });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: [validOrgId, "bank-transactions"],
      });

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: [validOrgId, "dashboard"],
      });

      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Transactions imported",
          variant: "success",
        })
      );
    });
  });

  describe("useReconcileTransaction", () => {
    it("should reconcile transaction to payment", async () => {
      const mockTransaction = {
        id: validTransactionId,
        is_reconciled: true,
      };

      vi.mocked(apiClient.api.post).mockResolvedValueOnce(mockTransaction);

      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      });
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const { result } = renderHook(
        () => useReconcileTransaction(validOrgId, validTransactionId),
        { wrapper: createWrapper(queryClient) }
      );

      await act(async () => {
        result.current.mutate({ payment_id: validPaymentId });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(apiClient.api.post).toHaveBeenCalledWith(
        expect.stringContaining("/reconcile/"),
        expect.objectContaining({ payment_id: validPaymentId })
      );

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: [validOrgId, "bank-transactions"],
      });

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: [validOrgId, "payments"],
      });

      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Transaction reconciled",
          variant: "success",
        })
      );
    });
  });

  describe("useUnreconcileTransaction", () => {
    it("should unreconcile transaction", async () => {
      const mockTransaction = {
        id: validTransactionId,
        is_reconciled: false,
      };

      vi.mocked(apiClient.api.post).mockResolvedValueOnce(mockTransaction);

      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      });
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const { result } = renderHook(
        () => useUnreconcileTransaction(validOrgId, validTransactionId),
        { wrapper: createWrapper(queryClient) }
      );

      await act(async () => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(apiClient.api.post).toHaveBeenCalledWith(
        expect.stringContaining("/unreconcile/")
      );

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: [validOrgId, "bank-transactions"],
      });

      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Transaction unreconciled",
          variant: "success",
        })
      );
    });
  });

  describe("useSuggestMatches", () => {
    it("should fetch match suggestions", async () => {
      const mockSuggestions = [
        {
          payment_id: validPaymentId,
          payment_number: "RCP-000001",
          amount: "1000.0000",
          match_score: 0.95,
        },
      ];

      vi.mocked(apiClient.api.get).mockResolvedValueOnce(mockSuggestions);

      const { result } = renderHook(
        () => useSuggestMatches(validOrgId, validTransactionId),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toHaveLength(1);
      expect(apiClient.api.get).toHaveBeenCalledWith(
        expect.stringContaining("/suggest-matches/")
      );
    });

    it("should pass tolerance parameter", async () => {
      vi.mocked(apiClient.api.get).mockResolvedValueOnce([]);

      renderHook(
        () => useSuggestMatches(validOrgId, validTransactionId, "2.00"),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(apiClient.api.get).toHaveBeenCalled());

      expect(apiClient.api.get).toHaveBeenCalledWith(
        expect.stringContaining("tolerance=2.00")
      );
    });

    it("should be disabled when transactionId is null", () => {
      const { result } = renderHook(
        () => useSuggestMatches(validOrgId, null),
        { wrapper: createWrapper() }
      );

      expect(result.current.fetchStatus).toBe("idle");
      expect(apiClient.api.get).not.toHaveBeenCalled();
    });
  });
});
