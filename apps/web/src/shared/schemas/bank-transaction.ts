import { z } from "zod";

/**
 * LEDGERSG BANK TRANSACTION SCHEMA
 *
 * IRAS Compliance: Bank transaction tracking for reconciliation
 * Financial Precision: 4 decimal places (internal)
 *
 * Backend Reference: apps/backend/apps/banking/serializers/bank_transaction.py
 */

// Import Sources
export const IMPORT_SOURCES = ["CSV", "OFX", "MT940", "API"] as const;
export type ImportSource = (typeof IMPORT_SOURCES)[number];

/**
 * Bank Transaction Schema (Read - from API)
 *
 * Matches BankTransactionSerializer from backend
 */
export const bankTransactionSchema = z.object({
  id: z.string().uuid(),
  org: z.string().uuid(),
  bank_account: z.string().uuid(),
  bank_account_name: z.string().optional(),
  transaction_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  value_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional().nullable(),
  description: z.string().min(1).max(500),
  reference: z.string().max(100).optional().nullable(),
  amount: z.string().regex(/^\d+\.\d{4}$/), // 4dp internal precision
  running_balance: z.string().regex(/^\d+\.\d{4}$/).optional().nullable(),
  is_reconciled: z.boolean(),
  reconciled_at: z.string().optional().nullable(),
  matched_payment: z.string().uuid().optional().nullable(),
  import_source: z.enum(IMPORT_SOURCES),
  external_id: z.string().max(100).optional().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

/**
 * Bank Transaction Input Schema (Write - for CSV import)
 *
 * Used for CSV import validation
 */
export const bankTransactionInputSchema = z.object({
  bank_account_id: z.string().uuid({ message: "Bank account ID must be a valid UUID" }),
  transaction_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, {
    message: "Transaction date must be in YYYY-MM-DD format",
  }),
  value_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional().nullable(),
  description: z.string().min(1, "Description required").max(500),
  reference: z.string().max(100).optional().nullable(),
  amount: z.string().regex(/^\d*\.?\d{0,4}$/, "Invalid amount format"),
  import_source: z.enum(IMPORT_SOURCES).default("CSV"),
  external_id: z.string().max(100).optional().nullable(),
});

// Export types
export type BankTransaction = z.infer<typeof bankTransactionSchema>;
export type BankTransactionInput = z.infer<typeof bankTransactionInputSchema>;

/**
 * Factory: Create empty bank transaction input with defaults
 */
export function createEmptyBankTransactionInput(): BankTransactionInput {
  return {
    bank_account_id: "",
    transaction_date: new Date().toISOString().split("T")[0],
    description: "",
    amount: "0.0000",
    import_source: "CSV",
  };
}

/**
 * Helper: Format transaction amount for display (2dp)
 */
export function formatTransactionAmount(amount: string): string {
  const num = parseFloat(amount);
  return num.toLocaleString("en-SG", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/**
 * Helper: Format transaction date for display
 */
export function formatTransactionDate(date: string): string {
  return new Date(date).toLocaleDateString("en-SG", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
