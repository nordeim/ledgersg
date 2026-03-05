/**
 * Banking Page Tests
 *
 * TDD tests for Phase 5.4: Banking UI Pages
 * Tests cover:
 * - Page rendering with tabs
 * - Bank accounts tab data fetching
 * - Empty states
 * - Error handling
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BankingClient } from "../banking-client";
import * as bankingHooks from "@/hooks/use-banking";

// Mock auth provider
vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({
    currentOrg: { id: "org-123", name: "Test Org" },
    isLoading: false,
  }),
}));

// Mock banking hooks
vi.mock("@/hooks/use-banking");

const mockBankAccounts = {
  results: [
    {
      id: "acc-1",
      org: "org-123",
      account_name: "Operating Account",
      bank_name: "DBS Bank",
      account_number: "1234567890",
      bank_code: "7171",
      branch_code: "001",
      currency: "SGD",
      gl_account: "gl-123",
      paynow_type: null,
      paynow_id: null,
      is_default: true,
      is_active: true,
      opening_balance: "10000.0000",
      opening_balance_date: "2026-01-01",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    {
      id: "acc-2",
      org: "org-123",
      account_name: "Savings Account",
      bank_name: "OCBC Bank",
      account_number: "9876543210",
      bank_code: "7339",
      branch_code: "001",
      currency: "SGD",
      gl_account: "gl-456",
      paynow_type: "UEN",
      paynow_id: "12345678A",
      is_default: false,
      is_active: true,
      opening_balance: "5000.0000",
      opening_balance_date: "2026-01-01",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ],
  count: 2,
};

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
};

describe("BankingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Page Structure", () => {
    it("should render page title and description", () => {
      vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
        data: mockBankAccounts,
        isLoading: false,
        error: null,
      } as any);

      render(<BankingClient />, { wrapper: createWrapper() });

      expect(screen.getByRole("heading", { name: /banking/i })).toBeInTheDocument();
      expect(screen.getByText(/manage bank accounts/i)).toBeInTheDocument();
    });

    it("should render three tabs: Accounts, Payments, Transactions", () => {
      vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
        data: mockBankAccounts,
        isLoading: false,
        error: null,
      } as any);

      render(<BankingClient />, { wrapper: createWrapper() });

      expect(screen.getByRole("tab", { name: /accounts/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /payments/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /transactions/i })).toBeInTheDocument();
    });

    it("should show Accounts tab as active by default", () => {
      vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
        data: mockBankAccounts,
        isLoading: false,
        error: null,
      } as any);

      render(<BankingClient />, { wrapper: createWrapper() });

      const accountsTab = screen.getByRole("tab", { name: /accounts/i });
      expect(accountsTab).toHaveAttribute("data-state", "active");
    });
  });

  describe("Bank Accounts Tab", () => {
    it("should display loading state while fetching accounts", () => {
      vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      } as any);

      render(<BankingClient />, { wrapper: createWrapper() });

      expect(screen.getByTestId("accounts-loading-skeleton")).toBeInTheDocument();
    });

    it("should display bank accounts list when data is loaded", async () => {
      vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
        data: mockBankAccounts,
        isLoading: false,
        error: null,
      } as any);

      render(<BankingClient />, { wrapper: createWrapper() });

      expect(screen.getByText("Operating Account")).toBeInTheDocument();
      expect(screen.getByText("Savings Account")).toBeInTheDocument();
      expect(screen.getByText(/DBS Bank/)).toBeInTheDocument();
      expect(screen.getByText(/OCBC Bank/)).toBeInTheDocument();
    });

    it("should display account balances formatted as currency", async () => {
      vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
        data: mockBankAccounts,
        isLoading: false,
        error: null,
      } as any);

      render(<BankingClient />, { wrapper: createWrapper() });

      expect(screen.getByText(/S\$ 10,000.00/i)).toBeInTheDocument();
      expect(screen.getByText(/S\$ 5,000.00/i)).toBeInTheDocument();
    });

    it("should show PayNow badge for accounts with PayNow configured", () => {
      vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
        data: mockBankAccounts,
        isLoading: false,
        error: null,
      } as any);

      render(<BankingClient />, { wrapper: createWrapper() });

      expect(screen.getByText("PayNow")).toBeInTheDocument();
      expect(screen.getByText("UEN")).toBeInTheDocument();
    });

    it("should display empty state when no accounts exist", () => {
      vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
        data: { results: [], count: 0 },
        isLoading: false,
        error: null,
      } as any);

      render(<BankingClient />, { wrapper: createWrapper() });

      expect(screen.getByText(/no bank accounts/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /add bank account/i })).toBeInTheDocument();
    });

    it("should display error state when fetch fails", () => {
      vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("Failed to fetch"),
      } as any);

      render(<BankingClient />, { wrapper: createWrapper() });

      expect(screen.getByText(/failed to load bank accounts/i)).toBeInTheDocument();
    });

    it("should have 'Add Account' button", () => {
      vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
        data: mockBankAccounts,
        isLoading: false,
        error: null,
      } as any);

      render(<BankingClient />, { wrapper: createWrapper() });

      expect(screen.getByRole("button", { name: /add account/i })).toBeInTheDocument();
    });
  });

  describe("Tab Navigation", () => {
  it("should switch to Payments tab when clicked", async () => {
    const user = userEvent.setup();
    vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
      data: mockBankAccounts,
      isLoading: false,
      error: null,
    } as any);
    
    // Mock usePayments hook
    vi.mocked(bankingHooks.usePayments).mockReturnValue({
      data: { results: [], count: 0, next: null, previous: null },
      isLoading: false,
      error: null,
    } as any);

    render(<BankingClient />, { wrapper: createWrapper() });

    const paymentsTab = screen.getByRole("tab", { name: /payments/i });
    await user.click(paymentsTab);

    expect(paymentsTab).toHaveAttribute("data-state", "active");
  });

    it("should switch to Transactions tab when clicked", async () => {
      const user = userEvent.setup();
      vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
        data: mockBankAccounts,
        isLoading: false,
        error: null,
      } as any);

      render(<BankingClient />, { wrapper: createWrapper() });

      const transactionsTab = screen.getByRole("tab", { name: /transactions/i });
      await user.click(transactionsTab);

      expect(transactionsTab).toHaveAttribute("data-state", "active");
    });

  it("should show Payments content", async () => {
    const user = userEvent.setup();
    vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
      data: mockBankAccounts,
      isLoading: false,
      error: null,
    } as any);
    
    // Mock usePayments hook
    vi.mocked(bankingHooks.usePayments).mockReturnValue({
      data: { results: [], count: 0, next: null, previous: null },
      isLoading: false,
      error: null,
    } as any);

    render(<BankingClient />, { wrapper: createWrapper() });

    const paymentsTab = screen.getByRole("tab", { name: /payments/i });
    await user.click(paymentsTab);

    // Check that payments tab shows filter controls (not placeholder)
    expect(screen.getByTestId("payment-filters")).toBeInTheDocument();
  });

    it("should show Transactions placeholder content", async () => {
      const user = userEvent.setup();
      vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
        data: mockBankAccounts,
        isLoading: false,
        error: null,
      } as any);

      render(<BankingClient />, { wrapper: createWrapper() });

      const transactionsTab = screen.getByRole("tab", { name: /transactions/i });
      await user.click(transactionsTab);

      expect(screen.getByText(/bank reconciliation module coming soon/i)).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have proper ARIA roles for tabs", () => {
      vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
        data: mockBankAccounts,
        isLoading: false,
        error: null,
      } as any);

      render(<BankingClient />, { wrapper: createWrapper() });

      const tabList = screen.getByRole("tablist");
      expect(tabList).toBeInTheDocument();

      const tabs = screen.getAllByRole("tab");
      expect(tabs).toHaveLength(3);
    });

    it("should have accessible labels for interactive elements", () => {
      vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
        data: mockBankAccounts,
        isLoading: false,
        error: null,
      } as any);

      render(<BankingClient />, { wrapper: createWrapper() });

      const addButton = screen.getByRole("button", { name: /add account/i });
      expect(addButton).toHaveAttribute("type", "button");
    });
  });
});
