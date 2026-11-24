"""
P9/C-3: InvoiceNow transmits invoices only.

Pre-P9: send_invoicenow checked status == APPROVED but never the document
type — and the P8 Convert flow mass-produces APPROVED quotes, while the
transmission path maps anything non-credit-note to UBL Invoice. Any org
member (the view's permission was IsOrgMember only, looser than every
sibling mutation) could POST an APPROVED quote and a quotation would go
out as a tax invoice into the recipient's AP pipeline.
"""

from unittest.mock import Mock, patch

import pytest
from rest_framework import status

from tests.conftest import create_test_contact, create_test_invoice


def _auth(api_client, user):
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return api_client


def _make_limited_member(org, **role_flags):
    """An accepted member with an all-False role unless flags say otherwise."""
    from datetime import date
    from uuid import uuid4

    from apps.core.models import AppUser, Role, UserOrganisation

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
    role = Role.objects.create(org=org, name="Limited P9", description="P9 test role", **defaults)
    user = AppUser.objects.create(
        id=uuid4(),
        email=f"limited_p9_{uuid4().hex[:8]}@example.com",
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


def _peppol_settings(org):
    from apps.peppol.models import OrganisationPeppolSettings

    return OrganisationPeppolSettings.objects.create(
        org=org,
        access_point_provider="storecove",
        access_point_api_url="https://api.storecove.example",
        access_point_api_key="test-key",
        access_point_client_id="test-client",
        auto_transmit=False,
        is_active=True,
    )


@pytest.mark.django_db
class TestInvoiceNowQuoteGate:
    """The type gate and the view permission, at the HTTP surface."""

    def test_approved_quote_is_refused(self, api_client, test_user, test_organisation):
        """An APPROVED SALES_QUOTE must not be transmittable — 400 naming the type."""
        _peppol_settings(test_organisation)
        contact = create_test_contact(test_organisation, peppol_id="0195:SG-UUID:demo-recipient")
        quote = create_test_invoice(
            test_organisation, contact, status="APPROVED", document_type="SALES_QUOTE"
        )
        _auth(api_client, test_user)

        url = (
            f"/api/v1/{test_organisation.id}/invoicing/"
            f"documents/{quote.id}/send-invoicenow/"
        )
        response = api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.data
        # The refusal must name the document type so the caller understands.
        assert "SALES_QUOTE" in str(response.data) or "quote" in str(response.data).lower()

    def test_approved_invoice_still_transmits(
        self, api_client, test_user, test_organisation
    ):
        """The gate must not break the legitimate flow: APPROVED SALES_INVOICE queues."""
        _peppol_settings(test_organisation)
        contact = create_test_contact(test_organisation, peppol_id="0195:SG-UUID:demo-recipient")
        invoice = create_test_invoice(test_organisation, contact, status="APPROVED")
        _auth(api_client, test_user)

        url = (
            f"/api/v1/{test_organisation.id}/invoicing/"
            f"documents/{invoice.id}/send-invoicenow/"
        )
        with patch("apps.peppol.tasks.transmit_peppol_invoice_task.delay") as mock_delay:
            mock_delay.return_value = Mock(id="task-123")
            response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK, response.data
        assert mock_delay.called, "the real Celery task must still be queued"

    def test_member_without_create_invoices_gets_403(
        self, api_client, test_organisation
    ):
        """View permission parity with QuoteConvertView (CanCreateInvoices)."""
        _peppol_settings(test_organisation)
        contact = create_test_contact(test_organisation, peppol_id="0195:SG-UUID:demo-recipient")
        invoice = create_test_invoice(test_organisation, contact, status="APPROVED")
        member = _make_limited_member(test_organisation)
        _auth(api_client, member)

        url = (
            f"/api/v1/{test_organisation.id}/invoicing/"
            f"documents/{invoice.id}/send-invoicenow/"
        )
        response = api_client.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN, response.data


# ---------------------------------------------------------------------------
# P13/B-10: the InvoiceNow endpoints must honor the typed 404 contract.
# send_invoicenow/get_invoicenow_status used raw .objects.get() — a missing
# document raised DoesNotExist, which is NOT a LedgerSGException, so the
# handler rendered it as a 500 instead of the 404 envelope every sibling
# endpoint returns.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestInvoiceNowMissingDocumentP13:
    def test_send_invoicenow_missing_document_is_404(
        self, api_client, test_user, test_organisation
    ):
        from uuid import uuid4

        client = _auth(api_client, test_user)
        url = (
            f"/api/v1/{test_organisation.id}/invoicing/documents/"
            f"{uuid4()}/send-invoicenow/"
        )
        response = client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND, (
            "A missing document must surface the typed 404 envelope, not a 500 "
            "(P13/B-10)."
        )
        assert response.data["error"]["code"] == "not_found"

    def test_invoicenow_status_missing_document_is_404(
        self, api_client, test_user, test_organisation
    ):
        from uuid import uuid4

        client = _auth(api_client, test_user)
        url = (
            f"/api/v1/{test_organisation.id}/invoicing/documents/"
            f"{uuid4()}/invoicenow-status/"
        )
        response = client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND, (
            "A missing document must surface the typed 404 envelope, not a 500 "
            "(P13/B-10)."
        )
        assert response.data["error"]["code"] == "not_found"
