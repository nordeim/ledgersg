"""
P8/S-1 + S-3: fiscal close requires closed periods; the dead core
dashboard is retired.

The year-close view flipped is_closed with no precondition (its own
docstring said "validation TBD") — closing a year with open periods
silently locks accounting history inconsistently. The core dashboard
(surface + service + 2 test files) is a dead duplicate of the live
reporting one (the frontend and e2e only ever call /reports/dashboard/).
"""

from datetime import date

import pytest
from rest_framework import status

from apps.core.models import FiscalPeriod, FiscalYear


@pytest.mark.django_db
class TestFiscalYearClosePreconditionP8:
    def _fy(self, org):
        return FiscalYear.objects.create(
            org=org, label="FY2024",
            start_date=date(2024, 1, 1), end_date=date(2024, 12, 31),
            is_closed=False,
        )

    def test_close_with_open_periods_is_400(self, auth_client, test_organisation):
        """A year with open periods cannot be closed — the 400 names the
        open periods (pre-P8: the flag flipped and history locked)."""
        fy = self._fy(test_organisation)
        FiscalPeriod.objects.create(
            org=test_organisation, fiscal_year=fy, label="January 2024",
            period_number=1, start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31), is_open=True,
        )
        FiscalPeriod.objects.create(
            org=test_organisation, fiscal_year=fy, label="February 2024",
            period_number=2, start_date=date(2024, 2, 1),
            end_date=date(2024, 2, 29), is_open=False,
        )

        response = auth_client.post(
            f"/api/v1/{test_organisation.id}/fiscal-years/{fy.id}/close/"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.data
        assert "January 2024" in str(response.data), response.data
        fy.refresh_from_db()
        assert fy.is_closed is False

    def test_close_after_all_periods_closed(self, auth_client, test_organisation):
        fy = self._fy(test_organisation)
        FiscalPeriod.objects.create(
            org=test_organisation, fiscal_year=fy, label="January 2024",
            period_number=1, start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31), is_open=False,
        )

        response = auth_client.post(
            f"/api/v1/{test_organisation.id}/fiscal-years/{fy.id}/close/"
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        fy.refresh_from_db()
        assert fy.is_closed is True

    def test_double_close_is_400(self, auth_client, test_organisation):
        fy = self._fy(test_organisation)
        fy.is_closed = True
        fy.save()

        response = auth_client.post(
            f"/api/v1/{test_organisation.id}/fiscal-years/{fy.id}/close/"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestCoreDashboardRetiredP8:
    def test_core_dashboard_route_is_gone(self, auth_client, test_organisation):
        """The dead duplicate surface (frontend only ever calls
        /reports/dashboard/metrics/) returns 404 — one dashboard service
        remains."""
        response = auth_client.get(
            f"/api/v1/{test_organisation.id}/dashboard/"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
