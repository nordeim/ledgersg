"""
P10/M-1: the P9/B-4 null-PayNow fix applied only to the CREATE serializer —
the UPDATE sibling (PATCH /banking/bank-accounts/{id}/) still derives
paynow_type from the model:

- PATCH {"paynow_type": null} → 400 "This field may not be null" (the
  exact wire value P9 fixed for create — the edit UI sends it too);
- PATCH {"paynow_type": ""} → passes (allow_blank), is falsy so both
  pairing checks skip, and "" reaches the DB where it violates
  CHECK (paynow_type IS NULL OR paynow_type IN ('UEN','MOBILE','NRIC'))
  → IntegrityError 500.

Also the I-5 rider: clearing paynow_id alone (""→None) leaves the old
paynow_type dangling — a semantically broken pair the DB accepts.
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
        email=f"banker_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Banker",
        is_active=True,
    )
    org = Organisation.objects.create(
        name="Banker Org",
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


def _create_account(user, org, account_number):
    from apps.core.services.organisation_service import create_organisation

    org = create_organisation(
        user=user,
        name="Seeded Banker Org",
        uen=f"T{uuid.uuid4().hex[:9].upper()}",
    )
    from apps.core.models import Account, BankAccount

    gl = Account.objects.filter(org=org, is_bank=True).first()
    assert gl is not None, "the seeded chart must include bank accounts"
    client = _client(user)
    response = client.post(
        f"/api/v1/{org.id}/banking/bank-accounts/",
        {
            "account_name": "Operating",
            "bank_name": "Test Bank",
            "account_number": account_number,
            "currency": "SGD",
            "gl_account": str(gl.id),
            "paynow_type": "UEN",
            "paynow_id": "201912345A",
            "is_default": False,
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED, response.data
    return org, BankAccount.objects.get(org=org, account_number=account_number)


class TestBankAccountUpdatePayNowP10:
    def _url(self, org, account):
        return f"/api/v1/{org.id}/banking/bank-accounts/{account.id}/"

    def test_patch_null_paynow_type_is_accepted_and_clears(self):
        """The exact wire value P9 fixed for create, on the update path."""
        user, _org = _org_with_banker()
        org, account = _create_account(user, _org, "000-111-333")
        client = _client(user)

        response = client.patch(
            self._url(org, account),
            {"paynow_type": None, "paynow_id": None},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        account.refresh_from_db()
        assert account.paynow_type is None
        assert account.paynow_id is None

    def test_patch_empty_string_paynow_type_stores_null_not_check_violation(self):
        """'' is the other "unset" wire value — it must normalise to NULL,
        not reach the DB and violate the CHECK (IntegrityError 500)."""
        user, _org = _org_with_banker()
        org, account = _create_account(user, _org, "000-111-444")
        client = _client(user)

        response = client.patch(
            self._url(org, account),
            {"paynow_type": "", "paynow_id": ""},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        account.refresh_from_db()
        assert account.paynow_type is None
        assert account.paynow_id is None

    def test_clearing_paynow_id_alone_refuses_the_dangling_pair(self):
        """A type without an id is a semantically broken pair — refuse it
        with a clean 400 instead of storing paynow_type='UEN', id=NULL."""
        user, _org = _org_with_banker()
        org, account = _create_account(user, _org, "000-111-555")
        client = _client(user)

        response = client.patch(
            self._url(org, account),
            {"paynow_id": ""},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.data
