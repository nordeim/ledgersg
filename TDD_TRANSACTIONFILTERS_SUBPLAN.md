# TDD Sub-Plan: TransactionFilters Component

**Component:** TransactionFilters  
**Part of Gap:** Gap 4 - Bank Transactions Tab  
**TDD Approach:** RED → GREEN → REFACTOR  
**Estimated Time:** 2-3 hours  
**Target Tests:** 7 tests

---

## Executive Summary

Create a TransactionFilters component for filtering bank transactions by:
- Bank account (dropdown)
- Reconciliation status (All/Reconciled/Unreconciled)
- Date range (from/to)
- Show unreconciled only toggle

**Pattern Reference:** `payment-filters.tsx` (similar implementation for payments)

---

## Pre-Execution Validation ✅

### Dependencies Verified

| Dependency | Status | Location | Notes |
|------------|--------|----------|-------|
| Select component | ✅ Ready | `src/components/ui/select.tsx` | Used in PaymentFilters |
| Button component | ✅ Ready | `src/components/ui/button.tsx` | Standard |
| Tabs component | ✅ Ready | `src/components/ui/tabs.tsx` | Optional pattern |
| Date input | ✅ Ready | Native HTML5 | Used in PaymentFilters |
| Bank account data | ✅ Ready | `useBankAccounts` hook | Already available |

### Filter Interface Design

```typescript
interface TransactionFilters {
  bank_account_id?: string;
  is_reconciled?: boolean | null;
  unreconciled_only?: boolean;
  date_from?: string;
  date_to?: string;
}
```

**Alignment with useBankTransactions hook:**
```typescript
useBankTransactions(orgId, {
  bank_account_id?: string;
  date_from?: string;
  date_to?: string;
  is_reconciled?: boolean;
  unreconciled_only?: boolean;
})
```

✅ **Perfect alignment** - filter keys match hook parameters

---

## Phase 1: RED - Write Failing Tests

### Test File: `transaction-filters.test.tsx`
**Location:** `src/app/(dashboard)/banking/__tests__/transaction-filters.test.tsx`

#### Test 1: Renders all filter controls
**Purpose:** Verify all UI elements exist
**Expectations:**
- Bank account dropdown visible
- Reconciliation status dropdown visible
- Date from input visible
- Date to input visible
- Reset button visible

#### Test 2: Updates bank account filter
**Purpose:** Verify bank account selection triggers onChange
**Mock Data:**
```typescript
const bankAccounts = [
  { id: "acc-1", account_name: "DBS Operating Account" },
  { id: "acc-2", account_name: "OCBC Savings" },
];
```
**Action:** Select "acc-1" from dropdown
**Expected:** onChange called with `{ bank_account_id: "acc-1" }`

#### Test 3: Updates reconciliation filter
**Purpose:** Verify reconciliation status selection
**Test Cases:**
- Select "All" → `{ is_reconciled: null }`
- Select "Reconciled" → `{ is_reconciled: true }`
- Select "Unreconciled" → `{ is_reconciled: false }`

#### Test 4: Toggles unreconciled only
**Purpose:** Verify checkbox/switch toggle
**Action:** Click "Unreconciled Only" checkbox
**Expected:** onChange called with `{ unreconciled_only: true }`

#### Test 5: Updates date range
**Purpose:** Verify date inputs work
**Actions:**
- Enter "2024-03-01" in From date
- Enter "2024-03-31" in To date
**Expected:**
- onChange called with `{ date_from: "2024-03-01" }`
- onChange called with `{ date_to: "2024-03-31" }`

#### Test 6: Resets all filters
**Purpose:** Verify reset functionality
**Initial State:**
```typescript
filters = {
  bank_account_id: "acc-1",
  is_reconciled: true,
  date_from: "2024-03-01",
}
```
**Action:** Click Reset button
**Expected:** onChange called with default filters (all undefined/null)

#### Test 7: Reset button state
**Purpose:** Verify reset button enabled/disabled logic
**Test Cases:**
- Default filters (no values) → button disabled
- With active filters → button enabled

---

## Phase 2: GREEN - Implement Component

### Component File: `transaction-filters.tsx`
**Location:** `src/app/(dashboard)/banking/components/transaction-filters.tsx`

#### Implementation Structure

```typescript
"use client";

import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";

export interface TransactionFilters {
  bank_account_id?: string;
  is_reconciled?: boolean | null;
  unreconciled_only?: boolean;
  date_from?: string;
  date_to?: string;
}

interface TransactionFiltersProps {
  filters: TransactionFilters;
  onChange: (filters: TransactionFilters) => void;
  bankAccounts: Array<{ id: string; account_name: string }>;
}

export function TransactionFilters({
  filters,
  onChange,
  bankAccounts,
}: TransactionFiltersProps) {
  // Implementation follows PaymentFilters pattern
  // with transaction-specific filters
}
```

#### UI Layout Design

**Container:**
- Card with border, carbon background
- Padding: p-4
- Rounded: rounded-sm

