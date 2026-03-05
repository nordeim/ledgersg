# Phase 5: Banking Frontend Integration - Implementation Sub-Plan

**Version:** 1.0.0
**Date:** 2026-03-04
**Status:** READY FOR EXECUTION
**Approach:** Test-Driven Development (TDD)

---

## Executive Summary

This sub-plan details the implementation of frontend UI integration for the backend Banking APIs. The implementation follows TDD principles, ensuring all code is tested before integration.

**Duration:** 24-32 hours
**Priority:** HIGH
**Dependencies:** Backend Banking API (COMPLETE)

---

## 1. Implementation Phases

### Phase 5.1: Foundation (TDD First)
**Duration:** 4-5 hours
**Priority:** CRITICAL

| Task | Test First | Implementation | Verification |
|------|-----------|----------------|--------------|
| 1.1 TypeScript Types | Write type tests | Implement schemas | Run type checker |
| 1.2 API Client Endpoints | Write endpoint tests | Expand endpoints | Run test suite |
| 1.3 React Query Hooks | Write hook tests | Implement hooks | Run test suite |
| 1.4 Navigation | Manual test | Add nav item | Visual verification |

### Phase 5.2: Bank Accounts UI
**Duration:** 8-10 hours
**Priority:** HIGH

| Task | Test First | Implementation | Verification |
|------|-----------|----------------|--------------|
| 2.1 List Page | Write component tests | Implement list page | Run E2E test |
| 2.2 Create Form | Write form tests | Implement create form | Run E2E test |
| 2.3 Edit Form | Write form tests | Implement edit form | Run E2E test |
| 2.4 Detail View | Write component tests | Implement detail view | Run E2E test |

### Phase 5.3: Payments UI
**Duration:** 8-10 hours
**Priority:** HIGH

| Task | Test First | Implementation | Verification |
|------|-----------|----------------|--------------|
| 3.1 Payments List | Write component tests | Implement list page | Run E2E test |
| 3.2 Receive Payment | Write form tests | Implement receive form | Run E2E test |
| 3.3 Payment Detail | Write component tests | Implement detail view | Run E2E test |
| 3.4 Payment Allocation | Write dialog tests | Implement allocation UI | Run E2E test |

### Phase 5.4: Integration & Polish
**Duration:** 4-6 hours
**Priority:** MEDIUM

| Task | Test First | Implementation | Verification |
|------|-----------|----------------|--------------|
| 4.1 Error Handling | Write error tests | Implement error boundaries | Run test suite |
| 4.2 Loading States | Write state tests | Implement loading UI | Visual verification |
| 4.3 Permission Guards | Write permission tests | Implement guards | Run test suite |
| 4.4 Dashboard Integration | Write integration tests | Update dashboard | Run all tests |

---

## 2. Test-Driven Development Workflow

### TDD Cycle (RED → GREEN → REFACTOR)

```
┌─────────────────────────────────────────────────────────────┐
│                    RED PHASE                                │
│  1. Write failing test for new functionality               │
│  2. Run test - confirm it fails                            │
│  3. Document expected behavior in test                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   GREEN PHASE                               │
│  1. Write minimum code to pass test                        │
│  2. Run test - confirm it passes                           │
│  3. No refactoring yet                                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                  REFACTOR PHASE                             │
│  1. Clean up code while keeping tests green                │
│  2. Remove duplication                                      │
│  3. Improve naming and structure                           │
│  4. Run tests after each change                            │
└─────────────────────────────────────────────────────────────┘
```

### Test File Structure

```
apps/web/src/
├── shared/schemas/
│   ├── bank-account.ts
│   ├── payment.ts
│   ├── bank-transaction.ts
│   └── __tests__/
│       ├── bank-account.test.ts
│       ├── payment.test.ts
│       └── bank-transaction.test.ts
├── hooks/
│   ├── use-banking.ts
│   └── __tests__/
│       └── use-banking.test.ts
├── lib/
│   └── __tests__/
│       └── banking-endpoints.test.ts
└── app/(dashboard)/banking/
    ├── __tests__/
    │   ├── accounts-list.test.tsx
    │   ├── payment-receive.test.tsx
    │   └── payment-detail.test.tsx
    └── (implementation files)
```

