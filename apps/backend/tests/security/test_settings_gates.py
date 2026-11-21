"""
Settings hardening gates (H-06 / H-07 remediation).

- Production must refuse to start with a default/short SECRET_KEY (it signs
  HS256 JWTs — a published default is full authentication bypass).
- Rate limiting must be ON by default in base settings (SEC-002 claim) and
  explicitly OFF only in testing.
"""

import importlib


def _load_production_settings(monkeypatch, secret):
    """Import config.settings.production with an overridden SECRET_KEY."""
    monkeypatch.setenv("SECRET_KEY", secret)
    # Clear cached modules so settings re-evaluate with the new env
    import sys
    for mod in list(sys.modules):
        if mod.startswith("config.settings"):
            del sys.modules[mod]
    import config.settings.production as prod
    importlib.reload(prod)
    return prod


def test_production_rejects_default_secret_key(monkeypatch):
    """RED for H-06: the published default SECRET_KEY must fail fast."""
    pytest = __import__("pytest")
    from django.core.exceptions import ImproperlyConfigured

    with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
        _load_production_settings(
            monkeypatch, "django-insecure-change-in-production"
        )


def test_production_rejects_short_secret_key(monkeypatch):
    """RED for H-06: a <50 char SECRET_KEY is not acceptable for HS256 JWT signing."""
    pytest = __import__("pytest")
    from django.core.exceptions import ImproperlyConfigured

    with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
        _load_production_settings(monkeypatch, "tooshort")


def test_production_accepts_strong_secret_key(monkeypatch):
    """A 50+ char random SECRET_KEY passes the gate."""
    strong = "a" * 64
    prod = _load_production_settings(monkeypatch, strong)
    assert strong == prod.SECRET_KEY


def test_rate_limiting_enabled_by_default():
    """RED for H-07: RATELIMIT_ENABLE must default to True (SEC-002)."""
    from config.settings import base

    assert base.RATELIMIT_ENABLE is True, (
        "Rate limiting must be on by default; the audit found it defaulted "
        "to False, contradicting the documented SEC-002 remediation"
    )


def test_rate_limiting_disabled_in_testing():
    """Tests must explicitly disable rate limiting (documented decision)."""
    from config.settings import testing

    assert testing.RATELIMIT_ENABLE is False


# =============================================================================
# P6/E-1 — e2e-friendly rate budgets as settings knobs
# =============================================================================

def test_refresh_throttle_is_a_settings_knob():
    """RED for P6/E-1: the refresh endpoint's throttle must be a settings
    knob (base default 20/minute), not a decorator literal — the full e2e
    suite legitimately issues ~37 refreshes against the local dev server
    and the hardcoded limit 429'd the tail of the suite."""
    from config.settings import base

    assert getattr(base, "REFRESH_RATELIMIT_IP", None) == "20/minute", (
        "base must define the refresh throttle knob with the documented "
        "SEC-002 posture (20/minute) — production is never weakened"
    )

    from config import ratelimits

    assert callable(getattr(ratelimits, "refresh_ip", None)), (
        "config.ratelimits must expose the dotted-path callable the "
        "refresh decorator references"
    )


def test_refresh_view_uses_the_settings_knob():
    """The refresh_view decorator must resolve its rate through
    config.ratelimits (lazily, per request) — not a hardcoded literal."""
    import inspect

    import apps.core.views.auth as auth_module

    source = inspect.getsource(auth_module)
    assert 'rate="config.ratelimits.refresh_ip"' in source, (
        "refresh_view must use the settings-driven dotted-path rate"
    )
    assert 'rate="20/minute"' not in source, (
        "the hardcoded refresh literal must be gone"
    )


def test_development_raises_refresh_and_anon_budgets():
    """Development raises the refresh + DRF anonymous/user budgets so the
    local e2e suite is not throttled; testing keeps them off."""
    from config.settings import development

    assert development.REFRESH_RATELIMIT_IP == "240/minute"
    rates = development.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    assert rates["anon"] == "240/minute"
    assert rates["user"] == "600/minute"


def test_base_throttle_posture_unchanged():
    """The production posture in base must stay 20/min anon, 100/min user —
    only the development budget moves (guardrail never weakened)."""
    from config.settings import base

    rates = base.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    assert rates["anon"] == "20/minute"
    assert rates["user"] == "100/minute"
    assert base.REFRESH_RATELIMIT_IP == "20/minute"


def test_custom_exception_handler_is_active():
    """P7/F-19 posture gate: DRF must resolve the custom exception handler.

    The pre-P7 settings used the wrong key ("DEFAULT_EXCEPTION_HANDLER" —
    DRF's key is "EXCEPTION_HANDLER", not namespaced under DEFAULT_*), so
    api_settings silently fell back to DRF's default handler and every
    LedgerSGException that wrap_response re-raises surfaced as an unhandled
    500 instead of its mapped status code (403/502/...).
    """
    from rest_framework.settings import api_settings

    handler = api_settings.EXCEPTION_HANDLER
    assert getattr(handler, "__module__", "") == "common.exceptions", (
        f"api_settings.EXCEPTION_HANDLER resolved to {handler!r} — "
        "the custom exception handler is NOT active"
    )


def test_wrap_response_exceptions_map_to_status_codes():
    """A LedgerSGException raised inside a wrapped view must produce its
    mapped status code (not an unhandled 500) — end-to-end through DRF
    dispatch with the custom exception handler active."""
    from rest_framework.test import APIRequestFactory
    from rest_framework.views import APIView
    from rest_framework.permissions import AllowAny
    from common.exceptions import UnauthorizedOrgAccess, PeppolTransmissionError

    class ExplodingView(APIView):
        authentication_classes = []
        permission_classes = [AllowAny]

        def post(self, request):
            raise UnauthorizedOrgAccess("nope")

    request = APIRequestFactory().post("/x")
    response = ExplodingView.as_view()(request)
    assert response.status_code == 403, response.data

    class PeppolView(APIView):
        authentication_classes = []
        permission_classes = [AllowAny]

        def post(self, request):
            raise PeppolTransmissionError("AP down")

    response = PeppolView.as_view()(APIRequestFactory().post("/x"))
    assert response.status_code == 502, response.data
