# TDD Sub-Plan: RLS Issues Remediation

**Date:** 2026-03-08
**Status:** VALIDATED - Ready for Execution
**Approach:** Test-Driven Development (RED → GREEN)

---

## Validation Summary (Completed)

All three root causes have been validated against the actual codebase:

| Issue | Validation Result | Evidence |
|-------|-------------------|----------|
| SQL NULL Syntax | ✅ CONFIRMED BUG | PostgreSQL error: `syntax error at or near "NULL"` |
| Test Assertion | ✅ CONFIRMED BUG | Found 3 occurrences of `response.data` (non-existent attribute) |
| Missing Org Membership | ✅ CONFIRMED BUG | Test creates user but not `UserOrganisation` |

---

## Root Cause Analysis

### Issue 1: SQL NULL Syntax Error

**Location:** `apps/backend/common/middleware/tenant_context.py` lines 80-81

**Current Code (WRONG):**
```python
cursor.execute("SET LOCAL app.current_org_id = NULL")
cursor.execute("SET LOCAL app.current_user_id = NULL")
```

**Error:**
```
ERROR: syntax error at or near "NULL"
LINE 1: SET LOCAL app.current_org_id = NULL
```

**Root Cause:** PostgreSQL `SET LOCAL` for custom configuration parameters requires a string value, not SQL NULL. The correct syntax is to use an empty string `''`.

**Fixed Code:**
```python
cursor.execute("SET LOCAL app.current_org_id = ''")
cursor.execute("SET LOCAL app.current_user_id = ''")
```

---

### Issue 2: Test Assertion Bug

**Location:** `apps/backend/tests/middleware/test_rls_context.py` lines 128, 151, 181

**Current Code (WRONG):**
```python
assert response.status_code == 200, (
    f"Expected 200, got {response.status_code}: {response.data}"
)
```

**Error:**
```
AttributeError: 'JsonResponse' object has no attribute 'data'
```

**Root Cause:** `JsonResponse` objects have `.content` (bytes) attribute, not `.data`. The response body must be parsed as JSON.

**Fixed Code:**
```python
import json

content = json.loads(response.content)
assert response.status_code == 200, (
    f"Expected 200, got {response.status_code}: {content}"
)
```

---

### Issue 3: Missing Org Membership in Tests

**Location:** `apps/backend/tests/middleware/test_rls_context.py` lines 57-65

**Current Code (INCOMPLETE):**
```python
user = User.objects.create_user(email="test_rls@example.com", password="testpass123")
# Create org and membership would go here
# For now, just test that user auth works
```

**Error:**
```
WARNING: User 55e5ecff-... not authorized for org 65abbcd6-...
```

**Root Cause:** The `TenantContextMiddleware._verify_org_membership()` method checks `UserOrganisation` table for membership with `accepted_at__isnull=False`. Tests must create:
1. An `Organisation`
2. A `Role`
3. A `UserOrganisation` with `accepted_at` set

**Fixed Code:**
```python
from apps.core.models import Organisation, UserOrganisation, Role
from django.utils import timezone

user = User.objects.create_user(email="test_rls@example.com", password="testpass123")

# Create test organisation
org = Organisation.objects.create(
    name="Test Organisation",
    base_currency="SGD",
    gst_registered=False
)

# Create OWNER role (required for org access)
role = Role.objects.create(
    org=org,
    name="OWNER",
    can_manage_org=True,
    can_manage_users=True,
    can_manage_coa=True,
    can_create_invoices=True,
    can_approve_invoices=True,
    can_void_invoices=True,
    can_create_journals=True,
    can_manage_banking=True,
    can_file_gst=True,
    can_view_reports=True,
    can_export_data=True,
)

# Create user-org membership (REQUIRED for RLS)
UserOrganisation.objects.create(
    user=user,
    org=org,
    role=role,
    accepted_at=timezone.now()  # REQUIRED - must be accepted
)

# Update request URL to use actual org.id
request = factory.get(f"/api/v1/{org.id}/banking/bank-accounts/")
```

---

## TDD Execution Plan

### Phase 1: Fix SQL NULL Syntax

**Step 1.1:** Edit middleware file
**File:** `apps/backend/common/middleware/tenant_context.py`
**Lines:** 80-81

**Change:**
```python
# BEFORE:
cursor.execute("SET LOCAL app.current_org_id = NULL")
cursor.execute("SET LOCAL app.current_user_id = NULL")

# AFTER:
cursor.execute("SET LOCAL app.current_org_id = ''")
cursor.execute("SET LOCAL app.current_user_id = ''")
```

**Step 1.2:** Run test to verify
```bash
cd /home/project/Ledger-SG/apps/backend
source /opt/venv/bin/activate
pytest tests/middleware/test_rls_context.py::TestRLSContextMiddleware::test_rls_context_not_set_when_user_unauthenticated -v --reuse-db --no-migrations
```

