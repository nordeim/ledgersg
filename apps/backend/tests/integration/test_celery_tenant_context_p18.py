"""
P18 Celery tenant-context completion + the on-commit coverage gate.

BE-M1: BE-H3 covered only 2 of 5 task bodies — the three remaining
    Peppol tasks (retry_failed_transmission_task,
    check_transmission_status_task, cleanup_old_transmission_logs_task)
    run unscoped on real workers, where the strict
    `org_id = core.current_org_id()` policies on
    gst.peppol_transmission_log make them see 0 rows (retry-to-death /
    silent None / 0 deletes). The task signatures now carry the org
    explicitly (the transmit task's pattern) and the bodies open the
    tenant context.
BE-L3: org/document-deleted-mid-flight is a PERMANENT error — the email
    task retried DoesNotExist 3x60s before dying while the API had
    already answered {"sent": true}. Permanent failures now return a
    terminal result without retry.
BE-M7: the production-only `on_commit` branch of queue_task had zero
    test coverage — every test runs eager (immediate .delay). A
    regression in the deferral (dispatch despite rollback) would be
    invisible to CI.
"""

from unittest.mock import patch

import pytest
from django.db import connection, transaction

from tests.conftest import create_test_contact, create_test_invoice


class _FakeStatusResult:
    success = False
    status = type("S", (), {"value": "FAILED"})()
    error_code = None
    error_message = "p18 probe"


class TestRetryTaskTenantContextP18:
    @pytest.mark.django_db
    def test_retry_task_opens_tenant_context(self, test_organisation, test_fiscal_period):
        """The retry body must run under the RLS tenant GUC — a real
        worker with a NULL GUC sees 0 rows on the strict
        peppol_transmission_log policies and retries to death."""
        from apps.peppol.tasks import retry_failed_transmission_task

        org = test_organisation
        contact = create_test_contact(org, is_customer=True)
        invoice = create_test_invoice(org, contact, status="APPROVED")
        from apps.peppol.models import PeppolTransmissionLog

        log = PeppolTransmissionLog.objects.create(
            org=org, document_id=invoice.id, status="FAILED"
        )
        seen = {}

        class _ProbeService:
            def __init__(self, *a, **kw):
                pass

            def retry_transmission(self, transmission_log_id):
                with connection.cursor() as cursor:
                    cursor.execute("SELECT current_setting('app.current_org_id', true)")
                    seen["org"] = cursor.fetchone()[0]
                log.attempt_number = 2
                return log

        with patch(
            "apps.peppol.services.transmission_service.TransmissionService",
            _ProbeService,
        ):
            retry_failed_transmission_task.apply(
                args=[str(log.id), str(org.id)]
            ).get()

        assert seen.get("org") == str(org.id), (
            "retry_failed_transmission_task must open tenant_context(org_id) "
            f"(BE-M1; saw {seen.get('org')!r})"
        )

    @pytest.mark.django_db
    def test_retry_task_missing_log_is_terminal_no_retry(self, test_organisation):
        """BE-L3 class: a deleted log is permanent — the task returns a
        terminal FAILED result without burning the retry cycle."""
        from apps.peppol.tasks import retry_failed_transmission_task

        result = retry_failed_transmission_task.apply(
            args=["00000000-0000-0000-0000-000000000000", str(test_organisation.id)]
        ).get()

        assert result.get("success") is False
        assert "not found" in str(result.get("error", "")).lower()


class TestCheckStatusTaskTenantContextP18:
    @pytest.mark.django_db
    def test_check_status_task_opens_tenant_context(
        self, test_organisation, test_fiscal_period
    ):
        """The status-check body must run under the RLS tenant GUC — the
        log lookup itself is RLS-scoped (NULL GUC → None returned
        silently)."""
        from apps.peppol.models import PeppolTransmissionLog
        from apps.peppol.tasks import check_transmission_status_task

        org = test_organisation
        contact = create_test_contact(org, is_customer=True)
        invoice = create_test_invoice(org, contact, status="APPROVED")
        message_uuid = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        PeppolTransmissionLog.objects.create(
            org=org,
            document_id=invoice.id,
            status="TRANSMITTING",
            peppol_message_id=message_uuid,
        )
        seen = {}

        class _ProbeAdapter:
            def check_status(self, message_id):
                with connection.cursor() as cursor:
                    cursor.execute("SELECT current_setting('app.current_org_id', true)")
                    seen["org"] = cursor.fetchone()[0]
                return _FakeStatusResult()

        class _ProbeService:
            def __init__(self, *a, **kw):
                pass

            def get_adapter_for_org(self, org_id):
                return _ProbeAdapter()

        with patch(
            "apps.peppol.services.transmission_service.TransmissionService",
            _ProbeService,
        ):
            result = check_transmission_status_task.apply(
                args=[message_uuid, str(org.id)]
            ).get()

        assert seen.get("org") == str(org.id), (
            "check_transmission_status_task must open tenant_context(org_id) "
            f"(BE-M1; saw {seen.get('org')!r})"
        )
        assert result["message_id"] == message_uuid

    @pytest.mark.django_db
    def test_check_status_task_requires_org_id(self):
        """The org-scoped contract: the signature now carries org_id (the
        transmit task's pattern) — a NULL-GUC worker cannot resolve the
        org from the RLS-blocked log row."""
        import inspect

        from apps.peppol.tasks import check_transmission_status_task

        params = inspect.signature(check_transmission_status_task).parameters
        assert "org_id" in params, (
            "check_transmission_status_task must take org_id explicitly "
            "(BE-M1: the log lookup itself is RLS-scoped)"
        )


