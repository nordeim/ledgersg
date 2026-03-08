# Backend Auth/CORS Issue - Root Cause Analysis & Remediation Plan

**Date:** 2026-03-07  
**Issue:** Dashboard shows "No Organisation Selected" due to CORS authentication failure  
**Severity:** HIGH - Production Blocking  
**Status:** 🔴 **ROOT CAUSE IDENTIFIED**

---

## 🔍 Executive Summary

The dashboard fails to load organization context because **CORS preflight requests are rejected with 401 Unauthorized** before the CORS middleware can respond. This prevents the frontend from fetching `/api/v1/auth/me/`, which provides user and organization data needed for the dashboard.

---

## 📊 Evidence

### 1. Browser Console Error

```
CONSOLE: error Access to fetch at 'http://localhost:8000/api/v1/auth/me/' from origin 
'http://localhost:3000' has been blocked by CORS policy: Response to preflight request 
doesn't pass access control check: No 'Access-Control-Allow-Origin' header is present on 
the requested resource.
```

### 2. Playwright Investigation

```
⚠️  FOUND: No Organisation Selected
⚠️  'No Organisation Selected' message present
REQUESTS LOG: GET http://localhost:8000/api/v1/auth/me/
```

### 3. Direct Testing

```bash
$ curl -X OPTIONS http://localhost:8000/api/v1/auth/me/ \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET"
HTTP/1.1 401 Unauthorized
# ❌ No CORS headers returned
```

### 4. Current State

- **Frontend:** ✅ CSP fixed, dashboard UI renders
- **Backend:** ❌ CORS preflight fails with 401
- **Auth Flow:** ❌ Cannot fetch user/organization data
- **Dashboard:** ⚠️ Shows "No Organisation Selected"

---

## 🎯 Root Cause Analysis

### Primary Issue: Middleware Order + Auth Blocking Preflight

**Problem Chain:**

1. **Browser sends OPTIONS preflight** to `/api/v1/auth/me/`
2. **Request passes through middleware stack:**
   - SecurityMiddleware (position 1)
   - CSPMiddleware (position 2)
   - WhiteNoiseMiddleware (position 3)
   - **CorsMiddleware (position 4)** ← Should be at position 2
   - SessionMiddleware (position 5)
   - AuthenticationMiddleware (position 8)
3. **AuthenticationMiddleware checks for auth token** (none in OPTIONS request)
4. **DRF permission_classes([IsAuthenticated])** decorator validates
5. **Request rejected with 401 BEFORE CorsMiddleware can respond**
6. **Result:** No CORS headers, browser blocks actual request

**Technical Detail:**

```python
# apps/core/views/auth.py (line ~80)
@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])  # ← Blocks OPTIONS without credentials
def me_view(request: Request) -> Response:
    """Get or update current user profile."""
    if request.method == "GET":
        return Response(UserProfileSerializer(request.user).data)
```

**Why This Breaks:**

- OPTIONS requests don't include auth tokens (by design)
- DRF's `IsAuthenticated` permission rejects OPTIONS
- CORS middleware never gets to add headers
- Browser sees 401 without CORS headers → blocks request

---

### Secondary Issue: Missing CORS_PREFLIGHT settings

**Missing Configuration:**

```python
# config/settings/base.py (current)
CORS_ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
CORS_ALLOW_CREDENTIALS = True

# MISSING - Need these:
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
CORS_ALLOW_HEADERS = ["content-type", "authorization"]
CORS_PREFLIGHT_MAX_AGE = 86400
```

---

## 🔧 Remediation Plan

### Solution Strategy: Fix Middleware Order + Add CORS Preflight Support

**Principle:** CORS middleware must process preflight requests BEFORE authentication checks

---

### Phase 1: Fix Middleware Order (CRITICAL)

**File:** `/home/project/Ledger-SG/apps/backend/config/settings/base.py`

