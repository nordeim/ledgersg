# Sub-Plan: Gap 4 - Bank Transactions Tab Implementation

**Gap ID:** Gap 4  
**Status:** ⏳ PENDING → Ready for Implementation  
**Estimated Effort:** 1.5-2 days  
**Priority:** HIGH  
**Created:** 2026-03-05  

---

## Executive Summary

Replace the placeholder `BankTransactionsTab` component with a fully functional bank reconciliation interface. This includes viewing imported bank transactions, importing statements via CSV, and reconciling transactions to recorded payments.

**Current State:** Placeholder showing "Bank reconciliation module coming soon"  
**Target State:** Full reconciliation workflow with import, matching, and reconciliation capabilities

---

## Dependencies Verified

| Dependency | Status | Location |
|------------|--------|----------|
| useBankTransactions hook | ✅ Ready | `src/hooks/use-banking.ts:395-424` |
| useImportBankTransactions hook | ✅ Ready | `src/hooks/use-banking.ts:429-465` |
| useReconcileTransaction hook | ✅ Ready | `src/hooks/use-banking.ts:470-498` |
| useUnreconcileTransaction hook | ✅ Ready | `src/hooks/use-banking.ts:503-530` |
| useSuggestMatches hook | ✅ Ready | `src/hooks/use-banking.ts:534-561` |
| useBankAccounts hook | ✅ Ready | `src/hooks/use-banking.ts:33-60` |
| BankTransaction interface | ✅ Ready | `src/hooks/use-banking.ts:372-390` |
| Button component | ✅ Ready | `src/components/ui/button.tsx` |
| Card component | ✅ Ready | `src/components/ui/card.tsx` |
| Input component | ✅ Ready | `src/components/ui/input.tsx` |
| Select component | ✅ Ready | `src/components/ui/select.tsx` |
| Badge component | ✅ Ready | `src/components/ui/badge.tsx` |
| Alert component | ✅ Ready | `src/components/ui/alert.tsx` |
| Tabs component | ✅ Ready | `src/components/ui/tabs.tsx` |
| Toast notifications | ✅ Ready | `src/hooks/use-toast.ts` |

---

## Component Architecture

```
banking/
├── page.tsx (server component - exists)
├── banking-client.tsx (client component - exists)
├── components/
│   ├── transaction-list.tsx (NEW)
│   ├── transaction-row.tsx (NEW)
│   ├── transaction-filters.tsx (NEW)
│   ├── import-transactions-modal.tsx (NEW)
│   ├── reconcile-modal.tsx (NEW)
│   ├── match-suggestions.tsx (NEW)
│   └── reconciliation-summary.tsx (NEW)
└── __tests__/
    ├── transactions.test.tsx (NEW)
    └── reconciliation.test.tsx (NEW)
```

---

## Phase 1: Core Components (Day 1, Morning)

### 1.1 Create TransactionList Component

**File:** `src/app/(dashboard)/banking/components/transaction-list.tsx`  
**Lines:** ~150  
**Props Interface:**
```typescript
interface TransactionListProps {
  orgId: string;
  filters?: {
    bank_account_id?: string;
    is_reconciled?: boolean;
    unreconciled_only?: boolean;
    date_from?: string;
    date_to?: string;
  };
  onTransactionClick?: (transaction: BankTransaction) => void;
}
```

**Features:**
- Display transactions in grouped list (by date)
- Columns: Date, Description, Reference, Amount, Running Balance, Status
- Expandable rows for transaction details
- Loading skeleton state
- Empty state (no transactions imported)
- Error state with retry
- Support for pagination
- Infinite scroll or "Load More" button
- Format amounts with proper currency symbols

**States:**
- `isLoading`: Show skeleton rows
- `isError`: Show error alert
- `data.count === 0`: Show empty state with import CTA
- `data.results`: Show transaction list

**Design Specs:**
- Group by transaction_date (today, yesterday, this week, older)
- Use TransactionRow component for each item
- Reconciled transactions: dimmed or strikethrough
- Unreconciled: highlighted with action button
- Running balance in muted color
- Click to expand details

**Test Cases:**
1. Renders loading skeleton
2. Renders empty state with import button
3. Renders error state
4. Groups transactions by date
5. Shows reconciled vs unreconciled
6. Handles transaction click

### 1.2 Create TransactionRow Component

**File:** `src/app/(dashboard)/banking/components/transaction-row.tsx`  
**Lines:** ~120  
**Props Interface:**
```typescript
interface TransactionRowProps {
  transaction: BankTransaction;
  isExpanded?: boolean;
  onToggle?: () => void;
  onReconcile?: () => void;
  onUnreconcile?: () => void;
}
```

