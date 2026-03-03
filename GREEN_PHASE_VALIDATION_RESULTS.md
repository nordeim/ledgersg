# GREEN Phase Validation Results - Dashboard Service TDD Tests

**Date**: 2026-03-03  
**Phase**: GREEN Phase Validation  
**Status**: 🟡 In Progress - 62% Passing (13/21 tests)

---

## Executive Summary

Successfully initialized test database and executed all 21 TDD tests. Current results show **13 tests passing (62%)** with 6 failures and 2 errors requiring fixes.

---

## Test Results Summary

### ✅ Passing Tests (13/21 - 62%)

| Test | Category | Status |
|------|----------|--------|
| `test_calculate_gst_payable_with_zero_rated_sales` | GST Calculations | ✅ PASS |
| `test_calculate_gst_payable_excludes_draft_invoices` | GST Calculations | ✅ PASS |
| `test_calculate_revenue_mtd_with_approved_invoices` | Revenue Aggregation | ✅ PASS |
| `test_calculate_revenue_ytd_with_multiple_invoices` | Revenue Aggregation | ✅ PASS |
| `test_calculate_revenue_excludes_void_and_draft` | Revenue Aggregation | ✅ PASS |
| `test_calculate_outstanding_receivables_with_partial_payments` | Outstanding Amounts | ✅ PASS |
| `test_calculate_outstanding_payables_with_multiple_vendors` | Outstanding Amounts | ✅ PASS |
| `test_calculate_outstanding_includes_overdue` | Outstanding Amounts | ✅ PASS |
| `test_calculate_outstanding_excludes_paid_documents` | Outstanding Amounts | ✅ PASS |
| `test_generate_filing_deadline_alert` | Compliance Alerts | ✅ PASS |
| `test_generate_overdue_invoice_alerts` | Compliance Alerts | ✅ PASS |
| `test_handles_empty_organisation` | Edge Cases | ✅ PASS |
| `test_handles_closed_fiscal_periods` | Edge Cases | ✅ PASS |

### ❌ Failing Tests (6/21 - 29%)

| Test | Category | Issue | Root Cause |
|------|----------|-------|------------|
| `test_calculate_gst_payable_with_std_rated_sales` | GST Calculations | AssertionError: Expected 900, Got 1800 | GST tax_amount being counted twice (debit + credit lines) |
| `test_calculate_gst_payable_with_credit_notes` | GST Calculations | AssertionError: Expected 720, Got 900 | Credit note not reducing GST payable correctly |
| `test_calculate_gst_threshold_utilization_safe` | GST Threshold | AssertionError: Expected 500000, Got 0 | Date range filtering issue (invoices outside test date range) |
| `test_calculate_gst_threshold_utilization_warning` | GST Threshold | AssertionError: Expected WARNING, Got SAFE | Same as above |
| `test_calculate_gst_threshold_utilization_critical` | GST Threshold | AssertionError: Expected CRITICAL, Got SAFE | Same as above |

### ⚠️ Error Tests (2/21 - 9%)

| Test | Category | Issue | Root Cause |
|------|----------|-------|------------|
| `test_calculate_cash_on_hand_with_multiple_accounts` | Cash Position | IntegrityError: bank_account_paynow_type_check | PayNow type constraint violation |
| `test_calculate_cash_on_hand_includes_payments` | Cash Position | IntegrityError: bank_account_paynow_type_check | Same as above |
| `test_generate_bank_reconciliation_alert` | Compliance Alerts | IntegrityError: bank_account_paynow_type_check | Same as above |

---

## Issues Identified

### Issue 1: BankAccount PayNow Type Constraint

**Error**: `new row for relation "bank_account" violates check constraint "bank_account_paynow_type_check"`

**Root Cause**: BankAccount fixture missing required fields for PayNow constraint.

**Solution**: The SQL constraint `bank_account_paynow_type_check` requires:
- If `paynow_type` is set, `paynow_id` must also be set
- `paynow_type` must be one of: 'UEN', 'MOBILE', 'NRIC'

