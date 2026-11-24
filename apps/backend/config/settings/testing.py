"""
Testing settings for LedgerSG API.

- In-memory SQLite (optional) or test PostgreSQL
- Fast password hashing
- Disabled throttling
- Synchronous Celery
"""

from decouple import config

from .base import *

# Explicit re-binding of the star-imported structure overridden below
# (copy-on-write, P13/B-7).
from .base import DATABASES

# =============================================================================
# DEBUG SETTINGS
# =============================================================================

DEBUG = False

# Allow testserver for Django test client
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

# =============================================================================
# DATABASE (Testing)
# =============================================================================

# Use the manually initialized test database. Credentials honor the same
# DB_* environment variables as base.py (P5/C-3: no hardcoded password —
# CI generates a per-run value; local dev uses the documented defaults).
# P13/B-7 copy-on-write: rebind a fresh DATABASES structure instead of
# mutating base's dicts in place (the P10 crash class).
DATABASES = {
    **DATABASES,
    "default": {
        **DATABASES["default"],
        "NAME": config("DB_NAME", default="test_ledgersg_dev"),
        "USER": config("DB_USER", default="ledgersg"),
        "PASSWORD": config(
            "DB_PASSWORD", default="ledgersg_secret_to_change"
        ),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
        # pytest uses exactly the database named above (SQL-First: pytest-django
        # cannot create tables for managed=False models — the schema is loaded
        # via psql in CI/docs, so the test DB must be the schema-loaded one).
        "TEST": {
            "NAME": config("DB_NAME", default="test_ledgersg_dev"),
        },
    },
}
# Prevent Django from running migrations
MIGRATE = False

# =============================================================================
# PASSWORD HASHING (Fast for tests)
# =============================================================================

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# =============================================================================
# CACHING (Testing)
# =============================================================================

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://localhost:6379/1",
    }
}

# Tests hit auth endpoints repeatedly with the same IP; the documented
# SEC-002 default (base.py: RATELIMIT_ENABLE = True) must not rate-limit
# the test suite itself.
RATELIMIT_ENABLE = False

RATELIMIT_USE_CACHE = "default"

# =============================================================================
# CELERY (Testing - Synchronous)
# =============================================================================

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# =============================================================================
# THROTTLING (Testing - Disabled)
# =============================================================================

# Copy-on-write (P6/E-1): never mutate the shared base dict — the in-place
# assignment corrupted config.settings.base.REST_FRAMEWORK for every other
# module in the process (the settings-gate posture test caught it).
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
}

# =============================================================================
# LOGGING (Testing - Minimal)
# =============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
        "level": "WARNING",
    },
}

# =============================================================================
# CORS (Testing)
# =============================================================================

CORS_ALLOW_ALL_ORIGINS = True

# =============================================================================
# SECURITY (Testing - Disabled)
# =============================================================================

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# =============================================================================
# SENTRY (Testing - Disabled)
# =============================================================================

SENTRY_DSN = None

# =============================================================================
# TEST RUNNER
# =============================================================================

TEST_RUNNER = "common.test_runner.SchemaTestRunner"

# Synchronous Celery
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Speed up tests
DEBUG_PROPAGATE_EXCEPTIONS = True