**Features:**
- Collapsed view: Date, Description (truncated), Amount, Status badge
- Expanded view: Full details + matched payment info
- Status indicators:
  - Reconciled: Green checkmark + matched payment link
  - Unreconciled: Alert/warning style + "Reconcile" button
- Amount formatting (debit/credit indicators)
- Running balance display
- Import source badge (CSV, OFX, etc.)
- External reference display

**Design Specs:**
- Border bottom: `border-border`
- Hover: `hover:bg-surface`
- Reconciled: `opacity-75` or `text-text-muted`
- Amount: Debit (red-ish), Credit (green-ish)
- Expand icon: Chevron down/up

**Test Cases:**
1. Renders collapsed view
2. Toggles expanded view
3. Shows reconciled status
4. Shows unreconciled with action
5. Formats amounts correctly
6. Shows matched payment when reconciled

### 1.3 Create TransactionFilters Component

**File:** `src/app/(dashboard)/banking/components/transaction-filters.tsx`  
**Lines:** ~100  
**Props Interface:**
```typescript
interface TransactionFiltersProps {
  filters: TransactionFilters;
  onChange: (filters: TransactionFilters) => void;
  bankAccounts: Array<{ id: string; account_name: string }>;
}

interface TransactionFilters {
  bank_account_id?: string;
  is_reconciled?: boolean | null;
  unreconciled_only?: boolean;
  date_from?: string;
  date_to?: string;
}
```

**Features:**
- Bank account selector (dropdown)
- Reconciliation filter: All | Reconciled | Unreconciled
- Date range picker
- "Show only unreconciled" toggle
- Reset filters button
- Compact toolbar layout

**Design Specs:**
- Use Select for bank account and reconciliation status
- Date inputs with clear buttons
- Apply/clear filter actions
- Responsive (stack on mobile)

**Test Cases:**
1. Renders all controls
2. Updates bank account filter
3. Updates reconciliation filter
4. Toggles unreconciled only
5. Resets filters

---

## Phase 2: Import & Reconciliation Modals (Day 1, Afternoon)

### 2.1 Create ImportTransactionsModal Component

**File:** `src/app/(dashboard)/banking/components/import-transactions-modal.tsx`  
**Lines:** ~250  
**Props Interface:**
```typescript
interface ImportTransactionsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  orgId: string;
}
```

**Features:**
- Multi-step modal:
  1. **Upload Step:** Drag & drop + file picker
  2. **Preview Step:** Parse and display transactions before import
  3. **Results Step:** Show import summary

**Upload Step:**
- Drag & drop zone with visual feedback
- Click to browse file picker
- Supported formats: CSV, OFX, MT940
- File size limit (5MB)
- Bank account selector (dropdown)

**Preview Step:**
- Parse preview (first 10 rows)
- Column mapping if needed
- Validation warnings
- Import button

**Results Step:**
- Summary: Imported count, duplicates, errors
- Error table (row number, error message)
- Download error report button
- Close button

**Validation:**
- File type validation
- File size check
- CSV parsing with error handling
- Duplicate detection preview

**Test Cases:**
1. Opens and shows upload step
2. Handles drag & drop
3. Handles file picker
4. Shows preview of parsed data
5. Imports successfully
6. Shows results with counts
7. Displays errors if any
8. Handles API errors
9. Validates file type
10. Validates bank account selection

### 2.2 Create ReconcileModal Component

**File:** `src/app/(dashboard)/banking/components/reconcile-modal.tsx`  
**Lines:** ~220  
**Props Interface:**
```typescript
interface ReconcileModalProps {
  transaction: BankTransaction;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  orgId: string;
}
```

**Features:**
- Transaction details section (read-only)
- Auto-suggested matches section
- Manual payment search section
- Selected payment comparison

**Transaction Details:**
- Date, Description, Reference
- Amount (prominent)
- Running balance
- Import source

**Suggested Matches Section:**
- Loading state while fetching
- List of suggested payments
- Match score/confidence percentage
- Payment details: number, date, amount, contact
- Amount difference indicator
- "Match" button for each

**Manual Search Section:**
- Search input for payment number
- Search results list
- Select payment to compare

**Comparison View:**
- Side-by-side comparison
- Highlight differences
- Confirm reconcile button

**Already Reconciled State:**
- Show matched payment details
- Unreconcile button
- Confirmation dialog

