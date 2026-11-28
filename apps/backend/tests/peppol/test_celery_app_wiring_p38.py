"""
P38/BE-P38-H2: the Celery app must load in the web process.

The canonical Celery+Django wiring (Celery's "First steps with Django"):
the project package's __init__ imports the app, so EVERY Django process
(runserver, gunicorn, wsgi) loads the configured app at startup and every
@shared_task binds to it. The pre-P38 config/__init__.py was empty and
NOTHING in the backend tree imported config.celery — in a web process the
shared tasks bound to Celery's DEFAULT app (broker amqp://localhost:5672
via kombu's fallback, task_always_eager=False), so the first real
queue_task dispatch on a Peppol-configured org 500'd with
Connection refused (reproduced live this session on :8000; the worker
escaped only through celery -A config's fallback search).

RED on the base tree: importing config wires nothing — the current app
stays "default" with no broker_url. GREEN after the canonical import.
Config-level gates only — no broker connection is made.
"""

from celery import current_app
from django.conf import settings


class TestConfigPackageLoadsTheCeleryApp:
    """Importing the config package (what every Django process does) must
    load the configured Celery app — the shared tasks bind to it."""

    def test_config_import_exposes_the_ledgersg_app(self):
        """import config -> celery.current_app is the configured app (RED on
        the base tree: the empty __init__ leaves the "default" app)."""
        import config  # noqa: F401 — the import itself is the wiring

        assert current_app.main == "ledgersg", (
            f"the config package must load the configured app; got "
            f"{current_app.main!r} (the 'default' app means no process "
            "wiring — every web-process dispatch would hit the amqp "
            "fallback broker)"
        )

    def test_shared_transmit_task_binds_to_the_configured_app(self):
        """The transmit task's app is the configured one, carrying the
        settings broker (never the kombu amqp fallback)."""
        from apps.peppol.tasks import transmit_peppol_invoice_task

        app = transmit_peppol_invoice_task._get_app()

        assert app.main == "ledgersg"
        # The broker is the settings Redis URL — never the amqp:// fallback
        # (broker_url None means kombu's default: amqp://guest@localhost:5672).
        assert app.conf.broker_url, "the broker must be configured, not kombu's amqp fallback"
        assert app.conf.broker_url == settings.CELERY_BROKER_URL
        assert app.conf.broker_url.startswith("redis://")

    def test_eager_contract_matches_the_settings_namespace(self):
        """CELERY_TASK_ALWAYS_EAGER flows to the app (True under testing —
        the inline dispatch contract queue_task documents)."""
        assert settings.CELERY_TASK_ALWAYS_EAGER is True
        assert current_app.conf.task_always_eager is True
