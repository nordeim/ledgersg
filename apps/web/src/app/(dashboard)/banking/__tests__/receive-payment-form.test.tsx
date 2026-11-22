import { describe, test, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
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

const mockUseBankAccounts = useBankAccounts as Mock;
const mockUseReceivePayment = useReceivePayment as Mock;

describe("ReceivePaymentForm", () => {
  const orgId = "550e8400-e29b-41d4-a716-446655440001";
  const mockBankAccounts = {
    results: [
      { id: "acc1", account_name: "DBS Operating Account", bank_name: "DBS" },
      { id: "acc2", account_name: "OCBC Savings", bank_name: "OCBC" },
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
});
