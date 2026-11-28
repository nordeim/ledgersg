"""
P37/BE-P37-H1 (PDF): the credit-note PDF presentation truth.

The invoice PDF template titles a credit note with the raw enum
"SALES_CREDIT_NOTE" and shows no reference to the original invoice —
while the DB layer REQUIRES related_document_id (P14/H-4, quoting the
IRAS rule) and IRAS expects the document headed "Credit Note" showing
"the number and date of the original tax invoice".

RED on the base tree for exactly the right reasons: no reference block
in the rendered HTML, the raw enum leaking as the heading, and no
related_document context entry.
"""

import datetime
from decimal import Decimal

import pytest

from apps.core.models import InvoiceDocument
from apps.invoicing.services.document_service import DocumentService


def _render_html(context):
    from django.template.loader import render_to_string

    return render_to_string("invoicing/invoice_pdf.html", context)


def _credit_note(org, invoice):
    return InvoiceDocument.objects.create(
        org=org,
        document_type="SALES_CREDIT_NOTE",
        document_number="CN-P37-001",
        contact=invoice.contact,
        issue_date=datetime.date(2026, 11, 28),
        due_date=datetime.date(2026, 12, 28),
        currency="SGD",
        exchange_rate=Decimal("1.000000"),
        total_excl=Decimal("1000.0000"),
        total_incl=Decimal("1090.0000"),
        amount_paid=Decimal("0.0000"),
        status="APPROVED",
        related_document=invoice,
    )


@pytest.mark.django_db
class TestPdfPresentation:
    """The PDF shows the reference and the CREDIT NOTE heading."""

    def test_credit_note_pdf_context_carries_the_reference(
        self, test_organisation, test_invoice
    ):
        """_get_pdf_context exposes the related document for credit notes
        (RED on the base tree: no such context entry)."""
        cn = _credit_note(test_organisation, test_invoice)
        context = DocumentService._get_pdf_context(test_organisation.id, cn.id)
        related = context.get("related_document")
        assert related is not None
        assert related.id == test_invoice.id
        assert related.document_number == test_invoice.document_number

    def test_credit_note_pdf_renders_the_reference(
        self, test_organisation, test_invoice
    ):
        """The rendered HTML carries the original invoice number and its
        issue date (RED on the base tree: the template has no reference
        block)."""
        cn = _credit_note(test_organisation, test_invoice)
        context = DocumentService._get_pdf_context(test_organisation.id, cn.id)
        html = _render_html(context)
        assert test_invoice.document_number in html
        assert test_invoice.issue_date.isoformat() in html

    def test_credit_note_pdf_heading_is_credit_note(
        self, test_organisation, test_invoice
    ):
        """The heading renders 'CREDIT NOTE' (RED on the base tree: the
        raw enum 'SALES_CREDIT_NOTE' leaks through)."""
        cn = _credit_note(test_organisation, test_invoice)
        context = DocumentService._get_pdf_context(test_organisation.id, cn.id)
        html = _render_html(context)
        assert "CREDIT NOTE" in html
        assert "SALES_CREDIT_NOTE" not in html

    def test_invoice_pdf_has_no_reference_block(
        self, test_organisation, test_invoice
    ):
        """The invoice PDF keeps its exact shape: no reference block, no
        heading change (the control)."""
        context = DocumentService._get_pdf_context(
            test_organisation.id, test_invoice.id
        )
        html = _render_html(context)
        assert "Original Invoice" not in html
        assert "SALES_INVOICE" not in html
