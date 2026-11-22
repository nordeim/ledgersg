"""
P10/M-2: transition_status's P9/K-1 VOID delegation crashes when the caller
omits user_id (the signature advertises `user_id: UUID | None = None`):

    void_user = AppUser.objects.get(id=user_id) if user_id else None
    → void_document(..., user=None) → _reverse_journal_entry(..., user.id)
    → AttributeError 500

and a deleted user id raises DoesNotExist → 500. posted_by is NOT NULL by
schema — a void without an accountable poster must REFUSE, not post a
reversing entry anonymously (fail-closed beats a traceback).
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from apps.invoicing.services import DocumentService
from common.exceptions import ValidationError as AppValidationError
from tests.conftest import create_test_contact


def _create_invoice(org, user, accounts, tax_codes, period):
    contact = create_test_contact(org)
    lines = [
        {
            "account_id": accounts["4000"].id,
            "description": "Consulting",
            "quantity": 1,
            "unit_price": Decimal("1000.00"),
            "tax_code_id": tax_codes["SR"].id,
        }
    ]
    invoice = DocumentService.create_document(
        org_id=org.id,
        document_type="SALES_INVOICE",
        contact_id=contact.id,
        issue_date=date(2024, 1, 15),  # inside the open fiscal period
        lines=lines,
        user_id=user.id,
    )
    DocumentService.transition_status(org.id, invoice.id, "SENT", user.id)
    return DocumentService.transition_status(org.id, invoice.id, "APPROVED", user.id)


@pytest.mark.django_db
class TestVoidSeamUserContractP10:
    def test_void_without_user_id_fails_closed_not_attributeerror(
        self, test_organisation, test_user, test_accounts, test_tax_codes,
        test_fiscal_period,
    ):
        """user_id=None must raise a clean ValidationError (posted_by is
        NOT NULL — no anonymous reversals), not AttributeError."""
        invoice = _create_invoice(
            test_organisation, test_user, test_accounts, test_tax_codes,
            test_fiscal_period,
        )

        with pytest.raises(AppValidationError) as excinfo:
            DocumentService.transition_status(
                test_organisation.id, invoice.id, "VOID", None
            )

        assert "user" in str(excinfo.value).lower()
        invoice.refresh_from_db()
        assert invoice.status == "APPROVED"  # unchanged — nothing posted

    def test_void_with_unknown_user_id_fails_closed_not_doesnotexist(
        self, test_organisation, test_user, test_accounts, test_tax_codes,
        test_fiscal_period,
    ):
        """A deleted user id must raise ValidationError, not DoesNotExist."""
        invoice = _create_invoice(
            test_organisation, test_user, test_accounts, test_tax_codes,
            test_fiscal_period,
        )

        ghost = uuid.uuid4()
        with pytest.raises(AppValidationError):
            DocumentService.transition_status(
                test_organisation.id, invoice.id, "VOID", ghost
            )