**Current (WRONG):**
```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",  # Position 1
    "csp.middleware.CSPMiddleware",                    # Position 2 ← Blocks CORS
    "whitenoise.middleware.WhiteNoiseMiddleware",      # Position 3
    "corsheaders.middleware.CorsMiddleware",           # Position 4 ← TOO LATE
    "django.contrib.sessions.middleware.SessionMiddleware",
    ...
]
```

**Fixed (CORRECT):**
```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",  # Position 1
    "corsheaders.middleware.CorsMiddleware",           # Position 2 ← MOVED UP
    "csp.middleware.CSPMiddleware",                    # Position 3
    "whitenoise.middleware.WhiteNoiseMiddleware",      # Position 4
    "django.contrib.sessions.middleware.SessionMiddleware",
    ...
]
```

**Why This Works:**

1. CorsMiddleware intercepts OPTIONS requests
2. Returns 200 with CORS headers (no auth check)
3. Browser receives CORS headers, allows actual request
4. Actual GET/POST request includes auth token → succeeds

---

### Phase 2: Add CORS Preflight Configuration (HIGH PRIORITY)

**File:** `/home/project/Ledger-SG/apps/backend/config/settings/base.py`

**Add after CORS_ALLOW_CREDENTIALS (line ~298):**

```python
# =============================================================================
# CORS CONFIGURATION
# =============================================================================

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
    cast=Csv(),
)

CORS_ALLOW_CREDENTIALS = True

# Preflight configuration
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

CORS_PREFLIGHT_MAX_AGE = 86400  # 24 hours
```

---

### Phase 3: Handle OPTIONS in Auth Views (ALTERNATIVE - If Phase 1 insufficient)

**File:** `/home/project/Ledger-SG/apps/backend/apps/core/views/auth.py`

**Add OPTIONS handling:**

```python
@api_view(["GET", "PATCH", "OPTIONS"])  # ← Add OPTIONS
@permission_classes([IsAuthenticated])  # ← This will still block OPTIONS
def me_view(request: Request) -> Response:
    """Get or update current user profile."""
    # Handle OPTIONS preflight
    if request.method == "OPTIONS":
        return Response(status=200)  # ← CORS middleware adds headers
    
    if request.method == "GET":
        return Response(UserProfileSerializer(request.user).data)
    
    # PATCH - update profile
    serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)
```

**Alternative: Use AllowAny for OPTIONS:**

```python
from rest_framework.permissions import AllowAny

@api_view(["GET", "PATCH", "OPTIONS"])
@permission_classes([IsAuthenticated])
def me_view(request: Request) -> Response:
    # OPTIONS requests should bypass authentication
    if request.method == "OPTIONS":
        return Response(status=200)
    
    if request.method == "GET":
        return Response(UserProfileSerializer(request.user).data)
    # ... rest of view
```

**BETTER APPROACH: Use custom permission class**

```python
from rest_framework import permissions

class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    Allow OPTIONS requests (preflight), require authentication for others.
    """
    def has_permission(self, request, view):
        if request.method == "OPTIONS":
            return True  # Allow preflight without auth
        return request.user and request.user.is_authenticated

@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticatedOrReadOnly])
def me_view(request: Request) -> Response:
    # ... view code
```

---

## 📝 Implementation Steps

### Step 1: Fix Middleware Order (REQUIRED)

```bash
# File: config/settings/base.py
# Move CorsMiddleware to position 2 (after SecurityMiddleware)
```

### Step 2: Add CORS Configuration (REQUIRED)

```bash
# File: config/settings/base.py
# Add CORS_ALLOW_METHODS, CORS_ALLOW_HEADERS, CORS_PREFLIGHT_MAX_AGE
```

### Step 3: Restart Backend

```bash
# Kill existing backend
pkill -f "python manage.py runserver"

# Start with development settings
source /opt/venv/bin/activate
DJANGO_SETTINGS_MODULE=config.settings.development python manage.py runserver 0.0.0.0:8000
```