class TestCleanupTaskTenantContextP18:
    @pytest.mark.django_db
    def test_cleanup_task_with_org_runs_scoped(self, test_organisation):
        """With an org_id the cleanup runs under that org's tenant context
        (per-org dispatch); without one it must say so loudly and delete
        nothing under the RLS-bound app role — never silently."""
        from apps.peppol.models import PeppolTransmissionLog
        from apps.peppol.tasks import cleanup_old_transmission_logs_task

        org = test_organisation
        seen = {}
        real_filter = PeppolTransmissionLog.objects.filter

        def _probe_filter(*args, **kwargs):
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_setting('app.current_org_id', true)")
                seen["org"] = cursor.fetchone()[0]
            return real_filter(*args, **kwargs)

        with patch.object(
            PeppolTransmissionLog.objects, "filter", side_effect=_probe_filter
        ):
            cleanup_old_transmission_logs_task.apply(args=[90, str(org.id)]).get()

        assert seen.get("org") == str(org.id), (
            "cleanup_old_transmission_logs_task(org_id=...) must open "
            f"tenant_context(org_id) (BE-M1; saw {seen.get('org')!r})"
        )

    @pytest.mark.django_db
    def test_cleanup_task_without_org_returns_zero_with_warning(self, caplog):
        """Without an org the task cannot see any rows under the RLS-bound
        app role — the contract is an explicit WARNING + 0, never a silent
        sweep that looks successful."""
        import logging

        from apps.peppol.tasks import cleanup_old_transmission_logs_task

        with caplog.at_level(logging.WARNING, logger="apps.peppol.tasks"):
            count = cleanup_old_transmission_logs_task.apply(args=[90]).get()

        assert count == 0
        assert any("org" in r.message for r in caplog.records), (
            "the unscoped cleanup must log a WARNING naming the org-context "
            "requirement (BE-M1) — the pre-P18 contract was silent death"
        )


class TestEmailTaskPermanentFailureP18:
    @pytest.mark.django_db
    def test_deleted_document_is_terminal_not_retried(self, test_organisation):
        """BE-L3: a document deleted mid-flight is a PERMANENT failure —
        the task must return a terminal result, not retry 3x60s while the
        API already answered {"sent": true}."""
        from apps.invoicing.tasks import send_invoice_email_task

        result = send_invoice_email_task.apply(
            args=[
                str(test_organisation.id),
                "00000000-0000-0000-0000-000000000000",
                ["to@example.com"],
            ]
        ).get()

        assert isinstance(result, dict), (
            "a permanent DoesNotExist must return a terminal result dict, "
            "not raise/retry (BE-L3)"
        )
        assert result.get("success") is False


class TestQueueTaskOnCommitP18:
    @pytest.mark.django_db
    def test_delay_fires_only_after_commit(
        self, test_organisation, django_capture_on_commit_callbacks
    ):
        """BE-M7: under ALWAYS_EAGER=False inside an atomic block, .delay
        must fire ONLY on commit — this is the branch real workers live
        in; it had zero test coverage (every test ran eager)."""
        from django.test.utils import override_settings

        from apps.peppol.tasks import transmit_peppol_invoice_task
        from common.tenant_context import queue_task

        with override_settings(CELERY_TASK_ALWAYS_EAGER=False), patch.object(
            transmit_peppol_invoice_task, "delay"
        ) as delay:
            with django_capture_on_commit_callbacks(execute=True):
                with transaction.atomic():
                    queue_task(
                        transmit_peppol_invoice_task, "log-id", str(test_organisation.id)
                    )
                    assert delay.call_count == 0, (
                        ".delay must NOT fire while the transaction is open"
                    )
            assert delay.call_count == 1, (
                ".delay must fire exactly once when the transaction commits"
            )

    @pytest.mark.django_db
    def test_delay_never_fires_on_rollback(
        self, test_organisation, django_capture_on_commit_callbacks
    ):
        """BE-M7 (the money side): a rolled-back transaction must never
        dispatch — the worker would see rows that do not exist."""
        from django.test.utils import override_settings

        from apps.peppol.tasks import transmit_peppol_invoice_task
        from common.tenant_context import queue_task

        with override_settings(CELERY_TASK_ALWAYS_EAGER=False), patch.object(
            transmit_peppol_invoice_task, "delay"
        ) as delay:
            with django_capture_on_commit_callbacks(execute=True):
                with transaction.atomic():
                    queue_task(
                        transmit_peppol_invoice_task, "log-id", str(test_organisation.id)
                    )
                    transaction.set_rollback(True)
            assert delay.call_count == 0, (
                ".delay must NOT fire when the transaction rolled back"
            )
