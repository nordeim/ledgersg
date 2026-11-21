"""P7/F-4: the fiscal-period/close endpoints must be ROUTED.

The three org-scoped fiscal routes existed only in the shadowed
apps/core/urls.py module (Python resolves apps.core.urls to the PACKAGE),
so every frontend call to /fiscal-periods/, /fiscal-years/{id}/close/ and
/fiscal-periods/{id}/close/ 404'd. The close views additionally lacked
CanManageOrg and used naive datetimes.
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestFiscalRoutes:
    def test_fiscal_periods_list_routed(self, auth_client, test_organisation, test_fiscal_period):
        """GET /api/v1/{org}/fiscal-periods/ returns the periods (was 404)."""
        url = f"/api/v1/{test_organisation.id}/fiscal-periods/"
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK, response.data
        assert "results" in response.data
        assert response.data["count"] >= 1

    def test_fiscal_period_close_routed_and_managed(
        self, api_client, auth_client, test_organisation, test_fiscal_period
    ):
        """POST /fiscal-periods/{id}/close/ is routed, gated on can_manage_org
        and closes the period."""
        period = test_fiscal_period
        url = f"/api/v1/{test_organisation.id}/fiscal-periods/{period.id}/close/"

        # Owner (has can_manage_org) may close.
        response = auth_client.post(url)
        assert response.status_code == status.HTTP_200_OK, response.data
        period.refresh_from_db()
        assert period.is_open is False

    def test_fiscal_year_close_routed(self, auth_client, test_organisation, test_fiscal_period):
        """POST /fiscal-years/{id}/close/ is routed (was 404)."""
        year = test_fiscal_period.fiscal_year
        url = f"/api/v1/{test_organisation.id}/fiscal-years/{year.id}/close/"
        response = auth_client.post(url)
        assert response.status_code == status.HTTP_200_OK, response.data
        year.refresh_from_db()
        assert year.is_closed is True
