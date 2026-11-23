/**
 * P10/M-6: the accounts tab rows gain Edit + Deactivate. The hooks
 * (useUpdateBankAccount/useDeactivateBankAccount) existed with zero
 * consumers — an account row could not be corrected or retired in-app.
 * Edit is covered wire-level in bank-account-dialog.test.tsx; this file
 * covers the row actions and the deactivate confirmation.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BankingClient } from "../banking-client";
import * as bankingHooks from "@/hooks/use-banking";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({
    currentOrg: { id: "org-123", name: "Test Org" },
    isLoading: false,
    hasPermission: (permission: string) => permission === "can_manage_banking",
  }),
}));

const deactivateMock = vi.fn().mockResolvedValue({});

vi.mock("@/hooks/use-banking", () => ({
  useBankAccounts: vi.fn(),
  useCreateBankAccount: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false }),
  useUpdateBankAccount: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false }),
  useDeactivateBankAccount: vi.fn(() => ({
    mutateAsync: deactivateMock,
    isPending: false,
  })),
  usePayments: vi.fn(),
  useBankTransactions: vi.fn(),
  useReceivePayment: vi.fn().mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
    isError: false,
    error: null,
  }),
}));
vi.mock("@/hooks/use-accounts", () => ({
  useAccounts: vi.fn().mockReturnValue({ data: [], isLoading: false }),
}));

const accounts = {
  results: [
    {
      id: "22222222-2222-4222-8222-222222222222",
      org: "org-123",
      account_name: "Operating Account",
      bank_name: "DBS Bank",
      account_number: "1234567890",
      bank_code: "7171",
      branch_code: "001",
      currency: "SGD",
      gl_account: "11111111-1111-4111-8111-111111111111",
      paynow_type: "UEN",
      paynow_id: "12345678A",
      is_default: true,
      is_active: true,
      opening_balance: "10000.0000",
      opening_balance_date: "2026-01-01",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    {
      id: "44444444-4444-4444-8444-444444444444",
      org: "org-123",
      account_name: "Savings Account",
      bank_name: "OCBC Bank",
      account_number: "9876543210",
      bank_code: "7339",
      branch_code: "001",
      currency: "SGD",
      gl_account: "11111111-1111-4111-8111-111111111111",
      paynow_type: null,
      paynow_id: null,
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

function renderClient() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BankingClient />
    </QueryClientProvider>
  );
}

describe("Bank accounts tab row actions (P10/M-6)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
      data: accounts,
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof bankingHooks.useBankAccounts>);
  });

  it("rows offer per-account Edit and Deactivate actions", () => {
    renderClient();

    expect(
      screen.getByRole("button", { name: /edit operating account/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /deactivate operating account/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /edit savings account/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /deactivate savings account/i })
    ).toBeInTheDocument();
  });

  it("Edit opens the dialog prefilled with the row's account", async () => {
    const user = userEvent.setup();
    renderClient();

    await user.click(
      screen.getByRole("button", { name: /edit savings account/i })
    );

    // The dialog is in edit mode with the row's values prefilled.
    expect(screen.getByText(/edit bank account/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/account name/i)).toHaveValue(
      "Savings Account"
    );
    expect(screen.getByLabelText(/account number/i)).toBeDisabled();
  });

  it("deactivates only after an explicit confirmation", async () => {
    const user = userEvent.setup();
    renderClient();

    await user.click(
      screen.getByRole("button", { name: /deactivate savings account/i })
    );

    // The confirm gate — nothing fired yet.
    expect(screen.getByText(/deactivate this account/i)).toBeInTheDocument();
    expect(deactivateMock).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /^deactivate$/i }));

    await waitFor(() => expect(deactivateMock).toHaveBeenCalledTimes(1));
  });

  it("the deactivate confirm closes without firing on Cancel", async () => {
    const user = userEvent.setup();
    renderClient();

    await user.click(
      screen.getByRole("button", { name: /deactivate savings account/i })
    );
    await user.click(screen.getByRole("button", { name: /cancel/i }));

    expect(deactivateMock).not.toHaveBeenCalled();
    expect(
      screen.queryByText(/deactivate this account/i)
    ).not.toBeInTheDocument();
  });
});
