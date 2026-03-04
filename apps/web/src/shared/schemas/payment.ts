import { z } from "zod";

/**
 * LEDGERSG PAYMENT SCHEMA
 *
 * IRAS Compliance: Payment tracking for Singapore businesses
 * Financial Precision: 4 decimal places (internal), 6dp for exchange rates
 *
 * Backend Reference: apps/backend/apps/banking/serializers/payment.py
 */

// Payment Types
export const PAYMENT_TYPES = ["RECEIVED", "MADE"] as const;
export type PaymentType = (typeof PAYMENT_TYPES)[number];

// Payment Methods (shared with Bank Account)
export const PAYMENT_METHODS = [
  "BANK_TRANSFER",
  "CHEQUE",
  "CASH",
  "PAYNOW",
  "CREDIT_CARD",
  "GIRO",
  "OTHER",
] as const;
export type PaymentMethod = (typeof PAYMENT_METHODS)[number];

/**
 * Payment Schema (Read - from API)
 *
 * Matches PaymentSerializer from backend
 */
export const paymentSchema = z.object({
  id: z.string().uuid(),
  org: z.string().uuid(),
  payment_type: z.enum(PAYMENT_TYPES),
  payment_number: z.string().min(1).max(50),
  payment_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  contact: z.string().uuid(),
  contact_name: z.string().optional(),
  bank_account: z.string().uuid(),
  bank_account_name: z.string().optional(),
  currency: z.string().length(3).toUpperCase(),
  exchange_rate: z.string().regex(/^\d+\.\d{6}$/), // 6dp for FX
  amount: z.string().regex(/^\d+\.\d{4}$/), // 4dp
  base_amount: z.string().regex(/^\d+\.\d{4}$/),
  fx_gain_loss: z.string().regex(/^\d+\.\d{4}$/),
  payment_method: z.enum(PAYMENT_METHODS),
  payment_method_display: z.string().optional(),
  payment_reference: z.string().max(100).optional().nullable(),
  journal_entry: z.string().uuid().optional().nullable(),
  is_reconciled: z.boolean(),
  is_voided: z.boolean(),
  notes: z.string().optional().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

/**
 * Payment Receive Input Schema (Write - to API)
 *
 * Matches PaymentReceiveSerializer from backend
 * Used for receiving payments from customers
 */
export const paymentReceiveInputSchema = z
  .object({
    contact_id: z.string().uuid({ message: "Contact ID must be a valid UUID" }),
    bank_account_id: z.string().uuid({ message: "Bank account ID must be a valid UUID" }),
    payment_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, {
      message: "Payment date must be in YYYY-MM-DD format",
    }),
    amount: z.string().regex(/^\d*\.?\d{0,4}$/, "Invalid amount format").refine((val) => {
      const num = parseFloat(val);
      return num > 0;
    }, "Amount must be greater than 0"),
    currency: z.string().length(3).toUpperCase().default("SGD"),
    exchange_rate: z.string().regex(/^\d*\.?\d{0,6}$/, "Invalid exchange rate format").default("1.000000"),
    payment_method: z.enum(PAYMENT_METHODS),
    payment_reference: z.string().max(100).optional(),
    notes: z.string().optional(),
    allocations: z
      .array(
        z.object({
          document_id: z.string().uuid(),
          allocated_amount: z.string().regex(/^\d*\.?\d{0,4}$/),
        })
      )
      .optional(),
  })
  .refine(
    (data) => {
      if (!data.allocations || data.allocations.length === 0) return true;
      const totalAllocated = data.allocations.reduce((sum, alloc) => {
        return sum + parseFloat(alloc.allocated_amount);
      }, 0);
      const paymentAmount = parseFloat(data.amount);
      return totalAllocated <= paymentAmount;
    },
    {
      message: "Total allocations cannot exceed payment amount",
      path: ["allocations"],
    }
  );

/**
 * Payment Make Input Schema (Write - to API)
 *
 * Matches PaymentMakeSerializer from backend
 * Used for making payments to suppliers
 */
export const paymentMakeInputSchema = z
  .object({
    contact_id: z.string().uuid({ message: "Contact ID must be a valid UUID" }),
    bank_account_id: z.string().uuid({ message: "Bank account ID must be a valid UUID" }),
    payment_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, {
      message: "Payment date must be in YYYY-MM-DD format",
    }),
    amount: z.string().regex(/^\d*\.?\d{0,4}$/, "Invalid amount format").refine((val) => {
      const num = parseFloat(val);
      return num > 0;
    }, "Amount must be greater than 0"),
    currency: z.string().length(3).toUpperCase().default("SGD"),
    exchange_rate: z.string().regex(/^\d*\.?\d{0,6}$/, "Invalid exchange rate format").default("1.000000"),
    payment_method: z.enum(PAYMENT_METHODS),
    payment_reference: z.string().max(100).optional(),
    notes: z.string().optional(),
    allocations: z
      .array(
        z.object({
          document_id: z.string().uuid(),
          allocated_amount: z.string().regex(/^\d*\.?\d{0,4}$/),
        })
      )
      .optional(),
  })
  .refine(
    (data) => {
      if (!data.allocations || data.allocations.length === 0) return true;
      const totalAllocated = data.allocations.reduce((sum, alloc) => {
        return sum + parseFloat(alloc.allocated_amount);
      }, 0);
      const paymentAmount = parseFloat(data.amount);
      return totalAllocated <= paymentAmount;
    },
    {
      message: "Total allocations cannot exceed payment amount",
      path: ["allocations"],
    }
  );