---

## 3. Detailed Implementation Plan

### 3.1 TypeScript Type Definitions (TDD)

#### Test File: `/apps/web/src/shared/schemas/__tests__/bank-account.test.ts`

```typescript
/**
 * Bank Account Schema Tests (TDD)
 * 
 * Tests validate:
 * - Type structure matches backend serializer
 * - Validation rules (PayNow, currency, etc.)
 * - Default values
 */

import { describe, it, expect } from "vitest";
import { bankAccountSchema, type BankAccount, type BankAccountInput } from "../bank-account";

describe("Bank Account Schema", () => {
  describe("Structure Validation", () => {
    it("should validate a complete bank account object", () => {
      const validAccount = {
        id: "550e8400-e29b-41d4-a716-446655440000",
        org: "550e8400-e29b-41d4-a716-446655440001",
        account_name: "Main Operating Account",
        bank_name: "DBS Bank",
        account_number: "1234567890",
        bank_code: "7171",
        branch_code: "001",
        currency: "SGD",
        gl_account: "550e8400-e29b-41d4-a716-446655440002",
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
    });

    it("should reject invalid currency code", () => {
      const invalidAccount = {
        // ... valid fields ...
        currency: "SG", // Invalid: must be 3 letters
      };

      const result = bankAccountSchema.safeParse(invalidAccount);
      expect(result.success).toBe(false);
    });
  });

  describe("PayNow Validation", () => {
    it("should require paynow_id when paynow_type is set", () => {
      const invalidAccount = {
        // ... valid fields ...
        paynow_type: "UEN",
        paynow_id: undefined, // Missing
      };

      const result = bankAccountSchema.safeParse(invalidAccount);
      expect(result.success).toBe(false);
    });

    it("should validate UEN PayNow format (max 10 chars)", () => {
      const validAccount = {
        // ... valid fields ...
        paynow_type: "UEN",
        paynow_id: "12345678A", // Valid UEN
      };

      const result = bankAccountSchema.safeParse(validAccount);
      expect(result.success).toBe(true);
    });

    it("should validate Mobile PayNow format (starts with +)", () => {
      const validAccount = {
        // ... valid fields ...
        paynow_type: "MOBILE",
        paynow_id: "+6591234567", // Valid mobile
      };

      const result = bankAccountSchema.safeParse(validAccount);
      expect(result.success).toBe(true);
    });

    it("should validate NRIC PayNow format (9 chars)", () => {
      const validAccount = {
        // ... valid fields ...
        paynow_type: "NRIC",
        paynow_id: "S1234567A", // Valid NRIC
      };

      const result = bankAccountSchema.safeParse(validAccount);
      expect(result.success).toBe(true);
    });
  });

  describe("Default Values", () => {
    it("should apply default currency as SGD", () => {
      const input = {
        account_name: "Test Account",
        bank_name: "Test Bank",
        account_number: "123456",
        gl_account: "550e8400-e29b-41d4-a716-446655440002",
      };

      const result = bankAccountInputSchema.parse(input);
      expect(result.currency).toBe("SGD");
    });
  });
});
```

#### Implementation File: `/apps/web/src/shared/schemas/bank-account.ts`

