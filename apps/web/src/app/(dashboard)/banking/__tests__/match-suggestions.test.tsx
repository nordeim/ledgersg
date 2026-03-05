/**
 * MatchSuggestions Tests - TDD
 * 
 * Tests for the MatchSuggestions component
 * Following TDD: RED → GREEN → REFACTOR
 */

import { describe, test, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MatchSuggestions } from "../components/match-suggestions";

describe("MatchSuggestions", () => {
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
    {
      payment_id: "pay-3",
      payment_number: "PAY-2024-003",
      amount: "3000.0000",
      contact_name: "Customer 123",
      match_score: 45,
    },
  ];

  const transactionAmount = "5000.0000";

  test("1. Renders list of suggestions", () => {
    const onSelect = vi.fn();
    
    render(
      <MatchSuggestions
        suggestions={mockMatches}
        transactionAmount={transactionAmount}
        onSelect={onSelect}
      />
    );

    expect(screen.getByText("PAY-2024-001")).toBeInTheDocument();
    expect(screen.getByText("PAY-2024-002")).toBeInTheDocument();
    expect(screen.getByText("PAY-2024-003")).toBeInTheDocument();
  });

  test("2. Shows match scores with color coding", () => {
    const onSelect = vi.fn();
    
    render(
      <MatchSuggestions
        suggestions={mockMatches}
        transactionAmount={transactionAmount}
        onSelect={onSelect}
      />
    );

    // High score (95%)
    expect(screen.getByText("95%")).toBeInTheDocument();
    
    // Medium score (75%)
    expect(screen.getByText("75%")).toBeInTheDocument();
    
    // Low score (45%)
    expect(screen.getByText("45%")).toBeInTheDocument();
  });

  test("3. Shows exact match indicator for matching amounts", () => {
    const onSelect = vi.fn();
    
    render(
      <MatchSuggestions
        suggestions={mockMatches}
        transactionAmount={transactionAmount}
        onSelect={onSelect}
      />
    );

    // First match should show "Exact Match" badge since amounts match
    expect(screen.getByText("Exact Match")).toBeInTheDocument();
  });

  test("4. Calls onSelect when suggestion clicked", () => {
    const onSelect = vi.fn();
    
    render(
      <MatchSuggestions
        suggestions={mockMatches}
        transactionAmount={transactionAmount}
        onSelect={onSelect}
      />
    );

    fireEvent.click(screen.getByText("PAY-2024-001"));
    expect(onSelect).toHaveBeenCalledWith("pay-1");
  });

  test("5. Shows loading state", () => {
    render(
      <MatchSuggestions
        suggestions={[]}
        transactionAmount={transactionAmount}
        onSelect={vi.fn()}
        isLoading={true}
      />
    );

    expect(screen.getByTestId("suggestions-loading")).toBeInTheDocument();
  });

  test("6. Shows empty state when no suggestions", () => {
    render(
      <MatchSuggestions
        suggestions={[]}
        transactionAmount={transactionAmount}
        onSelect={vi.fn()}
      />
    );

    expect(screen.getByText(/No matching payments found/i)).toBeInTheDocument();
  });
});
