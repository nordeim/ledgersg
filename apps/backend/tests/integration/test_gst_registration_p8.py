"""
P8/G-1: GST registration write actions are manager-gated again.

The P7/F-10 get_permissions() refactor was applied to GSTRegistrationView — but
this view has no PATCH; its mutating verbs are POST (register) and DELETE
(deregister). Class-level CanManageOrg was removed, so ANY org member could
register/deregister the organisation for GST post-P7.
"""

from datetime import date

import pytest
from rest_framework import status

from apps.core.models import Role, UserOrganisation


def _make_client(api_client, user):
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return api_client


def _make_limited_member(org, **role_flags):
    from apps.core.models import AppUser

    defaults = {
        "can_manage_org": False,
        "can_manage_users": False,
        "can_manage_coa": False,
        "can_create_invoices": False,
        "can_approve_invoices": False,
        "can_void_invoices": False,
        "can_create_journals": False,
        "can_manage_banking": False,
        "can_file_gst": False,
        "can_view_reports": False,
        "can_export_data": False,
    }
    defaults.update(role_flags)
    role = Role.objects.create(org=org, name="Limited P8", description="P8 test role", **defaults)

    import uuid

    user = AppUser.objects.create(
        id=uuid.uuid4(),
        email=f"limited_p8_{uuid.uuid4().hex[:8]}@example.com",
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
class TestGSTRegistrationPermissions:
    """POST/DELETE on /{org}/gst/ change core tax configuration — managers only."""

    def _url(self, org):
        return f"/api/v1/{org.id}/gst/"

    def _prepare(self, org):
        org.gst_registered = False
        org.gst_reg_number = ""
        org.save()

    def test_register_without_manage_org_forbidden(
        self, api_client, test_organisation, test_user
    ):
        self._prepare(test_organisation)
        limited = _make_limited_member(test_organisation)
        client = _make_client(api_client, limited)

        response = client.post(
            self._url(test_organisation),
            {"gst_reg_number": "M87654321W", "gst_reg_date": "2024-06-01"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN, response.content
        test_organisation.refresh_from_db()
        assert test_organisation.gst_registered is False

    def test_deregister_without_manage_org_forbidden(
        self, api_client, test_organisation, test_user
    ):
        test_organisation.gst_registered = True
        test_organisation.gst_reg_number = "M87654321W"
        test_organisation.save()
        limited = _make_limited_member(test_organisation)
        client = _make_client(api_client, limited)

        response = client.delete(self._url(test_organisation))
        assert response.status_code == status.HTTP_403_FORBIDDEN, response.content
        test_organisation.refresh_from_db()
        assert test_organisation.gst_registered is True

    def test_register_with_manage_org_allowed(self, api_client, test_organisation, test_user):
        self._prepare(test_organisation)
        manager = _make_limited_member(test_organisation, can_manage_org=True)
        client = _make_client(api_client, manager)

        response = client.post(
            self._url(test_organisation),
            {"gst_reg_number": "M87654321W", "gst_reg_date": "2024-06-01"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.content
        test_organisation.refresh_from_db()
        assert test_organisation.gst_registered is True
