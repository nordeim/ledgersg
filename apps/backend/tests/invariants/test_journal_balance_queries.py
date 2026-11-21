"""
Trial balance / account balance query tests (H-01 remediation).

The JournalLine FK is `entry` (not `journal_entry`) and no `is_posted` field
exists — the old `journal_entry__*` lookups raised FieldError on every call,
breaking GET /journal/trial-balance/ and /journal/accounts/{id}/balance/.
"""

from datetime import date
from decimal import Decimal

import pytest

from apps.journal.services.journal_service import JournalService


@pytest.fixture
def posted_entry(test_user, test_organisation, test_accounts, test_fiscal_period):
    """A posted journal entry: 100 debit AR / 100 credit revenue."""
    return JournalService.create_entry(
        org_id=test_organisation.id,
        entry_date=date(2024, 1, 20),
        source_type="MANUAL",
        narration="Test entry",
        lines=[
            {
                "account_id": test_accounts["1200"].id,
                "debit": Decimal("100.00"),
                "credit": Decimal("0.00"),
                "description": "AR",
            },
            {
                "account_id": test_accounts["4000"].id,
                "debit": Decimal("0.00"),
                "credit": Decimal("100.00"),
                "description": "Revenue",
            },
        ],
        user_id=test_user.id,
    )


@pytest.mark.django_db
def test_get_account_balance_sums_debits_credits(
    test_organisation, test_accounts, posted_entry
):
    """Account balance must aggregate debits minus credits for the account."""
    balance = JournalService.get_account_balance(
        org_id=test_organisation.id, account_id=test_accounts["1200"].id
    )
    assert balance == Decimal("100.00")

    balance_revenue = JournalService.get_account_balance(
        org_id=test_organisation.id, account_id=test_accounts["4000"].id
    )
    assert balance_revenue == Decimal("-100.00")


@pytest.mark.django_db
def test_get_account_balance_respects_date_cutoff(
    test_user, test_organisation, test_accounts, test_fiscal_period, posted_entry
):
    """Balance as-of a date before the entry must exclude it."""
    balance = JournalService.get_account_balance(
        org_id=test_organisation.id,
        account_id=test_accounts["1200"].id,
        date_to=date(2024, 1, 1),
    )
    assert balance == Decimal("0.00")


@pytest.mark.django_db
def test_get_trial_balance_returns_rows(
    test_organisation, test_accounts, posted_entry
):
    """Trial balance must return per-account debit/credit totals that net to zero."""
    result = JournalService.get_trial_balance(org_id=test_organisation.id)

    assert isinstance(result, list) and len(result) >= 2

    by_code = {row["account_code"]: row for row in result}
    ar = by_code.get("1200")
    rev = by_code.get("4000")
    assert ar is not None and rev is not None

    assert Decimal(ar["total_debits"]) == Decimal("100.00")
    assert Decimal(rev["total_credits"]) == Decimal("100.00")

    total_debits = sum(Decimal(row["total_debits"]) for row in result)
    total_credits = sum(Decimal(row["total_credits"]) for row in result)
    assert total_debits == total_credits, "Trial balance must balance"
