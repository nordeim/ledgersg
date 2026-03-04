/**
 * Bank Account Schema Tests (TDD)
 *
 * Tests validate:
 * - Type structure matches backend serializer
 * - Validation rules (PayNow, currency, etc.)
 * - Default values
 *
 * Backend Reference: apps/backend/apps/banking/serializers/bank_account.py
 */

import { describe, it, expect } from "vitest";
import {
  bankAccountSchema,
  bankAccountInputSchema,
  createEmptyBankAccountInput,
  type BankAccount,
  type BankAccountInput,
} from "../bank-account";

describe("Bank Account Schema", () => {
  const validAccountId = "550e8400-e29b-41d4-a716-446655440000";
  const validOrgId = "550e8400-e29b-41d4-a716-446655440001";
  const validGLAccountId = "550e8400-e29b-41d4-a716-446655440002";

  describe("Structure Validation", () => {
    it("should validate a complete bank account object", () => {
      const validAccount: BankAccount = {
        id: validAccountId,
        org: validOrgId,
        account_name: "Main Operating Account",
        bank_name: "DBS Bank",
        account_number: "1234567890",
        bank_code: "7171",
        branch_code: "001",
        currency: "SGD",
        gl_account: validGLAccountId,
        paynow_type: undefined,
        paynow_id: undefined,
        is_default: true,
        is_active: true,
        opening_balance: "10000.0000",
        opening_balance_date: "2024-01-01",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      const result = bankAccountSchema.safeParse(validAccount);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.account_name).toBe("Main Operating Account");
        expect(result.data.currency).toBe("SGD");
      }
    });

    it("should reject invalid UUID for id", () => {
      const invalidAccount = {
        id: "not-a-uuid",
        org: validOrgId,
        account_name: "Test Account",
        bank_name: "Test Bank",
        account_number: "123456",
        currency: "SGD",
        gl_account: validGLAccountId,
        is_default: false,
        is_active: true,
        opening_balance: "0.0000",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      const result = bankAccountSchema.safeParse(invalidAccount);
      expect(result.success).toBe(false);
    });

    it("should reject currency code not 3 letters", () => {
      const invalidAccount = {
        id: validAccountId,
        org: validOrgId,
        account_name: "Test Account",
        bank_name: "Test Bank",
        account_number: "123456",
        currency: "SG", // Invalid: must be 3 letters
        gl_account: validGLAccountId,
        is_default: false,
        is_active: true,
        opening_balance: "0.0000",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      const result = bankAccountSchema.safeParse(invalidAccount);
      expect(result.success).toBe(false);
    });

    it("should validate opening_balance format (4 decimal places)", () => {
      const validAccount = {
        id: validAccountId,
        org: validOrgId,
        account_name: "Test Account",
        bank_name: "Test Bank",
        account_number: "123456",
        currency: "SGD",
        gl_account: validGLAccountId,
        is_default: false,
        is_active: true,
        opening_balance: "10000.1234", // Valid 4dp
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      const result = bankAccountSchema.safeParse(validAccount);
      expect(result.success).toBe(true);
    });
  });

  describe("PayNow Validation", () => {
    it("should require paynow_id when paynow_type is set", () => {
      const invalidAccount = {
        id: validAccountId,
        org: validOrgId,
        account_name: "Test Account",
        bank_name: "Test Bank",
        account_number: "123456",
        currency: "SGD",
        gl_account: validGLAccountId,
        paynow_type: "UEN",
        paynow_id: undefined, // Missing
        is_default: false,
        is_active: true,
        opening_balance: "0.0000",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      const result = bankAccountSchema.safeParse(invalidAccount);
      expect(result.success).toBe(false);
    });

    it("should require paynow_type when paynow_id is set", () => {
      const invalidAccount = {
        id: validAccountId,
        org: validOrgId,
        account_name: "Test Account",
        bank_name: "Test Bank",
        account_number: "123456",
        currency: "SGD",
        gl_account: validGLAccountId,
        paynow_type: undefined, // Missing
        paynow_id: "12345678A",
        is_default: false,
        is_active: true,
        opening_balance: "0.0000",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      const result = bankAccountSchema.safeParse(invalidAccount);
      expect(result.success).toBe(false);
    });

    it("should validate UEN PayNow format (max 10 chars)", () => {
      const validAccount = {
        id: validAccountId,
        org: validOrgId,
        account_name: "Test Account",
        bank_name: "Test Bank",
        account_number: "123456",
        currency: "SGD",
        gl_account: validGLAccountId,
        paynow_type: "UEN",
        paynow_id: "12345678A", // Valid UEN (10 chars max)
        is_default: false,
        is_active: true,
        opening_balance: "0.0000",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      const result = bankAccountSchema.safeParse(validAccount);
      expect(result.success).toBe(true);
    });

    it("should reject UEN PayNow ID longer than 10 chars", () => {
      const invalidAccount = {
        id: validAccountId,
        org: validOrgId,
        account_name: "Test Account",
        bank_name: "Test Bank",
        account_number: "123456",
        currency: "SGD",
        gl_account: validGLAccountId,
        paynow_type: "UEN",
        paynow_id: "12345678901", // 11 chars - invalid
        is_default: false,
        is_active: true,
        opening_balance: "0.0000",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      const result = bankAccountSchema.safeParse(invalidAccount);
      expect(result.success).toBe(false);
    });

    it("should validate Mobile PayNow format (starts with +)", () => {
      const validAccount = {
        id: validAccountId,
        org: validOrgId,
        account_name: "Test Account",
        bank_name: "Test Bank",
        account_number: "123456",
        currency: "SGD",
        gl_account: validGLAccountId,
        paynow_type: "MOBILE",
        paynow_id: "+6591234567", // Valid mobile
        is_default: false,
        is_active: true,
        opening_balance: "0.0000",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      const result = bankAccountSchema.safeParse(validAccount);
      expect(result.success).toBe(true);
    });

    it("should reject Mobile PayNow ID not starting with +", () => {
      const invalidAccount = {
        id: validAccountId,
        org: validOrgId,
        account_name: "Test Account",
        bank_name: "Test Bank",
        account_number: "123456",
        currency: "SGD",
        gl_account: validGLAccountId,
        paynow_type: "MOBILE",
        paynow_id: "6591234567", // Missing +
        is_default: false,
        is_active: true,
        opening_balance: "0.0000",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      const result = bankAccountSchema.safeParse(invalidAccount);
      expect(result.success).toBe(false);
    });

    it("should validate NRIC PayNow format (9 chars)", () => {
      const validAccount = {
        id: validAccountId,
        org: validOrgId,
        account_name: "Test Account",
        bank_name: "Test Bank",
        account_number: "123456",
        currency: "SGD",
        gl_account: validGLAccountId,
        paynow_type: "NRIC",
        paynow_id: "S1234567A", // Valid NRIC (9 chars)
        is_default: false,
        is_active: true,
        opening_balance: "0.0000",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      const result = bankAccountSchema.safeParse(validAccount);
      expect(result.success).toBe(true);
    });

    it("should reject NRIC PayNow ID not 9 chars", () => {
      const invalidAccount = {
        id: validAccountId,
        org: validOrgId,
        account_name: "Test Account",
        bank_name: "Test Bank",
        account_number: "123456",
        currency: "SGD",
        gl_account: validGLAccountId,
        paynow_type: "NRIC",
        paynow_id: "S123456", // 7 chars - invalid
        is_default: false,
        is_active: true,
        opening_balance: "0.0000",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      const result = bankAccountSchema.safeParse(invalidAccount);
      expect(result.success).toBe(false);
    });
  });

  describe("Input Schema", () => {
    it("should apply default currency as SGD", () => {
      const input: BankAccountInput = {
        account_name: "Test Account",
        bank_name: "Test Bank",
        account_number: "123456",
        gl_account: validGLAccountId,
      };

      const result = bankAccountInputSchema.parse(input);
      expect(result.currency).toBe("SGD");
    });

    it("should apply default opening_balance as 0.0000", () => {
      const input: BankAccountInput = {
        account_name: "Test Account",
        bank_name: "Test Bank",
        account_number: "123456",
        gl_account: validGLAccountId,
      };

      const result = bankAccountInputSchema.parse(input);
      expect(result.opening_balance).toBe("0.0000");
    });

    it("should apply default is_default as false", () => {
      const input: BankAccountInput = {
        account_name: "Test Account",
        bank_name: "Test Bank",
        account_number: "123456",
        gl_account: validGLAccountId,
      };

      const result = bankAccountInputSchema.parse(input);
      expect(result.is_default).toBe(false);
    });

    it("should validate account_name is required", () => {
      const input = {
        bank_name: "Test Bank",
        account_number: "123456",
        gl_account: validGLAccountId,
      };

      const result = bankAccountInputSchema.safeParse(input);
      expect(result.success).toBe(false);
    });

    it("should validate bank_name is required", () => {
      const input = {
        account_name: "Test Account",
        account_number: "123456",
        gl_account: validGLAccountId,
      };

      const result = bankAccountInputSchema.safeParse(input);
      expect(result.success).toBe(false);
    });

    it("should validate account_number is required", () => {
      const input = {
        account_name: "Test Account",
        bank_name: "Test Bank",
        gl_account: validGLAccountId,
      };

      const result = bankAccountInputSchema.safeParse(input);
      expect(result.success).toBe(false);
    });

    it("should validate gl_account is required UUID", () => {
      const input = {
        account_name: "Test Account",
        bank_name: "Test Bank",
        account_number: "123456",
        gl_account: "not-a-uuid",
      };

      const result = bankAccountInputSchema.safeParse(input);
      expect(result.success).toBe(false);
    });
  });

  describe("Factory Function", () => {
    it("should create empty bank account input with defaults", () => {
      const empty = createEmptyBankAccountInput();

      expect(empty.account_name).toBe("");
      expect(empty.bank_name).toBe("");
      expect(empty.account_number).toBe("");
      expect(empty.currency).toBe("SGD");
      expect(empty.gl_account).toBe("");
      expect(empty.is_default).toBe(false);
      expect(empty.opening_balance).toBe("0.0000");
    });
  });
});
