"""
P9/C-5: status_history stops lying.

get_status_history returned [] behind a TODO while the model carries the
timestamps a real history needs (created_at -> DRAFT, approved_at ->
APPROVED, voided_at -> VOID). The field is typed and shipped to every
detail consumer; the synthesis is pure read-side code.
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from rest_framework import status

from apps.core.models import AppUser, Contact, InvoiceDocument, Organisation

pytestmark = pytest.mark.django_db


def _doc(org, contact, **kw):
    defaults = {
        "org": org,
        "document_type": "SALES_INVOICE",
        "document_number": "INV-SH-1",
        "contact": contact,
        "issue_date": date(2024, 1, 15),
        "due_date": date(2024, 2, 15),
        "currency": "SGD",
        "exchange_rate": Decimal("1.000000"),
        "total_excl": Decimal("100.0000"),
        "total_incl": Decimal("109.0000"),
        "amount_paid": Decimal("0.0000"),
        "status": "DRAFT",
    }
    defaults.update(kw)
    return InvoiceDocument.objects.create(**defaults)


@pytest.fixture
def org_and_client():
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    user = AppUser.objects.create(
        id=uuid.uuid4(),
        email=f"sh_{uuid.uuid4().hex[:8]}@example.com",
        full_name="SH User",
        is_active=True,
    )
    org = Organisation.objects.create(
        name="SH Org", entity_type="PRIVATE_LIMITED", base_currency="SGD"
    )
    from apps.core.models import Role, UserOrganisation

    role = Role.objects.create(org=org, name="Owner", description="o", can_manage_org=True)
    UserOrganisation.objects.create(
        user=user, org=org, role=role, is_default=True,
        invited_at=date.today(), accepted_at=date.today(),
    )
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return org, client


class TestStatusHistoryP9:
    def test_history_synthesizes_from_timestamps(self, org_and_client):
        org, client = org_and_client
        contact = Contact.objects.create(
            org=org, contact_type="CUSTOMER", name="SH C", is_customer=True, is_active=True
        )
        doc = _doc(
            org,
            contact,
            status="APPROVED",
            approved_at=datetime(2024, 1, 16, 10, 0, tzinfo=UTC),
        )

        response = client.get(f"/api/v1/{org.id}/invoicing/documents/{doc.id}/")

        assert response.status_code == status.HTTP_200_OK, response.data
        history = response.data["status_history"]
        # Chronological: DRAFT (creation) then APPROVED (approved_at).
        assert [h["status"] for h in history] == ["DRAFT", "APPROVED"]
        assert history[0]["at"]
        assert history[1]["at"].startswith("2024-01-16")

    def test_voided_document_carries_the_void_entry(self, org_and_client):
        org, client = org_and_client
        contact = Contact.objects.create(
            org=org, contact_type="CUSTOMER", name="SH C2", is_customer=True, is_active=True
        )
        doc = _doc(
            org,
            contact,
            status="VOID",
            approved_at=datetime(2024, 1, 16, 10, 0, tzinfo=UTC),
            voided_at=datetime(2024, 1, 20, 9, 30, tzinfo=UTC),
        )

        response = client.get(f"/api/v1/{org.id}/invoicing/documents/{doc.id}/")

        history = response.data["status_history"]
        assert [h["status"] for h in history] == ["DRAFT", "APPROVED", "VOID"]

    def test_list_serializer_exposes_related_document_for_the_badge(self, org_and_client):
        """P9/C-6: the quotes list's CONVERTED badge gates on the link, so
        the list serializer must carry related_document_id."""
        org, client = org_and_client
        contact = Contact.objects.create(
            org=org, contact_type="CUSTOMER", name="SH C3", is_customer=True, is_active=True
        )
        _doc(org, contact, status="APPROVED")

        response = client.get(
            f"/api/v1/{org.id}/invoicing/documents/", {"type": "SALES_INVOICE"}
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert "related_document_id" in response.data["results"][0]
