import { describe, test, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PaymentFilters } from "../components/payment-filters";

describe("PaymentFilters", () => {
  const defaultFilters = {
    payment_type: "ALL" as const,
    is_reconciled: null,
    date_from: undefined,
    date_to: undefined,
  };

  test("renders all filter controls", () => {
    const onChange = vi.fn();
    render(<PaymentFilters filters={defaultFilters} onChange={onChange} />);

    // Check tabs
    expect(screen.getByText("All Payments")).toBeInTheDocument();
    expect(screen.getByText("Received")).toBeInTheDocument();
    expect(screen.getByText("Made")).toBeInTheDocument();

    // Check reconciliation select
    expect(screen.getByTestId("reconciliation-select")).toBeInTheDocument();

    // Check date inputs
    expect(screen.getByTestId("date-from-input")).toBeInTheDocument();
    expect(screen.getByTestId("date-to-input")).toBeInTheDocument();

    // Check reset button
    expect(screen.getByTestId("reset-filters-button")).toBeInTheDocument();
  });

  test("displays payment type tabs", () => {
    const onChange = vi.fn();
    render(<PaymentFilters filters={defaultFilters} onChange={onChange} />);

    // Check that tabs are rendered
    expect(screen.getByRole("tab", { name: /all payments/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /received/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /made/i })).toBeInTheDocument();
  });

  test("updates reconciliation filter to reconciled", () => {
    const onChange = vi.fn();
    render(<PaymentFilters filters={defaultFilters} onChange={onChange} />);

    fireEvent.click(screen.getByTestId("reconciliation-select"));
    fireEvent.click(screen.getByText("Reconciled"));
    
    expect(onChange).toHaveBeenCalledWith({
      ...defaultFilters,
      is_reconciled: true,
    });
  });

  test("updates reconciliation filter to unreconciled", () => {
    const onChange = vi.fn();
    render(<PaymentFilters filters={defaultFilters} onChange={onChange} />);

    fireEvent.click(screen.getByTestId("reconciliation-select"));
    fireEvent.click(screen.getByText("Unreconciled"));
    
    expect(onChange).toHaveBeenCalledWith({
      ...defaultFilters,
      is_reconciled: false,
    });
  });

  test("updates date from filter", () => {
    const onChange = vi.fn();
    render(<PaymentFilters filters={defaultFilters} onChange={onChange} />);

    const dateFromInput = screen.getByTestId("date-from-input");
    fireEvent.change(dateFromInput, { target: { value: "2024-03-01" } });
    
    expect(onChange).toHaveBeenCalledWith({
      ...defaultFilters,
      date_from: "2024-03-01",
    });
  });

  test("updates date to filter", () => {
    const onChange = vi.fn();
    render(<PaymentFilters filters={defaultFilters} onChange={onChange} />);

    const dateToInput = screen.getByTestId("date-to-input");
    fireEvent.change(dateToInput, { target: { value: "2024-03-31" } });
    
    expect(onChange).toHaveBeenCalledWith({
      ...defaultFilters,
      date_to: "2024-03-31",
    });
  });

  test("resets all filters", () => {
    const filtersWithValues = {
      payment_type: "RECEIVED" as const,
      is_reconciled: true,
      date_from: "2024-03-01",
      date_to: "2024-03-31",
    };
    
    const onChange = vi.fn();
    render(<PaymentFilters filters={filtersWithValues} onChange={onChange} />);

    fireEvent.click(screen.getByTestId("reset-filters-button"));
    
    expect(onChange).toHaveBeenCalledWith({
      payment_type: "ALL",
      is_reconciled: null,
      date_from: undefined,
      date_to: undefined,
    });
  });

  test("reset button is disabled when no active filters", () => {
    const onChange = vi.fn();
    render(<PaymentFilters filters={defaultFilters} onChange={onChange} />);

    const resetButton = screen.getByTestId("reset-filters-button");
    expect(resetButton).toBeDisabled();
  });

  test("reset button is enabled when filters are active", () => {
    const filtersWithValues = {
      payment_type: "RECEIVED" as const,
      is_reconciled: null,
      date_from: undefined,
      date_to: undefined,
    };
    
    const onChange = vi.fn();
    render(<PaymentFilters filters={filtersWithValues} onChange={onChange} />);

    const resetButton = screen.getByTestId("reset-filters-button");
    expect(resetButton).not.toBeDisabled();
  });
});
