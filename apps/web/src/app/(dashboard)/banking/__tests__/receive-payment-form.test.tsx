import { describe, test, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ReceivePaymentForm } from "../components/receive-payment-form";
import { useReceivePayment, useBankAccounts } from "@/hooks/use-banking";

// Mock the hooks
vi.mock("@/hooks/use-banking", () => ({
  useReceivePayment: vi.fn(),
  useBankAccounts: vi.fn(),
}));

// P9/B-3: the contact picker's search hook (customer-side)
vi.mock("@/hooks/use-contacts", () => ({
  useContacts: vi.fn().mockReturnValue({ data: [], isLoading: false }),
}));

// P9/B-3b: the allocation section's document list
vi.mock("@/hooks/use-invoices", () => ({
  useInvoices: vi.fn().mockReturnValue({ data: { results: [], count: 0 } }),
}));

const mockUseBankAccounts = useBankAccounts as Mock;
const mockUseReceivePayment = useReceivePayment as Mock;

describe("ReceivePaymentForm", () => {
  const orgId = "550e8400-e29b-41d4-a716-446655440001";
  const mockBankAccounts = {
    results: [
      {
        id: "55555555-5555-4555-8555-555555555551",
        account_name: "DBS Operating Account",
        bank_name: "DBS",
      },
      {
        id: "55555555-5555-4555-8555-555555555552",
        account_name: "OCBC Savings",
        bank_name: "OCBC",
      },
    ],
    count: 2,
  };

  const mockMutateAsync = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    
    mockUseBankAccounts.mockReturnValue({
      data: mockBankAccounts,
      isLoading: false,
      error: null,
    });
    
    mockUseReceivePayment.mockReturnValue({
      mutateAsync: mockMutateAsync,
      isError: false,
      isLoading: false,
      error: null,
    });
  });

  test("renders form fields", () => {
    render(<ReceivePaymentForm orgId={orgId} />);

    // Check for unique elements
    expect(screen.getByRole("heading", { name: /receive payment/i })).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("Search customers by name…")
    ).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Additional notes...")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /receive payment/i })).toBeInTheDocument();
  });

  test("calls onCancel when cancel button is clicked", () => {
    const onCancel = vi.fn();
    render(<ReceivePaymentForm orgId={orgId} onCancel={onCancel} />);

    const cancelButton = screen.getByRole("button", { name: /cancel/i });
    fireEvent.click(cancelButton);

    expect(onCancel).toHaveBeenCalled();
  });

  test("P9/B-3b: prefilled allocations ride the payload (the Record Payment deep link)", async () => {
    render(
      <ReceivePaymentForm
        orgId={orgId}
        initialContactId="11111111-1111-4111-8111-111111111111"
        initialAllocations={[
          {
            document_id: "d-55555555-5555-4555-8555-555555555555",
            allocated_amount: "5000.00",
          },
        ]}
      />
    );

    // bank account (Radix select — keyboard pattern)
    const user = userEvent.setup();
    await user.click(screen.getByRole("combobox", { name: /bank account/i }));
    await user.keyboard("{ArrowDown}{Enter}");
    await user.type(screen.getByLabelText("Payment amount"), "5000");

    fireEvent.submit(screen.getByRole("button", { name: /receive payment/i }).closest("form")!);

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          contact_id: "11111111-1111-4111-8111-111111111111",
          allocations: [
            {
              document_id: "d-55555555-5555-4555-8555-555555555555",
              allocated_amount: "5000.00",
            },
          ],
        })
      );
    });
  });
});
