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
