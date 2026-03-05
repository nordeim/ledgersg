/**
 * ReconcileForm Tests - TDD
 * 
 * Tests for the ReconcileForm component
 * Following TDD: RED → GREEN → REFACTOR
 */

import { describe, test, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ReconcileForm } from "../components/reconcile-form";
import { useSuggestMatches, useReconcileTransaction } from "@/hooks/use-banking";
import type { BankTransaction } from "@/shared/schemas";

// Mock the hooks
vi.mock("@/hooks/use-banking", () => ({
  useSuggestMatches: vi.fn(),
  useReconcileTransaction: vi.fn(),
}));

const mockUseSuggestMatches = useSuggestMatches as jest.Mock;
const mockUseReconcileTransaction = useReconcileTransaction as jest.Mock;

describe("ReconcileForm", () => {
  const orgId = "org-550e8400-e29b-41d4-a716-446655440001";
  const mockTransaction: BankTransaction = {
    id: "txn-1",
    org: orgId,
    bank_account: "acc-1",
    bank_account_name: "DBS Account",
    transaction_date: "2024-03-15",
    value_date: "2024-03-15",
    description: "Customer Payment",
    reference: "INV-001",
    amount: "5000.0000",
    running_balance: "10000.0000",
    is_reconciled: false,
    reconciled_at: undefined,
    matched_payment: undefined,
    import_source: "CSV",
    external_id: null,
    created_at: "2024-03-15T10:00:00Z",
    updated_at: "2024-03-15T10:00:00Z",
  };

  const mockMatches = [
    {
      payment_id: "pay-1",
      payment_number: "PAY-2024-001",
      amount: "5000.0000",
      contact_name: "Customer ABC",
      match_score: 95,
    },
    {
      payment_id: "pay-2",
      payment_number: "PAY-2024-002",
      amount: "4500.0000",
      contact_name: "Customer XYZ",
      match_score: 75,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    
    mockUseSuggestMatches.mockReturnValue({
      data: mockMatches,
      isLoading: false,
      error: null,
    });
  });

  test("1. Shows transaction details", () => {
    mockUseReconcileTransaction.mockReturnValue({
      mutateAsync: vi.fn(),
      isLoading: false,
    });

    render(
      <ReconcileForm
        transaction={mockTransaction}
        orgId={orgId}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByText(/Customer Payment/i)).toBeInTheDocument();
    expect(screen.getByText(/INV-001/i)).toBeInTheDocument();
    // Use getAllByText since amount appears in multiple places
    expect(screen.getAllByText(/5,000\.00/i).length).toBeGreaterThanOrEqual(1);
  });

  test("2. Loads match suggestions automatically", () => {
    mockUseReconcileTransaction.mockReturnValue({
      mutateAsync: vi.fn(),
      isLoading: false,
    });

    render(
      <ReconcileForm
        transaction={mockTransaction}
        orgId={orgId}
        onClose={vi.fn()}
      />
    );

    expect(useSuggestMatches).toHaveBeenCalledWith(orgId, mockTransaction.id);
  });

  test("3. Displays match suggestions with scores", () => {
    mockUseReconcileTransaction.mockReturnValue({
      mutateAsync: vi.fn(),
      isLoading: false,
    });

    render(
      <ReconcileForm
        transaction={mockTransaction}
        orgId={orgId}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByText("PAY-2024-001")).toBeInTheDocument();
    expect(screen.getByText("Customer ABC")).toBeInTheDocument();
    expect(screen.getByText(/95%/)).toBeInTheDocument();
  });

  test("4. Confirms reconciliation on match selection", async () => {
    const mutateAsync = vi.fn().mockResolvedValue({});
    const onClose = vi.fn();

    mockUseReconcileTransaction.mockReturnValue({
      mutateAsync,
      isLoading: false,
    });

    render(
      <ReconcileForm
        transaction={mockTransaction}
        orgId={orgId}
        onClose={onClose}
      />
    );

    // Select a match
    fireEvent.click(screen.getByText(/PAY-2024-001/i));
    
    // Confirm reconciliation
    fireEvent.click(screen.getByRole("button", { name: /reconcile/i }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({ payment_id: "pay-1" });
    });
  });

  test("5. Shows loading state while reconciling", () => {
    mockUseReconcileTransaction.mockReturnValue({
      mutateAsync: vi.fn(),
      isLoading: true,
    });

    render(
      <ReconcileForm
        transaction={mockTransaction}
        orgId={orgId}
        onClose={vi.fn()}
      />
    );

    const reconcileButton = screen.getByRole("button", { name: /reconciling/i });
    expect(reconcileButton).toBeDisabled();
  });

  test("6. Calls onClose when close button clicked", () => {
    mockUseReconcileTransaction.mockReturnValue({
      mutateAsync: vi.fn(),
      isLoading: false,
    });

    const onClose = vi.fn();
    render(
      <ReconcileForm
        transaction={mockTransaction}
        orgId={orgId}
        onClose={onClose}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onClose).toHaveBeenCalled();
  });
});