```typescript
import { z } from "zod";

/**
 * LEDGERSG BANK ACCOUNT SCHEMA
 * 
 * IRAS Compliance: PayNow validation for Singapore businesses
 * Currency: 3-letter ISO code
 * Financial Precision: 4 decimal places (internal)
 */

// PayNow Types (Singapore-specific)
export const PAYNOW_TYPES = ["UEN", "MOBILE", "NRIC"] as const;
export type PayNowType = (typeof PAYNOW_TYPES)[number];

// Payment Methods
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

// Bank Account Schema
export const bankAccountSchema = z.object({
  id: z.string().uuid(),
  org: z.string().uuid(),
  account_name: z.string().min(1).max(200),
  bank_name: z.string().min(1).max(200),
  account_number: z.string().min(1).max(50),
  bank_code: z.string().max(10).optional(),
  branch_code: z.string().max(10).optional(),
  currency: z.string().length(3).toUpperCase(),
  gl_account: z.string().uuid(),
  paynow_type: z.enum(PAYNOW_TYPES).optional().nullable(),
  paynow_id: z.string().max(20).optional().nullable(),
  is_default: z.boolean(),
  is_active: z.boolean(),
  opening_balance: z.string().regex(/^\d+\.\d{4}$/), // 4dp
  opening_balance_date: z.string().optional().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
}).refine(
  (data) => {
    if (data.paynow_type && !data.paynow_id) return false;
    if (data.paynow_id && !data.paynow_type) return false;
    return true;
  },
  { message: "PayNow type and ID must both be set or both be null" }
).refine(
  (data) => {
    if (data.paynow_type === "UEN" && data.paynow_id && data.paynow_id.length > 10) return false;
    if (data.paynow_type === "MOBILE" && data.paynow_id && !data.paynow_id.startsWith("+")) return false;
    if (data.paynow_type === "NRIC" && data.paynow_id && data.paynow_id.length !== 9) return false;
    return true;
  },
  { message: "Invalid PayNow ID format for type" }
);

export const bankAccountInputSchema = z.object({
  account_name: z.string().min(1, "Account name required").max(200),
  bank_name: z.string().min(1, "Bank name required").max(200),
  account_number: z.string().min(1, "Account number required").max(50),
  bank_code: z.string().max(10).optional(),
  branch_code: z.string().max(10).optional(),
  currency: z.string().length(3).toUpperCase().default("SGD"),
  gl_account: z.string().uuid(),
  paynow_type: z.enum(PAYNOW_TYPES).optional().nullable(),
  paynow_id: z.string().max(20).optional().nullable(),
  is_default: z.boolean().optional().default(false),
  opening_balance: z.string().regex(/^\d*\.?\d{0,4}$/).default("0.0000"),
  opening_balance_date: z.string().optional().nullable(),
}).refine(
  (data) => {
    if (data.paynow_type && !data.paynow_id) return false;
    if (data.paynow_id && !data.paynow_type) return false;
    return true;
  },
  { message: "PayNow type and ID must both be set or both be null", path: ["paynow_id"] }
);

export type BankAccount = z.infer<typeof bankAccountSchema>;
export type BankAccountInput = z.infer<typeof bankAccountInputSchema>;

/**
 * Factory: Create empty bank account input
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
```

---

### 3.2 Payment Type Definitions

#### Test File: `/apps/web/src/shared/schemas/__tests__/payment.test.ts`

