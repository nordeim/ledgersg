"""
Development settings for LedgerSG API.

- Debug mode enabled
- Console email backend
- CORS allow-all for local development
- Debug toolbar enabled
- Expanded logging
"""

from .base import *

# =============================================================================
# DEBUG SETTINGS
# =============================================================================

DEBUG = True

# =============================================================================
# ALLOWED HOSTS
# =============================================================================

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "*"]

# =============================================================================
# EMAIL BACKEND
# =============================================================================

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# =============================================================================
# CORS SETTINGS (Development - Allow All)
# =============================================================================

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# =============================================================================
# DATABASE (Development)
# =============================================================================

# Use local PostgreSQL or Docker
DATABASES["default"]["NAME"] = config("DB_NAME", default="ledgersg_dev")
DATABASES["default"]["USER"] = config("DB_USER", default="ledgersg")
DATABASES["default"]["PASSWORD"] = config("DB_PASSWORD", default="ledgersg")
DATABASES["default"]["HOST"] = config("DB_HOST", default="localhost")

# =============================================================================
# LOGGING (Development - Debug Level)
# =============================================================================

LOGGING["loggers"]["django"]["level"] = "DEBUG"
LOGGING["loggers"]["ledgersg"]["level"] = "DEBUG"

# =============================================================================
# DEBUG TOOLBAR (Optional)
# =============================================================================

if config("DEBUG_TOOLBAR", default=True, cast=bool):
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    INTERNAL_IPS = ["127.0.0.1"]

# =============================================================================
# CELERY (Development - Synchronous)
# =============================================================================

# Run tasks synchronously in development
CELERY_TASK_ALWAYS_EAGER = config("CELERY_ALWAYS_EAGER", default=True, cast=bool)

# =============================================================================
# JWT (Development - Longer Lifetimes)
# =============================================================================

SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"] = timedelta(hours=1)
SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"] = timedelta(days=30)

# =============================================================================
# LOGIN RATE LIMIT (Development — e2e budget)
#
# `npm run test:e2e:full` legitimately issues ~11 login attempts per run
# against the local dev server (7 pre-P4 specs + 3 session-persistence
# specs + 1 bad-password assertion); the base 10/min-per-IP limit 429'd the
# tail of the suite. Production (base settings) keeps 10/min — the
# guardrail is not weakened, only the local budget is raised.
# =============================================================================

LOGIN_RATELIMIT_IP = "60/minute"

# P6/E-1: raise the refresh + DRF throttle budgets for the local e2e
# suite (npm run test:e2e:full legitimately issues ~37 refreshes and
# ~25 logins per run; the DRF anonymous 20/min budget stacked on the
# refresh endpoint on top of the decorator limit). Copy-on-write: never
# mutate the shared base dict. Production posture in base is unchanged
# (20/min anon, 100/min user, 20/min refresh).
REFRESH_RATELIMIT_IP = "240/minute"

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {
        **REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],
        "anon": "240/minute",
        "user": "600/minute",
    },
}

# =============================================================================
# SHELL PLUS (Django Extensions)
# =============================================================================

SHELL_PLUS = "ipython"
SHELL_PLUS_PRINT_SQL = True

# =============================================================================
# SECURITY (Development - Relaxed)
# =============================================================================

# Disable HTTPS redirect in development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