**Expected Result:** Test should pass (no more SQL syntax error)

---

### Phase 2: Fix Test Assertions

**Step 2.1:** Add json import
**File:** `apps/backend/tests/middleware/test_rls_context.py`
**Line:** Add to imports at top

```python
import json
```

**Step 2.2:** Fix assertions (3 locations)

**Line 128:**
```python
# BEFORE:
f"Expected 200, got {response.status_code}: {response.data}"

# AFTER:
f"Expected 200, got {response.status_code}: {json.loads(response.content)}"
```

**Line 151:** Same fix
**Line 181:** Same fix

---

### Phase 3: Fix Org Membership in Tests

**Step 3.1:** Add imports
**File:** `apps/backend/tests/middleware/test_rls_context.py`
**Lines:** Add to imports

```python
from apps.core.models import Organisation, UserOrganisation, Role
from django.utils import timezone
```

**Step 3.2:** Update `test_rls_context_set_when_user_authenticated`

**Replace lines 57-78:**
```python
# Create test user and org
user = User.objects.create_user(email="test_rls@example.com", password="testpass123")

# Create test organisation
org = Organisation.objects.create(
    name="Test Organisation",
    base_currency="SGD",
    gst_registered=False
)

# Create OWNER role
role = Role.objects.create(
    org=org,
    name="OWNER",
    can_manage_org=True,
    can_manage_users=True,
    can_manage_coa=True,
    can_create_invoices=True,
    can_approve_invoices=True,
    can_void_invoices=True,
    can_create_journals=True,
    can_manage_banking=True,
    can_file_gst=True,
    can_view_reports=True,
    can_export_data=True,
)

# Create user-org membership (REQUIRED for RLS)
UserOrganisation.objects.create(
    user=user,
    org=org,
    role=role,
    accepted_at=timezone.now()
)

factory = RequestFactory()
request = factory.get(f"/api/v1/{org.id}/banking/bank-accounts/")
request.user = user

# Execute middleware
mw = TenantContextMiddleware(lambda r: HttpResponse())
response = mw(request)

# Check RLS context is set
with connection.cursor() as cursor:
    cursor.execute("SELECT current_setting('app.current_org_id', true)")
    result = cursor.fetchone()[0]

assert result is not None and result != "", f"RLS context not set, got: {result}"
assert result == str(org.id), f"Expected org_id {org.id}, got: {result}"
```

**Step 3.3:** Update `test_bank_account_list_returns_200`, `test_tax_code_list_returns_200`, `test_journal_entries_list_returns_200`

Each test needs:
1. Create organisation
2. Create role
3. Create user-org membership
4. Use org.id in URL

---

## Success Criteria

| Criteria | Expected Result |
|----------|-----------------|
| SQL syntax fix | No more `syntax error at or near "NULL"` |
| Assertion fix | No more `AttributeError: 'JsonResponse' object has no attribute 'data'` |
| Org membership fix | No more `User X not authorized for org Y` |
| All tests pass | 6/6 tests passing |

---

## Test Commands

```bash
# Run all RLS context tests
cd /home/project/Ledger-SG/apps/backend
source /opt/venv/bin/activate
pytest tests/middleware/test_rls_context.py -v --reuse-db --no-migrations

# Run specific test
pytest tests/middleware/test_rls_context.py::TestRLSContextMiddleware::test_rls_context_set_when_user_authenticated -v --reuse-db --no-migrations
```

---

## Files to Modify

| File | Lines | Change |
|------|-------|--------|
| `common/middleware/tenant_context.py` | 80-81 | Change `NULL` to `''` |
| `tests/middleware/test_rls_context.py` | 8 | Add `import json` |
| `tests/middleware/test_rls_context.py` | 9 | Add `from apps.core.models import Organisation, UserOrganisation, Role` |
| `tests/middleware/test_rls_context.py` | 10 | Add `from django.utils import timezone` |
| `tests/middleware/test_rls_context.py` | 57-78 | Replace with complete test setup |
| `tests/middleware/test_rls_context.py` | 105-129 | Update test with org setup |
| `tests/middleware/test_rls_context.py` | 131-152 | Update test with org setup |
| `tests/middleware/test_rls_context.py` | 155-181 | Update test with org setup |

---

## Validation Checklist (Pre-Execution)

- [x] SQL NULL syntax confirmed via PostgreSQL test
- [x] JsonResponse attribute confirmed via code analysis
- [x] Missing org membership confirmed via test logs
- [x] Role model structure verified
- [x] Organisation model structure verified
- [x] UserOrganisation model structure verified
- [x] All imports identified
- [x] All line numbers identified

---

**Status:** PLAN VALIDATED - Ready for Meticulous Execution
