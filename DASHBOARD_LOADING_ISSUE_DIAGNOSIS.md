# Dashboard Loading Issue - Root Cause Analysis

**Date:** 2026-03-07  
**Issue:** Dashboard hangs at "Loading" spinner  
**Severity:** HIGH - Production Blocking  
**Status:** 🔴 **ROOT CAUSE IDENTIFIED**

---

## 🔍 Executive Summary

The dashboard fails to load due to **Content Security Policy (CSP) blocking inline scripts**. The frontend middleware is incorrectly configuring CSP with both a nonce and `'unsafe-inline'`, which causes browsers to ignore `'unsafe-inline'` and block Next.js's required inline scripts.

---

## 📊 Evidence

### 1. Browser Console Errors

```
BROWSER CONSOLE: error Executing inline script violates the following Content Security Policy directive 
'script-src 'self' 'unsafe-eval' 'nonce-ZDkwYjcyN2YtNDUxNC00YWRkLTg4MzctNTU1OGIzNjk1ZGQy' 
'unsafe-inline' https://vercel.live'. Note that 'unsafe-inline' is ignored if either a hash or nonce 
value is present in the source list. The action has been blocked.
```

**Repeated:** 6 times (one for each inline script)

### 2. CSP Header Analysis

**Current CSP Header:**
```
script-src 'self' 'unsafe-eval' 'nonce-XXX' 'unsafe-inline' https://vercel.live
```

**Problem:** 
- CSP specification: When nonce is present, `'unsafe-inline'` is **completely ignored**
- Next.js requires `'unsafe-inline'` for its inline scripts (React 19, Next.js 16)
- The nonce prevents Next.js scripts from executing

### 3. Playwright Test Results

```
⚠️  LOADING SPINNER STILL VISIBLE - Dashboard not loaded
Page title: LedgerSG — IRAS-Compliant Accounting for Singapore SMBs
```

### 4. Backend Status

```
HTTP/1.1 401 Unauthorized
Backend: http://localhost:8000
```

**Note:** Backend auth issue is secondary - the dashboard should handle this gracefully, but CSP blocks the client-side JavaScript that would handle auth.

---

## 🎯 Root Cause

**File:** `/home/project/Ledger-SG/apps/web/src/middleware.ts`  
**Line:** 63

```typescript
// INCORRECT - Line 63
.replace("'unsafe-inline'", `'nonce-${nonce}' 'unsafe-inline'`);
```

**Why This Breaks:**

1. CSP spec: If nonce OR hash present, `'unsafe-inline'` is ignored
2. Next.js 16 + React 19 requires `'unsafe-inline'` for inline scripts
3. The middleware generates a nonce, which makes `'unsafe-inline'` ineffective
4. Result: All Next.js inline scripts are blocked → Dashboard hangs

---

## 🔧 Solution

### Option 1: Remove Nonce, Keep 'unsafe-inline' (RECOMMENDED)

**Pros:**
- Fixes the issue immediately
- Compatible with Next.js 16 + React 19
- Simpler configuration
- Works in development and production

**Cons:**
- Slightly less secure (but necessary for Next.js)
- Inline scripts allowed globally

**Implementation:**

```typescript
// File: src/middleware.ts
// REMOVE lines 58-63 (nonce generation)
// REPLACE line 68 with:
"Content-Security-Policy": buildCSP(),

// Update cspDirectives (lines 18-23):
"script-src": [
  "'self'",
  "'unsafe-eval'", // Required for Next.js 16 + React 19
  "'unsafe-inline'", // Required for Next.js inline scripts
  "https://vercel.live", // Vercel Live feedback
],
```

### Option 2: Use Nonce-Only (More Secure, Complex)

**Pros:**
- More secure (only scripts with correct nonce execute)
- Better CSP score

**Cons:**
- Requires modifying Next.js to add nonce to all inline scripts
- Complex implementation
- May break existing components

**Implementation:**
- Remove `'unsafe-inline'` from script-src
- Add nonce to every inline script in Next.js
- Requires Next.js internals modification

### Option 3: Use 'strict-dynamic' (Modern Approach)

**Pros:**
- Modern CSP approach
- Good balance of security and functionality

**Cons:**
- Browser support varies
- Still requires careful implementation

---

## ✅ Recommended Fix

**Use Option 1:** Remove nonce generation, keep `'unsafe-inline'`

**Reason:**
- Next.js 16 + React 19 explicitly requires `'unsafe-inline'`
- Nonce generation is incompatible with Next.js's inline scripts
- This is a known tradeoff for server-side rendered React apps
- Security is still maintained via other CSP directives

---

## 📝 Implementation Steps

1. **Edit middleware.ts** - Remove nonce generation
2. **Test dashboard** - Verify scripts execute
3. **Check console** - No CSP violations
4. **Validate security** - Other headers still present

---

## 🧪 Testing Plan

### Before Fix
- [x] Dashboard shows loading spinner indefinitely
- [x] Browser console shows 6+ CSP violations
- [x] Network requests to backend return 401 (secondary issue)

### After Fix
- [ ] Dashboard loads without hanging
- [ ] No CSP violations in console
- [ ] Scripts execute properly
- [ ] Backend auth handled gracefully

---

## 🚨 Additional Issues

### Secondary Issue: Backend Authentication

**Finding:** Backend returns 401 Unauthorized  
**Impact:** Dashboard may still fail if backend auth not configured  
**Solution:** Separate from CSP fix - requires auth token in request

**Note:** This is a separate issue. Even if backend returns data, the dashboard will still hang due to CSP blocking the JavaScript that would display the data.

---

## 📚 References

1. **CSP Specification:** https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
2. **Next.js CSP:** https://nextjs.org/docs/app/building-your-application/configuring/content-security-policy
3. **CSP Level 3:** https://www.w3.org/TR/CSP3/#unsafe-inline-usage

---

## 🎯 Priority

**CRITICAL** - Production blocking issue

**Fix immediately:** Dashboard completely unusable due to CSP blocking all JavaScript

---

## 📋 Next Steps

1. Apply fix to `middleware.ts`
2. Restart Next.js server
3. Test dashboard loading
4. Verify no CSP violations in console
5. Address backend auth issue (separate)
6. Update documentation

---

**Status:** 🟡 Ready for Fix Implementation  
**Blocker:** None - Solution identified  
**Estimated Fix Time:** 5 minutes
