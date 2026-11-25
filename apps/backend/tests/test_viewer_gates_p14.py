"""
P14/M-5 — the Viewer role is read-only.

The pre-P14 contact mutations (create/patch/delete) and the invoice-send
path used only IsOrgMember — a Viewer could create contacts, deactivate
them and reach the send path. The permission matrix in the Role model
(can_create_invoices, can_manage_coa, …) is now reflected: contact
mutations and document sending require can_create_invoices — the same
verb the document-create path already uses (managing the master data
your own invoices need).
"""

import uuid
from datetime import date

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import AppUser, Organisation, Role, UserOrganisation
from tests.conftest import create_test_contact


def _org_with_role(role_flags):
    user = AppUser.objects.create(
        id=uuid.uuid4(),
        email=f"viewer_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Role Probe",
        is_active=True,
    )
    org = Organisation.objects.create(
        name=f"Role Org {uuid.uuid4().hex[:6]}", entity_type="PRIVATE_LIMITED", base_currency="SGD"
    )
    role = Role.objects.create(org=org, name="Custom", description="probe", **role_flags)
    UserOrganisation.objects.create(
        user=user, org=org, role=role, is_default=True,
        invited_at=date.today(), accepted_at=date.today(),
    )
    return user, org


def _client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


VIEWER = {
    "can_manage_org": False, "can_manage_users": False, "can_manage_coa": False,
    "can_create_invoices": False, "can_approve_invoices": False,
    "can_void_invoices": False, "can_create_journals": False,
    "can_manage_banking": False, "can_file_gst": False,
    "can_view_reports": True, "can_export_data": False,
}

MANAGER = {**VIEWER, "can_create_invoices": True}


class TestViewerGatesP14:
    @pytest.mark.django_db
    def test_viewer_cannot_create_contacts(self):
        """RED for M-5: Viewer POST /invoicing/contacts/ → 403."""
        user, org = _org_with_role(VIEWER)
        client = _client(user)
        r = client.post(
            f"/api/v1/{org.id}/invoicing/contacts/",
            {"name": "Probe Contact", "contact_type": "CUSTOMER", "is_customer": True},
            format="json",
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN, (
            f"Viewer must not create contacts (got {r.status_code})"
        )

    @pytest.mark.django_db
    def test_viewer_cannot_delete_contacts(self):
        """RED for M-5: Viewer DELETE /invoicing/contacts/{id}/ → 403."""
        user, org = _org_with_role(VIEWER)
        contact = create_test_contact(org, is_customer=True)
        client = _client(user)
        r = client.delete(f"/api/v1/{org.id}/invoicing/contacts/{contact.id}/")
        assert r.status_code == status.HTTP_403_FORBIDDEN, (
            f"Viewer must not deactivate contacts (got {r.status_code})"
        )

    @pytest.mark.django_db
    def test_viewer_cannot_patch_contacts(self):
        """RED for M-5: Viewer PATCH /invoicing/contacts/{id}/ → 403."""
        user, org = _org_with_role(VIEWER)
        contact = create_test_contact(org, is_customer=True)
        client = _client(user)
        r = client.patch(
            f"/api/v1/{org.id}/invoicing/contacts/{contact.id}/",
            {"name": "Renamed"},
            format="json",
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN, (
            f"Viewer must not update contacts (got {r.status_code})"
        )

    @pytest.mark.django_db
    def test_viewer_can_read_contacts(self):
        """Control: the Viewer's read paths stay green."""
        user, org = _org_with_role(VIEWER)
        create_test_contact(org, is_customer=True)
        client = _client(user)
        r = client.get(f"/api/v1/{org.id}/invoicing/contacts/")
        assert r.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_viewer_cannot_send_documents(self):
        """RED for M-5: the send path requires can_create_invoices."""
        from apps.invoicing.services import DocumentService

        user, org = _org_with_role(VIEWER)
        contact = create_test_contact(org, is_customer=True)
        doc = DocumentService.create_document(
            org_id=org.id,
            document_type="SALES_INVOICE",
            contact_id=contact.id,
            issue_date=date.today(),
            lines=[],
            user_id=user.id,
        )
        client = _client(user)
        r = client.post(
            f"/api/v1/{org.id}/invoicing/documents/{doc.id}/send/",
            {"to": ["someone@example.com"]},
            format="json",
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN, (
            f"Viewer must not send documents (got {r.status_code})"
        )

    @pytest.mark.django_db
    def test_manager_can_create_contacts(self):
        """Control: can_create_invoices carries the contact mutations."""
        user, org = _org_with_role(MANAGER)
        client = _client(user)
        r = client.post(
            f"/api/v1/{org.id}/invoicing/contacts/",
            {"name": "Manager Contact", "contact_type": "CUSTOMER", "is_customer": True},
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED, (
            f"Manager must create contacts (got {r.status_code})"
        )
