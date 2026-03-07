# Dashboard "No Organisation Selected" - Root Cause Analysis

**Date:** 2026-03-07  
**Investigation Method:** Playwright Browser Automation + curl API Testing  
**Status:** ✅ ROOT CAUSE IDENTIFIED

---

## Executive Summary

The dashboard displays "No Organisation Selected" because the user **is NOT authenticated**. The browser has no valid JWT tokens (neither access token in memory nor refresh token cookie), causing the backend API to return `401 Unauthorized` for the `/api/v1/auth/me/` endpoint.

---

## Investigation Results

### 1. Browser State Analysis

**Playwright Test Output:**
```
Page Title: LedgerSG — IRAS-Compliant Accounting for Singapore SMBs
Current URL: http://localhost:3000/dashboard/
Is Login Page: False
Has Loader: False
Has AlertTriangle Icon: False
Has 'No Organisation Selected': True
```

**Main Text Content (first 200 chars):**
```
LLEDGERSGIRAS-Compliant AccountingDashboardInvoicesQuotesLedgerBankingReportsSettingsDUDemo Useruser@example.comLedgerSGNew InvoiceNo Organisation SelectedPlease select an organisation to view the das
```

**Key Observation:** The dashboard renders but shows the organization selection prompt.

### 2. Network Request Analysis

**Auth-related Requests:** 1  
**Auth-related Responses:** 1

**Response Details:**
```
GET http://localhost:8000/api/v1/auth/me/
Status: 401 Unauthorized
Body: { "detail": "Authentication credentials were not provided." }
```

**Console Error:**
```
[error] Failed to load resource: the server responded with a status of 401 (Unauthorized)
at http://localhost:8000/api/v1/auth/me/:0
```

### 3. Cookie Analysis

**Total Cookies:** 0

**Expected Cookies:**  
- `refresh_token` (HttpOnly cookie with 7-day expiry)  
- Session cookies for authentication state

**Actual:** No cookies present in browser.

---

## Root Cause Analysis

### The Authentication Flow

```
Browser Loads Dashboard (/dashboard/)
    ↓
AuthProvider.checkSession() (useEffect on mount)
    ↓
api.get('/api/v1/auth/me/')
    ↓
Request sent with:
  - Authorization: Bearer {accessToken}  ← accessToken is NULL
  - credentials: 'include'              ← No refresh token cookie
    ↓
Backend: CORSJWTAuthentication.authenticate()
    ↓
JWTAuthentication.authenticate()
    ↓
No valid token found → 401 Unauthorized
    ↓
Response: {"detail": "Authentication credentials were not provided."}
    ↓
AuthProvider catches error → clearAuth()
    ↓
State: user=null, organisations=[], currentOrgId=null
    ↓
DashboardClient renders:
    - authLoading=false
    - orgId=undefined (currentOrg?.id)
    - Shows "No Organisation Selected" message
```

### Why User Isn't Redirected to Login

**Critical Issue:** The AuthProvider does NOT redirect to `/login` on authentication failure.

**Code Analysis:**

```typescript
// apps/web/src/providers/auth-provider.tsx:96-125
React.useEffect(() => {
  async function checkSession() {
    try {
      const userData = await api.get<User>(endpoints.auth.me);
      setUser(userData);
      
      const orgsData = await api.get<UserOrganisation[]>(
        endpoints.organisations.list
      );
      setOrganisations(orgsData);
      
      const defaultOrg = orgsData.find((uo) => uo.is_default);
      if (defaultOrg) {
        setCurrentOrgId(defaultOrg.org.id);
      } else if (orgsData.length > 0) {
        setCurrentOrgId(orgsData[0].org.id);
      }
    } catch {
      // No valid session
      clearAuth();  // ← Clears tokens but NO redirect
    } finally {
      setIsLoading(false);
    }
  }
  
  checkSession();
}, []);
```

**Expected Behavior:**
```typescript
} catch {
  clearAuth();
  router.push('/login');  // ← MISSING: Should redirect to login
}
```

**Current Behavior:**
- Clears auth state (`user=null`, `organisations=[]`, `currentOrgId=null`)
- Sets `isLoading=false`
- Does NOT redirect to login page
- Dashboard renders with "No Organisation Selected" message

---

## Expected vs Actual Behavior

### Expected Flow (Authenticated User)

```
1. User visits /dashboard/
2. Browser has refresh_token cookie from previous login
3. AuthProvider calls /api/v1/auth/me/
4. Backend returns 200 OK with user data
5. AuthProvider fetches /api/v1/auth/organisations/
6. Backend returns list of user's organisations
7. AuthProvider sets currentOrg to default org
8. Dashboard renders with organisation data
```

### Actual Flow (Unauthenticated User - Current State)