/**
 * Payment Allocation Input Schema
 *
 * Matches PaymentAllocationInputSerializer from backend
 */
export const paymentAllocationInputSchema = z.object({
  document_id: z.string().uuid({ message: "Document ID must be a valid UUID" }),
  allocated_amount: z
    .string()
    .regex(/^\d*\.?\d{0,4}$/, "Invalid amount format")
    .refine((val) => {
      const num = parseFloat(val);
      return num > 0;
    }, "Allocated amount must be greater than 0"),
});

/**
 * Payment Void Input Schema
 *
 * Matches PaymentVoidSerializer from backend
 */
export const paymentVoidInputSchema = z.object({
  reason: z.string().min(1, "Void reason is required").max(500),
});

// Export types
export type Payment = z.infer<typeof paymentSchema>;
export type PaymentReceiveInput = z.infer<typeof paymentReceiveInputSchema>;
export type PaymentMakeInput = z.infer<typeof paymentMakeInputSchema>;
export type PaymentAllocationInput = z.infer<typeof paymentAllocationInputSchema>;
export type PaymentVoidInput = z.infer<typeof paymentVoidInputSchema>;

/**
 * Factory: Create empty receive payment input with defaults
 */
export function createEmptyReceivePaymentInput(): PaymentReceiveInput {
  return {
    contact_id: "",
    bank_account_id: "",
    payment_date: new Date().toISOString().split("T")[0],
    amount: "0.0000",
    currency: "SGD",
    exchange_rate: "1.000000",
    payment_method: "BANK_TRANSFER",
  };
}

/**
 * Factory: Create empty make payment input with defaults
 */
export function createEmptyMakePaymentInput(): PaymentMakeInput {
  return {
    contact_id: "",
    bank_account_id: "",
    payment_date: new Date().toISOString().split("T")[0],
    amount: "0.0000",
    currency: "SGD",
    exchange_rate: "1.000000",
    payment_method: "BANK_TRANSFER",
  };
}

/**
 * Helper: Format payment amount for display (2dp)
 */
export function formatPaymentAmount(amount: string): string {
  const num = parseFloat(amount);
  return num.toLocaleString("en-SG", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/**
 * Helper: Get payment method display name
 */
export function getPaymentMethodDisplay(method: PaymentMethod): string {
  const displayNames: Record<PaymentMethod, string> = {
    BANK_TRANSFER: "Bank Transfer",
    CHEQUE: "Cheque",
    CASH: "Cash",
    PAYNOW: "PayNow",
    CREDIT_CARD: "Credit Card",
    GIRO: "GIRO",
    OTHER: "Other",
  };
  return displayNames[method];
}
