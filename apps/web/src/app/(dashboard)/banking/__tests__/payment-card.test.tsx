import { describe, test, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PaymentCard } from "../components/payment-card";
import type { Payment } from "@/shared/schemas";

// Mock payment data
const createMockPayment = (overrides: Partial<Payment> = {}): Payment => ({
  id: "550e8400-e29b-41d4-a716-446655440001",
  org: "550e8400-e29b-41d4-a716-446655440002",
  payment_type: "RECEIVED",
  payment_number: "PAY-2024-001",
  payment_date: "2024-03-01",
  contact: "550e8400-e29b-41d4-a716-446655440003",
  contact_name: "Acme Corporation",
  bank_account: "550e8400-e29b-41d4-a716-446655440004",
  bank_account_name: "DBS Operating Account",
  currency: "SGD",
  exchange_rate: "1.000000",
  amount: "5000.0000",
  base_amount: "5000.0000",
  fx_gain_loss: "0.0000",
  payment_method: "BANK_TRANSFER",
  payment_method_display: "Bank Transfer",
  payment_reference: "INV-2024-015",
  journal_entry: null,
  is_reconciled: false,
  is_voided: false,
  notes: null,
  created_at: "2024-03-01T10:00:00Z",
  updated_at: "2024-03-01T10:00:00Z",
  ...overrides,
});

describe("PaymentCard", () => {
  test("renders RECEIVED payment correctly", () => {
    const payment = createMockPayment({ payment_type: "RECEIVED" });
    render(<PaymentCard payment={payment} />);

    // Check payment number
    expect(screen.getByText("PAY-2024-001")).toBeInTheDocument();
    
    // Check contact name
    expect(screen.getByText("Acme Corporation")).toBeInTheDocument();
    
    // Check amount with + prefix for RECEIVED
    expect(screen.getByText(/SGD/)).toBeInTheDocument();
    expect(screen.getByText(/5,000\.00/)).toBeInTheDocument();
    
    // Check date and method
    expect(screen.getByText("2024-03-01")).toBeInTheDocument();
    expect(screen.getByText("Bank Transfer")).toBeInTheDocument();
    
    // Check card is rendered
    expect(screen.getByTestId("payment-card")).toBeInTheDocument();
  });

  test("renders MADE payment correctly", () => {
    const payment = createMockPayment({ 
      payment_type: "MADE",
      payment_number: "PAY-2024-002",
      contact_name: "Supplier Ltd",
      amount: "2500.0000",
    });
    render(<PaymentCard payment={payment} />);

    // Check payment number
    expect(screen.getByText("PAY-2024-002")).toBeInTheDocument();
    
    // Check contact name
    expect(screen.getByText("Supplier Ltd")).toBeInTheDocument();
    
    // Check amount with - prefix for MADE
    expect(screen.getByText(/SGD/)).toBeInTheDocument();
    expect(screen.getByText(/2,500\.00/)).toBeInTheDocument();
  });

  test("shows reconciled status", () => {
    const payment = createMockPayment({ is_reconciled: true });
    render(<PaymentCard payment={payment} />);

    expect(screen.getByText("Reconciled")).toBeInTheDocument();
  });

  test("shows voided status", () => {
    const payment = createMockPayment({ is_voided: true });
    render(<PaymentCard payment={payment} />);

    expect(screen.getByText("Voided")).toBeInTheDocument();
  });

  test("handles click event", () => {
    const payment = createMockPayment();
    const onClick = vi.fn();
    render(<PaymentCard payment={payment} onClick={onClick} />);

    fireEvent.click(screen.getByTestId("payment-card"));
    expect(onClick).toHaveBeenCalledWith(payment);
  });

  test("displays unknown contact when contact_name is undefined", () => {
    const payment = createMockPayment({ contact_name: undefined });
    render(<PaymentCard payment={payment} />);

    expect(screen.getByText("Unknown Contact")).toBeInTheDocument();
  });

  test("formats foreign currency amounts", () => {
    const payment = createMockPayment({
      currency: "USD",
      exchange_rate: "1.350000",
      amount: "1000.0000",
    });
    render(<PaymentCard payment={payment} />);

    expect(screen.getByText(/USD/)).toBeInTheDocument();
    expect(screen.getByText(/1,000\.00/)).toBeInTheDocument();
  });
});
