# Dashboard Service Remediation Plan

**Date:** 2026-03-04
**Status:** Analysis Complete - Remediation Planned
**Priority:** High
**Impact:** 20 failing tests across DashboardService

---

## Executive Summary

The DashboardService has field name mismatches between the service implementation and the actual Django models. This causes 20 test failures in `test_dashboard_service_tdd.py`. The caching implementation (Phase 4) is complete and working, but the underlying computation logic needs field alignment.

---

## Issue Analysis

### Root Cause
The DashboardService was implemented using assumed field names that don't match the actual database schema. The SQL schema is the source of truth, and Django models are unmanaged (`managed = False`), mapping directly to existing tables.

---

## Detailed Issue Breakdown

### Issue 1: InvoiceDocument Field Names ❌

**Current (Wrong) Fields in Service:**
- `subtotal` ❌
- `tax_amount` ❌
- `total` ❌
- `tax_code` ❌
- `payment_status` ❌

**Actual Fields from Model:**
```python
# From InvoiceDocument model (invoicing schema)
- base_subtotal ✅ (base currency subtotal)
- base_total_amount ✅ (base currency total)
- base_total_gst ✅ (base currency GST)
- total_excl ✅ (line-level total excluding tax)
- total_incl ✅ (line-level total including tax)
- gst_total ✅ (GST amount)
- amount_paid ✅ (amount paid)
- status ✅ (DRAFT, APPROVED, VOIDED, etc.)
# Note: No payment_status field - calculate from amount_paid vs total_incl
```

**Remediation:**
```python
# OLD (Broken):
.aggregate(total=Sum("subtotal"))

# NEW (Fixed):
.aggregate(total=Sum("base_subtotal"))
# OR for revenue (excluding GST):
.aggregate(total=Sum("total_excl"))
```

---

### Issue 2: JournalLine Field Names ❌

**Current (Wrong) Fields in Service:**
- `journal_entry` ❌
- `journal_entry__status` ❌
- `journal_entry__date` ❌

**Actual Fields from Model:**
```python
# From JournalLine model (journal schema)
- entry_id ✅ (FK to JournalEntry)
- entry ✅ (related_name accessor)
- entry__status ✅ (POSTED, DRAFT, etc.)
- entry__date ✅ (entry date)
- tax_code ✅ (FK to TaxCode)
- tax_code__is_input ✅
- tax_code__is_output ✅
```

**Remediation:**
```python
# OLD (Broken):
JournalLine.objects.filter(
    journal_entry__status="POSTED",
    journal_entry__date__gte=period_start,
)

# NEW (Fixed):
JournalLine.objects.filter(
    entry__status="POSTED",
    entry__date__gte=period_start,
)
```

---

### Issue 3: BankAccount Field Names ❌

**Current (Wrong) Fields in Service:**
- `current_balance` ❌

**Actual Fields from Model:**
```python
# From BankAccount model (banking schema)
- opening_balance ✅ (initial balance)
- opening_balance_date ✅ (when opening balance was set)
# Note: No current_balance field - must calculate from:
#   opening_balance + sum(transactions) - sum(payments)
```

**Remediation:**
```python
# OLD (Broken):
BankAccount.objects.filter(...).aggregate(total=Sum("current_balance"))

# NEW (Fixed):
# Calculate from opening_balance + transactions - payments
def calculate_cash_on_hand(self, org_id: str) -> Decimal:
    org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id
    
    # Get all bank accounts for org
    bank_accounts = BankAccount.objects.filter(org_id=org_uuid, is_active=True)
    
    total = Decimal("0.0000")
    for account in bank_accounts:
        # Calculate current balance: opening + received - paid
        total += account.opening_balance
    
    # TODO: Add transaction calculations when BankTransaction model aligned
    return money(total)
```

---

### Issue 4: Payment Status Logic ❌

**Current (Wrong) Logic:**
```python
.exclude(payment_status="PAID")
```

