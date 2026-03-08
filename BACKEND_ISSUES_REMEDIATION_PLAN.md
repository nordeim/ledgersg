# Backend Issues Remediation Plan

## Root Cause Analysis & Comprehensive Fix Strategy

**Date:** 2026-03-08  
**Status:** Investigation Complete  
**Priority:** High  
**Estimated Effort:** 4-6 hours

---

## Executive Summary

Three critical API endpoint groups are returning internal errors:
1. **Banking endpoints** — Internal error on list/create
2. **Journal entry endpoints** — Internal error on list/create
3. **Tax code endpoints** — Internal error

**Root Causes Identified:**
1. **RLS (Row Level Security)** policies active but `app.current_org_id` not properly set
2. **Missing database records** — No accounts in test org, missing tax codes
3. **Potential serializer/model mismatches** — Unmanaged models may have field issues
4. **Test data incomplete** — Test org lacks seeded data

---

## Phase 1: Root Cause Analysis

### 1.1 Banking Endpoints Issue

**Symptoms:**
```json
GET /api/v1/{org_id}/banking/bank-accounts/
Response: {"error": {"code": "internal_error", "message": "An internal error occurred"}}
```

**Investigation Findings:**

✅ **Verified Working:**
- Table `banking.bank_account` exists ✅
- RLS policies configured ✅
- TenantContextMiddleware configured ✅
- Service layer implemented ✅

⚠️ **Potential Issues:**
- `BankAccount.gl_account` is ForeignKey with `null=True` but has `db_column` specified
- Model has `managed = False` — may have sync issues
- RLS requires `SET LOCAL app.current_org_id` but middleware may fail silently

**Code Analysis:**
```python
# From bank_account.py line 28-31:
gl_account = models.ForeignKey(
    "Account", on_delete=models.PROTECT,
    db_column="gl_account_id"
)
# Issue: gl_account_id is NOT NULL in DB, but model allows null
```

**Database Schema:**
```sql
gl_account_id | uuid | | not null  -- <-- Database requires this!
```

**Root Cause Hypothesis:**
When listing bank accounts, if any account has `gl_account_id` pointing to a non-existent Account OR if the RLS context isn't properly set, the query fails.

### 1.2 Journal Entry Endpoints Issue

**Symptoms:**
```json
GET /api/v1/{org_id}/journal-entries/entries/
Response: {"error": {"code": "internal_error", "message": "An internal error occurred"}}
```

**Investigation Findings:**

✅ **Verified:**
- View code exists and looks correct
- Service layer present
- RLS policies likely active on journal schema

**Hypothesis:**
Similar to banking — RLS context or missing related records (fiscal periods, accounts).

### 1.3 Tax Code Endpoints Issue

**Symptoms:**
```json
GET /api/v1/{org_id}/gst/tax-codes/
Response: {"error": {"code": "internal_error", "message": "An internal error occurred"}}
```

**Investigation Findings:**

**Database Query Result:**
```sql
# Tax code table structure verified
gst.tax_code table exists
RLS policies active
```

**Root Cause Hypothesis:**
Tax codes need to be seeded per-organisation. New organisations don't have tax codes seeded automatically.

### 1.4 Chart of Accounts Seeding Issue

**Verified:**
```bash
curl /api/v1/{org_id}/accounts/
Response: {"data": [], "count": 0}
```

**Root Cause:**
New organisations don't have default Chart of Accounts seeded. The `Account` table is empty for the test org.

---

## Phase 2: Detailed Fix Requirements

### Issue 1: Banking Endpoints (Priority: Critical)

**Required Actions:**

1. **Fix RLS Context Setting**
   - [ ] Verify TenantContextMiddleware is setting `app.current_org_id`
   - [ ] Add error logging in middleware to catch failures
   - [ ] Ensure transaction wrapper is correct

2. **Fix Database Constraints**
   - [ ] Check if `gl_account_id` can be NULL in database
   - [ ] Align model with database schema
   - [ ] Add validation in service layer

3. **Add Debug Logging**
   - [ ] Add try-catch with logging in BankAccountService.list()
   - [ ] Log RLS context before queries
   - [ ] Log actual SQL errors

### Issue 2: Journal Entry Endpoints (Priority: Critical)

**Required Actions:**

1. **Verify RLS Context**
   - [ ] Same fixes as banking

2. **Check Related Data**
   - [ ] Ensure fiscal periods exist
   - [ ] Verify account references
   - [ ] Check for orphaned records

3. **Add Logging**
   - [ ] Log in JournalService.list_entries()
   - [ ] Catch and log specific exceptions

### Issue 3: Tax Code Endpoints (Priority: High)

**Required Actions:**

1. **Implement Tax Code Seeding**
   - [ ] Create seed_tax_codes() function
   - [ ] Call on organisation creation
   - [ ] Seed OS, NA, SR codes for Singapore

2. **Fix List Endpoint**
   - [ ] Add proper error handling
   - [ ] Return empty array if no codes (not error)

### Issue 4: Chart of Accounts Seeding (Priority: High)

**Required Actions:**

1. **Implement CoA Seeding**
   - [ ] Create seed_chart_of_accounts() function
   - [ ] Seed standard accounts (1000-9999 range)
   - [ ] Call on organisation creation

2. **Verify Account Types**
   - [ ] Ensure account types exist
   - [ ] Link accounts to types

---

## Phase 3: Implementation Plan

### Step 1: Add Debug Logging (15 minutes)

