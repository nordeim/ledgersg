"""P7/F-10: the two settings PATCH endpoints must validate and gate.

`OrganisationSettingsView.patch` and `PeppolSettingsView.patch` setattr raw
request.data onto models (a non-numeric retry_attempts or an invalid
entity_type reached the database and surfaced IntegrityError/TypeError as
500s), and both carried only IsOrgMember — any member could flip
invoicenow_enabled, base currency or the AP provider, while the sibling
OrganisationDetailView.patch correctly requires can_manage_org.
"""

import pytest
from rest_framework import status

from apps.core.models import Role, UserOrganisation
from tests.integration.test_document_status_view_p7 import (
    _limited_client,
    _make_limited_member,
)


@pytest.mark.django_db
class TestOrganisationSettingsPatch:
    def test_invalid_entity_type_is_400_not_500(self, auth_client, test_organisation):
        url = f"/api/v1/{test_organisation.id}/settings/"
        response = auth_client.patch(url, {"entity_type": "not-a-real-type"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.data

    def test_invalid_fy_start_month_is_400(self, auth_client, test_organisation):
        url = f"/api/v1/{test_organisation.id}/settings/"
        response = auth_client.patch(url, {"fy_start_month": 13}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.data

    def test_valid_patch_round_trips(self, auth_client, test_organisation):
        url = f"/api/v1/{test_organisation.id}/settings/"
        response = auth_client.patch(
            url, {"fy_start_month": 4, "base_currency": "SGD"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        test_organisation.refresh_from_db()
        assert test_organisation.fy_start_month == 4

    def test_member_without_manage_org_forbidden(
        self, api_client, test_organisation
    ):
        limited = _make_limited_member(test_organisation)
        client = _limited_client(api_client, limited)
        url = f"/api/v1/{test_organisation.id}/settings/"
        response = client.patch(url, {"fy_start_month": 7}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN, response.data
        test_organisation.refresh_from_db()
        assert test_organisation.fy_start_month != 7


@pytest.mark.django_db
class TestPeppolSettingsPatch:
    def url(self, org):
        return f"/api/v1/{org.id}/peppol/settings/"

    def test_non_numeric_retry_attempts_is_400_not_500(self, auth_client, test_organisation):
        response = auth_client.patch(
            self.url(test_organisation), {"retry_attempts": "abc"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.data

    def test_member_without_manage_org_forbidden(
        self, api_client, test_organisation
    ):
        limited = _make_limited_member(test_organisation)
        client = _limited_client(api_client, limited)
        response = client.patch(
            self.url(test_organisation), {"enabled": True}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN, response.data

    def test_valid_patch_round_trips(self, auth_client, test_organisation):
        response = auth_client.patch(
            self.url(test_organisation),
            {"enabled": True, "retry_attempts": 5},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        test_organisation.refresh_from_db()
        assert test_organisation.invoicenow_enabled is True


@pytest.mark.django_db
class TestDashboardMetricsPermission:
    def test_member_without_view_reports_forbidden(self, api_client, test_organisation):
        """P7/F-15: financial dashboard metrics require can_view_reports
        (any member could read them pre-P7)."""
        limited = _make_limited_member(test_organisation, can_view_reports=False)
        client = _limited_client(api_client, limited)
        url = f"/api/v1/{test_organisation.id}/reports/dashboard/metrics/"
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN, response.data
