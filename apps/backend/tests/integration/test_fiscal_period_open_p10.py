"""
P10/M-8: fiscal periods can be OPENED. The invoice-approval path raises
"No open fiscal period found… Please open the fiscal period or change the
invoice date" (document_service.py:646-650) — but NO endpoint could open a
period (only close existed), and no UI consumed any fiscal endpoint. The
back-dated invoice was a dead end whose error pointed at an impossible
action.

POST /fiscal-periods/{id}/open/ — symmetric to close: manager-gated
(CanManageOrg), is_open=True, clears locked_at/locked_by, refuses an
already-open period (400), refuses when the parent year is closed (400 —
a closed year is accounting history; its periods stay shut).
"""

from datetime import date
from uuid import uuid4

import pytest
from rest_framework import status

from apps.core.models import AppUser, FiscalPeriod, FiscalYear, Role, UserOrganisation


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
        org=org, name=f"Limited P10M8 {uuid4().hex[:6]}", description="P10/M-8", **defaults
    )
    user = AppUser.objects.create(
        id=uuid4(),
        email=f"limited_p10m8_{uuid4().hex[:8]}@example.com",
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
def closed_period(test_organisation, test_user):
    """A closed period in an open year, locked by the test user."""
    fy = FiscalYear.objects.create(
        org=test_organisation, label="FY2024",
        start_date=date(2024, 1, 1), end_date=date(2024, 12, 31),
        is_closed=False,
    )
    from django.utils import timezone

    return FiscalPeriod.objects.create(
        org=test_organisation, fiscal_year=fy, label="January 2024",
        period_number=1, start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31), is_open=False,
        locked_at=timezone.now(), locked_by=test_user.id,
    )


@pytest.mark.django_db
class TestFiscalPeriodOpenP10:
    """POST /fiscal-periods/{id}/open/ — the missing control act."""

    def _url(self, org, period):
        return f"/api/v1/{org.id}/fiscal-periods/{period.id}/open/"

    def test_open_is_manager_gated(
        self, api_client, test_organisation, closed_period
    ):
        """A member whose role lacks can_manage_org gets 403 (close parity)."""
        member = _limited_member(test_organisation)
        _auth(api_client, member)

        response = api_client.post(self._url(test_organisation, closed_period))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        closed_period.refresh_from_db()
        assert closed_period.is_open is False

    def test_open_reopens_and_clears_the_lock(
        self, api_client, test_user, test_organisation, closed_period
    ):
        """The manager act: is_open=True, locked_at/locked_by cleared."""
        _auth(api_client, test_user)

        response = api_client.post(self._url(test_organisation, closed_period))

        assert response.status_code == status.HTTP_200_OK, response.data
        closed_period.refresh_from_db()
        assert closed_period.is_open is True
        assert closed_period.locked_at is None
        assert closed_period.locked_by is None

    def test_open_an_open_period_is_400(
        self, api_client, test_user, test_organisation, closed_period
    ):
        """Idempotence refusal parity with close's double-close 400."""
        closed_period.is_open = True
        closed_period.locked_at = None
        closed_period.locked_by = None
        closed_period.save()
        _auth(api_client, test_user)

        response = api_client.post(self._url(test_organisation, closed_period))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already open" in str(response.data).lower()

    def test_open_under_a_closed_year_is_400(
        self, api_client, test_user, test_organisation, closed_period
    ):
        """A closed year is history — its periods cannot be reopened (the
        year-close precondition would be trivially circumventable)."""
        fy = closed_period.fiscal_year
        fy.is_closed = True
        fy.save()
        _auth(api_client, test_user)

        response = api_client.post(self._url(test_organisation, closed_period))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "closed" in str(response.data).lower()
        closed_period.refresh_from_db()
        assert closed_period.is_open is False

    def test_open_unknown_period_is_404(
        self, api_client, test_user, test_organisation
    ):
        _auth(api_client, test_user)

        response = api_client.post(
            f"/api/v1/{test_organisation.id}/fiscal-periods/{uuid4()}/open/"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