**Filter Layout:**
```
┌─────────────────────────────────────────────────────┐
│ Bank Account    Reconciliation    Date Range        │
│ [Dropdown ▼]  [Dropdown ▼]      [From] [To]       │
│                                                   │
│ [✓] Unreconciled Only              [Reset]       │
└─────────────────────────────────────────────────────┘
```

**Responsive Behavior:**
- Desktop: Horizontal layout with 3-4 columns
- Mobile: Stack vertically

#### Implementation Details

**1. Bank Account Select:**
```typescript
<Select
  value={filters.bank_account_id || "all"}
  onValueChange={(value) => 
    onChange({ 
      ...filters, 
      bank_account_id: value === "all" ? undefined : value 
    })
  }
>
  <SelectItem value="all">All Accounts</SelectItem>
  {bankAccounts.map((account) => (
    <SelectItem key={account.id} value={account.id}>
      {account.account_name}
    </SelectItem>
  ))}
</Select>
```

**2. Reconciliation Status:**
- Map internal values to display:
  - `"all"` → `null` (All)
  - `"reconciled"` → `true`
  - `"unreconciled"` → `false`

**3. Date Inputs:**
- Native HTML5 date inputs
- Styling consistent with payment-filters.tsx

**4. Unreconciled Toggle:**
- Checkbox or switch component
- Boolean value

**5. Reset Button:**
- Check if any filter is active:
  ```typescript
  const hasActiveFilters = 
    filters.bank_account_id || 
    filters.is_reconciled !== null ||
    filters.date_from ||
    filters.date_to;
  ```
- Reset to default values (all undefined/null/false)

---

## Phase 3: REFACTOR - Optimization

### Refactoring Opportunities

**1. Extract Filter Reset Logic:**
```typescript
const createDefaultFilters = (): TransactionFilters => ({
  bank_account_id: undefined,
  is_reconciled: null,
  unreconciled_only: false,
  date_from: undefined,
  date_to: undefined,
});
```

**2. Extract Reconciliation Options:**
```typescript
const RECONCILIATION_OPTIONS = [
  { value: "all", label: "All", dataValue: null },
  { value: "reconciled", label: "Reconciled", dataValue: true },
  { value: "unreconciled", label: "Unreconciled", dataValue: false },
] as const;
```

**3. Add Memoization:**
```typescript
const hasActiveFilters = useMemo(() => {
  return filters.bank_account_id || 
         filters.is_reconciled !== null ||
         filters.date_from ||
         filters.date_to;
}, [filters]);
```

---

## Validation Checklist

### Before Implementation
- [x] Dependencies verified
- [x] Interface aligned with useBankTransactions hook
- [x] UI components available
- [x] Pattern from PaymentFilters reviewed

### During Implementation
- [ ] Tests written first (RED phase)
- [ ] Component implements all filter controls
- [ ] All tests passing (GREEN phase)
- [ ] Code refactored (REFACTOR phase)

### After Implementation
- [ ] All 7 tests passing
- [ ] TypeScript compilation successful
- [ ] No console errors/warnings
- [ ] Responsive design works
- [ ] Reset functionality works
- [ ] Integration with TransactionList tested

---

## Success Criteria

**Functional:**
- ✅ All filter controls render correctly
- ✅ Bank account selection updates filters
- ✅ Reconciliation status updates correctly
- ✅ Date range inputs work
- ✅ Unreconciled toggle works
- ✅ Reset button clears all filters
- ✅ Reset button disabled when no filters active

**Technical:**
- ✅ TypeScript types correct
- ✅ Props interface documented
- ✅ No prop drilling issues
- ✅ State management clean

**Testing:**
- ✅ 7/7 tests passing
- ✅ >80% code coverage
- ✅ Edge cases covered (empty accounts, etc.)

---

## Integration with TransactionList

**Parent Component Usage:**
```typescript
const [filters, setFilters] = useState<TransactionFilters>({});
const { data: accountsData } = useBankAccounts(orgId, { is_active: true });

return (
  <div className="space-y-4">
    <TransactionFilters
      filters={filters}
      onChange={setFilters}
      bankAccounts={accountsData?.results || []}
    />
    <TransactionList 
      orgId={orgId} 
      filters={filters}
    />
  </div>
);
```

**Data Flow:**
1. User changes filter in TransactionFilters
2. onChange updates parent state
3. Parent passes new filters to TransactionList
4. TransactionList calls useBankTransactions with filters
5. React Query fetches filtered data

---

## Risk Mitigation

| Risk | Probability | Mitigation |
|------|-------------|------------|
| Empty bank accounts list | Low | Show "All Accounts" option only |
| Date format issues | Low | Use ISO format (YYYY-MM-DD) |
| Filter state confusion | Low | Clear labels and reset button |
| Mobile layout issues | Medium | Test responsive breakpoints |

---

## Next Steps After Completion

1. ✅ TransactionFilters complete (7 tests)
2. ⏳ Phase 1 Complete (24 tests total)
3. ⏳ Move to Phase 2: Modals
   - ReconciliationSummary (6 tests)
   - ImportTransactionsForm (10 tests)
   - ReconcileForm (12 tests)
   - MatchSuggestions (6 tests)

---

**Plan Status:** ✅ Validated & Ready for Execution  
**Next Action:** Write failing tests (Phase 1: RED)
