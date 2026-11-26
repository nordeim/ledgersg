"""
Development settings for LedgerSG API.

- Debug mode enabled
- Console email backend
- CORS allow-all for local development
- Debug toolbar enabled
- Expanded logging
"""

from .base import *

# Explicit re-bindings of the star-imported structures this module overrides
# below (copy-on-write): explicit imports keep the override lines F405-clean
# (import-star-usage) instead of deepening that debt class.
from .base import DATABASES, INSTALLED_APPS, LOGGING, MIDDLEWARE, SIMPLE_JWT

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
# P13/B-7 copy-on-write: rebind a fresh DATABASES structure instead of
# mutating base's dicts in place (the P10 crash class).
DATABASES = {
    **DATABASES,
    "default": {
        **DATABASES["default"],
        "NAME": config("DB_NAME", default="ledgersg_dev"),
        "USER": config("DB_USER", default="ledgersg"),
        "PASSWORD": config("DB_PASSWORD", default="ledgersg"),
        "HOST": config("DB_HOST", default="localhost"),
    },
}

# =============================================================================
# LOGGING (Development - Debug Level)
# =============================================================================

# Copy-on-write (the same rule the REST_FRAMEWORK override below documents):
# never mutate the shared base structures in place. Any process that imports
# this module while running under other settings — e.g. a test suite
# importing development.py to assert its knobs — would otherwise inject
# debug_toolbar into the live INSTALLED_APPS/MIDDLEWARE mid-run and crash
# middleware loading with "HistoryEntry isn't in an application in
# INSTALLED_APPS" (P10).
LOGGING = {
    **LOGGING,
    "loggers": {
        **LOGGING["loggers"],
        "django": {**LOGGING["loggers"]["django"], "level": "DEBUG"},
        "ledgersg": {**LOGGING["loggers"]["ledgersg"], "level": "DEBUG"},
    },
}

# =============================================================================
# DEBUG TOOLBAR (Optional)
# =============================================================================

if config("DEBUG_TOOLBAR", default=True, cast=bool):
    # Copy-on-write — see the LOGGING note above: += / .insert() would
    # mutate the shared base lists and poison any process importing this
    # module under other settings.
    INSTALLED_APPS = [*INSTALLED_APPS, "debug_toolbar"]
    MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware", *MIDDLEWARE]
    INTERNAL_IPS = ["127.0.0.1"]

# =============================================================================
# CELERY (Development - Synchronous)
# =============================================================================

# Run tasks synchronously in development
CELERY_TASK_ALWAYS_EAGER = config("CELERY_ALWAYS_EAGER", default=True, cast=bool)

# =============================================================================
# JWT (Development - Longer Lifetimes)
# =============================================================================

# P13/B-7 copy-on-write: rebind a fresh SIMPLE_JWT dict instead of
# mutating base's (the P10 crash class).
SIMPLE_JWT = {
    **SIMPLE_JWT,
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
}

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

# P10: the login per-user_or_ip budget (anonymous logins key by IP) was the
# third knob the P4/P6 pass missed — the full e2e suite legitimately issues
# ~30 logins per run against the local dev server, so base's 30/minute
# blocked the tail of the suite with a raw 403 (Ratelimited rendered as a
# permission failure, bouncing the frontend to /login mid-spec). Raise the
# development budget only; production (base settings) keeps 30/minute.
LOGIN_RATELIMIT_USER = "120/minute"

# P6/E-1: raise the refresh + DRF throttle budgets for the local e2e
# suite (npm run test:e2e:full legitimately issues ~37 refreshes and
# ~25 logins per run; the DRF anonymous 20/min budget stacked on the
# refresh endpoint on top of the decorator limit). Copy-on-write: never
# mutate the shared base dict. Production posture in base is unchanged
# (20/min anon, 100/min user, 20/min refresh).
REFRESH_RATELIMIT_IP = "240/minute"

# P11 live gate: raise the register budget for the local e2e suite — the
# self-serve spec registers one user per run and repeated runs against the
# same dev server exhausted base's 5/hour literal (the 429 bounced the
# spec off /register). Production posture in base is unchanged (5/hour).
REGISTER_RATELIMIT_IP = "120/hour"

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

# P17/BE-L3: the /admin/ route mounts only when ENABLE_ADMIN is true
# (gated in config/urls.py — development convenience, production OFF).
ENABLE_ADMIN = config("ENABLE_ADMIN", default=True, cast=bool)
