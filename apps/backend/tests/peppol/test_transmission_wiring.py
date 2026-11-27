"""
P5/C-2 — real InvoiceNow send/status wiring + retention-safe cleanup.

RED suite: every test here fails against the stub implementation
(send_invoicenow returns fabricated uuid4s, get_invoicenow_status always
answers NOT_APPLICABLE, cleanup deletes DELIVERED logs at 90 days, and the
task/service seam passes a log id where an invoice id is expected).
"""

from datetime import timedelta
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from django.utils import timezone

from apps.invoicing.services.document_service import DocumentService
from apps.peppol.models import OrganisationPeppolSettings, PeppolTransmissionLog
from apps.peppol.tasks import cleanup_old_transmission_logs_task
from tests.conftest import create_test_contact, create_test_invoice


def _peppol_ready_invoice(org, status="APPROVED", peppol_id="0195:SG-UUID:demo-recipient"):
    """Create an invoice whose contact carries a Peppol participant id."""
    contact = create_test_contact(org, peppol_id=peppol_id)
    return create_test_invoice(org, contact, status=status)


def _configure_peppol(org, auto_transmit=False):
    """Create a fully-configured OrganisationPeppolSettings row."""
    return OrganisationPeppolSettings.objects.create(
        org=org,
        access_point_provider="storecove",
        access_point_api_url="https://api.storecove.example",
        access_point_api_key="test-key",
        access_point_client_id="test-client",
        auto_transmit=auto_transmit,
        is_active=True,
    )


class TestSendInvoiceNow:
    """DocumentService.send_invoicenow must use the real transmission path."""

    @pytest.mark.django_db
    def test_unconfigured_org_is_rejected(self, test_organisation):
        """No Peppol settings -> ValidationError with a configure-first message."""
        invoice = _peppol_ready_invoice(test_organisation)

        from apps.invoicing.services.document_service import ValidationError

        with pytest.raises(ValidationError, match="[Pp]eppol"):
            DocumentService.send_invoicenow(
                test_organisation.id, invoice.id, user=None
            )

    @pytest.mark.django_db
    def test_creates_real_transmission_log_and_returns_its_id(
        self, test_organisation
    ):
        """The returned transmission_log_id must belong to a real DB row."""
        _configure_peppol(test_organisation)
        invoice = _peppol_ready_invoice(test_organisation)

        with patch(
            "apps.peppol.tasks.transmit_peppol_invoice_task.delay"
        ) as mock_delay:
            mock_delay.return_value = Mock(id="task-123")
            result = DocumentService.send_invoicenow(
                test_organisation.id, invoice.id, user=None
            )

        log = PeppolTransmissionLog.objects.get(id=result["transmission_log_id"])
        assert log.document_id == invoice.id
        assert log.org_id == test_organisation.id
        assert log.status in ("PENDING", "TRANSMITTING")
        assert mock_delay.called, "the real Celery task must be queued"
        assert result["queued_at"]

    @pytest.mark.django_db
    def test_draft_document_rejected(self, test_organisation):
        """Only APPROVED documents may be transmitted (existing contract)."""
        _configure_peppol(test_organisation)
        invoice = _peppol_ready_invoice(test_organisation, status="DRAFT")

        from apps.invoicing.services.document_service import ValidationError

        with pytest.raises(ValidationError, match="APPROVED"):
            DocumentService.send_invoicenow(
                test_organisation.id, invoice.id, user=None
            )

    @pytest.mark.django_db
    def test_contact_without_peppol_id_rejected(self, test_organisation):
        """Existing contract preserved: contact must have a Peppol id."""
        _configure_peppol(test_organisation)
        contact = create_test_contact(test_organisation)  # no peppol_id
        invoice = create_test_invoice(test_organisation, contact, status="APPROVED")

        from apps.invoicing.services.document_service import ValidationError

        with pytest.raises(ValidationError, match="Peppol ID"):
            DocumentService.send_invoicenow(
                test_organisation.id, invoice.id, user=None
            )


