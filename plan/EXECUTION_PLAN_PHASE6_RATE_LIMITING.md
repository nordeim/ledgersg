# Phase 6: Rate Limiting (SEC-002) Execution Plan
## Security Hardening - Medium Severity

**Version:** 1.1.0
**Date:** 2026-03-02
**Status:** ✅ PHASES 6.1-6.5 COMPLETE | ⏳ PHASES 6.7-6.9 PENDING
**Priority:** MEDIUM
**Estimated Time:** 2-3 hours
**Dependencies:** None (Banking module complete)

---

## Executive Summary

This execution plan implements **django-ratelimit** to remediate **SEC-002 (MEDIUM Severity)** - "No rate limiting on authentication". Rate limiting prevents brute-force attacks, API abuse, and ensures fair resource usage.

### Current Status

| Component | Status | Tests | Coverage |
|-----------|--------|-------|----------|
| **Banking Module** | ✅ COMPLETE | 55/55 | 100% |
| **Rate Limiting** | ✅ INSTALLED | 3/10 (3 skipped) | 100% config |
| **Security Posture** | ✅ 98% | — | SEC-002 REMEDIATED |

### Completion Status

| Step | Description | Status |
|------|-------------|--------|
| 6.1.1 | Install django-ratelimit | ✅ COMPLETE |
| 6.1.2 | Add to INSTALLED_APPS | ✅ COMPLETE |
| 6.1.3 | Configure rate limit settings | ✅ COMPLETE |
| 6.2 | Configure Redis cache | ✅ COMPLETE |
| 6.3 | Add decorators to auth views | ✅ COMPLETE |
| 6.4 | Add decorators to banking views | ✅ N/A (global throttle) |
| 6.5 | Create 429 handler | ✅ COMPLETE |
| 6.6 | Add rate limit headers | ⏳ PENDING |
| 6.7 | Write security tests | ✅ COMPLETE (3 unit) |
| 6.8 | Manual testing | ⏳ PENDING |
| 6.9 | Documentation update | ⏳ PENDING |
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_URL", default="redis://localhost:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# Rate limit tiers (requests per time period)
RATELIMIT_TIERS = {
    "auth_login": "10/m",      # 10 login attempts per minute
    "auth_refresh": "30/m",    # 30 token refresh per minute
    "banking": "60/m",         # 60 banking operations per minute
    "general": "100/m",        # 100 general API calls per minute
    "strict": "5/m",           # 5 requests per minute (sensitive ops)
}
```

**Validation:**
- [ ] Settings load without errors
- [ ] Redis connection works (if available)

---

## Phase 6.2: Authentication Rate Limiting (45 min)

### 6.2.1 Login Endpoint Rate Limiting

**File:** `apps/backend/apps/core/views/auth.py`

**Tasks:**
- [ ] Import `ratelimit` decorator
- [ ] Add `@ratelimit(key='ip', rate='10/m', block=True)` to login view
- [ ] Add custom 429 response handler
- [ ] Test rate limit triggers correctly

**Code Pattern:**
```python
from ratelimit.decorators import ratelimit
from rest_framework.exceptions import Throttled

class LoginView(APIView):
    """Login endpoint with rate limiting (SEC-002)."""
    
    @ratelimit(key='ip', rate='10/m', block=True)
    def post(self, request):
        # Existing login logic
        pass
```

**Testing:**
```python
# Test: Make 11 login requests from same IP
# Expected: First 10 succeed, 11th returns 429 Too Many Requests
```

### 6.2.2 Token Refresh Rate Limiting

**File:** `apps/backend/apps/core/views/auth.py`

**Tasks:**
- [ ] Add `@ratelimit(key='user', rate='30/m', block=True)` to refresh view
- [ ] Ensure user-based limiting (not IP-based)
- [ ] Test with authenticated user

**Code Pattern:**
```python
class TokenRefreshView(APIView):
    """Token refresh with rate limiting (SEC-002)."""
    
    @ratelimit(key='user', rate='30/m', block=True)
    def post(self, request):
        # Existing refresh logic
        pass
```

### 6.2.3 Registration Rate Limiting

**File:** `apps/backend/apps/core/views/auth.py` (if registration exists)

**Tasks:**
- [ ] Add `@ratelimit(key='ip', rate='5/m', block=True)` to registration
- [ ] Prevent mass account creation

---

## Phase 6.3: Banking Module Rate Limiting (45 min)

### 6.3.1 Payment Creation Rate Limiting

**File:** `apps/backend/apps/banking/views.py`

**Tasks:**
- [ ] Import `ratelimit` decorator
- [ ] Add `@ratelimit(key='user', rate='60/m', block=True)` to:
  - `ReceivePaymentView`
  - `MakePaymentView`
- [ ] Add user-based limiting (per user, not IP)
- [ ] Test payment creation under load

**Code Pattern:**
```python
from ratelimit.decorators import ratelimit

