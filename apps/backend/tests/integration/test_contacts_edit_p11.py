"""
P11/H-1 + M-4 — the contacts edit surface tells the truth.

- M-4: the edit dialog renders an editable "GST Registration No" field,
  but ContactUpdateSerializer has no gst_reg_number — DRF silently drops
  it; the save says "Contact updated" while nothing persisted.
- H-1 (backend half): the edit dialog prefills from the LIST row, whose
  serializer carries no uen/peppol_id — so those fields prefill blank and
  an unconditional eight-field PATCH erases them. The dialog must prefill
  from the DETAIL payload; the list serializer also gains uen/peppol_id so
  the row badges show real values.
- Contract guard: a partial PATCH (only the fields the user touched)
  must NOT erase unsent fields — the contract the fixed dialog relies on.
"""

import uuid
from datetime import date

import pytest
from rest_framework import status

from apps.core.models import AppUser, Contact, Organisation, Role, UserOrganisation

pytestmark = pytest.mark.django_db


def _org_with_contact(**contact_kwargs):
    user = AppUser.objects.create(
        id=uuid.uuid4(),
        email=f"contact_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Contact Tester",
        is_active=True,
    )
    org = Organisation.objects.create(
        name="Contact Org",
        entity_type="PRIVATE_LIMITED",
        base_currency="SGD",
        uen=f"T{uuid.uuid4().hex[:9].upper()}",
    )
    role = Role.objects.create(
        org=org, name="Owner", description="o",
        can_manage_org=True, can_create_invoices=True,
    )
    UserOrganisation.objects.create(
        user=user, org=org, role=role, is_default=True,
        invited_at=date.today(), accepted_at=date.today(),
    )
    defaults = dict(
        org=org,
        contact_type="CUSTOMER",
        name="Acme Trading Pte Ltd",
        is_customer=True,
        is_supplier=False,
        is_active=True,
        email="acme@example.com",
        uen="199001234D",
        peppol_id="0198:T10987654Z",
        gst_reg_number="M12345678X",
        address_line_1="12 Marina Boulevard",
        postal_code="018982",
    )
    defaults.update(contact_kwargs)
    contact = Contact.objects.create(**defaults)
    return user, org, contact


def _client(user):
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


class TestContactEditTruth:
    def test_patch_gst_reg_number_persists(self):
        """RED for M-4: gst_reg_number PATCHes must persist (today: dropped)."""
        user, org, contact = _org_with_contact()
        client = _client(user)

        response = client.patch(
            f"/api/v1/{org.id}/invoicing/contacts/{contact.id}/",
            {"gst_reg_number": "M87654321W"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.content
        contact.refresh_from_db()
        assert contact.gst_reg_number == "M87654321W", (
            "the update serializer must accept gst_reg_number — the edit "
            "dialog renders the field and reports success while the value "
            "is silently dropped"
        )

    def test_list_rows_carry_uen_and_peppol_id(self):
        """RED for H-1 (backend half): list rows carry the badge fields.

        The edit dialog prefilled from the LIST payload — uen/peppol_id
        were never in it, so they always prefilled blank and an
        unconditional save erased the stored values.
        """
        user, org, contact = _org_with_contact()
        client = _client(user)

        response = client.get(
            f"/api/v1/{org.id}/invoicing/contacts/", format="json"
        )

        assert response.status_code == status.HTTP_200_OK, response.content
        rows = response.data.get("results") or response.data.get("data")
        row = next(r for r in rows if str(r["id"]) == str(contact.id))
        assert row.get("uen") == "199001234D", (
            "list rows must carry uen (the row badge claims it)"
        )
        assert row.get("peppol_id") == "0198:T10987654Z", (
            "list rows must carry peppol_id (the row badge claims it)"
        )

    def test_partial_patch_does_not_erase_unsent_fields(self):
        """Contract guard: PATCHing only email must preserve UEN/Peppol/address.

        The fixed dialog prefills from the detail payload and PATCHes the
        (truthfully prefilled) fields; unsent fields must never be erased
        server-side.
        """
        user, org, contact = _org_with_contact()
        client = _client(user)

        response = client.patch(
            f"/api/v1/{org.id}/invoicing/contacts/{contact.id}/",
            {"email": "new@example.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.content
        contact.refresh_from_db()
        assert contact.email == "new@example.com"
        assert contact.uen == "199001234D", "unsent UEN must survive"
        assert contact.peppol_id == "0198:T10987654Z", "unsent Peppol ID must survive"
        assert contact.address_line_1 == "12 Marina Boulevard"
        assert contact.gst_reg_number == "M12345678X"
