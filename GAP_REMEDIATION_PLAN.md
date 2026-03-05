# LedgerSG Gap Remediation Plan

**Plan Date:** 2026-03-05  
**Status:** Planned → Validated → Ready for Execution  
**Priority:** High  
**Estimated Effort:** 2-3 days

---

## Executive Summary

This plan addresses the 4 gaps identified in the validation of `Current_Project_Status_2.md`:

| Gap | Severity | Effort | Status |
|-----|----------|--------|--------|
| **Gap 1:** Test count documentation | 🟡 Medium | 30 min | Planned |
| **Gap 2:** Phase 5.4 status clarity | 🟡 Medium | 15 min | Planned |
| **Gap 3:** Payment Tab UI (placeholder) | 🔴 High | 1-2 days | Planned |
| **Gap 4:** Bank Transactions Tab UI (placeholder) | 🔴 High | 1-2 days | Planned |

---

## Gap 1: Test Count Documentation

### Current State
- **README.md Line 63:** "222+ tests (206 frontend + 87 backend)"
- **ACCOMPLISHMENTS.md Line 38:** "87 backend + 36 TDD + 33 integration + 16 UI + 34 hooks = 206 tests"
- **Actual:** 325 backend tests + ~200 frontend tests = ~525 total

### Remediation Plan

#### Step 1.1: Update README.md
**File:** `/home/project/Ledger-SG/README.md`  
**Line:** 63  
**Current:**
```
| **Overall** | — | ✅ **Platform Ready** | 222+ tests (206 frontend + 87 backend), WCAG AAA, IRAS Compliant, 98% Security Score |
```

**New:**
```
| **Overall** | — | ✅ **Platform Ready** | ~525+ tests (325 backend + ~200 frontend), WCAG AAA, IRAS Compliant, 98% Security Score |
```

#### Step 1.2: Update ACCOMPLISHMENTS.md
**File:** `/home/project/Ledger-SG/ACCOMPLISHMENTS.md`  
**Line:** 38  
**Current:**
```
| **Testing** | ✅ Complete | v1.4.0 | 87 backend + 36 TDD + 33 integration + 16 UI + 34 hooks = 206 tests |
```

**New:**
```
| **Testing** | ✅ Complete | v1.4.0 | 325 backend + 16 UI + 34 hooks + ~150 other = ~525 total tests |
```

**Rationale:** 
- Backend: `pytest --collect-only` shows 325 tests (not 87)
- Frontend: 16 UI tests (banking page) + 34 hook tests (use-banking) + ~150 other tests
- The "87" count was likely integration tests only, not total

---

## Gap 2: Phase 5.4 Status Clarity

### Current State
- **ACCOMPLISHMENTS.md Line 43:** "Phase 5.4 Banking Frontend Integration ✅ COMPLETE"
- **ACCOMPLISHMENTS.md Line 37:** "Banking Frontend: v1.0.0 - Phase 5.4: Banking UI page with tabs (16 tests)"
- **README.md Line 60:** "Banking UI: v1.0.0 - Phase 5.4 Complete"

### Actual State
- ✅ Bank Accounts tab: **FULLY IMPLEMENTED**
- ❌ Payments tab: **PLACEHOLDER** ("coming soon")
- ❌ Bank Transactions tab: **PLACEHOLDER** ("coming soon")

### Remediation Plan

#### Step 2.1: Update ACCOMPLISHMENTS.md
**File:** `/home/project/Ledger-SG/ACCOMPLISHMENTS.md`  
**Lines:** 37, 43, 46  

**Line 37 Change:**
```
| **Banking Frontend** | ⚠️ Partial | v1.0.0 | Phase 5.4: Structure Complete (16 tests), Payment/Reconciliation UI Pending |
```

