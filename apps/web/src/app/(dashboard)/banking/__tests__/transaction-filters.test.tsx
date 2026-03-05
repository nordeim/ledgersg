/**
 * TransactionFilters Tests - TDD
 * 
 * Tests for the TransactionFilters component
 * Following TDD: RED → GREEN → REFACTOR
 */

import { describe, test, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TransactionFilters } from "../components/transaction-filters";

describe("TransactionFilters", () => {
  const defaultFilters = {
    bank_account_id: undefined,
    is_reconciled: null,
    unreconciled_only: false,
    date_from: undefined,
    date_to: undefined,
  };

  const mockBankAccounts = [
    { id: "acc-1", account_name: "DBS Operating Account" },
    { id: "acc-2", account_name: "OCBC Savings" },
  ];

  test("1. Renders all filter controls", () => {
    render(
      <TransactionFilters 
        filters={defaultFilters} 
        onChange={vi.fn()} 
        bankAccounts={mockBankAccounts} 
      />
    );

    // Bank account dropdown
    expect(screen.getByLabelText(/Bank Account/i)).toBeInTheDocument();
    
    // Reconciliation status dropdown
    expect(screen.getByLabelText(/Reconciliation Status/i)).toBeInTheDocument();
    
    // Date from input
    expect(screen.getByLabelText(/From Date/i)).toBeInTheDocument();
    
    // Date to input
    expect(screen.getByLabelText(/To Date/i)).toBeInTheDocument();
    
    // Reset button
    expect(screen.getByRole("button", { name: /reset/i })).toBeInTheDocument();
    
    // Component container
    expect(screen.getByTestId("transaction-filters")).toBeInTheDocument();
  });

  test("2. Updates bank account filter", () => {
    const onChange = vi.fn();
    
    render(
      <TransactionFilters 
        filters={defaultFilters} 
        onChange={onChange} 
        bankAccounts={mockBankAccounts} 
      />
    );

    // Open the select
    fireEvent.click(screen.getByLabelText(/Bank Account/i));
    
    // Select an account
    fireEvent.click(screen.getByText("DBS Operating Account"));
    
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ bank_account_id: "acc-1" })
    );
  });

  test("3. Updates reconciliation filter", () => {
    const onChange = vi.fn();
    
    render(
      <TransactionFilters 
        filters={defaultFilters} 
        onChange={onChange} 
        bankAccounts={[]} 
      />
    );

    // Open reconciliation select
    fireEvent.click(screen.getByLabelText(/Reconciliation Status/i));
    
    // Select "Reconciled"
    fireEvent.click(screen.getByText("Reconciled"));
    
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ is_reconciled: true })
    );
  });

  test("4. Updates date range", () => {
    const onChange = vi.fn();
    
    render(
      <TransactionFilters 
        filters={defaultFilters} 
        onChange={onChange} 
        bankAccounts={[]} 
      />
    );

    // Set From date
    fireEvent.change(screen.getByLabelText(/From Date/i), {
      target: { value: "2024-03-01" },
    });
    
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ date_from: "2024-03-01" })
    );

    // Set To date
    fireEvent.change(screen.getByLabelText(/To Date/i), {
      target: { value: "2024-03-31" },
    });
    
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ date_to: "2024-03-31" })
    );
  });

  test("5. Toggles unreconciled only", () => {
    const onChange = vi.fn();
    
    render(
      <TransactionFilters 
        filters={defaultFilters} 
        onChange={onChange} 
        bankAccounts={[]} 
      />
    );

    // Click the checkbox
    fireEvent.click(screen.getByLabelText(/Unreconciled Only/i));
    
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ unreconciled_only: true })
    );
  });

  test("6. Resets all filters", () => {
    const onChange = vi.fn();
    const filters = {
      bank_account_id: "acc-1",
      is_reconciled: true,
      unreconciled_only: false,
      date_from: "2024-03-01",
      date_to: "2024-03-31",
    };
    
    render(
      <TransactionFilters 
        filters={filters} 
        onChange={onChange} 
        bankAccounts={mockBankAccounts} 
      />
    );

    // Click reset button
    fireEvent.click(screen.getByRole("button", { name: /reset/i }));
    
    expect(onChange).toHaveBeenCalledWith(defaultFilters);
  });

  test("7. Shows reset button disabled when no active filters", () => {
    const { rerender } = render(
      <TransactionFilters 
        filters={defaultFilters} 
        onChange={vi.fn()} 
        bankAccounts={[]} 
      />
    );
    
    // No filters - button should be disabled
    expect(screen.getByRole("button", { name: /reset/i })).toBeDisabled();
    
    // With filters - button should be enabled
    rerender(
      <TransactionFilters 
        filters={{ ...defaultFilters, bank_account_id: "acc-1" }} 
        onChange={vi.fn()} 
        bankAccounts={[]} 
      />
    );
    
    expect(screen.getByRole("button", { name: /reset/i })).not.toBeDisabled();
  });
});
