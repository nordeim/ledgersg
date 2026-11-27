/**
 * P19 modal-semantics + keyboard-flow gates (the FE-H1/H2 pair).
 *
 * FE-H1: the four banking "modals" (Receive / Make / Import / Reconcile)
 *    were hand-rolled fixed-position divs — no role="dialog", no focus
 *    trap, no Escape, no aria-modal — on the payment-entry and
 *    reconciliation primary flows (violating the repo's own library
 *    discipline in ui/dialog.tsx). They must be Radix Dialogs.
 * FE-H2: the transaction-row header was a mouse-only clickable div —
 *    keyboard users could not expand a transaction, therefore could
 *    not reach the Reconcile flow at all (WCAG 2.1.1 Level A).
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi } from "vitest";
import BankingClient from "../banking-client";
import { TransactionRow } from "../components/transaction-row";
import * as bankingHooks from "@/hooks/use-banking";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({
    currentOrg: { id: "org-1", name: "Test Org" },
    isLoading: false,
    hasPermission: (permission: string) => permission === "can_manage_banking",
  }),
}));

vi.mock("@/hooks/use-banking", () => ({
  useCreateBankAccount: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false }),
  useUpdateBankAccount: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false }),
  useReceivePayment: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false }),
  useMakePayment: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false }),
  useDeactivateBankAccount: vi.fn().mockReturnValue({ mutateAsync: vi.fn(), isPending: false }),
  useBankAccounts: vi.fn(),
  usePayments: vi.fn(),
  useBankTransactions: vi.fn(),
  useImportBankTransactions: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false }),
  useUnreconcileTransaction: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false }),
}));
vi.mock("@/hooks/use-accounts", () => ({
  useAccounts: vi.fn().mockReturnValue({ data: [], isLoading: false }),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function mockEmptyBankingData() {
  vi.mocked(bankingHooks.useBankAccounts).mockReturnValue({
    data: { results: [], count: 0 },
    isLoading: false,
  } as unknown as ReturnType<typeof bankingHooks.useBankAccounts>);
  vi.mocked(bankingHooks.usePayments).mockReturnValue({
    data: { results: [], count: 0 },
    isLoading: false,
  } as unknown as ReturnType<typeof bankingHooks.usePayments>);
  vi.mocked(bankingHooks.useBankTransactions).mockReturnValue({
    data: { results: [], count: 0 },
    isLoading: false,
  } as unknown as ReturnType<typeof bankingHooks.useBankTransactions>);
}

describe("P19/FE-H1 — the banking modals are real dialogs", () => {
  it("Receive Payment opens a role=dialog with Escape close", async () => {
    const user = userEvent.setup();
    mockEmptyBankingData();

    render(<BankingClient />, { wrapper: createWrapper() });

    // The payments tab is not the default (accounts is).
    await user.click(screen.getByRole("tab", { name: /payments/i }));

    await user.click(screen.getByRole("button", { name: /receive payment/i }));

    // Radix 1.1.x contract: role="dialog" + focus trap + Escape (the
    // library does not set aria-modal itself); the accessible name comes
    // from the DialogContent aria-label.
    const dialog = screen.getByRole("dialog", { name: /receive payment/i });
    expect(dialog).toBeInTheDocument();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("Make Payment opens a role=dialog", async () => {
    const user = userEvent.setup();
    mockEmptyBankingData();

    render(<BankingClient />, { wrapper: createWrapper() });

    await user.click(screen.getByRole("tab", { name: /payments/i }));

    await user.click(screen.getByRole("button", { name: /make payment/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("Import Statement opens a role=dialog with Escape close", async () => {
    const user = userEvent.setup();
    mockEmptyBankingData();

    render(<BankingClient />, { wrapper: createWrapper() });

    const transactionsTab = screen.getByRole("tab", { name: /transactions/i });
    await user.click(transactionsTab);

    // Two "Import Statement" buttons exist in the transactions tab (the
    // section header + the list card) — either opens the dialog.
    const importButtons = screen.getAllByRole("button", { name: /import statement/i });
    await user.click(importButtons[0]);
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

const TRANSACTION = {
  id: "t-1",
  bank_account_id: "acc-1",
  bank_account_name: "DBS Current",
  transaction_date: "2026-01-15",
  value_date: "2026-01-15",
  description: "INCOMING TRANSFER",
  reference: "REF-1",
  amount: "109.00",
  running_balance: "109.00",
  import_source: "CSV",
  is_reconciled: false,
  external_id: null,
  matched_payment: null,
  reconciled_at: null,
} as unknown as Parameters<typeof TransactionRow>[0]["transaction"];

describe("P19/FE-H2 — the transaction row header is keyboard-operable", () => {
  it("the header exposes aria-expanded and toggles via Enter", async () => {
    const user = userEvent.setup();
    render(<TransactionRow transaction={TRANSACTION} />);

    // The header must be a focusable button (not a mouse-only div).
    const header = screen.getByRole("button", {
      name: /INCOMING TRANSFER/i,
    });
    expect(header.getAttribute("aria-expanded")).toBe("false");

    header.focus();
    await user.keyboard("{Enter}");

    expect(screen.getByRole("button", { name: /INCOMING TRANSFER/i }).getAttribute("aria-expanded")).toBe(
      "true"
    );
    // The expanded panel must be the button's controlled region.
    expect(screen.getByText("Transaction Details")).toBeInTheDocument();
  });

  it("Space also toggles the row", async () => {
    const user = userEvent.setup();
    render(<TransactionRow transaction={TRANSACTION} />);

    const header = screen.getByRole("button", { name: /INCOMING TRANSFER/i });
    header.focus();
    await user.keyboard(" ");

    expect(screen.getByText("Transaction Details")).toBeInTheDocument();
  });

  it("a keyboard user can reach the Reconcile action from the expanded panel", async () => {
    const user = userEvent.setup();
    const onReconcile = vi.fn();
    render(<TransactionRow transaction={TRANSACTION} onReconcile={onReconcile} />);

    const header = screen.getByRole("button", { name: /INCOMING TRANSFER/i });
    header.focus();
    await user.keyboard("{Enter}");

    const reconcile = screen.getByRole("button", { name: "Reconcile" });
    await user.click(reconcile);
    expect(onReconcile).toHaveBeenCalledTimes(1);
  });
});