**Line 43 Change:**
```markdown
# Major Milestone: Phase 5.4 Banking Frontend Integration ⚠️ PARTIAL (2026-03-05)

## Executive Summary
Implemented Banking UI **structure** using Test-Driven Development (TDD). Created tabbed interface framework with Bank Accounts fully implemented. Payments and Bank Transactions tabs are currently placeholders pending Phase 5.5 implementation. Achieved **100% test pass rate** (16/16 tests) for existing functionality.
```

**Line 59 Change:**
```markdown
- **Tabbed Interface**: 3 tabs (Accounts ✅, Payments ⏳, Transactions ⏳) with Radix UI tabs
```

#### Step 2.2: Update README.md
**File:** `/home/project/Ledger-SG/README.md`  
**Lines:** 60, 67-77  

**Line 60 Change:**
```
| **Banking UI** | v1.0.0 | ⚠️ Phase 5.4 Partial | Structure Complete: 16 TDD tests, Accounts tab live, Payments/Reconciliation pending |
```

**Lines 67-77: Add clarification**
```markdown
**🎉 Phase 5.4: Banking Frontend UI Structure (TDD)** — 2026-03-05
- ✅ **16 TDD Tests Passing**: 100% coverage for banking UI structure
- ✅ **Banking Page Created**: Tabbed interface framework with 3 tabs
- ✅ **Bank Accounts Tab**: Fully implemented with data fetching
- ⏳ **Payments Tab**: Placeholder - Phase 5.5
- ⏳ **Bank Transactions Tab**: Placeholder - Phase 5.5
- ✅ **Server/Client Split**: Next.js metadata compliance pattern implemented
- ✅ **Radix Tabs Component**: Accessible tab navigation with WCAG AAA support
```

---

## Gap 3: Payment Tab Implementation

### Current State
**File:** `apps/web/src/app/(dashboard)/banking/banking-client.tsx` Lines 225-241

```tsx
function PaymentsTab() {
  return (
    <Card className="border-border bg-carbon rounded-sm">
      <CardContent className="py-12">
        <div className="text-center">
          <CreditCard className="h-12 w-12 text-text-muted mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-text-primary mb-2">
            Payments module coming soon
          </h3>
          <p className="text-text-secondary">
            Receive and make payments with allocation tracking
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
```

### Requirements
Based on existing hooks in `use-banking.ts`:
- ✅ `usePayments()` - List payments
- ✅ `usePayment()` - Get single payment
- ✅ `useReceivePayment()` - Create receive payment
- ✅ `useMakePayment()` - Create make payment
- ✅ `useAllocatePayment()` - Allocate to invoices
- ✅ `useVoidPayment()` - Void payment

### Implementation Plan

#### Phase 3.1: Create Payment Components

**3.1.1 Create `PaymentList` Component**
```
File: apps/web/src/app/(dashboard)/banking/components/payment-list.tsx
Features:
- Display payment list with columns: Number, Contact, Date, Amount, Status
- Filter by: Payment type (RECEIVED/MADE), Date range, Reconciled status
- Actions: View details, Void (if not reconciled)
- Empty state
- Loading state
- Error state
```

**3.1.2 Create `PaymentCard` Component**
```
File: apps/web/src/app/(dashboard)/banking/components/payment-card.tsx
Features:
- Compact payment display
- Payment number badge
- Contact name
- Amount with currency
- Status indicator (reconciled, voided)
- Click to view details
```

**3.1.3 Create `PaymentFilters` Component**
```
File: apps/web/src/app/(dashboard)/banking/components/payment-filters.tsx
Features:
- Payment type tabs (All, Received, Made)
- Date range picker
- Reconciliation status toggle
- Reset filters button
```

**3.1.4 Create `ReceivePaymentModal` Component**
```
File: apps/web/src/app/(dashboard)/banking/components/receive-payment-modal.tsx
Features:
- Form for receiving payment
- Fields: Contact (searchable), Bank Account (dropdown), Amount, Date, Reference, Method
- Validation
- Submit button with loading state
- Success/error handling
```