**Test Cases:**
1. Loads suggestions automatically
2. Displays match scores
3. Allows manual search
4. Compares transaction with payment
5. Confirms reconciliation
6. Handles unreconcile
7. Shows loading states
8. Handles API errors

### 2.3 Create MatchSuggestions Component

**File:** `src/app/(dashboard)/banking/components/match-suggestions.tsx`  
**Lines:** ~100  
**Props Interface:**
```typescript
interface MatchSuggestionsProps {
  suggestions: PaymentMatch[];
  transactionAmount: string;
  onSelect: (paymentId: string) => void;
  isLoading?: boolean;
}

interface PaymentMatch {
  payment_id: string;
  payment_number: string;
  amount: string;
  contact_name: string;
  match_score: number;
}
```

**Features:**
- List of suggested payments
- Match confidence score (percentage)
- Amount comparison
- Date comparison
- Contact name
- One-click select button

**Design Specs:**
- Score badge: High (>80% green), Medium (50-80% yellow), Low (<50% gray)
- Amount difference: Exact match (green), Within 1% (yellow), Different (red)
- Compact card design
- Hover highlight

**Test Cases:**
1. Renders suggestions
2. Shows match scores
3. Highlights exact amount matches
4. Handles select action
5. Shows loading state

### 2.4 Create ReconciliationSummary Component

**File:** `src/app/(dashboard)/banking/components/reconciliation-summary.tsx`  
**Lines:** ~150  
**Props Interface:**
```typescript
interface ReconciliationSummaryProps {
  orgId: string;
  bankAccountId?: string;
}
```

**Features:**
- Stats cards:
  - Total transactions
  - Reconciled count
  - Unreconciled count
  - Reconciliation rate (percentage)
- Bank account selector
- Date range for stats
- Last import timestamp
- Quick actions: Import statement, View unreconciled

**Design Specs:**
- Card layout with 4 stat columns
- Progress bar for reconciliation rate
- Color coding: Reconciled (green), Unreconciled (orange)
- Compact dashboard-style

**Test Cases:**
1. Loads summary data
2. Displays stats correctly
3. Calculates reconciliation rate
4. Shows last import date
5. Handles bank account change

---

## Phase 3: Integration (Day 2, Morning)

### 3.1 Update banking-client.tsx

**File:** `src/app/(dashboard)/banking/banking-client.tsx`  
**Lines to modify:** 247-263 (BankTransactionsTab placeholder)

**New Implementation:**
```typescript
function BankTransactionsTab() {
  const { currentOrg } = useAuth();
  const orgId = currentOrg?.id ?? null;
  const [showImportModal, setShowImportModal] = useState(false);
  const [selectedTransaction, setSelectedTransaction] = useState<BankTransaction | null>(null);
  const [showReconcileModal, setShowReconcileModal] = useState(false);
  const [filters, setFilters] = useState<TransactionFilters>({});
  const { data: accountsData } = useBankAccounts(orgId, { is_active: true });

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

  const bankAccounts = accountsData?.results.map(a => ({
    id: a.id,
    account_name: a.account_name
  })) ?? [];

  return (
    <div className="space-y-4">
      <ReconciliationSummary orgId={orgId} />
      
      <Card className="border-border bg-carbon rounded-sm">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="font-display text-lg text-text-primary">
            Bank Transactions
          </CardTitle>
          <div className="flex gap-2">
            <Button
              onClick={() => setShowImportModal(true)}
              className="rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim"
            >
              <Upload className="h-4 w-4 mr-2" />
              Import Statement
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <TransactionFilters 
            filters={filters} 
            onChange={setFilters}
            bankAccounts={bankAccounts}
          />
          <TransactionList 
            orgId={orgId} 
            filters={filters}
            onTransactionClick={(transaction) => {
              setSelectedTransaction(transaction);
              setShowReconcileModal(true);
            }}
          />
        </CardContent>
      </Card>

      <ImportTransactionsModal
        open={showImportModal}
        onOpenChange={setShowImportModal}
        orgId={orgId}
      />

      {selectedTransaction && (
        <ReconcileModal
          transaction={selectedTransaction}
          open={showReconcileModal}
          onOpenChange={setShowReconcileModal}
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
import { Upload } from "lucide-react";
import { TransactionList } from "./components/transaction-list";
import { TransactionFilters, TransactionFilters as TransactionFiltersType } from "./components/transaction-filters";
import { ImportTransactionsModal } from "./components/import-transactions-modal";
import { ReconcileModal } from "./components/reconcile-modal";
import { ReconciliationSummary } from "./components/reconciliation-summary";
import { useBankTransactions } from "@/hooks/use-banking";
```

