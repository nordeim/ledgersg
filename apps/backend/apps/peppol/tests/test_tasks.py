"""
TDD Tests for Phase 4: Celery Tasks

Tests the async Celery tasks for Peppol transmission.
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4


class TestTransmitPeppolInvoiceTask:
    """Tests for transmit_peppol_invoice_task."""

    def test_transmit_task_exists(self):
        """Test that transmit_peppol_invoice_task can be imported."""
        from apps.peppol.tasks import transmit_peppol_invoice_task

        assert transmit_peppol_invoice_task is not None

    def test_transmit_task_calls_service(self):
        """Test that task executes against the pre-created log (P5/C-2 seam)."""
        from apps.peppol.tasks import transmit_peppol_invoice_task
        from apps.peppol.services.transmission_service import TransmissionService

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

    def test_transmit_task_success_updates_log(self):
        """Test successful transmission updates log to DELIVERED."""
        from apps.peppol.tasks import transmit_peppol_invoice_task
        from apps.peppol.services.transmission_service import TransmissionService

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

    def test_transmit_task_failure_triggers_retry(self):
        """Test that task retries on failure."""
        from apps.peppol.tasks import transmit_peppol_invoice_task
        from apps.peppol.services.transmission_service import TransmissionService

        with patch.object(
            TransmissionService, "execute_transmission_for_log"
        ) as mock_execute:
            log_id = str(uuid4())
            org_id = str(uuid4())

            # Simulate failure
            mock_execute.side_effect = Exception("Network error")

            # Task should raise exception for retry
            with pytest.raises(Exception):
                transmit_peppol_invoice_task(log_id, org_id)


class TestRetryFailedTransmissionTask:
    """Tests for retry_failed_transmission_task."""

    def test_retry_task_exists(self):
        """Test that retry_failed_transmission_task can be imported."""
        from apps.peppol.tasks import retry_failed_transmission_task

        assert retry_failed_transmission_task is not None

    def test_retry_task_calls_service(self):
        """Test that task calls TransmissionService.retry_transmission."""
        from apps.peppol.tasks import retry_failed_transmission_task
        from apps.peppol.services.transmission_service import TransmissionService

        with patch.object(TransmissionService, "retry_transmission") as mock_retry:
            transmission_log_id = str(uuid4())

            mock_log = Mock()
            mock_log.status = "DELIVERED"
            mock_retry.return_value = mock_log

            result = retry_failed_transmission_task(transmission_log_id)

            mock_retry.assert_called_once_with(transmission_log_id)


class TestCheckTransmissionStatusTask:
    """Tests for check_transmission_status_task."""

    def test_status_check_task_exists(self):
        """Test that check_transmission_status_task can be imported."""
        from apps.peppol.tasks import check_transmission_status_task

        assert check_transmission_status_task is not None

    @pytest.mark.django_db
    def test_status_check_task_returns_result(self):
        """Unknown message id -> None (the documented contract, P5/C-2)."""
        from apps.peppol.tasks import check_transmission_status_task

        result = check_transmission_status_task(str(uuid4()))

        # No log matches this message id
        assert result is None
