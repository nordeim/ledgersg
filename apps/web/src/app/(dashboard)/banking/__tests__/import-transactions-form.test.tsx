/**
 * ImportTransactionsForm Tests - TDD
 * 
 * Tests for the ImportTransactionsForm component
 * Following TDD: RED → GREEN → REFACTOR
 */

import { describe, test, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ImportTransactionsForm } from "../components/import-transactions-form";
import { useImportBankTransactions, useBankAccounts } from "@/hooks/use-banking";

// Mock the hooks
vi.mock("@/hooks/use-banking", () => ({
  useImportBankTransactions: vi.fn(),
  useBankAccounts: vi.fn(),
}));

const mockUseImportBankTransactions = useImportBankTransactions as Mock;
const mockUseBankAccounts = useBankAccounts as Mock;

describe("ImportTransactionsForm", () => {
  const orgId = "org-550e8400-e29b-41d4-a716-446655440001";
  const mockBankAccounts = {
    results: [
      { id: "acc-1", account_name: "DBS Operating Account" },
      { id: "acc-2", account_name: "OCBC Savings" },
    ],
    count: 2,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    
    mockUseBankAccounts.mockReturnValue({
      data: mockBankAccounts,
      isLoading: false,
      error: null,
    });
  });

  test("1. Renders upload form with bank account selector", () => {
    mockUseImportBankTransactions.mockReturnValue({
      mutateAsync: vi.fn(),
      isLoading: false,
    });

    render(<ImportTransactionsForm orgId={orgId} onCancel={vi.fn()} />);

    expect(screen.getByText(/Import Bank Statement/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Bank Account/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /import/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
  });

  test("2. Validates bank account selection is required before import", () => {
    mockUseImportBankTransactions.mockReturnValue({
      mutateAsync: vi.fn(),
      isLoading: false,
    });

    render(<ImportTransactionsForm orgId={orgId} onCancel={vi.fn()} />);

    // Import button should be disabled without bank account
    const importButton = screen.getByRole("button", { name: /import/i });
    expect(importButton).toBeDisabled();
  });

  test("3. Handles file selection", () => {
    mockUseImportBankTransactions.mockReturnValue({
      mutateAsync: vi.fn(),
      isLoading: false,
    });

    render(<ImportTransactionsForm orgId={orgId} onCancel={vi.fn()} />);

    const fileInput = screen.getByLabelText(/CSV File/i);
    const file = new File(["test"], "test.csv", { type: "text/csv" });
    
    fireEvent.change(fileInput, { target: { files: [file] } });
    
    expect(screen.getByText(/test.csv/i)).toBeInTheDocument();
  });

  test("4. Submits form successfully", async () => {
    const mutateAsync = vi.fn().mockResolvedValue({
      imported: 10,
      skipped: 2,
      errors: [],
    });
    const onSuccess = vi.fn();

    mockUseImportBankTransactions.mockReturnValue({
      mutateAsync,
      isLoading: false,
    });

    render(<ImportTransactionsForm orgId={orgId} onSuccess={onSuccess} onCancel={vi.fn()} />);

    // Select bank account
    fireEvent.click(screen.getByLabelText(/Bank Account/i));
    fireEvent.click(screen.getByText("DBS Operating Account"));

    // Upload file
    const fileInput = screen.getByLabelText(/CSV File/i);
    const file = new File(["test"], "test.csv", { type: "text/csv" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    // Submit
    fireEvent.click(screen.getByRole("button", { name: /import/i }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalled();
    });
  });

  test("5. Shows import results after success — including the per-row errors (P10/L-4)", async () => {
    const mutateAsync = vi.fn().mockResolvedValue({
      imported: 10,
      skipped: 2,
      errors: ["Row 3: Missing amount", "Row 7: Invalid date format '31/02/2026'"],
    });

    mockUseImportBankTransactions.mockReturnValue({
      mutateAsync,
      isLoading: false,
    });

    render(<ImportTransactionsForm orgId={orgId} onCancel={vi.fn()} />);

    // Complete import
    fireEvent.click(screen.getByLabelText(/Bank Account/i));
    fireEvent.click(screen.getByText("DBS Operating Account"));
    
    const fileInput = screen.getByLabelText(/CSV File/i);
    const file = new File(["test"], "test.csv", { type: "text/csv" });
    fireEvent.change(fileInput, { target: { files: [file] } });
    
    fireEvent.click(screen.getByRole("button", { name: /import/i }));

    await waitFor(() => {
      expect(screen.getByText(/10 transactions imported/i)).toBeInTheDocument();
    });
    // The truthful duplicates line (the wire key is `skipped`) …
    expect(screen.getByText(/2 duplicates skipped/i)).toBeInTheDocument();
    // … and the actionable per-row errors the backend actually returns
    // (strings, not the old imagined object shape).
    expect(screen.getByText(/2 rows could not be imported/i)).toBeInTheDocument();
    expect(screen.getByText("Row 3: Missing amount")).toBeInTheDocument();
    expect(
      screen.getByText("Row 7: Invalid date format '31/02/2026'")
    ).toBeInTheDocument();
  });

test("6. Shows loading state during import", () => {
                mockUseImportBankTransactions.mockReturnValue({
                        mutateAsync: vi.fn(),
                        isPending: true, // Changed from isLoading to isPending (TanStack Query v5)
                });

                render(<ImportTransactionsForm orgId={orgId} onCancel={vi.fn()} />);

                // Should show loading indicator on button
                const importButton = screen.getByRole("button", { name: /importing/i });
                expect(importButton).toBeDisabled();
                expect(importButton).toHaveTextContent("Importing...");
        });

  test("7. Handles import errors", async () => {
    const mutateAsync = vi.fn().mockRejectedValue(new Error("Import failed"));

    mockUseImportBankTransactions.mockReturnValue({
      mutateAsync,
      isLoading: false,
    });

    render(<ImportTransactionsForm orgId={orgId} onCancel={vi.fn()} />);

    fireEvent.click(screen.getByLabelText(/Bank Account/i));
    fireEvent.click(screen.getByText("DBS Operating Account"));
    
    const fileInput = screen.getByLabelText(/CSV File/i);
    const file = new File(["test"], "test.csv", { type: "text/csv" });
    fireEvent.change(fileInput, { target: { files: [file] } });
    
    fireEvent.click(screen.getByRole("button", { name: /import/i }));

    await waitFor(() => {
      expect(screen.getByText(/Import failed/i)).toBeInTheDocument();
    });
  });

  test("8. Calls onCancel when cancel button clicked", () => {
    mockUseImportBankTransactions.mockReturnValue({
      mutateAsync: vi.fn(),
      isLoading: false,
    });

    const onCancel = vi.fn();
    render(<ImportTransactionsForm orgId={orgId} onCancel={onCancel} />);

    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onCancel).toHaveBeenCalled();
  });
});
