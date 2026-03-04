# Banking API Integration Analysis Report

**Date:** 2026-03-04
**Status:** ❌ INCOMPLETE - Frontend Implementation Missing
**Risk Level:** HIGH

---

## Executive Summary

The backend Banking API is **fully implemented** with SEC-001 remediation complete (validated serializers, service layer, comprehensive testing). However, the **frontend integration is entirely missing** - no pages, components, hooks, or TypeScript types exist for the Banking module.

---

## 1. Backend API Inventory (COMPLETE)

### 1.1 Bank Accounts API

| Endpoint | Method | Path | Status |
|----------|--------|------|--------|
| List Bank Accounts | GET | `/api/v1/{org_id}/banking/bank-accounts/` | ✅ Implemented |
| Create Bank Account | POST | `/api/v1/{org_id}/banking/bank-accounts/` | ✅ Implemented |
| Get Bank Account | GET | `/api/v1/{org_id}/banking/bank-accounts/{account_id}/` | ✅ Implemented |
| Update Bank Account | PATCH | `/api/v1/{org_id}/banking/bank-accounts/{account_id}/` | ✅ Implemented |
| Deactivate Bank Account | DELETE | `/api/v1/{org_id}/banking/bank-accounts/{account_id}/` | ✅ Implemented |

**Query Parameters (List):**
- `is_active` (boolean) - Filter by active status
- `currency` (string) - Filter by currency code
- `search` (string) - Search in account_name, bank_name, account_number