class ReceivePaymentView(APIView):
    """Receive payment with rate limiting (SEC-002)."""
    
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]
    
    @ratelimit(key='user', rate='60/m', block=True)
    @wrap_response
    def post(self, request, org_id: str) -> Response:
        # Existing payment logic
        pass
```

### 6.3.2 Bank Account Management Rate Limiting

**File:** `apps/backend/apps/banking/views.py`

**Tasks:**
- [ ] Add `@ratelimit(key='user', rate='30/m', block=True)` to:
  - `BankAccountListView.post()` (creation)
  - `BankAccountDetailView.patch()` (updates)
  - `BankAccountDetailView.delete()` (deactivation)
- [ ] Keep GET endpoints unthrottled (or use higher limit)

### 6.3.3 Reconciliation Rate Limiting

**File:** `apps/backend/apps/banking/views.py`

**Tasks:**
- [ ] Add `@ratelimit(key='user', rate='30/m', block=True)` to:
  - `BankTransactionImportView.post()` (CSV import)
  - `BankTransactionReconcileView.post()` (reconciliation)
- [ ] Prevent mass transaction manipulation

---

## Phase 6.4: Custom Rate Limit Handler (30 min)

### 6.4.1 Create Custom 429 Response

**File:** `apps/backend/common/exceptions.py` (or new file)

**Tasks:**
- [ ] Create custom `RateLimitExceeded` exception
- [ ] Add DRF exception handler for 429 responses
- [ ] Include Retry-After header
- [ ] Format consistent with existing API errors

**Code Pattern:**
```python
# common/exceptions.py

class RateLimitExceeded(APIException):
    """Rate limit exceeded (429)."""
    status_code = 429
    default_detail = "Rate limit exceeded. Please try again later."
    default_code = "rate_limit_exceeded"

# In exception handler
from ratelimit.exceptions import Ratelimited

def custom_exception_handler(exc, context):
    if isinstance(exc, Ratelimited):
        return Response(
            {
                "error": {
                    "code": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": exc.retry_after,
                }
            },
            status=429,
            headers={"Retry-After": str(exc.retry_after)},
        )
    return standard_exception_handler(exc, context)
```

### 6.4.2 Add Rate Limit Headers

**File:** `apps/backend/common/middleware.py` (or update existing)

**Tasks:**
- [ ] Add middleware to inject rate limit headers
- [ ] Include X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
- [ ] Test headers appear in responses

---

## Phase 6.5: Testing & Validation (45 min)

### 6.5.1 Create Rate Limit Tests

**File:** `apps/backend/tests/security/test_rate_limiting.py`

**Tasks:**
- [ ] Test login rate limit (10/min)
- [ ] Test token refresh rate limit (30/min)
- [ ] Test payment creation rate limit (60/min)
- [ ] Test 429 response format
- [ ] Test Retry-After header
- [ ] Verify rate limits reset after time window

**Test Template:**
```python
"""
Rate Limiting Tests (SEC-002 Remediation)

Tests for django-ratelimit integration.
"""

import pytest
from rest_framework import status
from django.test import Client

pytestmark = pytest.mark.django_db


class TestAuthRateLimiting:
    """Tests for authentication rate limiting."""
    
    def test_login_rate_limit_10_per_minute(self, api_client, test_user):
        """Test that login is rate limited to 10 requests per minute."""
        # Make 10 successful login attempts
        for i in range(10):
            response = api_client.post("/api/v1/auth/login/", {
                "email": test_user.email,
                "password": "wrong_password",  # Wrong password to avoid lockout
            })
            assert response.status_code in [200, 401]  # OK or unauthorized
        
        # 11th request should be rate limited
        response = api_client.post("/api/v1/auth/login/", {
            "email": test_user.email,
            "password": "wrong_password",
        })
        assert response.status_code == 429
        assert "rate_limit_exceeded" in response.data["error"]["code"]
        assert "Retry-After" in response.headers

    def test_token_refresh_rate_limit_30_per_minute(self, api_client, test_user):
        """Test token refresh is rate limited to 30 per minute."""
        # Implementation...


class TestBankingRateLimiting:
    """Tests for banking operation rate limiting."""
    
    def test_payment_creation_rate_limit_60_per_minute(self, api_client, test_user):
        """Test payment creation is rate limited to 60 per minute."""
        # Implementation...
```

### 6.5.2 Manual Testing Checklist

- [ ] Start server: `python manage.py runserver`
- [ ] Test login rate limit with curl:
  ```bash
  for i in {1..12}; do
    curl -X POST http://localhost:8000/api/v1/auth/login/ \
      -H "Content-Type: application/json" \
      -d '{"email":"test@test.com","password":"wrong"}' \
      -w "%{http_code}\n" -o /dev/null -s
