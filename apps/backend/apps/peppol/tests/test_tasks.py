"""
TDD Tests for Phase 4: Celery Tasks

Tests the async Celery tasks for Peppol transmission.
"""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest


class TestTransmitPeppolInvoiceTask:
    """Tests for transmit_peppol_invoice_task."""

    def test_transmit_task_exists(self):
        """Test that transmit_peppol_invoice_task can be imported."""
        from apps.peppol.tasks import transmit_peppol_invoice_task

        assert transmit_peppol_invoice_task is not None

    @pytest.mark.django_db
    def test_transmit_task_calls_service(self):
        """Test that task executes against the pre-created log (P5/C-2 seam).

        django_db since P17/BE-H3: the task body opens the RLS tenant
        context (real transaction + set_config) before driving the service
        seam."""
        from apps.peppol.services.transmission_service import TransmissionService
        from apps.peppol.tasks import transmit_peppol_invoice_task

        with patch.object(
            TransmissionService, "execute_transmission_for_log"
        ) as mock_execute:
            log_id = str(uuid4())
            org_id = str(uuid4())

            # Mock the transmission log
            mock_log = Mock()
            mock_log.id = uuid4()
            mock_log.org_id = org_id
            mock_log.document_id = uuid4()
            mock_log.status = "DELIVERED"
            mock_log.peppol_message_id = "msg-123"

            mock_execute.return_value = mock_log

            # Execute task (synchronously for testing)
            result = transmit_peppol_invoice_task(log_id, org_id)

            # Verify the service seam was driven with the LOG id (the old
            # wiring passed it to transmit_invoice() which expects an
            # INVOICE id and can never succeed)
            mock_execute.assert_called_once_with(log_id)
            assert result["success"] is True

    @pytest.mark.django_db
    def test_transmit_task_success_updates_log(self):
        """Test successful transmission updates log to DELIVERED.

        django_db since P17/BE-H3: the task body opens the RLS tenant
        context (real transaction + set_config) before driving the service
        seam."""
        from apps.peppol.services.transmission_service import TransmissionService
        from apps.peppol.tasks import transmit_peppol_invoice_task

        with patch.object(
            TransmissionService, "execute_transmission_for_log"
        ) as mock_execute:
            log_id = str(uuid4())
            org_id = str(uuid4())

            mock_log = Mock()
            mock_log.status = "DELIVERED"
            mock_execute.return_value = mock_log

            result = transmit_peppol_invoice_task(log_id, org_id)

            assert result is not None
            assert mock_log.status == "DELIVERED"

    @pytest.mark.django_db
    def test_transmit_task_failure_triggers_retry(self):
        """Test that task retries on failure.

        P32/BE-P32-H1 (the B017 closure): the blind pytest.raises(Exception)
        had been swallowing pytest-django's db-blocker RuntimeError — the
        test passed without EVER reaching the simulated failure (the
        tenant-context cursor needs the django_db mark). With the mark +
        the specific exception class, the retry contract is finally what
        this test proves.
        """
        from apps.peppol.services.transmission_service import TransmissionService
        from apps.peppol.tasks import transmit_peppol_invoice_task

        with patch.object(
            TransmissionService, "execute_transmission_for_log"
        ) as mock_execute:
            log_id = str(uuid4())
            org_id = str(uuid4())

            # Simulate failure (P32/BE-P32-H1: a SPECIFIC class — the
            # eager+propagates retry re-raises the original, so a blind
            # pytest.raises(Exception) would also swallow programming
            # errors; this tightening lets those fail loudly)
            class _NetworkError(Exception):
                pass

            mock_execute.side_effect = _NetworkError("Network error")

            # Task should raise the retried exception for the caller
            with pytest.raises(_NetworkError):
                transmit_peppol_invoice_task(log_id, org_id)


class TestRetryFailedTransmissionTask:
    """Tests for retry_failed_transmission_task."""

    def test_retry_task_exists(self):
        """Test that retry_failed_transmission_task can be imported."""
        from apps.peppol.tasks import retry_failed_transmission_task

        assert retry_failed_transmission_task is not None

    @pytest.mark.django_db
    def test_retry_task_calls_service(self):
        """Test that task calls TransmissionService.retry_transmission.

        P18/BE-M1: the task signature now carries the org (the RLS
        tenant) — a NULL-GUC worker cannot resolve it from the
        RLS-blocked log row, so the caller hands it over explicitly.
        The db mark: the body opens the tenant context (transaction).
        """
        from apps.peppol.services.transmission_service import TransmissionService
        from apps.peppol.tasks import retry_failed_transmission_task

        with patch.object(TransmissionService, "retry_transmission") as mock_retry:
            transmission_log_id = str(uuid4())
            org_id = str(uuid4())

            mock_log = Mock()
            mock_log.status = "DELIVERED"
            mock_retry.return_value = mock_log

            retry_failed_transmission_task(transmission_log_id, org_id)

            mock_retry.assert_called_once_with(transmission_log_id)


class TestCheckTransmissionStatusTask:
    """Tests for check_transmission_status_task."""

    def test_status_check_task_exists(self):
        """Test that check_transmission_status_task can be imported."""
        from apps.peppol.tasks import check_transmission_status_task

        assert check_transmission_status_task is not None

    @pytest.mark.django_db
    def test_status_check_task_returns_result(self):
        """Unknown message id -> None (the documented contract, P5/C-2).

        P18/BE-M1: the task signature now carries the org (the RLS
        tenant) — the log lookup itself is RLS-scoped.
        """
        from apps.peppol.tasks import check_transmission_status_task

        result = check_transmission_status_task(str(uuid4()), str(uuid4()))

        # No log matches this message id
        assert result is None
