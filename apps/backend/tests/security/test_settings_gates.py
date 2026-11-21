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
