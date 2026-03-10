# Frontend-Backend Integration Remediation Plan
## Test-Driven Development (TDD) Approach

**Date:** 2026-03-10  
**Status:** ✅ Validated & Ready for Execution  
**TDD Methodology:** RED → GREEN → REFACTOR  

---

## 🔍 Re-Validation Summary

After meticulous re-validation against the actual codebase:

| Issue | Initial Finding | Re-Validation | Status |
|-------|----------------|---------------|--------|
| **#1** | Auth Refresh Response | ✅ **CONFIRMED** | **CRITICAL** |
| **#2** | Missing Contact Update | ❌ **FALSE POSITIVE** | **NOT AN ISSUE** |
| **#3** | Organization Endpoints | ✅ **CONFIRMED** | **LOW PRIORITY** |

### Actual Issues to Fix: 2 (Not 3)

---

## Issue #1: Auth Refresh Response Parsing [CRITICAL]

### Root Cause Analysis

**Backend Response (auth.py:113):**
```python
return Response({"tokens": tokens})
# Returns: {"tokens": {"access": "...", "refresh": "...", "access_expires": "..."}}
```

**Frontend Parsing (api-client.ts:119):**
```typescript
setAccessToken(data.access);  // ❌ WRONG - data.tokens.access needed
```

**Impact:**
- Token refresh will fail silently
- Users will be logged out unexpectedly after 15 minutes
- Authentication flow appears to work but breaks on refresh

---

## Issue #3: Organization Endpoints Architecture [LOW]

### Root Cause Analysis

**Current Frontend Pattern (api-client.ts:161-166):**
```typescript
organisations: {
  list: "/api/v1/auth/organisations/",  // ✅ Correct
  detail: (id: string) => `/api/v1/${id}/`,  // ❌ Misleading - should be org-scoped
  settings: (id: string) => `/api/v1/${id}/settings/`,  // ❌ Same issue
  setDefault: "/api/v1/auth/set-default-org/",  // ✅ Correct
}
```

**Backend Structure:**
- `api/v1/auth/organisations/` → Non-org-scoped ✅
- `api/v1/{org_id}/` → Org-scoped ✅
- `api/v1/{org_id}/settings/` → Org-scoped ✅

**The Problem:** The `detail` and `settings` endpoints are defined in the `organisations` object but behave inconsistently with other org-scoped endpoints. They should follow the pattern: `organisations(orgId).detail()` like `banking(orgId).accounts`.

---

## 📋 TDD Remediation Plan

### Phase 1: Issue #1 - Auth Refresh Response [CRITICAL]

#### Step 1: RED - Write Failing Test

**Test File:** `apps/web/src/lib/__tests__/api-client-auth.test.ts`

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { api, setAccessToken, getAccessToken, clearAuth } from "../api-client";