**3.1.5 Create `MakePaymentModal` Component**
```
File: apps/web/src/app/(dashboard)/banking/components/make-payment-modal.tsx
Features:
- Form for making payment
- Fields: Supplier (searchable), Bank Account, Amount, Date, Reference, Method
- Validation
- Submit button with loading state
- Success/error handling
```

**3.1.6 Create `PaymentDetail` Component**
```
File: apps/web/src/app/(dashboard)/banking/components/payment-detail.tsx
Features:
- Full payment information display
- Allocation section (if allocated)
- Actions: Allocate, Void (if applicable)
- Close button
```

**3.1.7 Create `AllocatePaymentModal` Component**
```
File: apps/web/src/app/(dashboard)/banking/components/allocate-payment-modal.tsx
Features:
- List unpaid invoices for contact
- Checkbox + amount input for each invoice
- Auto-calculate remaining allocation
- Submit allocation
- Validation
```

#### Phase 3.2: Replace Placeholder in banking-client.tsx

**File:** `apps/web/src/app/(dashboard)/banking/banking-client.tsx`

**Import additions:**
```tsx
import { PaymentList } from "./components/payment-list";
import { ReceivePaymentModal } from "./components/receive-payment-modal";
import { MakePaymentModal } from "./components/make-payment-modal";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { useState } from "react";
```

**Replace PaymentsTab function (lines 225-241):**
```tsx
function PaymentsTab() {
  const { currentOrg } = useAuth();
  const orgId = currentOrg?.id ?? null;
  const [showReceiveModal, setShowReceiveModal] = useState(false);
  const [showMakeModal, setShowMakeModal] = useState(false);

  if (!orgId) {
    return (
      <Card className="border-border bg-carbon rounded-sm">
        <CardContent className="py-12 text-center">
          <AlertTriangle className="h-12 w-12 text-warning mx-auto mb-4" />
          <p className="text-text-secondary">No organisation selected</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card className="border-border bg-carbon rounded-sm">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="font-display text-lg text-text-primary">
            Payments
          </CardTitle>
          <div className="flex gap-2">
            <Button
              onClick={() => setShowReceiveModal(true)}
              className="rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim"
            >
              <Plus className="h-4 w-4 mr-2" />
              Receive Payment
            </Button>
            <Button
              onClick={() => setShowMakeModal(true)}
              variant="outline"
              className="rounded-sm"
            >
              <Plus className="h-4 w-4 mr-2" />
              Make Payment
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <PaymentList orgId={orgId} />
        </CardContent>
      </Card>

      <ReceivePaymentModal
        open={showReceiveModal}
        onOpenChange={setShowReceiveModal}
        orgId={orgId}
      />

      <MakePaymentModal
        open={showMakeModal}
        onOpenChange={setShowMakeModal}
        orgId={orgId}
      />
    </div>
  );
}
```

#### Phase 3.3: Create Tests

**File:** `apps/web/src/app/(dashboard)/banking/__tests__/payments.test.tsx`

**Test Coverage:**
```
1. Payment list renders with data
2. Payment list shows loading state
3. Payment list shows empty state
4. Payment list shows error state
5. Receive Payment button opens modal
6. Make Payment button opens modal
7. Receive Payment form validation
8. Make Payment form validation
9. Payment card displays correctly
10. Payment allocation works
11. Payment void confirmation
12. Payment filters work
```

---

## Gap 4: Bank Transactions Tab Implementation

### Current State
**File:** `apps/web/src/app/(dashboard)/banking/banking-client.tsx` Lines 247-263

```tsx
function BankTransactionsTab() {
  return (
    <Card className="border-border bg-carbon rounded-sm">
      <CardContent className="py-12">
        <div className="text-center">
          <ArrowLeftRight className="h-12 w-12 text-text-muted mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-text-primary mb-2">
            Bank reconciliation module coming soon
          </h3>
          <p className="text-text-secondary">
            Import bank statements and reconcile transactions
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
```

