# Authentication Flow Remediation Plan

**Version:** 1.0  
**Date:** 2026-03-07  
**Status:** READY FOR EXECUTION  
**Priority:** CRITICAL (Blocks user access to dashboard)

---

## Executive Summary

This plan addresses the root cause of the "No Organisation Selected" issue by implementing a complete authentication flow from login page to dashboard. The remediation is organized into **5 phases** with detailed validation checkpoints.

---

## Root Cause Recap

**Issue:** Unauthenticated users see "No Organisation Selected" instead of being redirected to login.

**Root Cause:**
1. AuthProvider doesn't redirect to `/login` on authentication failure
2. Login page uses simulated authentication (not connected to backend)
3. No middleware guards to protect dashboard routes
4. DashboardClient shows generic message for all auth states

---

## Phase Structure Overview

```
Phase 1: AuthProvider Redirect (Critical)
    ↓
Phase 2: Login Backend Integration (Critical)
    ↓
Phase 3: Authentication Guard (High Priority)
    ↓
Phase 4: Error Message Differentiation (Medium Priority)
    ↓
Phase 5: End-to-End Testing & Documentation (Required)
```

---

## PHASE 1: AuthProvider Redirect (CRITICAL)

### Objective
Add automatic redirect to `/login` when authentication fails during initial session check.

### Codebase Alignment Validation

**File:** `apps/web/src/providers/auth-provider.tsx`

**Current Implementation (Lines 96-125):**
```typescript
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
      clearAuth();  // ← ISSUE: No redirect
    } finally {
      setIsLoading(false);
    }
  }
  
  checkSession();
}, []);
```

**Required Implementation:**
```typescript
} catch {
  // No valid session
  clearAuth();
  router.push('/login');  // ← FIX: Add redirect
}
```

**Dependencies:**
- `useRouter` hook is already imported (line 4)
- `router` instance available in component scope (line 78)

### Implementation Steps

#### Step 1.1: Modify AuthProvider
**File:** `apps/web/src/providers/auth-provider.tsx`  
**Line:** 116-118

**Change:**
```typescript
// BEFORE:
} catch {
  clearAuth();
}

// AFTER:
} catch {
  clearAuth();
  // Redirect to login if not already on login page
  if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
    router.push('/login');
  }
}
```

**Rationale:**
- Check `window.location.pathname` to prevent redirect loops
- Only redirect if NOT already on login page
- Use Next.js `router.push()` for client-side navigation

#### Step 1.2: Add Redirect State Preservation
**Enhancement:** Preserve intended destination for post-login redirect.

**Change:**
```typescript
} catch {
  clearAuth();
  const currentPath = window.location.pathname;
  const returnUrl = currentPath !== '/login' ? `?redirect=${encodeURIComponent(currentPath)}` : '';
  router.push(`/login${returnUrl}`);
}
```

**Rationale:**
- Users will be redirected back to intended page after login
- Improves UX for deep-link scenarios
- Follows OAuth 2.0 best practices

### Validation Criteria

**Manual Testing:**
```bash
# 1. Clear all cookies in browser
# 2. Visit http://localhost:3000/dashboard/
# 3. Expected: Automatically redirect to /login
# 4. Expected: URL should NOT change to /dashboard/ then back to /login/ (no flash)
```

**Automated Testing:**
```bash
# Run Playwright test
source /opt/venv/bin/activate
python /tmp/test_auth_redirect.py  # To be created in Phase 5
```

**Success Criteria:**
- [ ] Unauthenticated users are redirected to `/login`
- [ ] No redirect loop occurs
- [ ] No console errors
- [ ] URL bar shows `/login` (not `/dashboard`)
- [ ] Login form is visible and interactive

### Rollback Plan

If redirect causes issues:
```typescript
// Comment out redirect, keep clearAuth only
} catch {
  clearAuth();
  // TODO: Investigate redirect issue
  // router.push('/login');
}
```

---

## PHASE 2: Login Backend Integration (CRITICAL)

### Objective
Connect login form to backend authentication API, replacing simulated authentication.

### Codebase Alignment Validation

**File:** `apps/web/src/app/(auth)/login/page.tsx`

**Current Implementation (Lines 24-34):**
```typescript
const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
  e.preventDefault();
  setIsSubmitting(true);
  setError(null);
  
  // Simulate login - will be replaced with actual auth
  setTimeout(() => {
    setIsSubmitting(false);
    router.push("/dashboard");
  }, 1000);
};
```

**Backend API Contract:**