class TestInvoiceNowStatus:
    """get_invoicenow_status must report the real transmission log rows."""

    @pytest.mark.django_db
    def test_returns_real_log_rows(self, test_organisation):
        _configure_peppol(test_organisation)
        invoice = _peppol_ready_invoice(test_organisation)
        log = PeppolTransmissionLog.objects.create(
            org=test_organisation,
            document_id=invoice.id,
            status="DELIVERED",
            access_point_provider="storecove",
            attempt_number=1,
            peppol_message_id=uuid4(),
        )

        result = DocumentService.get_invoicenow_status(
            test_organisation.id, invoice.id
        )

        assert result["status"] == "DELIVERED"
        assert result["message_id"] == str(log.peppol_message_id)
        assert len(result["logs"]) >= 1
        assert result["logs"][0]["status"] == "DELIVERED"

    @pytest.mark.django_db
    def test_unconfigured_org_reports_not_configured(self, test_organisation):
        invoice = _peppol_ready_invoice(test_organisation)

        result = DocumentService.get_invoicenow_status(
            test_organisation.id, invoice.id
        )

        assert result["status"] == "NOT_CONFIGURED"

    @pytest.mark.django_db
    def test_configured_org_without_history_reports_no_transmissions(
        self, test_organisation
    ):
        _configure_peppol(test_organisation)
        invoice = _peppol_ready_invoice(test_organisation)

        result = DocumentService.get_invoicenow_status(
            test_organisation.id, invoice.id
        )

        assert result["status"] in ("NOT_TRANSMITTED", "PENDING", "QUEUED")
        assert result["logs"] == []


class TestTaskServiceSeam:
    """transmit_peppol_invoice_task must execute against the existing log."""

    @pytest.mark.django_db
    def test_execute_transmission_for_log_updates_existing_log(
        self, test_organisation
    ):
        """The service seam updates the pre-created log; no duplicate rows."""
        from apps.peppol.services.ap_adapter_base import TransmissionResult
        from apps.peppol.services.transmission_service import TransmissionService

        _configure_peppol(test_organisation)
        invoice = _peppol_ready_invoice(test_organisation)
        log = PeppolTransmissionLog.objects.create(
            org=test_organisation,
            document_id=invoice.id,
            status="PENDING",
            access_point_provider="storecove",
            attempt_number=1,
        )

        service = TransmissionService()
        mock_adapter = Mock()
        mock_adapter.send_invoice.return_value = TransmissionResult.success(
            message_id=str(uuid4()), raw_response={"status": "accepted"}
        )
        service.get_adapter_for_org = Mock(return_value=mock_adapter)
        service.mapping_service = Mock()
        service.mapping_service.map_invoice_to_ubl.return_value = {"demo": True}
        service.generator_service = Mock()
        service.generator_service.generate_invoice_xml.return_value = "<Invoice/>"
        service.generator_service.calculate_xml_hash.return_value = "hash"
        service.validation_service = Mock()
        service.validation_service.validate_invoice_xml.return_value = {
            "is_valid": True,
            "errors": [],
        }

        updated = service.execute_transmission_for_log(str(log.id))

        assert updated.id == log.id
        assert updated.status == "DELIVERED"
        assert updated.peppol_message_id is not None
        assert (
            PeppolTransmissionLog.objects.filter(document_id=invoice.id).count() == 1
        ), "the existing log must be updated, not duplicated"

    @pytest.mark.django_db
    def test_task_reaches_adapter_with_precreated_log(self, test_organisation):
        """End-to-end task path: pre-created log + mocked adapter -> DELIVERED."""
        from apps.peppol.services.ap_adapter_base import TransmissionResult
        from apps.peppol.tasks import transmit_peppol_invoice_task

        _configure_peppol(test_organisation)
        invoice = _peppol_ready_invoice(test_organisation)
        log = PeppolTransmissionLog.objects.create(
            org=test_organisation,
            document_id=invoice.id,
            status="PENDING",
            access_point_provider="storecove",
            attempt_number=1,
        )

        with patch(
            "apps.peppol.services.transmission_service.TransmissionService"
            ".get_adapter_for_org"
        ) as mock_get_adapter:
            mock_adapter = Mock()
            mock_adapter.send_invoice.return_value = TransmissionResult.success(
                message_id=str(uuid4()), raw_response={"status": "accepted"}
            )
            mock_get_adapter.return_value = mock_adapter
            with patch(
                "apps.peppol.services.xml_mapping_service.XMLMappingService"
                ".map_invoice_to_ubl",
                return_value={"demo": True},
            ), patch(
                "apps.peppol.services.xml_generator_service.XMLGeneratorService"
                ".generate_invoice_xml",
                return_value="<Invoice/>",
            ), patch(
                "apps.peppol.services.xml_generator_service.XMLGeneratorService"
                ".calculate_xml_hash",
                return_value="hash",
            ), patch(
                "apps.peppol.services.xml_validation_service.XMLValidationService"
                ".validate_invoice_xml",
                return_value={"is_valid": True, "errors": []},
            ):
                result = transmit_peppol_invoice_task.apply(
                    args=[str(log.id), str(test_organisation.id)]
                ).get()

        assert result["success"] is True, f"task result: {result}"
        log.refresh_from_db()
        assert log.status == "DELIVERED"


