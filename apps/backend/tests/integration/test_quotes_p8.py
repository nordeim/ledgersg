"""
P8/Q-1 + Q-3: quotes backend truth.

convert_quote_to_invoice set quote.converted_to_id — a field that does not
exist (the model has related_document) — so the quote→invoice link was
never persisted. The DOCUMENT_TYPES prefixes drift from the seeded
core.document_sequence config (SALES_QUOTE: QUO vs QT-; PURCHASE_INVOICE:
PINV vs BILL-) — the schema file is the source of truth.
"""

import pytest
from datetime import date
from decimal import Decimal

from apps.core.models import Contact, DocumentSequence, InvoiceDocument
from apps.invoicing.services.document_service import DOCUMENT_TYPES, DocumentService
from apps.core.models import FiscalPeriod, FiscalYear


@pytest.mark.django_db
class TestQuoteConversionP8:
    def _org_with_sequences(self, test_organisation):
        for doc_type, prefix in [
            ("SALES_QUOTE", "QT-"),
            ("SALES_INVOICE", "INV-"),
        ]:
            DocumentSequence.objects.get_or_create(
                org=test_organisation,
                document_type=doc_type,
                defaults={"prefix": prefix, "next_number": 1},
            )

    def _quote(self, org):
        contact = Contact.objects.create(
            org=org, contact_type="CUSTOMER", name="Quote Customer",
            email="quote@example.com", is_customer=True, is_active=True,
            payment_terms_days=30,
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

    def test_conversion_persists_the_related_document_link(
        self, test_user, test_organisation, test_fiscal_period, test_tax_codes
    ):
        """P8/Q-1: quote.related_document_id must point at the created
        invoice (pre-P8 the transient converted_to_id attribute was
        silently discarded by save())."""
        self._org_with_sequences(test_organisation)
        quote = self._quote(test_organisation)
        # one line so the invoice has content
        from apps.core.models import Account

        revenue = Account.objects.create(
            org=test_organisation, code="4000", name="Sales",
            account_type="REVENUE", is_system=True, is_active=True,
        )
        quote.lines.create(
            org=test_organisation,
            line_number=1, account=revenue, description="Consulting",
            quantity=Decimal("1.0000"), unit_price=Decimal("100.0000"),
            tax_code=test_tax_codes["SR"], tax_rate=Decimal("0.0900"),
            line_amount=Decimal("100.0000"), gst_amount=Decimal("9.0000"),
            total_amount=Decimal("109.0000"), base_line_amount=Decimal("100.0000"),
            base_gst_amount=Decimal("9.0000"), base_total_amount=Decimal("109.0000"),
        )

        invoice = DocumentService.convert_quote_to_invoice(
            test_organisation.id, quote.id, user_id=test_user.id
        )

        quote.refresh_from_db()
        assert quote.related_document_id == invoice.id, (
            "the quote→invoice link was not persisted"
        )
        assert invoice.document_type == "SALES_INVOICE"
        assert quote.document_number in (invoice.reference or "")

    def test_quote_prefix_matches_seeded_sequence(
        self, test_user, test_organisation, test_fiscal_period
    ):
        """P8/Q-3: a new quote gets the QT- prefix the seeded
        core.document_sequence promises (pre-P8: QUO-)."""
        self._org_with_sequences(test_organisation)
        contact = Contact.objects.create(
            org=test_organisation, contact_type="CUSTOMER", name="Prefix C",
            is_customer=True, is_active=True, payment_terms_days=30,
        )
        quote = DocumentService.create_document(
            org_id=test_organisation.id,
            document_type="SALES_QUOTE",
            contact_id=contact.id,
            issue_date=date(2024, 1, 15),
            due_date=date(2024, 2, 15),
            lines=[],
            user_id=test_user.id,
        )
        assert quote.document_number.startswith("QT-"), quote.document_number

    def test_document_types_match_seeded_prefixes(self):
        """The DOCUMENT_TYPES prefixes align with the seeded sequence
        config (schema = source of truth)."""
        seeded = {
            "SALES_QUOTE": "QT-",
            "PURCHASE_INVOICE": "BILL-",
            "SALES_INVOICE": "INV-",
            "SALES_CREDIT_NOTE": "CN-",
            "SALES_DEBIT_NOTE": "DN-",
            "PURCHASE_CREDIT_NOTE": "PCN-",
            "PURCHASE_DEBIT_NOTE": "PDN-",
            "PURCHASE_ORDER": "PO-",
        }
        for doc_type, seeded_prefix in seeded.items():
            python_prefix = DOCUMENT_TYPES[doc_type]["prefix"]
            assert python_prefix == seeded_prefix.rstrip("-"), (
                doc_type,
                python_prefix,
                seeded_prefix,
            )