**Endpoint:** `POST /api/v1/auth/login/`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Success Response (200 OK):**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "phone": "+65-1234-5678",
    "created_at": "2026-01-01T00:00:00Z"
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "access_expires": "2026-03-07T12:15:00Z"
  }
}
```

**Error Response (401 Unauthorized):**
```json
{
  "error": {
    "code": "invalid_credentials",
    "message": "Invalid email or password."
  }
}
```

**AuthProvider Integration:**

**File:** `apps/web/src/providers/auth-provider.tsx`  
**Lines 127-148:** `login()` function already exists

```typescript
const login = async (email: string, password: string) => {
  const response = await api.post<{
    user: User;
    organisations: UserOrganisation[];
    access: string;
  }>(endpoints.auth.login, { email, password });
  
  setAccessToken(response.access);
  setUser(response.user);
  setOrganisations(response.organisations);
  
  // Set default org
  const defaultOrg = response.organisations.find((uo) => uo.is_default);
  if (defaultOrg) {
    setCurrentOrgId(defaultOrg.org.id);
  } else if (response.organisations.length > 0) {
    setCurrentOrgId(response.organisations[0].org.id);
  }
  
  // Invalidate any cached queries
  queryClient.invalidateQueries();
};
```

**ISSUE:** Backend returns `{ user, tokens: { access, refresh } }` but frontend expects `{ user, organisations, access }`.

**Backend Actual Response Structure:**
```json
{
  "user": { ... },
  "tokens": {
    "access": "...",
    "refresh": "...",
    "access_expires": "..."
  }
}
```

**Frontend Expected Structure:**
```json
{
  "user": { ... },
  "organisations": [ ... ],
  "access": "..."
}
```

**MISMATCH DETECTED:** Frontend and backend have different response structures!

### Step 2.1: Backend Response Alignment

**Option A:** Modify backend to return organisations in login response (RECOMMENDED)

**File:** `apps/backend/apps/core/views/auth.py`  
**Lines 80-85**

**Current:**
```python
return Response(
    {
        "user": UserProfileSerializer(user).data,
        "tokens": tokens,
    }
)
```

**Required:**
```python
from apps.core.models import UserOrganisation

# Get user's organisations
user_orgs = UserOrganisation.objects.filter(
    user=user, 
    accepted_at__isnull=False
).select_related('org', 'role')

organisations_data = [
    {
        "id": str(membership.org.id),
        "org": {
            "id": str(membership.org.id),
            "name": membership.org.name,
            "legal_name": membership.org.legal_name,
            "uen": membership.org.uen,
            "entity_type": membership.org.entity_type,
            "gst_registered": membership.org.gst_registered,
            "gst_reg_number": membership.org.gst_reg_number,
            "gst_reg_date": membership.org.gst_reg_date,
            "gst_scheme": membership.org.gst_scheme,
            "gst_filing_frequency": membership.org.gst_filing_frequency,
            "peppol_participant_id": membership.org.peppol_participant_id,
            "invoicenow_enabled": membership.org.invoicenow_enabled,
            "fy_start_month": membership.org.fy_start_month,
            "base_currency": membership.org.base_currency,
            "timezone": membership.org.timezone,
            "is_active": membership.org.is_active,
        },
        "role": {
            "id": str(membership.role.id),
            "name": membership.role.name,
            "can_manage_org": membership.role.can_manage_org,
            "can_manage_users": membership.role.can_manage_users,
            "can_manage_coa": membership.role.can_manage_coa,
            "can_create_invoices": membership.role.can_create_invoices,
            "can_approve_invoices": membership.role.can_approve_invoices,
            "can_void_invoices": membership.role.can_void_invoices,
            "can_create_journals": membership.role.can_create_journals,
            "can_manage_banking": membership.role.can_manage_banking,
            "can_file_gst": membership.role.can_file_gst,
            "can_view_reports": membership.role.can_view_reports,
            "can_export_data": membership.role.can_export_data,
        },
        "is_default": membership.is_default,
    }
    for membership in user_orgs
]

return Response(
    {
        "user": UserProfileSerializer(user).data,
        "organisations": organisations_data,
        "access": tokens["access"],
    }
)
```

**Option B:** Modify frontend to match backend response (ALTERNATIVE)

**File:** `apps/web/src/providers/auth-provider.tsx`  
**Lines 127-148`

**Change:**
```typescript
const login = async (email: string, password: string) => {
  const response = await api.post<{
    user: User;
    tokens: {
      access: string;
      refresh: string;
      access_expires: string;
    };
  }>(endpoints.auth.login, { email, password });
  
  setAccessToken(response.tokens.access);
  setUser(response.user);
  
  // Fetch organisations separately
  const orgsData = await api.get<UserOrganisation[]>(
    endpoints.organisations.list
  );
  setOrganisations(orgsData);
  
  // Set default org
  const defaultOrg = orgsData.find((uo) => uo.is_default);
  if (defaultOrg) {
    setCurrentOrgId(defaultOrg.org.id);
  } else if (orgsData.length > 0) {
    setCurrentOrgId(orgsData[0].org.id);
  }
  
  queryClient.invalidateQueries();
};
```

**DECISION:** Use **Option B** (frontend modification) because:
1. Avoids backend API contract changes
2. Follows existing backend pattern (login returns tokens, separate call for orgs)
3. Less risk of breaking existing backend tests
4. Matches `checkSession()` implementation

### Step 2.2: Modify Login Page

