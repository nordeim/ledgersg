"""
P11/M-1 + M-11 — the GST deadlines surface tells the truth.

- M-1: the deadlines endpoint returned `{"data": [...], "count": n}` while
  the frontend hook typed and read `{results: []}` — the banner's
  `gstDeadlines.data?.results?.[0]` was always undefined and NEVER
  rendered. The backend standardizes to `{results, count}` — the
  B6-family list convention every sibling endpoint uses.
- M-11: `get_upcoming_deadlines` filtered `status__in=["DRAFT", "COMPUTED"]`
  — a REVIEWED-but-unfiled return (the state the P10/H-3 wire added) was
  invisible to the deadline banner exactly one step before filing.
"""

import uuid
from datetime import date, timedelta

import pytest
from rest_framework import status

from apps.core.models import AppUser, GSTReturn, Organisation, Role, UserOrganisation
from apps.gst.services.return_service import GSTReturnService

pytestmark = pytest.mark.django_db


def _org_with_owner():
    user = AppUser.objects.create(
        id=uuid.uuid4(),
        email=f"gstdl_{uuid.uuid4().hex[:8]}@example.com",
        full_name="GST Deadlines Tester",
        is_active=True,
    )
    org = Organisation.objects.create(
        name="GST Deadlines Org",
        entity_type="PRIVATE_LIMITED",
        base_currency="SGD",
        uen=f"T{uuid.uuid4().hex[:9].upper()}",
    )
    role = Role.objects.create(
        org=org, name="Owner", description="o",
        can_view_reports=True, can_file_gst=True,
    )
    UserOrganisation.objects.create(
        user=user, org=org, role=role, is_default=True,
        invited_at=date.today(), accepted_at=date.today(),
    )
    return user, org


def _return(org, status_value, due_date):
    return GSTReturn.objects.create(
        org=org,
        return_type="F5",
        period_start=date(2026, 10, 1),
        period_end=date(2026, 12, 31),
        filing_due_date=due_date,
        status=status_value,
    )


def _client(user):
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


class TestDeadlinesEnvelope:
    def test_deadlines_endpoint_uses_results_envelope(self):
        """RED for M-1: the envelope is {results, count}, the repo's list convention."""
        user, org = _org_with_owner()
        _return(org, "DRAFT", date.today() + timedelta(days=10))
        client = _client(user)

        response = client.get(
            f"/api/v1/{org.id}/gst/returns/deadlines/", format="json"
        )

        assert response.status_code == status.HTTP_200_OK, response.content
        payload = response.data
        assert "results" in payload, (
            f"the deadlines endpoint must speak the repo's list envelope "
            f"({{'results', 'count'}}) — the hook reads results and the "
            f"banner never rendered (got keys: {list(payload)})"
        )
        assert "data" not in payload
        assert payload["count"] == len(payload["results"]) == 1
        assert str(payload["results"][0]["filing_due_date"]) == str(
            date.today() + timedelta(days=10)
        )


class TestReviewedVisibility:
    def test_reviewed_return_visible_in_deadlines(self):
        """RED for M-11: a REVIEWED-but-unfiled return must surface.

        REVIEWED is the state between compute and file — exactly one step
        before the statutory deadline is missed.
        """
        _, org = _org_with_owner()
        _return(org, "REVIEWED", date.today() + timedelta(days=5))

        deadlines = GSTReturnService.get_upcoming_deadlines(org_id=org.id, days=30)

        assert len(deadlines) == 1, (
            "a REVIEWED-but-unfiled return must appear in the upcoming "
            "deadlines — the banner was blind exactly one step before filing"
        )
        assert deadlines[0].status == "REVIEWED"

    def test_filed_returns_stay_invisible(self):
        """FILED returns are done — they never surface in deadlines."""
        _, org = _org_with_owner()
        _return(org, "FILED", date.today() + timedelta(days=5))

        deadlines = GSTReturnService.get_upcoming_deadlines(org_id=org.id, days=30)
        assert deadlines == []
