"""
P11/M-2 — the bank-account PATCH 404s on a missing id.

The update view bound its instance via BankAccount.objects.get(...) —
DoesNotExist unhandled → 500 on a missing/deactivated account, where the
GET/DELETE siblings correctly return 404 (they route through
BankAccountService.get, which raises ResourceNotFound → 404). The PATCH
now routes the same way.
"""

import uuid
from datetime import date

import pytest
from rest_framework import status

from apps.core.models import AppUser, Organisation, Role, UserOrganisation

pytestmark = pytest.mark.django_db


def _org_with_banker():
    user = AppUser.objects.create(
        id=uuid.uuid4(),
        email=f"patch_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Banker",
        is_active=True,
    )
    org = Organisation.objects.create(
        name="Patch Org",
        entity_type="PRIVATE_LIMITED",
        base_currency="SGD",
        uen=f"T{uuid.uuid4().hex[:9].upper()}",
    )
    role = Role.objects.create(
        org=org, name="Owner", description="o",
        can_manage_banking=True, can_manage_org=True,
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


class TestBankAccountPatch404:
    def test_patch_missing_account_returns_404_not_500(self):
        """RED for M-2: PATCH on a random UUID must 404 (today: 500)."""
        user, org = _org_with_banker()
        client = _client(user)
        missing = uuid.uuid4()

        response = client.patch(
            f"/api/v1/{org.id}/banking/bank-accounts/{missing}/",
            {"account_name": "x"},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND, (
            f"PATCH on a missing bank account must 404 like GET/DELETE — "
            f"got {response.status_code}"
        )

    def test_get_and_delete_missing_account_still_404(self):
        """Regression guard: the GET/DELETE paths keep their 404s."""
        user, org = _org_with_banker()
        client = _client(user)
        missing = uuid.uuid4()

        get_response = client.get(
            f"/api/v1/{org.id}/banking/bank-accounts/{missing}/", format="json"
        )
        delete_response = client.delete(
            f"/api/v1/{org.id}/banking/bank-accounts/{missing}/", format="json"
        )

        assert get_response.status_code == status.HTTP_404_NOT_FOUND
        assert delete_response.status_code == status.HTTP_404_NOT_FOUND
