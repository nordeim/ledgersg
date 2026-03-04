# Phase 5.2: React Query Hooks - Implementation Sub-Plan

**Version:** 1.0.0
**Date:** 2026-03-04
**Status:** READY FOR EXECUTION
**Approach:** Test-Driven Development (TDD)

---

## Executive Summary

This sub-plan details the implementation of React Query hooks for the Banking module. Following the TDD methodology established in Phase 5.1, all hooks will be tested before implementation.

**Duration:** 4-5 hours
**Priority:** HIGH
**Dependencies:** Phase 5.1 (COMPLETE)

---

## 1. Pattern Analysis

### 1.1 Existing Hook Patterns

From codebase analysis (`use-invoices.ts`, `use-contacts.ts`, `use-dashboard.ts`):

**Query Hooks Pattern:**
```typescript
export function useX(orgId: string, filters?: Filters) {
  const queryString = filters
    ? "?" + new URLSearchParams(Object.entries(filters).filter(([, v]) => v)).toString()
    : "";

  return useQuery({
    queryKey: [orgId, "x", filters],
    queryFn: async () => {
      const response = await api.get<Type>(endpoints.x(orgId).list + queryString);
      return response;
    },
    enabled: !!orgId,
  });
}
```

**Mutation Hooks Pattern:**
```typescript
export function useCreateX(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Input) => {
      const response = await api.post<Type>(endpoints.x(orgId).list, data);
      return response;
    },
    onSuccess: () => {
      toast({ title: "X created", variant: "success" });
      queryClient.invalidateQueries({ queryKey: [orgId, "x"] });
      queryClient.invalidateQueries({ queryKey: [orgId, "dashboard"] });
    },
    onError: (error: Error) => {
      toast({ title: "Failed", description: error.message, variant: "error" });
    },
  });
}
```

### 1.2 Key Observations

1. **Query Keys:** `[orgId, "resource", id?]` structure
2. **Filter Handling:** URLSearchParams with empty filter removal
3. **Toast Notifications:** Success/error feedback via `use-toast`
4. **Cache Invalidation:** Invalidate list on create/update/delete
5. **Dashboard Invalidation:** Financial operations invalidate dashboard
6. **Enabled Guards:** Queries disabled when orgId is falsy

---

## 2. Banking Hooks Design

### 2.1 Bank Accounts Hooks

| Hook | Type | Purpose | Cache Keys |
|------|------|---------|------------|
| `useBankAccounts` | Query | List accounts with filters | `[orgId, "bank-accounts", filters]` |
| `useBankAccount` | Query | Get single account | `[orgId, "bank-accounts", accountId]` |
| `useCreateBankAccount` | Mutation | Create account | Invalidates: `["bank-accounts"], ["dashboard"]` |
| `useUpdateBankAccount` | Mutation | Update account | Invalidates: `["bank-accounts", accountId], ["bank-accounts"]` |
| `useDeactivateBankAccount` | Mutation | Soft delete | Invalidates: `["bank-accounts"]` |

### 2.2 Payments Hooks

| Hook | Type | Purpose | Cache Keys |
|------|------|---------|------------|
| `usePayments` | Query | List payments with filters | `[orgId, "payments", filters]` |
| `usePayment` | Query | Get single payment | `[orgId, "payments", paymentId]` |
| `useReceivePayment` | Mutation | Receive customer payment | Invalidates: `["payments"], ["dashboard"], ["invoices"]` |
| `useMakePayment` | Mutation | Make supplier payment | Invalidates: `["payments"], ["dashboard"]` |
| `useAllocatePayment` | Mutation | Allocate to invoices | Invalidates: `["payments", paymentId], ["payments"], ["invoices"]` |
| `useVoidPayment` | Mutation | Void payment | Invalidates: `["payments"], ["dashboard"]` |

### 2.3 Bank Transactions Hooks (Reconciliation)

| Hook | Type | Purpose | Cache Keys |
|------|------|---------|------------|
| `useBankTransactions` | Query | List transactions | `[orgId, "bank-transactions", filters]` |
| `useImportBankTransactions` | Mutation | Import CSV | Invalidates: `["bank-transactions"], ["dashboard"]` |
| `useReconcileTransaction` | Mutation | Reconcile to payment | Invalidates: `["bank-transactions"], ["payments"]` |
| `useUnreconcileTransaction` | Mutation | Remove reconciliation | Invalidates: `["bank-transactions", txnId]` |
| `useSuggestMatches` | Query | Get match suggestions | `[orgId, "bank-transactions", txnId, "matches"]` |

---

## 3. Test-Driven Development Workflow

