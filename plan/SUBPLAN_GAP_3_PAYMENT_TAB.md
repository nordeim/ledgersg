# Sub-Plan: Gap 3 - Payment Tab Implementation

**Gap ID:** Gap 3  
**Status:** ⏳ PENDING → Ready for Implementation  
**Estimated Effort:** 1.5-2 days  
**Priority:** HIGH  
**Created:** 2026-03-05  

---

## Executive Summary

Replace the placeholder `PaymentsTab` component with a fully functional payment management interface. This includes viewing payments list, creating receive/make payments, and allocating payments to invoices.

**Current State:** Placeholder showing "Payments module coming soon"  
**Target State:** Full payment management with list view, modals, and allocation workflow

---

## Dependencies Verified

| Dependency | Status | Location |
|------------|--------|----------|
| usePayments hook | ✅ Ready | `src/hooks/use-banking.ts:182-213` |
| useReceivePayment hook | ✅ Ready | `src/hooks/use-banking.ts:234-263` |
| useMakePayment hook | ✅ Ready | `src/hooks/use-banking.ts:268-296` |
| useAllocatePayment hook | ✅ Ready | `src/hooks/use-banking.ts:301-330` |
| useVoidPayment hook | ✅ Ready | `src/hooks/use-banking.ts:335-363` |
| Payment schema | ✅ Ready | `src/shared/schemas/payment.ts` |
| Button component | ✅ Ready | `src/components/ui/button.tsx` |
| Card component | ✅ Ready | `src/components/ui/card.tsx` |
| Input component | ✅ Ready | `src/components/ui/input.tsx` |
| Select component | ✅ Ready | `src/components/ui/select.tsx` |
| Badge component | ✅ Ready | `src/components/ui/badge.tsx` |
| MoneyInput component | ✅ Ready | `src/components/ui/money-input.tsx` |
| Tabs component | ✅ Ready | `src/components/ui/tabs.tsx` |
| Toast notifications | ✅ Ready | `src/hooks/use-toast.ts` |

---

## Component Architecture

```
banking/
├── page.tsx (server component - exists)
├── banking-client.tsx (client component - exists)
├── components/
│   ├── payment-list.tsx (NEW)
│   ├── payment-card.tsx (NEW)
│   ├── payment-filters.tsx (NEW)
│   ├── receive-payment-modal.tsx (NEW)
│   ├── make-payment-modal.tsx (NEW)
│   ├── payment-detail.tsx (NEW)
│   └── allocate-payment-modal.tsx (NEW)
└── __tests__/
    ├── payments.test.tsx (NEW)
    └── payment-modals.test.tsx (NEW)
```

---

## Phase 1: Core Components (Day 1, Morning)

### 1.1 Create Component Directory Structure

```bash
mkdir -p /home/project/Ledger-SG/apps/web/src/app/(dashboard)/banking/components
```

### 1.2 Create PaymentList Component

**File:** `src/app/(dashboard)/banking/components/payment-list.tsx`  
**Lines:** ~120  
**Props Interface:**
```typescript
interface PaymentListProps {
  orgId: string;
  filters?: {
    payment_type?: "RECEIVED" | "MADE";
    is_reconciled?: boolean;
    date_from?: string;
    date_to?: string;
  };
  onPaymentClick?: (payment: Payment) => void;
}
```

**Features:**
- Display payments in responsive list/grid
- Columns: Payment #, Contact, Date, Amount, Method, Status
- Loading skeleton state
- Empty state with "No payments" message
- Error state with retry button
- Support for infinite scroll or pagination
- Format amounts with S$ prefix and proper decimals

**States:**
- `isLoading`: Show skeleton
- `isError`: Show error alert with retry
- `data.count === 0`: Show empty state
- `data.results`: Show payment list

**Test Cases:**
1. Renders loading skeleton
2. Renders empty state
3. Renders error state with retry
4. Renders payment list correctly
5. Handles payment click

### 1.3 Create PaymentCard Component

**File:** `src/app/(dashboard)/banking/components/payment-card.tsx`  
**Lines:** ~80  
**Props Interface:**
```typescript
interface PaymentCardProps {
  payment: Payment;
  onClick?: (payment: Payment) => void;
  showActions?: boolean;
  onVoid?: (payment: Payment) => void;
}
```

**Features:**
- Compact card design matching "Illuminated Carbon" aesthetic
- Payment number badge (colored: received=green, made=blue)
- Contact name display
- Formatted amount with currency
- Payment method icon
- Status indicators: reconciled, voided, allocated
- Hover effects for interactivity

**Design Specs:**
- Border: `border-border` with hover `hover:border-accent-primary/50`
- Background: `bg-surface` on hover
- Amount: `font-mono` with `tabular-nums`
- Status badges: `RECEIVED` (green), `MADE` (blue), `RECONCILED` (secondary), `VOIDED` (alert)

**Test Cases:**
1. Renders RECEIVED payment correctly
2. Renders MADE payment correctly
3. Shows reconciled status
4. Shows voided status with strikethrough
5. Handles click event