### Requirements
Based on existing hooks in `use-banking.ts`:
- ✅ `useBankTransactions()` - List transactions
- ✅ `useImportBankTransactions()` - Import CSV
- ✅ `useReconcileTransaction()` - Reconcile to payment
- ✅ `useUnreconcileTransaction()` - Remove reconciliation
- ✅ `useSuggestMatches()` - Auto-match suggestions

### Implementation Plan

#### Phase 4.1: Create Transaction Components

**4.1.1 Create `BankTransactionList` Component**
```
File: apps/web/src/app/(dashboard)/banking/components/transaction-list.tsx
Features:
- Display transactions with columns: Date, Description, Reference, Amount, Status
- Filter by: Bank account, Date range, Reconciliation status
- Group by date
- Infinite scroll or pagination
- Empty state
- Loading state
- Error state
```

**4.1.2 Create `BankTransactionRow` Component**
```
File: apps/web/src/app/(dashboard)/banking/components/transaction-row.tsx
Features:
- Single transaction display
- Expandable details
- Reconciliation status indicator
- Match suggestions preview
- Action buttons: Reconcile, Unreconcile, View
```

**4.1.3 Create `ImportTransactionsModal` Component**
```
File: apps/web/src/app/(dashboard)/banking/components/import-transactions-modal.tsx
Features:
- CSV file upload (drag & drop + file picker)
- Bank account selector
- Preview parsed transactions before import
- Import progress indicator
- Results summary (imported, duplicates, errors)
- Download error report
```

**4.1.4 Create `ReconcileModal` Component**
```
File: apps/web/src/app/(dashboard)/banking/components/reconcile-modal.tsx
Features:
- Transaction details
- Auto-suggested matches list
- Manual payment search
- Match comparison (amount, date, reference)
- Confirm reconcile button
- Unreconcile option (if already reconciled)
```

**4.1.5 Create `MatchSuggestions` Component**
```
File: apps/web/src/app/(dashboard)/banking/components/match-suggestions.tsx
Features:
- List suggested payment matches
- Display match score/confidence
- Amount comparison
- Date comparison
- One-click match button
```

**4.1.6 Create `ReconciliationSummary` Component**
```
File: apps/web/src/app/(dashboard)/banking/components/reconciliation-summary.tsx
Features:
- Show reconciliation stats
- Total transactions
- Reconciled count
- Unreconciled count
- Last import date
- Account selector
```

#### Phase 4.2: Replace Placeholder in banking-client.tsx

**File:** `apps/web/src/app/(dashboard)/banking/banking-client.tsx`

**Import additions:**
```tsx
import { BankTransactionList } from "./components/transaction-list";
import { ImportTransactionsModal } from "./components/import-transactions-modal";
import { ReconciliationSummary } from "./components/reconciliation-summary";
import { Upload } from "lucide-react";
```

**Replace BankTransactionsTab function (lines 247-263):**
```tsx
function BankTransactionsTab() {
  const { currentOrg } = useAuth();
  const orgId = currentOrg?.id ?? null;
  const [showImportModal, setShowImportModal] = useState(false);

  if (!orgId) {
    return (
      <Card className="border-border bg-carbon rounded-sm">
        <CardContent className="py-12 text-center">
          <AlertTriangle className="h-12 w-12 text-warning mx-auto mb-4" />
          <p className="text-text-secondary">No organisation selected</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <ReconciliationSummary orgId={orgId} />
      
      <Card className="border-border bg-carbon rounded-sm">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="font-display text-lg text-text-primary">
            Bank Transactions
          </CardTitle>
          <Button
            onClick={() => setShowImportModal(true)}
            className="rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim"
          >
            <Upload className="h-4 w-4 mr-2" />
            Import Statement
          </Button>
        </CardHeader>
        <CardContent>
          <BankTransactionList orgId={orgId} />
        </CardContent>
      </Card>

      <ImportTransactionsModal
        open={showImportModal}
        onOpenChange={setShowImportModal}
        orgId={orgId}
      />
    </div>
  );
}
```

#### Phase 4.3: Create Tests

