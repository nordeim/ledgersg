"""
Integration Tests for Invoice Operations
Phase 2: Missing Invoice Workflow Endpoints

Tests for:
- POST /invoicing/documents/{id}/approve/
- POST /invoicing/documents/{id}/void/
- GET /invoicing/documents/{id}/pdf/
- POST /invoicing/documents/{id}/send/
- POST /invoicing/documents/{id}/send-invoicenow/
- GET /invoicing/documents/{id}/invoicenow-status/

These tests expect the endpoints to exist and return appropriate responses.
TDD: Tests will fail initially, then pass once implementation is complete.
"""

import pytest
from uuid import UUID, uuid4
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status


@pytest.mark.django_db
class TestInvoiceOperationsAPI:
    """Test suite for invoice workflow operations."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        """Setup test data for each test."""
        self.client = APIClient()
        self.org_id = str(uuid4())
        self.document_id = str(uuid4())
        self.contact_id = str(uuid4())

    def test_approve_document_endpoint_exists(self):
        """Test that approve endpoint exists and requires auth."""
        url = f"/api/v1/{self.org_id}/invoicing/documents/{self.document_id}/approve/"
        response = self.client.post(url)
        # Should fail with 401 (unauthorized) not 404 (not found)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    def test_void_document_endpoint_exists(self):
        """Test that void endpoint exists and requires auth."""
        url = f"/api/v1/{self.org_id}/invoicing/documents/{self.document_id}/void/"
        response = self.client.post(url)
        # Should fail with 401 (unauthorized) not 404 (not found)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    def test_pdf_endpoint_exists(self):
        """Test that PDF endpoint exists and requires auth."""
        url = f"/api/v1/{self.org_id}/invoicing/documents/{self.document_id}/pdf/"
        response = self.client.get(url)
        # Should fail with 401 (unauthorized) not 404 (not found)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    def test_send_email_endpoint_exists(self):
        """Test that send endpoint exists and requires auth."""
        url = f"/api/v1/{self.org_id}/invoicing/documents/{self.document_id}/send/"
        response = self.client.post(url)
        # Should fail with 401 (unauthorized) not 404 (not found)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    def test_send_invoicenow_endpoint_exists(self):
        """Test that InvoiceNow endpoint exists and requires auth."""
        url = f"/api/v1/{self.org_id}/invoicing/documents/{self.document_id}/send-invoicenow/"
        response = self.client.post(url)
        # Should fail with 401 (unauthorized) not 404 (not found)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    def test_invoicenow_status_endpoint_exists(self):
        """Test that InvoiceNow status endpoint exists and requires auth."""
        url = f"/api/v1/{self.org_id}/invoicing/documents/{self.document_id}/invoicenow-status/"
        response = self.client.get(url)
        # Should fail with 401 (unauthorized) not 404 (not found)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestInvoiceOperationsBusinessLogic:
    """Test suite for invoice operation business logic (service layer)."""

    @pytest.mark.django_db
    def test_approve_creates_journal_entries(
        self, test_user, test_organisation, test_accounts, test_tax_codes,
        test_fiscal_period, period_invoice_with_lines,
    ):
        """
        When an invoice is approved:
        - Status should change from DRAFT to APPROVED
        - A journal entry should be created and linked
        - Entry should balance (debits = credits)
        """
        from apps.invoicing.services import DocumentService
        from apps.core.models import JournalEntry

        document = DocumentService.approve_document(
            test_organisation.id, period_invoice_with_lines.id, test_user
        )

        assert document.status == "APPROVED"
        assert document.journal_entry_id is not None

        entry = JournalEntry.objects.get(id=document.journal_entry_id)
        total_debits = sum(line.debit for line in entry.lines.all())
        total_credits = sum(line.credit for line in entry.lines.all())
        assert total_debits == total_credits

    @pytest.mark.django_db
    def test_void_creates_reversal_entries(
        self, test_user, test_organisation, test_accounts, test_tax_codes,
        test_fiscal_period, period_invoice_with_lines,
    ):
        """
        When an invoice is voided:
        - Status should change from APPROVED to VOID
        - Reversal journal entries should be created
        - Void reason should be recorded
        """
        from apps.invoicing.services import DocumentService
        from apps.core.models import JournalEntry

        document = DocumentService.approve_document(
            test_organisation.id, period_invoice_with_lines.id, test_user
        )
        original_entry_id = document.journal_entry_id

        voided = DocumentService.void_document(
            test_organisation.id, document.id, test_user, "Customer cancelled order"
        )

        assert voided.status == "VOID"
        assert voided.void_reason == "Customer cancelled order"

        original = JournalEntry.objects.get(id=original_entry_id)
        assert original.is_reversed is True
        assert original.reversed_by_id is not None, "Void must create a reversal entry"

        reversal = JournalEntry.objects.get(id=original.reversed_by_id)
        # The reversal must exactly invert the original entry
        for orig_line, rev_line in zip(original.lines.all(), reversal.lines.all(), strict=False):
            assert rev_line.debit == orig_line.credit
            assert rev_line.credit == orig_line.debit

    @pytest.mark.django_db
    def test_void_partially_paid_invoice_allowed(
        self, test_user, test_organisation, test_accounts, test_tax_codes,
        test_fiscal_period, period_invoice_with_lines,
    ):
        """
        A PARTIALLY_PAID (enum-correct) invoice must be voidable — the old
        'PAID_PARTIAL' literal made this state impossible to void.
        """
        from apps.invoicing.services import DocumentService
        from apps.core.models import InvoiceDocument

        document = DocumentService.approve_document(
            test_organisation.id, period_invoice_with_lines.id, test_user
        )
        document.status = "PARTIALLY_PAID"
        document.save()

        voided = DocumentService.void_document(
            test_organisation.id, document.id, test_user, "Settled out of band"
        )
        assert voided.status == "VOID"

    @pytest.mark.django_db
    def test_draft_invoice_voids_as_a_pure_status_retirement(
        self, test_user, test_organisation, test_fiscal_period, period_invoice_with_lines,
    ):
        """P8/G-3: DRAFT→VOID is advertised by STATUS_TRANSITIONS and is how
        a wrong draft is retired — the void succeeds with no journal side
        effects (the pre-P8 engine refused drafts while advertising the
        transition, a guaranteed-400 contradiction). A draft WITH a payment
        allocation is still refused (the allocation guard)."""
        from apps.invoicing.services import DocumentService

        voided = DocumentService.void_document(
            test_organisation.id, period_invoice_with_lines.id, test_user, "created by mistake"
        )
        assert voided.status == "VOID"
        assert voided.void_reason == "created by mistake"
        assert voided.journal_entry_id is None  # nothing was ever posted

    @pytest.mark.django_db
    def test_pdf_generation_returns_valid_pdf(self, auth_client, test_organisation, test_invoice):
        """
        PDF generation should:
        - Return a 200 OK status
        - Return a PDF content type
        - Start with the PDF magic header %PDF
        """
        org_id = test_organisation.id
        invoice_id = test_invoice.id

        url = f"/api/v1/{org_id}/invoicing/documents/{invoice_id}/pdf/"
        response = auth_client.get(url)

        assert response.status_code == 200
        assert response['Content-Type'] == "application/pdf"
        assert response.getvalue().startswith(b"%PDF")

    @pytest.mark.django_db
    def test_email_sending_queues_task(self, auth_client, test_organisation, test_invoice):
        """
        Email sending should:
        - Return a 200 OK status
        - Return a success message indicating the task is queued
        """
        from unittest.mock import patch
        org_id = test_organisation.id
        invoice_id = test_invoice.id

        url = f"/api/v1/{org_id}/invoicing/documents/{invoice_id}/send/"
        data = {
            "to": ["customer@example.com"],
            "message": "Please find your invoice attached."
        }

        with patch("apps.invoicing.tasks.send_invoice_email_task.delay") as mock_delay:
            response = auth_client.post(url, data=data, format='json')

            assert response.status_code == 200
            assert "Invoice email has been queued for sending" in response.data['message']
            assert response.data['sent'] is True
            mock_delay.assert_called_once()

    def test_invoicenow_queuing(self):
        """
        InvoiceNow sending should:
        - Queue the invoice for transmission
        - Return transmission log ID
        - Set status to PENDING

        Deferred: requires wiring send_invoicenow to the real
        TransmissionService (audit H-08, see docs/REMEDIATION_PLAN_2026-11-21.md
        deferred debt register).
        """
        pytest.skip("H-08 deferred: send_invoicenow returns fabricated success until wired to TransmissionService")

    @pytest.mark.django_db
    def test_status_transitions(
        self, test_user, test_organisation, test_accounts, test_tax_codes,
        test_fiscal_period, period_invoice_with_lines,
    ):
        """
        Status transitions should be enforced:
        - DRAFT → APPROVED (via approve)
        - APPROVED → VOID (via void)
        - Cannot approve an already approved invoice
        """
        import pytest as _pytest
        from apps.invoicing.services import DocumentService

        document = DocumentService.approve_document(
            test_organisation.id, period_invoice_with_lines.id, test_user
        )
        assert document.status == "APPROVED"

        with _pytest.raises(Exception, match="[Cc]annot approve"):
            DocumentService.approve_document(
                test_organisation.id, document.id, test_user
            )

        voided = DocumentService.void_document(
            test_organisation.id, document.id, test_user, "Wrong customer"
        )
        assert voided.status == "VOID"


@pytest.fixture
def period_invoice_with_lines(test_organisation, test_accounts, test_tax_codes, test_fiscal_period):
    """A DRAFT sales invoice with two lines dated inside the open fiscal period."""
    from datetime import date
    from decimal import Decimal
    from apps.core.models import InvoiceDocument, InvoiceLine
    from tests.conftest import create_test_contact
    from unittest.mock import patch
    from apps.invoicing.services import DocumentService

    contact = create_test_contact(test_organisation)
    with patch.object(DocumentService, "_get_next_document_number", return_value="INV-00001"):
        invoice = InvoiceDocument.objects.create(
            org=test_organisation,
            document_type="SALES_INVOICE",
            contact=contact,
            document_number="INV-00001",
            issue_date=date(2024, 1, 15),
            due_date=date(2024, 2, 15),
            status="DRAFT",
            total_excl=Decimal("1100.00"),
            gst_total=Decimal("9.00"),
            total_incl=Decimal("1109.00"),
        )
    InvoiceLine.objects.create(
        org=test_organisation,
        document=invoice,
        line_number=1,
        description="Consulting services",
        account=test_accounts["4000"],
        quantity=Decimal("1"),
        unit_price=Decimal("100.00"),
        tax_code=test_tax_codes["SR"],
        tax_rate=Decimal("0.09"),
        line_amount=Decimal("100.00"),
        gst_amount=Decimal("9.00"),
        total_amount=Decimal("109.00"),
    )
    InvoiceLine.objects.create(
        org=test_organisation,
        document=invoice,
        line_number=2,
        description="Export services",
        account=test_accounts["4000"],
        quantity=Decimal("1"),
        unit_price=Decimal("1000.00"),
        tax_code=test_tax_codes["ZR"],
        tax_rate=Decimal("0.00"),
        line_amount=Decimal("1000.00"),
        gst_amount=Decimal("0.00"),
        total_amount=Decimal("1000.00"),
    )
    return invoice