### 1.4 Create PaymentFilters Component

**File:** `src/app/(dashboard)/banking/components/payment-filters.tsx`  
**Lines:** ~100  
**Props Interface:**
```typescript
interface PaymentFiltersProps {
  filters: PaymentFilters;
  onChange: (filters: PaymentFilters) => void;
}

interface PaymentFilters {
  payment_type?: "RECEIVED" | "MADE" | "ALL";
  is_reconciled?: boolean | null;
  date_from?: string;
  date_to?: string;
}
```

**Features:**
- Payment type tabs: All | Received | Made
- Reconciliation status: All | Reconciled | Unreconciled
- Date range picker (from/to inputs)
- Reset filters button
- Apply filters button
- Responsive layout (stack on mobile)

**Design Specs:**
- Use Tabs component for payment type
- Use Select for reconciliation status
- Use native date inputs
- Compact toolbar layout

**Test Cases:**
1. Renders all filter controls
2. Updates payment type filter
3. Updates reconciliation filter
4. Updates date range
5. Resets all filters

---

## Phase 2: Modals (Day 1, Afternoon)

### 2.1 Create ReceivePaymentModal

**File:** `src/app/(dashboard)/banking/components/receive-payment-modal.tsx`  
**Lines:** ~180  
**Props Interface:**
```typescript
interface ReceivePaymentModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  orgId: string;
}
```

**Features:**
- Modal dialog with overlay
- Form fields:
  - Contact (searchable dropdown - reuse from invoices)
  - Bank Account (dropdown of active accounts)
  - Amount (MoneyInput with validation)
  - Currency (default SGD, editable)
  - Exchange Rate (if foreign currency)
  - Payment Date (date picker)
  - Payment Method (Select: BANK_TRANSFER, CHEQUE, CASH, PAYNOW, etc.)
  - Reference (optional text input)
  - Notes (optional textarea)
  - Auto-allocate toggle (checkbox)
- Validation with Zod schema
- Loading state on submit
- Error display
- Success toast on completion

**Validation Rules:**
- Contact required
- Bank account required
- Amount > 0
- Date required (not future)
- Method required
- Exchange rate required if currency ≠ SGD

**Test Cases:**
1. Opens and closes correctly
2. Renders all form fields
3. Validates required fields
4. Validates amount > 0
5. Submits successfully
6. Shows loading state
7. Handles API error

### 2.2 Create MakePaymentModal

**File:** `src/app/(dashboard)/banking/components/make-payment-modal.tsx`  
**Lines:** ~180  
**Props Interface:**
```typescript
interface MakePaymentModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  orgId: string;
}
```

**Features:**
- Similar structure to ReceivePaymentModal
- Supplier search instead of contact
- Same form fields and validation
- Uses `useMakePayment` hook

**Test Cases:**
1-7: Same as ReceivePaymentModal

### 2.3 Create PaymentDetail Component

**File:** `src/app/(dashboard)/banking/components/payment-detail.tsx`  
**Lines:** ~150  
**Props Interface:**
```typescript
interface PaymentDetailProps {
  payment: Payment | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAllocate?: () => void;
  onVoid?: () => void;
}
```

**Features:**
- Slide-over or modal showing full payment details
- All payment fields displayed read-only
- Allocations section (if any):
  - Invoice number
  - Allocated amount
  - Date allocated
- Actions section:
  - Allocate button (if unreconciled and not voided)
  - Void button (if not voided)
  - Close button

**Test Cases:**
1. Displays payment details correctly
2. Shows allocations if present
3. Shows allocate button when appropriate
4. Shows void button when appropriate
5. Handles close action

### 2.4 Create AllocatePaymentModal

**File:** `src/app/(dashboard)/banking/components/allocate-payment-modal.tsx`  
**Lines:** ~200  
**Props Interface:**
```typescript
interface AllocatePaymentModalProps {
  payment: Payment;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  orgId: string;
}
```

**Features:**
- Display payment info at top
- List unpaid invoices for contact:
  - Invoice number, date, due date
  - Original amount
  - Outstanding amount
  - Checkbox to select
  - Input for allocation amount (default to outstanding)
- Summary section:
  - Payment total
  - Allocated total
  - Remaining unallocated
  - Warning if over-allocated
- Validation:
  - Total allocations ≤ payment amount
  - Each allocation ≤ invoice outstanding
- Submit button (disabled if invalid)

**Test Cases:**
1. Loads unpaid invoices for contact
2. Calculates totals correctly
3. Validates allocation amounts
4. Prevents over-allocation
5. Submits successfully
6. Handles API errors

---

## Phase 3: Integration (Day 2, Morning)

### 3.1 Update banking-client.tsx

**File:** `src/app/(dashboard)/banking/banking-client.tsx`  
**Lines to modify:** 221-241 (PaymentsTab placeholder)

