"""
P8/R-4: custom accounts join the reports.

The P&L / balance sheet aggregate via account_type_ref__code, but
AccountService.create_account never set the FK — an org's own revenue
account (created through the API) was INVISIBLE to its financial
statements while seeded accounts showed up fine.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models import AppUser, Organisation, Role, UserOrganisation

pytestmark = pytest.mark.django_db


def _make_user_org():
    user = AppUser.objects.create(
        id=uuid.uuid4(),
        email=f"coa_{uuid.uuid4().hex[:8]}@example.com",
        full_name="COA User",
        is_active=True,
    )
    org = Organisation.objects.create(
        name="COA Reports Org",
        entity_type="PRIVATE_LIMITED",
        base_currency="SGD",
        gst_registered=False,
    )
    role = Role.objects.create(
        org=org, name="Owner", description="owner",
        can_manage_coa=True, can_view_reports=True, can_manage_org=True,
        can_create_journals=True, can_create_invoices=True,
        can_approve_invoices=True, can_void_invoices=True,
        can_manage_banking=True, can_file_gst=True,
        can_manage_users=True, can_export_data=True,
    )
    UserOrganisation.objects.create(
        user=user, org=org, role=role, is_default=True,
        invited_at=date.today(), accepted_at=date.today(),
    )
    return user, org


def _client(user):
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


class TestCustomAccountTypeRefP8:
    """A custom account created through the API must carry its
    account_type_ref so the financial statements can see it."""

    def test_create_revenue_account_sets_type_ref(self):
        user, org = _make_user_org()
        client = _client(user)

        response = client.post(
            f"/api/v1/{org.id}/accounts/",
            {
                "code": "4500",
                "name": "Consulting Revenue",
                "account_type": "REVENUE",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, response.data

        from apps.core.models import Account

        account = Account.objects.get(org=org, code="4500")
        assert account.account_type_ref_id is not None, (
            "custom account has no account_type_ref — invisible to P&L/BS"
        )
        assert account.account_type_ref.code == "REVENUE"

    def test_group_to_coarse_fk_mapping(self):
        """Every ACCOUNT_TYPE_GROUPS entry with a category that exists as a
        coarse AccountType maps correctly on create (spot-check the
        non-trivial ones: COS->COGS, LIABILITY_LONG_TERM->LIABILITY,
        REVENUE_OTHER->OTHER_INCOME)."""
        from apps.coa.services import AccountService

        user, org = _make_user_org()
        cases = [
            ("COS", "COGS"),
            ("LIABILITY_LONG_TERM", "LIABILITY"),
            ("REVENUE_OTHER", "OTHER_INCOME"),
            ("ASSET_FIXED", "ASSET"),
            ("EQUITY", "EQUITY"),
            ("EXPENSE_ADMIN", "EXPENSE"),
        ]
        from apps.coa.services import ACCOUNT_TYPE_GROUPS

        for idx, (group, expected_fk) in enumerate(cases, start=1):
            prefix = ACCOUNT_TYPE_GROUPS[group]["code_prefix"]
            code = f"{prefix}{idx:03d}"  # e.g. COS -> "5001"
            acc = AccountService.create_account(
                org_id=org.id,
                code=code,
                name=f"Test {group}",
                account_type=group,
                description="",
            )
            acc.refresh_from_db()
            assert acc.account_type_ref is not None, (group, "no FK set")
            assert acc.account_type_ref.code == expected_fk, (group, acc.account_type_ref.code)

    def test_custom_revenue_account_visible_in_profit_loss(self):
        """End-to-end truth: book revenue on a CUSTOM account; the P&L must
        include it (pre-P8 the account_type_ref filter made it vanish)."""
        user, org = _make_user_org()
        client = _client(user)

        created = client.post(
            f"/api/v1/{org.id}/accounts/",
            {"code": "4600", "name": "Custom Revenue", "account_type": "REVENUE"},
            format="json",
        )
        assert created.status_code == status.HTTP_201_CREATED, created.data
        account_id = created.data["id"]

        # Book 200 of revenue on the custom account via a journal entry
        from apps.core.models import Account, DocumentSequence, FiscalPeriod, FiscalYear
        from apps.journal.services import JournalService

        fy = FiscalYear.objects.create(
            org=org, label="FY2024",
            start_date=date(2024, 1, 1), end_date=date(2024, 12, 31),
            is_closed=False,
        )
        FiscalPeriod.objects.create(
            org=org, fiscal_year=fy, label="Jan 2024", period_number=1,
            start_date=date(2024, 1, 1), end_date=date(2024, 1, 31), is_open=True,
        )
        DocumentSequence.objects.create(
            org=org, document_type="JOURNAL_ENTRY", prefix="JE-", next_number=1
        )
        cash = Account.objects.create(
            org=org, code="1010", name="Cash", account_type="ASSET_CURRENT",
            is_system=True, is_active=True,
        )
        custom = Account.objects.get(id=account_id)
        JournalService.create_entry(
            org_id=org.id,
            entry_date=date(2024, 1, 15),
            entry_type="MANUAL",
            description="custom revenue booking",
            lines=[
                {"account_id": cash.id, "debit": Decimal("200.0000"),
                 "credit": Decimal("0.0000")},
                {"account_id": custom.id, "debit": Decimal("0.0000"),
                 "credit": Decimal("200.0000")},
            ],
            user_id=user.id,
        )

        response = client.get(
            f"/api/v1/{org.id}/reports/financial/"
            "?report_type=profit_loss&start_date=2024-01-01&end_date=2024-12-31"
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        data = response.data["data"]
        assert Decimal(data["revenue_total"]) == Decimal("200.0000"), data
        assert any(
            line["account_code"] == "4600" for line in data["sections"]["revenue"]
        ), data["sections"]