**Fix Required**: Update BankAccount fixtures to include PayNow fields or leave both NULL:

```python
# Option 1: Set PayNow fields
BankAccount.objects.create(
    ...
    paynow_type="UEN",
    paynow_id="202400001A",
)

# Option 2: Leave both NULL (already done in fixture)
# But the constraint might be checking for NOT NULL when paynow_type is not set
```

**Action**: Check constraint definition and update fixtures accordingly.

---

### Issue 2: GST Calculation Double Counting

**Error**: `AssertionError: Expected Decimal('900.0000'), Got Decimal('1800.0000')`

**Root Cause**: The `calculate_gst_liability()` method is counting GST from both debit and credit journal lines, resulting in double the expected value.

**Analysis**:
- Test creates 1 journal entry with 3 lines
- Line 1: AR debit with tax_amount=900
- Line 3: GST credit with tax_amount=900
- Service queries all lines with `tax_amount__gt=0`
- Result: 900 + 900 = 1800

**Solution**: Only count tax_amount on lines where the tax_code is output tax, not on all lines with tax_amount. The debit line has the tax, the credit line is the tax account itself.

**Fix Required**:
```python
# Current logic (incorrect):
output_tax_result = JournalLine.objects.filter(
    tax_code__is_output=True,
    tax_amount__gt=0,
).aggregate(total=Sum("tax_amount"))

# Correct logic:
# Only count tax on debit lines for output tax
# Or use tax_code links to differentiate
```

**Action**: Review journal entry structure and fix query logic.

---

### Issue 3: GST Threshold Date Range Filtering

**Error**: `AssertionError: Expected Decimal('500000.0000'), Got Decimal('0.0000')`

**Root Cause**: Test creates invoices with `issue_date` in the past (using `timedelta(days=i * 30)`), but the current date might be outside the 12-month rolling window.

**Analysis**:
- Test: `issue_date=date(2024, 1, 1) - timedelta(days=i * 30)`
- If today is 2026-03-03, invoices from 2024 are > 12 months old
- Query: `issue_date__gte=twelve_months_ago` excludes all test invoices

**Solution**: Use relative dates in tests based on `date.today()` instead of hardcoded dates.

**Fix Required**:
```python
# Current test (incorrect for 2026):
issue_date=date(2024, 1, 1) - timedelta(days=i * 30)

# Correct approach:
today = date.today()
issue_date=today - timedelta(days=i * 30)
```

**Action**: Update GST threshold test fixtures to use relative dates.

---

## Recommended Fixes

### Priority 1: BankAccount PayNow Constraint (HIGH)

1. Check SQL constraint definition
2. Update test fixtures to satisfy constraint
3. Re-run affected tests

### Priority 2: GST Calculation Logic (HIGH)

1. Review journal entry structure in tests
2. Update `calculate_gst_liability()` query logic
3. Ensure only actual GST output is counted

### Priority 3: GST Threshold Date Filtering (MEDIUM)

1. Update test fixtures to use `date.today()` - timedelta
2. Ensure invoices fall within 12-month rolling window
3. Re-run threshold tests

---

## Next Steps

1. **Fix BankAccount fixtures** (15 min)
   - Update PayNow fields or verify constraint
   - Re-run Cash Position tests

2. **Fix GST calculation logic** (30 min)
   - Analyze journal entry structure
   - Update query to count correctly
   - Re-run GST tests

3. **Fix GST threshold dates** (20 min)
   - Update fixtures to use relative dates
   - Re-run threshold tests

4. **Run full test suite** (5 min)
   - Verify all 21 tests pass
   - Document final results

**Estimated Time to 100% Passing**: 1.5 hours

---

## Test Progress

- [x] Test database initialized
- [x] 13/21 tests passing (62%)
- [ ] Fix BankAccount constraint errors (2 tests)
- [ ] Fix GST calculation logic (2 tests)
- [ ] Fix GST threshold dates (3 tests)
- [ ] All 21 tests passing (100%)

**Current Status**: 🟡 GREEN Phase Validation In Progress