**Correct Logic:**
```python
# Payment status is calculated, not stored
# Paid = amount_paid >= total_incl
# Unpaid = amount_paid < total_incl

# For outstanding amounts:
.filter(
    status__in=["APPROVED", "OVERDUE"],
    amount_paid__lt=F("total_incl")  # Not fully paid
)
```

---

## Remediation Steps (Priority Order)

### Step 1: Fix InvoiceDocument Field Names (High Priority)
**File:** `apps/reporting/services/dashboard_service.py`
**Lines:** 181-240

**Changes:**
1. `subtotal` → `base_subtotal` (for revenue calculations)
2. Remove `payment_status` references
3. Add `amount_paid__lt=F("total_incl")` for unpaid filter

**Tests Fixed:** 8 tests
- `test_calculate_revenue_mtd_with_approved_invoices`
- `test_calculate_revenue_ytd_with_multiple_invoices`
- `test_calculate_revenue_excludes_void_and_draft`
- `test_calculate_outstanding_receivables_with_partial_payments`
- `test_calculate_outstanding_payables_with_multiple_vendors`
- `test_calculate_outstanding_includes_overdue`
- `test_calculate_outstanding_excludes_paid_documents`
- GST threshold tests

---

### Step 2: Fix JournalLine Field Names (High Priority)
**File:** `apps/reporting/services/dashboard_service.py`
**Lines:** 243-275

**Changes:**
1. `journal_entry__status` → `entry__status`
2. `journal_entry__date` → `entry__date`

**Tests Fixed:** 4 tests
- `test_calculate_gst_payable_with_std_rated_sales`
- `test_calculate_gst_payable_with_zero_rated_sales`
- `test_calculate_gst_payable_with_credit_notes`
- `test_calculate_gst_payable_excludes_draft_invoices`

---

### Step 3: Fix BankAccount Cash Calculation (High Priority)
**File:** `apps/reporting/services/dashboard_service.py`
**Lines:** 278-285

**Changes:**
1. Remove `current_balance` reference
2. Use `opening_balance` as base
3. Calculate from transactions (if BankTransaction model available)

**Tests Fixed:** 2 tests
- `test_calculate_cash_on_hand_with_multiple_accounts`
- `test_calculate_cash_on_hand_includes_payments`

---

### Step 4: Fix Compliance Alerts Logic (Medium Priority)
**File:** `apps/reporting/services/dashboard_service.py`
**Lines:** 347-420

**Changes:**
1. Remove `payment_status` references
2. Use `amount_paid__lt=F("total_incl")` for overdue detection

**Tests Fixed:** 4 tests
- `test_generate_filing_deadline_alert`
- `test_generate_overdue_invoice_alerts`
- `test_generate_bank_reconciliation_alert`
- `test_handles_empty_organisation` (format issue)

---

### Step 5: Fix Empty Dashboard Format (Low Priority)
**File:** `apps/reporting/services/dashboard_service.py`
**Lines:** 158-162

**Issue:** Empty dashboard returns `'0.00'` but test expects `'0.0000'`

**Fix:**
```python
# OLD:
"gst_payable": "0.00",

# NEW:
"gst_payable": "0.0000",
```

**Tests Fixed:** 1 test
- `test_handles_empty_organisation`

---

## Implementation Checklist

### Phase 1: Field Name Fixes (Estimated: 1 hour)
- [ ] Fix InvoiceDocument queries (lines 181-240)
- [ ] Fix JournalLine queries (lines 243-275)
- [ ] Fix BankAccount cash calculation (lines 278-285)
- [ ] Run tests to verify fixes

### Phase 2: Logic Fixes (Estimated: 1 hour)
- [ ] Fix payment status calculations
- [ ] Fix compliance alerts logic
- [ ] Fix empty dashboard format
- [ ] Run full test suite

### Phase 3: Verification (Estimated: 30 minutes)
- [ ] All 21 original dashboard tests passing
- [ ] All 15 new cache tests passing
- [ ] Verify caching still works
- [ ] Document changes

---

## Testing Strategy

