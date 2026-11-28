# LedgerSG config package

# P38/BE-P38-H2: the canonical Celery+Django wiring (Celery's "First steps
# with Django") — the package __init__ imports the app so EVERY Django
# process (runserver, gunicorn, wsgi) loads it at startup and every
# @shared_task binds to the CONFIGURED app. The pre-P38 empty __init__
# left nothing importing config.celery in the web process: the shared
# tasks bound to Celery's DEFAULT app (broker amqp://localhost:5672 via
# kombu's fallback, task_always_eager=False) — the first real queue_task
# dispatch on a Peppol-configured org 500'd with Connection refused
# (reproduced live; the worker escaped only through celery -A config's
# fallback search of config.celery.app).
from .celery import app as celery_app

__all__ = ("celery_app",)