```
1. User visits /dashboard/
2. Browser has NO cookies (fresh session)
3. AuthProvider calls /api/v1/auth/me/
4. Backend returns 401 Unauthorized
5. AuthProvider catches error and clears state
6. Dashboard renders "No Organisation Selected"
7. User sees confusing message (should see login form)
```

---

## Code Validation

### Frontend: AuthProvider (apps/web/src/providers/auth-provider.tsx)

**Lines 96-125:** Session check on mount
```typescript
// ISSUE: No redirect to login on auth failure
} catch {
  clearAuth();  // ← Only clears, no redirect
}
```

**Lines 150-163:** Logout function
```typescript
const logout = async () => {
  try {
    await api.post(endpoints.auth.logout);
  } catch {
    // Ignore logout errors
  } finally {
    clearAuth();
    setUser(null);
    setOrganisations([]);
    setCurrentOrgId(null);
    queryClient.clear();
    router.push("/login");  // ← Redirects to login (correct)
  }
};
```

**Observation:** Logout correctly redirects to login, but initial auth failure does not.

### Frontend: DashboardClient (apps/web/src/app/(dashboard)/dashboard/dashboard-client.tsx)

**Lines 72-94:** Auth loading and org check
```typescript
if (authLoading) {
  return (
    <div className="flex items-center justify-center h-[60vh]">
      <Loader2 className="h-8 w-8 animate-spin text-accent-primary" />
    </div>
  );
}

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

**Issue:** The message is misleading for unauthenticated users. It should differentiate between:
1. **Authenticated but no org:** "Please select an organisation"
2. **Not authenticated:** "Please log in to continue" → redirect to `/login`

### Backend: Authentication (apps/backend/apps/core/authentication.py)

**Lines 1-38:** CORSJWTAuthentication
```python
class CORSJWTAuthentication(JWTAuthentication):
    def authenticate(self, request: Request):
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return None  # Allow CORS preflight
        return super().authenticate(request)  # Normal JWT auth
```

**Backend is working correctly:** Returns 401 for unauthenticated GET requests.

---

## curl Verification

### Test 1: OPTIONS Preflight (CORS)
```bash
curl -X OPTIONS http://localhost:8000/api/v1/auth/me/ -i
```
**Result:** `HTTP/1.1 200 OK` ✅ CORS preflight works

### Test 2: GET Without Credentials
```bash
curl -X GET http://localhost:8000/api/v1/auth/me/ -i
```
**Result:** `HTTP/1.1 401 Unauthorized` ✅ Backend correctly rejects unauthenticated requests

### Test 3: Organisations Endpoint
```bash
curl -X GET http://localhost:8000/api/v1/organisations/ -i
```
**Result:** `HTTP/1.1 401 Unauthorized` ✅ Protected endpoint requires auth

---

## Frontend Layout Analysis

### Route Structure

```
/ (root)
├── (auth)/
│   └── login/
│       └── page.tsx  ← Login page (simulated, not connected to backend)
└── (dashboard)/
    ├── layout.tsx    ← Shell component (sidebar, header)
    └── dashboard/
        └── page.tsx  ← Dashboard page
```

### Component Hierarchy

```
RootLayout (app/layout.tsx)
└── Providers (providers/index.tsx)
    └── AuthProvider (providers/auth-provider.tsx)
        └── DashboardLayout (app/(dashboard)/layout.tsx)
            └── Shell (components/layout/shell.tsx)
                └── DashboardClient (dashboard-client.tsx)
