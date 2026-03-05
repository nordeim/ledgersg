import { describe, test, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PaymentList } from "../components/payment-list";
import { usePayments } from "@/hooks/use-banking";
import type { Payment } from "@/shared/schemas";

// Mock the hooks
vi.mock("@/hooks/use-banking", () => ({
  usePayments: vi.fn(),
}));

const mockUsePayments = usePayments as jest.Mock;

const createMockPayment = (id: string, overrides: Partial<Payment> = {}): Payment => ({
  id,
  org: "550e8400-e29b-41d4-a716-446655440002",
  payment_type: "RECEIVED",
  payment_number: `PAY-2024-${id.slice(-3)}`,
  payment_date: "2024-03-01",
  contact: "550e8400-e29b-41d4-a716-446655440003",
  contact_name: "Test Contact",
  bank_account: "550e8400-e29b-41d4-a716-446655440004",
  bank_account_name: "Test Account",
  currency: "SGD",
  exchange_rate: "1.000000",
  amount: "5000.0000",
  base_amount: "5000.0000",
  fx_gain_loss: "0.0000",
  payment_method: "BANK_TRANSFER",
  payment_method_display: "Bank Transfer",
  payment_reference: null,
  journal_entry: null,
  is_reconciled: false,
  is_voided: false,
  notes: null,
  created_at: "2024-03-01T10:00:00Z",
  updated_at: "2024-03-01T10:00:00Z",
  ...overrides,
});

describe("PaymentList", () => {
  const orgId = "550e8400-e29b-41d4-a716-446655440001";

  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("renders loading state", () => {
    mockUsePayments.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    });

    render(<PaymentList orgId={orgId} />);

    expect(screen.getByTestId("payments-loading")).toBeInTheDocument();
    expect(screen.getAllByRole("generic").length).toBeGreaterThan(0);
  });

  test("renders empty state", () => {
    mockUsePayments.mockReturnValue({
      data: { results: [], count: 0, next: null, previous: null },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<PaymentList orgId={orgId} />);

    expect(screen.getByTestId("payments-empty")).toBeInTheDocument();
    expect(screen.getByText("No payments found")).toBeInTheDocument();
  });

  test("renders error state with retry", () => {
    const refetch = vi.fn();
    mockUsePayments.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Failed to fetch"),
      refetch,
    });

    render(<PaymentList orgId={orgId} />);

    expect(screen.getByTestId("payments-error")).toBeInTheDocument();
    expect(screen.getByText("Error loading payments")).toBeInTheDocument();
    
    const retryButton = screen.getByRole("button", { name: /retry/i });
    fireEvent.click(retryButton);
    expect(refetch).toHaveBeenCalled();
  });

  test("renders payment list with data", () => {
    const payments = [
      createMockPayment("1"),
      createMockPayment("2"),
    ];
    
    mockUsePayments.mockReturnValue({
      data: { results: payments, count: 2, next: null, previous: null },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<PaymentList orgId={orgId} />);

    expect(screen.getByTestId("payments-list")).toBeInTheDocument();
    expect(screen.getByText("Showing 2 of 2 payments")).toBeInTheDocument();
    expect(screen.getAllByTestId("payment-card")).toHaveLength(2);
  });

  test("handles payment click", () => {
    const payments = [createMockPayment("1")];
    const onPaymentClick = vi.fn();
    
    mockUsePayments.mockReturnValue({
      data: { results: payments, count: 1, next: null, previous: null },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<PaymentList orgId={orgId} onPaymentClick={onPaymentClick} />);

    const paymentCard = screen.getByTestId("payment-card");
    fireEvent.click(paymentCard);
    
    expect(onPaymentClick).toHaveBeenCalledWith(expect.objectContaining({
      id: "1",
    }));
  });

  test("applies filters correctly", () => {
    mockUsePayments.mockReturnValue({
      data: { results: [], count: 0, next: null, previous: null },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    const filters = {
      payment_type: "RECEIVED" as const,
      is_reconciled: false,
    };

    render(<PaymentList orgId={orgId} filters={filters} />);

    expect(mockUsePayments).toHaveBeenCalledWith(orgId, filters);
  });

  test("shows empty state with RECEIVED filter message", () => {
    mockUsePayments.mockReturnValue({
      data: { results: [], count: 0, next: null, previous: null },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<PaymentList orgId={orgId} filters={{ payment_type: "RECEIVED" }} />);

    expect(screen.getByText("No received payments match your filters.")).toBeInTheDocument();
  });

  test("shows empty state with MADE filter message", () => {
    mockUsePayments.mockReturnValue({
      data: { results: [], count: 0, next: null, previous: null },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<PaymentList orgId={orgId} filters={{ payment_type: "MADE" }} />);

    expect(screen.getByText("No made payments match your filters.")).toBeInTheDocument();
  });
});