### 3.1 Test Structure

```
apps/web/src/hooks/__tests__/
└── use-banking.test.ts
```

### 3.2 Test Categories

1. **Query Hooks Tests:**
   - Data fetching with filters
   - Disabled when orgId is null
   - Error handling
   - Query key structure

2. **Mutation Hooks Tests:**
   - Successful creation
   - Cache invalidation
   - Toast notifications
   - Error handling

3. **Integration Tests:**
   - Filter parameter encoding
   - Query key uniqueness
   - Cache updates

---

## 4. Implementation Plan

### Phase 5.2.1: Bank Accounts Hooks

**Test File:** `use-banking.test.ts` (Lines 1-200)

```typescript
describe("useBankAccounts", () => {
  it("should fetch bank accounts list", async () => { /* ... */ });
  it("should apply filters to query", async () => { /* ... */ });
  it("should be disabled when orgId is null", () => { /* ... */ });
  it("should handle errors gracefully", async () => { /* ... */ });
});

describe("useBankAccount", () => {
  it("should fetch single bank account", async () => { /* ... */ });
  it("should be disabled when accountId is null", () => { /* ... */ });
});

describe("useCreateBankAccount", () => {
  it("should create bank account and invalidate cache", async () => { /* ... */ });
  it("should show success toast", async () => { /* ... */ });
  it("should handle errors", async () => { /* ... */ });
});
```

**Implementation:** `use-banking.ts` (Lines 1-150)

### Phase 5.2.2: Payments Hooks

**Test File:** `use-banking.test.ts` (Lines 201-400)

**Implementation:** `use-banking.ts` (Lines 151-300)

### Phase 5.2.3: Bank Transactions Hooks

**Test File:** `use-banking.test.ts` (Lines 401-550)

**Implementation:** `use-banking.ts` (Lines 301-450)

---

## 5. Detailed Test Specifications

### 5.1 Bank Accounts Tests

#### Test: Fetch Bank Accounts List
```typescript
it("should fetch bank accounts list", async () => {
  const mockAccounts = [
    { id: "1", account_name: "Main Account", currency: "SGD" },
    { id: "2", account_name: "USD Account", currency: "USD" },
  ];

  vi.mocked(api.get).mockResolvedValueOnce({
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
```

#### Test: Apply Filters
```typescript
it("should apply filters to query", async () => {
  vi.mocked(api.get).mockResolvedValueOnce({ results: [], count: 0 });

  renderHook(
    () => useBankAccounts("org-123", { is_active: true, currency: "SGD" }),
    { wrapper: createWrapper() }
  );

  await waitFor(() => expect(api.get).toHaveBeenCalled());

  expect(api.get).toHaveBeenCalledWith(
    expect.stringContaining("is_active=true")
  );
  expect(api.get).toHaveBeenCalledWith(
    expect.stringContaining("currency=SGD")
  );
});
```

#### Test: Disabled When orgId Null
```typescript
it("should be disabled when orgId is null", () => {
  const { result } = renderHook(() => useBankAccounts(null), {
    wrapper: createWrapper(),
  });

  expect(result.current.isIdle).toBe(true);
  expect(api.get).not.toHaveBeenCalled();
});
```

#### Test: Create Bank Account
```typescript
it("should create bank account and invalidate queries", async () => {
  const mockAccount = { id: "new-acc", account_name: "New Account" };
  vi.mocked(api.post).mockResolvedValueOnce(mockAccount);

  const queryClient = new QueryClient();
  const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

  const { result } = renderHook(() => useCreateBankAccount("org-123"), {
    wrapper: createWrapper(queryClient),
  });

  await act(async () => {
    result.current.mutate({
      account_name: "New Account",
      bank_name: "DBS",
      account_number: "123",
      gl_account: "gl-123",
    });
  });

  await waitFor(() => expect(result.current.isSuccess).toBe(true));

  expect(api.post).toHaveBeenCalledWith(
    expect.stringContaining("/bank-accounts/"),
    expect.objectContaining({ account_name: "New Account" })
  );

  expect(invalidateSpy).toHaveBeenCalledWith({
    queryKey: ["org-123", "bank-accounts"],
  });
});
```

---

## 6. Implementation Code Structure

### 6.1 File Organization

