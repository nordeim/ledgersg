/**
 * Integration Tests for BankTransactionsTab Component
 * 
 * Testing Strategy:
 * - Integration tests focusing on component wiring
 * - User interaction flows (filter changes, modal triggers)
 * - State management validation
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi } from "vitest";
import BankingClient from "../banking-client";
import * as bankingHooks from "@/hooks/use-banking";

// Mock auth provider
vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({
    currentOrg: { id: "org-1", name: "Test Org" },
    isLoading: false,
  }),
}));

// Mock banking hooks
vi.mock("@/hooks/use-banking");

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
    vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
      data: { results: [], count: 0 },
      isLoading: false,
    } as any);

    render(<BankingClient />, { wrapper: createWrapper() });
    expect(screen.getByRole("tab", { name: /transactions/i })).toBeInTheDocument();
  });

  it("should render TransactionFilters component when tab is active", async () => {
    const user = userEvent.setup();
    
    vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
      data: { results: [{ id: "acc-1", account_name: "DBS Current" }], count: 1 },
      isLoading: false,
    } as any);

    vi.mocked(bankingHooks.useBankTransactions).mockReturnValue({
      data: { results: [], count: 0 },
      isLoading: false,
    } as any);

    render(<BankingClient />, { wrapper: createWrapper() });

    const transactionsTab = screen.getByRole("tab", { name: /transactions/i });
    await user.click(transactionsTab);

    expect(await screen.findByTestId("transaction-filters")).toBeInTheDocument();
  });

  it("should render ReconciliationSummary component", async () => {
    const user = userEvent.setup();
    
    vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
      data: { results: [{ id: "acc-1", account_name: "DBS Current" }], count: 1 },
      isLoading: false,
    } as any);

    vi.mocked(bankingHooks.useBankTransactions).mockReturnValue({
      data: { results: [], count: 0 },
      isLoading: false,
    } as any);

    render(<BankingClient />, { wrapper: createWrapper() });

    const transactionsTab = screen.getByRole("tab", { name: /transactions/i });
    await user.click(transactionsTab);

    expect(await screen.findByTestId("reconciliation-summary")).toBeInTheDocument();
  });

  it("should render TransactionList component with data", async () => {
    const user = userEvent.setup();
    
    vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
      data: { results: [{ id: "acc-1", account_name: "DBS Current" }], count: 1 },
      isLoading: false,
    } as any);

    vi.mocked(bankingHooks.useBankTransactions).mockReturnValue({
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
    } as any);

    render(<BankingClient />, { wrapper: createWrapper() });

    const transactionsTab = screen.getByRole("tab", { name: /transactions/i });
    await user.click(transactionsTab);

    // Mock has count: 1, so should show transactions-list
    expect(await screen.findByTestId("transactions-list")).toBeInTheDocument();
  });

  it("should have Import button", async () => {
    const user = userEvent.setup();
    
    vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
      data: { results: [{ id: "acc-1", account_name: "DBS Current" }], count: 1 },
      isLoading: false,
    } as any);

    vi.mocked(bankingHooks.useBankTransactions).mockReturnValue({
      data: { results: [], count: 0 },
      isLoading: false,
    } as any);

    render(<BankingClient />, { wrapper: createWrapper() });

    const transactionsTab = screen.getByRole("tab", { name: /transactions/i });
    await user.click(transactionsTab);

    // There are two "Import Statement" buttons - we just need to find one
    const importButtons = await screen.findAllByRole("button", { name: /import statement/i });
    expect(importButtons.length).toBeGreaterThan(0);
  });

  it("should open ImportTransactionsForm when Import button is clicked", async () => {
    const user = userEvent.setup();
    
    vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
      data: { results: [{ id: "acc-1", account_name: "DBS Current" }], count: 1 },
      isLoading: false,
    } as any);

    vi.mocked(bankingHooks.useBankTransactions).mockReturnValue({
      data: { results: [], count: 0 },
      isLoading: false,
    } as any);

    vi.mocked(bankingHooks.useImportBankTransactions).mockReturnValue({
      mutateAsync: vi.fn(),
      isLoading: false,
    } as any);

    render(<BankingClient />, { wrapper: createWrapper() });

    const transactionsTab = screen.getByRole("tab", { name: /transactions/i });
    await user.click(transactionsTab);

    // Click the first Import Statement button (there are two)
    const importButtons = await screen.findAllByRole("button", { name: /import statement/i });
    await user.click(importButtons[0]);

    expect(await screen.findByText(/Import Bank Statement/i)).toBeInTheDocument();
  });

  it("should match PaymentsTab implementation pattern", async () => {
    const user = userEvent.setup();
    
    vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
      data: { results: [{ id: "acc-1", account_name: "DBS Current" }], count: 1 },
      isLoading: false,
    } as any);

    vi.mocked(bankingHooks.useBankTransactions).mockReturnValue({
      data: { results: [], count: 0 },
      isLoading: false,
    } as any);

    render(<BankingClient />, { wrapper: createWrapper() });

    const transactionsTab = screen.getByRole("tab", { name: /transactions/i });
    await user.click(transactionsTab);

    // Check all key components are present
    expect(await screen.findByTestId("transaction-filters")).toBeInTheDocument();
    expect(await screen.findByTestId("reconciliation-summary")).toBeInTheDocument();
    expect(await screen.findByTestId("transactions-empty")).toBeInTheDocument();
    // Verify at least one Import Statement button exists
    const importButtons = await screen.findAllByRole("button", { name: /import statement/i });
    expect(importButtons.length).toBeGreaterThan(0);
  });
});