**File:** `apps/web/src/app/(auth)/login/page.tsx`

**Changes Required:**

#### 2.2.1: Import useAuth hook
```typescript
// Line 6: Add import
import { useAuth } from "@/providers/auth-provider";
```

#### 2.2.2: Use AuthProvider in component
```typescript
// Line 22: Add after const router = useRouter();
const { login } = useAuth();
```

#### 2.2.3: Replace simulated login with actual API call
```typescript
// Lines 24-34: Replace handleSubmit
const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
  e.preventDefault();
  setIsSubmitting(true);
  setError(null);
  
  const formData = new FormData(e.currentTarget);
  const email = formData.get('email') as string;
  const password = formData.get('password') as string;
  
  try {
    await login(email, password);
    
    // Check for redirect parameter
    const params = new URLSearchParams(window.location.search);
    const redirect = params.get('redirect') || '/dashboard';
    
    router.push(redirect);
  } catch (err) {
    // Handle API errors
    const errorMessage = err instanceof Error 
      ? err.message 
      : 'Invalid email or password. Please try again.';
    setError(errorMessage);
  } finally {
    setIsSubmitting(false);
  }
};
```

#### 2.2.4: Handle specific error codes
```typescript
import { ApiError } from "@/lib/api-client";

// In handleSubmit catch block:
catch (err) {
  if (err instanceof ApiError) {
    // Map backend error codes to user-friendly messages
    switch (err.status) {
      case 401:
        setError('Invalid email or password. Please try again.');
        break;
      case 429:
        setError('Too many login attempts. Please wait and try again later.');
        break;
      default:
        setError(err.message || 'An error occurred. Please try again.');
    }
  } else {
    setError('Unable to connect to server. Please check your connection.');
  }
} finally {
  setIsSubmitting(false);
}
```

### Step 2.3: Update api-client Error Handling

**File:** `apps/web/src/lib/api-client.ts`  
**Lines 91-99:** Ensure ApiError is properly thrown

```typescript
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      errorData.message || errorData.detail || errorData.error?.message || `Request failed: ${response.statusText}`,
      errorData.errors || errorData.error?.details
    );
  }
  
  if (response.status === 204) {
    return {} as T;
  }
  
  return response.json();
}
```

**Validation:** Ensure error structure matches backend:
```json
// Backend error response
{
  "error": {
    "code": "invalid_credentials",
    "message": "Invalid email or password."
  }
}

// ApiError should extract message from error.message path
```

### Validation Criteria

**Manual Testing:**
```bash
# 1. Visit http://localhost:3000/login
# 2. Enter test credentials:
#    - Email: test@example.com
#    - Password: testpassword123
# 3. Click "Sign In"
# 4. Expected: Redirect to /dashboard
# 5. Expected: Dashboard shows organisation data
```

**Test Cases:**
- [ ] Valid credentials → redirect to dashboard
- [ ] Invalid credentials → show error message
- [ ] Network error → show connection error
- [ ] Rate limit exceeded → show rate limit message
- [ ] Redirect parameter preserved → redirect to intended page after login

**Success Criteria:**
- [ ] Login form calls backend API
- [ ] JWT tokens stored correctly (access in memory, refresh in HttpOnly cookie)
- [ ] User state updated in AuthProvider
- [ ] Organisations loaded and default set
- [ ] Redirect to dashboard (or intended page)
- [ ] Error messages user-friendly and localized

---

## PHASE 3: Authentication Guard (HIGH PRIORITY)

### Objective
Add route guard to prevent unauthenticated access to dashboard routes.

### Codebase Alignment Validation

**File:** `apps/web/src/app/(dashboard)/layout.tsx`

**Current Implementation:**
```typescript
"use client";

import { Shell } from "@/components/layout/shell";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <Shell>{children}</Shell>;
}
```

**ISSUE:** No authentication check before rendering.

### Implementation Steps

#### Step 3.1: Add Authentication Check to Layout

**File:** `apps/web/src/app/(dashboard)/layout.tsx`

**Required Implementation:**
```typescript
"use client";

import { useAuth } from "@/providers/auth-provider";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Shell } from "@/components/layout/shell";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  
  useEffect(() => {
    setMounted(true);
  }, []);
  
  useEffect(() => {
    // Only redirect after initial loading is complete
    if (mounted && !isLoading && !isAuthenticated) {
      const currentPath = window.location.pathname;
      router.push(`/login?redirect=${encodeURIComponent(currentPath)}`);
    }
  }, [mounted, isLoading, isAuthenticated, router]);
  
  // Show loading state during auth check
  if (!mounted || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-void">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-primary"></div>
      </div>
    );
  }
  
  // Don't render children if not authenticated
  if (!isAuthenticated) {
    return null;
  }
  
  return <Shell>{children}</Shell>;
}
```

**Rationale:**
- Check authentication before rendering protected content
- Use `mounted` state to prevent hydration mismatch
- Preserve intended destination via redirect parameter
- Show loading spinner during auth check
- Return `null` instead of flash of content

