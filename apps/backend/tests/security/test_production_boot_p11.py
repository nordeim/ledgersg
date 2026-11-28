"""
P11/C-2 — production settings boot truth.

The production settings must actually boot on a fresh host:

- The cache backend must resolve to an importable module. The previous
  override pointed at django_redis.cache.RedisCache — a dependency that is
  in neither pyproject nor uv.lock, so every org-scoped request (tenant
  cache + django-ratelimit) crashed with ModuleNotFoundError.
- The LOGGING file handler path must derive from a LOG_DIR knob the
  deployer creates (DEPLOYMENT.md ships the mkdir step) instead of a
  hardcoded /var/log path that crashes django.setup() when missing.
- Importing production must not mutate base's shared LOGGING dict in
  place (the copy-on-write class P10 already fixed in development.py).
"""

import copy
import importlib
import sys

STRONG_KEY = "a" * 64


def _import_base_then_production(monkeypatch, **env):
    """Import base, snapshot LOGGING, then import production fresh.

    Returns (base, snapshot, production) — the snapshot taken BEFORE
    production's `from .base import *` side effects can run.
    """
    for mod in list(sys.modules):
        if mod.startswith("config.settings"):
            del sys.modules[mod]

    monkeypatch.setenv("SECRET_KEY", STRONG_KEY)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    import config.settings.base as base

    snapshot = copy.deepcopy(base.LOGGING)

    import config.settings.production as production

    return base, snapshot, production


class TestProductionBootTruth:
    def test_cache_backend_module_resolves(self, monkeypatch):
        """RED for C-2(1): the production cache backend must be importable.

        django_redis.cache was never a declared dependency — resolving
        the backend class crashed with ModuleNotFoundError on every
        org-scoped request.
        """
        _, _, production = _import_base_then_production(monkeypatch)

        backend_path = production.CACHES["default"]["BACKEND"]
        module_name, _, _class = backend_path.rpartition(".")
        importlib.import_module(module_name)  # must not raise

    def test_importing_production_does_not_mutate_base_logging(
        self, monkeypatch
    ):
        """RED for C-2(3): production must copy-on-write LOGGING.

        The old code assigned into LOGGING["handlers"]["file"] — the SHARED
        base dict — so importing production corrupted every other settings
        module imported afterwards.
        """
        base, snapshot, _ = _import_base_then_production(monkeypatch)

        assert base.LOGGING == snapshot, (
            "importing config.settings.production must not mutate "
            "config.settings.base.LOGGING in place"
        )

    def test_log_dir_env_flows_into_file_handler_path(self, monkeypatch):
        """RED for C-2(2): LOG_DIR override must drive the handler filename."""
        _, _, production = _import_base_then_production(
            monkeypatch, LOG_DIR="/tmp/ledgersg-p11-gate"
        )

        filename = production.LOGGING["handlers"]["file"]["filename"]
        assert filename == "/tmp/ledgersg-p11-gate/django.log", (
            f"LOG_DIR must flow into the file handler path (got {filename})"
        )

    def test_log_dir_default_is_var_log_ledgersg(self, monkeypatch):
        """The LOG_DIR default keeps the documented deploy path."""
        monkeypatch.delenv("LOG_DIR", raising=False)
        _, _, production = _import_base_then_production(monkeypatch)

        assert production.LOG_DIR == "/var/log/ledgersg"
        assert (
            production.LOGGING["handlers"]["file"]["filename"]
            == "/var/log/ledgersg/django.log"
        )

    def test_file_handler_wired_to_django_and_ledgersg_loggers(
        self, monkeypatch
    ):
        """Both loggers keep console AND file handlers (as before the fix)."""
        _, _, production = _import_base_then_production(monkeypatch)

        assert production.LOGGING["loggers"]["django"]["handlers"] == [
            "console",
            "file",
        ]
        assert production.LOGGING["loggers"]["ledgersg"]["handlers"] == [
            "console",
            "file",
        ]

    def test_base_console_handler_survives_production_import(
        self, monkeypatch
    ):
        """Copy-on-write must not drop base's console handler definition."""
        base, _, production = _import_base_then_production(monkeypatch)

        assert "console" in production.LOGGING["handlers"]
        assert (
            production.LOGGING["handlers"]["console"]
            == base.LOGGING["handlers"]["console"]
        )
