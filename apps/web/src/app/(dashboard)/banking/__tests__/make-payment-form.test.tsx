/**
 * P9/B-5: the Make Payment form — the banking page's "Make Payment" button
 * set showMakeForm state that nothing read (no form existed) while
 * useMakePayment + POST /payments/make/ were real and unconsumed.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MakePaymentForm } from "../components/make-payment-form";
import { useMakePayment, useBankAccounts } from "@/hooks/use-banking";
import { useContacts } from "@/hooks/use-contacts";

vi.mock("@/hooks/use-banking", () => ({
  useMakePayment: vi.fn(),
  useBankAccounts: vi.fn(),
}));

vi.mock("@/hooks/use-contacts", () => ({
  useContacts: vi.fn(),
}));

// P9/B-3b: the allocation section's document list
vi.mock("@/hooks/use-invoices", () => ({
  useInvoices: vi.fn().mockReturnValue({ data: { results: [], count: 0 } }),
}));

const mockMakePayment = useMakePayment as unknown as ReturnType<typeof vi.fn>;
const mockBankAccounts = useBankAccounts as unknown as ReturnType<typeof vi.fn>;
const mockContacts = useContacts as unknown as ReturnType<typeof vi.fn>;

const SUPPLIER = {
  id: "33333333-3333-4333-8333-333333333333",
  name: "Globex Supplies",
  email: "ap@globex.example",
  contact_type: "SUPPLIER",
  is_active: true,
};

const BANK_ACCOUNT = {
  id: "44444444-4444-4444-8444-444444444444",
  account_name: "DBS Operating",
  bank_name: "DBS",
};

describe("MakePaymentForm (P9/B-5)", () => {
  const orgId = "550e8400-e29b-41d4-a716-446655440001";
  const mutateAsync = vi.fn().mockResolvedValue({});

  beforeEach(() => {
    vi.clearAllMocks();
    mockMakePayment.mockReturnValue({
      mutateAsync,
      isError: false,
      isLoading: false,
      error: null,
    });
    mockBankAccounts.mockReturnValue({
      data: { results: [BANK_ACCOUNT], count: 1 },
      isLoading: false,
      error: null,
    });
    mockContacts.mockReturnValue({ data: [SUPPLIER], isLoading: false });
  });

  it("renders with a supplier picker (not a raw UUID input)", () => {
    render(<MakePaymentForm orgId={orgId} />);

    expect(screen.getByRole("heading", { name: /make payment/i })).toBeInTheDocument();
    expect(
      screen.getByRole("combobox", { name: /search supplier/i })
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /make payment/i })).toBeInTheDocument();
  });

  it("submits the payment-make payload with the picked supplier", async () => {
    const onSuccess = vi.fn();
    const user = userEvent.setup();
    render(<MakePaymentForm orgId={orgId} onSuccess={onSuccess} />);

    // pick the supplier (focus opens the dropdown)
    fireEvent.focus(screen.getByRole("combobox", { name: /search supplier/i }));
    // P19/FE-M2: options select on mousedown (before the input blur).
    fireEvent.mouseDown(await screen.findByRole("option", { name: /Globex Supplies/i }));
    await waitFor(() =>
      expect(screen.getByText(/Globex Supplies/)).toBeInTheDocument()
    );

    // bank account (Radix select — keyboard pattern per repo convention)
    await user.click(
      screen.getByRole("combobox", { name: /bank account/i })
    );
    await user.keyboard("{ArrowDown}{Enter}");

    await user.type(screen.getByLabelText("Payment amount"), "250");

    await user.click(screen.getByRole("button", { name: /make payment/i }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          contact_id: SUPPLIER.id,
          bank_account_id: BANK_ACCOUNT.id,
          amount: "250.00",
          currency: "SGD",
        })
      );
    });
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
  });
});
