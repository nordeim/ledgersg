/**
 * Integration Tests for BankTransactionsTab Component
 * 
 * Testing Strategy:
 * - Integration tests focusing on component wiring
 * - User interaction flows (filter changes, modal triggers)
 * - State management validation
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi } from "vitest";
import BankingClient from "../banking-client";

// Mock auth provider
vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({
    currentOrg: { id: "org-1", name: "Test Org" },
    isLoading: false,
  }),
}));

// Mock banking hooks
vi.mock("@/hooks/use-banking", () => ({
  useBankAccounts: () => ({
    data: {
      results: [
        { id: "acc-1", account_name: "DBS Current", bank_name: "DBS", account_number: "1234" },
      ],
      count: 1,
    },
    isLoading: false,
  }),
  useBankTransactions: () => ({
    data: {
      results: [
        {
          id: "txn-1",
          amount: "100.00",
          description: "Payment from John",
          transaction_date: "2024-01-15",
          is_reconciled: false,
        },
      ],
      count: 1,
    },
    isLoading: false,
  }),
  useImportBankTransactions: () => ({
    mutateAsync: vi.fn(),
    isLoading: false,
  }),
  useReconcileTransaction: () => ({
    mutateAsync: vi.fn(),
    isLoading: false,
  }),
  useSuggestMatches: () => ({
    data: [],
    isLoading: false,
  }),
}));

// Test wrapper
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

describe("BankTransactionsTab Integration", () => {
  it("should render tab trigger with correct icon and label", () => {
    render(<BankingClient />, { wrapper: createWrapper() });
    expect(screen.getByRole("tab", { name: /transactions/i })).toBeInTheDocument();
  });

  it("should render TransactionFilters component when tab is active", async () => {
    render(<BankingClient />, { wrapper: createWrapper() });

    const transactionsTab = screen.getByRole("tab", { name: /transactions/i });
    fireEvent.click(transactionsTab);

    await waitFor(() => {
      expect(screen.getByTestId("transaction-filters")).toBeInTheDocument();
    });
  });

  it("should render ReconciliationSummary component", async () => {
    render(<BankingClient />, { wrapper: createWrapper() });

    const transactionsTab = screen.getByRole("tab", { name: /transactions/i });
    fireEvent.click(transactionsTab);

    await waitFor(() => {
      expect(screen.getByTestId("reconciliation-summary")).toBeInTheDocument();
    });
  });

  it("should render TransactionList component", async () => {
    render(<BankingClient />, { wrapper: createWrapper() });

    const transactionsTab = screen.getByRole("tab", { name: /transactions/i });
    fireEvent.click(transactionsTab);

    await waitFor(() => {
      expect(screen.getByTestId("transactions-list")).toBeInTheDocument();
    });
  });

  it("should have Import button", async () => {
    render(<BankingClient />, { wrapper: createWrapper() });

    const transactionsTab = screen.getByRole("tab", { name: /transactions/i });
    fireEvent.click(transactionsTab);

    await waitFor(() => {
      const importButton = screen.getByRole("button", { name: /import/i });
      expect(importButton).toBeInTheDocument();
    });
  });

  it("should open ImportTransactionsForm when Import button is clicked", async () => {
    render(<BankingClient />, { wrapper: createWrapper() });

    const transactionsTab = screen.getByRole("tab", { name: /transactions/i });
    fireEvent.click(transactionsTab);

    await waitFor(() => {
      const importButton = screen.getByRole("button", { name: /import/i });
      fireEvent.click(importButton);
    });

    await waitFor(() => {
      expect(screen.getByText(/Import Bank Statement/i)).toBeInTheDocument();
    });
  });

  it("should match PaymentsTab implementation pattern", async () => {
    render(<BankingClient />, { wrapper: createWrapper() });

    const transactionsTab = screen.getByRole("tab", { name: /transactions/i });
    fireEvent.click(transactionsTab);

    await waitFor(() => {
      expect(screen.getByTestId("transaction-filters")).toBeInTheDocument();
      expect(screen.getByTestId("reconciliation-summary")).toBeInTheDocument();
      expect(screen.getByTestId("transactions-list")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /import/i })).toBeInTheDocument();
    });
  });
});
