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


# =============================================================================
# P11 live gate — the register throttle gets the same settings-knob treatment
# =============================================================================

def test_register_throttle_is_a_settings_knob():
    """RED for the P11 live gate: the register endpoint's throttle must be
    a settings knob (base default 5/hour), not a decorator literal — the
    P10 spec's self-serve loop registers one user per `test:e2e:full` run,
    and re-running the suite against the local dev server 429'd the
    register step with no way to raise the budget without editing code
    (same class as the P6/E-1 refresh knob)."""
    from config.settings import base

    assert getattr(base, "REGISTER_RATELIMIT_IP", None) == "5/hour", (
        "base must define the register throttle knob with the documented "
        "SEC-002 posture (5/hour) — production is never weakened"
    )

    from config import ratelimits

    assert callable(getattr(ratelimits, "register_ip", None)), (
        "config.ratelimits must expose the dotted-path callable the "
        "register decorator references"
    )


def test_register_view_uses_the_settings_knob():
    """The register_view decorator must resolve its rate through
    config.ratelimits (lazily, per request) — not the hardcoded literal."""
    import inspect

    import apps.core.views.auth as auth_module

    source = inspect.getsource(auth_module)
    assert 'rate="config.ratelimits.register_ip"' in source, (
        "register_view must use the settings-driven dotted-path rate"
    )
    assert 'rate="5/hour"' not in source, (
        "the hardcoded register literal must be gone"
    )


def test_development_raises_register_budget():
    """Development raises the register budget so repeated local e2e runs
    are not throttled; testing keeps rate limiting off entirely."""
    from config.settings import development

    assert development.REGISTER_RATELIMIT_IP == "120/hour"


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
    from rest_framework.permissions import AllowAny
    from rest_framework.test import APIRequestFactory
    from rest_framework.views import APIView

    from common.exceptions import PeppolTransmissionError, UnauthorizedOrgAccess

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


# ── P14/H-9: the service settings module gates its key like production ─────

def _load_service_settings(monkeypatch, secret, hosts=None):
    """Import config.settings.service with an overridden SECRET_KEY.

    Session-30 ordering lesson: reload BASE first, then import service —
    importing service first executes it against the stale cached base
    module and raises before the new env is in effect.
    """
    import importlib
    import sys

    monkeypatch.setenv("SECRET_KEY", secret)
    if hosts is not None:
        monkeypatch.setenv("ALLOWED_HOSTS", hosts)
    for mod in list(sys.modules):
        if mod.startswith("config.settings") or mod == "config":
            del sys.modules[mod]
    import config.settings.base as base
    importlib.reload(base)
    import config.settings.service as service
    importlib.reload(service)
    return service


def test_service_rejects_default_secret_key(monkeypatch):
    """P14/H-9: the Docker path's service module must enforce the same
    key-strength gate as production (the Dockerfile previously generated
    SECRET_KEY=django-secret-key-for-hf-space-$(date +%s) — predictable)."""
    import pytest
    from django.core.exceptions import ImproperlyConfigured

    with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
        _load_service_settings(monkeypatch, "django-secret-key-for-hf-space-1760000000")


def test_service_rejects_short_secret_key(monkeypatch):
    """P14/H-9: a short key is brute-forceable for HS256 JWT forging."""
    import pytest
    from django.core.exceptions import ImproperlyConfigured

    with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
        _load_service_settings(monkeypatch, "short-service-key")


def test_service_boots_with_a_strong_key(monkeypatch):
    """Control: a strong key boots, and ALLOWED_HOSTS comes from env (the
    wildcard default is gone — H-9)."""
    strong = "svc-" + "k" * 80
    svc = _load_service_settings(monkeypatch, strong, hosts="localhost,127.0.0.1")
    assert svc.SECRET_KEY == strong
    assert svc.ALLOWED_HOSTS == ["localhost", "127.0.0.1"]


# =============================================================================
# P16/BE-H1 — the tenant/audit middleware must survive into EVERY
# HTTP-serving settings module (service.py rebuilt its MIDDLEWARE list from
# scratch and dropped all four base entries: the Docker/script API path ran
# with no org context — every org-scoped endpoint 403s for non-superusers,
# RLS sees NULL on every request, and the audit trigger loses attribution)
# =============================================================================

TENANT_MIDDLEWARE = "common.middleware.tenant_context.TenantContextMiddleware"
AUDIT_MIDDLEWARE = "common.middleware.audit_context.AuditContextMiddleware"
CSP_MIDDLEWARE = "csp.middleware.CSPMiddleware"
WHITENOISE_MIDDLEWARE = "whitenoise.middleware.WhiteNoiseMiddleware"


