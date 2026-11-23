"""
P11/M-5 — the organisation PATCH paths fail with 400s, not 500s.

The detail PATCH is a raw allowlist: `entity_type="PTE_LTD"` violates the
DB CHECK, `base_currency="SGDD"` exceeds CHAR(3), `country="SGP"` exceeds
CHAR(2) — all IntegrityError/DataError 500s. The settings serializer
leaves `gst_scheme`/`gst_filing_frequency` free-text (CHECK vocabulary
violations → 500), `timezone` max_length=63 vs the DB's VARCHAR(50)
(DataError 500), and PATCHing `gst_registered: true` without a
`gst_reg_date` violates chk_gst_consistency (500). Everything below must
be a 400 field error.
"""

import uuid
from datetime import date

import pytest
from rest_framework import status

from apps.core.models import AppUser, Organisation, Role, UserOrganisation

pytestmark = pytest.mark.django_db


def _org_with_manager(**org_kwargs):
    user = AppUser.objects.create(
        id=uuid.uuid4(),
        email=f"orgpatch_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Org Patch Tester",
        is_active=True,
    )
    defaults = dict(
        name="Patch Org",
        entity_type="PRIVATE_LIMITED",
        base_currency="SGD",
        uen=f"T{uuid.uuid4().hex[:9].upper()}",
        gst_registered=False,
        fy_start_month=1,
    )
    defaults.update(org_kwargs)
    org = Organisation.objects.create(**defaults)
    role = Role.objects.create(
        org=org, name="Owner", description="o", can_manage_org=True,
    )
    UserOrganisation.objects.create(
        user=user, org=org, role=role, is_default=True,
        invited_at=date.today(), accepted_at=date.today(),
    )
    return user, org


def _client(user):
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


class TestOrganisationDetailPatch400s:
    def test_patch_entity_type_out_of_vocabulary_returns_400(self):
        """RED for M-5: `PTE_LTD` violates the DB CHECK (today: 500)."""
        user, org = _org_with_manager()
        client = _client(user)

        response = client.patch(
            f"/api/v1/{org.id}/", {"entity_type": "PTE_LTD"}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"an out-of-vocabulary entity_type must be a 400 field error — "
            f"got {response.status_code}"
        )

    def test_patch_base_currency_too_long_returns_400(self):
        """RED for M-5: `SGDD` exceeds CHAR(3) (today: DataError 500)."""
        user, org = _org_with_manager()
        client = _client(user)

        response = client.patch(
            f"/api/v1/{org.id}/", {"base_currency": "SGDD"}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_country_too_long_returns_400(self):
        """RED for M-5: `SGP` exceeds CHAR(2) (today: DataError 500)."""
        user, org = _org_with_manager()
        client = _client(user)

        response = client.patch(
            f"/api/v1/{org.id}/", {"country": "SGP"}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_valid_fields_still_work(self):
        """Regression guard: a truthful PATCH keeps its 200."""
        user, org = _org_with_manager()
        client = _client(user)

        response = client.patch(
            f"/api/v1/{org.id}/",
            {"name": "Renamed Org", "city": "Singapore"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.content
        org.refresh_from_db()
        assert org.name == "Renamed Org"
        assert org.city == "Singapore"


class TestOrganisationSettingsPatch400s:
    def test_patch_gst_scheme_out_of_vocabulary_returns_400(self):
        """RED for M-5: free-text gst_scheme violates the DB CHECK (500)."""
        user, org = _org_with_manager()
        client = _client(user)

        response = client.patch(
            f"/api/v1/{org.id}/settings/", {"gst_scheme": "whenever"}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"got {response.status_code}"
        )

    def test_patch_gst_filing_frequency_out_of_vocabulary_returns_400(self):
        """RED for M-5: free-text frequency violates the DB CHECK (500)."""
        user, org = _org_with_manager()
        client = _client(user)

        response = client.patch(
            f"/api/v1/{org.id}/settings/",
            {"gst_filing_frequency": "hourly"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_timezone_longer_than_db_column_returns_400(self):
        """RED for M-5: serializer allows 63 chars, the DB column is 50."""
        user, org = _org_with_manager()
        client = _client(user)

        response = client.patch(
            f"/api/v1/{org.id}/settings/",
            {"timezone": "x" * 51},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_gst_registered_true_without_reg_date_returns_400(self):
        """RED for M-5: violates chk_gst_consistency (today: 500)."""
        user, org = _org_with_manager()
        client = _client(user)

        response = client.patch(
            f"/api/v1/{org.id}/settings/",
            {"gst_registered": True},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"registering for GST without a reg date must be a 400 — "
            f"got {response.status_code}"
        )

    def test_patch_gst_registered_true_with_reg_date_works(self):
        """The truthful registration PATCH keeps its 200."""
        user, org = _org_with_manager()
        client = _client(user)

        response = client.patch(
            f"/api/v1/{org.id}/settings/",
            {
                "gst_registered": True,
                "gst_reg_number": "M12345678X",
                "gst_reg_date": date(2026, 1, 1),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.content