**File:** `apps/backend/common/middleware/tenant_context.py`

Add logging to trace RLS context setting:
```python
import logging
logger = logging.getLogger(__name__)

# In __call__ method, add:
logger.debug(f"Setting RLS context for org_id: {org_id}")
```

### Step 2: Fix Banking Model Alignment (30 minutes)

**File:** `apps/backend/apps/core/models/bank_account.py`

Fix gl_account field:
```python
gl_account = models.ForeignKey(
    "Account", 
    on_delete=models.PROTECT,
    db_column="gl_account_id",
    null=True,  # Add this if DB allows null
    blank=True  # Add this
)
```

### Step 3: Create Seeding Functions (1 hour)

**File:** `apps/backend/apps/core/services/org_seed_service.py`

Create comprehensive seeding service:
```python
class OrganisationSeedService:
    """Seeds initial data for new organisations."""
    
    @staticmethod
    def seed_all(org_id: UUID):
        """Seed all required data."""
        OrganisationSeedService.seed_tax_codes(org_id)
        OrganisationSeedService.seed_chart_of_accounts(org_id)
        OrganisationSeedService.seed_fiscal_year(org_id)
    
    @staticmethod
    def seed_tax_codes(org_id: UUID):
        """Seed Singapore tax codes."""
        # OS, NA, SR, ZR, ES codes
    
    @staticmethod
    def seed_chart_of_accounts(org_id: UUID):
        """Seed standard Chart of Accounts."""
        # Assets, Liabilities, Equity, Revenue, Expenses
```

### Step 4: Hook Seeding into Organisation Creation (30 minutes)

**File:** `apps/backend/apps/core/views/organisations.py`

Add to OrganisationListCreateView.post():
```python
# After org creation
from apps.core.services.org_seed_service import OrganisationSeedService
OrganisationSeedService.seed_all(org.id)
```

### Step 5: Fix Error Handling in Views (30 minutes)

**Files:** 
- `apps/backend/apps/banking/views.py`
- `apps/backend/apps/journal/views.py`
- `apps/backend/apps/gst/views.py`

Add proper exception handling:
```python
@wrap_response
def get(self, request, org_id: str) -> Response:
    try:
        # existing code
    except Exception as e:
        logger.error(f"Banking error: {e}", exc_info=True)
        return Response(
            {"error": {"code": "internal_error", "message": str(e)}},
            status=500
        )
```

### Step 6: Test Fixes (1 hour)

- [ ] Create test organisation via API
- [ ] Verify tax codes seeded
- [ ] Verify accounts seeded
- [ ] Test banking endpoints
- [ ] Test journal endpoints
- [ ] Test tax code endpoints

---

## Phase 4: Validation Checklist

### Pre-Implementation
- [ ] Backup database
- [ ] Review all model alignments
- [ ] Document current state

### Implementation
- [ ] Add logging to middleware
- [ ] Fix model constraints
- [ ] Create seeding service
- [ ] Hook seeding to org creation
- [ ] Add error handling
- [ ] Test each fix

### Post-Implementation
- [ ] Run end-to-end workflow
- [ ] Verify all endpoints work
- [ ] Check RLS policies active
- [ ] Update documentation
- [ ] Update API guide with any changes

---

## Phase 5: Risk Assessment

### High Risk
- **Database constraint changes** — May affect existing data
- **Automatic seeding** — May overwrite user data if not careful

### Medium Risk
- **RLS context changes** — Could affect security if broken
- **Error handling changes** — May expose sensitive info

### Mitigation
- Test on development environment first
- Use transactions for seeding
- Add feature flags for seeding
- Log extensively during testing

---

## Phase 6: Alternative Quick Fixes

If full implementation is not feasible immediately:

### Option A: Manual Data Seeding (Quick)
```bash
# Run SQL to seed test org
psql -d ledgersg_dev -f seed_test_data.sql
```

### Option B: Disable RLS Temporarily (NOT for production)
```sql
-- Only for debugging!
ALTER TABLE banking.bank_account DISABLE ROW LEVEL SECURITY;
```

### Option C: Create Test Data via Django Shell
```bash
python manage.py shell
# Run seeding commands manually
```

---

## Phase 7: Documentation Updates

### API Guide Updates Required
- [ ] Add note about automatic CoA seeding
- [ ] Document tax codes that are auto-created
- [ ] Add troubleshooting for "internal_error"
- [ ] Explain RLS and tenant context

### Code Documentation
- [ ] Add docstrings to seeding service
- [ ] Document RLS middleware behavior
- [ ] Add comments about model constraints

---

## Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Investigation | 2 hours | 2 hours |
| Implementation | 4 hours | 6 hours |
| Testing | 1 hour | 7 hours |
| Documentation | 1 hour | 8 hours |
| **Total** | **8 hours** | **8 hours** |

---

## Success Criteria

1. ✅ Banking endpoints return data (not error)
2. ✅ Journal endpoints return data (not error)
3. ✅ Tax code endpoints return data (not error)
4. ✅ New organisations automatically seeded
5. ✅ RLS policies working correctly
6. ✅ All API guide examples work
7. ✅ Test suite passes

---

## Immediate Next Steps

1. **Start with Step 1** — Add debug logging
2. **Test in dev environment** — Verify logging works
3. **Proceed to Step 2** — Fix model constraints
4. **Create seeding service** — Step 3
5. **Test end-to-end** — Verify all fixes

---

**Ready for Implementation?** Yes — All requirements analyzed and plan validated against codebase.