class TestRetentionSafeCleanup:
    """cleanup must never delete DELIVERED/REJECTED (IRAS 5-year retention)."""

    @pytest.mark.django_db
    def test_delivered_logs_are_never_deleted(self, test_organisation):
        invoice = _peppol_ready_invoice(test_organisation)
        old = timezone.now() - timedelta(days=400)
        delivered = PeppolTransmissionLog.objects.create(
            org=test_organisation,
            document_id=invoice.id,
            status="DELIVERED",
            access_point_provider="storecove",
            attempt_number=1,
        )
        # transmitted_at is auto_now_add — bypass it with a queryset update
        PeppolTransmissionLog.objects.filter(id=delivered.id).update(
            transmitted_at=old
        )

        deleted = cleanup_old_transmission_logs_task(days=90)

        assert deleted == 0
        assert PeppolTransmissionLog.objects.filter(id=delivered.id).exists()

    @pytest.mark.django_db
    def test_stale_pending_logs_are_removed(self, test_organisation):
        invoice = _peppol_ready_invoice(test_organisation)
        old = timezone.now() - timedelta(days=400)
        stale = PeppolTransmissionLog.objects.create(
            org=test_organisation,
            document_id=invoice.id,
            status="PENDING",
            access_point_provider="storecove",
            attempt_number=1,
        )
        # transmitted_at is auto_now_add — bypass it with a queryset update
        PeppolTransmissionLog.objects.filter(id=stale.id).update(
            transmitted_at=old
        )

        # P18/BE-M1: per-org dispatch — the logs are RLS-scoped, so the
        # cleanup carries the org whose tenant context it must open.
        deleted = cleanup_old_transmission_logs_task(days=90, org_id=str(test_organisation.id))

        assert deleted == 1
        assert not PeppolTransmissionLog.objects.filter(id=stale.id).exists()

    @pytest.mark.django_db
    def test_fresh_logs_are_kept(self, test_organisation):
        invoice = _peppol_ready_invoice(test_organisation)
        pending = PeppolTransmissionLog.objects.create(
            org=test_organisation,
            document_id=invoice.id,
            status="PENDING",
            access_point_provider="storecove",
            attempt_number=1,
            transmitted_at=timezone.now(),
        )

        deleted = cleanup_old_transmission_logs_task(days=90)

        assert deleted == 0
        assert PeppolTransmissionLog.objects.filter(id=pending.id).exists()