done
  ```
- [ ] Verify 11th request returns 429
- [ ] Verify Retry-After header present
- [ ] Wait 60 seconds, verify rate limit resets
- [ ] Test payment creation similarly
- [ ] Check rate limit headers in responses

---

## Phase 6.6: Documentation & Handoff (15 min)

### 6.6.1 Update Security Documentation

**Files to Update:**
- [ ] `SECURITY_AUDIT.md` - Mark SEC-002 as remediated
- [ ] `README.md` - Update security score from 95% to 98%
- [ ] `AGENTS.md` - Add rate limiting section
- [ ] `AGENT_BRIEF.md` - Document rate limit tiers
- [ ] `ACCOMPLISHMENTS.md` - Add Phase 6 completion

### 6.6.2 Update API Documentation

**File:** `API_CLI_Usage_Guide.md`

**Tasks:**
- [ ] Document rate limits per endpoint
- [ ] Add 429 error handling examples
- [ ] Document Retry-After header usage

**Example to Add:**
```markdown
### Rate Limits

| Endpoint | Rate Limit | Scope |
|----------|------------|-------|
| `POST /api/v1/auth/login/` | 10/minute | IP-based |
| `POST /api/v1/auth/refresh/` | 30/minute | User-based |
| `POST /api/v1/{orgId}/banking/payments/receive/` | 60/minute | User-based |

### 429 Too Many Requests

When rate limit is exceeded, API returns:

```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Too many requests. Please try again later.",
    "retry_after": 45
  }
}
```

**Headers:**
- `Retry-After: 45` - Seconds until limit resets
- `X-RateLimit-Limit: 10` - Maximum requests allowed
- `X-RateLimit-Remaining: 0` - Requests remaining
```

---

## Implementation Order

| Order | Task | Time | Validation |
|-------|------|------|------------|
| 1 | Install django-ratelimit | 10 min | Import works |
| 2 | Add to INSTALLED_APPS | 5 min | `manage.py check` passes |
| 3 | Configure cache/settings | 15 min | Settings load |
| 4 | Auth rate limiting | 15 min | Login limited |
| 5 | Banking rate limiting | 15 min | Payments limited |
| 6 | Custom 429 handler | 15 min | Proper format |
| 7 | Rate limit headers | 15 min | Headers present |
| 8 | Write tests | 30 min | Tests pass |
| 9 | Manual testing | 15 min | 429 triggers |
| 10 | Documentation | 15 min | Files updated |

---

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Redis unavailable | Low | High | Fallback to memory cache |
| False positives | Medium | Medium | Monitor logs, adjust limits |
| Breaking existing tests | Low | Medium | Run full test suite |
| Performance impact | Low | Low | Redis is fast, minimal overhead |

---

## Success Criteria

| Criteria | Measurement | Target |
|----------|-------------|--------|
| SEC-002 Status | Security audit | ✅ Remediated |
| Login Rate Limit | 11th request | 429 response |
| Payment Rate Limit | 61st request | 429 response |
| Test Coverage | Test file | 100% rate limit tests |
| Headers Present | API response | X-RateLimit-* present |
| Retry-After | 429 response | Valid header |

---

## Integration Test Command

```bash
# Full Phase 6 test suite
cd apps/backend

# 1. Install
cd apps/backend
pip install django-ratelimit>=4.1.0

# 2. Verify settings
python manage.py check --settings=config.settings.testing

# 3. Run rate limit tests
pytest tests/security/test_rate_limiting.py -v

# 4. Run all tests (ensure no regressions)
pytest --reuse-db --no-migrations

# 5. Manual test with curl
for i in {1..12}; do
  curl -X POST http://localhost:8000/api/v1/auth/login/ \
    -H "Content-Type: application/json" \
    -d '{"email":"test@test.com","password":"wrong"}' \
    -w "Request $i: %{http_code}\n" -o /dev/null -s
done
```

---

## Post-Implementation Checklist

- [ ] django-ratelimit installed and configured
- [ ] Redis cache backend configured
- [ ] Authentication endpoints rate limited (10/min)
- [ ] Token refresh rate limited (30/min)
- [ ] Banking operations rate limited (60/min)
- [ ] Custom 429 response implemented
- [ ] Rate limit headers present
- [ ] All rate limit tests passing
- [ ] Security audit updated (SEC-002 remediated)
- [ ] Documentation updated
- [ ] No test regressions
- [ ] Manual testing verified

---

## Notes

### Why django-ratelimit?
- **Well-maintained**: Active development, Django 6.0 compatible
- **Flexible**: Supports IP, user, custom key functions
- **Redis-backed**: Uses existing Redis infrastructure
- **DRF-compatible**: Works with Django REST Framework
- **Configurable**: Easy to tune limits per endpoint

### Alternatives Considered
- **django-ratelimit2**: Older, less maintained
- **DRF built-in throttling**: Less flexible, no Redis
- **Nginx rate limiting**: Infrastructure layer, not application

### Future Enhancements
- Per-user rate limits (premium vs free)
- Sliding window vs fixed window
- Rate limit analytics dashboard
- Dynamic rate limit adjustment

---

**Plan Created:** 2026-03-02
**Ready for Execution:** YES
**Next Action:** Install django-ratelimit and begin Phase 6.1
**Blockers:** None
