"""
P9/B-4 (live-gate follow-up): the bank-account create contract accepts
unset PayNow.

The dialog sends paynow_type: null / paynow_id: null when the user
selects no PayNow — the DB columns are nullable (the CHECK allows NULL
or UEN/MOBILE/NRIC), but the ModelSerializer rejected null with a 400,
so the live e2e workflow could never create a bank account through the
UI (the mocked unit test could not see the contract break).
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
        name="Banker Org", entity_type="PRIVATE_LIMITED", base_currency="SGD"
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


class TestBankAccountCreateP9:
    def test_null_paynow_is_accepted(self):
        """paynow_type: null / paynow_id: null → 201 (the DB columns are
        nullable; "" would violate the CHECK — null is the correct wire
        value for "no PayNow")."""
        from apps.core.services.organisation_service import create_organisation

        user = AppUser.objects.create(
            id=uuid.uuid4(),
            email=f"seed_{uuid.uuid4().hex[:8]}@example.com",
            full_name="Seeder",
            is_active=True,
        )
        org = create_organisation(user=user, name="Seeded Banker Org")

        # the seeded bank-type GL account (1100 series — visible since C-4)
        from apps.core.models import Account

        gl = Account.objects.filter(org=org, is_bank=True).first()
        assert gl is not None, "the seeded chart must include bank accounts"

        client = _client(user)
        response = client.post(
            f"/api/v1/{org.id}/banking/bank-accounts/",
            {
                "account_name": "Operating",
                "bank_name": "Test Bank",
                "account_number": "000-111-222",
                "currency": "SGD",
                "gl_account": str(gl.id),
                "paynow_type": None,
                "paynow_id": None,
                "is_default": False,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data

        gl.refresh_from_db()
        from apps.core.models import BankAccount

        created = BankAccount.objects.get(org=org, account_number="000-111-222")
        assert created.paynow_type is None
