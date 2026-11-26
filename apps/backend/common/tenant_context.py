"""
RLS tenant context for non-request execution paths (P17/BE-H3).

The request path sets `app.current_org_id` / `app.current_user_id` via
TenantContextMiddleware (SET LOCAL inside the request's atomic block).
Celery workers have no middleware: every tenant-table SELECT policy is
`USING (org_id = core.current_org_id())` and `core.current_org_id()`
returns NULL when the GUC is unset — a worker querying tenant rows sees
NOTHING (task retries 3x and dies while the API already answered
`{"sent": true}`). Dev/test never see this because
`CELERY_TASK_ALWAYS_EAGER=True` runs task bodies synchronously inside the
request transaction where the context IS set; production disables eager
mode (config/settings/production.py) — the feature is dead there.

This module gives task bodies the same contract the middleware provides:

    with tenant_context(org_id):
        ...  # tenant queries + writes, RLS-enforced

Semantics (identical to the P14/C-1 organisation-service pattern):
- `set_config(..., true)` is transaction-scoped; the helper opens its own
  `transaction.atomic()` so the setting lives exactly as long as the task
  body's work.
- Inside an existing transaction (eager mode inside the request) the
  atomic block becomes a savepoint and the GUC re-set is a same-value
  no-op for the org the middleware already set — dev/test behavior is
  unchanged.
- `user_id` is optional: pass it when the task knows the acting user so
  audit triggers attribute rows; omit it when the task has no user
  context (audit rows record NULL attribution, honestly).
"""

from contextlib import contextmanager
from typing import Any
from uuid import UUID

from django.db import connection, transaction


@contextmanager
def tenant_context(org_id: UUID | str, user_id: UUID | str | None = None):
    """Run a block under the RLS tenant GUCs (see module docstring)."""
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.current_org_id', %s, true)",
                [str(org_id)],
            )
            if user_id is not None:
                cursor.execute(
                    "SELECT set_config('app.current_user_id', %s, true)",
                    [str(user_id)],
                )
        yield


def queue_task(task, *args, **kwargs):
    """Dispatch a Celery task without racing the caller's transaction.

    P17/BE-H3: the three dispatch seams fired `.delay()` INSIDE the
    request transaction — a real worker could dequeue the task and query
    rows the request had not committed yet (0 rows → retry → dead).

    Eager mode (development/testing: `CELERY_TASK_ALWAYS_EAGER=True`)
    dispatches immediately and synchronously — task bodies own their
    tenant context now, so running inside the request transaction is
    safe, and the mocked-`.delay` test contracts keep their exact
    semantics. Returns the task result (EagerResult) in that mode.
    Non-eager mode defers to `transaction.on_commit` so the worker only
    ever sees committed rows (returns None — the result handle does not
    exist before dispatch); outside a transaction (shell, cron) it
    dispatches immediately and returns the AsyncResult.
    """
    from django.conf import settings

    eager = bool(getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False))
    if eager or not connection.in_atomic_block:
        return task.delay(*args, **kwargs)
    transaction.on_commit(lambda: task.delay(*args, **kwargs))
    return None