def _load_settings_module(name):
    """Import a settings module fresh (cache-cleared) — the file's
    _load_production_settings pattern, generalized."""
    import sys

    for mod in list(sys.modules):
        if mod.startswith("config.settings"):
            del sys.modules[mod]
    return __import__(f"config.settings.{name}", fromlist=["*"])


def test_base_has_the_tenant_audit_csp_whitenoise_middleware():
    """Control: the base stack carries all four (the source of truth)."""
    base = _load_settings_module("base")
    for entry in (TENANT_MIDDLEWARE, AUDIT_MIDDLEWARE, CSP_MIDDLEWARE, WHITENOISE_MIDDLEWARE):
        assert entry in base.MIDDLEWARE, f"{entry} missing from base MIDDLEWARE"


def test_development_keeps_the_tenant_audit_middleware():
    dev = _load_settings_module("development")
    assert TENANT_MIDDLEWARE in dev.MIDDLEWARE
    assert AUDIT_MIDDLEWARE in dev.MIDDLEWARE


def test_production_keeps_the_tenant_audit_middleware(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "p" * 64)
    prod = _load_settings_module("production")
    assert TENANT_MIDDLEWARE in prod.MIDDLEWARE
    assert AUDIT_MIDDLEWARE in prod.MIDDLEWARE


def test_service_keeps_the_tenant_audit_middleware(monkeypatch):
    """RED for P16/BE-H1: the shipped Docker/script entrypoint must serve
    the API through the SAME middleware stack as every other mode —
    org context (RLS), audit attribution, CSP and static files included.
    service.py must DERIVE its list from base, never rebuild it."""
    monkeypatch.setenv("SECRET_KEY", "s" * 64)
    monkeypatch.setenv("ALLOWED_HOSTS", "localhost,127.0.0.1")
    svc = _load_settings_module("service")
    for entry in (TENANT_MIDDLEWARE, AUDIT_MIDDLEWARE, CSP_MIDDLEWARE, WHITENOISE_MIDDLEWARE):
        assert entry in svc.MIDDLEWARE, (
            f"{entry} missing from service MIDDLEWARE — the Docker/script "
            "API path runs without it (P16/BE-H1: no org context, no audit "
            "attribution, no CSP)"
        )


def test_admin_route_is_gated_off_in_testing_and_production(monkeypatch):
    """P17/BE-L3: /admin/ must not mount in non-development settings — the
    route carried a session-auth + password-reset surface into every mode
    while its own comment said "development only in production"."""
    import importlib
    import sys

    import pytest
    from django.conf import settings as dj_settings
    from django.urls import Resolver404, resolve

    # The URLconf reads ENABLE_ADMIN at import time — reload it for each
    # posture under test (the settings-gate pattern of this module).
    def _reload_urlconf(enable_admin: bool):
        for mod in list(sys.modules):
            if mod.startswith("config.settings") or mod == "config.urls":
                del sys.modules[mod]
        import config.settings.testing as testing_settings

        importlib.reload(testing_settings)
        monkeypatch.setattr(dj_settings, "ENABLE_ADMIN", enable_admin, raising=False)
        import config.urls as urlconf

        importlib.reload(urlconf)
        from django.urls import clear_url_caches

        clear_url_caches()
        return urlconf

    urlconf = _reload_urlconf(enable_admin=False)
    assert urlconf.urlpatterns and not any(
        getattr(p, "pattern", None) and str(p.pattern) == "admin/" for p in urlconf.urlpatterns
    ), "the admin route must not mount when ENABLE_ADMIN is false"
    with pytest.raises(Resolver404):
        resolve("/admin/login/")

    urlconf = _reload_urlconf(enable_admin=True)
    match = resolve("/admin/login/")
    assert "admin" in match.app_name or "admin" in match.view_name


def test_production_uses_storages_not_legacy_staticfiles_storage(monkeypatch):
    """P17/BE-L4: Django 6 reads STORAGES only — STATICFILES_STORAGE is a
    silent no-op, so the intended WhiteNoise manifest/compressed storage
    never actually engaged. Production must set the modern dict."""
    import importlib
    import sys

    for mod in list(sys.modules):
        if mod.startswith("config.settings"):
            del sys.modules[mod]
    monkeypatch.setenv("SECRET_KEY", "x" * 56)
    import config.settings.production as prod

    importlib.reload(prod)
    storages = getattr(prod, "STORAGES", None)
    assert storages is not None, "production must define STORAGES (Django 6 contract)"
    assert (
        storages.get("staticfiles", {}).get("BACKEND")
        == "whitenoise.storage.CompressedManifestStaticFilesStorage"
    ), storages
