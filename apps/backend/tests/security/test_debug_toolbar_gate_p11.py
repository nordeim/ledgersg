"""
P11/H-5 — the debug_toolbar gates align.

config/urls.py gated the __debug__ URLconf import on settings.DEBUG while
development.py gates INSTALLED_APPS on the DEBUG_TOOLBAR knob. The
documented backend env combination DEBUG=true + DEBUG_TOOLBAR=false
therefore crashed every manage.py command with "Model class ... isn't in
an application in INSTALLED_APPS". The single knob is INSTALLED_APPS —
the same gate development.py itself uses.
"""

import importlib
import sys
import types

from django.conf import settings as django_settings


def _import_urls_fresh():
    """Import config.urls with a clean module cache."""
    sys.modules.pop("config.urls", None)
    return importlib.import_module("config.urls")


class TestDebugToolbarGate:
    def test_debug_true_without_toolbar_app_imports_cleanly(self, settings):
        """RED for H-5: DEBUG=true + debug_toolbar NOT installed must boot.

        The old urls.py gate (settings.DEBUG) imported debug_toolbar's
        URLconf while the app was absent from INSTALLED_APPS — the exact
        crash of the documented DEBUG=true + DEBUG_TOOLBAR=false env.
        """
        settings.DEBUG = True
        settings.INSTALLED_APPS = [
            app for app in settings.INSTALLED_APPS if app != "debug_toolbar"
        ]

        urls = _import_urls_fresh()  # today: RuntimeError

        # The __debug__ routes are simply absent — no crash, no routes.
        assert not any(
            "__debug__" in str(pattern.pattern)
            for pattern in urls.urlpatterns
        )

    def test_urls_mount_when_toolbar_app_listed(self, monkeypatch):
        """With the app in INSTALLED_APPS, the __debug__ routes mount.

        The real app's registry populate is incompatible with the suite's
        --no-migrations runner (debug_toolbar's ready() calls
        MIGRATION_MODULES.setdefault, absent on DisableMigrations), so the
        app-present path is exercised with a stubbed module — what is
        under test is the URLCONF gate's behavior, not the app registry.
        """
        stub_urls = types.ModuleType("debug_toolbar.urls")
        stub = types.ModuleType("debug_toolbar")
        stub.urls = stub_urls
        monkeypatch.setitem(sys.modules, "debug_toolbar", stub)
        # A plain attribute shadow on the settings singleton — the URLconf
        # reads settings.INSTALLED_APPS at import time (same object).
        monkeypatch.setattr(
            django_settings, "INSTALLED_APPS", ["debug_toolbar"], raising=False
        )

        urls = _import_urls_fresh()

        assert any(
            "__debug__" in str(pattern.pattern)
            for pattern in urls.urlpatterns
        ), "the __debug__ routes must mount when the app is installed"
