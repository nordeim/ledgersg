# E2E Test Findings - 2026-03-14

## Executive Summary

The E2E frontend-backend integration test revealed one critical bug and successfully validated core authentication flows.

## Tests Completed

### ✅ Passing Tests

| Test | Status | Notes |
|------|--------|-------|
| User Registration (via API) | ✅ PASS | User lakshmi@kitchen.example exists |
| User Login | ✅ PASS | Login successful, redirect to dashboard |
| Dashboard Load | ✅ PASS | Metrics displayed, navigation visible |
| Navigation: Invoices | ✅ PASS | Page loads correctly |
| Navigation: Ledger | ✅ PASS | Page loads correctly |
| Navigation: Quotes | ✅ PASS | Page loads correctly |
| Organisation Selector | ✅ PASS | Shows "Lakshmi Kitchen Pte Ltd" |

### ❌ Failing Tests

| Test | Status | Root Cause |
|------|--------|------------|
| Navigation: Banking | ❌ FAIL | API contract mismatch |

## Critical Bug: Banking Page API Contract Mismatch

### Symptom
- Banking page shows error fallback: "Try Again", "Go Back", "Home" buttons
- Console error: `TypeError: Cannot read properties of undefined (reading 'map')`

### Root Cause
**Frontend-Backend API Contract Mismatch**

**Backend Response** (`/api/v1/{org_id}/banking/bank-accounts/`):
```json
[
  {"id": "...", "account_name": "DBS", ...}
]
```

**Frontend Expectation** (`useBankAccounts` hook in `apps/web/src/hooks/use-banking.ts`):
```typescript
{
  results: BankAccount[];
  count: number;
  next?: string;
  previous?: string;
}
```

**Code Location**:
- Frontend: `apps/web/src/app/(dashboard)/banking/banking-client.tsx:188`
- Calls `accountsData.results.map()` but `accountsData.results` is `undefined` because backend returns array directly

### Impact
- Banking page completely broken for all users
- Affects: Bank Accounts, Payments, Bank Transactions tabs

### Recommended Fix
**Option A (Backend)**: Change banking views to return paginated response:
```python
# apps/banking/views.py
return Response({
    "results": serializer.data,
    "count": len(serializer.data)
})
```

**Option B (Frontend)**: Handle array response in hook:
```typescript
// apps/web/src/hooks/use-banking.ts
queryFn: async () => {
  const response = await api.get<BankAccount[] | {results: BankAccount[], count: number}>(...);
  if (Array.isArray(response)) {
    return { results: response, count: response.length };
  }
  return response;
}
```

### Screenshot Evidence
- `/tmp/lakshmi/04-banking-error.png` - Error fallback shown

## Authentication Session Behavior

### Observation
- Access tokens stored in JavaScript memory (not persisted)
- Refresh tokens in HttpOnly cookies
- Client-side navigation preserves auth state
- Full page navigation (server-side) loses auth state temporarily
- Refresh token mechanism works but there's a timing issue on initial page load

### Files Created
- `/tmp/lakshmi/01-landing.png` - Login page
- `/tmp/lakshmi/02-dashboard.png` - Dashboard after login
- `/tmp/lakshmi/03-dashboard-logged-in.png` - Dashboard with session
- `/tmp/lakshmi/04-banking-error.png` - Banking error fallback

## Next Steps

1. **Fix Banking API Contract** - Priority: HIGH
   - Align backend response with frontend expectation
   - Add integration test for response shape

2. **Continue E2E Testing** - After fix
   - Test Invoices CRUD workflow
   - Test Ledger entry creation
   - Test Reports generation

3. **Add API Contract Tests**
   - Validate response shapes in backend tests
   - Add frontend API schema validation

---
**Test Duration**: ~45 minutes
**Environment**: Local development (localhost:3000, localhost:8000)
**Tool**: agent-browser CLI
