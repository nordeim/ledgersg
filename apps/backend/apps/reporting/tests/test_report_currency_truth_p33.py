"""
P33/BE-P33-M1: the financial-reports denomination truth.

Pre-P33: the three financial report views (trial balance, P&L, balance
sheet) hardcoded "currency": "SGD" while the ledger they aggregate is
denominated in the org's base_currency (CHAR(3), default SGD, settable).
A USD-based org received reports claiming SGD. The invoice PDF template
already rendered the truthful {{ org.base_currency }} — the API responses
were the untruthful surface.
"""

import uuid
from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.core.models import Account, AppUser, Organisation, Role, UserOrganisation

pytestmark = pytest.mark.django_db


def _make_usd_org_user():
    user = AppUser.objects.create(
        id=uuid.uuid4(),
        email=f"usd_{uuid.uuid4().hex[:8]}@example.com",
        full_name="USD Reporter",
        is_active=True,
    )
    org = Organisation.objects.create(
        name="USD Base Currency Org",
        entity_type="PRIVATE_LIMITED",
        base_currency="USD",
        gst_registered=False,
    )
    role = Role.objects.create(
        org=org, name="Owner", description="owner",
        can_view_reports=True, can_manage_org=True,
        can_create_invoices=True, can_approve_invoices=True,
        can_void_invoices=True, can_create_journals=True,
        can_manage_banking=True, can_file_gst=True,
        can_manage_users=True, can_manage_coa=True, can_export_data=True,
    )
    UserOrganisation.objects.create(
        user=user, org=org, role=role, is_default=True,
        invited_at=date.today(), accepted_at=date.today(),
    )
    return user, org


def _client(user) -> APIClient:
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


def _account(org, code, name, type_code):
    """Create an account; account_type_ref links the SEEDED coarse reference
    row (ASSET/LIABILITY/REVENUE/... — the schema's reference data; the
    pre-P33 blind spot in this spec's first draft was get_or_create on a
    fine-grained code the reference table never carries)."""
    from apps.core.models import AccountType

    at = AccountType.objects.get(code=type_code)
    return Account.objects.create(
        org=org, code=code, name=name, account_type=type_code,
        account_type_ref=at, is_system=True, is_active=True,
    )


class TestReportCurrencyTruth:
    """Every financial report must carry the org's base_currency."""

    def test_trial_balance_carries_base_currency(self):
        user, org = _make_usd_org_user()
        _account(org, "4000", "Sales Revenue", "REVENUE")
        _account(org, "6100", "Rent Expense", "EXPENSE")
        client = _client(user)

        response = client.get(
            f"/api/v1/{org.id}/reports/financial/?report_type=trial_balance"
        )
        assert response.status_code == 200
        assert response.data["currency"] == "USD", (
            f"trial_balance claims currency={response.data['currency']!r} "
            f"while the org's base_currency is USD"
        )

    def test_profit_loss_carries_base_currency(self):
        user, org = _make_usd_org_user()
        _account(org, "4000", "Sales Revenue", "REVENUE")
        _account(org, "6100", "Rent Expense", "EXPENSE")
        client = _client(user)

        response = client.get(
            f"/api/v1/{org.id}/reports/financial/?report_type=profit_loss"
        )
        assert response.status_code == 200
        assert response.data["currency"] == "USD", (
            f"profit_loss claims currency={response.data['currency']!r} "
            f"while the org's base_currency is USD"
        )

    def test_balance_sheet_carries_base_currency(self):
        user, org = _make_usd_org_user()
        _account(org, "1200", "Cash at Bank", "ASSET")
        _account(org, "2100", "Accounts Payable", "LIABILITY")
        client = _client(user)

        response = client.get(
            f"/api/v1/{org.id}/reports/financial/?report_type=balance_sheet"
        )
        assert response.status_code == 200
        assert response.data["currency"] == "USD", (
            f"balance_sheet claims currency={response.data['currency']!r} "
            f"while the org's base_currency is USD"
        )