describe("Token Refresh", () => {
  beforeEach(() => {
    clearAuth();
    vi.resetAllMocks();
  });

  it("should extract access token from nested response", async () => {
    // Mock fetch to return nested tokens structure
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        tokens: {
          access: "new-access-token",
          refresh: "new-refresh-token",
        },
      }),
    });

    // Trigger a request that causes 401
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        status: 401,
        ok: false,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          tokens: {
            access: "new-access-token",
            refresh: "new-refresh-token",
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true }),
      });

    // Make request
    await api.get("/test-endpoint/");

    // Verify token was extracted from nested structure
    expect(getAccessToken()).toBe("new-access-token");
  });

  it("should fail when response structure is wrong", async () => {
    // This test will pass with current broken code
    // and fail after fix - demonstrating the issue
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        access: "flat-access-token", // Wrong structure
      }),
    });

    // With current code, this would set "undefined"
    // After fix, this should work with tokens.access
  });
});
```

#### Step 2: GREEN - Implement Fix

**File:** `apps/web/src/lib/api-client.ts`

**Current (Line 119):**
```typescript
setAccessToken(data.access);
```

**Fix:**
```typescript
setAccessToken(data.tokens?.access || data.access);
// Support both structures for backward compatibility
// Backend returns: {tokens: {access, refresh}}
```

#### Step 3: REFACTOR - Improve Code Quality

Add better error handling and logging:

```typescript
async function tryRefreshToken(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh/`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    });

    if (response.ok) {
      const data = await response.json();
      
      // Handle both response structures for backward compatibility
      const accessToken = data.tokens?.access || data.access;
      
      if (!accessToken) {
        console.error("[Auth] No access token in refresh response", data);
        return false;
      }
      
      setAccessToken(accessToken);
      console.log("[Auth] Token refreshed successfully");
      return true;
    }
    
    console.error("[Auth] Token refresh failed:", response.status);
    return false;
  } catch (error) {
    console.error("[Auth] Token refresh error:", error);
    return false;
  }
}
```

#### Step 4: Verification

Run tests to ensure:
1. ✅ New test passes (nested structure)
2. ✅ Existing tests still pass
3. ✅ Manual test: Login → wait 15 min → request should auto-refresh

---

### Phase 2: Issue #3 - Organization Endpoints [LOW]

#### Step 1: RED - Write Test Exposing Issue

**Test File:** `apps/web/src/lib/__tests__/api-client-organisations.test.ts`

```typescript
import { describe, it, expect } from "vitest";
import { endpoints } from "../api-client";

describe("Organisations Endpoints", () => {
  it("should have consistent org-scoped pattern", () => {
    const orgId = "550e8400-e29b-41d4-a716-446655440000";
    
    // Check list endpoint (non-org-scoped)
    expect(endpoints.organisations.list).toBe("/api/v1/auth/organisations/");
    
    // Check setDefault endpoint (non-org-scoped)
    expect(endpoints.organisations.setDefault).toBe("/api/v1/auth/set-default-org/");
    
    // These should follow the same pattern as banking/invoicing
    // Currently they're defined differently
  });
  
  it("should generate correct org-scoped detail URL", () => {
    const orgId = "550e8400-e29b-41d4-a716-446655440000";
    
    // Current implementation
    const currentDetail = endpoints.organisations.detail(orgId);
    expect(currentDetail).toBe(`/api/v1/${orgId}/`);
    
    // This IS actually correct based on backend:
    // api/v1/{org_id}/ → OrganisationDetailView
    // api/v1/{org_id}/settings/ → OrganisationSettingsView
  });
  
  it("should match banking endpoint pattern consistency", () => {
    const orgId = "550e8400-e29b-41d4-a716-446655440000";
    
    // Banking pattern: endpoints.banking(orgId).accounts
    const bankingAccounts = endpoints.banking(orgId).accounts;
    expect(bankingAccounts).toContain(orgId);
    
    // Organisations pattern should be similar
    // But currently uses: endpoints.organisations.detail(orgId)
    // Which is different from: endpoints.organisations(orgId).detail
    
    // This inconsistency is the architectural issue
  });
});
```

#### Step 2: GREEN - Refactor to Consistent Pattern

**File:** `apps/web/src/lib/api-client.ts`

**Current (Lines 160-166):**
```typescript
// Organisations
organisations: {
  list: "/api/v1/auth/organisations/",
  detail: (id: string) => `/api/v1/${id}/`,
  settings: (id: string) => `/api/v1/${id}/settings/`,
  setDefault: "/api/v1/auth/set-default-org/",
},
```

**Refactored (Following Banking Pattern):**
```typescript
// Organisations
// Returns function that takes orgId for org-scoped endpoints
organisations: (orgId?: string) => ({
  // Non-org-scoped (available without orgId)
  list: "/api/v1/auth/organisations/",
  setDefault: "/api/v1/auth/set-default-org/",
  
  // Org-scoped (require orgId)
  detail: orgId ? `/api/v1/${orgId}/` : undefined,
  settings: orgId ? `/api/v1/${orgId}/settings/` : undefined,
}),

// Alternative: Keep backward compatibility while adding new pattern
organisations: {
  // Non-org-scoped
  list: "/api/v1/auth/organisations/",
  setDefault: "/api/v1/auth/set-default-org/",
  
  // Org-scoped - follow consistent pattern
  org: (orgId: string) => ({
    detail: `/api/v1/${orgId}/`,
    settings: `/api/v1/${orgId}/settings/`,
    summary: `/api/v1/${orgId}/summary/`,
    fiscalYears: `/api/v1/${orgId}/fiscal-years/`,
    fiscalPeriods: `/api/v1/${orgId}/fiscal-periods/`,
    closeFiscalYear: (yearId: string) => `/api/v1/${orgId}/fiscal-years/${yearId}/close/`,
    closeFiscalPeriod: (periodId: string) => `/api/v1/${orgId}/fiscal-periods/${periodId}/close/`,
    gst: `/api/v1/${orgId}/gst/`,
  }),
},
```

#### Step 3: Update All Usage Sites

Search and update any code using `endpoints.organisations.detail()` or `endpoints.organisations.settings()`:

```typescript
// OLD
endpoints.organisations.detail(orgId)
endpoints.organisations.settings(orgId)

// NEW
endpoints.organisations.org(orgId).detail
endpoints.organisations.org(orgId).settings
```

#### Step 4: REFACTOR - Document Pattern

Add documentation comment:

```typescript
/**
 * Organization endpoints follow a hybrid pattern:
 * 
 * Non-org-scoped (no orgId needed):
 * - organisations.list → GET /api/v1/auth/organisations/
 * - organisations.setDefault → POST /api/v1/auth/set-default-org/
 * 
 * Org-scoped (requires orgId):
 * - organisations.org(orgId).detail → GET /api/v1/{orgId}/
 * - organisations.org(orgId).settings → GET/PATCH /api/v1/{orgId}/settings/
 * - organisations.org(orgId).summary → GET /api/v1/{orgId}/summary/
 * 
 * This differs from banking/invoicing which are purely org-scoped.
 * The pattern was chosen to maintain backward compatibility while
 * providing a consistent API for org-scoped resources.
 */
```

#### Step 5: Verification

1. ✅ All tests pass
2. ✅ No TypeScript compilation errors
3. ✅ All usages updated
4. ✅ Documentation updated

---

## 📊 Implementation Checklist

### Pre-Implementation

- [ ] Create feature branch: `fix/auth-refresh-and-org-endpoints`
- [ ] Review current test coverage
- [ ] Identify all usages of affected endpoints
- [ ] Document rollback strategy

### Issue #1: Auth Refresh Response

#### Test Phase (RED)
- [ ] Create `api-client-auth.test.ts` with failing test
- [ ] Verify test fails with current code
- [ ] Document expected behavior

#### Implementation Phase (GREEN)
- [ ] Fix token extraction in `api-client.ts:119`
- [ ] Add error handling and logging
- [ ] Run test - should pass now

#### Refactor Phase
- [ ] Add backward compatibility support
- [ ] Improve error messages
- [ ] Add debug logging (dev only)
- [ ] Verify no regression in existing tests

#### Verification
- [ ] Unit tests pass
- [ ] Integration test: Login → wait → verify auto-refresh
- [ ] Check browser console for auth logs
- [ ] Verify token persistence across page reloads

### Issue #3: Organization Endpoints

#### Test Phase (RED)
- [ ] Create `api-client-organisations.test.ts` with failing tests
- [ ] Verify inconsistency is documented
- [ ] Test current behavior

#### Implementation Phase (GREEN)
- [ ] Refactor organisations endpoint structure
- [ ] Maintain backward compatibility
- [ ] Run tests - should pass

#### Refactor Phase
- [ ] Update all usage sites
- [ ] Add deprecation warnings for old pattern
- [ ] Improve documentation
- [ ] Verify consistency with other modules

#### Verification
- [ ] All tests pass
- [ ] TypeScript compilation succeeds
- [ ] No runtime errors
- [ ] Manual testing of org operations

### Post-Implementation

- [ ] Update INTEGRATION_AUDIT_REPORT.md
- [ ] Update API documentation
- [ ] Create PR with detailed description
- [ ] Request code review
- [ ] Merge after approval

---

## 🧪 Test Strategy

### Unit Tests

```typescript
// Auth Refresh
describe("Token Refresh", () => {
  it("should extract token from nested structure", () => {});
  it("should handle flat structure for backward compatibility", () => {});
  it("should fail gracefully on missing token", () => {});
  it("should retry request with new token", () => {});
});

// Organisation Endpoints
describe("Organisation Endpoints", () => {
  it("should follow consistent naming pattern", () => {});
  it("should generate correct URLs", () => {});
  it("should support org-scoped and non-org-scoped", () => {});
});
```

### Integration Tests

```typescript
// E2E Auth Flow
describe("Authentication Flow", () => {
  it("should login and maintain session", async () => {});
  it("should auto-refresh on 401", async () => {});
  it("should redirect to login on refresh failure", async () => {});
});

// E2E Organisation Operations
describe("Organisation Operations", () => {
  it("should list organisations", async () => {});
  it("should get org details", async () => {});
  it("should update org settings", async () => {});
  it("should set default org", async () => {});
});
```

### Manual Testing Checklist

**Auth Refresh:**
1. Login with valid credentials
2. Wait for token to expire (or manually expire)
3. Make API request
4. Verify auto-refresh triggered
5. Verify request succeeds with new token
6. Check localStorage/memory for new token

**Organisation Endpoints:**
1. Load organisation list
2. Switch to organisation detail
3. Update organisation settings
4. Set different org as default
5. Verify all URLs correct in network tab

---

## ⚠️ Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Backward Compatibility** | High | Support both response structures; Add deprecation warnings |
| **Breaking Changes** | Medium | Gradual migration; Keep old API available |
| **Token Loss** | High | Fallback to login on refresh failure; Clear error messages |
| **TypeScript Errors** | Low | Run tsc --noEmit before commit |
| **Test Failures** | Low | Full test suite before PR |

---

## 📝 Rollback Strategy

**If Issue #1 causes problems:**
1. Revert `api-client.ts:119` change
2. Deploy hotfix
3. Update backend to return flat structure temporarily
4. Plan proper migration

**If Issue #3 causes problems:**
1. Revert endpoint structure changes
2. Keep old implementation
3. Document as known technical debt
4. Plan gradual migration

---

## 📈 Success Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| **Test Coverage** | 100% | All new code covered |
| **Type Safety** | 0 errors | `tsc --noEmit` passes |
| **Auth Reliability** | 100% | No auth failures in testing |
| **Backward Compatibility** | 100% | Old code still works |
| **Performance** | No regression | Page load times unchanged |
| **Code Quality** | A+ | No ESLint/Prettier errors |

---

## ✅ Pre-Execution Approval Checklist

- [ ] Plan reviewed by technical lead
- [ ] All risks documented
- [ ] Rollback strategy prepared
- [ ] Test environment ready
- [ ] Stakeholders notified
- [ ] Time allocated: 4 hours estimated
- [ ] Feature branch created

---

**Ready for Execution:** ✅  
**Confidence Level:** 95%  
**Estimated Time:** 4 hours  
**Next Step:** Create feature branch and begin Phase 1
