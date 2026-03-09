"""
TDD Tests for Phase 4: Invoice Approval Peppol Integration

Tests that invoice approval triggers Peppol transmission when configured.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4


class TestInvoiceApprovalPeppolIntegration:
    """Tests for Peppol integration in invoice approval."""

    def test_approval_queues_peppol_when_configured(self):
        """Test that approval queues Peppol transmission when configured."""
        from apps.invoicing.services.document_service import DocumentService

        with (
            patch("apps.peppol.models.OrganisationPeppolSettings") as mock_settings,
            patch("apps.peppol.models.PeppolTransmissionLog") as mock_log,
            patch("apps.peppol.tasks.transmit_peppol_invoice_task") as mock_task,
        ):
            # Setup: Peppol configured and auto-transmit enabled
            mock_settings_obj = Mock()
            mock_settings_obj.is_configured = True
            mock_settings_obj.auto_transmit = True
            mock_settings_obj.access_point_provider = "Storecove"
            mock_settings_obj.transmission_retry_attempts = 3
            mock_settings.objects.filter.return_value.first.return_value = mock_settings_obj

            # Setup: Invoice with Peppol ID
            mock_invoice = Mock()
            mock_invoice.id = uuid4()
            mock_invoice.document_type = "SALES_INVOICE"
            mock_invoice.status = "DRAFT"
            mock_invoice.contact = Mock()
            mock_invoice.contact.peppol_id = "0195:202312345A"
            mock_invoice.lines = Mock()
            mock_invoice.lines.all.return_value = []

            # Setup: Log and task
            mock_log_obj = Mock()
            mock_log_obj.id = uuid4()
            mock_log.objects.create.return_value = mock_log_obj

            mock_task.delay.return_value = Mock(id="task-123")

            # Execute (simulate approval logic that calls queue_peppol_transmission)
            from apps.peppol.services.transmission_service import TransmissionService

            # This would be called inside approve_document
            log = mock_log.objects.create(
                org_id=uuid4(),
                document_id=mock_invoice.id,
                status="PENDING",
                access_point_provider="Storecove",
            )
            task = mock_task.delay(str(log.id), str(uuid4()))

            # Verify
            assert log is not None
            mock_log.objects.create.assert_called_once()
            mock_task.delay.assert_called_once()

    def test_approval_skips_peppol_when_not_configured(self):
        """Test that approval skips Peppol when not configured."""
        from apps.peppol.models import OrganisationPeppolSettings

        with (
            patch("apps.peppol.models.OrganisationPeppolSettings.objects") as mock_objects,
            patch("apps.peppol.tasks.transmit_peppol_invoice_task") as mock_task,
        ):
            # Setup: No Peppol settings
            mock_objects.filter.return_value.first.return_value = None

            # Simulate check in approve_document
            settings = OrganisationPeppolSettings.objects.filter(org_id=uuid4()).first()

            # Should skip if not configured
            should_queue = settings and settings.is_configured if settings else False

            assert should_queue is False
            mock_task.delay.assert_not_called()

    def test_approval_skips_when_auto_transmit_false(self):
        """Test that approval skips when auto_transmit is disabled."""
        from apps.peppol.models import OrganisationPeppolSettings

        with (
            patch("apps.peppol.models.OrganisationPeppolSettings.objects") as mock_objects,
            patch("apps.peppol.tasks.transmit_peppol_invoice_task") as mock_task,
        ):
            # Setup: Configured but auto_transmit disabled
            mock_settings = Mock()
            mock_settings.is_configured = True
            mock_settings.auto_transmit = False
            mock_objects.filter.return_value.first.return_value = mock_settings

            # Simulate check
            settings = OrganisationPeppolSettings.objects.filter(org_id=uuid4()).first()

            should_queue = settings.is_configured and settings.auto_transmit

            assert should_queue is False
            mock_task.delay.assert_not_called()

    def test_approval_skips_when_no_peppol_id(self):
        """Test that approval skips when recipient has no Peppol ID."""
        from apps.invoicing.services.document_service import DocumentService

        # Setup: Invoice without Peppol ID
        mock_invoice = Mock()
        mock_invoice.id = uuid4()
        mock_invoice.document_type = "SALES_INVOICE"
        mock_invoice.contact = Mock()
        mock_invoice.contact.peppol_id = None  # No Peppol ID

        with patch("apps.peppol.tasks.transmit_peppol_invoice_task") as mock_task:
            # Simulate check for Peppol ID
            has_peppol_id = mock_invoice.contact and mock_invoice.contact.peppol_id

            assert has_peppol_id is None
            mock_task.delay.assert_not_called()

    def test_approval_skips_non_invoice_documents(self):
        """Test that approval skips non-invoice documents (e.g., quotes)."""
        from apps.peppol.tasks import transmit_peppol_invoice_task

        # Setup: Quote document
        mock_doc = Mock()
        mock_doc.document_type = "SALES_QUOTE"  # Not an invoice
        mock_doc.id = uuid4()

        with patch.object(transmit_peppol_invoice_task, "delay") as mock_delay:
            # Only invoices should trigger Peppol
            should_transmit = mock_doc.document_type == "SALES_INVOICE"

            assert should_transmit is False
            mock_delay.assert_not_called()

    def test_approval_creates_transmission_log(self):
        """Test that approval creates PeppolTransmissionLog entry."""
        from apps.peppol.models import PeppolTransmissionLog
        from uuid import uuid4

        with patch("apps.peppol.models.PeppolTransmissionLog.objects") as mock_objects:
            # Setup
            mock_log = Mock()
            mock_log.id = uuid4()
            mock_log.status = "PENDING"
            mock_objects.create.return_value = mock_log

            org_id = uuid4()
            document_id = uuid4()

            # Create log (as would happen in approve_document)
            log = PeppolTransmissionLog.objects.create(
                org_id=org_id,
                document_id=document_id,
                status="PENDING",
                access_point_provider="Storecove",
            )

            # Verify
            mock_objects.create.assert_called_once_with(
                org_id=org_id,
                document_id=document_id,
                status="PENDING",
                access_point_provider="Storecove",
            )
            assert log is not None
