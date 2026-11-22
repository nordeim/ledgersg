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
