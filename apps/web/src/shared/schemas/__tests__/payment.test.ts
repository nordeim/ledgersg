/**
 * Payment Schema Tests (TDD)
 *
 * Tests validate:
 * - Type structure matches backend serializer
 * - Payment type (RECEIVED/MADE)
 * - Payment method validation
 * - Allocation validation
 *
 * Backend Reference: apps/backend/apps/banking/serializers/payment.py
 */

import { describe, it, expect } from "vitest";
import {
  paymentSchema,
  paymentReceiveInputSchema,
  paymentMakeInputSchema,
  paymentAllocationInputSchema,
  type Payment,
  type PaymentReceiveInput,
} from "../payment";

describe("Payment Schema", () => {
  const validPaymentId = "550e8400-e29b-41d4-a716-446655440000";
  const validOrgId = "550e8400-e29b-41d4-a716-446655440001";
  const validContactId = "550e8400-e29b-41d4-a716-446655440002";
  const validBankAccountId = "550e8400-e29b-41d4-a716-446655440003";
  const validDocumentId = "550e8400-e29b-41d4-a716-446655440004";

  describe("Structure Validation", () => {
    it("should validate a complete received payment object", () => {
      const validPayment: Payment = {
        id: validPaymentId,
        org: validOrgId,
        payment_type: "RECEIVED",
        payment_number: "RCP-000001",
        payment_date: "2024-01-20",
        contact: validContactId,
        contact_name: "Test Customer Pte Ltd",
        bank_account: validBankAccountId,
        bank_account_name: "Main Operating Account",
        currency: "SGD",
        exchange_rate: "1.000000",
        amount: "1000.0000",
        base_amount: "1000.0000",
        fx_gain_loss: "0.0000",
        payment_method: "BANK_TRANSFER",
        payment_method_display: "Bank Transfer",
        payment_reference: "REF-001",
        journal_entry: null,
        is_reconciled: false,
        is_voided: false,
        notes: "",
        created_at: "2024-01-20T00:00:00Z",
        updated_at: "2024-01-20T00:00:00Z",
      };

      const result = paymentSchema.safeParse(validPayment);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.payment_type).toBe("RECEIVED");
        expect(result.data.amount).toBe("1000.0000");
      }
    });

    it("should validate a complete made payment object", () => {
      const validPayment: Payment = {
        id: validPaymentId,
        org: validOrgId,
        payment_type: "MADE",
        payment_number: "PAY-000001",
        payment_date: "2024-01-20",
        contact: validContactId,
        contact_name: "Test Supplier Pte Ltd",
        bank_account: validBankAccountId,
        bank_account_name: "Main Operating Account",
        currency: "SGD",
        exchange_rate: "1.000000",
        amount: "5000.0000",
        base_amount: "5000.0000",
        fx_gain_loss: "0.0000",
        payment_method: "GIRO",
        payment_method_display: "GIRO",
        payment_reference: "GIRO-001",
        journal_entry: null,
        is_reconciled: false,
        is_voided: false,
        notes: "",
        created_at: "2024-01-20T00:00:00Z",
        updated_at: "2024-01-20T00:00:00Z",
      };

      const result = paymentSchema.safeParse(validPayment);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.payment_type).toBe("MADE");
      }
    });

    it("should validate payment methods", () => {
      const methods = [
        "BANK_TRANSFER",
        "CHEQUE",
        "CASH",
        "PAYNOW",
        "CREDIT_CARD",
        "GIRO",
        "OTHER",
      ];

      methods.forEach((method) => {
        const payment = {
          id: validPaymentId,
          org: validOrgId,
          payment_type: "RECEIVED",
          payment_number: "RCP-000001",
          payment_date: "2024-01-20",
          contact: validContactId,
          bank_account: validBankAccountId,
          currency: "SGD",
          exchange_rate: "1.000000",
          amount: "100.0000",
          base_amount: "100.0000",
          fx_gain_loss: "0.0000",
          payment_method: method,
          is_reconciled: false,
          is_voided: false,
          created_at: "2024-01-20T00:00:00Z",
          updated_at: "2024-01-20T00:00:00Z",
        };

        const result = paymentSchema.safeParse(payment);
        expect(result.success).toBe(true);
      });
    });

    it("should reject invalid payment method", () => {
      const invalidPayment = {
        id: validPaymentId,
        org: validOrgId,
        payment_type: "RECEIVED",
        payment_number: "RCP-000001",
        payment_date: "2024-01-20",
        contact: validContactId,
        bank_account: validBankAccountId,
        currency: "SGD",
        exchange_rate: "1.000000",
        amount: "100.0000",
        base_amount: "100.0000",
        fx_gain_loss: "0.0000",
        payment_method: "INVALID_METHOD",
        is_reconciled: false,
        is_voided: false,
        created_at: "2024-01-20T00:00:00Z",
        updated_at: "2024-01-20T00:00:00Z",
      };

      const result = paymentSchema.safeParse(invalidPayment);
      expect(result.success).toBe(false);
    });

    it("should validate amount format (4 decimal places)", () => {
      const validPayment = {
        id: validPaymentId,
        org: validOrgId,
        payment_type: "RECEIVED",
        payment_number: "RCP-000001",
        payment_date: "2024-01-20",
        contact: validContactId,
        bank_account: validBankAccountId,
        currency: "SGD",
        exchange_rate: "1.000000",
        amount: "1234.5678", // Valid 4dp
        base_amount: "1234.5678",
        fx_gain_loss: "0.0000",
        payment_method: "BANK_TRANSFER",
        is_reconciled: false,
        is_voided: false,
        created_at: "2024-01-20T00:00:00Z",
        updated_at: "2024-01-20T00:00:00Z",
      };

      const result = paymentSchema.safeParse(validPayment);
      expect(result.success).toBe(true);
    });
  });

  describe("Receive Payment Input", () => {
    it("should validate customer payment input", () => {
      const input: PaymentReceiveInput = {
        contact_id: validContactId,
        bank_account_id: validBankAccountId,
        payment_date: "2024-01-20",
        amount: "1000.0000",
        currency: "SGD",
        exchange_rate: "1.000000",
        payment_method: "BANK_TRANSFER",
        payment_reference: "REF-001",
        notes: "",
      };

      const result = paymentReceiveInputSchema.safeParse(input);
      expect(result.success).toBe(true);
    });

    it("should apply default currency as SGD", () => {
      const input = {
        contact_id: validContactId,
        bank_account_id: validBankAccountId,
        payment_date: "2024-01-20",
        amount: "1000.0000",
        payment_method: "BANK_TRANSFER",
      };

      const result = paymentReceiveInputSchema.parse(input);
      expect(result.currency).toBe("SGD");
    });

    it("should apply default exchange_rate as 1.000000", () => {
      const input = {
        contact_id: validContactId,
        bank_account_id: validBankAccountId,
        payment_date: "2024-01-20",
        amount: "1000.0000",
        payment_method: "BANK_TRANSFER",
      };

      const result = paymentReceiveInputSchema.parse(input);
      expect(result.exchange_rate).toBe("1.000000");
    });

    it("should validate with allocations", () => {
      const input = {
        contact_id: validContactId,
        bank_account_id: validBankAccountId,
        payment_date: "2024-01-20",
        amount: "1000.0000",
        payment_method: "BANK_TRANSFER",
        allocations: [
          { document_id: validDocumentId, allocated_amount: "600.0000" },
          { document_id: "550e8400-e29b-41d4-a716-446655440005", allocated_amount: "400.0000" },
        ],
      };

      const result = paymentReceiveInputSchema.safeParse(input);
      expect(result.success).toBe(true);
    });

    it("should reject allocations exceeding payment amount", () => {
      const input = {
        contact_id: validContactId,
        bank_account_id: validBankAccountId,
        payment_date: "2024-01-20",
        amount: "1000.0000",
        payment_method: "BANK_TRANSFER",
        allocations: [
          { document_id: validDocumentId, allocated_amount: "1200.0000" }, // Exceeds amount
        ],
      };

      const result = paymentReceiveInputSchema.safeParse(input);
      expect(result.success).toBe(false);
    });

    it("should validate contact_id is required UUID", () => {
      const input = {
        bank_account_id: validBankAccountId,
        payment_date: "2024-01-20",
        amount: "1000.0000",
        payment_method: "BANK_TRANSFER",
      };

      const result = paymentReceiveInputSchema.safeParse(input);
      expect(result.success).toBe(false);
    });

    it("should validate bank_account_id is required UUID", () => {
      const input = {
        contact_id: validContactId,
        payment_date: "2024-01-20",
        amount: "1000.0000",
        payment_method: "BANK_TRANSFER",
      };

      const result = paymentReceiveInputSchema.safeParse(input);
      expect(result.success).toBe(false);
    });

    it("should validate payment_date format", () => {
      const input = {
        contact_id: validContactId,
        bank_account_id: validBankAccountId,
        payment_date: "2024/01/20", // Invalid format
        amount: "1000.0000",
        payment_method: "BANK_TRANSFER",
      };

      const result = paymentReceiveInputSchema.safeParse(input);
      expect(result.success).toBe(false);
    });

    it("should validate amount is positive", () => {
      const input = {
        contact_id: validContactId,
        bank_account_id: validBankAccountId,
        payment_date: "2024-01-20",
        amount: "0.0000", // Invalid: must be positive
        payment_method: "BANK_TRANSFER",
      };

      const result = paymentReceiveInputSchema.safeParse(input);
      expect(result.success).toBe(false);
    });
  });

  describe("Make Payment Input", () => {
    it("should validate supplier payment input", () => {
      const input = {
        contact_id: validContactId,
        bank_account_id: validBankAccountId,
        payment_date: "2024-01-20",
        amount: "5000.0000",
        currency: "SGD",
        exchange_rate: "1.000000",
        payment_method: "GIRO",
        payment_reference: "GIRO-001",
        notes: "",
      };

      const result = paymentMakeInputSchema.safeParse(input);
      expect(result.success).toBe(true);
    });

    it("should apply defaults for make payment", () => {
      const input = {
        contact_id: validContactId,
        bank_account_id: validBankAccountId,
        payment_date: "2024-01-20",
        amount: "5000.0000",
        payment_method: "BANK_TRANSFER",
      };

      const result = paymentMakeInputSchema.parse(input);
      expect(result.currency).toBe("SGD");
      expect(result.exchange_rate).toBe("1.000000");
    });
  });

  describe("Payment Allocation Input", () => {
    it("should validate allocation input", () => {
      const input = {
        document_id: validDocumentId,
        allocated_amount: "1000.0000",
      };

      const result = paymentAllocationInputSchema.safeParse(input);
      expect(result.success).toBe(true);
    });

    it("should validate allocated_amount format (4dp)", () => {
      const input = {
        document_id: validDocumentId,
        allocated_amount: "1000.1234",
      };

      const result = paymentAllocationInputSchema.safeParse(input);
      expect(result.success).toBe(true);
    });

    it("should reject negative allocated_amount", () => {
      const input = {
        document_id: validDocumentId,
        allocated_amount: "-100.0000",
      };

      const result = paymentAllocationInputSchema.safeParse(input);
      expect(result.success).toBe(false);
    });

    it("should reject zero allocated_amount", () => {
      const input = {
        document_id: validDocumentId,
        allocated_amount: "0.0000",
      };

      const result = paymentAllocationInputSchema.safeParse(input);
      expect(result.success).toBe(false);
    });
  });
});