```

**Issue:** All routes under `(dashboard)` are publicly accessible. There's no middleware or route guard to redirect unauthenticated users to `/login`.

---

## Root Cause Summary

### Primary Issue: Missing Authentication Guard

**What:** The dashboard route is not protected. Unauthenticated users can access `/dashboard/` directly.

**Where:** 
- `AuthProvider` clears state on auth failure but doesn't redirect to `/login`
- No middleware checks authentication before rendering dashboard routes
- `DashboardClient` shows generic "No Organisation Selected" for all cases

**Why:**
- Auth flow was designed for "already logged in" scenarios
- Missing edge case handling for "never logged in" users
- Login page exists but is not connected to backend auth system (simulated)

### Secondary Issue: Misleading Error Message

**What:** "No Organisation Selected" is shown to both:
1. Authenticated users with no organisation
2. Unauthenticated users (actual issue)

**Where:** `DashboardClient.tsx:80-94`

**Why:** The component doesn't check `isAuthenticated` before checking `orgId`.

---

## Expected Behavior (Production)

### Option A: Redirect to Login (Recommended)

```typescript
// auth-provider.tsx
} catch {
  clearAuth();
  router.push('/login');  // ← Add redirect
}
```

**Flow:**
```
1. User visits /dashboard/
2. AuthProvider calls /api/v1/auth/me/
3. Backend returns 401
4. AuthProvider redirects to /login
5. User sees login form
6. User logs in → redirected back to /dashboard/
```

### Option B: Middleware Route Guard

```typescript
// middleware.ts (Next.js middleware)
export function middleware(request: NextRequest) {
  const isAuthenticated = request.cookies.get('refresh_token');
  
  if (!isAuthenticated && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
}
```

### Option C: Conditional Message

```typescript
// dashboard-client.tsx
if (!orgId) {
  if (!isAuthenticated) {
    return <Navigate to="/login" />;  // or redirect
  }
  return <NoOrganisationSelected />;
}
```

---

## Recommendations

### Immediate Fix (High Priority)

1. **Add redirect to AuthProvider:**
   ```typescript
   // apps/web/src/providers/auth-provider.tsx:116-120
   } catch {
     clearAuth();
     router.push('/login');  // ← ADD THIS
   }
   ```

2. **Connect Login Page to Backend:**
   - Replace simulated login with actual `api.post(endpoints.auth.login, { email, password })`
   - Handle success: call `login()` from AuthProvider
   - Handle errors: show error message

### Short-Term Fix (Medium Priority)

3. **Add Authentication Guard to Dashboard Layout:**
   ```typescript
   // apps/web/src/app/(dashboard)/layout.tsx
   const { isAuthenticated, isLoading } = useAuth();
   
   if (!isLoading && !isAuthenticated) {
     return <Navigate to="/login" />;
   }
   ```

4. **Differentiate Error Messages:**
   ```typescript
   // apps/web/src/app/(dashboard)/dashboard/dashboard-client.tsx
   if (!orgId) {
     if (!isAuthenticated) {
       return <RedirectToLogin />;
     }
     return <NoOrganisationSelected />;
   }
   ```

### Long-Term Enhancement (Low Priority)

5. **Implement Next.js Middleware:**
   - Check for `refresh_token` cookie before rendering protected routes
   - Redirect to login if missing
   - Preserve intended destination for post-login redirect

6. **Add "Remember Me" Feature:**
   - Extended refresh token lifetime (30 days vs 7 days)
   - Persistent login across browser sessions

---

## Test Plan

### Manual Testing Steps

1. **Test Current Behavior:**
   ```bash
   # Clear all cookies
   # Open browser DevTools → Application → Cookies → Clear all
   
   # Visit dashboard
   open http://localhost:3000/dashboard/
   
   # Expected: See "No Organisation Selected"
   # Actual: ✓ Confirmed
   ```

2. **Test Login Flow:**
   ```bash
   # Visit login page
   open http://localhost:3000/login/
   
   # Enter credentials (need test user)
   # Click "Sign In"
   
   # Expected: Redirect to dashboard
   # Actual: Simulated login (not connected to backend)
   ```

3. **Test with Valid Refresh Token:**
   ```bash
   # Log in via API
   curl -X POST http://localhost:8000/api/v1/auth/login/ \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"password"}' \
     -c cookies.txt  # Save cookies
   
   # Visit dashboard with cookies
   # Expected: Dashboard renders with org data
   ```

### Automated Testing Steps

```bash
# Run Playwright investigation
source /opt/venv/bin/activate
python /tmp/test_dashboard_investigation.py

# Check results:
# - /tmp/dashboard-screenshot.png
# - /tmp/dashboard-har.json
```

---

## Related Files

### Frontend Files
- `/apps/web/src/providers/auth-provider.tsx` - Authentication state management
- `/apps/web/src/app/(dashboard)/dashboard/dashboard-client.tsx` - Dashboard rendering
- `/apps/web/src/app/(auth)/login/page.tsx` - Login page (simulated)
- `/apps/web/src/lib/api-client.ts` - API client with JWT handling

### Backend Files
- `/apps/backend/apps/core/authentication.py` - CORSJWTAuthentication class
- `/apps/backend/apps/core/views/auth.py` - Auth endpoints (login, me, refresh)

### Documentation
- `/home/project/Ledger-SG/AGENTS.md` - Project architecture and standards
- `/home/project/Ledger-SG/ACCOMPLISHMENTS.md` - CORS fix milestone

---

## Conclusion

**Root Cause:** User is not authenticated. The browser has no JWT tokens, causing `401 Unauthorized` from the backend. The frontend doesn't redirect to login, resulting in the misleading "No Organisation Selected" message.

**Fix:** Add authentication guard to redirect unauthenticated users to the login page, and connect the login form to the backend authentication system.

**Impact:** This is a critical UX issue that prevents new users from accessing the dashboard. The login page exists but is not functional.

---

**Investigation Completed:** 2026-03-07  
**Method:** Playwright browser automation + curl API testing  
**Duration:** ~30 minutes  
**Confidence:** 100% (all evidence points to missing authentication)
