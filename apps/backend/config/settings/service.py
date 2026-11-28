"""
Service settings for LedgerSG API.

Optimized for running as a background service:
- Debug mode disabled for stability
- Console logging
- No debug toolbar
- Minimal middleware for performance

P14/H-9: the module now enforces the SAME SECRET_KEY strength gate as
production (the Docker path previously generated a predictable
django-secret-key-for-hf-space-$(date +%s) key — anyone who can estimate the
container start time can forge HS256 JWTs). ALLOWED_HOSTS comes from env
(the hardcoded wildcard is gone).
"""


from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403 — the established settings pattern
from .base import SECRET_KEY

# =============================================================================
# DEBUG SETTINGS
# =============================================================================

DEBUG = False

# =============================================================================
# ALLOWED HOSTS (P14/H-9: env-driven; the hardcoded wildcard is gone)
# =============================================================================

# P19/X-L4: decouple (`.env`-aware) — the os.environ-only read gave the
# service mode split semantics (SECRET_KEY from the same .env WAS
# honored while ALLOWED_HOSTS silently was not).
from decouple import (  # noqa: E402 — deliberate end-of-file import (Django circular-avoidance)
    Csv,  # noqa: E402 — the deliberate end-of-file import (Django circular-avoidance)
)
from decouple import (  # noqa: E402 — deliberate end-of-file import (Django circular-avoidance)
    config as _decouple_config,  # noqa: E402 — the deliberate end-of-file import (Django circular-avoidance)
)

ALLOWED_HOSTS = _decouple_config(
    "ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv()
)

# =============================================================================
# SECRET KEY GATE (P14/H-9 — the production H-06 posture)
# =============================================================================

_WEAK_KEY_PREFIXES = ("django-insecure", "django-secret-key-for-")
if len(SECRET_KEY) < 50 or SECRET_KEY.startswith(_WEAK_KEY_PREFIXES):
    raise ImproperlyConfigured(
        "SECRET_KEY must be a strong (>=50 char) value in service mode — "
        "it signs HS256 JWTs. Generate one with "
        "python -c \"import secrets;print(secrets.token_urlsafe(64))\" "
        "and pass it via the SECRET_KEY environment variable."
    )

# =============================================================================
# LOGGING SETTINGS
# =============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# =============================================================================
# MIDDLEWARE
# =============================================================================

# P16/BE-H1: DERIVE from base — never rebuild. The pre-P16 from-scratch
# list had drifted and dropped TenantContextMiddleware,
# AuditContextMiddleware, the CSP middleware and WhiteNoise: the Docker/
# script API path served every org-scoped request with no org context
# (403s for non-superusers; RLS saw NULL on every request) and no audit
# attribution. base.py has no debug_toolbar entry, so the service-mode
# list is identical to base's — copied so the module is a plain list
# (importing the NAME would alias base's list; a copy is the
# copy-on-write convention from P10/LG-4).
from .base import (  # noqa: E402 — deliberate end-of-file import (Django circular-avoidance)
    MIDDLEWARE as _BASE_MIDDLEWARE,  # noqa: E402 — the deliberate end-of-file import (Django circular-avoidance)
)

MIDDLEWARE = list(_BASE_MIDDLEWARE)

# =============================================================================
# EMAIL BACKEND
# =============================================================================

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# =============================================================================
# SECURITY (relaxed for local service)
# =============================================================================

# Don't enforce HTTPS for local development
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

ENABLE_ADMIN = False