**New Implementation:**
```typescript
function PaymentsTab() {
  const { currentOrg } = useAuth();
  const orgId = currentOrg?.id ?? null;
  const [showReceiveModal, setShowReceiveModal] = useState(false);
  const [showMakeModal, setShowMakeModal] = useState(false);
  const [selectedPayment, setSelectedPayment] = useState<Payment | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showAllocateModal, setShowAllocateModal] = useState(false);
  const [filters, setFilters] = useState<PaymentFilters>({});

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
      <PaymentFilters filters={filters} onChange={setFilters} />
      
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
          <PaymentList 
            orgId={orgId} 
            filters={filters}
            onPaymentClick={(payment) => {
              setSelectedPayment(payment);
              setShowDetailModal(true);
            }}
          />
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

      <PaymentDetail
        payment={selectedPayment}
        open={showDetailModal}
        onOpenChange={setShowDetailModal}
        onAllocate={() => {
          setShowDetailModal(false);
          setShowAllocateModal(true);
        }}
        onVoid={() => {
          // Handle void action
        }}
      />

      {selectedPayment && (
        <AllocatePaymentModal
          payment={selectedPayment}
          open={showAllocateModal}
          onOpenChange={setShowAllocateModal}
          orgId={orgId}
        />
      )}
    </div>
  );
}
```

### 3.2 Add Imports

**Add to banking-client.tsx imports:**
```typescript
import { useState } from "react";
import { PaymentList } from "./components/payment-list";
import { PaymentFilters, PaymentFilters as PaymentFiltersType } from "./components/payment-filters";
import { ReceivePaymentModal } from "./components/receive-payment-modal";
import { MakePaymentModal } from "./components/make-payment-modal";
import { PaymentDetail } from "./components/payment-detail";
import { AllocatePaymentModal } from "./components/allocate-payment-modal";
import type { Payment } from "@/shared/schemas";
```

---

## Phase 4: Testing (Day 2, Afternoon)

### 4.1 Create Payment Tests

**File:** `src/app/(dashboard)/banking/__tests__/payments.test.tsx`  
**Lines:** ~300

**Test Coverage:**
```typescript
describe("PaymentsTab", () => {
  // Rendering
  test("renders payment list with data", () => {});
  test("renders loading state", () => {});
  test("renders empty state", () => {});
  test("renders error state", () => {});
  
  // Filters
  test("filters by payment type", () => {});
  test("filters by reconciliation status", () => {});
  test("filters by date range", () => {});
  
  // Modals
  test("opens receive payment modal", () => {});
  test("opens make payment modal", () => {});
  test("opens payment detail on click", () => {});
  test("opens allocate modal from detail", () => {});
});

describe("PaymentList", () => {
  test("displays payments correctly", () => {});
  test("handles payment click", () => {});
  test("shows skeleton while loading", () => {});
  test("shows empty state", () => {});
  test("shows error with retry", () => {});
});

describe("PaymentCard", () => {
  test("renders RECEIVED payment", () => {});
  test("renders MADE payment", () => {});
  test("shows reconciled status", () => {});
  test("shows voided status", () => {});
});
```

### 4.2 Create Modal Tests

**File:** `src/app/(dashboard)/banking/__tests__/payment-modals.test.tsx`  
**Lines:** ~400

**Test Coverage:**
```typescript
describe("ReceivePaymentModal", () => {
  test("renders form fields", () => {});
  test("validates required fields", () => {});
  test("validates amount > 0", () => {});
  test("submits successfully", () => {});
  test("handles API error", () => {});
  test("closes on cancel", () => {});
});

describe("MakePaymentModal", () => {
  // Same as ReceivePaymentModal
});

describe("AllocatePaymentModal", () => {
  test("loads unpaid invoices", () => {});
  test("calculates totals", () => {});
  test("prevents over-allocation", () => {});
  test("submits allocations", () => {});
});
```

---

## Success Criteria

### Functional
- [ ] Payment list displays with proper formatting
- [ ] Filters work (type, reconciliation, date)
- [ ] Receive Payment modal creates payments
- [ ] Make Payment modal creates payments
- [ ] Payment detail shows full information
- [ ] Allocation modal allocates to invoices
- [ ] Toast notifications on success/error

### Technical
- [ ] All hooks integrate correctly
- [ ] TypeScript compiles without errors
- [ ] No console errors/warnings
- [ ] Responsive design works
- [ ] WCAG AAA accessible

### Testing
- [ ] Minimum 15 new tests passing
- [ ] >80% coverage for new components
- [ ] No existing tests broken

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Complex allocation UI | Medium | Medium | Start with simple checkbox approach |
| Contact search integration | Medium | Medium | Reuse existing contact hook from invoices |
| Foreign exchange handling | Low | High | Default exchange rate to 1.000000 |
| Date picker browser differences | Medium | Low | Use native input, style consistently |

---

## Definition of Done

- [ ] All 6 components created and working
- [ ] Placeholder replaced in banking-client.tsx
- [ ] 15+ tests passing
- [ ] TypeScript compilation successful
- [ ] No "coming soon" text remains
- [ ] Documentation updated to reflect completion

---

**Next Step:** Execute Phase 1 - Create core components (PaymentList, PaymentCard, PaymentFilters)
