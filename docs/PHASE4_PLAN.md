# Phase 4: Error Message Differentiation - Execution Plan

**Date:** 2026-03-08  
**Status:** READY FOR EXECUTION  
**Priority:** Medium  
**Method:** Test-Driven Development (TDD)

---

## Objective

Differentiate between "authenticated but no organisation" and "not authenticated" states in DashboardClient to provide appropriate user feedback and actions.

---

## Current State Analysis

### Current Implementation
**File:** `apps/web/src/app/(dashboard)/dashboard/dashboard-client.tsx` (lines 80-94)

**Current Behavior:**
```typescript
if (!orgId) {
  return (
    <div className="flex items-center justify-center h-[60vh]">
      <div className="text-center">
        <AlertTriangle className="h-12 w-12 text-warning mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-text-primary mb-2">
          No Organisation Selected
        </h2>
        <p className="text-text-secondary">
          Please select an organisation to view the dashboard
        </p>
      </div>
    </div>
  );
}
```

**Problem:** Shows the same message for:
1. ✅ Authenticated user with no organisation (VALID)
2. ❌ Unauthenticated user (should be redirected by Phase 3 guard, but good to have fallback)

---

## Implementation Strategy

### Step 1: Add Authentication State Check

**Changes Required:**
1. Destructure `isAuthenticated` from `useAuth()`
2. Check `isAuthenticated` before checking `orgId`
3. Show different messages for different states
4. Provide actionable buttons for each state

**Expected Behavior Matrix:**

| Authentication | Has Org | Message | Action |
|---------------|---------|---------|--------|
| ❌ Not Auth | - | "Authentication Required" | "Go to Login" button |
| ✅ Auth | ❌ No | "No Organisation Selected" | "Create Organisation" button |
| ✅ Auth | ✅ Yes | Show Dashboard | N/A |

---

## Implementation Plan

### Step 4.1: Write Failing Test (RED Phase)

**Test Scenarios:**
1. **Unauthenticated user** - Should see "Authentication Required" with "Go to Login" button
2. **Authenticated user, no organisation** - Should see "No Organisation Selected" with "Create Organisation" button
3. **Authenticated user, has organisation** - Should see dashboard content

### Step 4.2: Implement Changes (GREEN Phase)

**File:** `apps/web/src/app/(dashboard)/dashboard/dashboard-client.tsx`

**Required Changes:**

```typescript
export function DashboardClient() {
  const { currentOrg, isLoading: authLoading, isAuthenticated } = useAuth();
  
  const orgId = currentOrg?.id;
  
  // ... useQuery setup ...
  
  // STEP 1: Check auth loading
  if (authLoading) {
    return <LoadingSpinner />;
  }
  
  // STEP 2: Check authentication (NEW)
  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-alert mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-text-primary mb-2">
            Authentication Required
          </h2>
          <p className="text-text-secondary mb-4">
            Please log in to access the dashboard
          </p>
          <Link
            href="/login"
            className="inline-flex items-center px-4 py-2 bg-accent-primary text-void rounded-sm hover:bg-accent-primary-dim transition-colors"
          >
            Go to Login
          </Link>
        </div>
      </div>
    );
  }
  
  // STEP 3: Check for organisation (authenticated but no org)
  if (!orgId) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-warning mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-text-primary mb-2">
            No Organisation Selected
          </h2>
          <p className="text-text-secondary mb-4">
            You don't have any organisations. Create one to get started.
          </p>
          <Link
            href="/settings/organisations/new"
            className="inline-flex items-center px-4 py-2 bg-accent-primary text-void rounded-sm hover:bg-accent-primary-dim transition-colors"
          >
            Create Organisation
          </Link>
        </div>
      </div>
    );
  }
  
  // ... rest of component ...
}
```

### Step 4.3: Verify Test Passes (GREEN Phase)

Run tests to ensure:
- ✅ Unauthenticated users see appropriate message
- ✅ Authenticated users without org see appropriate message
- ✅ Dashboard renders for authenticated users with org

---

## Test Cases

### Test 1: Unauthenticated User

**Setup:**
- Clear all cookies
- Visit dashboard

**Expected:**
- Message: "Authentication Required"
- Button: "Go to Login" → links to `/login`

### Test 2: Authenticated User, No Organisation

**Setup:**
- Login with user that has no organisations
- Visit dashboard

**Expected:**
- Message: "No Organisation Selected"
- Button: "Create Organisation" → links to `/settings/organisations/new`

### Test 3: Authenticated User, Has Organisation

**Setup:**
- Login with user that has organisation
- Visit dashboard

**Expected:**
- Dashboard content visible
- Organisation name shown in sidebar

---

## Files to Modify

### Frontend
1. `apps/web/src/app/(dashboard)/dashboard/dashboard-client.tsx`
   - Add `isAuthenticated` check
   - Update error messages
   - Add actionable buttons

---

## Success Criteria

- [ ] Unauthenticated users see "Authentication Required" message
- [ ] Authenticated users without org see "No Organisation Selected" message
- [ ] Different messages for different states
- [ ] Actionable buttons available for each state
- [ ] No regression in existing dashboard functionality
- [ ] All tests passing

---

## Timeline

**Estimated Time:** 30 minutes

- Step 1: Write failing test - 10 minutes
- Step 2: Implement changes - 10 minutes
- Step 3: Verify tests - 5 minutes
- Step 4: Documentation - 5 minutes

---

## Risk Assessment

**Low Risk:**
- Changes are minimal and localized
- Only affects error message display
- Fallback behavior if state is incorrect
- Phase 3 guard already handles most cases

---

## Notes

1. **Phase 3 Overlap:** The authentication guard in Phase 3 should already handle most unauthenticated cases, but this provides an additional safety net and better UX.

2. **Button Actions:** The buttons provide clear next steps for users, improving the overall UX.

3. **Icon Colors:** Using `text-alert` for authentication errors and `text-warning` for organisation warnings provides visual distinction.

---

**Ready for Execution:** ✅ YES  
**TDD Phase:** RED → GREEN → REFACTOR  
**Status:** Proceeding to Step 4.1
