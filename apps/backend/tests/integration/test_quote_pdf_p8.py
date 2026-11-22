"""
P8/Q-4b: quotations get their own PDF.

generate_pdf rendered invoice_pdf.html ("TAX INVOICE") for EVERY document
type — a quote emailed or printed as a TAX INVOICE is materially wrong.
Quotes now render quote_pdf.html ("QUOTATION" framing, no tax-invoice
labelling).
"""

import pytest
from datetime import date
from decimal import Decimal

from apps.core.models import Contact, InvoiceDocument
from apps.invoicing.services import DocumentService


@pytest.mark.django_db
class TestQuotePdfP8:
    def _quote(self, org):
        contact = Contact.objects.create(
            org=org, contact_type="CUSTOMER", name="Quote PDF Customer",
            email="qp@example.com", is_customer=True, is_active=True,
        )
        return InvoiceDocument.objects.create(
            org=org,
            document_type="SALES_QUOTE",
            document_number="QT-00001",
            contact=contact,
            issue_date=date(2024, 1, 15),
            due_date=date(2024, 2, 15),
            currency="SGD",
            exchange_rate=Decimal("1.000000"),
            total_excl=Decimal("100.0000"),
            total_incl=Decimal("109.0000"),
            amount_paid=Decimal("0.0000"),
            status="DRAFT",
        )

    def test_quote_pdf_uses_the_quotation_template(self, test_organisation, test_invoice):
        """The quote PDF renders through quote_pdf.html — verified at the
        template-selection seam (the render call), the cheapest reliable
        probe."""
        from unittest.mock import patch

        quote = self._quote(test_organisation)
        with patch(
            "apps.invoicing.services.document_service.render_to_string",
            return_value="<html><body>QUOTATION</body></html>",
        ) as render:
            DocumentService.generate_pdf(test_organisation.id, quote.id)
            render.assert_called_once()
            template_name = render.call_args[0][0]
            assert template_name == "invoicing/quote_pdf.html", template_name

    def test_invoice_pdf_still_uses_the_invoice_template(self, test_organisation, test_invoice):
        from unittest.mock import patch

        with patch(
            "apps.invoicing.services.document_service.render_to_string",
            return_value="<html><body>TAX INVOICE</body></html>",
        ) as render:
            DocumentService.generate_pdf(
                test_organisation.id, test_invoice.id
            )
            render.assert_called_once()
            template_name = render.call_args[0][0]
            assert template_name == "invoicing/invoice_pdf.html", template_name

    def test_quote_template_renders_the_quote_number(self, test_organisation):
        """The template itself renders quote framing (title + number)."""
        from django.template.loader import render_to_string

        quote = self._quote(test_organisation)
        html = render_to_string(
            "invoicing/quote_pdf.html",
            {
                "document": quote,
                "org": test_organisation,
                "contact": quote.contact,
                "lines": [],
                "generated_at": date(2024, 1, 15),
            },
        )
        assert "QUOTATION" in html
        assert quote.document_number in html
        assert "TAX INVOICE" not in html
