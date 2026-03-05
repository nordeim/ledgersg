/**
 * TransactionRow Tests - TDD
 * 
 * Tests for the atomic TransactionRow component
 * Following TDD: RED → GREEN → REFACTOR
 */

import { describe, test, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TransactionRow } from "../components/transaction-row";
import type { BankTransaction } from "@/shared/schemas";

// Mock transaction factory
const createMockTransaction = (overrides: Partial<BankTransaction> = {}): BankTransaction => ({
  id: "txn-550e8400-e29b-41d4-a716-446655440001",
  org: "org-550e8400-e29b-41d4-a716-446655440002",
  bank_account: "acc-550e8400-e29b-41d4-a716-446655440003",
  bank_account_name: "DBS Operating Account",
  transaction_date: "2024-03-15",
  value_date: "2024-03-15",
  description: "Payment from Customer ABC",
  reference: "INV-2024-001",
  amount: "5000.0000",
  running_balance: "15000.0000",
  is_reconciled: false,
  reconciled_at: undefined,
  matched_payment: undefined,
  import_source: "CSV",
  external_id: "ext-123",
  created_at: "2024-03-15T10:00:00Z",
  updated_at: "2024-03-15T10:00:00Z",
  ...overrides,
});

describe("TransactionRow", () => {
  test("1. Renders collapsed view with basic info", () => {
    const transaction = createMockTransaction();
    render(<TransactionRow transaction={transaction} />);

    // Should show description
    expect(screen.getByText("Payment from Customer ABC")).toBeInTheDocument();
    
    // Should show formatted amount
    expect(screen.getByText(/5,000\.00/)).toBeInTheDocument();
    
    // Should show date
    expect(screen.getByText("2024-03-15")).toBeInTheDocument();
    
    // Should show unreconciled status
    expect(screen.getByText("Unreconciled")).toBeInTheDocument();
    
    // Card should be rendered
    expect(screen.getByTestId("transaction-row")).toBeInTheDocument();
  });

  test("2. Shows reconciled status with checkmark", () => {
    const reconciled = createMockTransaction({ 
      is_reconciled: true,
      reconciled_at: "2024-03-15T12:00:00Z",
    });
    
    render(<TransactionRow transaction={reconciled} />);
    
    expect(screen.getByText("Reconciled")).toBeInTheDocument();
    expect(screen.getByTestId("check-icon")).toBeInTheDocument();
  });

  test("3. Toggles expanded view on click", () => {
    const transaction = createMockTransaction();
    render(<TransactionRow transaction={transaction} />);

    // Initially collapsed - details should not be visible
    expect(screen.queryByText("Transaction Details")).not.toBeInTheDocument();
    
    // Click to expand
    fireEvent.click(screen.getByTestId("transaction-row"));
    
    // Now expanded - details should be visible
    expect(screen.getByText("Transaction Details")).toBeInTheDocument();
    
    // Click to collapse
    fireEvent.click(screen.getByTestId("transaction-row"));
    
    // Should be collapsed again
    expect(screen.queryByText("Transaction Details")).not.toBeInTheDocument();
  });

  test("4. Shows debit/credit amount styling", () => {
    // Debit (negative amount)
    const debit = createMockTransaction({ 
      id: "debit-1",
      amount: "-1000.0000",
      description: "Payment Made" 
    });
    const { rerender } = render(<TransactionRow transaction={debit} />);
    
    // Amount should be displayed
    expect(screen.getByText(/-1,000\.00/)).toBeInTheDocument();
    
    // Credit (positive amount)
    const credit = createMockTransaction({ 
      id: "credit-1",
      amount: "1000.0000",
      description: "Payment Received" 
    });
    rerender(<TransactionRow transaction={credit} />);
    
    // Amount should be displayed with +
    expect(screen.getByText(/\+1,000\.00/)).toBeInTheDocument();
  });

  test("5. Displays running balance when provided", () => {
    const transaction = createMockTransaction({ running_balance: "25000.0000" });
    render(<TransactionRow transaction={transaction} />);
    
    fireEvent.click(screen.getByTestId("transaction-row")); // Expand
    
    // In expanded view, should show balance information
    expect(screen.getByText(/25,000\.00/)).toBeInTheDocument();
  });

  test("6. Shows import source badge (CSV/OFX/MT940/API)", () => {
    const csv = createMockTransaction({ import_source: "CSV" });
    const { rerender } = render(<TransactionRow transaction={csv} />);
    expect(screen.getByText("CSV")).toBeInTheDocument();
    
    const ofx = createMockTransaction({ import_source: "OFX", id: "ofx-1" });
    rerender(<TransactionRow transaction={ofx} />);
    expect(screen.getByText("OFX")).toBeInTheDocument();
    
    const api = createMockTransaction({ import_source: "API", id: "api-1" });
    rerender(<TransactionRow transaction={api} />);
    expect(screen.getByText("API")).toBeInTheDocument();
  });

  test("7. Calls onReconcile when reconcile button clicked", () => {
    const transaction = createMockTransaction({ is_reconciled: false });
    const onReconcile = vi.fn();
    
    render(<TransactionRow transaction={transaction} onReconcile={onReconcile} />);
    
    // Expand to see reconcile button
    fireEvent.click(screen.getByTestId("transaction-row"));
    
    const reconcileButton = screen.getByRole("button", { name: /reconcile/i });
    fireEvent.click(reconcileButton);
    
    expect(onReconcile).toHaveBeenCalledWith(transaction);
  });

  test("8. Shows matched payment info when reconciled", () => {
    const reconciled = createMockTransaction({
      is_reconciled: true,
      reconciled_at: "2024-03-15T14:30:00Z",
      matched_payment: "pay-550e8400-e29b-41d4-a716-446655440099",
    });
    
    render(<TransactionRow transaction={reconciled} />);
    
    fireEvent.click(screen.getByTestId("transaction-row")); // Expand
    
    // In expanded view, should show matched payment info
    const expandedContent = screen.getByText(/Matched Payment/i);
    expect(expandedContent).toBeInTheDocument();
  });
});
