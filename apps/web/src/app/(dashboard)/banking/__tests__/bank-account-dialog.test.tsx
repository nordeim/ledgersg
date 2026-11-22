/**
 * P9/B-4: the bank-account creation dialog — the "Add Bank Account" /
 * "Add Account" buttons were dead (no onClick; no form existed anywhere)
 * while the backend create endpoint and hook were real. A new org could
 * not add a bank account through the UI, gating the whole payments
 * surface (the receive form's account select would be empty).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import * as bankingHooks from "@/hooks/use-banking";
import * as accountsHooks from "@/hooks/use-accounts";
import { BankAccountDialog } from "../components/bank-account-dialog";

vi.mock("@/hooks/use-banking", () => ({
  useCreateBankAccount: vi.fn(),
  // P10/M-6: the dialog gains an edit mode — the update hook is called in
  // every render (create mode passes a placeholder id).
  useUpdateBankAccount: vi.fn(),
}));
vi.mock("@/hooks/use-accounts", () => ({
  useAccounts: vi.fn(),
}));

const mutate = vi.fn();
const mockCreate = {
  mutate: (
    _data: unknown,
    options?: { onSuccess?: () => void }
  ) => {
    mutate(_data);
    options?.onSuccess?.();
  },
  isPending: false,
};

const updateMutate = vi.fn();
const mockUpdate = {
  mutate: (
    _data: unknown,
    options?: { onSuccess?: () => void }
  ) => {
    updateMutate(_data);
    options?.onSuccess?.();
  },
  isPending: false,
};

function renderDialog(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

const BANK_ACCOUNTS = [
  { id: "11111111-1111-4111-8111-111111111111", code: "1100", name: "Cash & Bank - DBS", account_type: "ASSET", is_active: true, is_bank: true },
  { id: "gl-rev-1", code: "4000", name: "Sales", account_type: "REVENUE", is_active: true, is_bank: false },
];

describe("BankAccountDialog (P9/B-4)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(bankingHooks.useCreateBankAccount).mockReturnValue(
      mockCreate as unknown as ReturnType<typeof bankingHooks.useCreateBankAccount>
    );
    vi.mocked(bankingHooks.useUpdateBankAccount).mockReturnValue(
      mockUpdate as unknown as ReturnType<typeof bankingHooks.useUpdateBankAccount>
    );
    vi.mocked(accountsHooks.useAccounts).mockReturnValue({
      data: BANK_ACCOUNTS,
      isLoading: false,
    } as unknown as ReturnType<typeof accountsHooks.useAccounts>);
  });

  it("offers only bank-type GL accounts", async () => {
    renderDialog(
      <BankAccountDialog open onOpenChange={vi.fn()} orgId="org-1" />
    );

    // The GL select offers the seeded bank account; the revenue account
    // is filtered out (backend contract: bank-type accounts only).
    const glSelect = screen.getByLabelText(/gl account/i) as HTMLSelectElement;
    const options = Array.from(glSelect.options).map((o) => o.textContent);
    expect(options).toContainEqual("1100 — Cash & Bank - DBS");
    expect(options).not.toContainEqual("4000 — Sales");
  });

  it("submits the backend contract (validated by the shared zod schema)", async () => {
    const user = userEvent.setup();
    renderDialog(
      <BankAccountDialog open onOpenChange={vi.fn()} orgId="org-1" />
    );

    await user.type(screen.getByLabelText(/account name/i), "Operating Account");
    await user.type(screen.getByLabelText(/bank name/i), "DBS Bank");
    await user.type(screen.getByLabelText(/account number/i), "1234567890");

    // pick the GL account (native select — label association works)
    await user.selectOptions(screen.getByLabelText(/gl account/i), "11111111-1111-4111-8111-111111111111");

    await user.click(screen.getByRole("button", { name: /add account/i }));

    await waitFor(() => {
      expect(mutate).toHaveBeenCalledWith(
        expect.objectContaining({
          account_name: "Operating Account",
          bank_name: "DBS Bank",
          account_number: "1234567890",
          currency: "SGD",
          gl_account: "11111111-1111-4111-8111-111111111111",
          // The wire contract the live e2e caught: no PayNow selected →
          // null on the wire (the DB CHECK rejects ""; the serializer
          // accepts null since P9/B-4).
          paynow_type: null,
          paynow_id: null,
        })
      );
    });
  });

  it("blocks submission when required fields are missing", async () => {
    const user = userEvent.setup();
    renderDialog(
      <BankAccountDialog open onOpenChange={vi.fn()} orgId="org-1" />
    );

    await user.click(screen.getByRole("button", { name: /add account/i }));

    expect(mutate).not.toHaveBeenCalled();
    expect(screen.getByText(/account name required/i)).toBeInTheDocument();
  });
});

// P10/M-6: bank-account edit — useUpdateBankAccount/useDeactivateBankAccount
// existed with zero consumers; a wrong PayNow ID or name could never be
// corrected in-app (account number/currency/GL are immutable by backend
// contract — BankAccountUpdateSerializer).
const EDIT_ACCOUNT = {
  id: "22222222-2222-4222-8222-222222222222",
  org: "33333333-3333-4333-8333-333333333333",
  account_name: "Operating Account",
  bank_name: "DBS Bank",
  account_number: "1234567890",
  bank_code: "7171",
  branch_code: "001",
  currency: "SGD",
  gl_account: "11111111-1111-4111-8111-111111111111",
  paynow_type: "UEN" as const,
  paynow_id: "12345678A",
  is_default: true,
  is_active: true,
  opening_balance: "10000.0000",
  opening_balance_date: "2026-01-01",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("BankAccountDialog edit mode (P10/M-6)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(bankingHooks.useCreateBankAccount).mockReturnValue(
      mockCreate as unknown as ReturnType<typeof bankingHooks.useCreateBankAccount>
    );
    vi.mocked(bankingHooks.useUpdateBankAccount).mockReturnValue(
      mockUpdate as unknown as ReturnType<typeof bankingHooks.useUpdateBankAccount>
    );
    vi.mocked(accountsHooks.useAccounts).mockReturnValue({
      data: BANK_ACCOUNTS,
      isLoading: false,
    } as unknown as ReturnType<typeof accountsHooks.useAccounts>);
  });

  it("prefills from the account and disables immutable fields", async () => {
    renderDialog(
      <BankAccountDialog
        open
        onOpenChange={vi.fn()}
        orgId="org-1"
        account={EDIT_ACCOUNT}
      />
    );

    expect(screen.getByText(/edit bank account/i)).toBeInTheDocument();

    // Prefill: the editable fields carry the persisted values.
    expect(screen.getByLabelText(/account name/i)).toHaveValue("Operating Account");
    expect(screen.getByLabelText(/bank name/i)).toHaveValue("DBS Bank");
    expect(
      screen.getByLabelText(/paynow id/i)
    ).toHaveValue("12345678A");

    // Immutable by backend contract: account number, currency, GL account.
    expect(screen.getByLabelText(/account number/i)).toBeDisabled();
    expect(screen.getByLabelText(/currency/i)).toBeDisabled();
    expect(screen.getByLabelText(/gl account/i)).toBeDisabled();
  });

  it("PATCHes the update contract (immutable fields not sent; unset PayNow → null)", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    renderDialog(
      <BankAccountDialog
        open
        onOpenChange={onOpenChange}
        orgId="org-1"
        account={EDIT_ACCOUNT}
      />
    );

    // Correct the name and clear the PayNow pair (the M-1 wire contract:
    // "" → null, not a dangling type).
    const nameInput = screen.getByLabelText(/account name/i);
    await user.clear(nameInput);
    await user.type(nameInput, "Operating Account (Main)");
    await user.selectOptions(screen.getByLabelText(/paynow type/i), "");
    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(updateMutate).toHaveBeenCalledWith({
        account_name: "Operating Account (Main)",
        bank_name: "DBS Bank",
        paynow_type: null,
        paynow_id: null,
        is_default: true,
      });
    });
    expect(mutate).not.toHaveBeenCalled();
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("refuses a dangling PayNow pair client-side", async () => {
    const user = userEvent.setup();
    renderDialog(
      <BankAccountDialog
        open
        onOpenChange={vi.fn()}
        orgId="org-1"
        account={EDIT_ACCOUNT}
      />
    );

    // Type without an ID → the create schema's pair rule, mirrored.
    await user.clear(screen.getByLabelText(/paynow id/i));
    await user.click(screen.getByRole("button", { name: /save changes/i }));

    expect(updateMutate).not.toHaveBeenCalled();
    expect(
      screen.getByText(/paynow type and id must both be set or both be null/i)
    ).toBeInTheDocument();
  });
});
