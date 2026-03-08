# TDD Sub-Plan: View Layer UUID Conversion Fix

**Date:** 2026-03-08
**Status:** VALIDATED - Ready for Execution
**Approach:** Test-Driven Development (RED → GREEN)

---

## Root Cause Analysis

### Problem
All three endpoints return 500 Internal Server Error with message:
```
'UUID' object has no attribute 'replace'
```

### Root Cause
**URL Configuration:** `config/urls.py:151`
```python
path("api/v1/<uuid:org_id>/", include(org_scoped_urlpatterns))
```

The `<uuid:org_id>` path converter **automatically converts** the URL parameter to a `UUID` object.

**View Code Problem:**
All views try to convert `org_id` to UUID again:
```python
# banking/views.py:60
org_id=UUID(org_id),  # ❌ ERROR: org_id is already a UUID!

# gst/views.py (13 occurrences)
org_id=UUID(org_id),

# journal/views.py (7 occurrences)
org_id=UUID(org_id),
```

### Why This Fails
When Django receives a request like `/api/v1/65abbcd6-6129-41ef-82ed-9e84a3442c7f/banking/bank-accounts/`:
1. The URL router extracts `65abbcd6-...` and converts it to a `UUID` object
2. The view receives `org_id` as a `UUID` object (NOT a string)
3. The view calls `UUID(org_id)` expecting a string
4. `UUID()` constructor calls `hex.replace()` on the UUID object
5. **Error:** `'UUID' object has no attribute 'replace'`

---

## Affected Files

| File | Pattern | Count |
|------|---------|-------|
| `apps/banking/views.py` | `UUID(org_id)` | Multiple |
| `apps/gst/views.py` | `UUID(org_id)` | 13 occurrences |
| `apps/journal/views.py` | `UUID(org_id)` | 7 occurrences |

---

## Solution

### Option A: Cast to UUID safely (Recommended)
Handle both string and UUID inputs:
```python
from uuid import UUID

def ensure_uuid(value):
    """Convert value to UUID, handling both strings and UUID objects."""
    if isinstance(value, UUID):
        return value
    return UUID(value)

# Usage:
org_id = ensure_uuid(org_id)
```

### Option B: Just remove UUID() calls (Simpler)
Since Django already converts to UUID:
```python
# BEFORE:
accounts = BankAccountService.list(org_id=UUID(org_id), ...)

# AFTER:
accounts = BankAccountService.list(org_id=org_id, ...)
```

**Recommendation:** Option B is cleaner and safer because:
1. Django guarantees `org_id` is already a UUID
2. No need for additional conversion
3. Cleaner code

---

## TDD Execution Plan

### Phase 1: Fix Banking Views

**Files to modify:**
- `apps/banking/views.py`

**Changes:**
Replace all `UUID(org_id)` with just `org_id` (or `ensure_uuid(org_id)` if needed)

**Test:**
```bash
pytest tests/middleware/test_rls_context.py::TestBankingEndpointsWithRLS::test_bank_account_list_returns_200 -v --reuse-db --no-migrations
```

### Phase 2: Fix GST Views

**Files to modify:**
- `apps/gst/views.py`

**Changes:**
Replace all 13 occurrences of `UUID(org_id)` with `org_id`

**Test:**
```bash
pytest tests/middleware/test_rls_context.py::TestBankingEndpointsWithRLS::test_tax_code_list_returns_200 -v --reuse-db --no-migrations
```

### Phase 3: Fix Journal Views

**Files to modify:**
- `apps/journal/views.py`

**Changes:**
Replace all 7 occurrences of `UUID(org_id)` with `org_id`

**Test:**
```bash
pytest tests/middleware/test_rls_context.py::TestJournalEndpointsWithRLS::test_journal_entries_list_returns_200 -v --reuse-db --no-migrations
```

---

## Execution Checklist

### Pre-Execution
- [x] Root cause validated
- [x] Affected files identified
- [x] Test environment ready

### Phase 1: Banking Views
- [ ] Replace `UUID(org_id)` with `org_id` in `banking/views.py`
- [ ] Run test: `test_bank_account_list_returns_200`
- [ ] Verify test passes

### Phase 2: GST Views
- [ ] Replace all `UUID(org_id)` with `org_id` in `gst/views.py`
- [ ] Run test: `test_tax_code_list_returns_200`
- [ ] Verify test passes

### Phase 3: Journal Views
- [ ] Replace all `UUID(org_id)` with `org_id` in `journal/views.py`
- [ ] Run test: `test_journal_entries_list_returns_200`
- [ ] Verify test passes

### Post-Execution
- [ ] Run all tests: `pytest tests/middleware/test_rls_context.py -v --reuse-db --no-migrations`
- [ ] Verify 6/6 tests passing

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Service expects UUID string | Low | Medium | Services receive UUID objects (same type) |
| Other views not affected | Low | Low | Test suite covers affected endpoints |
| Regression in other modules | Low | Medium | Run full test suite after changes |

---

## Success Criteria

- All 6 tests in `test_rls_context.py` passing
- No regressions in other test suites
- Clean code without redundant UUID conversions

---

**Status:** PLAN VALIDATED - Ready for Execution