#### Step 3.2: Alternative - Middleware Guard (Server-Side)

**File:** `apps/web/src/middleware.ts`

**Enhancement:** Add authentication check to existing middleware

```typescript
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const response = NextResponse.next();
  
  // Check if accessing protected route
  const isProtectedRoute = request.nextUrl.pathname.startsWith('/dashboard') ||
                           request.nextUrl.pathname.startsWith('/invoices') ||
                           request.nextUrl.pathname.startsWith('/quotes') ||
                           request.nextUrl.pathname.startsWith('/ledger') ||
                           request.nextUrl.pathname.startsWith('/banking') ||
                           request.nextUrl.pathname.startsWith('/reports') ||
                           request.nextUrl.pathname.startsWith('/settings');
  
  // Check for refresh token cookie
  const refreshToken = request.cookies.get('refresh_token');
  
  if (isProtectedRoute && !refreshToken) {
    // Redirect to login with return URL
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', request.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }
  
  // Apply security headers (existing code)
  const securityHeaders = {
    // ... existing headers ...
  };
  
  Object.entries(securityHeaders).forEach(([key, value]) => {
    response.headers.set(key, value);
  });
  
  return response;
}
```

**ISSUE:** Middleware runs server-side and can't check in-memory access token. Only refresh token cookie is available.

**Backend Cookie Configuration:**

Need to verify if backend sets refresh token as HttpOnly cookie. Check:

**File:** `apps/backend/config/settings/base.py`

Search for cookie settings in JWT configuration:
```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    # Cookie settings for refresh token
    'AUTH_COOKIE': 'refresh_token',
    'AUTH_COOKIE_SECURE': True,
    'AUTH_COOKIE_HTTP_ONLY': True,
    'AUTH_COOKIE_SAME_SITE': 'Lax',
    'AUTH_COOKIE_PATH': '/',
}
```

**Validation Required:** Check if backend actually sets cookies or returns tokens in response body.

**Current Implementation Check:**

Let me verify the backend authentication service implementation:

From `apps/backend/apps/core/services/auth_service.py`:
- Line 76: `tokens = generate_tokens(user)`
- Lines 107-111: Returns `{ "access": ..., "refresh": ..., "access_expires": ... }`

**FINDING:** Backend returns tokens in response body, NOT as HttpOnly cookies!

**Implication:**
- Frontend stores refresh token in memory (not ideal)
- Middleware cannot check refresh token cookie
- **Cannot use middleware-based auth guard**

**Alternative Solution:** Use client-side auth guard only (Phase 3.1)

**RECOMMENDATION:** Implement HttpOnly cookie for refresh token (future enhancement, outside scope of this plan).

### Validation Criteria

**Manual Testing:**
```bash
# 1. Clear all cookies and localStorage
# 2. Visit http://localhost:3000/dashboard/
# 3. Expected: Redirect to /login
# 4. Login with valid credentials
# 5. Expected: Redirect back to /dashboard
# 6. Refresh page
# 7. Expected: Dashboard loads (authenticated)
```

**Test Cases:**
- [ ] Unauthenticated access to /dashboard → redirect to /login
- [ ] Unauthenticated access to /invoices → redirect to /login
- [ ] Login with redirect parameter → redirect to intended page
- [ ] Authenticated access to /dashboard → render dashboard
- [ ] Refresh authenticated page → stay authenticated

**Success Criteria:**
- [ ] Protected routes inaccessible without authentication
- [ ] Redirect to login preserves intended destination
- [ ] No flash of protected content
- [ ] Loading state shown during auth check
- [ ] No hydration mismatch errors

---

## PHASE 4: Error Message Differentiation (MEDIUM PRIORITY)

### Objective
Differentiate between "authenticated but no organisation" and "not authenticated" states in DashboardClient.

### Codebase Alignment Validation

**File:** `apps/web/src/app/(dashboard)/dashboard/dashboard-client.tsx`

**Current Implementation (Lines 72-94):**
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

**ISSUE:** Shows same message for both:
1. Authenticated user with no organisation
2. Unauthenticated user (should have been redirected in Phase 1)

### Implementation Steps

#### Step 4.1: Check Authentication State Before Organisation

**File:** `apps/web/src/app/(dashboard)/dashboard/dashboard-client.tsx`

