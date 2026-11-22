"""
P8/R-2 + R-3: financial reports are real.

Pre-P8: report_type=trial_balance returned {"data": {}} (a stub) while the
real trial balance lived in the journal service; the balance sheet ignored
current-period earnings (assets != liabilities + equity whenever there was
P&L activity); and both P&L and BS exposed totals only — no per-account
lines.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models import Account, AccountType, AppUser, Organisation, Role, UserOrganisation

pytestmark = pytest.mark.django_db


def _make_user_org():
    user = AppUser.objects.create(
        id=uuid.uuid4(),
        email=f"fin_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Fin Reporter",
        is_active=True,
    )
    org = Organisation.objects.create(
        name="Financial Reports Org",
        entity_type="PRIVATE_LIMITED",
        base_currency="SGD",
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


def _client(user):
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


def _fk(org, code):
    """Get or create the coarse AccountType row and link an account to it."""
    at, _ = AccountType.objects.get_or_create(code=code)
    return at


def _account(org, code, name, type_code, group):
    return Account.objects.create(
        org=org, code=code, name=name, account_type=group,
        account_type_ref=_fk(org, type_code), is_system=True, is_active=True,
    )


def _entry(org, user, number, lines):
    """Create a journal entry with the given (account, debit, credit) lines."""
    from apps.journal.services import JournalService

    return JournalService.create_entry(
        org_id=org.id,
        entry_date=date(2024, 1, 15),
        entry_type="MANUAL",
        description=f"entry {number}",
        lines=[
            {"account_id": acc.id, "debit": debit, "credit": credit}
            for acc, debit, credit in lines
        ],
        user_id=user.id,
    )


class TestFinancialReportsP8:
    def url(self, org, **params):
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"/api/v1/{org.id}/reports/financial/{('?' + qs) if qs else ''}"

    def _fixture(self):
        """An org with revenue/expense activity and an unpaid AR: 109 revenue
        booked, 30 rent expense, 109 AR — so retained earnings = 79 and the
        balance sheet must tie out (AR 109 = equity 0 + retained 79 + ... a
        clean single-sided check is: assets 109 == liabilities 0 + equity
        30? No — rent PAID leaves via a cash account. Use AP-free books:
        AR 109, revenue 109, rent expense 30 (credit AR? no). Simplest true
        fixture: cash sale — DR cash 109, CR revenue 109; DR rent 30, CR
        cash 30. Assets = cash 79, revenue 109, expense 30, retained 79:
        79 == 0 + 79. Balanced."""
        user, org = _make_user_org()
        from apps.core.models import FiscalPeriod, FiscalYear

        fy = FiscalYear.objects.create(
            org=org, label="FY2024",
            start_date=date(2024, 1, 1), end_date=date(2024, 12, 31),
            is_closed=False,
        )
        FiscalPeriod.objects.create(
            org=org, fiscal_year=fy, label="January 2024", period_number=1,
            start_date=date(2024, 1, 1), end_date=date(2024, 1, 31), is_open=True,
        )
        from apps.core.models import DocumentSequence

        DocumentSequence.objects.create(
            org=org, document_type="JOURNAL_ENTRY", prefix="JE-", next_number=1
        )
        cash = _account(org, "1010", "Cash", "ASSET", "ASSET_CURRENT")
        revenue = _account(org, "4000", "Sales", "REVENUE", "REVENUE")
        rent = _account(org, "6100", "Rent", "EXPENSE", "EXPENSE_ADMIN")

        _entry(org, user, 1, [(cash, D("109.0000"), D("0.0000")), (revenue, D("0.0000"), D("109.0000"))])
        _entry(org, user, 2, [(rent, D("30.0000"), D("0.0000")), (cash, D("0.0000"), D("30.0000"))])
        return user, org, cash, revenue, rent

    def test_trial_balance_returns_real_rows(self):
        user, org, cash, revenue, rent = self._fixture()
        client = _client(user)

        response = client.get(self.url(org, report_type="trial_balance", as_at_date="2024-12-31"))
        assert response.status_code == status.HTTP_200_OK, response.data
        data = response.data["data"]
        codes = {row["account_code"] for row in data["lines"]}
        assert codes == {"1010", "4000", "6100"}, codes
        totals = data["totals"]
        assert Decimal(totals["total_debits"]) == Decimal("139.0000")
        assert Decimal(totals["total_credits"]) == Decimal("139.0000")
        assert data["totals"]["balanced"] is True

    def test_trial_balance_respects_as_at_date(self):
        user, org, cash, revenue, rent = self._fixture()
        client = _client(user)

        # as_at BEFORE the entries: nothing on the books yet
        response = client.get(self.url(org, report_type="trial_balance", as_at_date="2024-01-01"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["lines"] == []

    def test_balance_sheet_ties_out_with_retained_earnings(self):
        user, org, cash, revenue, rent = self._fixture()
        client = _client(user)

        response = client.get(self.url(org, report_type="balance_sheet", as_at_date="2024-12-31"))
        assert response.status_code == status.HTTP_200_OK, response.data
        data = response.data["data"]

        # Assets = cash 79
        assert Decimal(data["assets_total"]) == Decimal("79.0000"), data
        assert Decimal(data["liabilities_total"]) == Decimal("0.0000")
        assert Decimal(data["equity_total"]) == Decimal("0.0000")
        # Retained earnings = revenue 109 - expense 30
        assert Decimal(data["retained_earnings"]) == Decimal("79.0000"), data
        # The statement ties out: assets == liabilities + equity + retained
        assert data["balanced"] is True, data
        # The cash line is a real per-account line
        asset_lines = data["sections"]["assets"]
        assert any(
            line["account_code"] == "1010" and Decimal(line["amount"]) == Decimal("79.0000")
            for line in asset_lines
        ), asset_lines

    def test_profit_loss_exposes_per_account_lines(self):
        user, org, cash, revenue, rent = self._fixture()
        client = _client(user)

        response = client.get(
            self.url(org, report_type="profit_loss", start_date="2024-01-01", end_date="2024-12-31")
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        data = response.data["data"]

        assert Decimal(data["revenue_total"]) == Decimal("109.0000")
        assert Decimal(data["expense_total"]) == Decimal("30.0000")
        assert Decimal(data["net_profit"]) == Decimal("79.0000")
        rev_lines = data["sections"]["revenue"]
        assert any(
            line["account_code"] == "4000" and Decimal(line["amount"]) == Decimal("109.0000")
            for line in rev_lines
        ), rev_lines
        exp_lines = data["sections"]["expenses"]
        assert any(
            line["account_code"] == "6100" and Decimal(line["amount"]) == Decimal("30.0000")
            for line in exp_lines
        ), exp_lines

    def test_permission_required(self):
        """Unauthenticated access is refused."""
        user, org, *_ = self._fixture()
        anon = APIClient()
        response = anon.get(self.url(org, report_type="profit_loss"))
        assert response.status_code in (401, 403)


def D(x: str) -> Decimal:
    return Decimal(x)
