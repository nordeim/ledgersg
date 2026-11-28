"""
P34/BE-P34-M1: the ISO-4217 currency-input truth (organisation surfaces).

Pre-P34: base_currency accepted any string up to 3 chars on create
(max_length=3 — not even min_length, so "US" passed) and exactly-3 chars
on PATCH; a typo like "XYZ"/"SGE" reached the database and then propagated
into the P33 currency-truth surfaces (the reports denomination, the Peppol
DocumentCurrencyCode + every amount currencyID, the invoice PDF).
"""

import uuid
from datetime import date

import pytest
from rest_framework import status

from apps.core.models import AppUser, Organisation, Role, UserOrganisation

pytestmark = pytest.mark.django_db


def _manager_client():
    """A user + org + authenticated client (the P11 400-test pattern)."""
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    user = AppUser.objects.create(
        id=uuid.uuid4(),
        email=f"p34curr_{uuid.uuid4().hex[:8]}@example.com",
        full_name="P34 Currency Tester",
        is_active=True,
    )
    org = Organisation.objects.create(
        name="P34 Currency Org",
        entity_type="PRIVATE_LIMITED",
        base_currency="SGD",
        uen=f"T{uuid.uuid4().hex[:9].upper()}",
        gst_registered=False,
        fy_start_month=1,
    )
    role = Role.objects.create(
        org=org, name="Owner", description="o", can_manage_org=True,
    )
    UserOrganisation.objects.create(
        user=user, org=org, role=role, is_default=True,
        invited_at=date.today(), accepted_at=date.today(),
    )
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client, org


_ORG_CREATE_PAYLOAD = {
    "name": "Currency Truth Org",
    "entity_type": "PRIVATE_LIMITED",
    # T/S + YY + 2 letters + 4 digits + letter — the valid "other entities" UEN
    "uen": f"T24LL{uuid.uuid4().int % 10000:04d}A",
    "gst_registered": False,
}


class TestCurrencyVocabularyModule:
    """The shared allowlist pins (no DB — the module's own truth)."""

    def test_the_core_codes_are_present(self):
        from common.currency import ISO_4217_ACTIVE_CODES

        for code in ("SGD", "USD", "EUR", "GBP", "JPY", "AUD", "MYR", "CNY", "HKD", "INR"):
            assert code in ISO_4217_ACTIVE_CODES, f"{code} must be in the allowlist"

    def test_placeholder_and_metal_codes_are_excluded(self):
        from common.currency import ISO_4217_ACTIVE_CODES

        for code in ("XXX", "XTS", "XDR", "XAU", "XAG"):
            assert code not in ISO_4217_ACTIVE_CODES, (
                f"{code} carries no business meaning for an accounting platform"
            )

    def test_withdrawn_codes_are_absent(self):
        from common.currency import ISO_4217_ACTIVE_CODES

        # HRK (euro 2023), ANG (XCG 2025), ZWL (ZWG 2024), SLL (SLE 2022),
        # VEF (VES 2018), and typo-shaped garbage
        for code in ("HRK", "ANG", "ZWL", "SLL", "VEF", "XYZ", "SGE", "USDD", "US"):
            assert code not in ISO_4217_ACTIVE_CODES

    def test_normalize_case_and_whitespace(self):
        from common.currency import normalize_currency_code

        assert normalize_currency_code("usd") == "USD"
        assert normalize_currency_code(" sgd ") == "SGD"
        assert normalize_currency_code("XYZ") is None
        assert normalize_currency_code("") is None
        assert normalize_currency_code(None) is None


class TestOrganisationBaseCurrencyVocabulary:
    """The org create/PATCH currency inputs must be active ISO-4217 codes."""

    def test_create_rejects_out_of_vocabulary_code(self):
        client, _ = _manager_client()

        response = client.post(
            "/api/v1/organisations/",
            {**_ORG_CREATE_PAYLOAD, "base_currency": "XYZ"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"base_currency='XYZ' is not an ISO-4217 currency — must be a "
            f"400 field error, got {response.status_code}"
        )
        assert "base_currency" in str(response.data)

    def test_create_rejects_two_char_code(self):
        """The create path's missing min_length hole: 'US' is not a currency code."""
        client, _ = _manager_client()

        response = client.post(
            "/api/v1/organisations/",
            {**_ORG_CREATE_PAYLOAD, "base_currency": "US"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"base_currency='US' must be a 400 (a 2-char string is not a "
            f"currency code), got {response.status_code}"
        )

    def test_create_normalizes_case(self):
        """A lower-case valid code is accepted and stored upper-cased."""
        client, _ = _manager_client()
        payload = {**_ORG_CREATE_PAYLOAD, "base_currency": "usd"}

        response = client.post("/api/v1/organisations/", payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED, (
            f"'usd' is a valid ISO-4217 code in the wrong case — must be "
            f"accepted + normalized, got {response.status_code}: {response.data}"
        )
        org_id = response.data["id"]
        stored = Organisation.objects.get(id=org_id).base_currency
        assert stored == "USD", (
            f"the stored base_currency must be the normalized 'USD', got {stored!r}"
        )

    def test_create_defaults_to_sgd(self):
        """The control: no base_currency → the SGD default."""
        client, _ = _manager_client()

        response = client.post(
            "/api/v1/organisations/", _ORG_CREATE_PAYLOAD, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        org = Organisation.objects.get(id=response.data["id"])
        assert org.base_currency == "SGD"

    def test_patch_rejects_out_of_vocabulary_code(self):
        client, org = _manager_client()

        response = client.patch(
            f"/api/v1/{org.id}/", {"base_currency": "SGE"}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"base_currency='SGE' is a typo-class code — must be a 400 field "
            f"error, got {response.status_code}"
        )
        assert "base_currency" in str(response.data)

    def test_patch_accepts_valid_code(self):
        """The control: a valid ISO-4217 code PATCHes cleanly."""
        client, org = _manager_client()

        response = client.patch(
            f"/api/v1/{org.id}/", {"base_currency": "USD"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK, (
            f"base_currency='USD' is a valid code — got {response.status_code}: "
            f"{response.data}"
        )
        org.refresh_from_db()
        assert org.base_currency == "USD"
