"""
Settings copy-on-write gates (P13/B-7).

The P10 crash class: importing one settings module must never mutate the
shared dicts of another (SIMPLE_JWT, DATABASES). The P11 remediation made
LOGGING and the middleware lists copy-on-write, but SIMPLE_JWT (dev) and
DATABASES (dev/testing/production) still bind and mutate the base dicts in
place — importing development changes base's access-token lifetime and DB
settings for every later import in the same process (the exact mechanism
that once crashed a 79-test middleware cascade).

The gates assert OBJECT IDENTITY, not values: value comparisons can be
masked by a .env file resolving both sides to the same string.
"""

import importlib
import sys


def _fresh_import(module: str):
    """Import a settings module with a pristine config.settings.base."""
    for name in list(sys.modules):
        if name == "config.settings.base" or name.startswith("config.settings."):
            del sys.modules[name]
    return importlib.import_module(module)


def test_development_rebinds_simple_jwt_not_mutates():
    """RED for P13/B-7: development's SIMPLE_JWT must be a fresh dict."""
    base = _fresh_import("config.settings.base")
    dev = _fresh_import("config.settings.development")
    base2 = sys.modules["config.settings.base"]

    assert dev.SIMPLE_JWT is not base2.SIMPLE_JWT, (
        "config.settings.development shares (and mutates) base's SIMPLE_JWT "
        "dict — copy-on-write violation (the P10 crash class)."
    )
    # baseline lifetime must survive the dev import untouched
    assert (
        base2.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]
        == base.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]
    ), "base's ACCESS_TOKEN_LIFETIME changed when development was imported"


def test_development_rebinds_databases_not_mutates():
    """RED for P13/B-7: development's DATABASES dicts must be fresh objects."""
    dev = _fresh_import("config.settings.development")
    base2 = sys.modules["config.settings.base"]

    assert dev.DATABASES is not base2.DATABASES, (
        "config.settings.development shares base's DATABASES dict — "
        "copy-on-write violation."
    )
    assert dev.DATABASES["default"] is not base2.DATABASES["default"], (
        "config.settings.development mutates base's DATABASES['default'] "
        "inner dict in place — copy-on-write violation (the P10 crash class)."
    )


def test_testing_rebinds_databases_not_mutates():
    """RED for P13/B-7: testing's DATABASES dicts must be fresh objects."""
    _fresh_import("config.settings.base")
    testing = _fresh_import("config.settings.testing")
    base2 = sys.modules["config.settings.base"]

    assert testing.DATABASES is not base2.DATABASES, (
        "config.settings.testing shares base's DATABASES dict — "
        "copy-on-write violation."
    )
    assert testing.DATABASES["default"] is not base2.DATABASES["default"], (
        "config.settings.testing mutates base's DATABASES['default'] "
        "inner dict in place — copy-on-write violation."
    )
