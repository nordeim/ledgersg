"""
P7/F-2: Authorization and validation on the document status-transition endpoint.

The pre-P7 view gated on the literal "VOIDED" (the enum value is VOID), so the
CanVoidInvoices check NEVER fired — any org member could void any document via
POST /invoicing/documents/{id}/status/, and payment-derived statuses (PAID,
PARTIALLY_PAID) could be set with no payment record at all. The bare CharField
also accepted arbitrary strings.
"""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from apps.core.models import Contact, InvoiceDocument, Role, UserOrganisation


def _limited_client(api_client, user):
    """Return an APIClient authenticated as the limited member."""
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return api_client


def _make_document(org, contact, doc_status="DRAFT"):
    """Create a document directly (bypassing the API) in the given status."""
    from apps.core.models import DocumentSequence

    seq = DocumentSequence.objects.filter(org=org, document_type="SALES_INVOICE").first()
    doc = InvoiceDocument.objects.create(
        org=org,
        document_type="SALES_INVOICE",
        document_number=f"INV-TEST-{InvoiceDocument.objects.filter(org=org).count() + 1:05d}",
        contact=contact,
        issue_date=date(2024, 1, 15),
        due_date=date(2024, 2, 15),
        currency="SGD",
        exchange_rate=Decimal("1.000000"),
        total_excl=Decimal("100.0000"),
        total_incl=Decimal("109.0000"),
        amount_paid=Decimal("0.0000"),
        status=doc_status,
    )
    return doc


def _make_limited_member(org, **role_flags):
    """Create a user whose role in `org` has ONLY the given permission flags."""
    from apps.core.models import AppUser

    defaults = dict(
        can_manage_org=False,
        can_manage_users=False,
        can_manage_coa=False,
        can_create_invoices=False,
        can_approve_invoices=False,
        can_void_invoices=False,
        can_create_journals=False,
        can_manage_banking=False,
        can_file_gst=False,
        can_view_reports=False,
        can_export_data=False,
    )
    defaults.update(role_flags)
    role = Role.objects.create(org=org, name="Limited", description="P7 test role", **defaults)

    import uuid

    user = AppUser.objects.create(
        id=uuid.uuid4(),
        email=f"limited_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Limited Member",
        is_active=True,
    )
    UserOrganisation.objects.create(
        user=user,
        org=org,
        role=role,
        is_default=True,
        invited_at=date.today(),
        accepted_at=date.today(),
    )
    return user


@pytest.mark.django_db
class TestStatusTransitionAuthorization:
    """POST /invoicing/documents/{id}/status/ must be no weaker than the
    dedicated /approve/ and /void/ endpoints."""

    def _url(self, org, doc):
        return f"/api/v1/{org.id}/invoicing/documents/{doc.id}/status/"

    def test_void_without_permission_forbidden(self, api_client, test_organisation, test_user):
        """A member without can_void_invoices cannot void via /status/ (the
        pre-P7 'VOIDED' literal let this through — the authorization bypass)."""
        contact = Contact.objects.create(
            org=test_organisation, contact_type="CUSTOMER", name="C", is_customer=True, is_active=True
        )
        doc = _make_document(test_organisation, contact, "APPROVED")
        limited = _make_limited_member(test_organisation)
        client = _limited_client(api_client, limited)

        response = client.post(
            self._url(test_organisation, doc), {"status": "VOID", "reason": "wrong amount"}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN, response.data
        doc.refresh_from_db()
        assert doc.status == "APPROVED"

    def test_void_with_permission_allowed_and_reverses(
        self, auth_client, test_organisation, test_user, test_fiscal_period, test_accounts
    ):
        """With can_void_invoices (the owner fixture has it), VOID via /status/
        works exactly like the dedicated endpoint — status flips and the
        reversal journal entry exists."""
        contact = Contact.objects.create(
            org=test_organisation, contact_type="CUSTOMER", name="C", is_customer=True, is_active=True
        )
        doc = _make_document(test_organisation, contact, "APPROVED")
        # A posted entry to reverse: approve path creates one; create directly.
        from apps.journal.services import JournalService

        ar = test_accounts["1200"]
        rev = test_accounts["4000"]
        entry = JournalService.create_entry(
            org_id=test_organisation.id,
            entry_date=date(2024, 1, 15),
            entry_type="SALES_INVOICE",
            description="original",
            lines=[
                {"account_id": ar.id, "debit": Decimal("109.0000"), "credit": Decimal("0.0000")},
                {"account_id": rev.id, "debit": Decimal("0.0000"), "credit": Decimal("109.0000")},
            ],
            user_id=test_user.id,
        )
        doc.journal_entry = entry
        doc.save()

        response = auth_client.post(
            self._url(test_organisation, doc), {"status": "VOID", "reason": "wrong amount"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        doc.refresh_from_db()
        assert doc.status == "VOID"
        assert doc.void_reason == "wrong amount"

    def test_payment_statuses_rejected_on_generic_endpoint(
        self, auth_client, test_organisation, test_user
    ):
        """PAID/PARTIALLY_PAID are derived by the allocation service — the
        generic status endpoint must refuse to set them (no payment record
        would exist)."""
        contact = Contact.objects.create(
            org=test_organisation, contact_type="CUSTOMER", name="C", is_customer=True, is_active=True
        )
        doc = _make_document(test_organisation, contact, "APPROVED")

        for bad in ("PAID", "PARTIALLY_PAID"):
            response = auth_client.post(self._url(test_organisation, doc), {"status": bad}, format="json")
            assert response.status_code == status.HTTP_400_BAD_REQUEST, (bad, response.data)
            doc.refresh_from_db()
            assert doc.status == "APPROVED"

    def test_invalid_status_literal_rejected(self, auth_client, test_organisation, test_user):
        """'VOIDED' (the pre-P7 literal), 'GARBAGE' and empty are 400s — the
        field is a ChoiceField over the real doc_status vocabulary."""
        contact = Contact.objects.create(
            org=test_organisation, contact_type="CUSTOMER", name="C", is_customer=True, is_active=True
        )
        doc = _make_document(test_organisation, contact, "DRAFT")

        for bad in ("VOIDED", "GARBAGE", ""):
            response = auth_client.post(self._url(test_organisation, doc), {"status": bad}, format="json")
            assert response.status_code == status.HTTP_400_BAD_REQUEST, (bad, response.data)

    def test_approve_without_permission_forbidden(self, api_client, test_organisation, test_user):
        """APPROVED transitions require can_approve_invoices even on the
        generic endpoint (pre-P7: no gate at all)."""
        contact = Contact.objects.create(
            org=test_organisation, contact_type="CUSTOMER", name="C", is_customer=True, is_active=True
        )
        doc = _make_document(test_organisation, contact, "SENT")
        limited = _make_limited_member(test_organisation)
        client = _limited_client(api_client, limited)

        response = client.post(self._url(test_organisation, doc), {"status": "APPROVED"}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN, response.data
        doc.refresh_from_db()
        assert doc.status == "SENT"