**File:** `apps/web/src/app/(dashboard)/banking/__tests__/transactions.test.tsx`

**Test Coverage:**
```
1. Transaction list renders with data
2. Transaction list shows loading state
3. Transaction list shows empty state
4. Transaction list shows error state
5. Import button opens modal
6. CSV upload works
7. Transaction reconciliation flow
8. Transaction unreconciliation flow
9. Match suggestions display
10. Match confidence scoring
11. Reconciliation summary displays
12. Bank account filter works
```

---

## Validation Checklist

Before execution, verify:

### Gap 1: Test Counts
- [ ] Run `pytest --collect-only` in backend - confirm 325 tests
- [ ] Count frontend test files - confirm ~200 tests
- [ ] Update README.md line 63
- [ ] Update ACCOMPLISHMENTS.md line 38

### Gap 2: Phase 5.4 Status
- [ ] Review banking-client.tsx lines 225-263 - confirm placeholders
- [ ] Update ACCOMPLISHMENTS.md lines 37, 43, 59
- [ ] Update README.md lines 60, 67-77

### Gap 3: Payment Tab
- [ ] Verify usePayments hook exists
- [ ] Verify useReceivePayment hook exists
- [ ] Verify useMakePayment hook exists
- [ ] Verify useAllocatePayment hook exists
- [ ] Plan component architecture
- [ ] Identify required UI components

### Gap 4: Bank Transactions Tab
- [ ] Verify useBankTransactions hook exists
- [ ] Verify useImportBankTransactions hook exists
- [ ] Verify useReconcileTransaction hook exists
- [ ] Verify useSuggestMatches hook exists
- [ ] Plan component architecture
- [ ] Identify required UI components

---

## Execution Order

### Phase 1: Documentation Updates (30 min)
1. Update README.md test counts
2. Update ACCOMPLISHMENTS.md test counts
3. Update Phase 5.4 status to "Partial"

### Phase 2: Payment Tab Implementation (1-2 days)
4. Create PaymentList component
5. Create PaymentCard component
6. Create PaymentFilters component
7. Create ReceivePaymentModal component
8. Create MakePaymentModal component
9. Replace placeholder in banking-client.tsx
10. Create payment tests

### Phase 3: Bank Transactions Tab Implementation (1-2 days)
11. Create BankTransactionList component
12. Create BankTransactionRow component
13. Create ImportTransactionsModal component
14. Create ReconcileModal component
15. Create MatchSuggestions component
16. Create ReconciliationSummary component
17. Replace placeholder in banking-client.tsx
18. Create transaction tests

### Phase 4: Integration & Validation (2-4 hours)
19. Run all frontend tests
20. Run all backend tests
21. Build frontend
22. Update documentation to "Complete"

---

## Success Criteria

### Gap 1 Success
- README.md shows "~525+ tests"
- ACCOMPLISHMENTS.md shows "325 backend + ~200 frontend"
- Numbers match actual test counts

### Gap 2 Success
- Phase 5.4 status reads "Partial" or "Structure Complete"
- Clear indication that Payment/Reconciliation UI is pending
- No misleading "Complete" claims

### Gap 3 Success
- Payments tab displays real payment list
- Receive Payment button works
- Make Payment button works
- Minimum 10 new tests passing
- No "coming soon" placeholder text

### Gap 4 Success
- Bank Transactions tab displays real transaction list
- Import Statement button works
- Reconciliation workflow functional
- Minimum 10 new tests passing
- No "coming soon" placeholder text

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Complex payment allocation UI | Start with simple version, enhance later |
| CSV parsing edge cases | Use tested library, validate format strictly |
| Reconciliation performance | Implement pagination, lazy loading |
| Test coverage gaps | Add tests incrementally with each component |
| Hook compatibility issues | Test hooks in isolation before UI integration |

---

**Plan Status:** ✅ Validated & Ready for Execution  
**Next Step:** Execute Phase 1 (Documentation Updates)