**Serializer Fields (BankAccountSerializer):**
```json
{
  "id": "uuid",
  "org": "uuid",
  "account_name": "string",
  "bank_name": "string",
  "account_number": "string",
  "bank_code": "string",
  "branch_code": "string",
  "currency": "string (3-letter)",
  "gl_account": "uuid",
  "paynow_type": "UEN|MOBILE|NRIC|null",
  "paynow_id": "string|null",
  "is_default": "boolean",
  "is_active": "boolean",
  "opening_balance": "decimal",
  "opening_balance_date": "date|null",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### 1.2 Payments API

| Endpoint | Method | Path | Status |
|----------|--------|------|--------|
| List Payments | GET | `/api/v1/{org_id}/banking/payments/` | ✅ Implemented |
| Receive Payment (Customer) | POST | `/api/v1/{org_id}/banking/payments/receive/` | ✅ Implemented |
| Make Payment (Supplier) | POST | `/api/v1/{org_id}/banking/payments/make/` | ✅ Implemented |
| Get Payment Detail | GET | `/api/v1/{org_id}/banking/payments/{payment_id}/` | ✅ Implemented |
| Allocate Payment | POST | `/api/v1/{org_id}/banking/payments/{payment_id}/allocate/` | ✅ Implemented |
| Void Payment | POST | `/api/v1/{org_id}/banking/payments/{payment_id}/void/` | ✅ Implemented |

**Query Parameters (List):**
- `payment_type` (RECEIVED|MADE) - Filter by type
- `contact_id` (uuid) - Filter by contact
- `bank_account_id` (uuid) - Filter by bank account
- `date_from` (YYYY-MM-DD) - Date range start
- `date_to` (YYYY-MM-DD) - Date range end
- `is_reconciled` (boolean) - Filter by reconciliation status
- `is_voided` (boolean) - Filter by void status

**Serializer Fields (PaymentSerializer):**
```json
{
  "id": "uuid",
  "org": "uuid",
  "payment_type": "RECEIVED|MADE",
  "payment_number": "string",
  "payment_date": "date",
  "contact": "uuid",
  "contact_name": "string (read-only)",
  "bank_account": "uuid",
  "bank_account_name": "string (read-only)",
  "currency": "string",
  "exchange_rate": "decimal",
  "amount": "decimal",
  "base_amount": "decimal (read-only)",
  "fx_gain_loss": "decimal (read-only)",
  "payment_method": "BANK_TRANSFER|CHEQUE|CASH|PAYNOW|CREDIT_CARD|GIRO|OTHER",
  "payment_method_display": "string (read-only)",
  "payment_reference": "string|null",
  "journal_entry": "uuid|null",
  "is_reconciled": "boolean",
  "is_voided": "boolean",
  "notes": "string|null",
  "allocations": "array (nested)",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### 1.3 Bank Transactions (Reconciliation) API

| Endpoint | Method | Path | Status |
|----------|--------|------|--------|
| List Bank Transactions | GET | `/api/v1/{org_id}/banking/bank-transactions/` | ✅ Implemented |
| Import Bank Transactions | POST | `/api/v1/{org_id}/banking/bank-transactions/import/` | ✅ Implemented |
| Reconcile Transaction | POST | `/api/v1/{org_id}/banking/bank-transactions/{txn_id}/reconcile/` | ✅ Implemented |
| Unreconcile Transaction | POST | `/api/v1/{org_id}/banking/bank-transactions/{txn_id}/unreconcile/` | ✅ Implemented |
| Suggest Matches | GET | `/api/v1/{org_id}/banking/bank-transactions/{txn_id}/suggest-matches/` | ✅ Implemented |

**Query Parameters (List):**
- `bank_account_id` (uuid) - Filter by bank account
- `date_from` (YYYY-MM-DD) - Date range start
- `date_to` (YYYY-MM-DD) - Date range end
- `is_reconciled` (boolean) - Filter by reconciliation status
- `unreconciled_only` (boolean) - Show only unreconciled

**Serializer Fields (BankTransactionSerializer):**
```json
{
  "id": "uuid",
  "org": "uuid",
  "bank_account": "uuid",
  "bank_account_name": "string (read-only)",
  "transaction_date": "date",
  "value_date": "date|null",
  "description": "string",
  "reference": "string|null",
  "amount": "decimal",
  "running_balance": "decimal|null",
  "is_reconciled": "boolean",
  "reconciled_at": "datetime|null",
  "matched_payment": "uuid|null",
  "import_source": "CSV|OFX|MT940|API",
  "external_id": "string|null",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

---

## 2. Frontend Integration Status (MISSING)

### 2.1 API Client Endpoints

**File:** `/apps/web/src/lib/api-client.ts`

**Status:** ⚠️ PARTIALLY CONFIGURED

```typescript
// Line 194-199: Banking endpoints defined
banking: (orgId: string) => ({
  accounts: `/api/v1/${orgId}/banking/bank-accounts/`,
  payments: `/api/v1/${orgId}/banking/payments/`,
  receivePayment: `/api/v1/${orgId}/banking/payments/receive/`,
  makePayment: `/api/v1/${orgId}/banking/payments/make/`,
}),
```

**Missing Endpoints:**
- ❌ Bank account detail: `accounts.detail(id)`
- ❌ Payment detail: `payments.detail(id)`
- ❌ Payment allocation: `payments.allocate(id)`
- ❌ Payment void: `payments.void(id)`
- ❌ Bank transactions list: `transactions`
- ❌ Bank transactions import: `transactions.import`
- ❌ Bank transactions reconcile: `transactions.reconcile(id)`
- ❌ Bank transactions unreconcile: `transactions.unreconcile(id)`
- ❌ Bank transactions suggest matches: `transactions.suggestMatches(id)`

### 2.2 TypeScript Type Definitions

**Status:** ❌ NOT CREATED

**Missing Files:**
- `/apps/web/src/shared/schemas/bank-account.ts`
- `/apps/web/src/shared/schemas/payment.ts`
- `/apps/web/src/shared/schemas/bank-transaction.ts`

### 2.3 React Query Hooks

**Status:** ❌ NOT CREATED

**Missing File:** `/apps/web/src/hooks/use-banking.ts`

**Expected Hooks:**
```typescript
// Bank Accounts
useBankAccounts(orgId, filters?)
useBankAccount(orgId, accountId)
useCreateBankAccount(orgId)
useUpdateBankAccount(orgId, accountId)
useDeactivateBankAccount(orgId, accountId)

// Payments
usePayments(orgId, filters?)
usePayment(orgId, paymentId)
useReceivePayment(orgId)
useMakePayment(orgId)
useAllocatePayment(orgId, paymentId)
useVoidPayment(orgId, paymentId)

// Bank Transactions
useBankTransactions(orgId, filters?)
useImportBankTransactions(orgId)
useReconcileTransaction(orgId, transactionId)
useUnreconcileTransaction(orgId, transactionId)
useSuggestMatches(orgId, transactionId)
```

### 2.4 UI Pages & Components

**Status:** ❌ NOT CREATED

**Missing Pages:**
- `/apps/web/src/app/(dashboard)/banking/page.tsx` - Bank accounts list
- `/apps/web/src/app/(dashboard)/banking/accounts/page.tsx` - Bank accounts management
- `/apps/web/src/app/(dashboard)/banking/accounts/[id]/page.tsx` - Bank account detail
- `/apps/web/src/app/(dashboard)/banking/payments/page.tsx` - Payments list
- `/apps/web/src/app/(dashboard)/banking/payments/receive/page.tsx` - Receive payment form
- `/apps/web/src/app/(dashboard)/banking/payments/make/page.tsx` - Make payment form
- `/apps/web/src/app/(dashboard)/banking/payments/[id]/page.tsx` - Payment detail
- `/apps/web/src/app/(dashboard)/banking/reconciliation/page.tsx` - Bank reconciliation

**Missing Components:**
- Bank account list component
- Bank account form component
- Payment list component
- Payment receive form component
- Payment make form component
- Payment allocation dialog
- Bank transaction import dialog
- Bank reconciliation interface

### 2.5 Navigation Integration

**File:** `/apps/web/src/components/layout/shell.tsx`

**Status:** ❌ NOT INTEGRATED

**Current navItems (Line 42-49):**
```typescript
const navItems: NavItem[] = [
  { icon: LayoutDashboard, label: "Dashboard", href: "/dashboard" },
  { icon: FileText, label: "Invoices", href: "/invoices" },
  { icon: Receipt, label: "Quotes", href: "/quotes" },
  { icon: BookOpen, label: "Ledger", href: "/ledger" },
  { icon: PieChart, label: "Reports", href: "/reports" },
  { icon: Settings, label: "Settings", href: "/settings" },
];
```

**Missing:** Banking navigation item

---

## 3. Data Flow Analysis

### 3.1 Current State

```
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (COMPLETE)                           │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Views (views.py)                                           │ │
│  │ - BankAccountListView (GET/POST)                           │ │
│  │ - BankAccountDetailView (GET/PATCH/DELETE)                 │ │
│  │ - PaymentListView (GET)                                    │ │
│  │ - ReceivePaymentView (POST)                                │ │
│  │ - MakePaymentView (POST)                                   │ │
│  │ - PaymentDetailView (GET)                                  │ │
│  │ - PaymentAllocateView (POST)                               │ │
│  │ - PaymentVoidView (POST)                                   │ │
│  │ - BankTransactionListView (GET)                            │ │
│  │ - BankTransactionImportView (POST)                         │ │
│  │ - BankTransactionReconcileView (POST)                      │ │
│  │ - BankTransactionUnreconcileView (POST)                    │ │
│  │ - BankTransactionSuggestMatchesView (GET)                  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                  │
│  ┌───────────────────────────▼─────────────────────────────────┐│
│  │ Serializers (serializers/)                                 ││
│  │ - BankAccountSerializer (read)                             ││
│  │ - BankAccountCreateSerializer (write)                      ││
│  │ - BankAccountUpdateSerializer (write)                      ││
│  │ - PaymentSerializer (read)                                 ││
│  │ - PaymentReceiveSerializer (write)                         ││
│  │ - PaymentMakeSerializer (write)                            ││
│  │ - PaymentVoidSerializer (write)                            ││
│  │ - PaymentAllocationSerializer (read)                       ││
│  │ - BankTransactionSerializer (read)                         ││
│  │ - BankTransactionImportSerializer (write)                  ││
│  │ - BankTransactionReconcileSerializer (write)               ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                  │
│  ┌───────────────────────────▼─────────────────────────────────┐│
│  │ Services (services/)                                       ││
│  │ - BankAccountService.create()                              ││
│  │ - BankAccountService.list()                                ││
│  │ - BankAccountService.get()                                 ││
│  │ - BankAccountService.update()                              ││
│  │ - BankAccountService.deactivate()                          ││
│  │ - PaymentService.create_received()                         ││
│  │ - PaymentService.create_made()                             ││
│  │ - PaymentService.list()                                    ││
│  │ - PaymentService.get()                                     ││
│  │ - PaymentService.allocate()                                ││
│  │ - PaymentService.void()                                    ││
│  │ - ReconciliationService.list_transactions()                ││
│  │ - ReconciliationService.import_csv()                       ││
│  │ - ReconciliationService.reconcile()                        ││
│  │ - ReconciliationService.unreconcile()                      ││
│  │ - ReconciliationService.suggest_matches()                  ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                  │
│  ┌───────────────────────────▼─────────────────────────────────┐│
│  │ Models (unmanaged, SQL-first)                              ││
│  │ - BankAccount (core schema)                                ││
│  │ - Payment (core schema)                                    ││
│  │ - PaymentAllocation (core schema)                          ││
│  │ - BankTransaction (banking schema)                         ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/JSON
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                    FRONTEND (INCOMPLETE)                        │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ API Client (api-client.ts)                                 │ │
│  │ ✅ endpoints.banking(orgId).accounts                       │ │
│  │ ✅ endpoints.banking(orgId).payments                       │ │
│  │ ✅ endpoints.banking(orgId).receivePayment                 │ │
│  │ ✅ endpoints.banking(orgId).makePayment                    │ │
│  │ ❌ Missing: detail endpoints                               │ │
│  │ ❌ Missing: transaction endpoints                          │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                  │
│  ┌───────────────────────────▼─────────────────────────────────┐│
│  │ TypeScript Types (MISSING)                                 ││
│  │ ❌ BankAccount interface                                   ││
│  │ ❌ Payment interface                                       ││
│  │ ❌ BankTransaction interface                               ││
│  │ ❌ PaymentAllocation interface                             ││
│  │ ❌ Form input types                                        ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                  │
│  ┌───────────────────────────▼─────────────────────────────────┐│
│  │ React Query Hooks (MISSING)                                ││
│  │ ❌ useBankAccounts()                                       ││
│  │ ❌ usePayments()                                           ││
│  │ ❌ useBankTransactions()                                   ││
│  │ ❌ Mutation hooks                                          ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                  │
│  ┌───────────────────────────▼─────────────────────────────────┐│
│  │ UI Components (MISSING)                                    ││
│  │ ❌ Bank accounts list page                                 ││
│  │ ❌ Payments list page                                      ││
│  │ ❌ Reconciliation interface                                ││
│  │ ❌ Forms and dialogs                                       ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Security Validation Status

### 4.1 Backend Security (COMPLETE)

✅ **SEC-001 Remediation Complete:**
- All serializers validate input before persistence
- No unvalidated `request.data.get()` patterns
- Service layer enforces business rules
- Permission checks (`CanManageBanking`)
- Multi-tenancy enforcement via RLS

**Serializer Validation Examples:**
- `BankAccountCreateSerializer.validate_gl_account()` - Ensures GL account belongs to org and is ASSET/BANK type
- `PaymentReceiveSerializer.validate_contact_id()` - Ensures contact is a customer
- `PaymentMakeSerializer.validate_contact_id()` - Ensures contact is a supplier
- `BankTransactionReconcileSerializer.validate_payment_id()` - Ensures payment is not voided

### 4.2 Frontend Security (MISSING)

❌ **No Permission Guards:**
- Missing `hasPermission('can_manage_banking')` checks
- No role-based UI rendering
- No form validation before submission

---

## 5. Integration Gaps

### GAP-1: TypeScript Type Definitions

**Priority:** HIGH
**Effort:** 2-3 hours

**Required Files:**
```typescript
// /apps/web/src/shared/schemas/bank-account.ts
export interface BankAccount {
  id: string;
  org: string;
  account_name: string;
  bank_name: string;
  account_number: string;
  bank_code?: string;
  branch_code?: string;
  currency: string;
  gl_account: string;
  paynow_type?: "UEN" | "MOBILE" | "NRIC";
  paynow_id?: string;
  is_default: boolean;
  is_active: boolean;
  opening_balance: string;
  opening_balance_date?: string;
  created_at: string;
  updated_at: string;
}

export interface BankAccountInput {
  account_name: string;
  bank_name: string;
  account_number: string;
  bank_code?: string;
  branch_code?: string;
  currency?: string;
  gl_account: string;
  paynow_type?: "UEN" | "MOBILE" | "NRIC";
  paynow_id?: string;
  is_default?: boolean;
  opening_balance?: string;
  opening_balance_date?: string;
}
```

### GAP-2: React Query Hooks

**Priority:** HIGH
**Effort:** 4-5 hours

**Required File:** `/apps/web/src/hooks/use-banking.ts`

### GAP-3: UI Pages & Components

**Priority:** HIGH
**Effort:** 16-24 hours

**Minimum Viable Implementation:**
1. Bank accounts list page (4h)
2. Bank account create/edit form (4h)
3. Payments list page (4h)
4. Payment receive form (4h)
5. Bank reconciliation interface (8h)

### GAP-4: Navigation Integration

**Priority:** MEDIUM
**Effort:** 30 minutes

**Required Change:**
```typescript
// /apps/web/src/components/layout/shell.tsx
import { Landmark } from "lucide-react";

const navItems: NavItem[] = [
  { icon: LayoutDashboard, label: "Dashboard", href: "/dashboard" },
  { icon: FileText, label: "Invoices", href: "/invoices" },
  { icon: Receipt, label: "Quotes", href: "/quotes" },
  { icon: Landmark, label: "Banking", href: "/banking" }, // NEW
  { icon: BookOpen, label: "Ledger", href: "/ledger" },
  { icon: PieChart, label: "Reports", href: "/reports" },
  { icon: Settings, label: "Settings", href: "/settings" },
];
```

### GAP-5: API Client Endpoints

**Priority:** MEDIUM
**Effort:** 30 minutes

**Required Expansion:**
```typescript
// /apps/web/src/lib/api-client.ts
banking: (orgId: string) => ({
  accounts: `/api/v1/${orgId}/banking/bank-accounts/`,
  accountDetail: (id: string) => `/api/v1/${orgId}/banking/bank-accounts/${id}/`,
  payments: `/api/v1/${orgId}/banking/payments/`,
  paymentDetail: (id: string) => `/api/v1/${orgId}/banking/payments/${id}/`,
  receivePayment: `/api/v1/${orgId}/banking/payments/receive/`,
  makePayment: `/api/v1/${orgId}/banking/payments/make/`,
  allocatePayment: (id: string) => `/api/v1/${orgId}/banking/payments/${id}/allocate/`,
  voidPayment: (id: string) => `/api/v1/${orgId}/banking/payments/${id}/void/`,
  transactions: `/api/v1/${orgId}/banking/bank-transactions/`,
  transactionImport: `/api/v1/${orgId}/banking/bank-transactions/import/`,
  transactionReconcile: (id: string) => `/api/v1/${orgId}/banking/bank-transactions/${id}/reconcile/`,
  transactionUnreconcile: (id: string) => `/api/v1/${orgId}/banking/bank-transactions/${id}/unreconcile/`,
  transactionSuggestMatches: (id: string) => `/api/v1/${orgId}/banking/bank-transactions/${id}/suggest-matches/`,
}),
```

---

## 6. Recommendations

### 6.1 Immediate Actions (Week 1)

1. **Create TypeScript types** for BankAccount, Payment, BankTransaction
2. **Expand API client endpoints** to match all backend endpoints
3. **Add Banking navigation item** to sidebar
4. **Create basic hooks** for list operations

### 6.2 Short-Term (Week 2-3)

1. **Implement bank accounts page** with CRUD operations
2. **Implement payments list page** with filtering
3. **Create payment receive form** with allocation support
4. **Add permission guards** (`can_manage_banking`)

### 6.3 Medium-Term (Week 4-6)

1. **Implement bank reconciliation interface**
2. **Add CSV import functionality** for bank transactions
3. **Create auto-match suggestions UI**
4. **Add dashboard integration** (cash on hand widget)

### 6.4 Testing Requirements

**Frontend Tests Needed:**
- Unit tests for `use-banking.ts` hooks
- Integration tests for banking pages
- E2E tests for critical flows:
  - Create bank account
  - Receive payment
  - Allocate payment
  - Reconcile transaction

---

## 7. Conclusion

The backend Banking API is **production-ready** with comprehensive validation and service layer architecture. However, the **frontend integration is completely absent**, representing a significant gap in the application's functionality.

**Key Metrics:**
- Backend API Completion: **100%** (12 endpoints)
- Frontend Integration: **0%** (0 pages, 0 hooks, 0 types)
- Estimated Frontend Effort: **24-32 hours**

**Risk Assessment:**
- **HIGH**: Users cannot manage bank accounts or payments
- **HIGH**: No reconciliation capability for bank transactions
- **MEDIUM**: Dashboard cash metrics rely on banking data (but backend handles it)

**Recommendation:** Prioritize banking frontend implementation as part of Phase 5 roadmap to complete the core accounting platform functionality.