**Required Implementation:**
```typescript
import { useAuth } from "@/providers/auth-provider";

export function DashboardClient() {
  const { currentOrg, isLoading: authLoading, isAuthenticated } = useAuth();
  
  const orgId = currentOrg?.id;
  
  // ... useQuery setup ...
  
  // Check auth loading first
  if (authLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin text-accent-primary" />
      </div>
    );
  }
  
  // Check if authenticated (should not reach here if Phase 1 implemented correctly)
  if (!isAuthenticated) {
    // This should not happen if AuthProvider redirect is working
    // But handle gracefully as fallback
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
  
  // Now check for organisation (authenticated but no org)
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

**Rationale:**
- Check `isAuthenticated` before checking `orgId`
- Show different messages for different states
- Provide actionable buttons (Go to Login vs Create Organisation)
- Use different icon colors (alert for auth, warning for org)

### Validation Criteria

**Test Scenarios:**

1. **Unauthenticated User:**
   - Should be redirected to /login by Phase 1
   - If reaches dashboard, should see "Authentication Required" with "Go to Login" button

2. **Authenticated User, No Organisation:**
   - Should see "No Organisation Selected"
   - Should see "Create Organisation" button
   - Should be able to create new organisation

3. **Authenticated User, Has Organisation:**
   - Should see dashboard content
   - Should display organisation data

**Success Criteria:**
- [ ] Unauthenticated users see auth error (or redirected)
- [ ] Authenticated users without org see org creation prompt
- [ ] Different messages for different states
- [ ] Actionable buttons available

---

## PHASE 5: End-to-End Testing & Documentation (REQUIRED)

### Objective
Create comprehensive automated tests and update documentation.

### Implementation Steps

#### Step 5.1: Create Playwright Authentication Tests

**File:** `apps/web/tests/e2e/auth-flow.spec.ts` (NEW)

```typescript
import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('redirects unauthenticated users to login', async ({ page }) => {
    // Clear cookies
    await page.context().clearCookies();
    
    // Try to access dashboard
    await page.goto('http://localhost:3000/dashboard/');
    
    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
    
    // Should show login form
    await expect(page.locator('h2:has-text("LEDGERSG")')).toBeVisible();
    await expect(page.locator('input[name="email"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
  });
  
  test('login with valid credentials', async ({ page }) => {
    await page.goto('http://localhost:3000/login');
    
    // Fill login form
    await page.locator('input[name="email"]').fill('test@example.com');
    await page.locator('input[name="password"]').fill('testpassword123');
    
    // Submit form
    await page.locator('button[type="submit"]').click();
    
    // Should redirect to dashboard
    await expect(page).toHaveURL(/\/dashboard/);
    
    // Should show dashboard content
    await expect(page.locator('h1:has-text("Command Center")')).toBeVisible();
  });
  
  test('login with invalid credentials', async ({ page }) => {
    await page.goto('http://localhost:3000/login');
    
    // Fill login form with invalid credentials
    await page.locator('input[name="email"]').fill('invalid@example.com');
    await page.locator('input[name="password"]').fill('wrongpassword');
    
    // Submit form
    await page.locator('button[type="submit"]').click();
    
    // Should show error message
    await expect(page.locator('text=Invalid email or password')).toBeVisible();
    
    // Should stay on login page
    await expect(page).toHaveURL(/\/login/);
  });
  
  test('preserves redirect after login', async ({ page }) => {
    // Clear cookies
    await page.context().clearCookies();
    
    // Try to access protected route
    await page.goto('http://localhost:3000/invoices/');
    
    // Should redirect to login with redirect parameter
    await expect(page).toHaveURL(/\/login\?redirect=%2Finvoices/);
    
    // Login
    await page.locator('input[name="email"]').fill('test@example.com');
    await page.locator('input[name="password"]').fill('testpassword123');
    await page.locator('button[type="submit"]').click();
    
    // Should redirect to intended route
    await expect(page).toHaveURL(/\/invoices/);
  });
  
  test('logout clears session', async ({ page }) => {
    // Login first
    await page.goto('http://localhost:3000/login');
    await page.locator('input[name="email"]').fill('test@example.com');
    await page.locator('input[name="password"]').fill('testpassword123');
    await page.locator('button[type="submit"]').click();
    
    await expect(page).toHaveURL(/\/dashboard/);
    
    // Logout (assuming there's a logout button)
    await page.locator('button[aria-label="Logout"]').click();
    
    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
    
    // Try to access dashboard
    await page.goto('http://localhost:3000/dashboard/');
    
    // Should redirect back to login
    await expect(page).toHaveURL(/\/login/);
  });
});
```

#### Step 5.2: Create Backend Integration Tests

**File:** `apps/backend/tests/integration/test_login_response.py` (MODIFY EXISTING)

```python
import pytest
from django.urls import reverse
from rest_framework import status
from apps.core.models import AppUser, UserOrganisation, Organisation

@pytest.mark.django_db
def test_login_returns_organisations(api_client, test_user):
    """Test that login response includes user's organisations."""
    # Create organisation and membership
    org = Organisation.objects.create(
        name="Test Org",
        entity_type="PRIVATE_LIMITED",
        gst_registered=True,
    )
    
    UserOrganisation.objects.create(
        user=test_user,
        org=org,
        role_id="some-role-uuid",  # Need actual role
        is_default=True,
        accepted_at=timezone.now(),
    )
    
    url = "/api/v1/auth/login/"
    data = {
        "email": test_user.email,
        "password": "testpassword123"
    }
    
    response = api_client.post(url, data, format="json")
    
    assert response.status_code == status.HTTP_200_OK
    assert "user" in response.data
    assert "organisations" in response.data
    assert "access" in response.data
    assert len(response.data["organisations"]) == 1
    assert response.data["organisations"][0]["org"]["name"] == "Test Org"

