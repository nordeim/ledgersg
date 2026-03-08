# TDD Next Steps Subplan

## Goal

Execute recommended next steps after RLS fix: validate codebase, fix UUID issues, run full test suite, and document patterns.

## Validation Summary

### Issue 1: UUID Double Conversion in coa/views.py

**Status**: ✅ CONFIRMED - 7 occurrences found

**File**: `/home/project/Ledger-SG/apps/backend/apps/coa/views.py`

| Line | Current Code | Issue |
|------|--------------|-------|
| 128 | `UUID(org_id)` | Parameter already UUID from URL converter |
| 143 | `org_id=UUID(org_id)` | Parameter already UUID from URL converter |
| 157 | `UUID(org_id)` | Parameter already UUID from URL converter |
| 186 | `UUID(org_id)` | Parameter already UUID from URL converter |
| 187 | `UUID(org_id)` | Parameter already UUID from URL converter |
| 212 | `UUID(org_id)` | Parameter already UUID from URL converter |
| 267 | `UUID(org_id)` | Parameter already UUID from URL converter |

**URL Pattern**: `path("api/v1/<uuid:org_id>/", ...)` in config/urls.py

**Django Behavior**: The `<uuid:org_id>` path converter automatically converts URL parameters to `uuid.UUID` objects BEFORE they reach the view.

**Fix Strategy**: Remove all `UUID(org_id)` calls in coa/views.py. The parameter is already a UUID.

### Issue 2: Test Failure in test_auth_api.py

**Status**: ✅ CONFIRMED - Response structure mismatch

**Test**: `test_register_user_success` line 27

**Problem**: Test expects `response.data["email"]` but view returns nested structure:
```python
return Response({
    "user": UserProfileSerializer(user).data,  # Contains email
    "tokens": tokens,
})
```

**Expected**: `response.data["user"]["email"]`

### Issue 3: Other View Modules Check

**Status**: PENDING - Need to verify other modules

Modules to check:
- [ ] apps/invoicing/views.py
- [ ] apps/banking/views.py (already fixed)
- [ ] apps/gst/views.py (already fixed)
- [ ] apps/journal/views.py (already fixed)
- [ ] apps/reporting/views.py
- [ ] apps/peppol/views.py

## Execution Plan

### Phase 1: Fix Test Failure (Immediate)

**Task 1.1**: Update test_auth_api.py to use correct response structure
- File: `tests/integration/test_auth_api.py`
- Lines: 27-30
- Change: `response.data["email"]` → `response.data["user"]["email"]`

**Verification**: Run test_register_user_success

### Phase 2: Fix UUID Issues in coa/views.py

**Task 2.1**: Fix AccountDetailView.get (line 128)
- Remove: `UUID(org_id)`
- Keep: `org_id` (already UUID)

**Task 2.2**: Fix AccountDetailView.patch (lines 143-144)
- Remove: `UUID(org_id)` and `UUID(account_id)`
- Keep: `org_id` and `account_id` (already UUIDs)

**Task 2.3**: Fix AccountDetailView.delete (line 157)
- Remove: `UUID(org_id)` and `UUID(account_id)`
- Keep: `org_id` and `account_id` (already UUIDs)

**Task 2.4**: Fix AccountBalanceView.get (lines 186-187)
- Remove: `UUID(org_id)` and `UUID(account_id)`
- Keep: `org_id` and `account_id` (already UUIDs)

**Task 2.5**: Fix AccountHierarchyView.get (line 212)
- Remove: `UUID(org_id)`
- Keep: `org_id` (already UUID)

**Task 2.6**: Fix TrialBalanceView.get (lines 264, 267)
- Keep: `UUID(fiscal_year_id)` (comes from query_params, not URL)
- Remove: `UUID(org_id)` at line 267
- Keep: `org_id` (already UUID)

**Verification**: Run coa tests

### Phase 3: Check Other View Modules

**Task 3.1**: Scan invoicing/views.py for UUID(org_id)
**Task 3.2**: Scan reporting/views.py for UUID(org_id)
**Task 3.3**: Scan peppol/views.py for UUID(org_id)
**Task 3.4**: Document findings

### Phase 4: Run Full Test Suite

**Task 4.1**: Run all tests with coverage
- Command: `pytest --reuse-db --no-migrations -v`
- Expected: All tests pass

**Task 4.2**: Document any new failures

### Phase 5: Create UUID Handling Documentation

**Task 5.1**: Create UUID_PATTERNS_GUIDE.md
- Django URL converter behavior
- When to use UUID() vs when not to
- Examples of correct/incorrect usage
- Checklist for developers

**Task 5.2**: Update API_CLI_Usage_Guide.md troubleshooting section
- Add UUID issue documentation
- Link to UUID_PATTERNS_GUIDE.md

## Success Criteria

- [ ] Test `test_register_user_success` passes
- [ ] All 7 UUID issues in coa/views.py fixed
- [ ] No other view modules have UUID(org_id) issues
- [ ] Full test suite passes (346 tests)
- [ ] UUID documentation created

## Risks and Considerations

1. **Service Layer Compatibility**: The service methods expect `UUID` type. Since `org_id` is already a UUID from the URL converter, passing it directly is correct.

2. **Type Annotations**: The view method signatures show `org_id: str`, but Django actually passes a `UUID` object. This is a type annotation inconsistency but doesn't affect runtime.

3. **Query Parameters**: UUIDs from query parameters (e.g., `request.query_params.get("fiscal_year_id")`) ARE strings and DO need conversion.

## TDD Approach

For each fix:
1. **RED**: Run test to confirm failure
2. **GREEN**: Apply fix
3. **REFACTOR**: Verify fix works, clean up if needed

## Files to Modify

| File | Changes |
|------|---------|
| `tests/integration/test_auth_api.py` | Fix response data access |
| `apps/coa/views.py` | Remove 7 UUID(org_id) calls |
| `UUID_PATTERNS_GUIDE.md` | Create new documentation |
| `API_CLI_Usage_Guide.md` | Update troubleshooting |

## Test Commands

```bash
# Test specific file
cd apps/backend
source /opt/venv/bin/activate
pytest tests/integration/test_auth_api.py -v --reuse-db --no-migrations

# Test coa module
pytest apps/coa/tests/ -v --reuse-db --no-migrations

# Full test suite
pytest --reuse-db --no-migrations -v
```

---

*Plan created: 2026-03-08*
*Validated against: actual codebase*
*Status: Ready for execution*