---

## Phase 4: Testing (Day 2, Afternoon)

### 4.1 Create Transaction Tests

**File:** `src/app/(dashboard)/banking/__tests__/transactions.test.tsx`  
**Lines:** ~350

**Test Coverage:**
```typescript
describe("BankTransactionsTab", () => {
  // Rendering
  test("renders transaction list", () => {});
  test("renders reconciliation summary", () => {});
  test("renders empty state", () => {});
  test("renders loading state", () => {});
  
  // Filters
  test("filters by bank account", () => {});
  test("filters by reconciliation status", () => {});
  test("filters by date range", () => {});
  test("shows only unreconciled", () => {});
  
  // Modals
  test("opens import modal", () => {});
  test("opens reconcile modal on click", () => {});
});

describe("TransactionList", () => {
  test("displays transactions", () => {});
  test("groups by date", () => {});
  test("shows reconciled status", () => {});
  test("shows unreconciled with action", () => {});
  test("handles transaction click", () => {});
  test("shows empty state with import CTA", () => {});
  test("shows loading skeleton", () => {});
});

describe("TransactionRow", () => {
  test("renders collapsed view", () => {});
  test("expands to show details", () => {});
  test("shows reconciled indicator", () => {});
  test("shows reconcile button", () => {});
  test("formats amounts correctly", () => {});
});
```

### 4.2 Create Reconciliation Tests

**File:** `src/app/(dashboard)/banking/__tests__/reconciliation.test.tsx`  
**Lines:** ~400

**Test Coverage:**
```typescript
describe("ImportTransactionsModal", () => {
  test("renders upload step", () => {});
  test("handles drag and drop", () => {});
  test("handles file selection", () => {});
  test("shows preview step", () => {});
  test("imports successfully", () => {});
  test("shows results with counts", () => {});
  test("handles import errors", () => {});
  test("validates file type", () => {});
  test("requires bank account selection", () => {});
});

describe("ReconcileModal", () => {
  test("loads suggestions", () => {});
  test("displays match scores", () => {});
  test("allows manual search", () => {});
  test("compares amounts", () => {});
  test("confirms reconciliation", () => {});
  test("handles unreconcile", () => {});
  test("shows already reconciled state", () => {});
  test("handles API errors", () => {});
});

describe("MatchSuggestions", () => {
  test("renders suggestions", () => {});
  test("shows match scores", () => {});
  test("highlights amount matches", () => {});
  test("handles selection", () => {});
});

describe("ReconciliationSummary", () => {
  test("displays stats", () => {});
  test("calculates rate", () => {});
  test("shows last import", () => {});
  test("updates on filter change", () => {});
});
```

---

## Success Criteria

### Functional
- [ ] Transaction list displays with date grouping
- [ ] Filters work (bank account, reconciliation, date)
- [ ] Import modal handles CSV upload
- [ ] Preview before import
- [ ] Results summary shows counts
- [ ] Reconcile modal loads suggestions
- [ ] Match scoring displays correctly
- [ ] Manual search works
- [ ] Reconciliation creates link
- [ ] Unreconciliation removes link
- [ ] Summary stats update

### Technical
- [ ] All hooks integrate correctly
- [ ] File upload with FormData works
- [ ] CSV parsing handles edge cases
- [ ] TypeScript compiles without errors
- [ ] No console errors/warnings
- [ ] Responsive design works

### Testing
- [ ] Minimum 15 new tests passing
- [ ] >80% coverage for new components
- [ ] No existing tests broken

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| CSV parsing edge cases | Medium | Medium | Use tested parsing library, validate format |
| Large file uploads | Low | High | Add 5MB limit, show progress indicator |
| Suggestion API slow | Medium | Low | Add loading state, cache results |
| File type compatibility | Medium | Medium | Support CSV first, OFX/MT940 later |
| Date format variations | Medium | Medium | Allow format selection in import |

---

## Definition of Done

- [ ] All 7 components created and working
- [ ] Placeholder replaced in banking-client.tsx
- [ ] 15+ tests passing
- [ ] TypeScript compilation successful
- [ ] No "coming soon" text remains
- [ ] CSV import tested with sample files
- [ ] Reconciliation workflow tested end-to-end
- [ ] Documentation updated to reflect completion

---

## Next Step

Execute Phase 1 - Create core components (TransactionList, TransactionRow, TransactionFilters)