@pytest.mark.django_db
def test_login_user_without_organisations(api_client, test_user):
    """Test login for user with no organisations."""
    url = "/api/v1/auth/login/"
    data = {
        "email": test_user.email,
        "password": "testpassword123"
    }
    
    response = api_client.post(url, data, format="json")
    
    assert response.status_code == status.HTTP_200_OK
    assert "organisations" in response.data
    assert len(response.data["organisations"]) == 0
```

#### Step 5.3: Update AGENTS.md Documentation

**File:** `/home/project/Ledger-SG/AGENTS.md`

**Add Section:** Authentication Flow Documentation

```markdown
### 6.3 Authentication Flow (Updated 2026-03-07)

**Authentication Architecture:**
- Frontend: AuthProvider (React Context) + JWT tokens
- Backend: Django REST Framework + SimpleJWT
- Token Storage: Access token in memory, Refresh token in HttpOnly cookie (FUTURE)
- Session Management: 15-minute access tokens, 7-day refresh tokens

**Authentication Flow:**

```
Unauthenticated User Flow:
1. User visits /dashboard/
2. AuthProvider.checkSession() calls /api/v1/auth/me/
3. Backend returns 401 (no valid token)
4. AuthProvider catches error and redirects to /login
5. User sees login form

Login Flow:
1. User enters credentials
2. Login page calls AuthProvider.login(email, password)
3. AuthProvider calls /api/v1/auth/login/
4. Backend validates credentials and returns:
   - user: { id, email, full_name, ... }
   - organisations: [ { id, org, role, is_default }, ... ]
   - access: "JWT_ACCESS_TOKEN"
5. AuthProvider stores access token in memory
6. AuthProvider sets user state
7. AuthProvider fetches organisations (if not in response)
8. AuthProvider redirects to intended destination

Authenticated User Flow:
1. User visits /dashboard/
2. AuthProvider.checkSession() calls /api/v1/auth/me/
3. Backend returns 200 OK with user data
4. AuthProvider sets user state
5. AuthProvider fetches organisations
6. Dashboard renders with organisation context

Logout Flow:
1. User clicks logout button
2. AuthProvider.logout() calls /api/v1/auth/logout/
3. Backend blacklists refresh token
4. AuthProvider clears all state
5. AuthProvider redirects to /login
```

**Protected Routes:**
- `/dashboard` - Dashboard overview
- `/invoices` - Invoice management
- `/quotes` - Quote management
- `/ledger` - Journal entries
- `/banking` - Bank reconciliation
- `/reports` - Financial reports
- `/settings` - Organisation settings

**Route Guard Implementation:**
- Client-side: DashboardLayout checks `isAuthenticated`
- Redirect to `/login?redirect={currentPath}` if not authenticated
- Server-side: FUTURE - Middleware checks refresh_token cookie

