import { z } from "zod";

/**
 * LEDGERSG BANK ACCOUNT SCHEMA
 *
 * IRAS Compliance: PayNow validation for Singapore businesses
 * Currency: 3-letter ISO code
 * Financial Precision: 4 decimal places (internal)
 *
 * Backend Reference: apps/backend/apps/banking/serializers/bank_account.py
 */

// PayNow Types (Singapore-specific)
export const PAYNOW_TYPES = ["UEN", "MOBILE", "NRIC"] as const;
export type PayNowType = (typeof PAYNOW_TYPES)[number];

/**
 * Bank Account Schema (Read - from API)
 *
 * Matches BankAccountSerializer from backend
 */
export const bankAccountSchema = z
  .object({
    id: z.string().uuid(),
    org: z.string().uuid(),
    account_name: z.string().min(1).max(200),
    bank_name: z.string().min(1).max(200),
    account_number: z.string().min(1).max(50),
    bank_code: z.string().max(10).optional().nullable(),
    branch_code: z.string().max(10).optional().nullable(),
    currency: z.string().length(3).toUpperCase(),
    gl_account: z.string().uuid(),
    paynow_type: z.enum(PAYNOW_TYPES).optional().nullable(),
    paynow_id: z.string().max(20).optional().nullable(),
    is_default: z.boolean(),
    is_active: z.boolean(),
    opening_balance: z.string().regex(/^\d+\.\d{4}$/), // 4dp internal precision
    opening_balance_date: z.string().optional().nullable(),
    created_at: z.string(),
    updated_at: z.string(),
  })
  .refine(
    (data) => {
      // PayNow type and ID must both be set or both be null
      if (data.paynow_type && !data.paynow_id) return false;
      if (data.paynow_id && !data.paynow_type) return false;
      return true;
    },
    {
      message: "PayNow type and ID must both be set or both be null",
    }
  )
  .refine(
    (data) => {
      if (!data.paynow_type || !data.paynow_id) return true;

      // Validate PayNow ID format based on type
      switch (data.paynow_type) {
        case "UEN":
          return data.paynow_id.length <= 10;
        case "MOBILE":
          return data.paynow_id.startsWith("+");
        case "NRIC":
          return data.paynow_id.length === 9;
        default:
          return true;
      }
    },
    {
      message: "Invalid PayNow ID format for type",
    }
  );

/**
 * Bank Account Input Schema (Write - to API)
 *
 * Matches BankAccountCreateSerializer from backend
 */
export const bankAccountInputSchema = z
  .object({
    account_name: z.string().min(1, "Account name required").max(200),
    bank_name: z.string().min(1, "Bank name required").max(200),
    account_number: z.string().min(1, "Account number required").max(50),
    bank_code: z.string().max(10).optional(),
    branch_code: z.string().max(10).optional(),
    currency: z.string().length(3).toUpperCase().default("SGD"),
    gl_account: z.string().uuid({ message: "GL account must be a valid UUID" }),
    paynow_type: z.enum(PAYNOW_TYPES).optional().nullable(),
    paynow_id: z.string().max(20).optional().nullable(),
    is_default: z.boolean().optional().default(false),
    opening_balance: z
      .string()
      .regex(/^\d*\.?\d{0,4}$/, "Invalid amount format")
      .default("0.0000"),
    opening_balance_date: z.string().optional().nullable(),
  })
  .refine(
    (data) => {
      // PayNow type and ID must both be set or both be null
      if (data.paynow_type && !data.paynow_id) return false;
      if (data.paynow_id && !data.paynow_type) return false;
      return true;
    },
    {
      message: "PayNow type and ID must both be set or both be null",
      path: ["paynow_id"],
    }
  )
  .refine(
    (data) => {
      if (!data.paynow_type || !data.paynow_id) return true;

      // Validate PayNow ID format based on type
      switch (data.paynow_type) {
        case "UEN":
          return data.paynow_id.length <= 10;
        case "MOBILE":
          return data.paynow_id.startsWith("+");
        case "NRIC":
          return data.paynow_id.length === 9;
        default:
          return true;
      }
    },
    {
      message: "Invalid PayNow ID format for type",
      path: ["paynow_id"],
    }
  );

/**
 * Bank Account Update Schema (Write - to API)
 *
 * Matches BankAccountUpdateSerializer from backend
 */
export const bankAccountUpdateSchema = z.object({
  account_name: z.string().min(1).max(200).optional(),
  bank_name: z.string().min(1).max(200).optional(),
  bank_code: z.string().max(10).optional().nullable(),
  branch_code: z.string().max(10).optional().nullable(),
  paynow_type: z.enum(PAYNOW_TYPES).optional().nullable(),
  paynow_id: z.string().max(20).optional().nullable(),
  is_default: z.boolean().optional(),
  is_active: z.boolean().optional(),
  opening_balance: z.string().regex(/^\d*\.?\d{0,4}$/).optional(),
  opening_balance_date: z.string().optional().nullable(),
});

// Export types
export type BankAccount = z.infer<typeof bankAccountSchema>;
export type BankAccountInput = z.infer<typeof bankAccountInputSchema>;
export type BankAccountUpdate = z.infer<typeof bankAccountUpdateSchema>;

/**
 * Factory: Create empty bank account input with defaults
 */
export function createEmptyBankAccountInput(): BankAccountInput {
  return {
    account_name: "",
    bank_name: "",
    account_number: "",
    currency: "SGD",
    gl_account: "",
    is_default: false,
    opening_balance: "0.0000",
  };
}

/**
 * Helper: Format bank account for display
 */
export function formatBankAccountName(account: BankAccount): string {
  return `${account.bank_name} - ${account.account_number}`;
}

/**
 * Helper: Format opening balance for display (2dp)
 */
export function formatOpeningBalance(balance: string): string {
  const num = parseFloat(balance);
  return num.toLocaleString("en-SG", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}