```typescript
// apps/web/src/hooks/use-banking.ts

/**
 * Banking Hooks - LedgerSG Frontend
 *
 * Provides hooks for banking operations:
 * - Bank accounts CRUD
 * - Payments (receive/make)
 * - Payment allocation
 * - Bank reconciliation
 *
 * All hooks use TanStack Query for caching and state management.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, endpoints } from "@/lib/api-client";
import { toast } from "@/hooks/use-toast";
import type {
  BankAccount,
  BankAccountInput,
  BankAccountUpdate,
  Payment,
  PaymentReceiveInput,
  PaymentMakeInput,
  PaymentAllocationInput,
  PaymentVoidInput,
} from "@/shared/schemas";

// ============================================
// BANK ACCOUNTS
// ============================================

export function useBankAccounts(
  orgId: string | null,
  filters?: {
    is_active?: boolean;
    currency?: string;
    search?: string;
  }
) { /* ... */ }

export function useBankAccount(orgId: string | null, accountId: string | null) { /* ... */ }

export function useCreateBankAccount(orgId: string) { /* ... */ }

export function useUpdateBankAccount(orgId: string, accountId: string) { /* ... */ }

export function useDeactivateBankAccount(orgId: string, accountId: string) { /* ... */ }

// ============================================
// PAYMENTS
// ============================================

export function usePayments(
  orgId: string | null,
  filters?: {
    payment_type?: "RECEIVED" | "MADE";
    contact_id?: string;
    bank_account_id?: string;
    date_from?: string;
    date_to?: string;
    is_reconciled?: boolean;
    is_voided?: boolean;
  }
) { /* ... */ }

export function usePayment(orgId: string | null, paymentId: string | null) { /* ... */ }

export function useReceivePayment(orgId: string) { /* ... */ }

export function useMakePayment(orgId: string) { /* ... */ }

export function useAllocatePayment(orgId: string, paymentId: string) { /* ... */ }

export function useVoidPayment(orgId: string, paymentId: string) { /* ... */ }

// ============================================
// BANK TRANSACTIONS (RECONCILIATION)
// ============================================

export function useBankTransactions(
  orgId: string | null,
  filters?: {
    bank_account_id?: string;
    date_from?: string;
    date_to?: string;
    is_reconciled?: boolean;
    unreconciled_only?: boolean;
  }
) { /* ... */ }

export function useImportBankTransactions(orgId: string) { /* ... */ }

export function useReconcileTransaction(orgId: string, transactionId: string) { /* ... */ }

export function useUnreconcileTransaction(orgId: string, transactionId: string) { /* ... */ }

export function useSuggestMatches(
  orgId: string | null,
  transactionId: string | null,
  tolerance?: string
) { /* ... */ }
```

---

## 7. Test Execution Commands

```bash
# Run banking hooks tests
npm test -- --run src/hooks/__tests__/use-banking.test.ts

# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Watch mode
npm run test:watch
```

---

## 8. Success Criteria

### Unit Tests
- [ ] All 25+ hook tests passing
- [ ] 100% coverage for use-banking.ts
- [ ] Error scenarios covered
- [ ] Cache invalidation verified

### Integration Tests
- [ ] Query keys structured correctly
- [ ] Filters encoded properly
- [ ] Toast notifications working
- [ ] Cache updates propagated

### Code Quality
- [ ] TypeScript strict mode passing
- [ ] ESLint passing
- [ ] No console errors
- [ ] Consistent with existing patterns

---

## 9. Timeline

| Task | Duration | Deliverable |
|------|----------|-------------|
| Write Bank Accounts tests | 45 min | 8 tests |
| Implement Bank Accounts hooks | 45 min | 5 hooks |
| Write Payments tests | 45 min | 10 tests |
| Implement Payments hooks | 45 min | 6 hooks |
| Write Bank Transactions tests | 30 min | 7 tests |
| Implement Bank Transactions hooks | 30 min | 5 hooks |
| Verify & refactor | 30 min | All tests passing |

**Total:** 4.5 hours

---

## 10. Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Mock setup complexity | MEDIUM | Use existing wrapper pattern |
| Cache invalidation logic | HIGH | Test invalidation calls explicitly |
| Filter encoding | LOW | URLSearchParams handles encoding |
| Toast mocking | MEDIUM | Mock toast module |
| Query key conflicts | LOW | Follow established pattern |

---

## 11. Next Steps After Phase 5.2

**Phase 5.3: Navigation Integration**
- Add Banking menu item to sidebar
- Update navigation in `shell.tsx`

**Phase 5.4: UI Components**
- Bank accounts list page
- Payment receive form
- Reconciliation interface

---

## 12. Conclusion

This sub-plan ensures comprehensive testing and implementation of Banking React Query hooks. The TDD approach guarantees reliability and maintainability, while following established codebase patterns ensures consistency.

**Next Step:** Execute Phase 5.2.1 - Write Bank Accounts tests (RED phase).
