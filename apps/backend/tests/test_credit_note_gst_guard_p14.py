"""
P14/H-4 + H-5 — the credit-note and GST-registration contracts.

H-4: a credit note is a CORRECTION of an original tax invoice (IRAS:
"A credit note must show the number and date of the original tax
invoice") — it must reference the original document, share its contact,
and not credit more than the original total (incl. GST).
H-5: only a GST-registered organisation may charge GST, and only from
its registration date (until deregistration): a tax code with rate > 0
on a line is refused otherwise.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from common.exceptions import ValidationError
from apps.core.models import Contact, InvoiceDocument, InvoiceLine, DocumentSequence, Organisation
from apps.invoicing.services import DocumentService
from tests.conftest import create_test_contact


@pytest.fixture
def doc_fixture(test_organisation, test_user, test_accounts, test_tax_codes, test_fiscal_period):
    org = test_organisation
    for doc_type, prefix in [
        ("SALES_INVOICE", "INV-"),
        ("SALES_CREDIT_NOTE", "CN-"),
    ]:
        DocumentSequence.objects.get_or_create(
            org=org, document_type=doc_type, defaults={"prefix": prefix, "next_number": 1}
        )
    contact = create_test_contact(org, is_customer=True)
    return {
        "org": org,
        "user": test_user,
        "accounts": test_accounts,
        "tax_codes": test_tax_codes,
        "contact": contact,
    }


def _line_payload(fx, unit_price="100.00"):
    return [
        {
            "account_id": str(fx["accounts"]["4000"].id),
            "description": "H4/H5 probe line",
            "quantity": "1.0000",
            "unit_price": unit_price,
            "tax_code_id": str(fx["tax_codes"]["SR"].id),
        }
    ]


def _make_invoice(fx, issue_date=date(2024, 3, 10), unit_price="1000.00"):
    return DocumentService.create_document(
        org_id=fx["org"].id,
        document_type="SALES_INVOICE",
        contact_id=fx["contact"].id,
        issue_date=issue_date,
        lines=_line_payload(fx, unit_price),
        user_id=fx["user"].id,
    )


class TestCreditNoteLinkageP14:
    @pytest.mark.django_db
    def test_credit_note_without_original_is_refused(self, doc_fixture):
        """RED for H-4: an unlinked credit note is not a valid correction."""
        fx = doc_fixture
        with pytest.raises(ValidationError) as excinfo:
            DocumentService.create_document(
                org_id=fx["org"].id,
                document_type="SALES_CREDIT_NOTE",
                contact_id=fx["contact"].id,
                issue_date=date(2024, 3, 20),
                lines=_line_payload(fx, "250.00"),
                user_id=fx["user"].id,
            )
        assert "original" in str(excinfo.value).lower()

    @pytest.mark.django_db
    def test_credit_note_with_original_is_accepted(self, doc_fixture):
        """H-4 control: a properly linked credit note creates fine."""
        fx = doc_fixture
        invoice = _make_invoice(fx)
        cn = DocumentService.create_document(
            org_id=fx["org"].id,
            document_type="SALES_CREDIT_NOTE",
            contact_id=fx["contact"].id,
            issue_date=date(2024, 3, 20),
            lines=_line_payload(fx, "250.00"),
            related_document_id=invoice.id,
            user_id=fx["user"].id,
        )
        assert cn.related_document_id == invoice.id

    @pytest.mark.django_db
    def test_credit_note_cross_contact_is_refused(self, doc_fixture):
        """H-4: the credit note's contact must be the original's contact."""
        fx = doc_fixture
        invoice = _make_invoice(fx)
        other_contact = create_test_contact(
            fx["org"], name="Other Customer", email="other@example.com", is_customer=True
        )
        with pytest.raises(ValidationError):
            DocumentService.create_document(
                org_id=fx["org"].id,
                document_type="SALES_CREDIT_NOTE",
                contact_id=other_contact.id,
                issue_date=date(2024, 3, 20),
                lines=_line_payload(fx, "250.00"),
                related_document_id=invoice.id,
                user_id=fx["user"].id,
            )

    @pytest.mark.django_db
    def test_credit_note_over_cap_is_refused(self, doc_fixture):
        """H-4: cumulative credit (incl. GST) may not exceed the original
        total (incl. GST) — a 5000.00 credit against a 1000.00 invoice
        drives F5 boxes negative."""
        fx = doc_fixture
        invoice = _make_invoice(fx, unit_price="1000.00")  # 1090.00 incl.
        with pytest.raises(ValidationError) as excinfo:
            DocumentService.create_document(
                org_id=fx["org"].id,
                document_type="SALES_CREDIT_NOTE",
                contact_id=fx["contact"].id,
                issue_date=date(2024, 3, 20),
                lines=_line_payload(fx, "5000.00"),
                related_document_id=invoice.id,
                user_id=fx["user"].id,
            )
        assert "exceed" in str(excinfo.value).lower() or "original" in str(excinfo.value).lower()

    @pytest.mark.django_db
    def test_second_credit_note_over_cap_is_refused(self, doc_fixture):
        """H-4: the cap is CUMULATIVE — 800 + 800 against a 1000-net
        original must refuse on the second."""
        fx = doc_fixture
        invoice = _make_invoice(fx, unit_price="1000.00")
        DocumentService.create_document(
            org_id=fx["org"].id,
            document_type="SALES_CREDIT_NOTE",
            contact_id=fx["contact"].id,
            issue_date=date(2024, 3, 20),
            lines=_line_payload(fx, "800.00"),
            related_document_id=invoice.id,
            user_id=fx["user"].id,
        )
        with pytest.raises(ValidationError):
            DocumentService.create_document(
                org_id=fx["org"].id,
                document_type="SALES_CREDIT_NOTE",
                contact_id=fx["contact"].id,
                issue_date=date(2024, 3, 25),
                lines=_line_payload(fx, "800.00"),
                related_document_id=invoice.id,
                user_id=fx["user"].id,
            )


class TestGSTRegistrationGuardP14:
    @pytest.mark.django_db
    def test_gst_line_on_unregistered_org_is_refused(self, doc_fixture):
        """RED for H-5: a non-GST-registered org cannot charge GST."""
        fx = doc_fixture
        fx["org"].gst_registered = False
        fx["org"].save()

        with pytest.raises(ValidationError) as excinfo:
            _make_invoice(fx)
        assert "register" in str(excinfo.value).lower()

    @pytest.mark.django_db
    def test_gst_line_before_registration_date_is_refused(self, doc_fixture):
        """H-5: a GST line dated before the org's registration date is
        refused (the pre-P14 incidental control-account guard is not a
        compliance rule)."""
        fx = doc_fixture
        fx["org"].gst_registered = True
        fx["org"].gst_reg_date = date(2024, 6, 1)
        fx["org"].save()

        with pytest.raises(ValidationError) as excinfo:
            _make_invoice(fx, issue_date=date(2024, 3, 10))
        assert "registration" in str(excinfo.value).lower() or "register" in str(excinfo.value).lower()

    @pytest.mark.django_db
    def test_gst_line_after_registration_is_accepted(self, doc_fixture):
        """H-5 control: within the registration window, unchanged."""
        fx = doc_fixture
        fx["org"].gst_registered = True
        fx["org"].gst_reg_date = date(2024, 1, 1)
        fx["org"].save()

        doc = _make_invoice(fx, issue_date=date(2024, 3, 10))
        assert doc.status == "DRAFT"

    @pytest.mark.django_db
    def test_zero_rated_line_on_unregistered_org_is_accepted(self, doc_fixture):
        """H-5 control: zero-rated/exempt lines don't charge GST — a
        non-registered org can still invoice with them."""
        fx = doc_fixture
        fx["org"].gst_registered = False
        fx["org"].save()

        doc = DocumentService.create_document(
            org_id=fx["org"].id,
            document_type="SALES_INVOICE",
            contact_id=fx["contact"].id,
            issue_date=date(2024, 3, 10),
            lines=[
                {
                    "account_id": str(fx["accounts"]["4000"].id),
                    "description": "zero-rated probe",
                    "quantity": "1.0000",
                    "unit_price": "100.00",
                    "tax_code_id": str(fx["tax_codes"]["ZR"].id),
                }
            ],
            user_id=fx["user"].id,
        )
        assert doc.status == "DRAFT"
