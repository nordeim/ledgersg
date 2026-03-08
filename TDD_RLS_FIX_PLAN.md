# TDD Plan for RLS Context Fix

## Root Cause Validated ✅

**Issue:** TenantContextMiddleware returns early when user is not authenticated (line 69-70), skipping RLS context setup.

**Code Path:**
```python
# Line 66-70 in tenant_context.py
user = self._get_authenticated_user(request)
if not user or not user.is_authenticated:
    return self.get_response(request)  # <-- RLS never set!
```

**Impact:** API endpoints using RLS-protected tables (banking, journal, gst) fail because PostgreSQL RLS policies require `app.current_org_id` to be set.

---

## TDD Approach

### Phase 1: Write Failing Tests (RED)

#### Test 1: RLS Context Should Be Set for Authenticated Requests
```python
def test_rls_context_set_for_authenticated_org_scoped_request():
    """
    GIVEN: Authenticated user accessing org-scoped endpoint
    WHEN: TenantContextMiddleware processes the request
    THEN: RLS context variables should be set in PostgreSQL session
    """
    # Setup: Create authenticated request
    # Execute: Call middleware
    # Assert: RLS context is set
```

#### Test 2: Middleware Should Extract User from JWT Token
```python
def test_middleware_extracts_user_from_jwt_token():
    """
    GIVEN: Request with valid JWT token in Authorization header
    WHEN: _get_authenticated_user is called
    THEN: Should return the user instance
    """
```

#### Test 3: Bank Account List Should Work with RLS
```python
def test_bank_account_list_with_rls():
    """
    GIVEN: User belongs to org and has valid token
    WHEN: GET /api/v1/{org_id}/banking/bank-accounts/
    THEN: Should return list (not internal error)
    """
```

### Phase 2: Implement Fixes (GREEN)

#### Fix 1: Ensure RLS Context Always Set for Org-Scoped URLs
**File:** `common/middleware/tenant_context.py`

**Current (Bug):**
```python
if not user or not user.is_authenticated:
    return self.get_response(request)  # RLS not set!
```

**Fixed:**
```python
if not user or not user.is_authenticated:
    # Still need to set RLS for public endpoints that query org data
    # Or: Set RLS to NULL to enforce policy denial
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL app.current_org_id = NULL")
    return self.get_response(request)
```

#### Fix 2: Fix JWT Token Extraction in Middleware
**Issue:** The JWT token extraction might be failing silently.

**Current Code (line 199-210):**
```python
try:
    from rest_framework_simplejwt.tokens import AccessToken
    access_token = AccessToken(token)
    user_id = access_token['user_id']
    return User.objects.get(id=user_id)
except Exception:
    # Invalid token - let the view handle it
    pass
```

**Problem:** Exception is silently caught, user is None.

**Solution:** Add proper error handling and logging.

#### Fix 3: Add Debug Logging to Middleware
**Purpose:** Enable debugging of authentication flow.

### Phase 3: Refactor and Improve (REFACTOR)

- Extract JWT authentication to separate service
- Add comprehensive logging
- Improve error messages
- Add caching for membership checks

---

## Implementation Checklist

### Test Files to Create
- [ ] `tests/middleware/test_tenant_context_rls.py`
- [ ] `tests/views/test_banking_rls.py`
- [ ] `tests/views/test_journal_rls.py`
- [ ] `tests/views/test_gst_rls.py`

### Fixes to Implement
- [ ] Fix 1: Always set RLS context (even if user is None)
- [ ] Fix 2: Add debug logging to middleware
- [ ] Fix 3: Verify JWT token extraction works
- [ ] Fix 4: Add proper error handling in views

### Validation Tests
- [ ] Run all new tests (should fail initially - RED)
- [ ] Implement fixes
- [ ] Run all tests (should pass - GREEN)
- [ ] Run existing test suite (should still pass)
- [ ] End-to-end API test

---

## Test Implementation Details

### Test: RLS Context Set for Authenticated Requests

```python
@pytest.mark.django_db
def test_rls_context_set_with_authenticated_user():
    # Create user and org
    user = User.objects.create_user(email='test@example.com', password='test123')
    org = Organisation.objects.create(name='Test Org', base_currency='SGD')
    
    # Link user to org
    UserOrganisation.objects.create(user=user, organisation=org, role='OWNER')
    
    # Create request
    factory = RequestFactory()
    request = factory.get(f'/api/v1/{org.id}/banking/bank-accounts/')
    request.user = user
    
    # Execute middleware
    from common.middleware.tenant_context import TenantContextMiddleware
    mw = TenantContextMiddleware(lambda r: HttpResponse())
    response = mw(request)
    
    # Verify RLS context set
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('app.current_org_id', true)")
        result = cursor.fetchone()[0]
        assert result == str(org.id), f"Expected {org.id}, got {result}"
```

### Test: Bank Account Endpoint Works

```python
@pytest.mark.django_db
def test_bank_account_list_endpoint_with_auth():
    # Setup: Create user, org, membership, token
    # Execute: Make authenticated request
    # Assert: 200 OK, returns data
    pass
```

---

## Execution Order

1. **Write Test 1** (RLS context test) → Run → Should FAIL (RED)
2. **Implement Fix 1** (always set RLS) → Run Test 1 → Should PASS (GREEN)
3. **Write Test 2** (JWT extraction) → Run → Should FAIL (RED)
4. **Implement Fix 2** (JWT logging) → Run Test 2 → Should PASS (GREEN)
5. **Write Test 3** (Bank account endpoint) → Run → Should FAIL (RED)
6. **Implement Fix 3** (view error handling) → Run Test 3 → Should PASS (GREEN)
7. **Run Full Test Suite** → Should ALL PASS
8. **End-to-End Test** → Verify with curl

---

## Expected Results

### Before Fix
```bash
curl /api/v1/{org_id}/banking/bank-accounts/
→ {"error": {"code": "internal_error", "message": "An internal error occurred"}}
```

### After Fix
```bash
curl /api/v1/{org_id}/banking/bank-accounts/ -H "Authorization: Bearer {token}"
→ {"data": [], "count": 0}  # or actual bank accounts
```

---

## Success Criteria

- [ ] All new TDD tests pass
- [ ] Existing test suite passes (no regressions)
- [ ] End-to-end API calls work:
  - [ ] `GET /banking/bank-accounts/` → 200 OK
  - [ ] `GET /journal-entries/entries/` → 200 OK
  - [ ] `GET /gst/tax-codes/` → 200 OK
- [ ] RLS context properly set in PostgreSQL session
- [ ] No internal server errors

---

**Ready to Execute:** Yes - Plan validated against codebase
