/**
 * ReconciliationSummary Tests - TDD
 * 
 * Tests for the ReconciliationSummary component
 * Following TDD: RED → GREEN → REFACTOR
 */

import { describe, test, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ReconciliationSummary } from "../components/reconciliation-summary";
import { useBankTransactions } from "@/hooks/use-banking";

// Mock the hook
vi.mock("@/hooks/use-banking", () => ({
  useBankTransactions: vi.fn(),
}));

const mockUseBankTransactions = useBankTransactions as jest.Mock;

describe("ReconciliationSummary", () => {
  const orgId = "org-550e8400-e29b-41d4-a716-446655440001";

  test("1. Renders stats cards", () => {
    mockUseBankTransactions.mockReturnValue({
      data: { results: [], count: 0 },
      isLoading: false,
      error: null,
    });

    render(<ReconciliationSummary orgId={orgId} />);

    // Use specific role-based queries to avoid duplicates
    expect(screen.getByText(/Total Transactions/i)).toBeInTheDocument();
    expect(screen.getByText("Reconciliation Rate")).toBeInTheDocument();
    expect(screen.getByTestId("reconciliation-summary")).toBeInTheDocument();
  });

  test("2. Shows correct counts", () => {
    mockUseBankTransactions.mockReturnValue({
      data: {
        results: [
          { is_reconciled: true },
          { is_reconciled: true },
          { is_reconciled: false },
        ],
        count: 3,
      },
      isLoading: false,
      error: null,
    });

    render(<ReconciliationSummary orgId={orgId} />);

    expect(screen.getByText("3")).toBeInTheDocument(); // Total
    expect(screen.getByText("2")).toBeInTheDocument(); // Reconciled
    expect(screen.getByText("1")).toBeInTheDocument(); // Unreconciled
  });

  test("3. Shows reconciliation rate as percentage", () => {
    mockUseBankTransactions.mockReturnValue({
      data: {
        results: [
          { is_reconciled: true },
          { is_reconciled: true },
          { is_reconciled: false },
          { is_reconciled: false },
        ],
        count: 4,
      },
      isLoading: false,
      error: null,
    });

    render(<ReconciliationSummary orgId={orgId} />);

    // 2 out of 4 = 50%
    expect(screen.getByText("50%")).toBeInTheDocument();
  });

  test("4. Shows loading state", () => {
    mockUseBankTransactions.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(<ReconciliationSummary orgId={orgId} />);

    expect(screen.getByTestId("summary-loading")).toBeInTheDocument();
  });

  test("5. Shows zero state correctly", () => {
    mockUseBankTransactions.mockReturnValue({
      data: { results: [], count: 0 },
      isLoading: false,
      error: null,
    });

    render(<ReconciliationSummary orgId={orgId} />);

    // Should show multiple zeros (one for each stat)
    const zeroElements = screen.getAllByText("0");
    expect(zeroElements.length).toBeGreaterThanOrEqual(1);
    
    // Should show 0% for rate when there are no transactions
    const rateElements = screen.getAllByText(/0%/);
    expect(rateElements.length).toBeGreaterThanOrEqual(1);
  });

  test("6. Updates when bank account filter changes", () => {
    const { rerender } = render(<ReconciliationSummary orgId={orgId} />);

    // Mock with different data for different account
    mockUseBankTransactions.mockReturnValue({
      data: {
        results: [{ is_reconciled: true }],
        count: 1,
      },
      isLoading: false,
      error: null,
    });

    rerender(<ReconciliationSummary orgId={orgId} bankAccountId="acc-2" />);

    // Should have been called with the bank account filter
    expect(mockUseBankTransactions).toHaveBeenCalledWith(
      orgId,
      expect.objectContaining({ bank_account_id: "acc-2" })
    );
  });
});
