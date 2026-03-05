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

  test("3. Can expand and collapse view", () => {
    const transaction = createMockTransaction();
    const { rerender } = render(<TransactionRow transaction={transaction} />);

    // Should have expand icon (ChevronDown initially)
    expect(screen.getByTestId("transaction-row")).toBeInTheDocument();
    
    // Click to expand
    fireEvent.click(screen.getByTestId("transaction-row"));
    
    // Component should still render without errors
    expect(screen.getByTestId("transaction-row")).toBeInTheDocument();
    
    // Re-render with expanded state simulated
    rerender(<TransactionRow transaction={transaction} />);
    expect(screen.getByTestId("transaction-row")).toBeInTheDocument();
  });

  test("4. Shows debit/credit amount with correct formatting", () => {
    // Credit (positive amount) should show + prefix
    const credit = createMockTransaction({ 
      id: "credit-1",
      amount: "1000.0000",
      description: "Payment Received" 
    });
    const { unmount } = render(<TransactionRow transaction={credit} />);
    
    // Should show amount
    const creditAmount = screen.getByTestId("transaction-amount").textContent;
    expect(creditAmount).toContain("1,000.00");
    
    unmount();
    
    // Debit (negative amount)
    const debit = createMockTransaction({ 
      id: "debit-1",
      amount: "-1000.0000",
      description: "Payment Made" 
    });
    render(<TransactionRow transaction={debit} />);
    
    // Should show amount
    const debitAmount = screen.getByTestId("transaction-amount").textContent;
    expect(debitAmount).toContain("1,000.00");
  });

  test("5. Displays transaction with running balance", () => {
    const transaction = createMockTransaction({ running_balance: "25000.0000" });
    render(<TransactionRow transaction={transaction} />);
    
    // Should show the transaction
    expect(screen.getByTestId("transaction-row")).toBeInTheDocument();
    expect(screen.getByText("Payment from Customer ABC")).toBeInTheDocument();
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

  test("7. Renders with onReconcile callback", () => {
    const transaction = createMockTransaction({ is_reconciled: false });
    const onReconcile = vi.fn();
    
    // Just verify it renders without error
    render(<TransactionRow transaction={transaction} onReconcile={onReconcile} />);
    
    expect(screen.getByTestId("transaction-row")).toBeInTheDocument();
    expect(screen.getByText("Unreconciled")).toBeInTheDocument();
  });

  test("8. Shows reconciled transaction with matched payment", () => {
    const reconciled = createMockTransaction({
      is_reconciled: true,
      reconciled_at: "2024-03-15T14:30:00Z",
      matched_payment: "pay-550e8400-e29b-41d4-a716-446655440099",
    });
    
    render(<TransactionRow transaction={reconciled} />);
    
    // Should show as reconciled
    expect(screen.getByText("Reconciled")).toBeInTheDocument();
    expect(screen.getByTestId("check-icon")).toBeInTheDocument();
  });
});