```typescript
import { describe, it, expect } from "vitest";
import { 
  paymentSchema, 
  paymentReceiveInputSchema,
  paymentMakeInputSchema,
  type Payment,
  type PaymentReceiveInput,
} from "../payment";

describe("Payment Schema", () => {
  describe("Structure Validation", () => {
    it("should validate a complete payment object", () => {
      const validPayment = {
        id: "550e8400-e29b-41d4-a716-446655440000",
        org: "550e8400-e29b-41d4-a716-446655440001",
        payment_type: "RECEIVED",
        payment_number: "RCP-000001",
        payment_date: "2024-01-20",
        contact: "550e8400-e29b-41d4-a716-446655440002",
        contact_name: "Test Customer Pte Ltd",
        bank_account: "550e8400-e29b-41d4-a716-446655440003",
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
    });

    it("should validate payment types", () => {
      const receivedPayment = { /* ... */ payment_type: "RECEIVED" };
      const madePayment = { /* ... */ payment_type: "MADE" };
      
      expect(paymentSchema.safeParse(receivedPayment).success).toBe(true);
      expect(paymentSchema.safeParse(madePayment).success).toBe(true);
    });
  });

  describe("Receive Payment Input", () => {
    it("should validate customer payment input", () => {
      const input = {
        contact_id: "550e8400-e29b-41d4-a716-446655440002",
        bank_account_id: "550e8400-e29b-41d4-a716-446655440003",
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

    it("should validate allocations don't exceed payment amount", () => {
      const input = {
        contact_id: "550e8400-e29b-41d4-a716-446655440002",
        bank_account_id: "550e8400-e29b-41d4-a716-446655440003",
        payment_date: "2024-01-20",
        amount: "1000.0000",
        currency: "SGD",
        exchange_rate: "1.000000",
        payment_method: "BANK_TRANSFER",
        allocations: [
          { document_id: "550e8400-e29b-41d4-a716-446655440004", allocated_amount: "1200.0000" },
        ],
      };

      const result = paymentReceiveInputSchema.safeParse(input);
      expect(result.success).toBe(false);
    });
  });
});
```

---

### 3.3 API Client Endpoints Expansion

#### Test File: `/apps/web/src/lib/__tests__/banking-endpoints.test.ts`

```typescript
import { describe, it, expect } from "vitest";
import { endpoints } from "../api-client";

describe("Banking API Endpoints", () => {
  const orgId = "test-org-123";
  const accountId = "account-456";
  const paymentId = "payment-789";
  const transactionId = "txn-012";

  describe("Bank Accounts", () => {
    it("should return correct accounts list endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.accounts).toBe(`/api/v1/${orgId}/banking/bank-accounts/`);
    });

    it("should return correct account detail endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.accountDetail(accountId)).toBe(
        `/api/v1/${orgId}/banking/bank-accounts/${accountId}/`
      );
    });
  });

  describe("Payments", () => {
    it("should return correct payments list endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.payments).toBe(`/api/v1/${orgId}/banking/payments/`);
    });

    it("should return correct payment detail endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.paymentDetail(paymentId)).toBe(
        `/api/v1/${orgId}/banking/payments/${paymentId}/`
      );
    });

    it("should return correct receive payment endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.receivePayment).toBe(`/api/v1/${orgId}/banking/payments/receive/`);
    });

    it("should return correct make payment endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.makePayment).toBe(`/api/v1/${orgId}/banking/payments/make/`);
    });

    it("should return correct allocate payment endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.allocatePayment(paymentId)).toBe(
        `/api/v1/${orgId}/banking/payments/${paymentId}/allocate/`
      );
    });

    it("should return correct void payment endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.voidPayment(paymentId)).toBe(
        `/api/v1/${orgId}/banking/payments/${paymentId}/void/`
      );
    });
  });

  describe("Bank Transactions", () => {
    it("should return correct transactions list endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.transactions).toBe(`/api/v1/${orgId}/banking/bank-transactions/`);
    });

    it("should return correct transaction import endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.transactionImport).toBe(
        `/api/v1/${orgId}/banking/bank-transactions/import/`
      );
    });

    it("should return correct reconcile transaction endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.transactionReconcile(transactionId)).toBe(
        `/api/v1/${orgId}/banking/bank-transactions/${transactionId}/reconcile/`
      );
    });
  });
});
```

---

### 3.4 React Query Hooks (TDD)

#### Test File: `/apps/web/src/hooks/__tests__/use-banking.test.ts`

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useBankAccounts,
  useBankAccount,
  useCreateBankAccount,
  usePayments,
  useReceivePayment,
} from "../use-banking";
import * as apiClient from "@/lib/api-client";

