"""
Integration tests for Journal Entry Workflow.

Tests double-entry accounting including balance validation and reversals.
Updated for SQL schema field alignment (source_type, narration, source_id).
"""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from apps.core.models import JournalEntry, JournalLine


@pytest.mark.django_db
def test_create_journal_entry_success(
    auth_client, test_organisation, test_accounts, test_fiscal_period, test_user
):
    """Test creating a balanced journal entry."""
    url = f"/api/v1/{test_organisation.id}/journal-entries/entries/"

    ar_account = test_accounts["1200"]
    revenue_account = test_accounts["4000"]

    response = auth_client.post(
        url,
        {
            "entry_date": "2024-01-15",
            "source_type": "MANUAL",
            "narration": "Test journal entry",
            "fiscal_period_id": str(test_fiscal_period.id),
            "lines": [
                {
                    "account_id": str(ar_account.id),
                    "description": "AR increase",
                    "debit": "100.00",
                    "credit": "0.00",
                },
                {
                    "account_id": str(revenue_account.id),
                    "description": "Revenue recognition",
                    "debit": "0.00",
                    "credit": "100.00",
                },
            ],
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["source_type"] == "MANUAL"


@pytest.mark.django_db
def test_journal_entry_unbalanced_rejected(
    auth_client, test_organisation, test_accounts, test_fiscal_period
):
    """Test that unbalanced journal entries are rejected."""
    url = f"/api/v1/{test_organisation.id}/journal-entries/entries/"

    ar_account = test_accounts["1200"]

    response = auth_client.post(
        url,
        {
            "entry_date": "2024-01-15",
            "source_type": "MANUAL",
            "narration": "Unbalanced entry",
            "lines": [
                {
                    "account_id": str(ar_account.id),
                    "description": "Only debit",
                    "debit": "100.00",
                    "credit": "0.00",
                }
            ],
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_journal_entry_validate_balance(auth_client, test_organisation, test_accounts):
    """Test the balance validation endpoint."""
    url = f"/api/v1/{test_organisation.id}/journal-entries/entries/validate/"

    ar_account = test_accounts["1200"]
    revenue_account = test_accounts["4000"]

    response = auth_client.post(
        url,
        {
            "lines": [
                {"account_id": str(ar_account.id), "debit": "100.00", "credit": "0.00"},
                {"account_id": str(revenue_account.id), "debit": "0.00", "credit": "100.00"},
            ]
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["valid"] is True
    assert response.data["total_debits"] == "100.00"
    assert response.data["total_credits"] == "100.00"
    assert response.data["difference"] == "0.00"


@pytest.mark.django_db
def test_journal_entry_validate_unbalanced(auth_client, test_organisation, test_accounts):
    """Test validation catches unbalanced entries."""
    url = f"/api/v1/{test_organisation.id}/journal-entries/entries/validate/"

    ar_account = test_accounts["1200"]

    response = auth_client.post(
        url,
        {
            "lines": [
                {"account_id": str(ar_account.id), "debit": "100.00", "credit": "0.00"},
                {"account_id": str(ar_account.id), "debit": "50.00", "credit": "0.00"},
            ]
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["valid"] is False
    assert response.data["difference"] == "150.00"


@pytest.mark.django_db
def test_journal_entry_reversal(
    auth_client, test_organisation, test_accounts, test_fiscal_period, test_user
):
    """Test creating a reversal entry."""
    from apps.journal.services import JournalService

    ar_account = test_accounts["1200"]
    revenue_account = test_accounts["4000"]

    original = JournalService.create_entry(
        org_id=test_organisation.id,
        entry_date=date(2024, 1, 15),
        source_type="MANUAL",
        narration="Original entry",
        lines=[
            {
                "account_id": ar_account.id,
                "debit": Decimal("100.00"),
                "credit": Decimal("0.00"),
                "description": "AR",
            },
            {
                "account_id": revenue_account.id,
                "debit": Decimal("0.00"),
                "credit": Decimal("100.00"),
                "description": "Revenue",
            },
        ],
        fiscal_period_id=test_fiscal_period.id,
        user_id=test_user.id,
    )

    url = f"/api/v1/{test_organisation.id}/journal-entries/entries/{original.id}/reverse/"
    response = auth_client.post(
        url, {"reversal_date": "2024-01-20", "reason": "Correction needed"}, format="json"
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert "reversal" in response.data

    reversal = JournalEntry.objects.get(id=response.data["reversal"]["id"])
    lines = list(reversal.lines.all())

    ar_line = [line for line in lines if line.account_id == ar_account.id][0]
    revenue_line = [line for line in lines if line.account_id == revenue_account.id][0]

    assert ar_line.debit == Decimal("0.00")
    assert ar_line.credit == Decimal("100.00")
    assert revenue_line.debit == Decimal("100.00")
    assert revenue_line.credit == Decimal("0.00")


@pytest.mark.django_db
def test_trial_balance(
    auth_client, test_organisation, test_accounts, test_fiscal_period, test_user
):
    """Test trial balance generation."""
    from apps.journal.services import JournalService

    ar_account = test_accounts["1200"]
    revenue_account = test_accounts["4000"]

    JournalService.create_entry(
        org_id=test_organisation.id,
        entry_date=date(2024, 1, 15),
        source_type="MANUAL",
        narration="Test entry",
        lines=[
            {
                "account_id": ar_account.id,
                "debit": Decimal("200.00"),
                "credit": Decimal("0.00"),
                "description": "AR",
            },
            {
                "account_id": revenue_account.id,
                "debit": Decimal("0.00"),
                "credit": Decimal("200.00"),
                "description": "Revenue",
            },
        ],
        fiscal_period_id=test_fiscal_period.id,
        user_id=test_user.id,
    )

    url = f"/api/v1/{test_organisation.id}/journal-entries/trial-balance/"
    response = auth_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    # P21/BE-M6: the unified list envelope — results + totals survive.
    assert "results" in response.data
    assert "totals" in response.data
    assert response.data["totals"]["balanced"] is True


@pytest.mark.django_db
def test_account_balance(
    auth_client, test_organisation, test_accounts, test_fiscal_period, test_user
):
    """Test getting account running balance."""
    from apps.journal.services import JournalService

    ar_account = test_accounts["1200"]
    revenue_account = test_accounts["4000"]

    JournalService.create_entry(
        org_id=test_organisation.id,
        entry_date=date(2024, 1, 15),
        source_type="MANUAL",
        narration="Entry 1",
        lines=[
            {
                "account_id": ar_account.id,
                "debit": Decimal("100.00"),
                "credit": Decimal("0.00"),
                "description": "AR",
            },
            {
                "account_id": revenue_account.id,
                "debit": Decimal("0.00"),
                "credit": Decimal("100.00"),
                "description": "Revenue",
            },
        ],
        fiscal_period_id=test_fiscal_period.id,
        user_id=test_user.id,
    )

    url = f"/api/v1/{test_organisation.id}/journal-entries/accounts/{ar_account.id}/balance/"
    response = auth_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["account_code"] == ar_account.code
    assert Decimal(response.data["balance"]) == Decimal("100.00")


@pytest.mark.django_db
def test_journal_entry_types(auth_client, test_organisation):
    """Test getting journal entry types."""
    url = f"/api/v1/{test_organisation.id}/journal-entries/entries/types/"

    response = auth_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    # P21/BE-M6: the unified list envelope ({results, count}).
    assert "results" in response.data

    types = [t["code"] for t in response.data["results"]]
    assert "MANUAL" in types
    assert "SALES_INVOICE" in types


@pytest.mark.django_db
def test_journal_entry_double_reversal_refused(
    auth_client, test_organisation, test_accounts, test_fiscal_period, test_user
):
    """P17/BE-H1: an already-reversed entry must not be reversible again.

    A second reversal would double-count every affected account (swap-side
    lines posted twice) while the trial balance stays balanced — silent GL
    corruption. The guard must refuse with a 400 before any lines post.
    """
    from apps.journal.services import JournalService

    ar_account = test_accounts["1200"]
    revenue_account = test_accounts["4000"]

    original = JournalService.create_entry(
        org_id=test_organisation.id,
        entry_date=date(2024, 1, 15),
        source_type="MANUAL",
        narration="Original entry to be reversed twice",
        lines=[
            {
                "account_id": ar_account.id,
                "debit": Decimal("100.00"),
                "credit": Decimal("0.00"),
                "description": "AR",
            },
            {
                "account_id": revenue_account.id,
                "debit": Decimal("0.00"),
                "credit": Decimal("100.00"),
                "description": "Revenue",
            },
        ],
        fiscal_period_id=test_fiscal_period.id,
        user_id=test_user.id,
    )

    url = f"/api/v1/{test_organisation.id}/journal-entries/entries/{original.id}/reverse/"

    # First reversal: accepted (the contract unchanged).
    first = auth_client.post(
        url, {"reversal_date": "2024-01-20", "reason": "Correction needed"}, format="json"
    )
    assert first.status_code == status.HTTP_201_CREATED

    lines_before = JournalLine.objects.filter(
        entry__source_type="REVERSAL", org_id=test_organisation.id
    ).count()

    # Second reversal of the SAME original: must be refused.
    second = auth_client.post(
        url, {"reversal_date": "2024-01-21", "reason": "Accidental repeat"}, format="json"
    )
    assert second.status_code == status.HTTP_400_BAD_REQUEST, (
        f"double reversal must 400, got {second.status_code}: {second.data}"
    )

    # No new reversal lines were posted by the refused attempt.
    lines_after = JournalLine.objects.filter(
        entry__source_type="REVERSAL", org_id=test_organisation.id
    ).count()
    assert lines_after == lines_before, "the refused reversal must not post lines"
