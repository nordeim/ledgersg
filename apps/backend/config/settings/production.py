"""
Production settings for LedgerSG API.

- Debug mode disabled
- HTTPS enforcement
- HSTS headers
- CSP headers
- Sentry error tracking
- Restricted CORS
"""

from django.core.exceptions import ImproperlyConfigured

from .base import *

# Explicit re-binding of the star-imported structure overridden below
# (copy-on-write, P13/B-7).
from .base import DATABASES

# =============================================================================
# SECURITY SETTINGS
# =============================================================================

# H-06: SECRET_KEY signs HS256 JWTs — a published/default key is a full
# authentication bypass. Fail fast rather than start with a known key.
_KNOWN_DEFAULT_KEYS = {
    "django-insecure-change-in-production",
    "your-secret-key-here-change-in-production",
}
if (
    SECRET_KEY in _KNOWN_DEFAULT_KEYS
    or len(SECRET_KEY) < 50
    or SECRET_KEY.startswith("django-insecure")
):
    raise ImproperlyConfigured(
        "SECRET_KEY must be set to a strong random value (>= 50 chars) in "
        "production. It signs the platform's JWTs; shipping a default key "
        "would allow anyone to mint valid tokens."
    )

DEBUG = False

# Force HTTPS
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Secure cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# =============================================================================
# CORS SETTINGS (Production)
# =============================================================================

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    cast=Csv(),
    default="https://app.ledgersg.sg",
)

# =============================================================================
# DATABASE (Production)
# =============================================================================

# P13/B-7 copy-on-write: rebind a fresh DATABASES structure instead of
# mutating base's dicts in place (the P10 crash class).
DATABASES = {
    **DATABASES,
    "default": {
        **DATABASES["default"],
        "CONN_MAX_AGE": 60,  # Persistent connections
    },
}

# =============================================================================
# CACHING (Production)
# =============================================================================
# P11/C-2: no override — inherit base's builtin Redis backend. The old
# django_redis.cache.RedisCache override pointed at a dependency that is
# in neither pyproject nor uv.lock, so every org-scoped request (tenant
# membership cache + django-ratelimit) crashed with ModuleNotFoundError.
# The builtin django.core.cache.backends.redis.RedisCache is the repo's
# own convention (base + testing use the same stack) and needs no extra
# dependency; production points it at REDIS_URL via base.

# =============================================================================
# CELERY (Production)
# =============================================================================

CELERY_TASK_ALWAYS_EAGER = False

# =============================================================================
# LOGGING (Production)
# =============================================================================

# P11/C-2: LOG_DIR is the deployer's knob (default /var/log/ledgersg —
# DEPLOYMENT.md ships the mkdir step). The file handler path derives
# from it instead of a hardcoded path that crashes django.setup() when
# the directory does not exist on a fresh host.
LOG_DIR = config("LOG_DIR", default="/var/log/ledgersg")

# P11/C-2: copy-on-write — the dict is SHARED with base via
# `from .base import *`; assigning into LOGGING["handlers"] mutated
# base's (and every other settings module's) LOGGING in place.
LOGGING = {
    **LOGGING,
    "handlers": {
        **LOGGING["handlers"],
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": f"{LOG_DIR}/django.log",
            "maxBytes": 10485760,  # 10 MB
            "backupCount": 10,
            "formatter": "verbose",
        },
    },
    "loggers": {
        **LOGGING["loggers"],
        "django": {
            **LOGGING["loggers"]["django"],
            "handlers": ["console", "file"],
        },
        "ledgersg": {
            **LOGGING["loggers"]["ledgersg"],
            "handlers": ["console", "file"],
        },
    },
}

# =============================================================================
# STATIC FILES (Production)
# =============================================================================

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# =============================================================================
# ADMINS AND MANAGERS
# =============================================================================

ADMINS = [
    ("LedgerSG DevOps", config("ADMIN_EMAIL", default="ops@ledgersg.sg")),
]

MANAGERS = ADMINS

# =============================================================================
# ERROR REPORTING
# =============================================================================

# Only report errors via Sentry (configured in base.py)
# Disable email error reporting to avoid spam
SEND_BROKEN_LINK_EMAILS = False