// Mock API client
vi.mock("@/lib/api-client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  endpoints: {
    banking: (orgId: string) => ({
      accounts: `/api/v1/${orgId}/banking/bank-accounts/`,
      accountDetail: (id: string) => `/api/v1/${orgId}/banking/bank-accounts/${id}/`,
      payments: `/api/v1/${orgId}/banking/payments/`,
      receivePayment: `/api/v1/${orgId}/banking/payments/receive/`,
    }),
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("Banking Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("useBankAccounts", () => {
    it("should fetch bank accounts list", async () => {
      const mockAccounts = [
        { id: "1", account_name: "Main Account" },
        { id: "2", account_name: "Secondary Account" },
      ];

      vi.mocked(apiClient.api.get).mockResolvedValueOnce({
        results: mockAccounts,
        count: 2,
      });

      const { result } = renderHook(() => useBankAccounts("org-123"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.results).toHaveLength(2);
      expect(result.current.data?.results[0].account_name).toBe("Main Account");
    });

    it("should apply filters to query", async () => {
      vi.mocked(apiClient.api.get).mockResolvedValueOnce({ results: [], count: 0 });

      const { result } = renderHook(
        () => useBankAccounts("org-123", { is_active: true, currency: "SGD" }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(apiClient.api.get).toHaveBeenCalledWith(
        expect.stringContaining("is_active=true")
      );
      expect(apiClient.api.get).toHaveBeenCalledWith(
        expect.stringContaining("currency=SGD")
      );
    });

    it("should be disabled when orgId is null", () => {
      const { result } = renderHook(() => useBankAccounts(null), {
        wrapper: createWrapper(),
      });

      expect(result.current.isIdle).toBe(true);
      expect(apiClient.api.get).not.toHaveBeenCalled();
    });
  });

  describe("useBankAccount", () => {
    it("should fetch single bank account", async () => {
      const mockAccount = {
        id: "acc-123",
        account_name: "Main Operating Account",
        bank_name: "DBS Bank",
      };

      vi.mocked(apiClient.api.get).mockResolvedValueOnce(mockAccount);

      const { result } = renderHook(
        () => useBankAccount("org-123", "acc-123"),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockAccount);
    });
  });

  describe("useCreateBankAccount", () => {
    it("should create bank account and invalidate queries", async () => {
      const mockAccount = {
        id: "new-acc",
        account_name: "New Account",
      };

      vi.mocked(apiClient.api.post).mockResolvedValueOnce(mockAccount);

      const { result } = renderHook(() => useCreateBankAccount("org-123"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        result.current.mutate({
          account_name: "New Account",
          bank_name: "DBS",
          account_number: "123",
          gl_account: "gl-123",
        });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(apiClient.api.post).toHaveBeenCalledWith(
        expect.stringContaining("/bank-accounts/"),
        expect.objectContaining({ account_name: "New Account" })
      );
    });
  });

  describe("usePayments", () => {
    it("should fetch payments list with filters", async () => {
      const mockPayments = [
        { id: "pay-1", payment_number: "RCP-000001" },
        { id: "pay-2", payment_number: "PAY-000001" },
      ];

      vi.mocked(apiClient.api.get).mockResolvedValueOnce({
        results: mockPayments,
        count: 2,
      });

      const { result } = renderHook(
        () => usePayments("org-123", { payment_type: "RECEIVED" }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.results).toHaveLength(2);
      expect(apiClient.api.get).toHaveBeenCalledWith(
        expect.stringContaining("payment_type=RECEIVED")
      );
    });
  });

  describe("useReceivePayment", () => {
    it("should create received payment", async () => {
      const mockPayment = {
        id: "pay-new",
        payment_number: "RCP-000002",
      };

      vi.mocked(apiClient.api.post).mockResolvedValueOnce(mockPayment);

      const { result } = renderHook(() => useReceivePayment("org-123"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        result.current.mutate({
          contact_id: "contact-123",
          bank_account_id: "bank-123",
          payment_date: "2024-01-20",
          amount: "1000.0000",
          currency: "SGD",
          exchange_rate: "1.000000",
          payment_method: "BANK_TRANSFER",
        });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(apiClient.api.post).toHaveBeenCalledWith(
        expect.stringContaining("/payments/receive/"),
        expect.objectContaining({ amount: "1000.0000" })
      );
    });
  });
});
```

---

## 4. Implementation Checklist

### Phase 5.1: Foundation

- [ ] **RED**: Write TypeScript schema tests (bank-account.test.ts, payment.test.ts)
- [ ] **RED**: Write API endpoint tests (banking-endpoints.test.ts)
- [ ] **RED**: Write React Query hook tests (use-banking.test.ts)
- [ ] **GREEN**: Implement bank-account.ts schema
- [ ] **GREEN**: Implement payment.ts schema
- [ ] **GREEN**: Expand api-client.ts endpoints
- [ ] **GREEN**: Implement use-banking.ts hooks
- [ ] **REFACTOR**: Clean up and optimize
- [ ] **VERIFY**: Run all tests (`npm test`)

### Phase 5.2: Bank Accounts UI

- [ ] **RED**: Write accounts list component tests
- [ ] **RED**: Write account form component tests
- [ ] **GREEN**: Implement accounts list page
- [ ] **GREEN**: Implement account create/edit forms
- [ ] **REFACTOR**: Extract reusable components
- [ ] **VERIFY**: Run E2E tests

### Phase 5.3: Payments UI

- [ ] **RED**: Write payments list component tests
- [ ] **RED**: Write receive payment form tests
- [ ] **GREEN**: Implement payments list page
- [ ] **GREEN**: Implement receive payment form
- [ ] **REFACTOR**: Extract form utilities
- [ ] **VERIFY**: Run E2E tests

### Phase 5.4: Integration

- [ ] **RED**: Write error handling tests
- [ ] **RED**: Write permission guard tests
- [ ] **GREEN**: Implement error boundaries
- [ ] **GREEN**: Implement permission guards
- [ ] **GREEN**: Add navigation item
- [ ] **VERIFY**: Run full test suite

---

## 5. Test Execution Commands

```bash
# Run all unit tests
npm test

# Run specific test file
npm test bank-account.test.ts

# Run tests in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage

# Run E2E tests
npm run test:e2e

# Run all tests (unit + E2E)
npm run test:all
```

---

## 6. Success Criteria

### Unit Tests
- [ ] 100% coverage for banking schemas
- [ ] 100% coverage for banking hooks
- [ ] 100% coverage for endpoint definitions
- [ ] All tests passing

### Integration Tests
- [ ] Bank accounts CRUD flow
- [ ] Payment receive flow
- [ ] Payment allocation flow
- [ ] Error handling scenarios

### E2E Tests
- [ ] User can create bank account
- [ ] User can edit bank account
- [ ] User can receive payment
- [ ] User can allocate payment to invoice

### Code Quality
- [ ] TypeScript strict mode passing
- [ ] ESLint passing
- [ ] No console errors
- [ ] WCAG AAA accessibility

---

## 7. Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Schema mismatch | HIGH | Tests validate against backend fixtures |
| API endpoint typo | HIGH | Endpoint tests verify paths |
| Permission bypass | CRITICAL | Permission guard tests |
| Form validation | MEDIUM | Zod schema validation + tests |
| Loading state race | LOW | React Query handles caching |

---

## 8. Timeline

| Week | Phase | Deliverable |
|------|-------|-------------|
| Week 1 | 5.1 Foundation | Types, endpoints, hooks (tested) |
| Week 2 | 5.2 Bank Accounts | List page, forms (tested) |
| Week 3 | 5.3 Payments | List, receive form (tested) |
| Week 4 | 5.4 Integration | Error handling, permissions, polish |

---

## 9. Conclusion

This sub-plan ensures a rigorous, test-driven approach to implementing the Banking frontend integration. Every component will have tests before implementation, guaranteeing reliability and maintainability.

**Next Step:** Execute Phase 5.1 - Foundation with TDD workflow.
