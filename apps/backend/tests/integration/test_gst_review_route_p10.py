"""
P10/H-3: the GST F5 lifecycle is half-wired in the UI, and the review
transition has NO route at all — the service method (review_return,
return_service.py:237) is unreachable over HTTP while its siblings
(file/amend) are routed. The F5 state machine (DRAFT -> COMPUTED ->
REVIEWED -> FILED -> AMENDED) cannot be walked by any client.
"""

from datetime import date
from uuid import uuid4

import pytest
from rest_framework import status

from apps.core.models import AppUser, GSTReturn, Role, UserOrganisation


def _auth(api_client, user):
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return api_client


def _limited_member(org, **role_flags):
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
    role = Role.objects.create(
        org=org, name=f"Limited P10 {uuid4().hex[:6]}", description="P10", **defaults
    )
    user = AppUser.objects.create(
        id=uuid4(),
        email=f"limited_p10_{uuid4().hex[:8]}@example.com",
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


@pytest.fixture
def computed_return(test_organisation):
    return GSTReturn.objects.create(
        org_id=test_organisation.id,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 31),
        filing_due_date=date(2024, 2, 29),
        status="COMPUTED",
    )


@pytest.mark.django_db
class TestGSTReviewRouteP10:
    """POST /{org}/gst/returns/{id}/review/ — the missing state-machine edge."""

    def _url(self, org, ret):
        return f"/api/v1/{org.id}/gst/returns/{ret.id}/review/"

    def test_review_routes_and_transitions_computed_to_reviewed(
        self, api_client, test_user, test_organisation, computed_return
    ):
        """A can_file_gst member walks COMPUTED -> REVIEWED over HTTP."""
        _auth(api_client, test_user)

        response = api_client.post(self._url(test_organisation, computed_return))

        assert response.status_code == status.HTTP_200_OK, response.content
        computed_return.refresh_from_db()
        assert computed_return.status == "REVIEWED"
        assert computed_return.reviewed_by_id == test_user.id
        assert computed_return.reviewed_at is not None

    def test_review_is_permission_gated(
        self, api_client, test_organisation, computed_return
    ):
        """A member whose role lacks can_file_gst gets 403 (parity with file/amend)."""
        member = _limited_member(test_organisation)
        _auth(api_client, member)

        response = api_client.post(self._url(test_organisation, computed_return))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        computed_return.refresh_from_db()
        assert computed_return.status == "COMPUTED"

    def test_review_refuses_non_computed_status(
        self, api_client, test_user, test_organisation
    ):
        """The engine's guard (only COMPUTED can be reviewed) surfaces as a 400."""
        _auth(api_client, test_user)
        draft = GSTReturn.objects.create(
            org_id=test_organisation.id,
            period_start=date(2024, 2, 1),
            period_end=date(2024, 2, 29),
            filing_due_date=date(2024, 3, 31),
            status="DRAFT",
        )

        response = api_client.post(self._url(test_organisation, draft))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        draft.refresh_from_db()
        assert draft.status == "DRAFT"
