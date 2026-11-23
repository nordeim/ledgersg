"""
Dotted-path rate callables for django-ratelimit (P4).

django-ratelimit resolves `rate="module.callable"` lazily at request time
(`django_ratelimit.core.get_usage` imports the path and calls it with
`(group, request)`), which is what lets the login limits be SETTINGS-driven
knobs instead of decorator literals:

- base settings (production defaults): LOGIN_RATELIMIT_IP = "10/minute",
  LOGIN_RATELIMIT_USER = "30/minute" — the documented SEC-002 posture,
  unchanged
- development settings raise the IP budget because `npm run
  test:e2e:full` legitimately issues ~11 login attempts per run against the
  local dev server (7 pre-P3 specs + 3 session-persistence specs + 1
  bad-password assertion) and the old 10/min-per-IP limit 429'd the tail of
  the suite
- testing settings: RATELIMIT_ENABLE = False (the suite self-limits)

The guardrail is never weakened in production — only the development
budget moves.
"""

from django.conf import settings


def login_ip(group, request) -> str:
    """Per-IP login rate (settings knob; default 10/minute)."""
    return settings.LOGIN_RATELIMIT_IP


def login_user(group, request) -> str:
    """Per-user (or IP fallback) login rate (settings knob; default 30/minute)."""
    return settings.LOGIN_RATELIMIT_USER


def refresh_ip(group, request) -> str:
    """Per-IP refresh rate (P6/E-1 settings knob; default 20/minute).

    The refresh decorator referenced a hardcoded literal, so the full
    e2e suite (which legitimately issues ~37 refreshes via the P4
    session-persistence flow) 429'd mid-run against the local dev server
    with no way to raise the budget without editing code.
    """
    return settings.REFRESH_RATELIMIT_IP


def register_ip(group, request) -> str:
    """Per-IP register rate (P11 live-gate settings knob; default 5/hour).

    Same class as the refresh knob: the register decorator carried a
    hardcoded "5/hour" literal, so re-running the e2e suite against the
    local dev server (one self-serve registration per run) 429'd the
    register step with no settings-driven way to raise the development
    budget. Production posture (5/hour) is unchanged.
    """
    return settings.REGISTER_RATELIMIT_IP