### Test Command Sequence
```bash
# 1. Test cache functionality (should still pass)
pytest apps/reporting/tests/test_dashboard_cache.py -v --tb=short

# 2. Test dashboard service (should pass after fixes)
pytest apps/reporting/tests/test_dashboard_service_tdd.py -v --tb=short

# 3. Run all reporting tests
pytest apps/reporting/tests/ -v --tb=short

# 4. Full test suite
pytest apps/reporting/tests/test_dashboard_service_tdd.py apps/reporting/tests/test_dashboard_cache.py -v
```

### Expected Results After Remediation
```
============================== 36 passed in X.XXs ==============================
```
- 21 original dashboard tests ✅
- 15 cache tests ✅
- Total: 36 tests passing

---

## Code Changes Required

### File 1: `apps/reporting/services/dashboard_service.py`

#### Change 1.1: Revenue Query (Line ~200)
```python
# BEFORE:
result = (
    InvoiceDocument.objects.filter(...)
    .aggregate(total=Sum("subtotal"))  # ❌ Wrong field
)

# AFTER:
result = (
    InvoiceDocument.objects.filter(...)
    .aggregate(total=Sum("base_subtotal"))  # ✅ Correct field
)
```

#### Change 1.2: Outstanding Receivables (Line ~255)
```python
# BEFORE:
.exclude(payment_status="PAID")  # ❌ Field doesn't exist

# AFTER:
.filter(amount_paid__lt=F("total_incl"))  # ✅ Calculate unpaid
```

#### Change 1.3: JournalLine Query (Line ~265)
```python
# BEFORE:
JournalLine.objects.filter(
    journal_entry__status="POSTED",  # ❌ Wrong field
    journal_entry__date__gte=period_start,  # ❌ Wrong field
)

# AFTER:
JournalLine.objects.filter(
    entry__status="POSTED",  # ✅ Correct field
    entry__date__gte=period_start,  # ✅ Correct field
)
```

#### Change 1.4: Cash Calculation (Line ~285)
```python
# BEFORE:
result = BankAccount.objects.filter(...).aggregate(
    total=Sum("current_balance")  # ❌ Field doesn't exist
)

# AFTER:
# Calculate from opening_balance + transactions
bank_accounts = BankAccount.objects.filter(org_id=org_uuid, is_active=True)
total = Decimal("0.0000")
for account in bank_accounts:
    total += account.opening_balance
# TODO: Add transaction sum when aligned
return money(total)
```

#### Change 1.5: Empty Dashboard Format (Line ~159)
```python
# BEFORE:
"gst_payable": "0.00",  # ❌ Wrong format

# AFTER:
"gst_payable": "0.0000",  # ✅ Matches test expectation
```

---

## Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| More field name mismatches | Medium | Medium | Check all models before fixing |
| Transaction calculation complex | High | Low | Use opening_balance only for now |
| Tests still fail after fixes | Low | High | Verify with single test first |

---

## Success Criteria

- [ ] All 21 original dashboard tests passing
- [ ] All 15 new cache tests passing
- [ ] No regression in other tests
- [ ] Cache functionality verified
- [ ] Code follows existing patterns
- [ ] Documentation updated

---

## Related Documentation

- `apps/core/models/invoice_document.py` - InvoiceDocument model
- `apps/core/models/journal_line.py` - JournalLine model
- `apps/core/models/bank_account.py` - BankAccount model
- `database_schema.sql` - SQL schema (source of truth)
- `apps/reporting/tests/test_dashboard_service_tdd.py` - Original tests
- `apps/reporting/tests/test_dashboard_cache.py` - Cache tests

---

## Notes

1. **SQL-First Design:** The database schema is the source of truth. Django models map to existing tables.
2. **No Migrations:** This is an unmanaged model environment. Schema changes require SQL patches.
3. **Decimal Precision:** All monetary values must use `NUMERIC(10,4)` (4 decimal places).
4. **Cache Impact:** The caching implementation is correct. The failing tests are due to computation logic, not caching.

---

**Estimated Time:** 2-3 hours
**Priority:** High
**Blocker Resolution:** This will unblock all 20 failing dashboard tests