### Step 4: Test CORS Preflight

```bash
# Test OPTIONS request
curl -X OPTIONS http://localhost:8000/api/v1/auth/me/ \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -v 2>&1 | grep -E "HTTP|Access-Control"

# Expected:
# HTTP/1.1 200 OK
# Access-Control-Allow-Origin: http://localhost:3000
# Access-Control-Allow-Methods: GET, PATCH, OPTIONS
# Access-Control-Allow-Headers: authorization, content-type
# Access-Control-Allow-Credentials: true
```

### Step 5: Test with Playwright

```bash
source /opt/venv/bin/activate
python /tmp/playwright_dashboard_test.py

# Expected:
# ✅ No loading spinner
# ✅ No "No Organisation Selected" message
# ✅ Dashboard loads with organization data
```

---

## 🧪 Verification Checklist

### Before Fix

- [x] OPTIONS request returns 401
- [x] No CORS headers in response
- [x] Dashboard shows "No Organisation Selected"
- [x] Browser console: CORS policy blocked

### After Fix

- [ ] OPTIONS request returns 200
- [ ] Response includes Access-Control-Allow-Origin header
- [ ] Dashboard shows organization data
- [ ] Browser console: No CORS errors
- [ ] Auth flow completes successfully

---

## 🎓 Technical Details

### CORS Preflight Flow

**Normal Flow (CORRECT):**
```
Browser                Django
  |                      |
  |--- OPTIONS --------> | (no auth)
  |                      |
  |<-- 200 + CORS ----- | CorsMiddleware responds
  |                      |
  |--- GET + Auth -----> | (with token)
  |                      |
  |<-- 200 + Data ------ | View responds
```

**Broken Flow (CURRENT):**
```
Browser                Django
  |                      |
  |--- OPTIONS --------> | (no auth)
  |                      |
  |                      | AuthenticationMiddleware
  |                      | checks auth → FAILS
  |                      |
  |<-- 401 ------------ | Rejected before CorsMiddleware
  |                      |
  |--- BLOCKED --------- | Browser blocks actual request
```

### Middleware Order Best Practices

**Correct Order (Django):**
1. SecurityMiddleware (adds security headers)
2. **CorsMiddleware** (handle CORS preflight)
3. SessionMiddleware
4. AuthenticationMiddleware
5. Other middleware

**Why Order Matters:**
- Each middleware processes request in order
- AuthenticationMiddleware adds `request.user`
- If user not authenticated → 401 before CORS
- CORS must be earlier to respond to OPTIONS

---

## 🚨 Known Issues After Fix

### Issue 1: User Not Logged In

**Problem:** Even with CORS fixed, if user has no auth token, dashboard still shows "No Organisation"

**Solution:** Implement proper login flow or use demo user

### Issue 2: Demo Mode vs Real Auth

**Problem:** Frontend may expect demo user but backend requires real auth

**Solution:** Either:
1. Add demo user endpoint
2. Implement proper login flow
3. Use server-side session auth

---

## 📚 References

1. **Django CORS Headers:** https://pypi.org/project/django-cors-headers/
2. **CORS Preflight:** https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS#preflighted_requests
3. **DRF Permissions:** https://www.django-rest-framework.org/api-guide/permissions/
4. **Middleware Order:** https://docs.djangoproject.com/en/4.2/topics/http/middleware/#middleware-ordering

---

## 🎯 Priority

**CRITICAL** - Production blocking issue

**Must Fix:** Dashboard cannot load organization data without CORS fix

---

## ✅ Success Criteria

1. OPTIONS requests return 200 with CORS headers
2. GET requests include auth token and return user data
3. Dashboard displays organization information
4. No CORS errors in browser console
5. Dashboard fully functional

---

**Status:** 🟡 Ready for Implementation  
**Estimated Fix Time:** 10 minutes  
**Risk:** LOW (configuration change only)