**Error Handling:**
- 401 Unauthorized → Redirect to login
- 403 Forbidden → Show permission error
- 429 Rate Limited → Show rate limit message
- Network Error → Show connection error
```

#### Step 5.4: Create Test User Seed Script

**File:** `apps/backend/scripts/seed_test_user.py` (NEW)

```python
"""
Seed script for creating test user with organisation.
Used for development and testing.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
sys.path.insert(0, '/home/project/Ledger-SG/apps/backend')
django.setup()

from apps.core.models import AppUser, Organisation, UserOrganisation, Role
from apps.core.services import auth_service

def seed_test_user():
    """Create test user with default organisation."""
    
    # Check if test user already exists
    if AppUser.objects.filter(email='test@example.com').exists():
        print("Test user already exists")
        user = AppUser.objects.get(email='test@example.com')
    else:
        # Create test user
        user = auth_service.register_user(
            email='test@example.com',
            password='testpassword123',  # Min 12 chars
            full_name='Test User',
        )
        print(f"Created test user: {user.email}")
    
    # Check if test organisation exists
    org, created = Organisation.objects.get_or_create(
        name='Test Organisation',
        defaults={
            'legal_name': 'Test Organisation Pte Ltd',
            'uen': '202603071ABC',
            'entity_type': 'PRIVATE_LIMITED',
            'gst_registered': True,
            'gst_reg_number': 'M90345678X',
            'gst_scheme': 'STANDARD',
            'gst_filing_frequency': 'QUARTERLY',
            'invoicenow_enabled': True,
            'fy_start_month': 1,
            'base_currency': 'SGD',
            'timezone': 'Asia/Singapore',
        }
    )
    
    if created:
        print(f"Created test organisation: {org.name}")
    else:
        print(f"Test organisation already exists: {org.name}")
    
    # Get or create default role
    role, created = Role.objects.get_or_create(
        name='Admin',
        defaults={
            'can_manage_org': True,
            'can_manage_users': True,
            'can_manage_coa': True,
            'can_create_invoices': True,
            'can_approve_invoices': True,
            'can_void_invoices': True,
            'can_create_journals': True,
            'can_manage_banking': True,
            'can_file_gst': True,
            'can_view_reports': True,
            'can_export_data': True,
        }
    )
    
    # Create user-organisation membership
    membership, created = UserOrganisation.objects.get_or_create(
        user=user,
        org=org,
        defaults={
            'role': role,
            'is_default': True,
            'accepted_at': timezone.now(),
        }
    )
    
    if created:
        print(f"Created membership: {user.email} -> {org.name}")
    else:
        print(f"Membership already exists: {user.email} -> {org.name}")
    
    print("\n=== Test Credentials ===")
    print(f"Email: {user.email}")
    print(f"Password: testpassword123")
    print(f"Organisation: {org.name}")
    print("========================\n")

if __name__ == '__main__':
    from django.utils import timezone
    seed_test_user()
```

**Usage:**
```bash
cd /home/project/Ledger-SG/apps/backend
source /opt/venv/bin/activate
python scripts/seed_test_user.py
```

#### Step 5.5: Update README.md

**File:** `/home/project/Ledger-SG/README.md`

**Add Section:** Authentication Testing

```markdown
### Testing Authentication

#### Create Test User

```bash
# Backend
cd apps/backend
source /opt/venv/bin/activate
python scripts/seed_test_user.py

# This creates:
# - Email: test@example.com
# - Password: testpassword123
# - Organisation: Test Organisation
```

#### Test Login Flow

```bash
# Start backend
cd apps/backend
python manage.py runserver

# Start frontend
cd apps/web
npm run dev

# Run E2E tests
npx playwright test tests/e2e/auth-flow.spec.ts
```

#### Manual Testing

1. **Test Redirect:**
   - Clear browser cookies
   - Visit http://localhost:3000/dashboard/
   - Expected: Redirect to /login

2. **Test Login:**
   - Enter: test@example.com
   - Enter: testpassword123
   - Click "Sign In"
   - Expected: Redirect to /dashboard

3. **Test Logout:**
   - Click logout button
   - Expected: Redirect to /login
   - Visit /dashboard/ again
   - Expected: Redirect to /login
```

### Validation Criteria

**Test Execution:**
```bash
# Frontend E2E tests
cd apps/web
npx playwright test tests/e2e/auth-flow.spec.ts

# Backend integration tests
cd apps/backend
source /opt/venv/bin/activate
pytest tests/integration/test_login_response.py -v
```

**Success Criteria:**
- [ ] All E2E tests pass
- [ ] All backend integration tests pass
- [ ] Test user can be created via seed script
- [ ] Documentation updated in AGENTS.md
- [ ] README includes testing instructions
- [ ] Root cause analysis document updated

---

## Phase Execution Order

### Recommended Execution Sequence

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: AuthProvider Redirect                              │
│ - Modify auth-provider.tsx                                  │
│ - Test redirect behavior                                    │
│ - Validation: Unauthenticated users redirect to login      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: Login Backend Integration                          │
│ - Modify AuthProvider.login() to match backend response     │
│ - Modify login page to use AuthProvider.login()             │
│ - Create test user seed script                              │
│ - Validation: Can login with valid credentials              │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: Authentication Guard                               │
│ - Add auth check to DashboardLayout                         │
│ - Test protected routes                                     │
│ - Validation: Protected routes inaccessible without auth    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4: Error Message Differentiation                      │
│ - Update DashboardClient to check isAuthenticated           │
│ - Add different error states                                │
│ - Validation: Correct messages for different states         │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 5: End-to-End Testing & Documentation                 │
│ - Create Playwright E2E tests                               │
│ - Update backend integration tests                          │
│ - Update AGENTS.md with auth flow                           │
│ - Update README with testing instructions                   │
│ - Validation: All tests pass, docs complete                 │
└─────────────────────────────────────────────────────────────┘
```

### Dependency Graph

```
Phase 1 ──→ Phase 3
    │           │
    ↓           ↓
Phase 2 ──────→ Phase 4
    │           │
    └───────────┴──→ Phase 5
```

**Critical Path:** Phase 1 → Phase 2 → Phase 5  
**Parallel Work:** Phase 3 and Phase 4 can be developed in parallel after Phase 1

---

## Risk Assessment

### High Risk Items

1. **Backend Response Structure Mismatch (Phase 2)**
   - **Risk:** Frontend expects different response structure
   - **Mitigation:** Use Option B (frontend modification) to avoid backend changes
   - **Impact:** Medium - requires frontend code changes but no backend API changes

2. **Redirect Loop (Phase 1)**
   - **Risk:** Redirect from /login to /login if AuthProvider redirects on all auth failures
   - **Mitigation:** Check `window.location.pathname` before redirecting
   - **Impact:** High - could render app unusable

3. **Test User Creation (Phase 5)**
   - **Risk:** Seed script fails due to missing Role model or other dependencies
   - **Mitigation:** Use get_or_create for all related models
   - **Impact:** Low - can manually create test user in admin

### Medium Risk Items

4. **Hydration Mismatch (Phase 3)**
   - **Risk:** Layout uses client-side auth check but renders server-side
   - **Mitigation:** Use `mounted` state to prevent hydration mismatch
   - **Impact:** Medium - causes console warnings but doesn't break functionality

5. **Token Refresh Logic (Phase 2)**
   - **Risk:** Current implementation expects organisations in login response
   - **Mitigation:** Fetch organisations separately after login
   - **Impact:** Low - adds one extra API call

### Low Risk Items

6. **Error Message Copy (Phase 4)**
   - **Risk:** Error messages not user-friendly
   - **Mitigation:** Follow existing error message patterns
   - **Impact:** Low - only affects UX, not functionality

---

## Rollback Plan

### Phase 1 Rollback
```typescript
// Revert auth-provider.tsx change
} catch {
  clearAuth();
  // Comment out redirect
  // router.push('/login');
}
```

### Phase 2 Rollback
```typescript
// Revert login page change
const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
  e.preventDefault();
  setIsSubmitting(true);
  setError(null);
  
  // Revert to simulation
  setTimeout(() => {
    setIsSubmitting(false);
    router.push("/dashboard");
  }, 1000);
};
```

### Phase 3 Rollback
```typescript
// Revert layout.tsx change
"use client";

import { Shell } from "@/components/layout/shell";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <Shell>{children}</Shell>;
}
```

### Phase 4 Rollback
```typescript
// Revert dashboard-client.tsx change
// Remove isAuthenticated check, keep only orgId check
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

---

## Success Metrics

### Phase 1 Success
- [ ] Unauthenticated users redirect to /login
- [ ] No redirect loops
- [ ] No console errors
- [ ] URL bar shows /login

### Phase 2 Success
- [ ] Login form calls backend API
- [ ] Valid credentials → dashboard access
- [ ] Invalid credentials → error message
- [ ] JWT tokens stored correctly

### Phase 3 Success
- [ ] Protected routes require authentication
- [ ] Redirect preserves intended destination
- [ ] No flash of protected content
- [ ] Loading state during auth check

### Phase 4 Success
- [ ] Different messages for different states
- [ ] Unauthenticated users see auth error
- [ ] Authenticated users without org see org creation prompt
- [ ] Actionable buttons available

### Phase 5 Success
- [ ] All E2E tests pass
- [ ] All backend tests pass
- [ ] Test user can be created
- [ ] Documentation complete
- [ ] README updated

---

## Timeline Estimate

**Phase 1:** 30 minutes (modify, test, validate)  
**Phase 2:** 1 hour (modify AuthProvider + login page + test)  
**Phase 3:** 30 minutes (modify layout + test)  
**Phase 4:** 30 minutes (modify DashboardClient + test)  
**Phase 5:** 1.5 hours (E2E tests + backend tests + docs)

**Total:** 4 hours

**Critical Path:** 3 hours (Phase 1 → Phase 2 → Phase 5)

---

## Post-Implementation Verification

### Final Checklist

After all phases are complete, perform end-to-end verification:

1. **Clear Browser State**
   ```bash
   # Clear all cookies, localStorage, sessionStorage
   ```

2. **Test Unauthenticated Flow**
   - Visit /dashboard/ → should redirect to /login
   - Visit /invoices/ → should redirect to /login
   - URL should preserve redirect parameter

3. **Test Login Flow**
   - Enter valid credentials → should redirect to dashboard
   - Enter invalid credentials → should show error
   - Test rate limiting (10 attempts quickly)

4. **Test Authenticated Flow**
   - Navigate between protected routes
   - Refresh page → should stay authenticated
   - Check organisation selector works

5. **Test Logout Flow**
   - Click logout → should redirect to /login
   - Try to access /dashboard/ → should redirect to /login

6. **Test Error States**
   - Disconnect backend → should show connection error
   - Use expired token → should redirect to login
   - User with no organisation → should show org creation prompt

7. **Run All Tests**
   ```bash
   # Frontend tests
   npm test
   npx playwright test
   
   # Backend tests
   pytest --reuse-db --no-migrations
   ```

8. **Update Documentation**
   - AGENTS.md updated
   - README updated
   - Root cause analysis updated

---

## Conclusion

This remediation plan provides a comprehensive, phase-by-phase approach to fixing the authentication flow in LedgerSG. Each phase builds on the previous one, with clear validation criteria and rollback plans.

**Key Principles:**
- ✅ Minimal backend changes (frontend-first approach)
- ✅ Backward compatible (existing functionality preserved)
- ✅ Well-tested (E2E + integration tests)
- ✅ Documented (AGENTS.md + README)
- ✅ Rollback-ready (each phase can be reverted)

**Next Action:** Begin Phase 1 implementation after plan approval.

---

**Plan Created:** 2026-03-07  
**Plan Version:** 1.0  
**Estimated Completion:** 4 hours  
**Ready for Execution:** ✅ YES
